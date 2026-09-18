#!/usr/bin/env python3
"""
live.py - live thrust readout, logger and BEMT overlay for the nacelle thrust stand.

Runs a small web server on this machine. Open the page in any browser on the
Mac, or on an iPad / phone over the VPN, and you get a live readout, a rolling
strip chart, the calibration controls, and a power chart with the BEMT model,
the flight-test anchor (hover 1800 rpm at 446 W per nacelle) and your
measured grid points laid over it.

    pip3 install pyserial
    python3 live.py --port /dev/cu.usbserial-1480
    python3 live.py --list          # show serial ports and exit

Then open  http://localhost:8765

The default HTTP port is 8765 rather than 8000, because 8000 is the port
everything else on a Mac grabs first. If it is busy anyway, live.py walks
upward to the next free one and prints which it took. --http-port pins it.

To reach it from an iPad over the VPN, use the Mac's VPN address instead of
localhost. The server binds all interfaces by default.

Two log files are written next to this script (override with --logdir):

    stream-YYYYmmdd-HHMMSS.csv   every sample that arrives, wall-clock stamped
    run-log.csv                  one row per marked grid point, schema matches
                                 data/run-log-template.csv so reduce.py eats it

Nothing here talks to the ESC or the motor. It reads the load cell and it
writes files. Volts and amps are typed in by hand from the watt meter.
"""

import argparse
import csv
import json
import os
import queue
import re
import statistics
import sys
import threading
import time
from collections import deque
from datetime import datetime
import errno
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    sys.exit("pyserial not installed.  pip3 install pyserial")

VERSION = "2026-09-17.5"
HERE = os.path.dirname(os.path.abspath(__file__))

RUN_LOG_FIELDS = [
    "height_mm", "z_over_R", "head_rpm_cmd", "head_rpm_actual",
    "collective_deg", "servo_us", "throttle_pct", "thrust_lbf",
    "volts", "amps", "pack_soc", "notes",
]

# ------------------------------------------------------------------ state

