#!/usr/bin/env python3
"""
bench.py - laptop-side control and logging for the nacelle thrust stand.

Talks to the Arduino running firmware/thrust_stand/thrust_stand.ino over USB
serial. Gives you a menu: live readout, tare, calibration wizard, and a guided
run capture that walks the collective staircase at a governed RPM and writes rows
straight into the
run log CSV.

Install:
    pip3 install pyserial

Run:
    python3 bench.py                                  auto-detect the port
    python3 bench.py --port COM4                      Windows
    python3 bench.py --port /dev/ttyUSB0              Linux
    python3 bench.py --port /dev/cu.usbserial-1420    macOS
    python3 bench.py --simulate                       no hardware, learn the workflow

Everything except pyserial is standard library.
"""

import argparse
import csv
import math
import os
import queue
import random
import statistics
import sys
import threading
import time
from datetime import datetime

try:
    import serial
    from serial.tools import list_ports
    HAVE_SERIAL = True
except ImportError:
    HAVE_SERIAL = False

LBF_TO_N = 4.4482216
DEFAULT_BAUD = 115200
CSV_FIELDS = ["height_mm", "z_over_R", "head_rpm_cmd", "head_rpm_actual",
              "collective_deg", "servo_us", "throttle_pct",
              "thrust_lbf", "volts", "amps",
              "pack_soc", "notes"]

# The ladders from docs/06-test-protocol.md.
# Height is the OUTER loop, governed RPM the middle, collective the inner.
ROTOR_RADIUS_MM = 457.0          # confirmed 4 Sep 2026, hub centreline to tip
Z_OVER_R_LADDER = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
HEIGHT_LADDER = [round(z * ROTOR_RADIUS_MM) for z in Z_OVER_R_LADDER]

RPM_LADDER = [1600, 1700, 1800, 1900, 2000]

# Collective staircase, in DEGREES AT 0.75R, per governed RPM setpoint.
# Predicted hover pitch falls from ~16 deg at 1600 rpm to ~10 deg at 2000 rpm,
# so each ladder is shifted to bracket 7.5 lbf with points either side.
COLLECTIVE_STEPS = {
    1600: [6, 9, 11, 13, 15, 17],
    1700: [5, 8, 10, 12, 14, 16],
    1800: [4, 7, 9, 11, 13, 15],
    1900: [4, 6, 8, 10, 12, 14],
    2000: [3, 6, 8, 10, 12, 14],
}
DEFAULT_COLLECTIVE_STEPS = [4, 7, 9, 11, 13, 15]
PLATEAU_SECONDS = 5.0


# ------------------------------------------------------------------ transport

class SerialLink:
    """Background reader thread. Lines arrive on self.lines."""

    def __init__(self, port, baud=DEFAULT_BAUD):
        self.ser = serial.Serial(port, baud, timeout=0.2)
        self.lines = queue.Queue()
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._reader, daemon=True)
        self._t.start()

    def _reader(self):
        buf = b""
        while not self._stop.is_set():
            try:
                chunk = self.ser.read(256)
            except Exception:
                break
            if chunk:
                buf += chunk
                while b"\n" in buf:
                    raw, buf = buf.split(b"\n", 1)
                    self.lines.put(raw.decode("utf-8", "replace").strip())

    def send(self, s):
        self.ser.write((s + "\n").encode())
        self.ser.flush()

    def drain(self):
        while not self.lines.empty():
            try:
                self.lines.get_nowait()
            except queue.Empty:
                break

    def close(self):
        self._stop.set()
        time.sleep(0.25)
        try:
            self.ser.close()
        except Exception:
            pass


