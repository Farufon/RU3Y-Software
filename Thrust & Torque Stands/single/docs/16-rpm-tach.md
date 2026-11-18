# 16 - Rotor RPM in `live.py` (FT232H tach)

One Adafruit FT232H breakout counting the Castle ESC's AUX **RPM OUT**
pulses. `live.py` runs the compiled reader for it as a child process, parses
its CSV, and shows rotor RPM with a 90 second strip chart under the thrust
panel. Capture fills `head_rpm_actual` from the tach so you stop typing it.

The reader itself, its FTDI library, the Castle Link setup and the wiring
handbook all live in `rpm/`. This doc is the part that touches the stand.

## The numbers that matter

| | value | where it is set |
|---|---|---|
| Motor | T-Motor Antigravity MN6007 II 320KV, **24N28P** | |
| Magnets | **28**, so **14 pole pairs** | `--rpm-poles 28` (default) |
| Drivetrain | **3:1** helical step-down, motor to rotor | the **Gear ratio** box on the page, or `--rpm-ratio` |
| Sample window | 50 ms | `--rpm-window 0.05` |

Rotor rpm = motor rpm / 3. Motor rpm = (rising edges per second x 60) / 14.
At hover, 1800 rotor rpm is 5400 motor rpm, 1260 edges per second, 63 edges per
50 ms window. The panel shows `edges/win`; at hover expect about 63.

**Verify the chain once with an optical tach on the rotor.** Castle's wording,
"toggles the AUX line at every electrical commutation", can be read as one
pulse per electrical cycle or as one per commutation step (three rising edges
per cycle). The reader assumes one rising edge per pole pair per revolution,
which is what your earlier runs used. If the optical tach reads a third of
the panel, the fix is `--rpm-poles 84` (three edges per pair looks like three
times the magnets), not a code change. Doc 05a step 4 is where this check
goes.

## Build the reader, once

```
bash rpm/scripts/build_static.sh
```

Produces `rpm/rpm_reader_static` and `rpm/list_ftdi`. Needs `clang` from the
Apple command line tools. The binaries are not tracked in git; `start.sh`
builds them if they are missing. `live.py` looks for the reader in `rpm/`
beside `tools/` and says so at startup if it is not there.

## Which board

`start.sh` finds it. By hand:

```
cd rpm
./list_ftdi
# index=0  serial=FT6JABCD  desc=Single RS232-HS
```

A board with a serial number is started by serial and the plug can move:

```
python3 live.py --port /dev/cu.usbserial-1480 --tach FT6JABCD
```

Adafruit boards usually have a blank serial, in which case `--tach 0` (the
default) is all there is, and that index follows the hub socket. `find_ports.py`
writes whichever applies into `ports.json`. One stand, one board; if more are
plugged in the first is used and you are told.

## Running

```
bash tools/start.sh
```

or by hand:

```
source ~/venvs/forcerigs/bin/activate
cd tools
python3 live.py --port /dev/cu.usbserial-1480 --tach 0
```

Defaults are 28 poles, 3:1, 50 ms. The banner prints the reader path and
settings. `--no-rpm` runs thrust only.

The gear ratio is a box on the page, next to the RPM chart: type the
motor:rotor ratio and press Apply or Enter. It takes effect on the next tach
row, no restart. The value is kept in `tools/live-settings.json` and comes
back on the next launch; `--rpm-ratio` on the command line overrides it and
stores it. The reader binary only reports motor rpm to live.py; rotor rpm is
computed in live.py, which is why the box can change it live.
`logs/rpm-*.csv` carries the ratio in force on every row.

The RPM card has a dot: green with rows arriving, amber if the reader is up
but nothing has come in for 1.5 s, red if the reader process is down (its
last complaint is shown). A down reader restarts itself every 3 s, so
replugging the board recovers without restarting `live.py`.

Capture takes the tach's 5 s average as `head_rpm_actual`. The reader prints
a row every window whether or not anything is turning, so below 30 rpm the
tach counts as no reading rather than as 0 rpm. Typing a value in the RPM
actual box overrides the tach for that row; the tach average still goes in
`rpm_tach`.

## Log files

`logs/rpm-YYYYmmdd-HHMMSS.csv` gets every reader row, 20 rows per second at
the default window. Columns: `iso_time, epoch_s, edges, motor_rpm,
rotor_rpm, ratio`.

`logs/stream-*.csv` carries `rpm` on every thrust row: the latest rotor rpm
if it is under a second old, else blank.

`logs/run-log.csv` carries `head_rpm_actual` and `rpm_tach`. `reduce.py`
uses the first.

## Wiring recap

ESC white (AUX) through **1 kΩ** to FT232H **D0**, ESC ground to FT232H
**GND**. Nothing to the FT232H 5 V or 3.3 V pins; it is USB powered. Keep the
white lead short. `rpm/docs/` has the full handbook and the Castle Link steps
to set AUX to RPM OUT.

Nothing crosses the torque cradle (doc 14). The tach lead goes down the tube
with the throttle lead.

## Things that will bite you

- **`reader down: FT_Open failed (FT_STATUS=2)`** means the board at that
  index or serial is not there. Run `./list_ftdi`.
- **`FT_STATUS=3`**, device in use, means another copy of the reader is still
  holding it. `bash tools/stop.sh` kills them.
- **A Terminal window from `run_dual.scpt` and `live.py` cannot share the
  board.** Pick one.
- **Edges but wrong rpm** is poles or ratio, not wiring. Check `edges/win`
  against the 63 at hover figure above.
- **Zero edges on a spinning motor** is wiring or Castle Link: AUX defaults to
  disabled until a mode is written.
- The D2XX driver and Apple's own FTDI VCP driver compete for the chip. If
  `FT_Open` fails with the board plainly present, the VCP driver has it; the
  handbook's tutorial covers unloading it.
