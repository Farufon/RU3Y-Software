/*
 * Nacelle Power Meter, single channel
 * One Hall-effect current sensor + one resistor divider + one Arduino Nano
 *
 * SINGLE-NACELLE PACKAGE. One stand, one pack, one sensor. The two-channel
 * sketch in ../thrust-torque_deployed/firmware/power_meter reads two packs on
 * one Nano; this one reads the pack on A0/A1 only and takes calibration
 * commands without a channel letter ('ka 18.4', not 'ka p 18.4'). A Nano
 * that was flashed with the two-channel sketch keeps its first-channel
 * calibration when this one is loaded (see loadSettings).
 *
 * Reports pack volts, amps and watts over USB so live.py can show them next
 * to thrust and RPM.
 *
 * The current sensor is a Pololu ACS724 carrier, +-50 A bidirectional
 * (Pololu #4049, Allegro ACS724LLCTR-50AB). Hall sensor: the pack positive
 * passes THROUGH the sensor (IP+ to IP-) and the measurement side is
 * galvanically isolated from it. Nothing is inserted in the negative lead,
 * so there is no shunt voltage for the USB grounds to short around.
 *
 * Wiring
 *   Pack +  -> ACS724 IP+ ;  ACS724 IP- -> nacelle +     (12 AWG, soldered)
 *   Pack -  -> nacelle -   straight through, unbroken
 *   ACS724 VCC -> Nano 5V, GND -> Nano GND
 *   ACS724 OUT -> A0
 *   Pack +  -> 100k -> A1 -> 10k -> GND   (1% resistors)
 *   100 nF from the divider tap to GND
 *
 * Keep the divider ground wire thin (22 AWG or so) so it can never carry
 * motor current.
 *
 * Sensor math (datasheet, VCC = 5 V): OUT = 2.5 V + 0.040 V/A * I.
 * Sensor and ADC are both ratiometric to the 5 V rail, so zero current is
 * 512 counts and 40 mV/A is 8.19 counts/A regardless of the USB rail.
 * Those are the defaults; 'z', 'ka', 'kv' trim them, 'w' stores them.
 *
 * Divider: 100k / 10k puts 25.2 V (6S full) at 2.29 V on the tap. The
 * divider path is NOT ratiometric: the tap voltage is absolute, so its ADC
 * count scales with 1/VCC, and a USB rail that sags 2% under hub load would
 * read 2% extra pack volts and watts. Each row therefore measures VCC
 * against the ATmega328P's internal 1.1 V bandgap and uses that instead of
 * assuming 5.000 V. vScale is stored as the dimensionless divider ratio
 * (nominal 11.0), and 'kv' calibrates it at whatever the rail is that day;
 * the bandgap's own part-to-part spread falls out in that calibration, and
 * only rail CHANGES after it are tracked, which is the point.
 *
 * Serial: 115200 baud. Send 'h' for help.
 * Row: n,ms,volts,amps,watts,rawI,rawV
 *
 * Upload with Arduino IDE 1.8.19, board Arduino Nano, processor plain
 * ATmega328P. NOT IDE 2.x and NOT Old Bootloader. docs/13 has the story.
 */

#include <EEPROM.h>

// ---------------------------------------------------------------- pins

const uint8_t PIN_I = A0;   // ACS724 OUT
const uint8_t PIN_V = A1;   // divider tap

// ---------------------------------------------------------------- config

const uint32_t SERIAL_BAUD = 115200;
const uint16_t STREAM_MS   = 50;    // 20 rows per second
const uint8_t  OVERSAMPLE  = 16;    // ADC reads per channel per row

const float    I_ZERO_NOMINAL  = 512.0f;
const float    I_COUNTS_PER_A  = 0.040f * 1023.0f / 5.0f;   // 8.184 counts/A
const float    V_DIV_RATIO     = 11.0f;                     // divider (100k+10k)/10k
const float    BANDGAP_V       = 1.10f;                     // nominal internal reference

// ---------------------------------------------------------------- EEPROM

const int      EE_MAGIC_ADDR = 0;
const int      EE_DATA       = 4;              // Cal follows
const uint32_t EE_MAGIC      = 0x50575233UL;   // "PWR3": single channel, divider ratio
const uint32_t EE_MAGIC_TWO  = 0x50575232UL;   // "PWR2": the two-channel sketch's layout

// ---------------------------------------------------------------- state

struct Cal { float iZero, iGain, vScale; };
struct Row { float rawI, rawV, amps, volts, vcc; };
Cal      cal;
bool     calibrated = false;
bool     streaming  = false;
uint32_t lastStream = 0;
uint32_t sampleNum  = 0;

char     cmdBuf[24];
uint8_t  cmdLen = 0;

void setNominal() {
  cal.iZero = I_ZERO_NOMINAL; cal.iGain = I_COUNTS_PER_A; cal.vScale = V_DIV_RATIO;
}

// ---------------------------------------------------------------- EEPROM helpers

void saveSettings() {
  uint32_t magic = EE_MAGIC;
  EEPROM.put(EE_MAGIC_ADDR, magic);
  EEPROM.put(EE_DATA, cal);
}