class SimLink:
    """Fake stand so you can learn the workflow before the parts arrive."""

    def __init__(self):
        self.lines = queue.Queue()
        self.streaming = False
        self.throttle = 0.0
        self.tare = 0.0
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._gen, daemon=True)
        self._t.start()
        self._say("# SIMULATION MODE - no hardware attached")
        self._say("# thrust follows a plausible curve, noise is synthetic")
        self._say("# use the 'throttle' menu item to move the fake motor")

    def _say(self, s):
        self.lines.put(s)

    def _gen(self):
        n = 0
        while not self._stop.is_set():
            if self.streaming:
                t = 14.0 * (self.throttle / 100.0) ** 2
                t += random.gauss(0, 0.03 + 0.02 * self.throttle / 100.0)
                t -= self.tare
                self.lines.put(f"{n},{int(time.time()*1000)%10**7},"
                               f"{t:.4f},{t*LBF_TO_N:.3f},{int(t*12000)}")
                n += 1
            time.sleep(0.1)

    def send(self, s):
        s = s.strip()
        if s.startswith("s"):
            self.streaming = not self.streaming
            self._say("# streaming ON" if self.streaming else "# streaming OFF")
            if self.streaming:
                self._say("# n,ms,lbf,N,raw")
        elif s.startswith("t"):
            self.tare = 14.0 * (self.throttle / 100.0) ** 2
            self._say("# tare offset = 123456")
            self._say("# zeroed. readings are now change from tare.")
        elif s.startswith("c"):
            self._say("# calFactor = 21500.0000 counts/lbf, saved to EEPROM")
        elif s.startswith("d"):
            self._say("  calFactor (counts/lbf) : 21500.0000")
            self._say("  HX711 ready            : yes")
        elif s.startswith("r"):
            t = 14.0 * (self.throttle / 100.0) ** 2 - self.tare
            self._say("# n,ms,lbf,N,raw")
            self._say(f"0,0,{t:.4f},{t*LBF_TO_N:.3f},0")
        else:
            self._say("# (sim) ok")

    def drain(self):
        while not self.lines.empty():
            try:
                self.lines.get_nowait()
            except queue.Empty:
                break

    def close(self):
        self._stop.set()


# ------------------------------------------------------------------ helpers

def find_port():
    if not HAVE_SERIAL:
        return None
    cands = list(list_ports.comports())
    if not cands:
        return None
    # CH340 clones, FTDI, and genuine Arduinos, in rough order of likelihood
    keys = ("ch340", "ch910", "usb-serial", "wchusb", "ftdi", "ft232",
            "arduino", "usbmodem", "usbserial", "cp210")
    for p in cands:
        blob = f"{p.device} {p.description} {p.manufacturer}".lower()
        if any(k in blob for k in keys):
            return p.device
    return cands[0].device


def list_all_ports():
    if not HAVE_SERIAL:
        print("  pyserial not installed")
        return
    ports = list(list_ports.comports())
    if not ports:
        print("  no serial ports found")
        return
    for p in ports:
        print(f"  {p.device:24s} {p.description}")


def parse_sample(line):
    """Return thrust in lbf from a data line, or None."""
    if not line or line.startswith("#") or line.startswith("!"):
        return None
    parts = line.split(",")
    if len(parts) < 3:
        return None
    try:
        return float(parts[2])
    except ValueError:
        return None


def collect(link, seconds, show=True):
    """Stream for `seconds` and return the list of thrust samples."""
    link.drain()
    link.send("s")
    samples = []
    t0 = time.time()
    last_print = 0.0
    while time.time() - t0 < seconds:
        try:
            line = link.lines.get(timeout=0.3)
        except queue.Empty:
            continue
        v = parse_sample(line)
        if v is not None:
            samples.append(v)
            if show and time.time() - last_print > 0.25:
                last_print = time.time()
                el = time.time() - t0
                sys.stdout.write(f"\r  {el:4.1f}s  {v:8.3f} lbf   "
                                 f"({len(samples)} samples)   ")
                sys.stdout.flush()
    link.send("s")
    time.sleep(0.2)
    link.drain()
    if show:
        sys.stdout.write("\r" + " " * 60 + "\r")
    return samples


def summarise(samples):
    if not samples:
        return None
    mean = statistics.fmean(samples)
    sd = statistics.pstdev(samples) if len(samples) > 1 else 0.0
    return {"mean": mean, "sd": sd, "n": len(samples),
            "min": min(samples), "max": max(samples)}


def ask(prompt, default=None, cast=str, allow_blank=False):
    suffix = f" [{default}]" if default is not None else ""
    while True:
        s = input(f"{prompt}{suffix}: ").strip()
        if not s:
            if default is not None:
                return default
            if allow_blank:
                return ""
            continue
        try:
            return cast(s)
        except ValueError:
            print("  not a valid value, try again")


# ------------------------------------------------------------------ actions

