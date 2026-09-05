
# FT232H → macOS: Real-Time RPM from Castle ESC (No Python)

> Outcome: a self-contained binary (`rpm_reader_static`) that reads the Castle **AUX (white) RPM OUT** via **FT232H** and prints RPM in real time.

---

## What You’ll Need

* **FT232H breakout (USB-C, STEMMA QT)** — e.g., Adafruit Product 2264. ([Adafruit][1])
* **Your Castle Phoenix Edge Lite 50 ESC** (any Edge/Edge Lite with AUX works). ([Castle Homepage][2])
* **1 kΩ resistor** (series protection on the AUX signal).
* **Jumper wires**.
* **Mac with Apple Command Line Tools** (`clang`). Check with:

  ```bash
  clang --version
  ```
* **FTDI D2XX (macOS) SDK/driver** (we’ll use its headers + static library). ([FTDI][3])

---

# STEP A — Wire It (2 connections)

**Do not** power FT232H from the ESC — it’s USB-powered from your Mac.

```
[ESC] AUX (white) ──[ 1 kΩ ]──► AD0 / D0  (FT232H)
[ESC] GND (black)  ───────────► GND       (FT232H)
```

**Notes**

* Shared ground is essential.
* The AUX (white) must be configured to **RPM Out** in Castle Link (one-time config, see Step 6).




# STEP B - Configure Castle ESC AUX = RPM OUT (Castle Link Classic)

> Props off. Bench test only.

## 1) Hardware hookup (in the right order)

1. **Unplug** the ESC **AUX/white** lead from any receiver/device. Castle specifically warns to disconnect AUX before linking. ([Castle Homepage][1])
2. Plug the ESC’s **3-wire throttle lead** into the **Castle Link USB** adapter. ([Castle Homepage][1])
3. Connect the Castle Link USB adapter to your **Windows PC** (Castle Link runs on Windows).
4. **Then** power the ESC from its main battery. (Castle notes applying main power after you’ve connected the USB link.) ([Castle Homepage][1])

> If Castle Link can’t “see” the ESC, recheck this order and that AUX is unplugged.

## 2) Open Castle Link (Classic)

* Launch **Castle Link Classic** (the “legacy” UI—distinct from Castle Link 2). Castle’s own article shows both Classic and the newer “Castle Link 2,” and confirms Classic is still used with the V3 USB kit. ([Castle Homepage][2])

> If you only have Castle Link 2 installed, no problem—the setting name is the same. The path may look a bit different visually.

## 3) Read the ESC & (optional) update firmware

* Wait for the software status bar to show your ESC is connected; use **Update/Read** to pull settings.
* If a firmware update prompt appears, you can accept it now for best compatibility. (Castle Link article covers firmware updating with Classic.) ([Castle Homepage][2])

## 4) Find the AUX Wire setting

* In **Castle Link Classic**, go to the menu/tab where **AUX / Auxiliary Wire Mode** is listed (on Edge/Edge Lite, AUX modes are selectable only via Castle Link). The Edge user guide states the **AUX line is disabled until a mode is selected** with Castle Link. ([Minicars][3])

> Depending on version, you’ll see AUX items among the advanced/other menus. Castle’s docs and product pages describe the AUX as the **“user-programmable white wire.”** ([Castle Homepage][4])

## 5) Select **RPM OUT**

* Choose **RPM OUT** for **AUX Wire Mode**.
* Castle’s Edge manuals and tech tip define RPM OUT as:
  **“The ESC toggles the AUX line at every electrical commutation. Divide by magnetic pole-pairs to get mechanical RPM.”** ([LeoMotion Download][5])

*(Optional)* Leave “Idle Datalog Erase” **off** unless you want AUX toggling at idle to clear logs. (Castle calls this out as an add-on behavior in Castle Link.) ([Castle Homepage][6])

## 6) Write settings & power-cycle

* Click **Update/Write** (or **Send Settings to Controller**) to save.
* **Disconnect** main power, then remove the USB link.
* Your **white wire now outputs a TTL pulse train** proportional to commutation. (You’ll use that for your FT232H reader, flight controller capture, or an I²C tach bridge.)

## 7) Verify the output (quick sanity)

* Re-power the ESC (still no prop), run the motor slowly, and probe the white wire vs GND with a scope or your working FT232H reader. You should see pulses that increase with throttle.
* Mechanical RPM ≈ *(edges/sec × 60) / pole-pairs*. (Pole-pairs = total magnets ÷ 2.) ([LeoMotion Download][5])

---

## Notes & references