class Stand:
    """Owns the serial port. One reader thread, one writer queue."""

    READING = re.compile(r"^\s*(\d+),(\d+),(-?[\d.]+),(-?[\d.]+),(-?\d+)\s*$")

    def __init__(self, port, baud, logdir, radius_mm):
        self.port_name = port
        self.baud = baud
        self.logdir = logdir
        self.radius_mm = radius_mm

        self.ser = None
        self.connected = False
        self.error = ""
        self.streaming = False

        self.lock = threading.Lock()
        self.samples = deque(maxlen=4000)      # (wall_epoch, ms, lbf, N, raw)
        self.banner = deque(maxlen=200)        # '#' lines from the board
        self.arrivals = deque(maxlen=60)       # for measured sample rate
        self.cal = {"factor": None, "sign": None, "tare": None, "ready": None}
        self.opened_at = 0.0
        self.cal_asked = 0
        self.marks = []

        self.outq = queue.Queue()

        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.stream_path = os.path.join(logdir, f"stream-{stamp}.csv")
        self.runlog_path = os.path.join(logdir, "run-log.csv")
        os.makedirs(logdir, exist_ok=True)

        with open(self.stream_path, "w", newline="") as f:
            csv.writer(f).writerow(
                ["iso_time", "epoch_s", "board_ms", "thrust_lbf", "thrust_N", "raw_counts"])

        if not os.path.exists(self.runlog_path):
            with open(self.runlog_path, "w", newline="") as f:
                csv.writer(f).writerow(RUN_LOG_FIELDS)

        threading.Thread(target=self._reader, daemon=True).start()
        threading.Thread(target=self._writer, daemon=True).start()

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
            with self.lock:
                self.samples.append(rec)
                self.arrivals.append(now)
            with open(self.stream_path, "a", newline="") as f:
                csv.writer(f).writerow([
                    datetime.fromtimestamp(now).isoformat(timespec="milliseconds"),
                    f"{now:.3f}", ms, lbf, newton, raw])
            return

        with self.lock:
            self.banner.append(line)
        low = line.lower()
        if "streaming on" in low:
            self.streaming = True
        elif "streaming off" in low:
            self.streaming = False
        elif "calfactor (counts/lbf)" in low:
            self.cal["factor"] = _num(line)
        elif low.strip().startswith("sign"):
            self.cal["sign"] = _num(line)
        elif "tare offset" in low:
            self.cal["tare"] = _num(line)
        elif "hx711 ready" in low:
            self.cal["ready"] = "yes" in low
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
        row = {k: "" for k in RUN_LOG_FIELDS}
        row.update({
            "height_mm": _s(height),
            "z_over_R": f"{height / self.radius_mm:.4f}" if height is not None else "",
            "head_rpm_cmd": _s(_f(body.get("head_rpm_cmd"))),
            "head_rpm_actual": _s(_f(body.get("head_rpm_actual"))),
            "collective_deg": _s(_f(body.get("collective_deg"))),
            "servo_us": _s(_f(body.get("servo_us"))),
            "throttle_pct": _s(_f(body.get("throttle_pct"))),
            "thrust_lbf": f"{avg['mean_lbf']:.4f}",
            "volts": _s(_f(body.get("volts"))),
            "amps": _s(_f(body.get("amps"))),
            "pack_soc": _s(_f(body.get("pack_soc"))),
            "notes": (body.get("notes") or "").replace("\n", " "),
        })

        with open(self.runlog_path, "a", newline="") as f:
            csv.DictWriter(f, fieldnames=RUN_LOG_FIELDS).writerow(row)

        volts, amps = _f(body.get("volts")), _f(body.get("amps"))
        self.marks.append({
            "thrust_lbf": avg["mean_lbf"],
            "sd_lbf": avg["sd_lbf"],
            "n": avg["n"],
            "watts": (volts * amps) if (volts is not None and amps is not None) else None,
            "amps": amps,
            "rpm": _f(body.get("head_rpm_actual")) or _f(body.get("head_rpm_cmd")),
            "height_mm": height,
            "collective_deg": _f(body.get("collective_deg")),
            "when": datetime.now().strftime("%H:%M:%S"),
        })
        return {"ok": True, "avg": avg, "row": row}


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
            self.stand.send(str(body.get("cmd", "")))
            return self._send(200, json.dumps({"ok": True}))
        if path == "/api/mark":
            return self._send(200, json.dumps(self.stand.mark(body)))
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
 .grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
 @media(max-width:860px){.grid{grid-template-columns:1fr}}
 .card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px}
 .big{font:600 68px/1 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:-.02em}
 .unit{font-size:22px;color:var(--dim);margin-left:6px}
 .sub{color:var(--dim);font:12px/1.6 ui-monospace,Menlo,monospace;white-space:pre}
 button{background:#252a35;color:var(--ink);border:1px solid var(--line);
        border-radius:7px;padding:9px 13px;font-size:13px;cursor:pointer;margin:0 6px 6px 0}
 button:hover{border-color:var(--accent)}
 button.on{background:var(--accent);border-color:var(--accent);color:#0b1220;font-weight:600}
 button.danger{border-color:#4a2c2c}
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

<div class="row" style="margin-bottom:14px">
  <div><span class="dot" id="dot"></span><b id="status">connecting</b>
       <span class="tag" id="porttag"></span></div>
  <div class="tag" id="logs"></div>
</div>

<div class="grid">
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

<div class="card" style="margin-top:14px">
  <h2>Mark a grid point</h2>
  <div class="f">
    <div><label>Height mm</label><input id="height_mm" inputmode="decimal"></div>
    <div><label>RPM cmd</label><input id="head_rpm_cmd" inputmode="decimal"></div>
    <div><label>RPM actual</label><input id="head_rpm_actual" inputmode="decimal"></div>
    <div><label>Collective deg</label><input id="collective_deg" inputmode="decimal"></div>
    <div><label>Servo us</label><input id="servo_us" inputmode="decimal"></div>
    <div><label>Throttle %</label><input id="throttle_pct" inputmode="decimal"></div>
    <div><label>Volts</label><input id="volts" inputmode="decimal"></div>
    <div><label>Amps</label><input id="amps" inputmode="decimal"></div>
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

const post=(u,b)=>fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},
                          body:JSON.stringify(b||{})}).then(r=>r.json());