def action_live(link):
    print("\n  Live readout. Ctrl-C to stop.\n")
    link.drain()
    link.send("s")
    try:
        while True:
            try:
                line = link.lines.get(timeout=0.5)
            except queue.Empty:
                continue
            v = parse_sample(line)
            if v is not None:
                bar = "#" * max(0, min(50, int(abs(v) * 4)))
                sign = "-" if v < 0 else " "
                sys.stdout.write(f"\r {sign}{abs(v):7.3f} lbf "
                                 f"{v*LBF_TO_N:8.2f} N  |{bar:<50}|")
                sys.stdout.flush()
    except KeyboardInterrupt:
        pass
    finally:
        link.send("s")
        time.sleep(0.2)
        link.drain()
        print("\n")


def action_tare(link):
    print("\n  Motor OFF. Rig settled. Nothing touching it.")
    input("  Press Enter to tare...")
    link.drain()
    link.send("t")
    time.sleep(1.5)
    while not link.lines.empty():
        print("   ", link.lines.get())
    s = summarise(collect(link, 2.0, show=False))
    if s:
        print(f"    check: {s['mean']:+.4f} lbf mean, {s['sd']:.4f} sd over {s['n']} samples")
        if abs(s["mean"]) > 0.05:
            print("    ! zero is off. something is touching the rig or drifting.")
    print()


def action_calibrate(link):
    print("\n  CALIBRATION")
    print("  Prop removed. Stand fully assembled in test orientation.")
    print("  Electronics powered for at least two minutes.\n")
    if input("  Ready? (y/n): ").strip().lower() != "y":
        return

    print("\n  Step 1: tare with nothing applied.")
    input("  Press Enter...")
    link.drain()
    link.send("t")
    time.sleep(1.5)
    link.drain()

    w = ask("\n  Step 2: apply a KNOWN weight along the post axis.\n"
            "  Enter its weight in lbf", cast=float)
    input("  Weight applied and settled? Press Enter...")
    link.drain()
    link.send(f"c {w}")
    time.sleep(2.5)
    while not link.lines.empty():
        print("   ", link.lines.get())

    print("\n  Step 3: remove the weight.")
    input("  Press Enter when removed...")
    s = summarise(collect(link, 3.0, show=False))
    if s:
        print(f"    return to zero: {s['mean']:+.4f} lbf")
        if abs(s["mean"]) > 0.08:
            print("    ! did not return to zero. check for slipping or creep.")

    print("\n  Step 4: linearity check. Apply each weight and record.")
    print("  (docs/05-calibration.md has the table to fill in)\n")
    while True:
        a = input("  Applied weight in lbf, or blank to finish: ").strip()
        if not a:
            break
        try:
            applied = float(a)
        except ValueError:
            continue
        s = summarise(collect(link, 3.0, show=False))
        if s:
            err = s["mean"] - applied
            flag = "  <-- CHECK" if abs(err) > 0.25 else ""
            print(f"    applied {applied:6.2f}  measured {s['mean']:7.3f}  "
                  f"error {err:+.3f} lbf{flag}")
    print()


