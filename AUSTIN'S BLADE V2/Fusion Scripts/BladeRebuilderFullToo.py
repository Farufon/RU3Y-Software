# BladeRebuildFull.py
#
# Autodesk Fusion script. Rebuilds an entire propeller blade, root face to tip,
# as a single precision lofted solid, working directly from the STL.
#
# Nothing else is needed. No CSV, no numpy, no external step. Pure Python, so
# it runs inside Fusion's own interpreter.
#
# INSTALL
#   Fusion > Utilities > ADD-INS > Scripts and Add-Ins > Scripts > green "+"
#   Create a script named BladeRebuildFull, replace its .py with this file.
#   Run it. A file dialog asks for the STL.
#
# HOW IT WORKS
#   1. Parses the STL, ASCII or binary.
#   2. Slices the mesh at spanwise station planes using true plane/triangle
#      intersection. This works everywhere, including regions where the
#      triangulation is irregular, which is why it recovers the root that
#      vertex-ring extraction misses.
#   3. Clocks every section consistently. It seeds at a station out in the
#      airfoil, where the trailing edge is a detectable corner, then walks
#      outboard and inboard, each station taking the point nearest its
#      neighbour's start. That carries a continuous seam into the blunt shank,
#      where there is no corner to find. Inconsistent clocking is what makes a
#      loft fold into itself.
#   4. Resamples each section, clustered at the leading and trailing edges.
#   5. Builds one sketch per station and lofts them into a solid.

import adsk.core
import adsk.fusion
import traceback
import math
import struct
import bisect

# ============================ USER SETTINGS ============================

# Blank prompts with a file dialog.
STL_PATH = ''

# Sections spread evenly across the whole span.
N_STATIONS = 70

# Extra sections packed into the root, where chord and thickness change many
# times faster than they do out along the airfoil. Without these the blend
# gets undersampled and the loft can fold.
ROOT_EXTRA = 30
ROOT_SPAN_FRACTION = 0.12

# Same idea at the tip, where the chord falls away quickly over the last few
# centimetres of span.
TIP_EXTRA = 14
TIP_SPAN_FRACTION = 0.05

# Points fitted around each section. Fusion splines pass exactly through every
# point given, so very high counts produce high-order curves that can wobble.
POINTS_PER_SECTION = 120

# 0 spaces points evenly by arc length. Higher values pack them toward the
# leading and trailing edges, where curvature is highest. 0.35 is a good start.
CLUSTER = 0.35

# Fusion's API works in centimetres internally whatever the document is set to.
#
# This source STL is NOT in millimetres. Its numbers run ten times oversize, so
# a value of 4950 in the file is a real 495 mm. Converting tenths-of-a-mm to
# centimetres is therefore 0.01, not 0.1. Getting this wrong builds a model ten
# times too big, which then has to be scaled by 0.1 by hand after every run.
#
# If a future export is genuinely in millimetres, use 0.1. Centimetres, 1.0.
# Inches, 2.54.
UNIT_SCALE = 0.01

# Two open splines meeting at the trailing edge, preserving the sharp corner.
# False uses one closed spline per section, smooth but blunt at the edge.
SHARP_TE = True

# Slicing exactly on an end face is degenerate, so the first and last planes
# are pulled in by this much, in source units. At the file's ten-times scale
# this is 0.05 mm of real geometry.
END_INSET = 0.5

# Nudges every plane off round numbers. Planes landing exactly on mesh vertices
# emit duplicate on-plane edges, which breaks the loop walk.
NUDGE = 0.013

# Faster, at the cost of a parametric history tree.
DIRECT_MODE = True

CLEAN_UP = True

# =======================================================================


def parse_stl(path):
    """Return a list of triangles, each ((x,y,z),(x,y,z),(x,y,z))."""
    with open(path, 'rb') as f:
        head = f.read(5)
        f.seek(0)
        if head[:5] == b'solid':
            text = f.read().decode('utf-8', 'replace')
            tris, cur = [], []
            for line in text.splitlines():
                s = line.strip()
                if s[:6] == 'vertex':
                    p = s.split()
                    cur.append((float(p[1]), float(p[2]), float(p[3])))
                    if len(cur) == 3:
                        tris.append(tuple(cur)); cur = []
            if tris:
                return tris
            f.seek(0)
        f.seek(80)
        n = struct.unpack('<I', f.read(4))[0]
        data = f.read(n * 50)
        tris = []
        for i in range(n):
            v = struct.unpack_from('<12f', data, i * 50)
            tris.append(((v[3], v[4], v[5]),
                         (v[6], v[7], v[8]),
                         (v[9], v[10], v[11])))
        return tris


