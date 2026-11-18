#!/usr/bin/env python3
"""
find_ports.py - work out which USB device is which, and remember it.

    python3 find_ports.py            # probe, print, write ports.json
    python3 find_ports.py --show     # print the last result, no probing

Nanos: every /dev/cu.usbserial-* is opened at 115200, which resets the board,
and the boot banner says what it is:
    "Nacelle Thrust Stand"  -> thrust
    "Nacelle Power Meter"   -> power
    "torque stand"          -> torque
The tach board: rpm/list_ftdi prints the FT232H's USB serial number, which
does not change when you move the plug, so live.py is handed the serial. A
board with a blank serial (common on Adafruit's) is handed its USB index
instead, which follows the hub socket. One stand, one tach board; if more
are plugged in the first is used and you are told.

Result goes to tools/ports.json. start.sh reads it.
"""

import argparse
import glob
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "ports.json")
LIST_FTDI = os.path.join(ROOT, "rpm", "list_ftdi")

SIGNATURES = (
    ("thrust", "nacelle thrust stand"),
    ("power", "nacelle power meter"),
    ("torque", "torque stand"),
)


def probe_nano(dev, baud=115200):
    """Open the port, catch the reset banner, ask for help if the banner was missed."""
    try:
        import serial
    except ImportError:
        sys.exit("pyserial missing. Activate the venv: source ~/venvs/forcerigs/bin/activate")
    text = ""
    try:
        with serial.Serial(dev, baud, timeout=0.2) as s:
            deadline = time.time() + 3.0
            while time.time() < deadline:
                text += s.read(4096).decode("ascii", "replace")
            if not any(sig in text.lower() for _, sig in SIGNATURES):
                s.write(b"h\n")
                deadline = time.time() + 1.5
                while time.time() < deadline:
                    text += s.read(4096).decode("ascii", "replace")
    except Exception as exc:
        return None, f"could not open: {exc}"
    low = text.lower()
    for kind, sig in SIGNATURES:
        if sig in low:
            return kind, text.strip().splitlines()[0] if text.strip() else ""
    return None, "no recognised banner (sketch not loaded, or not one of ours)"


def list_ftdi():
    if not os.path.exists(LIST_FTDI):
        return None, "rpm/list_ftdi not built; run: bash rpm/scripts/build_static.sh"
    try:
        out = subprocess.run([LIST_FTDI], capture_output=True, text=True, timeout=10).stdout
    except Exception as exc:
        return None, f"list_ftdi failed: {exc}"
    found = []
    for line in out.splitlines():
        if line.startswith("index="):
            kv = dict(part.split("=", 1) for part in line.split() if "=" in part)
            found.append({"index": int(kv["index"]), "serial": kv.get("serial", ""),
                          "desc": kv.get("desc", "")})
    return found, ""


def load_previous():
    if os.path.exists(OUT):
        with open(OUT) as f:
            return json.load(f)
    return {}


def assign_rpm(found, previous):
    """Return the selector for THE tach board: its USB serial, or its index.

    One test stand, one FT232H. Adafruit boards often ship with a blank serial,
    and then the USB index (0 in plug order) is all there is; it follows the
    hub socket. If more than one board is present the first one is used and
    the rest are listed, so unplug the ones that are not on this stand.
    """
    for d in found:
        d["key"] = d["serial"] or str(d["index"])
    if not found:
        return "", "no tach board present"
    if len(found) == 1:
        return found[0]["key"], "one tach board"
    old = previous.get("rpm") or ""
    keys = [d["key"] for d in found]
    if old in keys:
        return old, f"{len(found)} boards present, kept {old} from last time"
    return keys[0], f"{len(found)} boards present, using the first; unplug the others or edit ports.json"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--show", action="store_true", help="print ports.json and exit")
    args = ap.parse_args()

    previous = load_previous()
    if args.show:
        print(json.dumps(previous, indent=2) if previous else "no ports.json yet")
        return

    result = {"nanos": {}, "rpm": "", "unknown": [], "probed": time.strftime("%Y-%m-%d %H:%M:%S")}

    devs = sorted(glob.glob("/dev/cu.usbserial-*"))
    print("== Nanos")
    if not devs:
        print("   no /dev/cu.usbserial-* present. Cable, hub socket, or hub power.")
    for dev in devs:
        kind, note = probe_nano(dev)
        if kind:
            if kind in result["nanos"]:
                print(f"   {dev:34s} {kind:7s} DUPLICATE, already have {result['nanos'][kind]}")
            else:
                result["nanos"][kind] = dev
                print(f"   {dev:34s} {kind:7s} {note}")
        else:
            result["unknown"].append(dev)
            print(f"   {dev:34s} ?       {note}")

    print("== FT232H tach boards")
    found, note = list_ftdi()
    if found is None:
        print(f"   {note}")
        result["rpm"] = previous.get("rpm", "")
        result["rpm_note"] = note
    else:
        for d in found:
            print(f"   index {d['index']}  serial {d['serial']}  {d['desc']}")
        result["rpm"], how = assign_rpm(found, previous)
        if found and not any(d["serial"] for d in found):
            how += "; serial is blank so this is the USB index and follows the hub socket"
        result["rpm_note"] = how
        print(f"   tach = {result['rpm'] or '-'}   ({how})")

    with open(OUT, "w") as f:
        json.dump(result, f, indent=2)
    print(f"== wrote {OUT}")

    missing = [k for k in ("thrust", "power") if k not in result["nanos"]]
    if missing:
        print(f"   NOTE: not found: {', '.join(missing)}. start.sh will launch without them.")
    if "torque" in result["nanos"]:
        print("   NOTE: torque Nano found. live.py has no --torque-port yet; recorded only.")


if __name__ == "__main__":
    main()
