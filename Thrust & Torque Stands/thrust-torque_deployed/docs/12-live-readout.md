# 12 - Live readout, logging and power overlay (`tools/live.py`)

A local web app. It holds the serial port, streams the load cell, logs
everything, and plots your measured points against the BEMT prediction for the
V49 rotor at R = 457 mm.

Open it in Safari or Chrome on the Mac, or on an iPad over the VPN. The iPad
cannot talk to the CH340 directly (iPadOS exposes no USB serial API), but it
can render a page served by the Mac that is holding the port.

## Install and run

This Mac has more than one Python on it, so everything here runs inside a
virtual environment. Do not `pip install` into the system Python.

**1. Find the Python you want.** The python.org framework build, not
`/usr/bin/python3`:

```
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 -V
```

Expect `Python 3.12.3`. If that path is wrong, `ls
/Library/Frameworks/Python.framework/Versions/` shows what is actually
installed.

**2. Create the virtual environment.** Once, ever. It lives outside the repo so
a `git clean` cannot eat it:

```
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 -m venv ~/venvs/forcerigs
```

**3. Clear the quarantine flag.** Gatekeeper attaches `com.apple.quarantine` to
files that arrived through a browser, and it propagates into the environment:

```
xattr -r -d com.apple.quarantine ~/venvs/forcerigs/
```

**4. Activate and install.** This part repeats in every new shell:

```
source ~/venvs/forcerigs/bin/activate
pip install --upgrade pip
pip3 install pyserial
```

The prompt gains a `(forcerigs)` prefix when the environment is live. That
prefix is the only reliable indicator, so look for it before blaming the code.

**5. Run it.**

```
cd tools
python3 live.py --list                       # find the port
```

The port number changes between replugs and between physical USB sockets, so
check it every session. `--list` prints what the tool can see; to ask the OS
directly instead:

```
ls /dev/cu.usbserial-*
```

Always the `cu.` device, never `tty.`. Then:

```
python3 live.py --port /dev/cu.usbserial-1430
```

Open `http://localhost:8765`.

The default is 8765, not 8000, because this Mac is already serving other
things and 8000 is the port everything grabs first. If 8765 is busy too,
`live.py` steps up to the next free port and tells you which it took. Pin one
with `--http-port` if you want it fixed; a pinned port that is occupied fails
loudly rather than landing somewhere you are not looking.

For the iPad, use the Mac's VPN address instead of `localhost`. The server
binds all interfaces by default; pass `--bind 127.0.0.1` to lock it to the
Mac only.

Useful flags:

| Flag | Default | Notes |
|---|---|---|
| `--port` | auto if exactly one `usbserial` | serial device |
| `--http-port` | 8765 | pins the port. Without it, the next free one is used |
| `--bind` | `0.0.0.0` | `127.0.0.1` for local only |
| `--logdir` | `tools/logs/` | where the CSVs go |
| `--radius` | 457.0 | rotor radius mm, used for `z_over_R` |
| `--rpm-port` / `--rpm-stbd` | `0` / `1` | FT232H index or USB serial per nacelle |
| `--rpm-poles` | 28 | MN6007 II is 24N28P |
| `--rpm-ratio` | 3.0 or last set on page | motor:rotor; also a box on the page |
| `--rpm-window` | 0.05 | seconds per rpm sample |
| `--no-rpm` | | thrust only, no tach readers |
| `--power-port` | | serial device of the power-meter Nano (doc 17); omit to type volts/amps |
| `--single` / `--dual` | `--dual` here; `--single` in the sibling package `single` | one nacelle on the bench (one RPM card, one power card) or port and stbd side by side |
| `--open` | | open the browser on the port actually bound; `start.sh` passes it |

Nothing here touches the ESC or the motor. It reads the cell and the tachs and
writes files.

To leave the environment, `deactivate`. Closing the Terminal window does the
same thing.

## What it gives you

**Live number.** Current thrust in lbf, plus newtons, raw counts, and the age
of the last sample. Goes amber if samples stop arriving.

**One nacelle or two.** This package defaults to the port and stbd cards
side by side. `--single` is the layout for the bench with one nacelle on the
stand: one rotor RPM card and one pack power card, each beside its strip
chart, with a narrow number column and a wide chart. The RPM card follows
whichever tach sees a rotor turning (above 30 rpm) and stays on it when the
motor stops; the power card follows whichever meter channel has a pack on
its divider. Both titles name the channel they are showing, so the stbd
hardware can stay plugged in without confusing anything. The sibling package
`../single` is the same code with `--single` as its default. The capture
logic is the same in both layouts: an idle tach that is still printing zeros
is never averaged into `head_rpm_actual`.

**Strip chart.** Last 90 seconds, autoscaled, with a dashed line at zero.

**Statistics.** Rolling mean, standard deviation and peak-to-peak band over 5 s
and 30 s, in both lbf and raw counts. This is how you measure your noise floor:
let it sit still for a minute and read the 30 s standard deviation.

**Controls.** Tare, single read, stream toggle, dump settings, raw counts, sign
flip, and a free-text box for anything else (`c 15.0` and so on). Sign flip
asks for confirmation because it writes EEPROM.

**The sign flip is part of calibrating on this rig, not a fallback.** The cell is
bolted under the nacelle, so you calibrate in compression and thrust pulls the
other way. Every `c` must be followed by `f`, and `c` silently re-derives the
sign, so recalibrating undoes a previous flip. The settings line under the live
number shows `sign` at all times; check it reads `-1` before a run. Doc 05 has
the full argument.

