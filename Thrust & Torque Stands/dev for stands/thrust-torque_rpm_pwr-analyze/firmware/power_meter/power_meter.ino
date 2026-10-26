/*
 * Nacelle Power Meter
 * Hall-effect current sensor + resistor divider + Arduino Nano
 *
 * Sits in the pack lead between the LiPo and the aircraft power input, where
 * the LCD watt meter used to be. Reports pack volts, amps and watts over USB
 * as CSV so live.py can show them next to thrust and RPM.
 *
 * The current sensor is a Pololu ACS724 carrier, +-50 A bidirectional
 * (Pololu #4049, Allegro ACS724LLCTR-50AB). It is a Hall sensor: the pack
 * positive passes THROUGH it (IP+ to IP-) and the measurement side is
 * galvanically isolated from it. Nothing is inserted in the negative lead, so
 * there is no shunt voltage for the USB grounds to short around. That is the
 * whole reason for this design over a shunt meter.
 *
 * Wiring
 *   Pack +  -> ACS724 IP+ ;  ACS724 IP- -> aircraft +      (12 AWG, soldered)
 *   Pack -  -> aircraft -  straight through, unbroken
 *   ACS724 VCC -> Nano 5V, GND -> Nano GND, OUT -> Nano A0
 *   Pack +  -> 100k -> A1 -> 10k -> GND   (voltage divider, 1% resistors)
 *   100 nF from A1 to GND (optional, quiets the divider)
 *
 * Sensor math (datasheet, VCC = 5 V): OUT = 2.5 V + 0.040 V/A * I.
 * Both the sensor and the Nano ADC are ratiometric to the same 5 V rail, so
 * the ADC counts for zero current are 512 and 40 mV/A is 8.19 counts/A, no
 * matter what the USB rail does. Those are the defaults below; 'z' and
 * 'ka' trim them against reality and 'w' stores the result.
 *
 * Divider: 100k / 10k puts 25.2 V (6S full) at 2.29 V on A1. Default scale
 * is the nominal 11.0 ratio; 'kv' corrects it against a meter.
 *
 * Serial: 115200 baud. Send 'h' for help.
 *
 * Upload with Arduino IDE 1.8.19, board Arduino Nano, processor plain
 * ATmega328P. NOT IDE 2.x and NOT Old Bootloader. docs/13 has the story.
 */

#include <EEPROM.h>

// ---------------------------------------------------------------- pins

const uint8_t PIN_I = A0;     // ACS724 OUT
const uint8_t PIN_V = A1;     // divider tap

// ---------------------------------------------------------------- config

const uint32_t SERIAL_BAUD = 115200;
const uint16_t STREAM_MS   = 50;    // 20 rows per second
const uint8_t  OVERSAMPLE  = 32;    // ADC reads per channel per row (~3.5 ms each channel)

// sensor nominals, ADC counts (10-bit, VCC reference)
const float    I_ZERO_NOMINAL  = 512.0f;              // 2.5 V of 5 V
const float    I_COUNTS_PER_A  = 0.040f * 1023.0f / 5.0f;   // 8.184 counts/A
const float    V_PER_COUNT     = 5.0f / 1023.0f * 11.0f;    // divider 100k/10k

// ---------------------------------------------------------------- EEPROM

const int      EE_MAGIC_ADDR = 0;
const int      EE_IZERO      = 4;
const int      EE_IGAIN      = 8;
const int      EE_VSCALE     = 12;
const uint32_t EE_MAGIC      = 0x50575231UL;   // "PWR1"

// ---------------------------------------------------------------- state

float    iZero   = I_ZERO_NOMINAL;    // counts at zero current
float    iGain   = I_COUNTS_PER_A;    // counts per amp
float    vScale  = V_PER_COUNT;       // volts per count
bool     calibrated = false;   // true when EEPROM had valid settings
bool     streaming = false;
uint32_t lastStream = 0;
uint32_t sampleNum  = 0;

char     cmdBuf[24];
uint8_t  cmdLen = 0;

// ---------------------------------------------------------------- EEPROM helpers

void saveSettings() {
  uint32_t magic = EE_MAGIC;
  EEPROM.put(EE_MAGIC_ADDR, magic);
  EEPROM.put(EE_IZERO, iZero);
  EEPROM.put(EE_IGAIN, iGain);
  EEPROM.put(EE_VSCALE, vScale);
}

bool loadSettings() {
  uint32_t magic = 0;
  EEPROM.get(EE_MAGIC_ADDR, magic);
  if (magic != EE_MAGIC) return false;
  EEPROM.get(EE_IZERO, iZero);
  EEPROM.get(EE_IGAIN, iGain);
  EEPROM.get(EE_VSCALE, vScale);
  bool ok = true;
  if (isnan(iZero)  || iZero < 300 || iZero > 700) { iZero = I_ZERO_NOMINAL; ok = false; }
  if (isnan(iGain)  || iGain <= 0)                 { iGain = I_COUNTS_PER_A; ok = false; }
  if (isnan(vScale) || vScale <= 0)                { vScale = V_PER_COUNT;   ok = false; }
  return ok;
}

// ---------------------------------------------------------------- sampling

float readAvg(uint8_t pin, uint8_t n) {
  analogRead(pin);                  // throw one away after a mux change
  uint32_t acc = 0;
  for (uint8_t i = 0; i < n; ++i) acc += analogRead(pin);
  return (float)acc / n;
}

void sampleRow(float &rawI, float &rawV, float &amps, float &volts) {
  rawI  = readAvg(PIN_I, OVERSAMPLE);
  rawV  = readAvg(PIN_V, OVERSAMPLE);
  amps  = (rawI - iZero) / iGain;
  volts = rawV * vScale;
}

// ---------------------------------------------------------------- output