* **AUX modes & RPM OUT definition (Edge manuals & tech tip)**: AUX is user-selectable; **RPM OUT toggles every electrical commutation**. ([LeoMotion Download][5])
* **Castle Link connection order & AUX disconnect warning** (downloads page): unplug AUX → connect Castle Link → then apply main power. ([Castle Homepage][1])
* **Classic vs Castle Link 2** (what you’re looking at): Castle’s “Castle Link Explained” article shows both UIs and when each is used. ([Castle Homepage][2])
* **Product pages reaffirm AUX = programmable white wire** on Edge series. ([Castle Homepage][7])




# STEP C — Get the FTDI D2XX SDK (macOS)

Download FTDI’s **D2XX** package for macOS. It contains:

* `ftd2xx.h` and `WinTypes.h` (headers)
* `build/libftd2xx.a` (static library) — we’ll link this to avoid any runtime `.dylib`
* Samples & notes

> FTDI D2XX driver page: **D2XX Drivers** → **Mac OS X** download. ([FTDI][3])

Assume you place/extract it at:

```
~/Desktop/FT232H_RPM/release/
  ftd2xx.h
  WinTypes.h
  build/
    libftd2xx.a
    libftd2xx.1.4.30.dylib  (not needed for static build)
```

---

# STEPH D — Create a Clean Project Folder

```bash
mkdir -p ~/Desktop/FT232H_RPM
cd ~/Desktop/FT232H_RPM
```

Confirm you have the SDK files there (either keep them in `release/` or copy them in). We’ll reference them **in place**:

```
~/Desktop/FT232H_RPM/
  release/ftd2xx.h
  release/WinTypes.h
  release/build/libftd2xx.a
```

---

# STEP E — Add the RPM Reader Source

Create `rpm_reader.c`:

```bash
cat > rpm_reader.c <<'EOF'
// rpm_reader.c — FT232H + D2XX RPM reader (static link)
// Wiring: ESC white AUX -> 1k -> FT232H AD0 (D0); ESC GND -> FT232H GND
// Usage:  ./rpm_reader_static --poles 14 --ratio 1.0 --index 0 --window 0.05

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <time.h>
#ifdef __APPLE__
#include <mach/mach_time.h>
#endif

#include "ftd2xx.h"

static int    motor_poles = 14;     // total magnets, 14 => 7 pole-pairs
static double gear_ratio  = 1.0;    // motor:rotor (10.0 for 10:1)
static int    dev_index   = 0;      // FTDI device index to open
static double window_s    = 0.05;   // seconds per RPM sample

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

static void usage(const char *p) {
    fprintf(stderr,
      "Usage: %s [--poles N] [--ratio R] [--index I] [--window S]\n"
      "  --poles   Total motor poles (default 14)\n"
      "  --ratio   Gear ratio motor:rotor (default 1.0)\n"
      "  --index   FTDI device index to open (default 0)\n"
      "  --window  Seconds per RPM sample (default 0.05)\n", p);
}

static void die(const char *msg, FT_STATUS st) {
    fprintf(stderr, "%s (FT_STATUS=%ld)\n", msg, (long)st);
    exit(1);
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
    int pole_pairs = motor_poles / 2; if (pole_pairs < 1) pole_pairs = 1;
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

    UCHAR prev=0, cur=0;
    st = FT_GetBitMode(ft, &prev);
    if (st != FT_OK) die("FT_GetBitMode (init) failed", st);
    prev &= 0x01; // AD0

    for (;;) {
        unsigned edges = 0;
        double deadline = block_start + window_s;

        while (now_s() < deadline) {
            st = FT_GetBitMode(ft, &cur);
            if (st != FT_OK) die("FT_GetBitMode failed", st);
            UCHAR bit = cur & 0x01; // AD0 (LSB)
            if (!prev && bit) edges++;
            prev = bit;
        }

        double dt = now_s() - block_start;
        block_start = now_s();
        double eps = edges / (dt > 0 ? dt : window_s);
        double motor_rpm = (eps * 60.0) / pole_pairs;
        double rotor_rpm = motor_rpm / gear_ratio;

        printf("%.3f,%u,%.1f,%.0f,%.0f\n", now_s()-t0, edges, eps, motor_rpm, rotor_rpm);
        fflush(stdout);
    }

    FT_Close(ft);
    return 0;
}
EOF
```

---

# STEP F — Build a **Static** Binary (no runtime `.dylib`)

> This links against FTDI’s **static** library so your app runs anywhere without shipping extra files.

```bash
# (optional) Confirm the static library exists:
test -f release/build/libftd2xx.a || echo "Missing: release/build/libftd2xx.a"

# (optional) Check its architecture (arm64 preferred on Apple Silicon):
lipo -info release/build/libftd2xx.a

# Build:
clang -O2 -Wall rpm_reader.c -o rpm_reader_static \
  -Irelease \
  release/build/libftd2xx.a \
  -framework IOKit -framework CoreFoundation
```

