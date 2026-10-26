# INSTALL - updating this package on the Mac, and killing stale processes

This folder is a **git working copy**: `thrust-torque_deployed` inside the
`RU3Y-Software` repository. Updates come through git, not zips. (Earlier
versions shipped as `nacelle-thrust-stand-live-*.zip` and unpacked beside the
old folder; Finder would quietly make a `... 2` copy and you would run old
code without noticing. That is why `live.py --version` prints the path of the
file that actually ran. Keep reading it.)

## Check what you are running

```
cat VERSION
python3 tools/live.py --version
```

Both print the version. `live.py --version` also prints the full path of the
file, which is the thing to look at when something seems stale. The startup
banner prints the same line every launch.

## Update

```
bash tools/stop.sh      # nothing of ours may hold a port while files change
git pull
cat VERSION
```

Everything you generate on the bench is listed in `.gitignore` and survives a
pull: `tools/logs/` (all the CSVs), `tools/ports.json` (which board is on
which socket), `tools/live-settings.json` (the gear ratio from the dashboard),
and the two binaries under `rpm/`. If you have edited a doc by hand, commit
it or copy it out first; `git status` shows what you have touched.

Commit by **named path**, never `git add .`. A bare `git add .` once bundled
a mass deletion into a commit here.

## Build the tach reader once

`live.py` spawns `rpm/rpm_reader_static` for the two FT232H boards. It is
compiled from `rpm/src` and is not tracked in git, so on a fresh clone:

```
bash rpm/scripts/build_static.sh
```

`tools/start.sh` runs this for you if the binary is missing. Needs the Apple
command line tools (`clang`). If it fails, thrust still works and the RPM
panels say `reader down`. Doc 16 has the rest.

## Firmware

Three sketches, three Nanos: `firmware/thrust_stand`, `firmware/power_meter`,
`firmware/torque_stand`. After a pull that touched a sketch, re-flash that
board from Arduino IDE 1.8.19 (`docs/13-arduino-working-config.md`). The
power meter's 2026-10-26 build changed what `vScale` means; an existing `kv`
calibration is converted on first boot, not lost, but check `d` and the
`vcc (bandgap)` line once.

## First run after updating

```
bash tools/start.sh
```

That is `stop.sh`, the rpm build if needed, `find_ports.py`, then `live.py`
with every board and the dashboard opened in the browser. Doc 18 has the
flags. By hand, if you want to see each step:

```
source ~/venvs/forcerigs/bin/activate
cd tools
python3 live.py --version
python3 live.py --list
python3 live.py --port /dev/cu.usbserial-XXXX
```

The banner reports the version, the file path, the serial port and the HTTP
port it bound. Read it before opening the browser.

## Killing a stale process

```
bash tools/stop.sh
```

kills any `live.py`, `bench.py` or `rpm_reader_static` still running, then
lists who holds 8000, 8765, 8766, 8767 and every `cu.usbserial-*` device.
8000 is your video server; `stop.sh` reports it and leaves it alone.

By hand, if you want to see it happen:

```
pgrep -fl live.py                       # is one running, and what pid
pkill -f live.py                        # kill it
lsof -nP -iTCP:8765 -sTCP:LISTEN        # who is on the web port
lsof /dev/cu.usbserial-*                # who is on the serial port
```

`Errno 48 Address already in use` is always the web port, never the serial
port, and `live.py` steps past it on its own unless you pinned a port with
`--http-port`. With `start.sh`, the browser opens on whichever port it took.