void printHeader() {
  Serial.println(F("# n,ms,volts,amps,watts,rawI,rawV"));
}

void printRow() {
  float rawI, rawV, amps, volts;
  sampleRow(rawI, rawV, amps, volts);
  Serial.print(sampleNum++);        Serial.print(',');
  Serial.print(millis());           Serial.print(',');
  Serial.print(volts, 3);           Serial.print(',');
  Serial.print(amps, 3);            Serial.print(',');
  Serial.print(volts * amps, 1);    Serial.print(',');
  Serial.print(rawI, 1);            Serial.print(',');
  Serial.println(rawV, 1);
}

void printHelp() {
  Serial.println();
  Serial.println(F("=== Nacelle Power Meter ==="));
  Serial.println(F("  h            this help"));
  Serial.println(F("  r            single reading"));
  Serial.println(F("  s            start / stop streaming (20 Hz)"));
  Serial.println(F("  z            ZERO current. pack connected, motor OFF, nothing drawing."));
  Serial.println(F("               sets the sensor's zero point. do it once per session."));
  Serial.println(F("  ka <amps>    calibrate current: run a steady known load, read the"));
  Serial.println(F("               reference meter, then e.g. 'ka 18.4'"));
  Serial.println(F("  kv <volts>   calibrate volts: read pack with a meter, then e.g. 'kv 24.87'"));
  Serial.println(F("  d            dump settings"));
  Serial.println(F("  w            write settings to EEPROM"));
  Serial.println(F("  x            reset to nominal sensor values (does not write)"));
  Serial.println();
  Serial.println(F("Order: 'z' with motor off, 'kv' against a meter, 'ka' at a steady"));
  Serial.println(F("load against the LCD watt meter, then 'w'. Repeat 'z' each session;"));
  Serial.println(F("the Hall zero drifts a little with temperature."));
  Serial.println();
}

void printSettings() {
  float rawI, rawV, amps, volts;
  sampleRow(rawI, rawV, amps, volts);
  Serial.println();
  Serial.print(F("  calibrated (EEPROM)     : ")); Serial.println(calibrated ? F("yes") : F("NO, nominal values"));
  Serial.print(F("  iZero  (counts at 0 A)  : ")); Serial.println(iZero, 2);
  Serial.print(F("  iGain  (counts per A)   : ")); Serial.println(iGain, 4);
  Serial.print(F("  vScale (volts per count): ")); Serial.println(vScale, 6);
  Serial.print(F("  now rawI / rawV         : ")); Serial.print(rawI, 1); Serial.print(F(" / ")); Serial.println(rawV, 1);
  Serial.print(F("  now volts / amps        : ")); Serial.print(volts, 3); Serial.print(F(" / ")); Serial.println(amps, 3);
  Serial.println();
}

// ---------------------------------------------------------------- commands

void doZero() {
  Serial.println(F("# zeroing current, motor off, hold still..."));
  float acc = 0;
  for (uint8_t i = 0; i < 16; ++i) { acc += readAvg(PIN_I, 64); delay(10); }
  iZero = acc / 16.0f;
  Serial.print(F("# iZero = ")); Serial.println(iZero, 2);
  Serial.println(F("# 'w' to keep it"));
}

void doCalAmps(float refAmps) {
  if (refAmps <= 0.5f) { Serial.println(F("# need a real load, > 0.5 A")); return; }
  float acc = 0;
  for (uint8_t i = 0; i < 16; ++i) { acc += readAvg(PIN_I, 64); delay(10); }
  float raw = acc / 16.0f;
  float delta = raw - iZero;
  if (delta < 2.0f) { Serial.println(F("# sensor sees almost nothing. wiring? direction?")); return; }
  iGain = delta / refAmps;
  Serial.print(F("# iGain = ")); Serial.print(iGain, 4);
  Serial.print(F(" counts/A  (nominal ")); Serial.print(I_COUNTS_PER_A, 4); Serial.println(')');
  Serial.println(F("# 'w' to keep it"));
}

void doCalVolts(float refVolts) {
  if (refVolts <= 1.0f) { Serial.println(F("# need a real voltage")); return; }
  float acc = 0;
  for (uint8_t i = 0; i < 16; ++i) { acc += readAvg(PIN_V, 64); delay(10); }
  float raw = acc / 16.0f;
  if (raw < 20.0f) { Serial.println(F("# divider reads almost nothing. pack connected?")); return; }
  vScale = refVolts / raw;
  Serial.print(F("# vScale = ")); Serial.print(vScale, 6);
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
    case 'k':
      if (cmd[1] == 'a') doCalAmps(atof(cmd + 2));
      else if (cmd[1] == 'v') doCalVolts(atof(cmd + 2));
      else Serial.println(F("# ka <amps> or kv <volts>"));
      break;
    case 'd': printSettings(); break;
    case 'w': saveSettings(); calibrated = true; Serial.println(F("# settings written")); break;
    case 'x':
      iZero = I_ZERO_NOMINAL; iGain = I_COUNTS_PER_A; vScale = V_PER_COUNT;
      Serial.println(F("# nominal values restored (not written)"));
      break;
    case 0: break;
    default: Serial.println(F("# ? send 'h' for help"));
  }
}

// ---------------------------------------------------------------- arduino

void setup() {
  Serial.begin(SERIAL_BAUD);
  analogReference(DEFAULT);       // VCC, so sensor and ADC share the rail
  pinMode(PIN_I, INPUT);
  pinMode(PIN_V, INPUT);
  delay(50);
  bool ok = loadSettings();
  calibrated = ok;
  Serial.println();
  Serial.println(F("# Nacelle Power Meter  ACS724 +-50A + divider"));
  Serial.println(ok ? F("# settings loaded from EEPROM")
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
