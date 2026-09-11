# Nacelle Thrust Stand

An axial-post thrust stand for measuring single-nacelle thrust, electrical power, and
ground-effect behaviour on a 914 mm-disc (R = 457 mm) VTOL tilt-rotor nacelle.

Built for a two-nacelle, 15 lb tilt-rotor VTOL. Hover thrust per nacelle is 7.5 lbf.
The deliverable this rig produces is a family of curves: **electrical watts required to
produce 7.5 lbf, as a function of rotor height above ground.**

---

## Start here

- Never used an Arduino? -> `docs/10-arduino-first-time.md`
- Already have the parts and want one page? -> `docs/00-quickstart.md`
- Want to try the software before parts arrive? -> `python3 tools/bench.py --simulate`
- **Before the first spin** -> `docs/09-safety.md`

## What is in this package

```
README.md                          this file

docs/00-quickstart.md              one page, if you already have the parts
docs/01-system-design.md           why this rig, what it measures, what it cannot
docs/02-bill-of-materials.md       parts, quantities, sources, links
docs/03-mechanical-build.md        step-by-step assembly
docs/04-wiring.md                  load cell to HX711 to Arduino, noise control
docs/05-calibration.md             load cell calibration, bidirectional, through-zero check
docs/05a-pitch-and-rpm-calibration.md
                                   servo->pitch and throttle->governed RPM. Do this first.
docs/06-test-protocol.md           the height / RPM / collective grid
docs/07-data-reduction.md          turning the raw log into the delivered curves
docs/08-post-vs-hinge.md           the argument, for the conversation with Vermont
docs/09-safety.md                  read before the first spin
docs/10-arduino-first-time.md      IDE setup, Uno vs Nano, drivers, upload errors
docs/11-load-cell-datasheet.md     ATO cell dimensions, specs, and CAD envelope
docs/wiring-adafruit-hx711.svg     printable wiring diagram - Adafruit 5974 board
docs/wiring-generic-hx711.svg      printable wiring diagram - SparkFun / generic green

firmware/thrust_stand/
    thrust_stand.ino               the sketch. tare, calibrate, stream.

tools/
    bench.py                       laptop app: menu, guided run capture, CSV logging
    reduce.py                      turns the run log into the deliverable table
    requirements.txt               pyserial, and nothing else

data/
    run-log-template.csv           the sheet, if you prefer filling it in by hand
```

## The software, in one paragraph

`thrust_stand.ino` runs on the Arduino and does one job: read the load cell and print
thrust over USB. `bench.py` runs on your laptop, drives the sketch, and walks you through
taring, calibration and a full collective staircase at a governed RPM, writing rows
    into a CSV as you go.
`reduce.py` reads that CSV and interpolates the watts required at 7.5 lbf for every height
you tested. That last table is what you send to Vermont.

## The short version

1. Build the post. Nacelle on top, S-beam load cell directly underneath it, post below
   that, three splayed legs reaching past the disc radius.
2. Wire the cell to an HX711 to an Arduino. Flash the sketch.
3. `pip3 install -r tools/requirements.txt`, then `python3 tools/bench.py`.
4. Calibrate once against known weights.
5. Per height: tare, run the staircase, log each plateau, tare again to verify.
6. `python3 tools/reduce.py data/runs.csv --thrust 7.5 --radius 457`

## Expect

267 to 295 W electrical per nacelle at 7.5 lbf, out of ground effect, depending on
head RPM. Predicted 280 W at 1800 rpm, which matches Austin's measured figure. Hover
collective
about 16 deg at 0.75R at 1600 rpm, falling to 10 deg at 2000. Ground effect will save real
power near the floor, but less than
the textbook thrust benefit suggests, because it reduces induced power only.

## Read first

`docs/09-safety.md`. A 914 mm disc at hover thrust holds enough energy to kill you if a
blade lets go. The blade-failure plane is a **disc, not a cone.** Do not stand in it.