bool sane(Cal &c) {
  bool ok = true;
  if (isnan(c.iZero)  || c.iZero < 300 || c.iZero > 700) { c.iZero = I_ZERO_NOMINAL; ok = false; }
  if (isnan(c.iGain)  || c.iGain <= 0)   { c.iGain = I_COUNTS_PER_A; ok = false; }
  // the two-channel sketch before 2026-10-26 stored vScale in volts per count
  // at an assumed 5.000 V rail (about 0.054); convert to a divider ratio
  if (!isnan(c.vScale) && c.vScale > 0 && c.vScale < 1.0f) c.vScale *= 1023.0f / 5.0f;
  if (isnan(c.vScale) || c.vScale <= 0)  { c.vScale = V_DIV_RATIO;   ok = false; }
  return ok;
}

bool loadSettings() {
  uint32_t magic = 0;
  EEPROM.get(EE_MAGIC_ADDR, magic);
  if (magic == EE_MAGIC) {
    EEPROM.get(EE_DATA, cal);
    return sane(cal);
  }
  if (magic == EE_MAGIC_TWO) {
    // two-channel layout: Cal[2] at EE_DATA. Take the first channel (the one
    // wired to A0/A1), which is what this sketch reads.
    Cal both[2];
    EEPROM.get(EE_DATA, both);
    cal = both[0];
    bool ok = sane(cal);
    Serial.println(F("# calibration carried over from the two-channel sketch (its first channel); 'w' to keep"));
    return ok;
  }
  setNominal();
  return false;
}

// ---------------------------------------------------------------- sampling

float readAvg(uint8_t pin, uint8_t n) {
  analogRead(pin);                  // throw one away after a mux change
  uint32_t acc = 0;
  for (uint8_t i = 0; i < n; ++i) acc += analogRead(pin);
  return (float)acc / n;
}

// The Nano's AVcc rail, from the internal 1.1 V bandgap read against it.
// ADMUX 1110 selects the bandgap; REFS0 keeps AVcc as the reference. The
// next analogRead() rewrites ADMUX, and readAvg() already discards one
// conversion after the mux change. Out-of-range answers (rail outside
// roughly 2.8 to 7.5 V) mean the reading is nonsense; fall back to 5.0.
float readVcc() {
  ADMUX = _BV(REFS0) | _BV(MUX3) | _BV(MUX2) | _BV(MUX1);
  delay(2);                          // let the bandgap reference settle
  ADCSRA |= _BV(ADSC);
  while (bit_is_set(ADCSRA, ADSC)) { }
  uint16_t adc = ADC;
  if (adc < 150 || adc > 400) return 5.0f;
  return BANDGAP_V * 1023.0f / (float)adc;
}

// pack volts = tap counts * (VCC / 1023) * divider ratio
float countsToVolts(float rawV, float vcc) {
  return rawV * (vcc / 1023.0f) * cal.vScale;
}

void sampleRow(Row &r) {
  r.vcc   = readVcc();
  r.rawI  = readAvg(PIN_I, OVERSAMPLE);
  r.rawV  = readAvg(PIN_V, OVERSAMPLE);
  r.amps  = (r.rawI - cal.iZero) / cal.iGain;
  r.volts = countsToVolts(r.rawV, r.vcc);
}

// ---------------------------------------------------------------- output

void printHeader() {
  Serial.println(F("# n,ms,volts,amps,watts,rawI,rawV"));
}

void printRow() {
  Row r; sampleRow(r);
  Serial.print(sampleNum++);       Serial.print(',');
  Serial.print(millis());          Serial.print(',');
  Serial.print(r.volts, 3);        Serial.print(',');
  Serial.print(r.amps, 3);         Serial.print(',');
  Serial.print(r.volts * r.amps, 1); Serial.print(',');
  Serial.print(r.rawI, 1);         Serial.print(',');
  Serial.println(r.rawV, 1);
}

void printHelp() {
  Serial.println();
  Serial.println(F("=== Nacelle Power Meter ==="));
  Serial.println(F("  h            this help"));
  Serial.println(F("  r            single reading"));
  Serial.println(F("  s            start / stop streaming (20 Hz)"));
  Serial.println(F("  z            ZERO the current. pack connected, motor OFF."));
  Serial.println(F("  ka <amps>    calibrate amps at a steady known load, e.g. 'ka 18.4'"));
  Serial.println(F("  kv <volts>   calibrate volts against a meter, e.g. 'kv 24.87'"));
  Serial.println(F("  d            dump settings"));
  Serial.println(F("  w            write settings to EEPROM"));
  Serial.println(F("  x            reset to nominal sensor values (does not write)"));
  Serial.println();
  Serial.println(F("Order: 'z' with the motor off, 'kv' against a meter, 'ka' at a steady"));
  Serial.println(F("load, then 'w'. Repeat 'z' each session."));
  Serial.println();
}

