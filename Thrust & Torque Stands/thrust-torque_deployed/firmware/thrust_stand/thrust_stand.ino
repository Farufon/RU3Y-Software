/*
 * Nacelle Thrust Stand
 * S-beam load cell + HX711 + Arduino
 *
 * Measures axial thrust on a single VTOL nacelle mounted on an axial post.
 * The cell reads compression at rest (nacelle weight) and tension under thrust
 * (thrust exceeds weight). Both are handled: you tare with the motor off, and
 * every reading after that is change from tare, which is thrust.
 *
 * Requires the bogde HX711 library.
 *   Arduino IDE -> Library Manager -> search "HX711" -> install "HX711 Arduino Library"
 *   by Bogdan Necula. Or: https://github.com/bogde/HX711
 *
 * Serial: 115200 baud. Send 'h' for help.
 *
 * Upload with Arduino IDE 1.8.19, board Arduino Nano, processor plain ATmega328P.
 * NOT IDE 2.x (avrdude 8.0 cannot write this board) and NOT Old Bootloader.
 * See docs/13-arduino-working-config.md.
 *
 * Calibration factor is stored in EEPROM and survives power cycles.
 */

#include <HX711.h>
#include <EEPROM.h>

// ---------------------------------------------------------------- pins

const uint8_t PIN_DOUT = 2;   // HX711 DT
const uint8_t PIN_SCK  = 3;   // HX711 SCK

// ---------------------------------------------------------------- config

const uint32_t SERIAL_BAUD   = 115200;
const uint16_t STREAM_MS     = 100;   // asks for 10 Hz; the real rate is set by the
                                      // HX711 RATE switch and READ_AVG below.
                                      // RATE=L (10 SPS) x READ_AVG 8 => ~1.2 Hz.
                                      // RATE=H (80 SPS) x READ_AVG 8 => 10 Hz.
const uint8_t  READ_AVG      = 8;     // HX711 samples per reported value
const uint8_t  CAL_AVG       = 32;    // samples used during calibration
const uint16_t READY_TIMEOUT_MS = 600; // per conversion; RATE=L is 100 ms, H is 12.5 ms
const float    LBF_TO_N      = 4.4482216f;

// ---------------------------------------------------------------- EEPROM

const int      EE_ADDR_MAGIC = 0;
const int      EE_ADDR_CAL   = 4;
const int      EE_ADDR_SIGN  = 8;
const uint32_t EE_MAGIC      = 0x54485231UL;   // "THR1"

// ---------------------------------------------------------------- state

HX711    scale;
float    calFactor  = 1.0f;    // HX711 counts per lbf
int8_t   signFlip   = 1;       // +1 or -1
bool     streaming  = false;
uint32_t lastStream = 0;
uint32_t sampleNum  = 0;

char     cmdBuf[24];
uint8_t  cmdLen = 0;

// ---------------------------------------------------------------- EEPROM helpers

void saveSettings() {
  uint32_t magic = EE_MAGIC;
  EEPROM.put(EE_ADDR_MAGIC, magic);
  EEPROM.put(EE_ADDR_CAL, calFactor);
  EEPROM.put(EE_ADDR_SIGN, signFlip);
}

bool loadSettings() {
  uint32_t magic = 0;
  EEPROM.get(EE_ADDR_MAGIC, magic);
  if (magic != EE_MAGIC) return false;
  EEPROM.get(EE_ADDR_CAL, calFactor);
  EEPROM.get(EE_ADDR_SIGN, signFlip);
  if (!(calFactor > 0.0f) || isnan(calFactor)) { calFactor = 1.0f; return false; }
  if (signFlip != 1 && signFlip != -1) signFlip = 1;
  return true;
}

// ---------------------------------------------------------------- measurement

