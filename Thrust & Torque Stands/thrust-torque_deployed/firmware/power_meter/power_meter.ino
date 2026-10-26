/*
 * Nacelle Power Meter, two channels (port and stbd)
 * Two Hall-effect current sensors + two resistor dividers + one Arduino Nano
 *
 * Each nacelle has its own pack. One sensor and one divider per pack, all on
 * the same Nano so both channels are sampled on one clock and reported in one
 * CSV row. Reports pack volts, amps and watts for both over USB so live.py
 * can show them next to thrust and RPM.
 *
 * The current sensors are Pololu ACS724 carriers, +-50 A bidirectional
 * (Pololu #4049, Allegro ACS724LLCTR-50AB). Hall sensors: the pack positive
 * passes THROUGH the sensor (IP+ to IP-) and the measurement side is
 * galvanically isolated from it. Nothing is inserted in either negative lead,
 * so there is no shunt voltage for the USB grounds to short around.
 *
 * Wiring, per channel (P = port, S = stbd)
 *   Pack +  -> ACS724 IP+ ;  ACS724 IP- -> nacelle +     (12 AWG, soldered)
 *   Pack -  -> nacelle -   straight through, unbroken
 *   ACS724 VCC -> Nano 5V, GND -> Nano GND
 *   ACS724 OUT -> A0 (port)  or  A2 (stbd)
 *   Pack +  -> 100k -> A1 (port) or A3 (stbd) -> 10k -> GND   (1% resistors)
 *   100 nF from the divider tap to GND
 *
 * Both dividers return to the one Nano GND, so the two pack negatives share
 * a reference through 10k. They already share one through the ESC RPM leads
 * and the USB hub; this adds nothing new. Keep the divider ground wires thin
 * (22 AWG or so) so they can never carry motor current.
 *
 * Sensor math (datasheet, VCC = 5 V): OUT = 2.5 V + 0.040 V/A * I.
 * Sensor and ADC are both ratiometric to the 5 V rail, so zero current is
 * 512 counts and 40 mV/A is 8.19 counts/A regardless of the USB rail.
 * Those are the defaults; 'z', 'ka', 'kv' trim them, 'w' stores them.
 *
 * Divider: 100k / 10k puts 25.2 V (6S full) at 2.29 V on the tap.
 *
 * Serial: 115200 baud. Send 'h' for help.
 * Row: n,ms,vP,aP,wP,vS,aS,wS,rawIP,rawVP,rawIS,rawVS
 *
 * Upload with Arduino IDE 1.8.19, board Arduino Nano, processor plain
 * ATmega328P. NOT IDE 2.x and NOT Old Bootloader. docs/13 has the story.
 */

#include <EEPROM.h>

// ---------------------------------------------------------------- pins

const uint8_t PIN_I[2] = { A0, A2 };   // ACS724 OUT, port then stbd
const uint8_t PIN_V[2] = { A1, A3 };   // divider taps, port then stbd
const char    CH_NAME[2] = { 'p', 's' };

// ---------------------------------------------------------------- config

const uint32_t SERIAL_BAUD = 115200;
const uint16_t STREAM_MS   = 50;    // 20 rows per second
const uint8_t  OVERSAMPLE  = 16;    // ADC reads per channel per row (4 channels * 16 ~ 7 ms)

const float    I_ZERO_NOMINAL  = 512.0f;
const float    I_COUNTS_PER_A  = 0.040f * 1023.0f / 5.0f;   // 8.184 counts/A
const float    V_PER_COUNT     = 5.0f / 1023.0f * 11.0f;    // divider 100k/10k

// ---------------------------------------------------------------- EEPROM

const int      EE_MAGIC_ADDR = 0;
const int      EE_DATA       = 4;              // 6 floats follow
const uint32_t EE_MAGIC      = 0x50575232UL;   // "PWR2"

// ---------------------------------------------------------------- state

struct Cal { float iZero, iGain, vScale; };
struct Row { float rawI[2], rawV[2], amps[2], volts[2]; };
Cal      cal[2];
bool     calibrated = false;
bool     streaming  = false;
uint32_t lastStream = 0;
uint32_t sampleNum  = 0;

