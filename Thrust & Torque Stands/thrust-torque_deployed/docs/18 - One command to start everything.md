# 18 - One command to start everything: `tools/start.sh`

`start.sh` finds every board on the USB hub, works out which is which, and
launches `live.py` with all of them. Replaces typing the `--port` and
`--power-port` paths by hand, and stops being wrong when a plug moves to
another hub socket.

## Every session

From the project folder:

```
bash tools/start.sh
```

Leave that terminal open; it is `live.py`. `Ctrl-C` stops everything.
The dashboard opens in the browser on its own (http://localhost:8765).

The dashboard comes up with the port and stbd cards side by side. For one
nacelle on the bench there is a **single-nacelle** layout: one thrust card,
one rotor RPM card, one pack power card, each beside its strip chart. The RPM
card shows whichever tach sees a rotor turning and the power card whichever
meter channel has a pack on it; the card title names the channel. Both
FT232Hs and both ACS724 channels can stay plugged in.

```
bash tools/start.sh --single
```

The sibling package `../single` is this same code with that layout as its
default; use it on the bench and keep this one for two-nacelle work.

Once the boards are known:

```
bash tools/start.sh --no-probe
```

skips the probing step (about 3 s per Nano) and launches from the last
`tools/ports.json`. Use this when nothing has been plugged or unplugged.

Anything else on the command line is passed to `live.py` unchanged, so
`bash tools/start.sh --rpm-window 0.1` works. (`live.py --open` is added by
`start.sh` itself, so the browser lands on whatever port `live.py` actually
bound, including when 8765 is busy and it steps to 8766.)

## What it does, in order

1. `stop.sh`: kills any `live.py`, `bench.py` or tach reader still running,
   and anything of ours holding the serial ports or port 8765. It never
   touches port 8000 (video server) or the Arduino IDE.
2. Builds `rpm/rpm_reader_static` and `rpm/list_ftdi` if they are missing
   (first run only, see doc 16).
3. `find_ports.py`: identifies the boards and writes `tools/ports.json`.
4. Launches `live.py --port <thrust> --power-port <power> --rpm-port <p> --rpm-stbd <s>`.

## How the boards are identified

**Nanos.** Every `/dev/cu.usbserial-*` is opened once at 115200. Opening the
port resets the Nano, and the first lines it prints say what it is:

| banner contains        | role    | firmware                    |
|------------------------|---------|-----------------------------|
| `Nacelle Thrust Stand` | thrust  | `firmware/thrust_stand`     |
| `Nacelle Power Meter`  | power   | `firmware/power_meter`      |
| `torque stand`         | torque  | `firmware/torque_stand`     |

So the hub socket does not matter. The `usbserial-NNNN` number encodes the
socket path and changes when a plug moves; the banner does not.

A board shown as `?` has no recognised banner: the sketch is not loaded, or
it is not one of ours. Re-upload from the IDE (doc 13) and run again.

**FT232H tach boards.** `rpm/list_ftdi` lists them. Adafruit boards usually
ship with a blank USB serial number, in which case all the computer can see is
the USB index, 0 and 1, and that follows the hub socket. Which index is the
PORT nacelle is a label on the board, not something software can tell, so the
first time two boards are present `find_ports.py` asks:

```
Two FT232H tach boards found. Which is the PORT nacelle?
   [0] serial (blank)   USB index 0
   [1] serial (blank)   USB index 1
PORT is [0/1]:
```

The old hand-typed launch command never named the tach boards, so `live.py`
used index 0 for port and index 1 for starboard. Answering `0` keeps that.
The answer is saved in `ports.json` and not asked again.

If a board does have a serial number it is used instead of the index, and then
the plug can move freely.

## If the RPM shows up on the wrong side

Swap the assignment without touching the hardware:

```
python3 tools/find_ports.py --reassign-rpm
```

answer the other way, then `bash tools/start.sh --no-probe`.

Do not move the two FT232H plugs to different hub sockets once this is set;
with blank serials the index follows the socket.

## Reading `ports.json`

```
python3 tools/find_ports.py --show
```

Example:

```json
{
  "nanos": {
    "thrust": "/dev/cu.usbserial-1434110",
    "power":  "/dev/cu.usbserial-14341440"
  },
  "rpm": { "port": "0", "stbd": "1" },
  "unknown": [],
  "rpm_note": "assigned by you just now; serials are blank so these are USB indices and follow the hub socket",
  "probed": "2026-10-23 12:40:11"
}
```

`rpm` values are either USB serial numbers or, when blank, index strings.
`live.py` accepts both.

## After it is up

The probe reset the power Nano. Calibration comes back from EEPROM, but the
current zero is per session: on the dashboard, motor off, pack on, press
**Zero amps**. See doc 17.

## Torque stand

`find_ports.py` recognises a torque Nano and records it under `nanos.torque`,
but `live.py` does not take a `--torque-port` yet, so it is not launched.
That is on the list; the script says so when it finds one.

## Files

- `tools/start.sh` launcher
- `tools/find_ports.py` probe and `ports.json` writer
- `tools/ports.json` result of the last probe (generated, safe to delete)
- `tools/stop.sh` kill stale instances; `start.sh` runs it first, and it is
  still fine to run on its own