void printSettings() {
  Row r; sampleRow(r);
  Serial.println();
  Serial.print(F("  calibrated (EEPROM)     : ")); Serial.println(calibrated ? F("yes") : F("NO, nominal values"));
  Serial.print(F("  vcc (bandgap)           : ")); Serial.print(r.vcc, 3); Serial.println(F(" V"));
  Serial.print(F("  iZero  (counts at 0 A)  : ")); Serial.println(cal.iZero, 2);
  Serial.print(F("  iGain  (counts per A)   : ")); Serial.println(cal.iGain, 4);
  Serial.print(F("  vScale (divider ratio)  : ")); Serial.println(cal.vScale, 4);
  Serial.print(F("  now rawI / rawV         : ")); Serial.print(r.rawI, 1); Serial.print(F(" / ")); Serial.println(r.rawV, 1);
  Serial.print(F("  now volts / amps        : ")); Serial.print(r.volts, 3); Serial.print(F(" / ")); Serial.println(r.amps, 3);
  Serial.println();
}

// ---------------------------------------------------------------- commands

float settle(uint8_t pin) {
  float acc = 0;
  for (uint8_t i = 0; i < 16; ++i) { acc += readAvg(pin, 64); delay(10); }
  return acc / 16.0f;
}

void doZero() {
  Serial.println(F("# zeroing current, motor off, hold still..."));
  cal.iZero = settle(PIN_I);
  Serial.print(F("# iZero = ")); Serial.println(cal.iZero, 2);
  Serial.println(F("# 'w' to keep it"));
}

void doCalAmps(float refAmps) {
  if (refAmps <= 0.5f) { Serial.println(F("# need a real load, > 0.5 A")); return; }
  float delta = settle(PIN_I) - cal.iZero;
  if (delta < 2.0f) { Serial.println(F("# sensor sees almost nothing. wiring? direction?")); return; }
  cal.iGain = delta / refAmps;
  Serial.print(F("# iGain = ")); Serial.print(cal.iGain, 4);
  Serial.print(F(" counts/A  (nominal ")); Serial.print(I_COUNTS_PER_A, 4); Serial.println(')');
  Serial.println(F("# 'w' to keep it"));
}

void doCalVolts(float refVolts) {
  if (refVolts <= 1.0f) { Serial.println(F("# need a real voltage")); return; }
  float vcc = readVcc();
  float raw = settle(PIN_V);
  if (raw < 20.0f) { Serial.println(F("# divider reads almost nothing. pack connected?")); return; }
  cal.vScale = refVolts / (raw * vcc / 1023.0f);
  Serial.print(F("# vScale = ")); Serial.print(cal.vScale, 4);
  Serial.print(F(" ratio  (nominal ")); Serial.print(V_DIV_RATIO, 4);
  Serial.print(F(", rail ")); Serial.print(vcc, 3); Serial.println(F(" V)"));
  Serial.println(F("# 'w' to keep it"));
}

void handleCommand(const char *cmd) {
  while (*cmd == ' ') ++cmd;
  switch (cmd[0]) {
    case 'h': printHelp(); break;
    case 'r': printHeader(); printRow(); break;
    case 's':
      streaming = !streaming;
      if (streaming) { printHeader(); lastStream = 0; }
      else Serial.println(F("# stream stopped"));
      break;
    case 'z': doZero(); break;
    case 'k': {
      if (cmd[1] != 'a' && cmd[1] != 'v') { Serial.println(F("# ka <amps>  or  kv <volts>")); break; }
      const char *p = cmd + 2;
      while (*p == ' ') ++p;
      if (*p == 'p' || *p == 's' || *p == 'P' || *p == 'S') ++p;   // tolerate the two-channel form
      float val = atof(p);
      if (cmd[1] == 'a') doCalAmps(val); else doCalVolts(val);
      break;
    }
    case 'd': printSettings(); break;
    case 'w': saveSettings(); calibrated = true; Serial.println(F("# settings written")); break;
    case 'x': setNominal(); Serial.println(F("# nominal values restored (not written)")); break;
    case 0: break;
    default: Serial.println(F("# ? send 'h' for help"));
  }
}

// ---------------------------------------------------------------- arduino

void setup() {
  Serial.begin(SERIAL_BAUD);
  analogReference(DEFAULT);
  pinMode(PIN_I, INPUT); pinMode(PIN_V, INPUT);
  delay(50);
  Serial.println();
  Serial.println(F("# Nacelle Power Meter  ACS724 +-50A + divider  (A0/A1)"));
  calibrated = loadSettings();
  Serial.println(calibrated ? F("# settings loaded from EEPROM")
                            : F("# NOT calibrated: nominal values in use. 'z', 'kv', 'ka', then 'w'."));
  Serial.println(F("# 'h' for help"));
}

void loop() {
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      cmdBuf[cmdLen] = 0;
      if (cmdLen) handleCommand(cmdBuf);
      cmdLen = 0;
    } else if (cmdLen < sizeof(cmdBuf) - 1) {
      cmdBuf[cmdLen++] = c;
    }
  }
  if (streaming && millis() - lastStream >= STREAM_MS) {
    lastStream = millis();
    printRow();
  }
}
