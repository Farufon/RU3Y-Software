#!/usr/bin/env python3
"""
live.py - live thrust readout, logger and BEMT overlay for the nacelle thrust stand.

SINGLE-NACELLE PACKAGE. One stand, one nacelle, one tach, one pack. This copy
lives in "Thrust & Torque Stands/single". The two-nacelle package with port
and starboard channels is ../thrust-torque_deployed; the two are kept in step
by hand, and a fix in one is a fix in the other.

Runs a small web server on this machine. Open the page in any browser on the
Mac, or on an iPad / phone over the VPN, and you get a live readout, a rolling
strip chart, a guided load-cell calibration, and a power chart with the BEMT
model, the flight-test anchor (hover 1800 rpm at 446 W per nacelle) and your
measured grid points laid over it.

    pip3 install pyserial
    python3 live.py --port /dev/cu.usbserial-1480
    python3 live.py --list          # show serial ports and exit

Then open  http://localhost:8765   (live.py prints the exact link once it has
bound a port; if 8765 is busy it steps to the next free one. --http-port pins it.)

To reach it from an iPad over the VPN, use the Mac's address instead of
localhost. The server binds all interfaces by default.

Log files are written to tools/logs/ (override with --logdir):

    stream-YYYYmmdd-HHMMSS.csv   every thrust sample, wall-clock stamped, with
                                 the latest rpm, volts and amps beside it
    rpm-YYYYmmdd-HHMMSS.csv      every tach row
    power-YYYYmmdd-HHMMSS.csv    every power-meter row
    run-log.csv                  one row per captured grid point; reduce.py eats it

RPM comes from the FT232H tach board (rpm/ in this package). live.py spawns
rpm_reader_static for it and shows rotor RPM beside the thrust number with its
own strip chart. Capture fills head_rpm_actual from the tach unless you type
something in. Build the reader once with  bash rpm/scripts/build_static.sh ;
if the binary is missing, the RPM panel says so and everything else still
works. --no-rpm turns it off.

    python3 live.py --port /dev/cu.usbserial-1480 --tach 0          # by USB index
    python3 live.py --port /dev/cu.usbserial-1480 --tach FT6JABCD   # by USB serial

Pack power comes from the hall-sensor Nano (firmware/power_meter). Give it
its own serial port with --power-port and the page gets volts, amps and
watts next to thrust, a power strip chart, and capture fills volts and amps
from it unless you type them.

    python3 live.py --port /dev/cu.usbserial-1480 --power-port /dev/cu.usbserial-1490

Nothing here talks to the ESC or the motor. It reads the load cell, the tach
and the power meter and it writes files. Without --power-port, volts and amps
are typed in by hand from the LCD watt meter.

tools/start.sh fills in every port for you and opens the browser.
"""

import argparse
import csv
import json
import os
import queue
import re
import shutil
import socket
import statistics
import subprocess
import sys
import threading
import time
import webbrowser
from collections import deque
from datetime import datetime
import errno
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    sys.exit("pyserial not installed.  pip3 install pyserial")

VERSION = "2026-10-28.1-single"
HERE = os.path.dirname(os.path.abspath(__file__))

RUN_LOG_FIELDS = [
    "height_mm", "z_over_R", "head_rpm_cmd", "head_rpm_actual",
    "collective_deg", "servo_us", "throttle_pct", "thrust_lbf",
    "volts", "amps", "pack_soc", "notes",
    "rpm_tach",      # tach average over the capture window, even when head_rpm_actual was typed
    "watts",         # mean of instantaneous V*I from the meter (ripple-correct);
                     # volts*amps when typed. reduce.py prefers this column.
]

SETTINGS_PATH = os.path.join(HERE, "live-settings.json")


class RpmConfig:
    """Gear ratio, motor:rotor, editable from the page. Persisted in
    live-settings.json so it survives a restart. --rpm-ratio on the command
    line overrides the stored value and stores it."""

    def __init__(self, cli_ratio=None, default=3.0):
        self.ratio = default
        try:
            with open(SETTINGS_PATH) as f:
                self.ratio = float(json.load(f).get("rpm_ratio", default))
        except Exception:
            pass
        if cli_ratio is not None:
            self.ratio = float(cli_ratio)
            self.save()

    def set(self, ratio):
        ratio = float(ratio)
        if not (0.1 <= ratio <= 100):
            raise ValueError("ratio out of range")
        self.ratio = ratio
        self.save()

    def save(self):
        try:
            data = {}
            if os.path.exists(SETTINGS_PATH):
                with open(SETTINGS_PATH) as f:
                    data = json.load(f)
            data["rpm_ratio"] = self.ratio
            with open(SETTINGS_PATH, "w") as f:
                json.dump(data, f, indent=1)
        except Exception as exc:
            print(f"warning   could not save {SETTINGS_PATH}: {exc}")


# ------------------------------------------------------------------ rpm