// Average n HX711 conversions into out. Returns false, with a '!' line, if
// the chip stops answering. The library's own read_average()/get_units()
// call wait_ready(), which spins forever when DT stays high on a broken cell
// lead, and the stream would simply stop with no message.
bool readCounts(uint8_t n, long &out) {
  long acc = 0;
  for (uint8_t i = 0; i < n; ++i) {
    if (!scale.wait_ready_timeout(READY_TIMEOUT_MS, 1)) {
      Serial.println(F("! HX711 timeout. cell lead, DT/SCK wiring, or 5V."));
      return false;
    }
    acc += scale.read();
  }
  out = acc / n;
  return true;
}

// Thrust in lbf from absolute counts: change from tare, scaled, signed.
float countsToLbf(long raw) {
  return signFlip * (float)(raw - scale.get_offset()) / calFactor;
}

void printHeader() {
  Serial.println(F("# n,ms,lbf,N,raw"));
}

// lbf and raw come from the SAME n conversions. (Earlier builds took two
// extra conversions for raw, so the columns were from different samples and
// each row cost 10 conversions instead of 8.)
void printReading(uint8_t n) {
  long raw;
  if (!readCounts(n, raw)) return;
  float lbf = countsToLbf(raw);
  Serial.print(sampleNum++);        Serial.print(',');
  Serial.print(millis());           Serial.print(',');
  Serial.print(lbf, 4);             Serial.print(',');
  Serial.print(lbf * LBF_TO_N, 3);  Serial.print(',');
  Serial.println(raw);
}

// ---------------------------------------------------------------- commands

void printHelp() {
  Serial.println();
  Serial.println(F("=== Nacelle Thrust Stand ==="));
  Serial.println(F("  h            this help"));
  Serial.println(F("  t            TARE. motor off, rig settled. do this every run."));
  Serial.println(F("  r            single reading"));
  Serial.println(F("  s            start / stop streaming (RATE=L gives ~1.2 Hz, H gives 10)"));
  Serial.println(F("  c <lbf>      calibrate: tare first, hang known weight, then e.g. 'c 5.0'"));
  Serial.println(F("  f            flip sign. REQUIRED after every 'c' on this rig."));
  Serial.println(F("  z            raw counts, no scaling. for diagnostics."));
  Serial.println(F("  d            dump settings"));
  Serial.println(F("  w            write settings to EEPROM"));
  Serial.println();
  Serial.println(F("Procedure per run: 't' with motor off, 's' to stream, run the"));
  Serial.println(F("collective staircase at a governed RPM, 's' to stop, then 't'"));
  Serial.println(F("again and check zero."));
  Serial.println(F("If the second tare has wandered, discard the run."));
  Serial.println();
}

void dumpSettings() {
  Serial.println();
  Serial.print(F("  calFactor (counts/lbf) : ")); Serial.println(calFactor, 4);
  Serial.print(F("  sign                   : ")); Serial.println((int)signFlip);
  Serial.print(F("  tare offset (counts)   : ")); Serial.println(scale.get_offset());
  Serial.print(F("  HX711 ready            : ")); Serial.println(scale.is_ready() ? F("yes") : F("NO"));
  Serial.println();
}

void doTare() {
  Serial.println(F("# taring, hold still..."));
  long raw;
  if (!readCounts(CAL_AVG, raw)) { Serial.println(F("! tare aborted")); return; }
  scale.set_offset(raw);
  Serial.print(F("# tare offset = "));
  Serial.println(scale.get_offset());
  Serial.println(F("# zeroed. readings are now change from tare."));
}

