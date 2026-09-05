Great—thanks for the exact filenames. You have:

* `build/libftd2xx.1.4.30.dylib` (dynamic library)
* `build/libftd2xx.a` (static library)
* `ftd2xx.h`, `WinTypes.h`
* plus some subfolders

Below is a **from-scratch, copy-pasteable** setup that works with *your* files and avoids guessing.

---

# 1) Make a clean project folder

```bash
mkdir -p ~/Desktop/FT232H_RPM
cd ~/Desktop/FT232H_RPM
```

Copy the **headers** and the **.dylib** in:

```bash
# adjust the source path below to wherever your "release" folder actually is:
cp /Users/jon/Desktop/FT232H_RPM/release/ftd2xx.h .
cp /Users/jon/Desktop/FT232H_RPM/release/WinTypes.h .
cp /Users/jon/Desktop/FT232H_RPM/release/build/libftd2xx.1.4.30.dylib .
```

(Optional but convenient) add a symlink with a generic name:

```bash
ln -sf libftd2xx.1.4.30.dylib libftd2xx.dylib
```

You should now have:

```
~/Desktop/FT232H_RPM/
  ftd2xx.h
  WinTypes.h
  libftd2xx.1.4.30.dylib
  libftd2xx.dylib  -> libftd2xx.1.4.30.dylib (symlink)
```

---

# 2) Check architecture (VERY IMPORTANT on Apple Silicon)

Your Mac is **arm64**. Make sure the library matches:

```bash
lipo -info libftd2xx.1.4.30.dylib
```

* If it says **arm64** (or **arm64 x86\_64**), you’re good.
* If it says **x86\_64 only**, you have an Intel-only build. Either:

  * grab an **arm64** macOS D2XX build, **or**
  * run under Rosetta (see “Plan B” at the end).

---

# 3) Create the app source file

Create `rpm_reader.c` here with this content (same as earlier, kept local-include):

```c
// rpm_reader.c — FT232H + D2XX RPM reader for Castle ESC AUX "RPM OUT"
// Wiring: ESC white AUX -> 1k -> FT232H AD0 (D0); ESC GND -> FT232H GND
// Build:  clang -O2 -Wall rpm_reader.c -o rpm_reader -I. -L. -l:libftd2xx.1.4.30.dylib -Wl,-rpath,@executable_path

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <time.h>
#ifdef __APPLE__
#include <mach/mach_time.h>
#endif

#include "ftd2xx.h"   // in current directory

static int    motor_poles = 14;     // total magnets, e.g. 14 -> 7 pole-pairs
static double gear_ratio  = 1.0;    // motor:rotor (10.0 for 10:1)
static int    dev_index   = 0;      // FTDI device index to open
static double window_s    = 0.05;   // seconds per RPM sample (50 ms)

static double now_s(void) {
#ifdef __APPLE__
    static mach_timebase_info_data_t tb;
    static uint64_t start = 0;
    if (!tb.denom) mach_timebase_info(&tb);
    if (!start) start = mach_absolute_time();
    uint64_t t = mach_absolute_time() - start;
    double ns = (double)t * (double)tb.numer / (double)tb.denom;
    return ns * 1e-9;
#else
    struct timespec ts; clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;
#endif
}

static void die(const char *msg, FT_STATUS st) {
    fprintf(stderr, "%s (FT_STATUS=%ld)\n", msg, (long)st);
    exit(1);
}

static void usage(const char *prog) {
    fprintf(stderr,
        "Usage: %s [--poles N] [--ratio R] [--index I] [--window S]\n"
        "  --poles   Total motor poles (default 14)\n"
        "  --ratio   Gear ratio motor:rotor (default 1.0)\n"
        "  --index   FTDI device index to open (default 0)\n"
        "  --window  Seconds per RPM sample window (default 0.05)\n",
        prog);
}

int main(int argc, char **argv) {
    for (int i=1; i<argc; ++i) {
        if (!strcmp(argv[i], "--poles") && i+1<argc)      motor_poles = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--ratio") && i+1<argc) gear_ratio  = atof(argv[++i]);
        else if (!strcmp(argv[i], "--index") && i+1<argc) dev_index   = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--window") && i+1<argc)window_s    = atof(argv[++i]);
        else { usage(argv[0]); return 1; }
    }
    if (motor_poles < 2) motor_poles = 2;
    int pole_pairs = motor_poles / 2;
    if (pole_pairs < 1) pole_pairs = 1;
    if (gear_ratio <= 0.0) gear_ratio = 1.0;
    if (window_s < 0.01) window_s = 0.01;

    FT_STATUS st;
    FT_HANDLE ft;

    st = FT_Open(dev_index, &ft);
    if (st != FT_OK) die("FT_Open failed", st);

    FT_SetLatencyTimer(ft, 2); // ms

    UCHAR mask = 0x00; // all inputs
    UCHAR mode = 0x01; // async bit-bang
    st = FT_SetBitMode(ft, mask, mode);
    if (st != FT_OK) die("FT_SetBitMode failed", st);

    printf("# t_s, edges, edges_per_s, motor_rpm, rotor_rpm\n");
    double t0 = now_s();
    double block_start = t0;

    UCHAR prev = 0, cur = 0;
    st = FT_GetBitMode(ft, &prev);
    if (st != FT_OK) die("FT_GetBitMode (init) failed", st);
    prev &= 0x01;

    for (;;) {
        unsigned edges = 0;
        double deadline = block_start + window_s;

        while (now_s() < deadline) {
            st = FT_GetBitMode(ft, &cur);
            if (st != FT_OK) die("FT_GetBitMode failed", st);
            UCHAR bit = cur & 0x01;  // AD0 is LSB
            if (prev == 0 && bit == 1) edges++; // rising edge
            prev = bit;
        }

        double window_actual = now_s() - block_start;
        block_start = now_s();

        double eps = edges / (window_actual > 0 ? window_actual : window_s);
        double motor_rpm = (eps * 60.0) / pole_pairs;
        double rotor_rpm = motor_rpm / gear_ratio;

        printf("%.3f,%u,%.1f,%.0f,%.0f\n",
               now_s()-t0, edges, eps, motor_rpm, rotor_rpm);
        fflush(stdout);
    }

    FT_Close(ft);
    return 0;
}
```