def station_planes(x0, x1, n_even, n_root, root_frac,
                   n_tip, tip_frac, inset, nudge):
    """Even coverage plus extra density at the root blend and the tip."""
    lo, hi = x0 + inset, x1 - inset
    xs = [lo + (hi - lo) * i / float(n_even - 1) for i in range(n_even)]
    if n_root > 0:
        rhi = lo + (hi - lo) * root_frac
        xs += [lo + (rhi - lo) * i / float(n_root - 1) for i in range(n_root)]
    if n_tip > 0:
        tlo = hi - (hi - lo) * tip_frac
        xs += [tlo + (hi - tlo) * i / float(n_tip - 1) for i in range(n_tip)]
    xs = sorted(set(round(v, 6) for v in xs))
    out, last = [], None
    for v in xs:
        if last is None or v - last > 1e-3:
            out.append(v + nudge); last = v
    return out


def bucket(tris, planes):
    """For each plane, the triangles whose x span crosses it."""
    buckets = [[] for _ in planes]
    for t in tris:
        xa, xb, xc = t[0][0], t[1][0], t[2][0]
        lo = bisect.bisect_left(planes, min(xa, xb, xc))
        hi = bisect.bisect_right(planes, max(xa, xb, xc))
        for j in range(lo, hi):
            buckets[j].append(t)
    return buckets


def slice_plane(tris, xp):
    """Deduplicated cut segments as ((y,z),(y,z)) pairs."""
    segs = set()
    for t in tris:
        d0, d1, d2 = t[0][0] - xp, t[1][0] - xp, t[2][0] - xp
        if (d0 > 0 and d1 > 0 and d2 > 0) or (d0 < 0 and d1 < 0 and d2 < 0):
            continue
        hits = []
        for (a, da), (b, db) in (((t[0], d0), (t[1], d1)),
                                 ((t[1], d1), (t[2], d2)),
                                 ((t[2], d2), (t[0], d0))):
            if da == 0.0:
                hits.append((a[1], a[2]))
            if da * db < 0.0:
                f = da / (da - db)
                hits.append((a[1] + f * (b[1] - a[1]),
                             a[2] + f * (b[2] - a[2])))
        uniq = []
        for p in hits:
            if not any(abs(p[0] - q[0]) < 1e-7 and abs(p[1] - q[1]) < 1e-7
                       for q in uniq):
                uniq.append(p)
        if len(uniq) == 2:
            a = (round(uniq[0][0], 6), round(uniq[0][1], 6))
            b = (round(uniq[1][0], 6), round(uniq[1][1], 6))
            if a != b:
                segs.add((a, b) if a < b else (b, a))
    return segs


def largest_loop(segs):
    """Longest closed chain, plus a count of non degree-2 vertices."""
    adj = {}
    for a, b in segs:
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    branchy = sum(1 for v in adj.values() if len(v) != 2)
    best, seen = None, set()
    for start in adj:
        if start in seen:
            continue
        loop, local = [start], {start}
        prev, cur = None, start
        while True:
            nxt = [n for n in adj[cur] if n != prev]
            if not nxt:
                break
            n = nxt[0]
            if n == start or n in local:
                break
            loop.append(n); local.add(n); prev, cur = cur, n
        seen |= local
        if best is None or len(loop) > len(best):
            best = loop
    return best, branchy


def orient(loop):
    """Force counter-clockwise winding."""
    a = 0.0
    for i in range(len(loop)):
        y0, z0 = loop[i]
        y1, z1 = loop[(i + 1) % len(loop)]
        a += y0 * z1 - y1 * z0
    return loop if a > 0 else loop[::-1]