const cmd=c=>post('/api/cmd',{cmd:c});
const rawsend=()=>{const e=document.getElementById('raw');
  if(e.value.trim()){cmd(e.value.trim());e.value='';}};

function flip(){
  if(confirm("Flip the sign and save it to EEPROM?\n\nDo this after calibrating with a "
            +"weight pressing DOWN, so that thrust pulling UP reads positive."))
    cmd('f');
}

function mark(){
  const ids=['height_mm','head_rpm_cmd','head_rpm_actual','collective_deg','servo_us',
             'throttle_pct','volts','amps','pack_soc','avg_seconds','notes'];
  const b={}; ids.forEach(i=>b[i]=document.getElementById(i).value);
  post('/api/mark',b).then(r=>{
    const m=document.getElementById('markmsg');
    m.textContent = r.ok
      ? `captured ${r.avg.mean_lbf.toFixed(3)} lbf  sd ${r.avg.sd_lbf.toFixed(4)}  n=${r.avg.n}`
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
  x.strokeStyle='#6aa9ff';x.lineWidth=1.6;x.beginPath();
  d.forEach((p,i)=>{const q=m(p[0],p[1]);i?x.lineTo(q[0],q[1]):x.moveTo(q[0],q[1]);});
  x.stroke();
  const z=m(0,0);
  if(z[1]>18&&z[1]<h-18){x.strokeStyle='#3a4152';x.setLineDash([3,3]);x.beginPath();
    x.moveTo(52,z[1]);x.lineTo(w-18,z[1]);x.stroke();x.setLineDash([]);}
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
    document.getElementById('logs').textContent = `${s.stream_log}   ${s.run_log}`;
    document.getElementById('sbtn').className = s.streaming?'on':'';

    document.getElementById('lbf').textContent =
      s.last ? s.last.lbf.toFixed(3) : '--';
    document.getElementById('detail').textContent = s.last
      ? `${s.last.N.toFixed(2)} N     raw ${s.last.raw}     ${s.last.age_s.toFixed(1)} s ago\n`
        + `calFactor ${s.cal.factor??'?'}   sign ${s.cal.sign??'?'}   tare ${s.cal.tare??'?'}`
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
      +`<td>${k.watts?k.watts.toFixed(0):''}</td><td>${k.amps??''}</td>`
      +`<td>${k.height_mm??''}</td></tr>`).join('');

    strip(); power();
  }).catch(()=>{});
}

fetch('/api/bemt').then(r=>r.json()).then(b=>{B=b;power();});
setInterval(tick,300); tick();
window.addEventListener('resize',()=>{strip();power();});
</script></body></html>
"""


# ------------------------------------------------------------------ main


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
    ap.add_argument("--port", help="serial device, e.g. /dev/cu.usbserial-1480")
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
            sys.exit("specify --port. Run with --list to see what is there.")

    curves_path = os.path.join(HERE, "bemt_curves_v49.json")
    curves = {}
    if os.path.exists(curves_path):
        with open(curves_path) as f:
            curves = json.load(f)
    else:
        print(f"note: {curves_path} missing, the power chart will be empty")

    Handler.stand = Stand(port, args.baud, args.logdir, args.radius)
    Handler.curves = curves

    pinned = any(a.startswith("--http-port") for a in sys.argv[1:])
    srv, http_port = serve_on(args.bind, args.http_port, Handler, pinned)

    print(f"live.py   {VERSION}   {os.path.abspath(__file__)}")
    print(f"port      {port} @ {args.baud}")
    print(f"logs      {args.logdir}")
    if http_port != args.http_port:
        print(f"note      {args.http_port} was busy, using {http_port}")
    print(f"open      http://localhost:{http_port}")
    if args.bind == "0.0.0.0":
        print(f"          or http://<this-mac-vpn-address>:{http_port} from an iPad")
    print("ctrl-C to stop")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