---

# 4) Build (links to your exact dylib name)

```bash
cd ~/Desktop/FT232H_RPM
clang -O2 -Wall rpm_reader.c -o rpm_reader \
  -I. -L. \
  -l:libftd2xx.1.4.30.dylib \
  -Wl,-rpath,@executable_path
```

**Why this works:**

* `-I.` and `-L.`: use headers and libs from the current folder
* `-l:…` links **that exact filename** (no need to rename)
* `-Wl,-rpath,@executable_path` lets the app find the dylib **next to the binary** at runtime

> If Gatekeeper blocks the library the first time, clear quarantine once:
>
> ```bash
> xattr -dr com.apple.quarantine libftd2xx.1.4.30.dylib rpm_reader
> ```

---

# 5) Wire & run

**Wiring recap**

* ESC **white AUX** → **1 kΩ** → FT232H **AD0 (D0)**
* ESC **GND** → FT232H **GND**
* Don’t connect the ESC +5 V to FT232H VCC (FT232H is USB powered)

**Run**

```bash
./rpm_reader --poles 14 --ratio 1.0 --index 0 --window 0.05
```

You should see CSV rows like:

```
# t_s, edges, edges_per_s, motor_rpm, rotor_rpm
0.051,125,2482.5,21236,21236
0.102,121,2410.3,20659,20659
```

Tweak flags as needed:

* `--poles N` → total motor poles (14 ⇒ 7 pole-pairs)
* `--ratio R` → motor\:rotor (10.0 for 10:1)
* `--window S` → 0.02–0.10 typical
* `--index I` → if multiple FTDI devices connected

---

## If you get errors

* **`ld: library not found for -l:libftd2xx.1.4.30.dylib`**
  Ensure the file is in the same directory as you’re compiling from and you included `-L.`

* **`dyld: Library not loaded: libftd2xx.1.4.30.dylib`**
  Ensure `-Wl,-rpath,@executable_path` is in the compile line, or run once with:

  ```bash
  export DYLD_LIBRARY_PATH=.
  ./rpm_reader ...
  ```

* **`image not found` or Apple security prompt**
  Clear quarantine:

  ```bash
  xattr -dr com.apple.quarantine libftd2xx.1.4.30.dylib rpm_reader
  ```

  If it still complains, open **System Settings → Privacy & Security** and click **Allow Anyway** for the blocked item, then run again.

* **Architecture mismatch**
  If `lipo -info` showed **x86\_64 only** and your Mac is arm64:

  * Best: obtain an **arm64** build of `libftd2xx.1.4.30.dylib`.
  * Plan B (Rosetta): build and run everything as x86\_64:

    ```bash
    # compile for x86_64
    arch -x86_64 clang -O2 -Wall rpm_reader.c -o rpm_reader_x86 \
      -I. -L. -l:libftd2xx.1.4.30.dylib -Wl,-rpath,@executable_path
    # run under Rosetta
    arch -x86_64 ./rpm_reader_x86 --poles 14 --ratio 1.0
    ```

* **Always zero edges**
  Check wiring (AD0/D0 is bit 0), **common ground**, and confirm **AUX = RPM Out** in Castle Link.

---

## Optional: static link (no .dylib at runtime)

If you want to avoid the dynamic library entirely and the static **`.a`** matches your architecture, you can link it directly:

```bash
clang -O2 -Wall rpm_reader.c -o rpm_reader_static \
  -I. /path/to/release/build/libftd2xx.a
```

If that works, you can run `./rpm_reader_static` without shipping a `.dylib`.

---

That’s the whole path with your specific `libftd2xx.1.4.30.dylib`. If you hit a specific compiler or runtime message, paste it verbatim and I’ll adjust the exact flags fast.
