# Build & Run (macOS)

> Requires Apple Command Line Tools (`clang`) and the FTDI D2XX SDK files bundled in `vendor/ftdi/`.

## Static build (preferred — no runtime dylib)

```bash
cd "$(dirname "$0")/.."
clang -O2 -Wall src/rpm_reader.c -o rpm_reader_static   -Ivendor/ftdi   vendor/ftdi/libftd2xx.a   -framework IOKit -framework CoreFoundation
```

Run:

```bash
./rpm_reader_static --poles 14 --ratio 1.0 --index 0 --window 0.05
```

Log to CSV while keeping live output:

```bash
./rpm_reader_static --poles 8 --ratio 8.0 --index 0 --window 0.05 | tee rpm_log.csv
```

## Optional: Build device enumerator

```bash
clang -O2 -Wall src/list_ftdi.c -o list_ftdi   -Ivendor/ftdi vendor/ftdi/libftd2xx.a   -framework IOKit -framework CoreFoundation

./list_ftdi
```

## Notes

- `--poles` = total motor magnets (e.g., 8 or 14). Pole-pairs = poles/2.
- `--ratio` = motor:rotor gear ratio (e.g., 8.0 for 8:1).
- `--index` selects which FT232H to open (0, 1, ...).
- Increase `--window` (e.g., `0.10`) if CPU gets busy.