def sharpest(loop, near=None, window=None, min_turn=45.0):
    """Index of the sharpest corner, optionally within a window of `near`."""
    n = len(loop)
    if near is None:
        idxs = range(n)
    else:
        w = window if window else max(3, n // 12)
        idxs = [(near + k) % n for k in range(-w, w + 1)]
    best, best_turn = near if near is not None else 0, min_turn
    for i in idxs:
        py, pz = loop[(i - 1) % n]
        cy, cz = loop[i]
        ny, nz = loop[(i + 1) % n]
        ay, az = py - cy, pz - cz
        by, bz = ny - cy, nz - cz
        na = math.hypot(ay, az); nb = math.hypot(by, bz)
        if na == 0 or nb == 0:
            continue
        c = max(-1.0, min(1.0, (ay * by + az * bz) / (na * nb)))
        turn = 180.0 - math.degrees(math.acos(c))
        if turn > best_turn:
            best, best_turn = i, turn
    return best


def resample(loop, start, count, cluster):
    """Arc-length resample from `start`, clustered at both chord extremes."""
    n = len(loop)
    lp = [loop[(start + i) % n] for i in range(n)] + [loop[start]]
    seg, s = [], [0.0]
    for i in range(n):
        d = math.hypot(lp[i + 1][0] - lp[i][0], lp[i + 1][1] - lp[i][1])
        seg.append(d); s.append(s[-1] + d)
    total = s[-1]
    out = []
    for k in range(count):
        u = k / float(count)
        t = u - (cluster / (2.0 * math.pi)) * math.sin(4.0 * math.pi * u)
        t = min(max(t, 0.0), 1.0)
        want = t * total
        j = bisect.bisect_right(s, want) - 1
        j = min(max(j, 0), n - 1)
        f = (want - s[j]) / seg[j] if seg[j] > 0 else 0.0
        out.append((lp[j][0] + f * (lp[j + 1][0] - lp[j][0]),
                    lp[j][1] + f * (lp[j + 1][1] - lp[j][1])))
    out[0] = loop[start]
    return out


def farthest(pts, i=0):
    y0, z0 = pts[i]
    best, bd = i, -1.0
    for k, (y, z) in enumerate(pts):
        d = (y - y0) ** 2 + (z - z0) ** 2
        if d > bd:
            best, bd = k, d
    return best


def build_sketch(sk, x, pts, scale, sharp):
    def sp(y, z):
        return sk.modelToSketchSpace(
            adsk.core.Point3D.create(x * scale, y * scale, z * scale))
    splines = sk.sketchCurves.sketchFittedSplines
    le = farthest(pts, 0)
    if le < 2 or le > len(pts) - 3:
        return False
    if sharp:
        up = adsk.core.ObjectCollection.create()
        for y, z in pts[0:le + 1]:
            up.add(sp(y, z))
        splines.add(up)
        lo = adsk.core.ObjectCollection.create()
        for y, z in pts[le:]:
            lo.add(sp(y, z))
        lo.add(sp(pts[0][0], pts[0][1]))
        splines.add(lo)
    else:
        c = adsk.core.ObjectCollection.create()
        for y, z in pts:
            c.add(sp(y, z))
        c.add(sp(pts[0][0], pts[0][1]))
        s = splines.add(c)
        try:
            s.isClosed = True
        except Exception:
            pass
    return True


def best_profile(sk):
    n = sk.profiles.count
    if n == 0:
        return None, 0
    best, ba = None, -1.0
    for i in range(n):
        p = sk.profiles.item(i)
        try:
            a = p.areaProperties(
                adsk.fusion.CalculationAccuracy.LowCalculationAccuracy).area
        except Exception:
            a = 0.0
        if a > ba:
            best, ba = p, a
    return best, n


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            ui.messageBox('Open a Fusion design first, then run this script.')
            return

        path = STL_PATH
        if not path:
            dlg = ui.createFileDialog()
            dlg.title = 'Select the blade STL'
            dlg.filter = 'STL files (*.stl)'
            if dlg.showOpen() != adsk.core.DialogResults.DialogOK:
                return
            path = dlg.filename

        prog = ui.createProgressDialog()
        prog.isBackgroundTranslucent = False
        prog.show('Rebuilding blade', 'Reading the STL', 0, 100, 0)
        adsk.doEvents()

        tris = parse_stl(path)
        if len(tris) < 4:
            prog.hide()
            ui.messageBox('Could not read triangles from that file.')
            return

        xmin = min(min(t[0][0], t[1][0], t[2][0]) for t in tris)
        xmax = max(max(t[0][0], t[1][0], t[2][0]) for t in tris)

        planes = station_planes(xmin, xmax, N_STATIONS,
                                ROOT_EXTRA, ROOT_SPAN_FRACTION,
                                TIP_EXTRA, TIP_SPAN_FRACTION,
                                END_INSET, NUDGE)
        buckets = bucket(tris, planes)

        prog.message = 'Slicing %d sections' % len(planes)
        prog.maximumValue = len(planes)
        adsk.doEvents()

        loops, branch_warn = [], 0
        for j, xp in enumerate(planes):
            if prog.wasCancelled:
                prog.hide(); return
            lp, branchy = largest_loop(slice_plane(buckets[j], xp))
            if branchy:
                branch_warn += 1
            if lp and len(lp) >= 20:
                loops.append((xp, orient(lp)))
            prog.progressValue = j + 1
            adsk.doEvents()

        if len(loops) < 2:
            prog.hide()
            ui.messageBox('Only %d sections could be sliced.' % len(loops))
            return

        # Seed the clocking out in the airfoil, where the trailing edge is a
        # real corner, then propagate both ways.
        seed = int(len(loops) * 0.65)
        starts = [0] * len(loops)
        starts[seed] = sharpest(loops[seed][1])
        for i in range(seed + 1, len(loops)):
            prev = loops[i - 1][1][starts[i - 1]]
            lp = loops[i][1]
            near = min(range(len(lp)),
                       key=lambda k: (lp[k][0] - prev[0]) ** 2
                       + (lp[k][1] - prev[1]) ** 2)
            starts[i] = sharpest(lp, near)
        for i in range(seed - 1, -1, -1):
            prev = loops[i + 1][1][starts[i + 1]]
            lp = loops[i][1]
            near = min(range(len(lp)),
                       key=lambda k: (lp[k][0] - prev[0]) ** 2
                       + (lp[k][1] - prev[1]) ** 2)
            starts[i] = sharpest(lp, near)

        sections = [(x, resample(lp, starts[i], POINTS_PER_SECTION, CLUSTER))
                    for i, (x, lp) in enumerate(loops)]

        if DIRECT_MODE:
            design.designType = adsk.fusion.DesignTypes.DirectDesignType

        root = design.rootComponent
        cplanes = root.constructionPlanes
        sketches = root.sketches
        made_p, made_s, profiles, messy = [], [], [], 0

        prog.message = 'Building %d sketches' % len(sections)
        prog.maximumValue = len(sections)
        prog.progressValue = 0
        adsk.doEvents()

        for i, (x, pts) in enumerate(sections):
            if prog.wasCancelled:
                prog.hide(); return
            pin = cplanes.createInput()
            pin.setByOffset(root.yZConstructionPlane,
                            adsk.core.ValueInput.createByReal(x * UNIT_SCALE))
            pl = cplanes.add(pin)
            pl.isLightBulbOn = False
            made_p.append(pl)

            sk = sketches.add(pl)
            sk.name = 'sec_%03d' % i
            sk.isComputeDeferred = True
            ok = build_sketch(sk, x, pts, UNIT_SCALE, SHARP_TE)
            sk.isComputeDeferred = False
            sk.isLightBulbOn = False
            made_s.append(sk)

            prof, nprof = best_profile(sk)
            if not ok or prof is None:
                prog.hide()
                ui.messageBox('Section %d (x = %.3f) did not close into a '
                              'profile.' % (i, x))
                return
            if nprof > 1:
                messy += 1
            profiles.append(prof)
            prog.progressValue = i + 1
            adsk.doEvents()

        prog.message = 'Lofting %d sections. This is the slow part.' % len(profiles)
        adsk.doEvents()

        lofts = root.features.loftFeatures
        li = lofts.createInput(
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        for p in profiles:
            li.loftSections.add(p)
        li.isSolid = True
        li.isClosed = False

        try:
            loft = lofts.add(li)
        except Exception:
            prog.hide()
            ui.messageBox(
                'The loft failed.\n\n'
                'Sections        : %d\n'
                'Points/section  : %d\n'
                'Split profiles  : %d\n'
                'Branchy slices  : %d\n\n'
                'Raise ROOT_EXTRA or TIP_EXTRA if those regions are '
                'undersampled, or lower POINTS_PER_SECTION if the splines are '
                'wobbling.\n\n%s'
                % (len(profiles), POINTS_PER_SECTION, messy, branch_warn,
                   traceback.format_exc()))
            return

        prog.hide()
        body = loft.bodies.item(0)
        body.name = 'Blade'

        if CLEAN_UP:
            for sk in made_s:
                try:
                    sk.deleteMe()
                except Exception:
                    pass
            for pl in made_p:
                try:
                    pl.deleteMe()
                except Exception:
                    pass

        bbox = body.boundingBox
        bbx = bbox.maxPoint.x - bbox.minPoint.x
        bby = bbox.maxPoint.y - bbox.minPoint.y
        bbz = bbox.maxPoint.z - bbox.minPoint.z
        pp = body.physicalProperties
        ui.messageBox(
            'Blade rebuilt, root face to tip.\n\n'
            'Triangles read   : %d\n'
            'Sections lofted  : %d\n'
            'Points/section   : %d\n'
            'File units span  : %.2f to %.2f  (%.2f wide)\n'
            'BUILT SIZE       : %.2f x %.2f x %.2f mm\n'
            'Trailing edge    : %s\n'
            'Branchy slices   : %d  (want 0)\n'
            'Split profiles   : %d  (want 0)\n'
            'Volume           : %.3f mm^3\n'
            'Surface area     : %.3f mm^2\n'
            'Solid            : %s\n\n'
            'If BUILT SIZE is ten times off, flip UNIT_SCALE between\n'
            '0.01 and 0.1 and run again.\n\n'
            'Export with File > Export > STEP.'
            % (len(tris), len(profiles), POINTS_PER_SECTION,
               sections[0][0], sections[-1][0],
               sections[-1][0] - sections[0][0],
               bbx * 10.0, bby * 10.0, bbz * 10.0,
               'sharp' if SHARP_TE else 'closed spline',
               branch_warn, messy,
               pp.volume * 1000.0, pp.area * 100.0,
               'yes' if body.isSolid else 'NO'))

    except Exception:
        if ui:
            ui.messageBox('Failed:\n%s' % traceback.format_exc())