**Rotor RPM, port and starboard.** Two panels and a strip chart fed by the
FT232H tachs on the Castle ESCs. Rotor rpm big, motor rpm and edges per window
under it, 5 s mean and sd. Red is port, green is starboard. Doc 16 covers
building the reader, picking boards by serial, and what the dots mean.

**Pack power.** With `--power-port`, a third card shows watts, volts and
amps from the hall-sensor Nano with its own strip and a console for the
calibration commands. Doc 17.

**Capture point.** Fill in height, RPM cmd, collective, throttle, then press
Capture. Volts and amps fill from the power meter if it is running, else
type them. It averages the last 5 seconds of thrust and of each tach,
appends one row to `run-log.csv` in the schema `reduce.py` already expects,
and fills `head_rpm_actual` from whichever tach is live unless you typed one.
`z_over_R` is computed for you.

**Power chart.** BEMT-predicted electrical watts against thrust for 1000
through 2000 rpm, the 7.5 lbf target line, an amber diamond at the flight-test
hover point (1800 rpm, 446 W per nacelle), and your captured points in white.

Your 1800 rpm OGE point should land on the diamond. The model curves sit about
1.6 below it; that gap is known, and whether it belongs to the rotor or the
drivetrain is what the torque stand (doc 14) resolves. Where your white dots
fall relative to the diamond is the result of this rig; where they fall
relative to the curves is a comment on the model.

## Log files

`logs/stream-YYYYmmdd-HHMMSS.csv` gets **every** sample that arrives, with a
wall-clock timestamp alongside the board's `millis()`. New file each launch.

`logs/run-log.csv` gets one row per captured grid point. Appended across
launches, so it accumulates. Feed it straight to `reduce.py`.

`logs/rpm-YYYYmmdd-HHMMSS.csv` gets every tach row from both boards. New file
each launch. See doc 16.

`logs/power-YYYYmmdd-HHMMSS.csv` gets every power-meter row. New file each
launch. See doc 17.

## Volts and amps are typed in by hand

The stand has no power sensing. The Nano reads the load cell and nothing else.
The watt meter in the BOM has an LCD and no data output, so you read it and
type it in. That is why the volts and amps fields exist on the capture panel.

Consequence: the white dots on the power chart only appear once you have
entered both volts and amps for that point. A capture without them still
records thrust correctly, it just cannot be placed on the power axis.

If you later want this automated, an INA226 breakout on the Nano's I2C pins
(A4/A5) would do it and would not disturb D2/D3. That is a firmware change,
not something to attempt mid-campaign.

## Sample rate

Two things set it, and the defaults are slower than they look.

`STREAM_MS = 100` in the firmware asks for 10 Hz. But `READ_AVG = 8` means each
reported value is 8 HX711 conversions, and with the **RATE switch on L** the
HX711 converts at 10 SPS. Eight conversions take 800 ms, so `s` actually
delivers about 1.2 Hz, and the loop blocks while it collects them.

The page shows the measured rate next to the port name. Trust that number over
any of this.

To go faster, in order of preference:

1. **RATE switch to H** on the Adafruit board. 80 SPS. Eight conversions now
   take 100 ms, so you get the 10 Hz the firmware intended, with no code
   change. Per-sample noise is higher at 80 SPS, but you are averaging 8 of
   them, which claws most of it back. Measure it rather than trusting that
   claim: run 30 seconds still, read the standard deviation off the page,
   compare to what you get on L.
2. **`READ_AVG` to 1** in the firmware, and let the host average. You get every
   raw conversion in the log and can filter afterwards however you like. On H
   that is 80 samples/sec, roughly 3 kB/s, comfortable at 115200.

For steady-state hover points, 1.2 Hz is honestly fine, you are averaging 5
seconds anyway. Rate matters if you want to see transients: spool-up, collective
steps, ground-effect entry.

## Things that will bite you

- **A new Terminal window is not in the venv.** `ModuleNotFoundError: No module
  named 'serial'` almost always means you skipped
  `source ~/venvs/forcerigs/bin/activate`, not that the install failed. Check
  the prompt for `(forcerigs)`.
- **The port number is not stable.** macOS assigns `cu.usbserial-NNNN` per
  physical socket and per enumeration, so it moves when you replug or change
  sockets. Nothing is wrong. Re-run `--list`.
- The tach readers are child processes of `live.py`. Ctrl-C stops them with it;
  if one lingers, `bash tools/stop.sh` kills it.
- Only one program can hold the port. Quit the Arduino Serial Monitor before
  starting `live.py`, and stop `live.py` before uploading firmware.
- Opening the port resets the board, which re-tares against whatever is sitting
  on the cell at that instant. Do not launch with a load hanging.
- The app reconnects on its own if the USB drops, but the board will have
  reset and re-tared. If a run looks discontinuous, that is why. Re-tare.
- `sd` in the statistics panel is population standard deviation over the
  window, not a measurement uncertainty. Drift shows up in it too.


## Time-of-day clock (2026-10-15.1)

The header shows the Mac's local time of day as HH:MM:SS.tenths, in the same size as the thrust and RPM readouts. It is the same clock that stamps `iso_time` in every log row, so a camera pointed at the screen gives video a reference that lines up with the CSVs to about a tenth of a second (display refresh 100 ms; log rows carry milliseconds).


## Two-channel power (2026-10-15.3)

The power meter now reads both packs on one Nano (port A0/A1, stbd A2/A3). Two power cards, one strip with both channels, calibration commands take a channel letter: `ka p 18.4`, `kv s 24.87`. See docs/17.