**If the `.a` is x86\_64-only** and your Mac is Apple Silicon, use Rosetta to build & run:

```bash
arch -x86_64 clang -O2 -Wall rpm_reader.c -o rpm_reader_static_x86 \
  -Irelease \
  release/build/libftd2xx.a \
  -framework IOKit -framework CoreFoundation

arch -x86_64 ./rpm_reader_static_x86 --poles 14 --ratio 1.0
```

---

# STEP G — Configure the ESC AUX to **RPM Out** (one time)

Open **Castle Link** on Windows (using the Castle Link USB adapter), connect the ESC, and set the **AUX/White Wire** function to **RPM Out** (naming can vary slightly by firmware UI, but look for AUX/Auxiliary Wire Mode). On Edge/Edge Lite, AUX supports RPM and telemetry modes. ([Castle Homepage][4])

> Tip: After you save/apply settings, power-cycle the ESC.

---

# STEP H — Run It

1. Plug **FT232H → Mac** (USB-C).
2. Power the ESC + motor (props removed).
3. Run:

```bash
cd ~/Desktop/FT232H_RPM
./rpm_reader_static --poles 14 --ratio 1.0 --index 0 --window 0.05
```

You’ll see CSV-style lines like:

```
# t_s, edges, edges_per_s, motor_rpm, rotor_rpm
0.050,120,2400.0,20571,20571
0.100,118,2360.0,20228,20228
```

**Parameters**

* `--poles` = total motor magnets (e.g., 14 ⇒ 7 pole-pairs)
* `--ratio` = motor\:rotor gear ratio (10.0 for 10:1)
* `--window` = sample window seconds (0.02–0.10 typical)
* `--index` = 0 unless you have multiple FTDI devices attached

**Log to CSV**

```bash
./rpm_reader_static --poles 14 --ratio 1.0 > rpm_log.csv
```

---

## Troubleshooting

* **Compiler can’t find headers**
  Ensure `release/ftd2xx.h` exists (we used `-Irelease`).

* **Missing `libftd2xx.a`**
  Confirm it’s at `release/build/libftd2xx.a`. If not present, re-download the macOS D2XX package. ([FTDI][3])

* **Architecture mismatch**
  If `lipo -info` shows only `x86_64` on an Apple-silicon Mac, use the Rosetta commands shown above or obtain an arm64 library.

* **Always zero edges**

  * Check wiring (AD0/D0 is bit 0 on FT232H).
  * Confirm **common ground** between ESC and FT232H.
  * Verify Castle AUX really is set to **RPM Out** and the motor is actually commutating.
  * Try a longer `--window 0.10` while testing.

* **Multiple FTDI devices**
  Try `--index 1` (etc.).

---

## Where to Buy (handy links)

* **Adafruit FT232H Breakout (USB-C)**: Adafruit store page. ([Adafruit][1])
* **Alternate FT232H listings** (retailers): examples on Amazon / Jameco / others. ([Amazon][5])
* **Castle Phoenix Edge Lite 50 product page** (reference/specs). ([Castle Homepage][2])
* **FTDI D2XX Drivers (macOS)** — official driver/SDK downloads. ([FTDI][3])

---

### Safety

Spin-testing can be dangerous. **Remove props**, clamp the motor/airframe, and keep clear while validating RPM.

---

We can extend this with a **“higher-rate” sampler** (synchronous bit-bang with buffered reads) and/or a small **I²C scan** utility next — both on the same FTDI D2XX stack.

[1]: https://www.adafruit.com/product/2264?srsltid=AfmBOoqDS3rauLb61qHovqUXyKXyc_LqX7658f08hTQYDhxJaqLpyJty&utm_source=chatgpt.com "Adafruit FT232H Breakout - General Purpose USB to GPIO ..."
[2]: https://www.castlecreations.com/en/phoenix-edge-lite-50-esc-010-0113-00?utm_source=chatgpt.com "PHOENIX EDGE LITE 50 AMP ESC, 8S / 34V WITH 5 ..."
[3]: https://ftdichip.com/drivers/d2xx-drivers/?utm_source=chatgpt.com "D2XX Drivers"
[4]: https://home.castlecreations.com/phoenix-edge-lite?utm_source=chatgpt.com "Phoenix Edge Lite — Castle Homepage"
[5]: https://www.amazon.com/Adafruit-Industries-FT232H-Breakout-General/dp/B09CJNVTS7?utm_source=chatgpt.com "Amazon.com: Adafruit Industries FT232H Breakout ..."