void doCalibrate(float knownLbf) {
  if (!(knownLbf > 0.0f)) {
    Serial.println(F("! calibration weight must be positive, e.g. 'c 5.0'"));
    return;
  }
  Serial.print(F("# calibrating against "));
  Serial.print(knownLbf, 3);
  Serial.println(F(" lbf. hold still..."));

  // raw minus tare offset, unscaled.
  long raw;
  if (!readCounts(CAL_AVG, raw)) { Serial.println(F("! calibration aborted")); return; }
  float counts = (float)(raw - scale.get_offset());

  if (fabs(counts) < 1000.0f) {
    Serial.println(F("! signal too small. is the weight applied? is the cell wired?"));
    return;
  }

  if (counts < 0) {
    signFlip = -1;
    counts = -counts;
    Serial.println(F("# negative signal, sign flipped automatically"));
  } else {
    signFlip = 1;
  }

  calFactor = counts / knownLbf;
  scale.set_scale(calFactor);
  saveSettings();

  Serial.print(F("# calFactor = "));
  Serial.print(calFactor, 4);
  Serial.println(F(" counts/lbf, saved to EEPROM"));
  long again;
  if (readCounts(CAL_AVG, again)) {
    Serial.print(F("# check: reading now "));
    Serial.print(countsToLbf(again), 4);
    Serial.println(F(" lbf"));
  }
}

void handleCommand(char *s) {
  while (*s == ' ') s++;
  char c = *s;

  switch (c) {
    case 'h': case 'H': case '?':
      printHelp();
      break;

    case 't': case 'T':
      doTare();
      break;

    case 'r': case 'R':
      printHeader();
      printReading(READ_AVG);
      break;

    case 's': case 'S':
      streaming = !streaming;
      if (streaming) {
        sampleNum = 0;
        Serial.println(F("# streaming ON"));
        printHeader();
      } else {
        Serial.println(F("# streaming OFF"));
      }
      break;

    case 'c': case 'C':
      doCalibrate(atof(s + 1));
      break;

    case 'f': case 'F':
      signFlip = -signFlip;
      saveSettings();
      Serial.print(F("# sign now "));
      Serial.println((int)signFlip);
      break;

    case 'z': case 'Z': {
      long raw;
      if (readCounts(CAL_AVG, raw)) {
        Serial.print(F("# raw counts = "));
        Serial.println(raw);
      }
      break;
    }

    case 'd': case 'D':
      dumpSettings();
      break;

    case 'w': case 'W':
      saveSettings();
      Serial.println(F("# settings written"));
      break;

    case '\0':
      break;

    default:
      Serial.println(F("! unknown command, 'h' for help"));
      break;
  }
}

void pollSerial() {
  while (Serial.available()) {
    char ch = Serial.read();
    if (ch == '\n' || ch == '\r') {
      if (cmdLen > 0) {
        cmdBuf[cmdLen] = '\0';
        handleCommand(cmdBuf);
        cmdLen = 0;
      }
    } else if (cmdLen < sizeof(cmdBuf) - 1) {
      cmdBuf[cmdLen++] = ch;
    }
  }
}

// ---------------------------------------------------------------- setup / loop

void setup() {
  Serial.begin(SERIAL_BAUD);
  while (!Serial) { ; }

  scale.begin(PIN_DOUT, PIN_SCK);

  uint32_t t0 = millis();
  while (!scale.is_ready() && millis() - t0 < 3000) { delay(10); }

  if (!scale.is_ready()) {
    Serial.println(F("! HX711 not responding. check DT/SCK pins and 5V/GND."));
  }

  bool loaded = loadSettings();
  scale.set_scale(calFactor);
  long boot;
  if (readCounts(CAL_AVG, boot)) scale.set_offset(boot);
  else Serial.println(F("! boot tare skipped; send 't' once the cell answers"));

  Serial.println();
  Serial.println(F("# Nacelle Thrust Stand ready"));
  if (loaded) {
    Serial.print(F("# calibration loaded from EEPROM, calFactor = "));
    Serial.println(calFactor, 4);
  } else {
    Serial.println(F("# NO CALIBRATION STORED. readings are meaningless until you"));
    Serial.println(F("# run 't' then hang a known weight and run 'c <lbf>'."));
  }
  Serial.println(F("# 'h' for help"));
  Serial.println();
}

void loop() {
  pollSerial();

  if (streaming && (millis() - lastStream >= STREAM_MS)) {
    lastStream = millis();
    printReading(READ_AVG);
  }
}