class RpmChannel:
    """The FT232H tach board, read through rpm_reader_static as a subprocess.

    The C reader does the edge counting against the FTDI D2XX driver, which
    Python cannot share with pyftdi anyway. We only parse its CSV. If the
    process dies (board unplugged, driver hiccup) it is restarted every few
    seconds and the panel goes amber, then red, in the meantime.
    """

    LINE = re.compile(r"^\s*(-?[\d.]+),(\d+),(-?[\d.]+),(-?[\d.]+),(-?[\d.]+)\s*$")

    def __init__(self, selector, binary, poles, cfg, window_s, logpath):
        self.selector = str(selector)
        self.binary = binary
        self.poles = poles
        self.cfg = cfg                 # RpmConfig; ratio is read live on every row
        self.window_s = window_s
        self.logpath = logpath

        self.proc = None
        self.running = False
        self.error = ""
        self.noise = ""                # last line we could not parse; the reader's
                                       # stderr is merged into stdout so this is
                                       # usually its complaint when it dies
        self.header = ""
        self.lock = threading.Lock()
        self.samples = deque(maxlen=6000)      # (wall_epoch, edges, motor_rpm, rotor_rpm)

        if binary:
            threading.Thread(target=self._loop, daemon=True).start()
        else:
            self.error = "reader binary not found; bash rpm/scripts/build_static.sh"

    def argv(self):
        sel = ["--serial", self.selector] if not self.selector.isdigit() else ["--index", self.selector]
        return [self.binary, *sel, "--poles", str(self.poles),
                "--ratio", "1", "--window", f"{self.window_s:g}"]   # rotor computed here

    def _loop(self):
        while True:
            try:
                # stderr merged into stdout: reading stdout to EOF and stderr
                # afterwards would deadlock if the reader ever filled the
                # stderr pipe, and the merged lines fall through _line() to
                # self.noise anyway
                self.proc = subprocess.Popen(
                    self.argv(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1)
            except Exception as exc:
                self.error = str(exc)
                self.running = False
                time.sleep(3.0)
                continue
            self.running = True
            self.error = ""
            self.noise = ""
            for line in self.proc.stdout:
                self._line(line.rstrip("\r\n"))
            self.proc.wait()
            self.running = False
            self.error = self.noise or f"reader exited {self.proc.returncode}"
            time.sleep(3.0)

    def _line(self, line):
        if not line:
            return
        if line.startswith("#"):
            if "rpm_reader" in line:
                self.header = line.lstrip("# ")
            return
        m = self.LINE.match(line)
        if not m:
            self.noise = line.strip()
            return
        now = time.time()
        _t, edges, _eps, motor, _rotor_from_binary = m.groups()
        rotor = float(motor) / self.cfg.ratio
        rec = (now, int(edges), float(motor), rotor)
        with self.lock:
            self.samples.append(rec)
        with open(self.logpath, "a", newline="") as f:
            csv.writer(f).writerow([
                datetime.fromtimestamp(now).isoformat(timespec="milliseconds"),
                f"{now:.3f}", edges, motor, f"{rotor:.1f}", f"{self.cfg.ratio:g}"])

    def last(self):
        with self.lock:
            return self.samples[-1] if self.samples else None

    def window(self, seconds):
        cut = time.time() - seconds
        with self.lock:
            return [s for s in self.samples if s[0] >= cut]

    def average(self, seconds):
        win = self.window(seconds)
        if not win:
            return None
        rot = [s[3] for s in win]
        return {"n": len(win), "mean_rotor": statistics.fmean(rot),
                "sd_rotor": statistics.pstdev(rot) if len(rot) > 1 else 0.0,
                "min_rotor": min(rot), "max_rotor": max(rot),
                "mean_motor": statistics.fmean(s[2] for s in win)}

    def state(self):
        last = self.last()
        age = (time.time() - last[0]) if last else None
        return {
            "selector": self.selector,
            "ratio": self.cfg.ratio,
            "poles": self.poles,
            "running": self.running,
            "error": self.error,
            "header": self.header,
            "last": {"rotor": last[3], "motor": last[2], "edges": last[1],
                     "age_s": round(age, 2)} if last else None,
            "series": [[round(t - time.time(), 2), round(r, 0)]
                       for (t, _e, _m, r) in self.window(90)[-1800:]],
            "avg5": self.average(5),
        }

    def stop(self):
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
            except Exception:
                pass


# ------------------------------------------------------------------ power

class PowerChannel:
    """The power-meter Nano (firmware/power_meter) on its own serial port.

    Same reconnect-forever pattern as Stand. Rows are
    n,ms,volts,amps,watts,rawI,rawV at 20 Hz once 's' has been sent; this
    class sends 's' itself on connect so the stream is always on.

    A Nano still carrying the two-channel sketch from the two-nacelle package
    prints n,ms,vP,aP,wP,vS,aS,wS,rawIP,rawVP,rawIS,rawVS. Those rows are
    accepted and the first channel (A0/A1) is used, so the bench works before
    the board is re-flashed; the banner says so.

    Samples are stored as (wall, ms, volts, amps, watts, rawI, rawV).
    """

    NUM = r"(-?[\d.]+)"
    LINE1 = re.compile(r"^\s*(\d+),(\d+)," + ",".join([NUM] * 5) + r"\s*$")
    LINE2 = re.compile(r"^\s*(\d+),(\d+)," + ",".join([NUM] * 10) + r"\s*$")

    def __init__(self, port, baud, logpath):
        self.port_name = port
        self.baud = baud
        self.logpath = logpath
        self.ser = None
        self.connected = False
        self.error = ""
        self.streaming = False
        self.two_channel = False       # the old two-channel sketch is on the board
        self.lock = threading.Lock()
        self.samples = deque(maxlen=6000)
        self.banner = deque(maxlen=60)
        self.settings = {"calibrated": None, "iZero": None, "iGain": None, "vScale": None, "vcc": None}
        self._skip = False             # inside the second channel's block of a two-channel dump
        self.outq = queue.Queue()
        self.opened_at = 0.0
        threading.Thread(target=self._reader, daemon=True).start()
        threading.Thread(target=self._writer, daemon=True).start()

    def send(self, cmd):
        self.outq.put(cmd.strip() + "\n")

    def _open(self):
        try:
            self.ser = serial.Serial(self.port_name, self.baud, timeout=0.4)
            time.sleep(2.2)
            self.ser.reset_input_buffer()
            self.connected = True
            self.error = ""
            self.opened_at = time.time()
            self.streaming = False
            self.send("d")
            self.send("s")
        except Exception as exc:
            self.connected = False
            self.error = str(exc)

    def _writer(self):
        while True:
            cmd = self.outq.get()
            if not self.connected:
                continue
            try:
                self.ser.write(cmd.encode())
                if cmd.strip() == "s":
                    self.streaming = not self.streaming
            except Exception as exc:
                self.error = str(exc)

    def _reader(self):
        buf = b""
        while True:
            if not self.connected:
                self._open()
                if not self.connected:
                    time.sleep(2.0)
                    continue
            try:
                chunk = self.ser.read(256)
            except Exception as exc:
                self.error = str(exc)
                self.connected = False
                try:
                    self.ser.close()
                except Exception:
                    pass
                continue
            if not chunk:
                # the 's' can be lost in the reset window; nudge once
                if self.connected and not self.samples and time.time() - self.opened_at > 4.0:
                    self.opened_at = time.time()
                    self.send("d")
                    self.send("s")
                continue
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                self._line(line.decode("utf-8", "replace").strip("\r\n"))

    def _record(self, now, ms, v, a, w, ri, rv):
        self.streaming = True
        with self.lock:
            self.samples.append((now, ms, v, a, w, ri, rv))
        with open(self.logpath, "a", newline="") as f:
            csv.writer(f).writerow([
                datetime.fromtimestamp(now).isoformat(timespec="milliseconds"),
                f"{now:.3f}", ms, v, a, w, ri, rv])

    def _line(self, line):
        if not line:
            return
        m = self.LINE1.match(line)
        if m:
            g = m.groups()
            v, a, w, ri, rv = (float(x) for x in g[2:])
            self._record(time.time(), int(g[1]), v, a, w, ri, rv)
            return
        m = self.LINE2.match(line)
        if m:
            g = m.groups()
            vP, aP, wP, _vS, _aS, _wS, riP, rvP, _riS, _rvS = (float(x) for x in g[2:])
            if not self.two_channel:
                self.two_channel = True
                with self.lock:
                    self.banner.append("# two-channel sketch on this Nano; using its first channel (A0/A1). "
                                       "Flash firmware/power_meter from this package when convenient.")
            self._record(time.time(), int(g[1]), vP, aP, wP, riP, rvP)
            return
        with self.lock:
            self.banner.append(line)
        ls = line.strip()
        if ls in ("[p]", "[s]"):
            self._skip = ls == "[s]"           # two-channel dump: ignore the second block
            return
        if self._skip and not ls.startswith("#"):
            return
        if "iZero" in line or "iGain" in line or "vScale" in line:
            key = "iZero" if "iZero" in line else ("iGain" if "iGain" in line else "vScale")
            mm = re.search(r"(?:iZero|iGain|vScale)\s+([ps])\b", line)
            if mm and mm.group(1) == "s":
                return                          # the two-channel sketch's second channel
            self.settings[key] = _num(line)
        elif "vcc (bandgap)" in line:
            self.settings["vcc"] = _num(line)
        elif "calibrated" in line:
            self.settings["calibrated"] = "NO" not in line and "NOT" not in line
            self._skip = False
        elif "stream stopped" in line:
            self.streaming = False

    def last(self):
        with self.lock:
            return self.samples[-1] if self.samples else None

    def window(self, seconds):
        cut = time.time() - seconds
        with self.lock:
            return [s for s in self.samples if s[0] >= cut]

    def alive(self):
        """The meter counts as live when a pack is on it: rawV above the
        noise floor means the divider sees a voltage."""
        last = self.last()
        return bool(last) and time.time() - last[0] < 1.5 and last[6] > 20

    def average(self, seconds):
        win = self.window(seconds)
        if not win:
            return None
        v = [s[2] for s in win]; a = [s[3] for s in win]; w = [s[4] for s in win]
        return {"n": len(win),
                "mean_v": statistics.fmean(v), "mean_a": statistics.fmean(a),
                "mean_w": statistics.fmean(w),
                "sd_a": statistics.pstdev(a) if len(a) > 1 else 0.0,
                "sd_w": statistics.pstdev(w) if len(w) > 1 else 0.0,
                "min_v": min(v)}

    def state(self):
        last = self.last()
        with self.lock:
            banner = list(self.banner)[-8:]
        return {
            "port": self.port_name,
            "connected": self.connected,
            "streaming": self.streaming,
            "error": self.error,
            "two_channel": self.two_channel,
            "calibrated": self.settings["calibrated"],
            "banner": banner,
            "last": {"volts": last[2], "amps": last[3], "watts": last[4],
                     "rawI": last[5], "rawV": last[6],
                     "age_s": round(time.time() - last[0], 2)} if last else None,
            "alive": self.alive(),
            "series": [[round(t - time.time(), 2), round(w, 1), round(a, 2), round(v, 2)]
                       for (t, _ms, v, a, w, _ri, _rv) in self.window(90)[-1800:]],
            "avg5": self.average(5),
            "settings": self.settings,
        }


def find_rpm_binary(explicit):
    """The reader lives in rpm/ beside tools/. Accept an explicit path, else look there."""
    cands = [explicit] if explicit else []
    cands += [os.path.join(HERE, "..", "rpm", "rpm_reader_static"),
              os.path.join(HERE, "rpm_reader_static"),
              shutil.which("rpm_reader_static")]
    for c in cands:
        if c and os.path.isfile(c) and os.access(c, os.X_OK):
            return os.path.abspath(c)
    return None

# ------------------------------------------------------------------ state

class Stand:
    """Owns the thrust board's serial port. One reader thread, one writer queue."""

    READING = re.compile(r"^\s*(\d+),(\d+),(-?[\d.]+),(-?[\d.]+),(-?\d+)\s*$")
    RPM_SPINNING = 30.0     # rotor rpm below this is a reader counting noise, not a rotor

    def __init__(self, port, baud, logdir, radius_mm, rpm=None, power=None):
        self.port_name = port
        self.baud = baud
        self.logdir = logdir
        self.radius_mm = radius_mm
        self.rpm = rpm                 # RpmChannel or None
        self.power = power             # PowerChannel or None

        self.ser = None
        self.connected = False
        self.error = ""
        self.streaming = False

        self.lock = threading.Lock()
        self.samples = deque(maxlen=4000)      # (wall_epoch, ms, lbf, N, raw)
        self.banner = deque(maxlen=200)        # '#' lines from the board
        self.events = deque(maxlen=100)        # (seq, line) of the same, for the calibration wizard
        self.seq = 0
        self.arrivals = deque(maxlen=60)       # for measured sample rate
        self.cal = {"factor": None, "sign": None, "tare": None, "ready": None}
        self.opened_at = 0.0
        self.cal_asked = 0
        self.marks = []
        self.cal_lock = threading.Lock()       # one wizard step at a time

        self.outq = queue.Queue()

        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.stream_path = os.path.join(logdir, f"stream-{stamp}.csv")
        self.runlog_path = os.path.join(logdir, "run-log.csv")
        os.makedirs(logdir, exist_ok=True)

        with open(self.stream_path, "w", newline="") as f:
            csv.writer(f).writerow(
                ["iso_time", "epoch_s", "board_ms", "thrust_lbf", "thrust_N", "raw_counts",
                 "rpm", "volts", "amps"])

        self._ensure_runlog_header()

        threading.Thread(target=self._reader, daemon=True).start()
        threading.Thread(target=self._writer, daemon=True).start()

    def _ensure_runlog_header(self):
        """Create run-log.csv, widen an older one in place, or set a foreign one aside.

        If the existing header is a prefix of the current one, the file is
        rewritten with the new header and the old rows padded. Any other
        header (for instance a run-log written by the two-nacelle package,
        whose columns are named differently) is renamed out of the way and a
        fresh file started, rather than appending misaligned rows to it.
        reduce.py reads columns by name, so the old file still reduces.
        """
        if not os.path.exists(self.runlog_path):
            with open(self.runlog_path, "w", newline="") as f:
                csv.writer(f).writerow(RUN_LOG_FIELDS)
            return
        with open(self.runlog_path, newline="") as f:
            rows = list(csv.reader(f))
        if not rows or rows[0] == RUN_LOG_FIELDS:
            return
        old = rows[0]
        if old == RUN_LOG_FIELDS[:len(old)]:
            pad = len(RUN_LOG_FIELDS) - len(old)
            with open(self.runlog_path, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(RUN_LOG_FIELDS)
                for r in rows[1:]:
                    w.writerow(r + [""] * pad)
            print(f"note      widened {os.path.basename(self.runlog_path)} to the new schema "
                  f"({len(rows) - 1} rows kept)")
        else:
            aside = self.runlog_path.replace(".csv", f"-old-schema-{datetime.now():%Y%m%d-%H%M%S}.csv")
            os.replace(self.runlog_path, aside)
            with open(self.runlog_path, "w", newline="") as f:
                csv.writer(f).writerow(RUN_LOG_FIELDS)
            print(f"note      {os.path.basename(self.runlog_path)} had a different column layout; "
                  f"moved it to {os.path.basename(aside)} and started a fresh one")

    def _rpm_now(self):
        if not self.rpm:
            return ""
        last = self.rpm.last()
        if not last or time.time() - last[0] > 1.0:
            return ""
        return f"{last[3]:.0f}"

    def _power_now(self):
        if not self.power:
            return "", ""
        last = self.power.last()
        if not last or time.time() - last[0] > 1.0:
            return "", ""
        return f"{last[2]:.2f}", f"{last[3]:.2f}"

    # -------------------------------------------------------------- serial

    def _open(self):
        try:
            self.ser = serial.Serial(self.port_name, self.baud, timeout=0.4)
            time.sleep(2.2)          # board resets on port open; wait for banner
            self.ser.reset_input_buffer()
            self.connected = True
            self.error = ""
            self.send("d")           # ask for settings so the page has them
            self.opened_at = time.time()
            self.cal_asked = 0
        except Exception as exc:
            self.connected = False
            self.error = str(exc)

    def _reader(self):
        buf = b""
        while True:
            if not self.connected:
                self._open()
                if not self.connected:
                    time.sleep(2.0)
                    continue
            # the first 'd' can be lost in the board's reset window; ask again
            if (self.cal["factor"] is None and self.cal_asked < 4
                    and time.time() - self.opened_at > 3.0 + 3.0 * self.cal_asked):
                self.cal_asked += 1
                self.send("d")
            try:
                chunk = self.ser.read(256)
            except Exception as exc:
                self.error = str(exc)
                self.connected = False
                try:
                    self.ser.close()
                except Exception:
                    pass
                continue
            if not chunk:
                continue
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                self._line(line.decode("utf-8", "replace").strip("\r\n"))

    def _line(self, line):
        if not line:
            return
        m = self.READING.match(line)
        if m:
            now = time.time()
            _, ms, lbf, newton, raw = m.groups()
            rec = (now, int(ms), float(lbf), float(newton), int(raw))
            if self.cal.get("ready") is False:
                self.cal["ready"] = True       # the cell is answering again
                self.error = ""
            with self.lock:
                self.samples.append(rec)
                self.arrivals.append(now)
            with open(self.stream_path, "a", newline="") as f:
                csv.writer(f).writerow([
                    datetime.fromtimestamp(now).isoformat(timespec="milliseconds"),
                    f"{now:.3f}", ms, lbf, newton, raw,
                    self._rpm_now(), *self._power_now()])
            return

        with self.lock:
            self.banner.append(line)
            self.seq += 1
            self.events.append((self.seq, line))
        low = line.lower()
        if "streaming on" in low:
            self.streaming = True
        elif "streaming off" in low:
            self.streaming = False
        elif "calfactor (counts/lbf)" in low:
            self.cal["factor"] = _num(line)
        elif low.strip().startswith("sign"):
            self.cal["sign"] = _num(line)
        elif "sign now" in low:
            self.cal["sign"] = _num(line)
        elif "tare offset" in low:
            self.cal["tare"] = _num(line)
        elif "hx711 ready" in low:
            self.cal["ready"] = "yes" in low
        elif "hx711 timeout" in low or "hx711 not responding" in low:
            self.cal["ready"] = False      # firmware gave up waiting for DT; the page goes red
            self.error = line.lstrip("! ").strip()
        elif "calfactor =" in low:
            self.cal["factor"] = _num(line)

    def _writer(self):
        while True:
            cmd = self.outq.get()
            if self.connected and self.ser:
                try:
                    self.ser.write((cmd + "\n").encode())
                    self.ser.flush()
                except Exception as exc:
                    self.error = str(exc)
                    self.connected = False
            time.sleep(0.08)

    def send(self, cmd):
        self.outq.put(cmd.strip())

    # -------------------------------------------------------------- derived

    def rate_hz(self):
        with self.lock:
            a = list(self.arrivals)
        if len(a) < 3:
            return 0.0
        span = a[-1] - a[0]
        return (len(a) - 1) / span if span > 0 else 0.0

    def window(self, seconds):
        cut = time.time() - seconds
        with self.lock:
            return [s for s in self.samples if s[0] >= cut]

    def average(self, seconds):
        win = self.window(seconds)
        if not win:
            return None
        lbf = [s[2] for s in win]
        raw = [s[4] for s in win]
        return {
            "n": len(win),
            "seconds": seconds,
            "mean_lbf": statistics.fmean(lbf),
            "sd_lbf": statistics.pstdev(lbf) if len(lbf) > 1 else 0.0,
            "min_lbf": min(lbf),
            "max_lbf": max(lbf),
            "mean_raw": statistics.fmean(raw),
            "sd_raw": statistics.pstdev(raw) if len(raw) > 1 else 0.0,
        }

    def mark(self, body):
        """Capture an averaged grid point and append it to run-log.csv."""
        secs = float(body.get("avg_seconds") or 5)
        avg = self.average(secs)
        if avg is None:
            return {"ok": False, "why": f"no samples in the last {secs:g} s"}

        height = _f(body.get("height_mm"))

        # tach average over the same window as the thrust average. A tach that
        # is plugged in but idle still prints rows (all zero), so below
        # RPM_SPINNING it counts as no reading rather than as 0 rpm.
        tach = None
        if self.rpm:
            a = self.rpm.average(secs)
            tach = a["mean_rotor"] if a else None
        typed_actual = _f(body.get("head_rpm_actual"))
        auto_actual = tach if (tach is not None and tach > self.RPM_SPINNING) else None
        actual = typed_actual if typed_actual is not None else auto_actual

        # pack volts and amps: typed wins, else the power meter's average
        typed_v, typed_a = _f(body.get("volts")), _f(body.get("amps"))
        typed_any = typed_v is not None or typed_a is not None
        pwr = self.power.average(secs) if self.power else None
        volts = typed_v if typed_v is not None else (pwr["mean_v"] if pwr else None)
        amps = typed_a if typed_a is not None else (pwr["mean_a"] if pwr else None)
        # watts straight from the meter is the mean of v*i, which is the right
        # number under ripple; v_mean * i_mean is the fallback for typed values
        watts = None
        if not typed_any and pwr:
            watts = pwr["mean_w"]
        elif volts is not None and amps is not None:
            watts = volts * amps

        row = {k: "" for k in RUN_LOG_FIELDS}
        row.update({
            "height_mm": _s(height),
            "z_over_R": f"{height / self.radius_mm:.4f}" if height is not None else "",
            "head_rpm_cmd": _s(_f(body.get("head_rpm_cmd"))),
            "head_rpm_actual": f"{actual:.0f}" if actual is not None else "",
            "collective_deg": _s(_f(body.get("collective_deg"))),
            "servo_us": _s(_f(body.get("servo_us"))),
            "throttle_pct": _s(_f(body.get("throttle_pct"))),
            "thrust_lbf": f"{avg['mean_lbf']:.4f}",
            "volts": f"{volts:.2f}" if volts is not None else "",
            "amps": f"{amps:.2f}" if amps is not None else "",
            "pack_soc": _s(_f(body.get("pack_soc"))),
            "notes": (body.get("notes") or "").replace("\n", " "),
            "rpm_tach": f"{tach:.0f}" if tach is not None else "",
            "watts": f"{watts:.1f}" if watts is not None else "",
        })

        with open(self.runlog_path, "a", newline="") as f:
            csv.DictWriter(f, fieldnames=RUN_LOG_FIELDS).writerow(row)

        self.marks.append({
            "thrust_lbf": avg["mean_lbf"],
            "sd_lbf": avg["sd_lbf"],
            "n": avg["n"],
            "watts": watts,
            "amps": round(amps, 2) if amps is not None else None,
            "volts": round(volts, 2) if volts is not None else None,
            "rpm": (round(actual) if actual is not None else None) or _f(body.get("head_rpm_cmd")),
            "rpm_tach": tach,
            "height_mm": height,
            "collective_deg": _f(body.get("collective_deg")),
            "when": datetime.now().strftime("%H:%M:%S"),
        })
        return {"ok": True, "avg": avg, "row": row, "rpm_actual": actual,
                "rpm_source": "typed" if typed_actual is not None else ("tach" if auto_actual is not None else "none"),
                "watts": watts,
                "power_source": "typed" if typed_any else ("meter" if pwr else "none")}

    # -------------------------------------------------------------- calibration wizard

    def _wait(self, since, pred, timeout):
        """First board line after event `since` for which pred(lowercased) holds."""
        end = time.time() + timeout
        while time.time() < end:
            with self.lock:
                hits = [l for (n, l) in self.events if n > since and pred(l.lower())]
            if hits:
                return hits[0]
            time.sleep(0.05)
        return None

    def calibrate(self, body):
        """The doc 05 sequence, driven from the page.

        step "tare":   't'. Nacelle mounted, nothing else on it, motor off.
        step "weight": 'c <lbf>' with the known weight stacked on the mount,
                       then 'f' (compression calibration on this rig, so the
                       sign must be flipped for thrust to read positive), then
                       'd' so the page shows the stored values.
        The page then asks for the weight to come off and the mount to be
        lifted by hand, and shows the live number, which must go positive.
        """
        if not self.connected:
            return {"ok": False, "why": "thrust board not connected"}
        if not self.cal_lock.acquire(blocking=False):
            return {"ok": False, "why": "a calibration step is already running"}
        try:
            step = body.get("step")
            if step == "tare":
                since = self.seq
                self.send("t")
                done = self._wait(since, lambda l: "zeroed" in l or l.startswith("!"), 12.0)
                if done is None:
                    return {"ok": False, "why": "no reply to tare in 12 s"}
                if done.startswith("!"):
                    return {"ok": False, "why": done.lstrip("! ")}
                return {"ok": True, "tare": self.cal.get("tare")}

            if step == "weight":
                lbf = _f(body.get("lbf"))
                if lbf is None or lbf <= 0:
                    return {"ok": False, "why": "enter the known weight in lbf, e.g. 15.0"}
                since = self.seq
                self.send(f"c {lbf:.3f}")
                done = self._wait(since, lambda l: "calfactor =" in l or l.startswith("!"), 12.0)
                if done is None:
                    return {"ok": False, "why": "no reply to calibrate in 12 s"}
                if done.startswith("!"):
                    return {"ok": False, "why": done.lstrip("! ")}
                check = self._wait(since, lambda l: "check: reading now" in l, 6.0)
                check_lbf = _num(check) if check else None
                # the weight is pressing DOWN on the cell; thrust pulls UP, so flip
                since = self.seq
                self.send("f")
                flipped = self._wait(since, lambda l: "sign now" in l, 6.0)
                self.send("d")
                time.sleep(1.2)                   # let the dump land in self.cal
                return {"ok": True, "factor": self.cal.get("factor"), "sign": self.cal.get("sign"),
                        "check_lbf": check_lbf, "flipped": flipped is not None}

            return {"ok": False, "why": f"unknown step {step!r}"}
        finally:
            self.cal_lock.release()


def _num(line):
    m = re.search(r"(-?\d+\.?\d*)", line.split(":")[-1] if ":" in line else line)
    return float(m.group(1)) if m else None


def _f(v):
    try:
        if v in (None, ""):
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _s(v):
    return "" if v is None else (f"{v:g}")


# ------------------------------------------------------------------ web

# What the page may send to the boards. The server binds every interface so an
# iPad on the VPN can reach it, which also means anything on that network can
# POST here. Nothing here can spin the motor, but a stray 't', 'f' or 'c' in
# the middle of a staircase would corrupt the run with no trace, so only the
# firmware's own command set gets through, and nothing else.
CMD_OK = re.compile(r"^(?:[htrsfzdw?]|c\s*\d*\.?\d+)$", re.I)
PCMD_OK = re.compile(r"^(?:[hrszdwx]|k[av]\s*\d*\.?\d+)$")


class Handler(BaseHTTPRequestHandler):
    stand = None
    curves = {}

    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            return self._send(200, PAGE, "text/html; charset=utf-8")
        if path == "/api/bemt":
            return self._send(200, json.dumps(self.curves))
        if path == "/api/state":
            s = self.stand
            win = s.window(90)
            with s.lock:
                banner = list(s.banner)[-14:]
            last = win[-1] if win else None
            return self._send(200, json.dumps({
                "connected": s.connected,
                "error": s.error,
                "streaming": s.streaming,
                "port": s.port_name,
                "rate_hz": round(s.rate_hz(), 2),
                "cal": s.cal,
                "radius_mm": s.radius_mm,
                "last": {"lbf": last[2], "N": last[3], "raw": last[4],
                         "age_s": round(time.time() - last[0], 2)} if last else None,
                "series": [[round(t - time.time(), 2), round(lbf, 4)]
                           for (t, _ms, lbf, _n, _r) in win[-900:]],
                "avg5": s.average(5),
                "avg30": s.average(30),
                "banner": banner,
                "marks": s.marks[-200:],
                "stream_log": os.path.basename(s.stream_path),
                "run_log": os.path.basename(s.runlog_path),
                "rpm": s.rpm.state() if s.rpm else None,
                "rpm_ratio": s.rpm.cfg.ratio if s.rpm else None,
                "rpm_log": os.path.basename(s.rpm.logpath) if s.rpm else "",
                "power": s.power.state() if s.power else None,
                "power_log": os.path.basename(s.power.logpath) if s.power else "",
            }))
        return self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except json.JSONDecodeError:
            return self._send(400, json.dumps({"ok": False, "why": "bad json"}))
        path = self.path.split("?")[0]
        if path == "/api/cmd":
            cmd = str(body.get("cmd", "")).strip()
            if not CMD_OK.match(cmd):
                return self._send(400, json.dumps({"ok": False, "why": f"not a thrust-stand command: {cmd!r}"}))
            self.stand.send(cmd)
            return self._send(200, json.dumps({"ok": True}))
        if path == "/api/rpmcfg":
            if not self.stand.rpm:
                return self._send(200, json.dumps({"ok": False, "why": "rpm off"}))
            try:
                self.stand.rpm.cfg.set(body.get("ratio"))
            except (TypeError, ValueError) as exc:
                return self._send(200, json.dumps({"ok": False, "why": str(exc)}))
            return self._send(200, json.dumps({"ok": True, "ratio": self.stand.rpm.cfg.ratio}))
        if path == "/api/pcmd":
            if not self.stand.power:
                return self._send(200, json.dumps({"ok": False, "why": "no power meter"}))
            cmd = str(body.get("cmd", "")).strip()
            if not PCMD_OK.match(cmd):
                return self._send(400, json.dumps({"ok": False, "why": f"not a power-meter command: {cmd!r}"}))
            self.stand.power.send(cmd)
            return self._send(200, json.dumps({"ok": True}))
        if path == "/api/mark":
            return self._send(200, json.dumps(self.stand.mark(body)))
        if path == "/api/cal":
            return self._send(200, json.dumps(self.stand.calibrate(body)))
        return self._send(404, json.dumps({"ok": False}))


# ------------------------------------------------------------------ page

PAGE = r"""<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Nacelle Thrust Stand</title>
<style>
 :root{--bg:#12141a;--panel:#1b1e26;--line:#2c3140;--ink:#e6e9f0;--dim:#8b93a7;
       --good:#4ec9a0;--warn:#e0a458;--bad:#e05a5a;--accent:#6aa9ff}
 *{box-sizing:border-box}
 body{margin:0;background:var(--bg);color:var(--ink);
      font:14px/1.45 -apple-system,BlinkMacSystemFont,"SF Pro Text",sans-serif}
 .wrap{max-width:1180px;margin:0 auto;padding:16px}
 h2{font-size:13px;text-transform:uppercase;letter-spacing:.09em;color:var(--dim);
    margin:0 0 10px;font-weight:600}
 .grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:14px}
 .grid.top{grid-template-columns:minmax(0,1fr) minmax(0,1.6fr)}
 .grid.wide{grid-template-columns:minmax(0,1fr) minmax(0,2.6fr)}
 .grid.steps{grid-template-columns:repeat(3,minmax(0,1fr))}
 @media(max-width:860px){.grid,.grid.top,.grid.wide,.grid.steps{grid-template-columns:1fr}}
 .big.mid{font-size:48px}
 .card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px}
 .step{background:#15181f;border:1px solid var(--line);border-radius:8px;padding:12px}
 .step h3{margin:0 0 6px;font-size:13px;color:var(--ink)}
 .step p{margin:0 0 10px;color:var(--dim);font-size:12.5px;line-height:1.5}
 .big{font:600 68px/1 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:-.02em}
 .unit{font-size:22px;color:var(--dim);margin-left:6px}
 .sub{color:var(--dim);font:12px/1.6 ui-monospace,Menlo,monospace;white-space:pre-wrap;overflow-wrap:anywhere}
 .ok{color:var(--good)} .warn{color:var(--warn)} .bad{color:var(--bad)}
 button{background:#252a35;color:var(--ink);border:1px solid var(--line);
        border-radius:7px;padding:9px 13px;font-size:13px;cursor:pointer;margin:0 6px 6px 0}
 button:hover{border-color:var(--accent)}
 button.on{background:var(--accent);border-color:var(--accent);color:#0b1220;font-weight:600}
 button.danger{border-color:#4a2c2c}
 button:disabled{opacity:.5;cursor:default}
 input{background:#0f1116;color:var(--ink);border:1px solid var(--line);
       border-radius:6px;padding:7px 8px;font-size:13px;width:100%}
 label{display:block;font-size:11px;color:var(--dim);margin:0 0 3px;
       text-transform:uppercase;letter-spacing:.05em}
 .f{display:grid;grid-template-columns:repeat(4,1fr);gap:9px;margin-bottom:10px}
 @media(max-width:640px){.f{grid-template-columns:repeat(2,1fr)}}
 canvas{width:100%;display:block;border-radius:6px;background:#0f1116;height:230px}
 #power{height:300px}
 .dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}
 .term{background:#0f1116;border-radius:6px;padding:9px;height:150px;overflow-y:auto;
       font:11px/1.5 ui-monospace,Menlo,monospace;color:#9aa3b8;white-space:pre-wrap}
 .row{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap}
 .tag{font:11px ui-monospace,Menlo,monospace;color:var(--dim)}
 table{width:100%;border-collapse:collapse;font:12px ui-monospace,Menlo,monospace}
 th,td{text-align:right;padding:4px 6px;border-bottom:1px solid var(--line)}
 th{color:var(--dim);font-weight:500;text-align:right}
 td:last-child,th:last-child{text-align:left}
</style></head><body><div class="wrap">

<div class="row" style="margin-bottom:14px;align-items:center">
  <div><div><span class="dot" id="dot"></span><b id="status">connecting</b>
       <span class="tag" id="porttag"></span></div>
       <div class="tag" id="logs"></div></div>
  <div style="text-align:right"><span class="big" id="clock">--:--:--.-</span>
       <div class="sub" id="clockdate"> </div></div>
</div>

<div class="grid top">
  <div class="card">
    <h2>Thrust</h2>
    <div><span class="big" id="lbf">--</span><span class="unit">lbf</span></div>
    <div class="sub" id="detail"> </div>
    <div style="margin-top:12px">
      <button onclick="cmd('t')">Tare</button>
      <button onclick="cmd('r')">Read once</button>
      <button id="sbtn" onclick="cmd('s')">Stream</button>
      <button onclick="cmd('d')">Settings</button>
      <button onclick="cmd('z')">Raw counts</button>
      <button class="danger" onclick="flip()">Flip sign</button>
    </div>
  </div>

  <div class="card">
    <h2>Last 90 seconds</h2>
    <canvas id="strip" data-h="230"></canvas>
    <div class="sub" id="stats" style="margin-top:8px"> </div>
  </div>
</div>

<div class="grid wide" style="margin-top:14px">
  <div class="card">
    <h2><span class="dot" id="dot_rpm"></span>Rotor RPM</h2>
    <div><span class="big mid" id="rpm">--</span><span class="unit">rpm</span></div>
    <div class="sub" id="rpm_detail"> </div>
  </div>
  <div class="card">
    <h2>Rotor RPM, last 90 seconds</h2>
    <canvas id="rpmstrip" data-h="150"></canvas>
    <div class="row" style="margin-top:6px">
      <div class="sub"><span style="color:#6aa9ff">&#9632;</span> rotor rpm (motor rpm / gear ratio)</div>
      <div style="display:flex;align-items:center;gap:6px">
        <label style="margin:0">Gear ratio motor:rotor</label>
        <input id="ratio" inputmode="decimal" style="width:70px" placeholder="3.0">
        <button onclick="setRatio()">Apply</button>
      </div>
    </div>
  </div>
</div>

<div class="grid wide" style="margin-top:14px">
  <div class="card">
    <h2><span class="dot" id="dot_pwr"></span>Pack power</h2>
    <div><span class="big mid" id="pw_w">--</span><span class="unit">W</span></div>
    <div class="sub" id="pw_detail"> </div>
  </div>
  <div class="card">
    <h2>Watts and amps, last 90 seconds</h2>
    <canvas id="pwstrip" data-h="150"></canvas>
    <div class="sub" style="margin-top:6px"><span style="color:#6aa9ff">&#9632;</span> W   <span style="color:#6aa9ff">&#8211; &#8211;</span> A x10</div>
  </div>
</div>

<div class="card" style="margin-top:14px">
  <h2>Calibrate the load cell</h2>
  <div class="grid steps">
    <div class="step">
      <h3>1. Zero</h3>
      <p>Nacelle bolted on, nothing else on it, motor off, rig settled. The cell is
         under the nacelle, so this zeroes out its dead weight.</p>
      <button id="cal_tare" onclick="calTare()">Tare</button>
      <div class="sub" id="cal_tare_msg"> </div>
    </div>
    <div class="step">
      <h3>2. Known weight</h3>
      <p>Stack the known weight on the nacelle mount. Enter what it weighs and
         calibrate. The weight presses DOWN, thrust pulls UP, so the sign is
         flipped for you afterwards and the values are saved to EEPROM.</p>
      <div style="display:flex;gap:8px;align-items:center;margin-bottom:8px">
        <input id="cal_lbf" inputmode="decimal" value="15.0" style="width:90px">
        <span class="tag">lbf</span>
        <button id="cal_go" onclick="calWeight()">Calibrate</button>
      </div>
      <div class="sub" id="cal_weight_msg"> </div>
    </div>
    <div class="step">
      <h3>3. Check</h3>
      <p>Take the weight off. Lift the nacelle mount by hand: the number below must go
         <b>positive</b>. Set it down, then Tare again before the first run.</p>
      <div><span class="big mid" id="cal_live">--</span><span class="unit">lbf</span></div>
      <div class="sub" id="cal_check_msg"> </div>
    </div>
  </div>
</div>

<div class="grid" style="margin-top:14px">
  <div class="card">
    <h2>Power meter</h2>
    <div class="sub" id="pw_cal"> </div>
    <div style="margin-top:10px">
      <button onclick="pcmd('z')" title="motor off, pack connected">Zero amps</button>
      <button onclick="pcmd('d')">Settings</button>
      <button onclick="pcmd('w')">Write</button>
    </div>
  </div>
  <div class="card">
    <h2>Power meter console</h2>
    <div class="term" id="pterm" style="height:120px"></div>
    <div style="margin-top:8px;display:flex;gap:6px">
      <input id="pcmdin" placeholder="ka 18.4   or   kv 24.87" style="flex:1">
      <button onclick="pcmdSend()">Send</button>
    </div>
  </div>
</div>

<div class="card" style="margin-top:14px">
  <h2>Mark a grid point</h2>
  <div class="f">
    <div><label>Height mm</label><input id="height_mm" inputmode="decimal"></div>
    <div><label>RPM cmd</label><input id="head_rpm_cmd" inputmode="decimal"></div>
    <div><label>RPM actual</label><input id="head_rpm_actual" inputmode="decimal" placeholder="auto from tach"></div>
    <div><label>Collective deg</label><input id="collective_deg" inputmode="decimal"></div>
    <div><label>Servo us</label><input id="servo_us" inputmode="decimal"></div>
    <div><label>Throttle %</label><input id="throttle_pct" inputmode="decimal"></div>
    <div><label>Volts</label><input id="volts" inputmode="decimal" placeholder="auto from meter"></div>
    <div><label>Amps</label><input id="amps" inputmode="decimal" placeholder="auto from meter"></div>
    <div><label>Pack SOC</label><input id="pack_soc" inputmode="decimal"></div>
    <div><label>Average over s</label><input id="avg_seconds" value="5" inputmode="decimal"></div>
    <div style="grid-column:span 2"><label>Notes</label><input id="notes"></div>
  </div>
  <button class="on" onclick="mark()">Capture point</button>
  <span class="tag" id="markmsg"></span>
</div>

<div class="grid" style="margin-top:14px">
  <div class="card">
    <h2>Electrical watts vs thrust: BEMT model vs flight test, R = 457 mm</h2>
    <canvas id="power" data-h="300"></canvas>
    <div class="sub" id="legend" style="margin-top:8px"> </div>
  </div>
  <div class="card">
    <h2>Captured points</h2>
    <div style="max-height:200px;overflow-y:auto">
      <table id="mtab"><thead><tr>
        <th>time</th><th>lbf</th><th>sd</th><th>rpm</th><th>W</th><th>A</th><th>ht</th>
      </tr></thead><tbody></tbody></table>
    </div>
    <h2 style="margin-top:14px">Board</h2>
    <div class="term" id="term"> </div>
  </div>
</div>

<div class="card" style="margin-top:14px">
  <h2>Send anything</h2>
  <div style="display:flex;gap:9px">
    <input id="raw" placeholder="e.g.  c 15.0" onkeydown="if(event.key==='Enter')rawsend()">
    <button onclick="rawsend()">Send</button>
  </div>
</div>

</div><script>
let S={},B={},marks=[];
const ACC='#6aa9ff';

const post=(u,b)=>fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},
                          body:JSON.stringify(b||{})}).then(r=>r.json());
const rejected=r=>{if(r&&r.ok===false&&r.why)alert(r.why);return r;};
const cmd=c=>post('/api/cmd',{cmd:c}).then(rejected);
const pcmd=c=>post('/api/pcmd',{cmd:c}).then(rejected);
function setRatio(){
  const i=document.getElementById('ratio'); const r=parseFloat(i.value);
  if(!(r>0)){i.value='';return;}
  post('/api/rpmcfg',{ratio:r}).then(x=>{if(!x.ok)alert('ratio: '+x.why); i.blur();});
}
function pcmdSend(){const i=document.getElementById('pcmdin');if(i.value.trim()){pcmd(i.value.trim());i.value='';}}
document.addEventListener('keydown',e=>{if(e.key!=='Enter')return;
  if(document.activeElement.id==='pcmdin')pcmdSend();
  if(document.activeElement.id==='ratio')setRatio();
  if(document.activeElement.id==='cal_lbf')calWeight();});
const rawsend=()=>{const e=document.getElementById('raw');
  if(e.value.trim()){cmd(e.value.trim());e.value='';}};

function flip(){
  if(confirm("Flip the sign and save it to EEPROM?\n\nDo this after calibrating with a "
            +"weight pressing DOWN, so that thrust pulling UP reads positive."))
    cmd('f');
}

// ---- calibration wizard --------------------------------------------------
let calStage=0;   // 0 nothing, 1 tared, 2 calibrated: step 3 shows the live number
function setMsg(id,text,cls){const e=document.getElementById(id);e.textContent=text;e.className='sub '+(cls||'');}
function calTare(){
  const b=document.getElementById('cal_tare'); b.disabled=true;
  setMsg('cal_tare_msg','taring, hold still (about 4 s)...','warn');
  post('/api/cal',{step:'tare'}).then(r=>{
    b.disabled=false;
    if(r.ok){calStage=1;setMsg('cal_tare_msg',`zeroed. tare offset ${r.tare??'?'} counts. Now stack the weight.`,'ok');
             setMsg('cal_weight_msg',' ');}
    else setMsg('cal_tare_msg','failed: '+r.why,'bad');
  }).catch(e=>{b.disabled=false;setMsg('cal_tare_msg','request failed: '+e,'bad');});
}
function calWeight(){
  const lbf=parseFloat(document.getElementById('cal_lbf').value);
  if(!(lbf>0)){setMsg('cal_weight_msg','enter the known weight in lbf','bad');return;}
  if(calStage<1 && !confirm("You have not tared in this session. The calibration is measured "
      +"from the last tare, which must have been taken with nothing but the nacelle on the mount.\n\nContinue anyway?")) return;
  const b=document.getElementById('cal_go'); b.disabled=true;
  setMsg('cal_weight_msg',`calibrating against ${lbf} lbf, hold still (about 8 s)...`,'warn');
  post('/api/cal',{step:'weight',lbf:lbf}).then(r=>{
    b.disabled=false;
    if(r.ok){
      calStage=2;
      const chk=r.check_lbf!=null?`read back ${r.check_lbf.toFixed(3)} lbf with the weight on`:'no read-back';
      const sign=r.sign==null?'sign unknown, press Settings':(r.sign===-1?'sign -1 (flipped for thrust)':'sign +1: NOT flipped, press Flip sign');
      setMsg('cal_weight_msg',`calFactor ${r.factor!=null?r.factor.toFixed(1):'?'} counts/lbf, saved.\n${chk}.\n${sign}.`,r.sign===-1?'ok':'warn');
      setMsg('cal_check_msg','weight off, lift the mount by hand',' ');
    } else setMsg('cal_weight_msg','failed: '+r.why,'bad');
  }).catch(e=>{b.disabled=false;setMsg('cal_weight_msg','request failed: '+e,'bad');});
}
function calCheck(s){
  const v=document.getElementById('cal_live');
  v.textContent=s.last?s.last.lbf.toFixed(3):'--';
  if(calStage<2||!s.last)return;
  const x=s.last.lbf;
  if(x>0.3) setMsg('cal_check_msg','reads POSITIVE while lifted: sign is right. Set it down and Tare.','ok');
  else if(x<-0.3) setMsg('cal_check_msg','reads NEGATIVE while lifted (or the weight is still on). If you are lifting, press Flip sign.','bad');
  else setMsg('cal_check_msg','weight off, lift the mount by hand',' ');
}

function mark(){
  const ids=['height_mm','head_rpm_cmd','head_rpm_actual','collective_deg','servo_us',
             'throttle_pct','volts','amps','pack_soc','avg_seconds','notes'];
  const b={}; ids.forEach(i=>b[i]=document.getElementById(i).value);
  post('/api/mark',b).then(r=>{
    const m=document.getElementById('markmsg');
    m.textContent = r.ok
      ? `captured ${r.avg.mean_lbf.toFixed(3)} lbf  sd ${r.avg.sd_lbf.toFixed(4)}  n=${r.avg.n}`
        +(r.rpm_actual!=null?`   rpm ${Math.round(r.rpm_actual)} (${r.rpm_source})`:'   no rpm')
        +(r.watts!=null?`   ${r.watts.toFixed(0)} W (${r.power_source})`:'   no power')
      : `not captured: ${r.why}`;
    m.style.color = r.ok ? 'var(--good)' : 'var(--bad)';
  });
}

function fit(c){
  // CSS size comes from data-h, never from the height attribute: setting
  // c.height rewrites that attribute, and reading it back next tick would
  // double the canvas every refresh on a Retina display.
  const r=window.devicePixelRatio||1, h=parseInt(c.dataset.h);
  c.style.height=h+'px';
  const w=c.clientWidth;
  const bw=Math.round(w*r), bh=Math.round(h*r);
  if(c.width!==bw) c.width=bw;
  if(c.height!==bh) c.height=bh;
  const x=c.getContext('2d'); x.setTransform(r,0,0,r,0,0);
  return [x,w,h];}

function axes(x,w,h,pad,x0,x1,y0,y1,xl,yl){
  x.clearRect(0,0,w,h);
  x.strokeStyle='#2c3140';x.fillStyle='#8b93a7';x.lineWidth=1;
  x.font='10px ui-monospace,Menlo,monospace';
  for(let i=0;i<=4;i++){
    const yy=pad+ (h-2*pad)*i/4, v=y1-(y1-y0)*i/4;
    x.beginPath();x.moveTo(pad+34,yy);x.lineTo(w-pad,yy);x.stroke();
    x.textAlign='right';x.fillText(v.toFixed(Math.abs(y1-y0)<4?2:0),pad+30,yy+3);
  }
  for(let i=0;i<=4;i++){
    const xx=pad+34+(w-pad-34-pad)*i/4, v=x0+(x1-x0)*i/4;
    x.textAlign='center';x.fillText(v.toFixed(Math.abs(x1-x0)<20?1:0),xx,h-pad+13);
  }
  x.textAlign='left';x.fillText(yl,pad+2,pad-6);
  x.textAlign='right';x.fillText(xl,w-pad,h-4);
  return (vx,vy)=>[pad+34+(w-pad-34-pad)*(vx-x0)/(x1-x0),
                   pad+(h-2*pad)*(1-(vy-y0)/(y1-y0))];
}

function strip(){
  const c=document.getElementById('strip');const [x,w,h]=fit(c);
  const d=S.series||[];
  if(!d.length){x.clearRect(0,0,w,h);return;}
  const ys=d.map(p=>p[1]);
  let lo=Math.min(...ys),hi=Math.max(...ys);
  const span=Math.max(hi-lo,0.05); lo-=span*0.25; hi+=span*0.25;
  const m=axes(x,w,h,18,-90,0,lo,hi,'seconds ago','lbf');
  x.strokeStyle=ACC;x.lineWidth=1.6;x.beginPath();
  d.forEach((p,i)=>{const q=m(p[0],p[1]);i?x.lineTo(q[0],q[1]):x.moveTo(q[0],q[1]);});
  x.stroke();
  const z=m(0,0);
  if(z[1]>18&&z[1]<h-18){x.strokeStyle='#3a4152';x.setLineDash([3,3]);x.beginPath();
    x.moveTo(52,z[1]);x.lineTo(w-18,z[1]);x.stroke();x.setLineDash([]);}
}

function rpmstrip(){
  const c=document.getElementById('rpmstrip');const [x,w,h]=fit(c);
  const R=S.rpm; const d=(R&&R.series)||[];
  if(!d.length){x.clearRect(0,0,w,h);return;}
  let hi=Math.max(...d.map(p=>p[1]),100); hi=Math.ceil(hi/250)*250;
  const m=axes(x,w,h,16,-90,0,0,hi,'seconds ago','rpm');
  x.strokeStyle=ACC;x.lineWidth=1.4;x.beginPath();
  d.forEach((p,i)=>{const q=m(p[0],p[1]);i?x.lineTo(q[0],q[1]):x.moveTo(q[0],q[1]);});
  x.stroke();
}

function pwstrip(){
  const c=document.getElementById('pwstrip');const [x,w,h]=fit(c);
  const P=S.power; if(!P||!P.alive||!P.series.length){x.clearRect(0,0,w,h);return;}
  let hi=100;
  P.series.forEach(p=>{hi=Math.max(hi,p[1],p[2]*10);});
  hi=Math.ceil(hi/100)*100;
  const m=axes(x,w,h,16,-90,0,0,hi,'seconds ago','W  /  A x10');
  [[1,[]],[2,[4,3]]].forEach(([i,dash])=>{
    x.strokeStyle=ACC;x.lineWidth=1.4;x.setLineDash(dash);x.beginPath();
    P.series.forEach((p,j)=>{const q=m(p[0],i===1?p[1]:p[2]*10);j?x.lineTo(q[0],q[1]):x.moveTo(q[0],q[1]);});
    x.stroke();});
  x.setLineDash([]);
}

function pwPanel(){
  const P=S.power, t=document.getElementById('pterm'), cal=document.getElementById('pw_cal');
  const dot=document.getElementById('dot_pwr'), v=document.getElementById('pw_w'),
        d=document.getElementById('pw_detail');
  if(!P){dot.style.background='#3a4152';v.textContent='--';d.textContent='no --power-port; type volts and amps at capture';
         t.textContent='';cal.textContent='no --power-port';return;}
  const L=P.last, a=P.avg5, s=P.settings||{};
  dot.style.background=P.connected?(P.alive?'var(--good)':'var(--warn)'):'var(--bad)';
  v.textContent=(L&&P.alive)?L.watts.toFixed(0):'--';
  d.textContent = P.connected
    ? (L ? (P.alive
          ? `${L.volts.toFixed(2)} V   ${L.amps.toFixed(2)} A   raw ${L.rawI.toFixed(0)}/${L.rawV.toFixed(0)}   ${L.age_s.toFixed(1)} s ago\n`
            +(a?`5 s: ${a.mean_w.toFixed(0)} W  sd ${a.sd_w.toFixed(0)}   ${a.mean_v.toFixed(2)} V   ${a.mean_a.toFixed(2)} A  sd ${a.sd_a.toFixed(2)}\n`:'')
            +`iZero ${s.iZero??'?'}  iGain ${s.iGain??'?'}  vScale ${s.vScale??'?'}`+(s.vcc!=null?`  rail ${s.vcc.toFixed(3)} V`:'')
          : `no pack on the meter   raw ${L.rawI.toFixed(0)}/${L.rawV.toFixed(0)}`)
         : 'connected, no rows yet')
    : ('disconnected  '+(P.error||''));
  cal.textContent = (P.calibrated===false ? 'NOT CALIBRATED: z, then kv against a meter, ka at a steady load, then w'
                  : P.calibrated===true ? 'calibration loaded from EEPROM. press Zero amps once per session, motor off.'
                  : 'waiting for settings dump')
                  + (P.two_channel ? '\ntwo-channel sketch on this Nano: using its first channel. Flash firmware/power_meter from this package.' : '');
  t.textContent=(P.banner||[]).join('\n'); t.scrollTop=t.scrollHeight;
}

function rpmPanel(){
  const R=S.rpm; const dot=document.getElementById('dot_rpm'),
        v=document.getElementById('rpm'), d=document.getElementById('rpm_detail');
  if(!R){dot.style.background='#3a4152';v.textContent='--';d.textContent='rpm off (--no-rpm)';return;}
  const live=R.running&&R.last&&R.last.age_s<1.5;
  dot.style.background=R.running?(live?'var(--good)':'var(--warn)'):'var(--bad)';
  v.textContent=R.last?R.last.rotor.toFixed(0):'--';
  const a=R.avg5;
  d.textContent = R.running
    ? (R.last ? `motor ${R.last.motor.toFixed(0)} rpm  /${R.ratio}   ${R.last.edges} edges/win   ${R.last.age_s.toFixed(1)} s ago\n`
                +(a?`5 s: ${a.mean_rotor.toFixed(0)}  sd ${a.sd_rotor.toFixed(0)}  band ${(a.max_rotor-a.min_rotor).toFixed(0)}  n=${a.n}`:'')
              : 'reader up, no rows yet')
    : ('reader down: '+(R.error||'')+'\n'+(R.selector?('tach '+R.selector):''));
}

const COL=['#7d8aa0','#8fa3c4','#6aa9ff','#4ec9a0','#3fb87a','#e0a458','#c58ae0','#e05a5a'];
const MEAS='#ffc75f';

function power(){
  const c=document.getElementById('power');const [x,w,h]=fit(c);
  if(!B.rpm){x.clearRect(0,0,w,h);return;}
  const rpms=Object.keys(B.rpm).sort();
  let tmax=0,wmax=0;
  rpms.forEach(r=>B.rpm[r].data.forEach(d=>{tmax=Math.max(tmax,d[0]);wmax=Math.max(wmax,d[2]);}));
  marks.forEach(m=>{tmax=Math.max(tmax,m.thrust_lbf||0);
                    if(m.watts)wmax=Math.max(wmax,m.watts);});
  const meas=((B.measured||{}).points||[]).filter(p=>p.static&&p.thrust_lbf!=null);
  meas.forEach(p=>{tmax=Math.max(tmax,p.thrust_lbf);wmax=Math.max(wmax,p.elec_w);});
  tmax=Math.ceil(tmax); wmax=Math.ceil(wmax/50)*50;
  const m=axes(x,w,h,18,0,tmax,0,wmax,'thrust lbf','elec W');
  rpms.forEach((r,i)=>{
    x.strokeStyle=COL[i%COL.length];x.lineWidth=1.6;x.beginPath();
    B.rpm[r].data.forEach((d,j)=>{const q=m(d[0],d[2]);j?x.lineTo(q[0],q[1]):x.moveTo(q[0],q[1]);});
    x.stroke();
  });
  const t=m(7.5,0),tt=m(7.5,wmax);
  x.strokeStyle='#e05a5a';x.setLineDash([4,4]);x.lineWidth=1;x.beginPath();
  x.moveTo(t[0],t[1]);x.lineTo(tt[0],tt[1]);x.stroke();x.setLineDash([]);
  x.fillStyle='#e05a5a';x.font='10px ui-monospace,Menlo,monospace';
  x.textAlign='left';x.fillText('7.5 target',tt[0]+4,tt[1]+11);
  meas.forEach(p=>{const q=m(p.thrust_lbf,p.elec_w);
    x.fillStyle=MEAS;x.beginPath();
    x.moveTo(q[0],q[1]-7);x.lineTo(q[0]+7,q[1]);x.lineTo(q[0],q[1]+7);x.lineTo(q[0]-7,q[1]);
    x.closePath();x.fill();x.strokeStyle='#12141a';x.lineWidth=1.5;x.stroke();
    x.fillStyle=MEAS;x.font='10px ui-monospace,Menlo,monospace';x.textAlign='left';
    x.fillText(`${p.elec_w.toFixed(0)} W flight, ${p.rpm} rpm`,q[0]+10,q[1]-6);});
  marks.forEach(k=>{if(!k.watts)return;const q=m(k.thrust_lbf,k.watts);
    x.fillStyle='#fff';x.beginPath();x.arc(q[0],q[1],4,0,7);x.fill();
    x.strokeStyle='#12141a';x.lineWidth=1.5;x.stroke();});
  const L=document.getElementById('legend');
  L.innerHTML = rpms.map((r,i)=>
      `<span style="color:${COL[i%COL.length]}">&#9632;</span> ${r} rpm, `
      +`max ${B.rpm[r].max_thrust_lbf.toFixed(2)} lbf`).join('<br>')
    + '<br><span style="color:#fff">&#9679;</span> your captured points'
    + ' (needs volts and amps)'
    + (meas.length ? '<br><span style="color:'+MEAS+'">&#9670;</span> flight test, per nacelle'
      + ': the anchor. BEMT curves are the model and run about 1.6 low here.' : '');
}

function tick(){
  fetch('/api/state').then(r=>r.json()).then(s=>{
    S=s; marks=s.marks||[];
    const dot=document.getElementById('dot'),st=document.getElementById('status');
    const live = s.connected && s.last && s.last.age_s < 4;
    dot.style.background = s.connected ? (live?'var(--good)':'var(--warn)') : 'var(--bad)';
    st.textContent = s.connected ? (s.streaming?'streaming':'connected, idle')
                                 : ('disconnected  '+(s.error||''));
    document.getElementById('porttag').textContent =
      `${s.port}   ${s.rate_hz.toFixed(2)} Hz`;
    document.getElementById('logs').textContent = `${s.stream_log}   ${s.run_log}`+(s.rpm_log?`   ${s.rpm_log}`:'')+(s.power_log?`   ${s.power_log}`:'');
    document.getElementById('sbtn').className = s.streaming?'on':'';

    document.getElementById('lbf').textContent =
      s.last ? s.last.lbf.toFixed(3) : '--';
    document.getElementById('detail').textContent = s.last
      ? `${s.last.N.toFixed(2)} N     raw ${s.last.raw}     ${s.last.age_s.toFixed(1)} s ago\n`
        + `calFactor ${s.cal.factor??'?'}   sign ${s.cal.sign??'?'}   tare ${s.cal.tare??'?'}`
        + (s.cal.ready===false?'\nHX711 NOT ANSWERING: '+(s.error||''):'')
      : 'no samples yet  -  press Stream or Read once';

    const a=s.avg5,b=s.avg30;
    document.getElementById('stats').textContent = a
      ? `5 s : ${a.mean_lbf.toFixed(4)} lbf  sd ${a.sd_lbf.toFixed(4)}  `
        +`band ${(a.max_lbf-a.min_lbf).toFixed(4)}  n=${a.n}\n`
        +(b?`30 s: ${b.mean_lbf.toFixed(4)} lbf  sd ${b.sd_lbf.toFixed(4)}  `
            +`raw sd ${b.sd_raw.toFixed(0)} counts  n=${b.n}`:'')
      : ' ';

    const t=document.getElementById('term');
    t.textContent=(s.banner||[]).join('\n'); t.scrollTop=t.scrollHeight;

    const tb=document.querySelector('#mtab tbody');
    tb.innerHTML = marks.slice().reverse().map(k=>
      `<tr><td>${k.when}</td><td>${k.thrust_lbf.toFixed(3)}</td>`
      +`<td>${k.sd_lbf.toFixed(4)}</td><td>${k.rpm??''}</td>`
      +`<td>${k.watts?k.watts.toFixed(0):''}</td>`
      +`<td>${k.amps??''}</td>`
      +`<td>${k.height_mm??''}</td></tr>`).join('');

    rpmPanel(); pwPanel(); calCheck(s);
    const ri=document.getElementById('ratio');
    if(s.rpm_ratio!=null && document.activeElement!==ri) ri.value=s.rpm_ratio;
    strip(); rpmstrip(); pwstrip(); power();
  }).catch(()=>{});
}

fetch('/api/bemt').then(r=>r.json()).then(b=>{B=b;power();});
function clock(){
  const d=new Date(), z=n=>String(n).padStart(2,'0');
  document.getElementById('clock').textContent =
    `${z(d.getHours())}:${z(d.getMinutes())}:${z(d.getSeconds())}.${Math.floor(d.getMilliseconds()/100)}`;
  document.getElementById('clockdate').textContent =
    `${d.getFullYear()}-${z(d.getMonth()+1)}-${z(d.getDate())}  local time, same clock as log iso_time`;
}
setInterval(clock,100); clock();
setInterval(tick,300); tick();
window.addEventListener('resize',()=>{strip();rpmstrip();pwstrip();power();});
</script></body></html>
"""


# ------------------------------------------------------------------ main


def lan_addresses():
    """This Mac's own IPv4 addresses, for the dashboard link from other devices.
    The UDP connect sends nothing; it just asks the kernel which interface
    would route out, which is the address the iPad can reach."""
    found = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        found.append(s.getsockname()[0])
        s.close()
    except Exception:
        pass
    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            if not ip.startswith("127.") and ip not in found:
                found.append(ip)
    except Exception:
        pass
    return found


def serve_on(bind, first_port, handler, pinned, tries=20):
    """Bind the HTTP server, stepping up from first_port if it is taken.

    This Mac serves other things. 8000 in particular is almost always gone,
    and an occupied port is not a reason to stop taking data. If the user
    pinned --http-port explicitly, respect that and fail loudly instead of
    silently landing somewhere they are not looking.
    """
    last = None
    for p in range(first_port, first_port + (1 if pinned else tries)):
        try:
            return ThreadingHTTPServer((bind, p), handler), p
        except OSError as exc:
            if exc.errno not in (errno.EADDRINUSE, errno.EACCES):
                raise
            last = exc
    raise SystemExit(
        f"no free HTTP port in {first_port}..{first_port + tries - 1} ({last}).\n"
        f"Something else is holding them. Try --http-port with a number you know "
        f"is free, or:  lsof -nP -iTCP:{first_port} -sTCP:LISTEN"
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", help="serial device of the thrust Nano, e.g. /dev/cu.usbserial-1480")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--version", action="store_true", help="print version and file path, then exit")
    ap.add_argument("--http-port", type=int, default=8765,
                    help="default 8765. If busy, the next free port is used "
                         "unless you pin one explicitly.")
    ap.add_argument("--bind", default="0.0.0.0",
                    help="0.0.0.0 lets an iPad on the VPN reach it; 127.0.0.1 for local only")
    ap.add_argument("--logdir", default=os.path.join(HERE, "logs"))
    ap.add_argument("--radius", type=float, default=457.0, help="rotor radius mm, for z/R")
    ap.add_argument("--list", action="store_true", help="list serial ports and exit")
    ap.add_argument("--open", action="store_true",
                    help="open the dashboard in the default browser once the server is up "
                         "(start.sh uses this, so it always lands on the port actually bound)")
    g = ap.add_argument_group("rpm tach (FT232H, rpm/rpm_reader_static)")
    g.add_argument("--no-rpm", action="store_true", help="do not start the tach reader")
    g.add_argument("--rpm-bin", help="path to rpm_reader_static (default: rpm/ beside tools/)")
    g.add_argument("--tach", default="0",
                   help="the FT232H: USB device index or USB serial (default 0). "
                        "start.sh fills this in from ports.json.")
    g.add_argument("--rpm-poles", type=int, default=28,
                   help="motor magnets. MN6007 II is 24N28P: 28 (default)")
    g.add_argument("--rpm-ratio", type=float, default=None,
                   help="motor:rotor gear ratio. Default 3.0, or the last value set on the page "
                        "(kept in live-settings.json). Giving it here overrides and stores it.")
    g.add_argument("--rpm-window", type=float, default=0.05, help="seconds per RPM sample")
    p = ap.add_argument_group("power meter (firmware/power_meter Nano)")
    p.add_argument("--power-port", help="serial device of the power-meter Nano; omit to type volts/amps by hand")
    p.add_argument("--power-baud", type=int, default=115200)
    args = ap.parse_args()
    if args.version:
        print(f"live.py {VERSION}  {os.path.abspath(__file__)}")
        return

    ports = list(serial.tools.list_ports.comports())
    if args.list:
        if not ports:
            print("no serial ports found")
        for p in ports:
            print(f"{p.device:34s} {p.description}")
        return

    port = args.port
    if not port:
        guess = [p.device for p in ports if "usbserial" in p.device or "usbmodem" in p.device]
        if len(guess) == 1:
            port = guess[0]
            print(f"auto-selected {port}")
        else:
            sys.exit("specify --port. Run with --list to see what is there, or use tools/start.sh.")

    curves_path = os.path.join(HERE, "bemt_curves_v49.json")
    curves = {}
    if os.path.exists(curves_path):
        with open(curves_path) as f:
            curves = json.load(f)
    else:
        print(f"note: {curves_path} missing, the power chart will be empty")

    rpm = None
    rpm_bin = None
    rpm_cfg = RpmConfig(args.rpm_ratio)
    if not args.no_rpm:
        rpm_bin = find_rpm_binary(args.rpm_bin)
        os.makedirs(args.logdir, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        rpm_log = os.path.join(args.logdir, f"rpm-{stamp}.csv")
        with open(rpm_log, "w", newline="") as f:
            csv.writer(f).writerow(
                ["iso_time", "epoch_s", "edges", "motor_rpm", "rotor_rpm", "ratio"])
        rpm = RpmChannel(args.tach, rpm_bin, args.rpm_poles, rpm_cfg, args.rpm_window, rpm_log)

    power = None
    if args.power_port:
        if args.power_port == port:
            sys.exit("--power-port is the same device as --port; the power meter is a separate Nano")
        os.makedirs(args.logdir, exist_ok=True)
        pstamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        power_log = os.path.join(args.logdir, f"power-{pstamp}.csv")
        with open(power_log, "w", newline="") as f:
            csv.writer(f).writerow(
                ["iso_time", "epoch_s", "board_ms", "volts", "amps", "watts", "rawI", "rawV"])
        power = PowerChannel(args.power_port, args.power_baud, power_log)

    Handler.stand = Stand(port, args.baud, args.logdir, args.radius, rpm, power)
    Handler.curves = curves

    pinned = any(a.startswith("--http-port") for a in sys.argv[1:])
    srv, http_port = serve_on(args.bind, args.http_port, Handler, pinned)

    print(f"live.py   {VERSION}   {os.path.abspath(__file__)}")
    print(f"port      {port} @ {args.baud}")
    print(f"logs      {args.logdir}")
    if args.no_rpm:
        print("rpm       off (--no-rpm)")
    elif rpm_bin:
        print(f"rpm       {rpm_bin}")
        print(f"          tach={args.tach}  poles={args.rpm_poles}  ratio={rpm_cfg.ratio:g}  "
              f"window={args.rpm_window:g}s")
    else:
        print("rpm       reader binary not found. Build it:  bash rpm/scripts/build_static.sh")
        print("          thrust works without it; the RPM panel will say reader down")
    print(f"power     {args.power_port}" if args.power_port
          else "power     off (no --power-port); volts and amps typed by hand")
    if http_port != args.http_port:
        print(f"note      {args.http_port} was busy, using {http_port}")
    print()
    print("=" * 60)
    print(f"DASHBOARD   http://localhost:{http_port}")
    if args.bind == "0.0.0.0":
        for ip in lan_addresses():
            print(f"            http://{ip}:{http_port}   (iPad or any device on the LAN / VPN)")
    print("=" * 60)
    print("ctrl-C to stop")
    if args.open:
        try:
            webbrowser.open(f"http://localhost:{http_port}")
        except Exception as exc:
            print(f"note      could not open the browser: {exc}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        if rpm:
            rpm.stop()
        print("\nstopped")


if __name__ == "__main__":
    main()
