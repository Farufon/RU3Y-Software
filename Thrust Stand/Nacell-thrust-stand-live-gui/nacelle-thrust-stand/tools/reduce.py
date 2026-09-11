#!/usr/bin/env python3
"""
Nacelle thrust stand data reduction.

Reads the bench run log (data/run-log-template.csv, filled in). For each rotor
height AND each governed head RPM, interpolates the electrical power required to
produce the target thrust. Then, for each height, reports the (RPM, collective)
combination that reaches the target thrust for the fewest watts.

That minimum-watts-vs-height curve is the deliverable.

Standard library only. No install needed.

Usage:
    python3 reduce.py ../data/my-runs.csv
    python3 reduce.py ../data/my-runs.csv --thrust 7.5
    python3 reduce.py ../data/my-runs.csv --thrust 7.5 --radius 457
    python3 reduce.py ../data/my-runs.csv --by-rpm        # full grid, not just the best
"""

import argparse
import csv
import sys
from collections import defaultdict

LBF_TO_N = 4.4482216
DEFAULT_RADIUS_MM = 457.0      # confirmed 4 Sep 2026, hub centreline to tip


def _f(raw, key):
    v = (raw.get(key) or "").strip()
    return float(v) if v else None


def load_rows(path):
    rows = []
    with open(path, newline="") as fh:
        reader = csv.DictReader(r for r in fh if not r.lstrip().startswith("#"))
        for i, raw in enumerate(reader, start=2):
            if not raw or all((v or "").strip() == "" for v in raw.values()):
                continue
            try:
                thrust = _f(raw, "thrust_lbf")
                volts = _f(raw, "volts")
                amps = _f(raw, "amps")
                if thrust is None or volts is None or amps is None:
                    continue          # unfilled template row, silently skip
                rows.append({
                    "height_mm":       _f(raw, "height_mm"),
                    "head_rpm_cmd":    _f(raw, "head_rpm_cmd"),
                    "head_rpm_actual": _f(raw, "head_rpm_actual"),
                    "collective_deg":  _f(raw, "collective_deg"),
                    "servo_us":        _f(raw, "servo_us"),
                    "thrust_lbf":      thrust,
                    "volts":           volts,
                    "amps":            amps,
                    "watts":           volts * amps,
                    "line":            i,
                })
            except (KeyError, ValueError, TypeError) as exc:
                print(f"  skipping line {i}: {exc}", file=sys.stderr)
    return rows


def check_governor(rows, tol_pct=2.0):
    """Warn where the governor did not hold its setpoint."""
    bad = []
    for r in rows:
        c, a = r["head_rpm_cmd"], r["head_rpm_actual"]
        if c and a and c > 0:
            err = 100.0 * (a - c) / c
            if abs(err) > tol_pct:
                bad.append((r["line"], c, a, err))
    return bad


def interp_at_thrust(points, target):
    """points: list of (thrust, watts, collective, rpm_actual) sorted by thrust.

    Returns interpolated dict at target thrust, or None if not bracketed.
    Extrapolation is deliberately refused.
    """
    for p0, p1 in zip(points, points[1:]):
        t0, t1 = p0[0], p1[0]
        if t0 <= target <= t1 and t1 > t0:
            f = (target - t0) / (t1 - t0)
            return {
                "watts":      p0[1] + f * (p1[1] - p0[1]),
                "collective": None if p0[2] is None or p1[2] is None
                              else p0[2] + f * (p1[2] - p0[2]),
                "rpm":        None if p0[3] is None or p1[3] is None
                              else p0[3] + f * (p1[3] - p0[3]),
            }
    return None