char     cmdBuf[24];
uint8_t  cmdLen = 0;

void setNominal() {
  for (uint8_t c = 0; c < 2; ++c) {
    cal[c].iZero = I_ZERO_NOMINAL; cal[c].iGain = I_COUNTS_PER_A; cal[c].vScale = V_PER_COUNT;
  }
}

// ---------------------------------------------------------------- EEPROM helpers

void saveSettings() {
  uint32_t magic = EE_MAGIC;
  EEPROM.put(EE_MAGIC_ADDR, magic);
  EEPROM.put(EE_DATA, cal);
}

bool loadSettings() {
  uint32_t magic = 0;
  EEPROM.get(EE_MAGIC_ADDR, magic);
  if (magic != EE_MAGIC) { setNominal(); return false; }
  EEPROM.get(EE_DATA, cal);
  bool ok = true;
  for (uint8_t c = 0; c < 2; ++c) {
    if (isnan(cal[c].iZero)  || cal[c].iZero < 300 || cal[c].iZero > 700) { cal[c].iZero = I_ZERO_NOMINAL; ok = false; }
    if (isnan(cal[c].iGain)  || cal[c].iGain <= 0)   { cal[c].iGain = I_COUNTS_PER_A; ok = false; }
    if (isnan(cal[c].vScale) || cal[c].vScale <= 0)  { cal[c].vScale = V_PER_COUNT;   ok = false; }
  }
  return ok;
}

// ---------------------------------------------------------------- sampling

float readAvg(uint8_t pin, uint8_t n) {
  analogRead(pin);                  // throw one away after a mux change
  uint32_t acc = 0;
  for (uint8_t i = 0; i < n; ++i) acc += analogRead(pin);
  return (float)acc / n;
}


void sampleRow(Row &r) {
  for (uint8_t c = 0; c < 2; ++c) {
    r.rawI[c]  = readAvg(PIN_I[c], OVERSAMPLE);
    r.rawV[c]  = readAvg(PIN_V[c], OVERSAMPLE);
    r.amps[c]  = (r.rawI[c] - cal[c].iZero) / cal[c].iGain;
    r.volts[c] = r.rawV[c] * cal[c].vScale;
  }
}

// ---------------------------------------------------------------- output

void printHeader() {
  Serial.println(F("# n,ms,vP,aP,wP,vS,aS,wS,rawIP,rawVP,rawIS,rawVS"));
}

void printRow() {
  Row r; sampleRow(r);
  Serial.print(sampleNum++);  Serial.print(',');
  Serial.print(millis());     Serial.print(',');
  for (uint8_t c = 0; c < 2; ++c) {
    Serial.print(r.volts[c], 3);             Serial.print(',');
    Serial.print(r.amps[c], 3);              Serial.print(',');
    Serial.print(r.volts[c] * r.amps[c], 1); Serial.print(',');
  }
  Serial.print(r.rawI[0], 1); Serial.print(',');
  Serial.print(r.rawV[0], 1); Serial.print(',');
  Serial.print(r.rawI[1], 1); Serial.print(',');
  Serial.println(r.rawV[1], 1);
}

void printHelp() {
  Serial.println();
  Serial.println(F("=== Nacelle Power Meter, 2 channel ==="));
  Serial.println(F("  h              this help"));
  Serial.println(F("  r              single reading"));
  Serial.println(F("  s              start / stop streaming (20 Hz)"));
  Serial.println(F("  z              ZERO both currents. packs connected, motors OFF."));
  Serial.println(F("  ka p <amps>    calibrate port amps at a steady known load, e.g. 'ka p 18.4'"));
  Serial.println(F("  ka s <amps>    same for stbd"));
  Serial.println(F("  kv p <volts>   calibrate port volts against a meter, e.g. 'kv p 24.87'"));
  Serial.println(F("  kv s <volts>   same for stbd"));
  Serial.println(F("  d              dump settings"));
  Serial.println(F("  w              write settings to EEPROM"));
  Serial.println(F("  x              reset to nominal sensor values (does not write)"));
  Serial.println();
  Serial.println(F("Order: 'z' with motors off, 'kv' per pack against a meter, 'ka' per"));
  Serial.println(F("channel at a steady load, then 'w'. Repeat 'z' each session."));
  Serial.println();
}

