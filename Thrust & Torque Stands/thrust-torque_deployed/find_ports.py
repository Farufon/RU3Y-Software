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
FT232H tach boards: rpm/list_ftdi prints their USB serial numbers. The serial
never changes when you move the plug, so live.py is handed serials, not indices.
Which FT232H is PORT and which is STBD is a label on the board, not something
the computer can see, so the first time two are found you are asked once and the
answer is kept in ports.json. Re-run with --reassign-rpm to ask again.

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


def assign_rpm(found, previous, reassign):
    """Return {'port': serial, 'stbd': serial}. Keep an old assignment if the boards match."""
    serials = [d["serial"] for d in found if d["serial"]]
    old = (previous.get("rpm") or {})
    if (not reassign and old.get("port") in serials and old.get("stbd") in serials
            and old["port"] != old["stbd"]):
        return {"port": old["port"], "stbd": old["stbd"]}, "kept from last time"
    if len(serials) == 1:
        return {"port": serials[0], "stbd": ""}, "only one tach board present, assigned to PORT"
    if len(serials) == 0:
        return {"port": "", "stbd": ""}, "no tach boards present"
    # two or more and no usable history: ask once
    print("\nTwo FT232H tach boards found. Which is the PORT nacelle?")
    for i, d in enumerate(found):
        print(f"   [{i}] serial {d['serial']}   (USB index {d['index']})")
    print("Tip: unplug one, re-run, and the one that remains is the one you can see.")
    while True:
        ans = input("PORT is [0/1]: ").strip()
        if ans in ("0", "1") and int(ans) < len(found):
            p = found[int(ans)]["serial"]
            s = next(d["serial"] for d in found if d["serial"] != p)
            return {"port": p, "stbd": s}, "assigned by you just now"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--show", action="store_true", help="print ports.json and exit")
    ap.add_argument("--reassign-rpm", action="store_true",
                    help="ask again which FT232H is port and which is stbd")
    args = ap.parse_args()

    previous = load_previous()
    if args.show:
        print(json.dumps(previous, indent=2) if previous else "no ports.json yet")
        return

    result = {"nanos": {}, "rpm": {}, "unknown": [], "probed": time.strftime("%Y-%m-%d %H:%M:%S")}

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
        result["rpm"] = previous.get("rpm", {})
        result["rpm_note"] = note
    else:
        for d in found:
            print(f"   index {d['index']}  serial {d['serial']}  {d['desc']}")
        result["rpm"], how = assign_rpm(found, previous, args.reassign_rpm)
        result["rpm_note"] = how
        print(f"   PORT = {result['rpm'].get('port') or '-'}   STBD = {result['rpm'].get('stbd') or '-'}   ({how})")

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
