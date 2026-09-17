/*
  torque_stand.ino  -  reaction torque stand, standalone board

  Second Arduino Nano, second HX711, second load cell, own USB port.
  Deliberately NOT sharing the thrust stand's board: separate rigs, separate
  sketches, separate serial ports. See docs/14 for what that costs you in
  time alignment.

  HARDWARE
    Nano (ATmega328P) + Adafruit HX711 #5974 + ATO micro S-type 5 kg,
    M6 male thread both ends.

    HX711 VIN -> Nano 5V
    HX711 GND -> Nano GND
    HX711 DAT -> Nano D2
    HX711 SCK -> Nano D3
    HX711 VIO   unconnected
    RATE switch on L (10 SPS) unless you have measured H and preferred it.

    Cell red    -> E+      (excitation +)
    Cell black  -> E-      (excitation -)
    Cell green  -> A+      (signal +)
    Cell white  -> A-      (signal -)
    Cell shield -> Nano GND, at the Nano end ONLY.

  LIBRARY
    "HX711 Arduino Library" by Bogdan Necula. Not the SparkFun one, not
    the Queuetue one. The API below assumes Bogdan's.

  WHAT IT REPORTS
    Torque directly in newton metres. Calibration is done in torque units
    by hanging a known mass at a caliper-measured radius, so the arm length
    cancels out of the result and never appears in the maths. ARM_R is
    stored only so the sketch can also report the tangential force at the
    cell, which is what you want when you are checking you have not
    overloaded it.

    Reading line:   n,ms,Nm,N,raw
      n    sample counter since boot
      ms   millis() on this board
      Nm   torque, newton metres, signed
      N    tangential force at the load cell pin, newtons
      raw  tare-corrected counts, before calFactor

  SIGN
    The rotor turns one way, so torque is one-signed in service. Set the
    sign once so that running the motor reads POSITIVE, and leave it. As on
    the thrust stand, 'c' always makes the calibration direction positive,
    so if you calibrate by pulling the arm the wrong way you must follow
    with 'f'. Check 'd' before every run.

  WHAT IS NOT STORED
    Tare. setup() re-tares on every boot, and opening the serial port
    resets the board, so never start with the loom dressed differently
    from how it will be in the run, and never start with the rotor turning.

  COMMANDS
    h ?          this help
    t            tare, 32 samples
    r            one reading, 8 samples
    s            toggle streaming
    c <N.m>      calibrate against a known applied torque, 32 samples
    a <mm>       set arm radius, axis to cell pin, for the force column
    f            flip sign, writes EEPROM
    z            raw counts, 32 samples, no tare or scaling
    d            dump settings
    w            force EEPROM write
*/

#include <EEPROM.h>
#include "HX711.h"

// ------------------------------------------------------------------ pins --
const uint8_t PIN_DOUT = 2;
const uint8_t PIN_SCK  = 3;

// --------------------------------------------------------------- sampling --
const uint8_t  READ_AVG  = 8;    // conversions per reported value
const uint8_t  TARE_AVG  = 32;
const uint8_t  CAL_AVG   = 32;
const uint16_t STREAM_MS = 100;  // requested; RATE=L makes the real rate ~1.2 Hz

// ----------------------------------------------------------------- eeprom --
const int EE_MAGIC = 0;   // uint16
const int EE_CAL   = 2;   // float
const int EE_SIGN  = 6;   // int8
const int EE_ARM   = 7;   // float
const uint16_t MAGIC = 0x7451;

// ---------------------------------------------------------------- globals --
HX711 cell;

float  calFactor = 700000.0f;  // counts per N.m, ballpark until calibrated
int8_t signFlag  = 1;
float  armR_mm   = 150.0f;     // axis to cell pin, millimetres

long          tareOffset = 0;
bool          streaming  = false;
unsigned long lastStream = 0;
unsigned long sampleN    = 0;

char    lineBuf[24];
uint8_t lineLen = 0;

// ---------------------------------------------------------------- helpers --
long readRaw(uint8_t n) {
  // Bogdan's read_average returns a long already averaged over n conversions.
  return cell.read_average(n);
}

void doTare(uint8_t n) {
  tareOffset = readRaw(n);
  Serial.print(F("tared, offset "));
  Serial.println(tareOffset);
}

float countsToNm(long corrected) {
  return (float)signFlag * (float)corrected / calFactor;
}

void printReading(uint8_t n) {
  long corrected = readRaw(n) - tareOffset;
  float nm = countsToNm(corrected);
  float force = (armR_mm > 0.1f) ? (nm / (armR_mm / 1000.0f)) : 0.0f;

  sampleN++;
  Serial.print(sampleN);        Serial.print(',');
  Serial.print(millis());       Serial.print(',');
  Serial.print(nm, 4);          Serial.print(',');
  Serial.print(force, 3);       Serial.print(',');
  Serial.println(corrected);
}

void saveSettings() {
  EEPROM.put(EE_MAGIC, MAGIC);
  EEPROM.put(EE_CAL,   calFactor);
  EEPROM.put(EE_SIGN,  signFlag);
  EEPROM.put(EE_ARM,   armR_mm);
  Serial.println(F("settings written"));
}

