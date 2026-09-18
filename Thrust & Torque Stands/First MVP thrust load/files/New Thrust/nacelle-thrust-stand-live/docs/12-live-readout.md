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

Open `http://localhost:8000`.

For the iPad, use the Mac's VPN address instead of `localhost`. The server
binds all interfaces by default; pass `--bind 127.0.0.1` to lock it to the
Mac only.

Useful flags:

| Flag | Default | Notes |
|---|---|---|
| `--port` | auto if exactly one `usbserial` | serial device |
| `--http-port` | 8000 | change if something else has 8000 |
| `--bind` | `0.0.0.0` | `127.0.0.1` for local only |
| `--logdir` | `tools/logs/` | where the CSVs go |
| `--radius` | 457.0 | rotor radius mm, used for `z_over_R` |

Nothing here touches the ESC or the motor. It reads the cell and writes files.

To leave the environment, `deactivate`. Closing the Terminal window does the
same thing.

## What it gives you

**Live number.** Current thrust in lbf, plus newtons, raw counts, and the age
of the last sample. Goes amber if samples stop arriving.

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

**Capture point.** Fill in height, RPM, collective, throttle, volts, amps, then
press Capture. It averages the last 5 seconds of thrust and appends one row to
`run-log.csv` in the schema `reduce.py` already expects. `z_over_R` is computed
for you.

**Power chart.** Predicted electrical watts against thrust for 1600 through
2000 rpm, with the 7.5 lbf target marked, and your captured points laid over
it in white. Divergence between the dots and the curves is the real result of
this whole exercise.

## Log files

`logs/stream-YYYYmmdd-HHMMSS.csv` gets **every** sample that arrives, with a
wall-clock timestamp alongside the board's `millis()`. New file each launch.

`logs/run-log.csv` gets one row per captured grid point. Appended across
launches, so it accumulates. Feed it straight to `reduce.py`.

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
- Only one program can hold the port. Quit the Arduino Serial Monitor before
  starting `live.py`, and stop `live.py` before uploading firmware.
- Opening the port resets the board, which re-tares against whatever is sitting
  on the cell at that instant. Do not launch with a load hanging.
- The app reconnects on its own if the USB drops, but the board will have
  reset and re-tared. If a run looks discontinuous, that is why. Re-tare.
- `sd` in the statistics panel is population standard deviation over the
  window, not a measurement uncertainty. Drift shows up in it too.
