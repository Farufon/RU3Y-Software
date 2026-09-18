# 00 - Quickstart

If you already have the parts, this is the whole thing in one page.

## Build

1. Yoke clamps the nacelle trunnion, rotor axis vertical. Three bolts to a flat plate.
2. S-beam load cell bolts **directly under that plate**, stud each end, jam nuts, thread
   locker. 1.5 diameters of engagement, do not bottom out, nothing bridging the cell.
3. Lower plate, then post, then three splayed legs with feet **outside 700 mm radius**.
   (Rotor is 457 mm now; Austin has said it will grow. Cut the legs long once.)
4. No solid base plate under the disc.

## Wire

```
CELL          HX711            ARDUINO
red    -----> E+
black  -----> E-
green  -----> A+
white  -----> A-
shield -----> GND / YLW  (this end only)

              VIN or VCC ----> 5V
              GND        ----> GND
              DAT / DT   ----> D2
              SCK        ----> D3
                               USB ----> laptop
```

**Check your board first.** If the silkscreen reads VIN / VIO / GND / SCK / DAT / RATE you
have the Adafruit 5974: **leave VIO unconnected** (it is an output, not a supply input) and
set the RATE slide switch to **L**. If it reads VCC / VDD you have the SparkFun board:
jumper VCC and VDD together. Full detail and printable diagrams in doc 04.

Arduino powered from USB. Never from the flight pack.

## Flash

**Arduino IDE 1.8.19, not 2.x.** IDE 2.3.10 ships avrdude 8.0, which cannot write flash to
this board. Install "HX711 Arduino Library" by Bogdan Necula, open
`firmware/thrust_stand/thrust_stand.ino`, upload. Serial monitor at **115200**, line ending
Newline. Send `h`.

**Elegoo Nano owners:** no driver needed on macOS. Use a Mini-B **data** cable, set
Tools > Board to `Arduino Nano`, and Tools > Processor to plain **`ATmega328P`** (not Old
Bootloader). Port is `/dev/cu.usbserial-XXXX`. The headers ship loose; you only need to
solder D3, D2, GND (three consecutive pads) and 5V. Short version in
`docs/13-arduino-working-config.md`, full detail in `docs/10-arduino-first-time.md`.

## Calibrate (once)

Prop off, nacelle mounted. Warm up two minutes. `t` to tare. **Stack** a known weight on the
nacelle mount, `c 15.0`. Remove it, confirm return to zero. **Then send `f`.**

`f` is required, not conditional. The cell sits under the nacelle, so you calibrate in
compression and thrust pulls the other way; without the flip the whole campaign logs
negative. Confirm with `d` (`sign : -1`) and by lifting the mount by hand until `r` reads
positive. Any recalibration undoes it, so `f` goes last, every time. Then check linearity.

## Test (each height)

```
set post section  ->  measure rotor height with a tape  ->  't'  ->  's'
  ->  spool to a governed RPM at MIN collective, then walk the COLLECTIVE
      staircase in degrees at 0.75R, five seconds each, record settled values
      (throttle is an RPM setpoint on this head, not a power setting)
  ->  back down  ->  's'  ->  't' again and confirm zero returns
```

With `tools/live.py` instead (`source ~/venvs/forcerigs/bin/activate`, then
`python3 tools/live.py --port /dev/cu.usbserial-XXXX`, then
open `http://localhost:8000`, or the Mac's VPN address from an iPad):

```
set post section  ->  measure rotor height  ->  Tare  ->  check sign is -1
  ->  watch the 30 s statistics line until the zero is quiet  ->  Stream
  ->  spool to a governed RPM at MIN collective, walk the COLLECTIVE staircase,
      press CAPTURE POINT at each settled step with volts and amps filled in
  ->  back down  ->  Stream off  ->  Tare again and confirm zero returns
```

Same sequence, same discipline. Capture Point averages five seconds and writes the
`run-log.csv` row for you. See `docs/12-live-readout.md`.

Record thrust, volts, amps, rpm per plateau into `data/run-log-template.csv`.

Heights (z/R x 457 mm): 229, 343, 457, 571, 686, 914 mm.
The 914 is your out-of-ground-effect baseline.
RPM setpoints: 1600, 1700, 1800, 1900, 2000.

## Reduce

```
source ~/venvs/forcerigs/bin/activate
python3 tools/reduce.py data/my-runs.csv --thrust 7.5 --radius 457
```

First time on this Mac, build the environment once:

```
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 -m venv ~/venvs/forcerigs
xattr -r -d com.apple.quarantine ~/venvs/forcerigs/
source ~/venvs/forcerigs/bin/activate
pip install --upgrade pip
pip3 install pyserial
```

Every new Terminal window needs the `source` line again. The prompt shows
`(forcerigs)` when it is live. Full detail, including how to start over, is in
`docs/15-python-venv.md`.

## Expect

267 to 295 W electrical per nacelle at 7.5 lbf, out of ground effect, depending on
head RPM. Predicted 280 W at 1800 rpm, which matches Austin's measured figure. Hover
collective
about 16 deg at 0.75R at 1600 rpm, falling to 10 deg at 2000. Ground effect saving at
z/R = 0.5 will be real but smaller than
the 33 percent thrust benefit the textbook relation predicts, because ground effect
reduces induced power only.

## Do not skip

`docs/09-safety.md`. The blade failure plane is a disc, not a cone.