void loadSettings() {
  uint16_t m = 0;
  EEPROM.get(EE_MAGIC, m);
  if (m != MAGIC) {
    Serial.println(F("no stored settings, using defaults"));
    return;
  }
  EEPROM.get(EE_CAL,  calFactor);
  EEPROM.get(EE_SIGN, signFlag);
  EEPROM.get(EE_ARM,  armR_mm);
  if (!(calFactor > 1.0f)) calFactor = 700000.0f;
  if (signFlag != 1 && signFlag != -1) signFlag = 1;
  if (!(armR_mm > 0.1f)) armR_mm = 150.0f;
}

void dumpSettings() {
  Serial.println(F("--- settings ---"));
  Serial.print(F("calFactor : ")); Serial.print(calFactor, 4);
  Serial.println(F(" counts per N.m"));
  Serial.print(F("sign      : ")); Serial.println((int)signFlag);
  Serial.print(F("armR      : ")); Serial.print(armR_mm, 2);
  Serial.println(F(" mm  (display only, not in the torque maths)"));
  Serial.print(F("tare      : ")); Serial.println(tareOffset);
  Serial.print(F("full scale: "));
  Serial.print(49.03f * (armR_mm / 1000.0f), 3);
  Serial.println(F(" N.m for a 5 kg cell at this radius"));
  Serial.println(F("----------------"));
}

void doCalibrate(float knownNm) {
  if (!(knownNm > 0.0f)) {
    Serial.println(F("ERR: calibration torque must be positive N.m"));
    return;
  }
  long corrected = readRaw(CAL_AVG) - tareOffset;
  long mag = corrected < 0 ? -corrected : corrected;
  if (mag < 1000L) {
    Serial.print(F("ERR: only "));
    Serial.print(mag);
    Serial.println(F(" counts of signal. Is the torque actually applied?"));
    return;
  }
  calFactor = (float)mag / knownNm;
  signFlag  = (corrected >= 0) ? 1 : -1;
  saveSettings();
  Serial.print(F("calFactor "));
  Serial.print(calFactor, 4);
  Serial.println(F(" counts per N.m"));
  Serial.println(F("NOTE: 'c' forces the CALIBRATION direction positive."));
  Serial.println(F("      If the motor drives the arm the other way, send 'f' now."));
}

void printHelp() {
  Serial.println(F("torque stand - commands"));
  Serial.println(F("  h ?      help"));
  Serial.println(F("  t        tare (32)"));
  Serial.println(F("  r        one reading (8)"));
  Serial.println(F("  s        toggle stream"));
  Serial.println(F("  c <N.m>  calibrate against a known applied torque (32)"));
  Serial.println(F("  a <mm>   set arm radius for the force column"));
  Serial.println(F("  f        flip sign (writes EEPROM)"));
  Serial.println(F("  z        raw counts (32)"));
  Serial.println(F("  d        dump settings"));
  Serial.println(F("  w        force EEPROM write"));
  Serial.println(F("line format: n,ms,Nm,N,raw"));
  Serial.println(F("stream is ~1.2 Hz with RATE on L and READ_AVG 8"));
}

// ---------------------------------------------------------------- command --
void handleLine(char *s) {
  while (*s == ' ') s++;
  char c = *s;
  if (c == 0) return;

  switch (c) {
    case 'h':
    case '?':
      printHelp();
      break;

    case 't':
      doTare(TARE_AVG);
      break;

    case 'r':
      printReading(READ_AVG);
      break;

    case 's':
      streaming = !streaming;
      if (streaming) Serial.println(F("stream on"));
      else           Serial.println(F("stream off"));
      break;

    case 'z': {
      long v = readRaw(CAL_AVG);
      Serial.print(F("raw "));
      Serial.println(v);
      break;
    }

    case 'd':
      dumpSettings();
      break;

    case 'w':
      saveSettings();
      break;

    case 'f':
      signFlag = (int8_t)(-signFlag);
      saveSettings();
      Serial.print(F("sign now "));
      Serial.println((int)signFlag);
      break;

    case 'c':
      doCalibrate(atof(s + 1));
      break;

    case 'a': {
      float v = atof(s + 1);
      if (v > 0.1f) {
        armR_mm = v;
        saveSettings();
        Serial.print(F("armR "));
        Serial.print(armR_mm, 2);
        Serial.println(F(" mm"));
      } else {
        Serial.println(F("ERR: arm radius must be positive mm"));
      }
      break;
    }

    default:
      Serial.println(F("? try h"));
      break;
  }
}

void pollSerial() {
  while (Serial.available()) {
    char ch = (char)Serial.read();
    if (ch == '\r') continue;
    if (ch == '\n') {
      lineBuf[lineLen] = 0;
      handleLine(lineBuf);
      lineLen = 0;
    } else if (lineLen < sizeof(lineBuf) - 1) {
      lineBuf[lineLen++] = ch;
    }
  }
}

// ------------------------------------------------------------------ setup --
void setup() {
  Serial.begin(115200);
  cell.begin(PIN_DOUT, PIN_SCK);
  cell.set_gain(128);

  loadSettings();

  // Let the bridge settle before taring. The cell has just been powered.
  delay(500);
  doTare(TARE_AVG);

  Serial.println(F("torque stand ready"));
  dumpSettings();
  Serial.println(F("h for help"));
}

void loop() {
  pollSerial();
  if (streaming && (millis() - lastStream >= STREAM_MS)) {
    lastStream = millis();
    printReading(READ_AVG);
  }
}
