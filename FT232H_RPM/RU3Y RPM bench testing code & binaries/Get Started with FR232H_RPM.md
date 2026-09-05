Awesome—let’s go all-in and assemble it as a **single distributable project**. I’ve packaged everything into a clean, print-ready, “clone-and-build” folder with your source, tutorials, quick start, dual-device notes, and FTDI vendor bits (headers/libs/config + release notes). You can grab it here:

[Download the FT232H RPM Handbook (zip)](sandbox:/mnt/data/FT232H_RPM_Handbook.zip)

### What’s inside

* `src/` — your `rpm_reader.c` + a tiny `list_ftdi.c` enumerator (handy if you want to select boards by serial)
* `docs/` — your detailed tutorial, quick-start, and “two FT232H” guide (kept intact)
* `vendor/ftdi/` — `ftd2xx.h`, `WinTypes.h`, `libftd2xx.a`, optional `ftd2xx.cfg`, `release-notes.txt`, and the FTDI ReadMe
* `scripts/` — one-shot static build script and an AppleScript that launches two Terminal windows, one per board
* `BUILD.md` — concise build & run instructions
* `README.md` — master handbook tying it all together

### How to use it (30-second version)

```bash
# unzip, then:
cd FT232H_RPM_Handbook

# 1) build static (no dylib dependency)
./scripts/build_static.sh

# 2) run one board (example: 8 poles, 8:1 gear)
./rpm_reader_static --poles 8 --ratio 8.0 --index 0 --window 0.05 | tee rpm_log.csv

# 3) run two boards in two Terminal windows
osascript scripts/run_dual.scpt
```

### Why I recommend the unified package

* **Frictionless onboarding:** one folder = everything you need; no hunting for headers or library versions.
* **Reproducible builds:** default to **static link** via `libftd2xx.a` so the binary runs without a dylib on the target machine.
* **Modular docs preserved:** your long tutorial, quick-start, and dual-device notes are still standalone, but cross-linked via the master README.

If you’d rather keep documents split across separate repos or want a polished PDF “handbook” compiled from the Markdown, say the word and I’ll export a print-grade PDF with a table of contents.