void printSettings() {
  Row r; sampleRow(r);
  Serial.println();
  Serial.print(F("  calibrated (EEPROM)     : ")); Serial.println(calibrated ? F("yes") : F("NO, nominal values"));
  for (uint8_t c = 0; c < 2; ++c) {
    Serial.print(F("  [")); Serial.print(CH_NAME[c]); Serial.println(']');
    Serial.print(F("  iZero  (counts at 0 A)  : ")); Serial.println(cal[c].iZero, 2);
    Serial.print(F("  iGain  (counts per A)   : ")); Serial.println(cal[c].iGain, 4);
    Serial.print(F("  vScale (volts per count): ")); Serial.println(cal[c].vScale, 6);
    Serial.print(F("  now rawI / rawV         : ")); Serial.print(r.rawI[c], 1); Serial.print(F(" / ")); Serial.println(r.rawV[c], 1);
    Serial.print(F("  now volts / amps        : ")); Serial.print(r.volts[c], 3); Serial.print(F(" / ")); Serial.println(r.amps[c], 3);
  }
  Serial.println();
}

// ---------------------------------------------------------------- commands

float settle(uint8_t pin) {
  float acc = 0;
  for (uint8_t i = 0; i < 16; ++i) { acc += readAvg(pin, 64); delay(10); }
  return acc / 16.0f;
}

void doZero() {
  Serial.println(F("# zeroing both currents, motors off, hold still..."));
  for (uint8_t c = 0; c < 2; ++c) {
    cal[c].iZero = settle(PIN_I[c]);
    Serial.print(F("# iZero ")); Serial.print(CH_NAME[c]); Serial.print(F(" = ")); Serial.println(cal[c].iZero, 2);
  }
  Serial.println(F("# 'w' to keep it"));
}

int chanOf(char c) {
  if (c == 'p' || c == 'P') return 0;
  if (c == 's' || c == 'S') return 1;
  return -1;
}

void doCalAmps(int c, float refAmps) {
  if (refAmps <= 0.5f) { Serial.println(F("# need a real load, > 0.5 A")); return; }
  float delta = settle(PIN_I[c]) - cal[c].iZero;
  if (delta < 2.0f) { Serial.println(F("# sensor sees almost nothing. wiring? direction?")); return; }
  cal[c].iGain = delta / refAmps;
  Serial.print(F("# iGain ")); Serial.print(CH_NAME[c]); Serial.print(F(" = ")); Serial.print(cal[c].iGain, 4);
  Serial.print(F(" counts/A  (nominal ")); Serial.print(I_COUNTS_PER_A, 4); Serial.println(')');
  Serial.println(F("# 'w' to keep it"));
}

void doCalVolts(int c, float refVolts) {
  if (refVolts <= 1.0f) { Serial.println(F("# need a real voltage")); return; }
  float raw = settle(PIN_V[c]);
  if (raw < 20.0f) { Serial.println(F("# divider reads almost nothing. pack connected?")); return; }
  cal[c].vScale = refVolts / raw;
  Serial.print(F("# vScale ")); Serial.print(CH_NAME[c]); Serial.print(F(" = ")); Serial.print(cal[c].vScale, 6);
  Serial.print(F(" V/count  (nominal ")); Serial.print(V_PER_COUNT, 6); Serial.println(')');
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
      const char *p = cmd + 2;
      while (*p == ' ') ++p;
      int c = chanOf(*p);
      if (c < 0 || (cmd[1] != 'a' && cmd[1] != 'v')) { Serial.println(F("# ka p|s <amps>  or  kv p|s <volts>")); break; }
      float val = atof(p + 1);
      if (cmd[1] == 'a') doCalAmps(c, val); else doCalVolts(c, val);
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
  for (uint8_t c = 0; c < 2; ++c) { pinMode(PIN_I[c], INPUT); pinMode(PIN_V[c], INPUT); }
  delay(50);
  calibrated = loadSettings();
  Serial.println();
  Serial.println(F("# Nacelle Power Meter  2x ACS724 +-50A + dividers  (port A0/A1, stbd A2/A3)"));
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