def cheeseman_bennett(z_mm, radius_mm):
    if z_mm <= 0:
        return None
    ratio = radius_mm / (4.0 * z_mm)
    denom = 1.0 - ratio ** 2
    # model invalid below z/R = 0.5; 1% tolerance so a nominal 0.50 step that
    # measures a hair low still evaluates instead of silently printing n/a
    if denom <= 0 or z_mm < 0.495 * radius_mm:
        return None
    return 1.0 / denom


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csvfile", help="filled-in run log")
    ap.add_argument("--thrust", type=float, default=7.5,
                    help="target thrust in lbf per nacelle (default 7.5)")
    ap.add_argument("--radius", type=float, default=DEFAULT_RADIUS_MM,
                    help=f"rotor radius in mm (default {DEFAULT_RADIUS_MM:.0f})")
    ap.add_argument("--by-rpm", action="store_true",
                    help="print the full height x RPM grid, not just the best per height")
    args = ap.parse_args()

    rows = load_rows(args.csvfile)
    if not rows:
        print("No usable data rows found.", file=sys.stderr)
        return 1

    bad = check_governor(rows)
    if bad:
        print("WARNING: governor did not hold setpoint on these lines "
              "(commanded vs actual differ by more than 2%):")
        for line, c, a, err in bad:
            print(f"    line {line:4d}   cmd {c:6.0f}   actual {a:6.0f}   {err:+.1f}%")
        print("  Those rows are not the operating point their label claims.\n")

    # group by (height, commanded rpm)
    grid = defaultdict(list)
    for r in rows:
        grid[(r["height_mm"], r["head_rpm_cmd"])].append(r)

    # interpolate each cell
    cells = {}
    for (h, rpm), pts in grid.items():
        seq = sorted(
            ((p["thrust_lbf"], p["watts"], p["collective_deg"],
              p["head_rpm_actual"] or rpm) for p in pts),
            key=lambda x: x[0])
        got = interp_at_thrust(seq, args.thrust)
        if got:
            cells[(h, rpm)] = got

    if not cells:
        print(f"No height/RPM cell brackets {args.thrust:.2f} lbf. "
              "You need points above and below the target.", file=sys.stderr)
        return 1

    heights = sorted({h for h, _ in cells})
    rpms = sorted({r for _, r in cells if r is not None})

    if args.by_rpm:
        print(f"\nElectrical watts to hold {args.thrust:.2f} lbf - full grid")
        print(f"Rotor radius {args.radius:.0f} mm\n")
        head = f"{'z mm':>7}{'z/R':>7}"
        for rp in rpms:
            head += f"{int(rp):>10}"
        print(head)
        print("-" * len(head))
        for h in heights:
            line = f"{h:7.0f}{h/args.radius:7.2f}"
            for rp in rpms:
                c = cells.get((h, rp))
                line += f"{c['watts']:10.1f}" if c else f"{'--':>10}"
            print(line)
        print()

    # best cell per height
    print(f"\nDELIVERABLE: minimum electrical watts to hold {args.thrust:.2f} lbf vs height")
    print(f"Rotor radius {args.radius:.0f} mm. C-B column is a THRUST ratio, "
          "shown only as a sanity reference.\n")
    hdr = (f"{'z mm':>7}{'z/R':>7}{'watts':>9}{'best RPM':>10}"
           f"{'pitch@0.75R':>13}{'vs OGE':>9}{'C-B thrust':>12}")
    print(hdr)
    print("-" * len(hdr))

    best = {}
    for h in heights:
        cand = [(rp, c) for (hh, rp), c in cells.items() if hh == h]
        rp, c = min(cand, key=lambda x: x[1]["watts"])
        best[h] = (rp, c)

    ogeh = max(heights)
    oge_w = best[ogeh][1]["watts"]

    for h in heights:
        rp, c = best[h]
        cb = cheeseman_bennett(h, args.radius)
        coll = f"{c['collective']:13.2f}" if c["collective"] is not None else f"{'--':>13}"
        print(f"{h:7.0f}{h/args.radius:7.2f}{c['watts']:9.1f}{int(rp):10d}"
              f"{coll}{c['watts']/oge_w:9.3f}"
              f"{(f'{cb:.3f}' if cb else 'n/a'):>12}")

    print(f"\nOGE baseline taken at z = {ogeh:.0f} mm (z/R = {ogeh/args.radius:.2f}).")
    print("`vs OGE` is a POWER ratio at constant thrust. The C-B column is a THRUST")
    print("ratio at constant power. They are different quantities. Do not compare them")
    print("directly; C-B is there to tell you the measurement is the right shape.")

    spread = [best[h][0] for h in heights]
    if len(set(spread)) > 1:
        print("\nNote: the best RPM is not the same at every height. That is a real and")
        print("interesting result. Report the whole grid, not just the minimum curve.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
