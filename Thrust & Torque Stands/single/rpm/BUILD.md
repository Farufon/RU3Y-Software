# Build & Run (macOS)

> Requires Apple Command Line Tools (`clang`) and the FTDI D2XX SDK files bundled in `vendor/ftdi/`.

## Static build (preferred — no runtime dylib)

```bash
cd "$(dirname "$0")/.."
clang -O2 -Wall src/rpm_reader.c -o rpm_reader_static   -Ivendor/ftdi   vendor/ftdi/libftd2xx.a   -framework IOKit -framework CoreFoundation
```

Run:

```bash
./rpm_reader_static --poles 28 --ratio 3.0 --index 0 --window 0.05
```

Log to CSV while keeping live output:

```bash
./rpm_reader_static --poles 28 --ratio 3.0 --index 0 --window 0.05 | tee rpm_log.csv
```

## Optional: Build device enumerator

```bash
clang -O2 -Wall src/list_ftdi.c -o list_ftdi   -Ivendor/ftdi vendor/ftdi/libftd2xx.a   -framework IOKit -framework CoreFoundation

./list_ftdi
```

## Notes

- `--poles` = total motor magnets. MN6007 II 320KV is 24N28P: 28 magnets, 14 pole-pairs. Default 28.
- `--ratio` = motor:rotor gear ratio. The nacelle drivetrain is 3:1, so 3.0. Default 3.0.
- `--index` selects which FT232H to open (0, 1, ...); `--serial FT6JABCD` opens by USB serial instead and survives replugs. `./list_ftdi` shows both.
- Increase `--window` (e.g., `0.10`) if CPU gets busy.
