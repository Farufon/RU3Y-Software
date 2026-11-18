# 18 - One command to start everything: `tools/start.sh`

`start.sh` finds every board on the USB hub, works out which is which, and
launches `live.py` with all of them. Replaces typing the `--port` and
`--power-port` paths by hand, and stops being wrong when a plug moves to
another hub socket.

## Every session

From the `single` folder:

```
bash tools/start.sh
```

Leave that terminal open; it is `live.py`. `Ctrl-C` stops everything.
The dashboard opens in the browser on its own, and the link is printed twice:
once by `start.sh` before launching, once by `live.py` after it has bound its
port. The second one is the one to trust if 8765 was busy.

```
DASHBOARD   http://localhost:8765
            http://192.168.x.x:8765   (iPad or any device on the LAN / VPN)
```

Once the boards are known:

```
bash tools/start.sh --no-probe
```

skips the probing step (about 3 s per Nano) and launches from the last
`tools/ports.json`. Use this when nothing has been plugged or unplugged.

Anything else on the command line is passed to `live.py` unchanged, so
`bash tools/start.sh --rpm-window 0.1` works.

## What it does, in order

1. `stop.sh`: kills any `live.py`, `bench.py` or tach reader still running,
   and anything of ours holding the serial ports or port 8765. It never
   touches port 8000 (video server) or the Arduino IDE.
2. Builds `rpm/rpm_reader_static` and `rpm/list_ftdi` if they are missing
   (first run only, see doc 16).
3. `find_ports.py`: identifies the boards and writes `tools/ports.json`.
4. Launches `live.py --open --port <thrust> --power-port <power> --tach <tach>`.

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

**The tach board.** `rpm/list_ftdi` lists FT232H boards. If the board has a
USB serial number it is used, and then the plug can move freely. Adafruit
boards usually ship with a blank serial, in which case all the computer can
see is the USB index, `0` for the only board, and that follows the hub
socket. Do not move the FT232H plug to a different hub socket once the probe
has run, or run the probe again after you do.

One stand, one tach. If more than one FT232H is plugged in, the first is used
and `find_ports.py` says so; unplug the others.

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
  "rpm": "0",
  "unknown": [],
  "rpm_note": "one tach board; serial is blank so this is the USB index and follows the hub socket",
  "probed": "2026-10-28 09:12:40"
}
```

`rpm` is either the USB serial number or, when blank, the index as a string.
`live.py --tach` accepts both. A `ports.json` left over from the two-nacelle
package (with `"rpm": {"port": ..., "stbd": ...}`) is read too; its port
entry is used.

## After it is up

The probe reset the power Nano. Calibration comes back from EEPROM, but the
current zero is per session: on the dashboard, motor off, pack on, press
**Zero amps**. See doc 17.

The load cell has its own guided calibration on the dashboard (the
"Calibrate the load cell" card): tare with only the nacelle on, stack the
known weight, enter its weight, press Calibrate, then lift the mount and
confirm the number goes positive. Doc 05 has the reasoning; the card does
the sequence, including the sign flip this rig needs.

## Torque stand

`find_ports.py` recognises a torque Nano and records it under `nanos.torque`,
but `live.py` does not take a `--torque-port` yet, so it is not launched.
That is on the list; the script says so when it finds one.