def action_run(link, csv_path, raw_dir):
    print("\n  GUIDED RUN CAPTURE\n")
    print("  This head is GOVERNED and VARIABLE PITCH.")
    print("  Throttle is an RPM setpoint. Thrust comes from COLLECTIVE.\n")
    print("  Height ladder (z/R x %.0f mm): " % ROTOR_RADIUS_MM,
          ", ".join(f"{h}" for h in HEIGHT_LADDER), "mm")
    height = ask("  Rotor height, MEASURED with a tape, in mm", cast=float)
    zr = height / ROTOR_RADIUS_MM
    print(f"    z/R = {zr:.2f}")

    print("\n  RPM ladder:", ", ".join(str(r) for r in RPM_LADDER))
    rpm_cmd = ask("  Governed RPM setpoint for this run", cast=float)
    steps = COLLECTIVE_STEPS.get(int(rpm_cmd), DEFAULT_COLLECTIVE_STEPS)

    throttle = ask("  Throttle command giving that setpoint (doc 05a)",
                   cast=str, allow_blank=True)
    soc = ask("  Pack state of charge note", default="full", cast=str)

    print("\n  Motor OFF, rig settled. Taring before the run.")
    input("  Press Enter...")
    link.drain()
    link.send("t")
    time.sleep(1.5)
    link.drain()

    print("\n  Watching the zero for 30 s. It must not WALK.")
    print("  Scatter is fine; a trend is not.")
    z = collect(link, 30.0, show=False)
    zs = summarise(z)
    if zs and len(z) >= 6:
        n = len(z) // 3
        first = sum(z[:n]) / n
        last = sum(z[-n:]) / n
        walk = last - first
        print(f"    zero mean {zs['mean']:+.3f} lbf   sd {zs['sd']:.3f}"
              f"   drift over 30 s {walk:+.3f} lbf")
        problems = []
        if abs(zs["mean"]) > 0.10:
            problems.append("offset from zero")
        if abs(walk) > 0.10:
            problems.append("steady drift")
        if zs["sd"] > 0.25:
            problems.append("very noisy")
        if problems:
            print("    ! " + ", ".join(problems).upper() +
                  ". STOP and find out why before running.")
            print("    ! drift is usually thermal or a creeping joint;")
            print("    ! noise is usually cable routing. See docs 03 and 04.")
            if ask("    continue anyway? (y/n)", default="n", cast=str).lower() != "y":
                return

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    raw_path = os.path.join(raw_dir, f"raw-{int(height)}mm-{int(rpm_cmd)}rpm-{stamp}.csv")
    os.makedirs(raw_dir, exist_ok=True)
    raw_f = open(raw_path, "w", newline="")
    raw_w = csv.writer(raw_f)
    raw_w.writerow(["collective_deg", "sample_idx", "thrust_lbf"])

    rows = []

    def capture(coll_label, coll_value):
        """Capture one plateau. Returns a row dict or None."""
        samples = collect(link, PLATEAU_SECONDS)
        st = summarise(samples)
        if not st:
            print("    ! no samples. is the Arduino connected?")
            return None
        for i, v in enumerate(samples):
            raw_w.writerow([coll_label, i, f"{v:.4f}"])
        spread = st["max"] - st["min"]
        print(f"    thrust {st['mean']:7.3f} lbf  sd {st['sd']:.3f}  "
              f"spread {spread:.3f}  n={st['n']}")
        if st["sd"] > 0.25:
            print("    ! noisy plateau. vibration, governor hunting, or not settled.")

        rpm_act = ask("    ACTUAL rpm (tach or telemetry)", cast=str, allow_blank=True)
        if rpm_act:
            try:
                err = 100.0 * (float(rpm_act) - rpm_cmd) / rpm_cmd
                if abs(err) > 2.0:
                    print(f"    ! governor off setpoint by {err:+.1f}%. "
                          "This row is not the RPM its label claims.")
            except ValueError:
                pass
        servo = ask("    servo us (blank if not logged)", cast=str, allow_blank=True)
        volts = ask("    volts UNDER LOAD", cast=float)
        amps = ask("    amps (watt meter, not ESC)", cast=float)
        note = ask("    notes (blank for none)", cast=str, allow_blank=True)
        print(f"    => {volts*amps:.0f} W\n")

        return {
            "height_mm": f"{height:.0f}",
            "z_over_R": f"{zr:.3f}",
            "head_rpm_cmd": f"{rpm_cmd:.0f}",
            "head_rpm_actual": rpm_act,
            "collective_deg": "" if coll_value is None else f"{coll_value}",
            "servo_us": servo,
            "throttle_pct": throttle,
            "thrust_lbf": f"{st['mean']:.4f}",
            "volts": f"{volts:.2f}",
            "amps": f"{amps:.2f}",
            "pack_soc": soc,
            "notes": note,
        }

    print(f"\n  Spool up to {rpm_cmd:.0f} rpm at MINIMUM COLLECTIVE.")
    print("  Let the governor settle before capturing.\n")
    if ask("  Capture the flat-pitch reference point? (y/n)",
           default="y", cast=str).lower() == "y":
        input("  --> at min collective, governor settled, Enter to capture: ")
        r = capture("flat", None)
        if r:
            r["notes"] = (r["notes"] + " flat pitch reference").strip()
            rows.append(r)

    print(f"\n  Collective staircase at {rpm_cmd:.0f} rpm: {steps} deg at 0.75R")
    print(f"  {PLATEAU_SECONDS:.0f}s per step. Set pitch, let it settle, press Enter.")
    print("  Type 's' to skip a step, 'q' to stop the run early.\n")

    order = list(steps) + list(reversed(steps))
    for idx, coll in enumerate(order):
        leg = "up" if idx < len(steps) else "down"
        cmd = input(f"  --> collective to {coll} deg ({leg}), settle, "
                    "Enter to capture: ").strip().lower()
        if cmd == "q":
            break
        if cmd == "s":
            continue
        r = capture(coll, coll)
        if r:
            r["notes"] = (r["notes"] + f" {leg}-leg").strip()
            rows.append(r)

    print("\n  Return to MINIMUM COLLECTIVE and spool down.")
    input("  Press Enter when the rotor has stopped...")

    raw_f.close()

    print("  Motor OFF, rig settled. Taring again to verify.")
    input("  Press Enter...")
    link.drain()
    link.send("t")
    time.sleep(1.5)
    link.drain()
    st = summarise(collect(link, 3.0, show=False))
    if st:
        print(f"    post-run zero: {st['mean']:+.4f} lbf")
        if abs(st["mean"]) > 0.08:
            print("    ! TARE WANDERED. Something shifted during the run.")
            print("    ! Per docs/06, discard this run and find what moved.")
            if input("    Save anyway? (y/n): ").strip().lower() != "y":
                print("    discarded.\n")
                return

    write_rows(csv_path, rows)
    print(f"\n  {len(rows)} rows appended to {csv_path}")
    print(f"  raw samples in {raw_path}\n")


