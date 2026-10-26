# 16 - Port and starboard rotor RPM in `live.py` (FT232H tachs)

Two Adafruit FT232H breakouts, one per nacelle, each counting the Castle ESC's
AUX **RPM OUT** pulses. `live.py` runs the compiled reader for both boards as
child processes, parses their CSV, and shows two rotor RPM numbers and a
shared 90 second strip chart under the thrust panel. Capture fills
`head_rpm_actual` from the tach so you stop typing it.

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
Apple command line tools. The binary is not in the zip; rebuild after every
unpack. `live.py` looks for it in `rpm/` beside `tools/` and says so at
startup if it is missing.

## Which board is which

FTDI indexes `0` and `1` are assigned in enumeration order and can swap when
you replug or change USB sockets. Serial numbers do not move:

```
cd rpm
./list_ftdi
# index=0  serial=FT6JABCD  desc=Single RS232-HS
# index=1  serial=FT6JEFGH  desc=Single RS232-HS
```

Then start by serial and the assignment is permanent:

```
python3 live.py --port /dev/cu.usbserial-1480 --rpm-port FT6JABCD --rpm-stbd FT6JEFGH
```

Label the boards. Port is red on the chart, starboard green, to match the
arm LEDs.

## Running

```
source ~/venvs/forcerigs/bin/activate
cd tools
python3 live.py --port /dev/cu.usbserial-1480
```

Defaults are index 0 = port, index 1 = starboard, 28 poles, 3:1, 50 ms. The
banner prints the reader path and settings. `--no-rpm` runs thrust only.

The gear ratio is a box on the page, next to the RPM chart: type the
motor:rotor ratio and press Apply or Enter. It takes effect on the next tach
row, both panels, no restart. The value is kept in `tools/live-settings.json`
and comes back on the next launch; `--rpm-ratio` on the command line
overrides it and stores it. The reader binary only reports motor rpm to
live.py; rotor rpm is computed in live.py, which is why the box can change
it live. `logs/rpm-*.csv` carries the ratio in force on every row.

Each RPM panel has a dot: green with rows arriving, amber if the reader is up
but nothing has come in for 1.5 s, red if the reader process is down (the
last stderr line is shown). A down reader restarts itself every 3 s, so
replugging a board recovers without restarting `live.py`.

In a thrust run only the nacelle on the stand is spinning, so one panel reads
and the other sits at zero. Capture takes whichever tach is live as
`head_rpm_actual`. If both are live (spin test), it takes the mean of the
two, and the per-nacelle averages go in `rpm_port` and `rpm_stbd` regardless.
Typing a value in the RPM actual box overrides the tach for that row.

## Log files

`logs/rpm-YYYYmmdd-HHMMSS.csv` gets every reader row from both boards, 20
rows per second per board at the default window, tagged `port` or `stbd`.
Columns: `iso_time, epoch_s, channel, edges, motor_rpm, rotor_rpm`.

`logs/stream-*.csv` gains `rpm_port, rpm_stbd` on every thrust row: the latest
rotor rpm from each tach if it is under a second old, else blank.

`logs/run-log.csv` gains `rpm_port, rpm_stbd` at the end. An older run-log
without those columns is widened in place on first launch (old rows padded
with blanks, nothing lost, the banner says so). `reduce.py` ignores the two
new columns.

## Wiring recap

Per nacelle: ESC white (AUX) through **1 kΩ** to FT232H **D0**, ESC ground to
FT232H **GND**. Nothing to the FT232H 5 V or 3.3 V pins; it is USB powered.
Keep the white lead short. `rpm/docs/` has the full handbook and the Castle
Link steps to set AUX to RPM OUT.

Nothing crosses the torque cradle (doc 14). The tach lead goes down the tube
with the throttle lead.

## Things that will bite you

- **`reader down: FT_Open failed (FT_STATUS=2)`** means the board at that
  index or serial is not there. Run `./list_ftdi`.
- **`FT_STATUS=3`**, device in use, means another copy of the reader is still
  holding it. `bash tools/stop.sh` kills them.
- **Two Terminal windows from `run_dual.scpt` and `live.py` cannot share a
  board.** Pick one.
- **Edges but wrong rpm** is poles or ratio, not wiring. Check `edges/win`
  against the 63 at hover figure above.
- **Zero edges on a spinning motor** is wiring or Castle Link: AUX defaults to
  disabled until a mode is written.
- The D2XX driver and Apple's own FTDI VCP driver compete for the chip. If
  `FT_Open` fails with the board plainly present, the VCP driver has it; the
  handbook's tutorial covers unloading it.
