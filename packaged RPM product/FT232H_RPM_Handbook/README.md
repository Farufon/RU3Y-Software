# FT232H → Castle ESC RPM Kit (macOS, No Python)

This is a distributable handbook + project that measures **real‑time RPM** from a Castle ESC’s **AUX (white) RPM OUT** using an **FT232H** and the **FTDI D2XX** API—compiled as a **static binary** for a zero‑dependency run.

## Contents

```
FT232H_RPM_Handbook/
├─ src/
│  ├─ rpm_reader.c          # core reader (CSV to stdout)
│  └─ list_ftdi.c           # helper: list FTDI devices / serials
├─ docs/
│  ├─ C - FT232H TUTORIAL.md                 # full setup & wiring
│  ├─ QUICKSTART.md                          # concise run + logging
│  └─ RUNNING TWO RPM FT232Hs in REAL TIME.md# dual boards, AppleScript/tmux tips
├─ vendor/ftdi/
│  ├─ ftd2xx.h, WinTypes.h                   # FTDI headers
│  ├─ libftd2xx.a                            # static lib (preferred)
│  ├─ ftd2xx.cfg                             # optional config (advanced)
│  ├─ release-notes.txt                      # FTDI D2XX changelog
│  └─ ReadMe.rtf                             # FTDI install notes
├─ scripts/
│  ├─ build_static.sh                        # one-click static build
│  └─ run_dual.scpt                          # opens two Terminal windows
└─ BUILD.md                                   # build & run instructions
```

## Quick Start

1. **Props off.** Wire AUX (white) → 1 kΩ → FT232H **AD0(D0)** and **GND → GND**.  
2. Ensure Castle **AUX = RPM OUT** (Castle Link).  
3. Build static binary:

   ```bash
   ./scripts/build_static.sh
   ```

4. Run (single board):

   ```bash
   ./rpm_reader_static --poles 8 --ratio 8.0 --index 0 --window 0.05
   ```

   Log to CSV while keeping live output:

   ```bash
   ./rpm_reader_static --poles 8 --ratio 8.0 --index 0 --window 0.05 | tee rpm_log.csv
   ```

5. Run **two** FT232H boards (two windows):

   ```bash
   osascript scripts/run_dual.scpt
   ```

## Notes

- `motor_rpm` is derived from commutation edges and **pole‑pairs**.  
- `rotor_rpm = motor_rpm / gear_ratio`.  
- If you swap USB ports and device indices change, compile and use `src/list_ftdi.c` to enumerate serials and extend the reader to open by serial (optional).

---

**License & Attribution**  
FTDI headers/libraries are © FTDI and redistributed under their terms. See `vendor/ftdi/release-notes.txt` and the header notices. Your source files are yours—add your preferred license as needed.