def write_rows(path, rows):
    if not rows:
        return
    exists = os.path.exists(path) and os.path.getsize(path) > 0
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        if not exists:
            fh.write("# Nacelle thrust stand run log, written by bench.py\n")
            w.writeheader()
        for r in rows:
            w.writerow(r)


def action_console(link):
    print("\n  Raw console. Type sketch commands directly. 'h' for its help.")
    print("  Blank line to return to the menu.\n")
    while True:
        s = input("  > ")
        if not s.strip():
            break
        link.send(s)
        time.sleep(0.6)
        while not link.lines.empty():
            print("   ", link.lines.get())
    print()


# ------------------------------------------------------------------ main

MENU = """
  ================ NACELLE THRUST STAND ================
   1  Live readout
   2  Tare
   3  Calibration wizard
   4  Capture a run (guided staircase)
   5  Raw console
   6  List serial ports
   q  Quit
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", help="serial port, e.g. COM4 or /dev/ttyUSB0")
    ap.add_argument("--baud", type=int, default=DEFAULT_BAUD)
    ap.add_argument("--out", default="../data/runs.csv", help="run log CSV to append to")
    ap.add_argument("--raw-dir", default="../data/raw", help="where per-plateau raw samples go")
    ap.add_argument("--simulate", action="store_true", help="no hardware, fake stand")
    ap.add_argument("--list-ports", action="store_true")
    args = ap.parse_args()

    if args.list_ports:
        list_all_ports()
        return 0

    if args.simulate:
        link = SimLink()
        print("\n  *** SIMULATION MODE, no hardware ***")
    else:
        if not HAVE_SERIAL:
            print("pyserial is not installed. Run:  pip3 install pyserial")
            print("Or try:  python3 bench.py --simulate")
            return 1
        port = args.port or find_port()
        if not port:
            print("No serial port found. Ports available:")
            list_all_ports()
            print("\nPlug the board in, or pass --port explicitly.")
            return 1
        print(f"\n  Opening {port} at {args.baud}...")
        try:
            link = SerialLink(port, args.baud)
        except Exception as exc:
            print(f"  Could not open {port}: {exc}")
            print("  On Linux you may need:  sudo usermod -a -G dialout $USER")
            return 1
        time.sleep(2.2)   # board resets on connect
        while not link.lines.empty():
            print("   ", link.lines.get())

    try:
        while True:
            print(MENU)
            c = input("  choice: ").strip().lower()
            if c == "1":
                action_live(link)
            elif c == "2":
                action_tare(link)
            elif c == "3":
                action_calibrate(link)
            elif c == "4":
                action_run(link, args.out, args.raw_dir)
            elif c == "5":
                action_console(link)
            elif c == "6":
                list_all_ports()
            elif c == "throttle" and isinstance(link, SimLink):
                link.throttle = ask("  fake throttle percent", cast=float)
            elif c in ("q", "quit", "exit"):
                break
    except KeyboardInterrupt:
        pass
    finally:
        link.close()
        print("\n  closed.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
