"""
Helical Gear Pair Generator for Autodesk Fusion (3.5:1 ratio, finished parts)
-----------------------------------------------------------------------------
Replacement for the 3:1 pair in 3-to-1_current_helical.step.

Held identical to the 3:1 STEP:
  * axle-to-axle (center) distance ........ 31.87997 mm
  * face width / every axial height ....... measured from the STEP
  * pinion flange, 4 x 2.5 mm holes on a 20 mm bolt circle, stepped bore,
    radial 2.5 mm hub hole
  * gear top boss, stepped bore, bottom counterbore, bottom pocket,
    cross hole (4.5 spotface / 2.5 clearance / M2.5x0.45 tapped far wall)
  * hands (pinion RH, gear LH), 20 deg normal pressure angle, 20 deg helix

Changed:
  * ratio 3.5:1. Tooth counts are PINION_TEETH and PINION_TEETH * GEAR_RATIO,
    so PINION_TEETH must be even.
    The module is no longer an input. It is derived from the fixed center
    distance, so changing PINION_TEETH re-sizes the teeth, never the axles.
  * pinion hub diameter follows the new (smaller) pinion root so the larger
    gear clears it.
  * teeth are lofted through LOFT_SECTIONS stations instead of two. The
    two-section loft in the 3:1 script made straight-line teeth that sag
    toward the axis at mid face (0.20 mm on the old pinion tip).

  * tooth roots carry a fillet (ROOT_FILLET x normal module) and the pinion
    tip corners a small radius (PINION_TIP_BREAK). Both are drawn in the
    transverse tooth profile, so they run the full face width.

Each part is built in its own component with its axis on local Z and the
bottom of the teeth at local Z = 0, then placed. With PLACE_LIKE_STEP = True
the two occurrences land exactly where the 3:1 parts sit in the STEP
(gear axis on world Y through the origin, pinion axis at X = -31.87997).

Run via: Utilities > Add-Ins > Scripts and Add-Ins > create/paste this script.
All user parameters are mm / degrees.
"""

import adsk.core, adsk.fusion, traceback, math

# ----------------------- GEAR PARAMETERS (mm / degrees) -----------------------
CENTER_DISTANCE = 31.87997   # axle to axle, from the STEP. Do not change.
PINION_TEETH    = 20         # even only. 20 -> 20/70.  18 -> 18/63 (near old tooth size).  16 -> 16/56
GEAR_RATIO      = 3.5        # 3.5:1
PRESSURE_ANGLE  = 20.0       # normal pressure angle, deg
HELIX_ANGLE     = 20.0       # helix angle, deg (pinion RH, gear LH)
FACE_WIDTH      = 9.36168    # mm, from the STEP
BACKLASH        = 0.0        # circumferential backlash per gear, mm (0 = as 3:1 script)
INVOLUTE_PTS    = 14         # points sampled along each involute flank
LOFT_SECTIONS   = 9          # tooth sections along the face (2 = old behaviour)
ROOT_FILLET     = 0.2        # root fillet radius, x normal module, both gears (0 = sharp)
PINION_TIP_BREAK = 0.05      # mm radius on the pinion tooth tip corners (0 = sharp)
GEAR_TIP_BREAK   = 0.0       # mm radius on the gear tooth tip corners (0 = sharp)
PLACE_LIKE_STEP = True       # True: same world position/orientation as the STEP

# ----------------------- PINION FEATURES (from the STEP) ----------------------
# Z values are measured from the bottom face of the teeth (Z = 0), up = +.
P_FLANGE_R        = 13.310036
P_FLANGE_Z_BOT    = -12.12906
P_FLANGE_Z_TOP    = -10.12906
P_HUB_BELOW_ROOT  = 0.496028   # hub radius = pinion root radius - this (as in STEP)
P_HUB_FILLET      = 0.2        # fillet at both ends of the hub
P_BORE_SMALL_R    = 2.05       # from flange bottom up to P_BORE_STEP_Z
P_BORE_STEP_Z     = -7.12906
P_BORE_LARGE_R    = 3.0        # from the step up through the teeth
P_BOLT_CIRCLE_R   = 10.0
P_BOLT_HOLE_R     = 1.25
P_BOLT_COUNT      = 4
P_BOLT_START_DEG  = 45.0       # relative to the radial hub hole
P_CROSS_HOLE_R    = 1.25       # radial hub hole, one wall only
P_CROSS_HOLE_Z    = -3.30751
P_CLOCK_DEG       = -80.79     # where the radial hub hole points in the STEP

# ------------------------ GEAR FEATURES (from the STEP) -----------------------
G_BOSS_R          = 9.5
G_BOSS_Z_TOP      = 16.12373
G_BORE_R          = 2.995737   # through the tooth zone
G_BORE_BOSS_R     = 3.103879   # through the top boss
G_CBORE_R         = 9.5        # bottom counterbore
G_CBORE_DEPTH     = 0.5
G_POCKET_R_IN     = 11.770971  # bottom annular pocket
G_POCKET_R_OUT    = 19.734774  # raise this to thin the rim on the bigger gear
G_POCKET_DEPTH    = 4.901
G_POCKET_FILLET   = 1.0        # two floor fillets + round on the outer mouth edge
G_XHOLE_Z         = 12.47396   # cross hole through the boss, along -X .. +X
G_XHOLE_SPOT_R    = 2.25       # spotface, entry side (-X)
G_XHOLE_SPOT_X    = -8.5039    # X of the spotface floor
G_XHOLE_CLEAR_R   = 1.25       # clearance hole, entry wall
G_XHOLE_TAP_R     = 1.03775    # M2.5x0.45 minor radius, far wall (+X)
G_THREAD          = ('ISO Metric profile', 'M2.5x0.45', '6H')

# World placement of the bottom-of-teeth plane in the STEP (gear axis = world Y)
STEP_TEETH_BASE_Y = 8.94156
# ------------------------------------------------------------------------------

MM = 0.1        # mm -> cm (Fusion API internal units)
S45 = math.sqrt(0.5)


# ------------------------------- pure geometry --------------------------------

def gear_geometry():
    """Transverse system derived from the fixed center distance."""
    N1 = int(PINION_TEETH)
    N2 = int(PINION_TEETH * GEAR_RATIO)
    beta    = math.radians(HELIX_ANGLE)
    alpha_n = math.radians(PRESSURE_ANGLE)
    mt      = 2.0 * CENTER_DISTANCE * MM / (N1 + N2)      # transverse module
    mn      = mt * math.cos(beta)                         # normal module
    alpha_t = math.atan(math.tan(alpha_n) / math.cos(beta))
    return dict(N1=N1, N2=N2, mn=mn, mt=mt, alpha_t=alpha_t, beta=beta,
                fw=FACE_WIDTH * MM, backlash=BACKLASH * MM)


def gear_radii(N, geom):
    r  = geom['mt'] * N / 2.0
    return dict(r=r,
                rb=r * math.cos(geom['alpha_t']),
                ra=r + geom['mn'],                  # addendum 1.00 mn
                rf=r - 1.25 * geom['mn'],           # dedendum 1.25 mn
                r_close=r - 1.30 * geom['mn'])      # closure just inside root cyl


def _flank_angle(rr, rb, theta0):
    """Angle of flank A at radius rr (radial line below the base circle)."""
    if rr <= rb:
        return theta0
    t = math.sqrt((rr / rb) ** 2 - 1.0)
    return theta0 + t - math.atan(t)


def _tangent_circle(rc, rho, side, rb, theta0, r_lo, r_hi):
    """Circle of radius rho, center at radius rc, tangent to flank A.
    side = -1: center on the tooth-space side (root fillet).
    side = +1: center on the tooth-body side (tip break).
    Returns (center angle, flank radius at the tangent point)."""
    n = 600
    rs = [r_lo + (r_hi - r_lo) * i / n for i in range(n + 1)]
    fl = [(q * math.cos(_flank_angle(q, rb, theta0)),
           q * math.sin(_flank_angle(q, rb, theta0)), q) for q in rs]

    def nearest(phi):
        cx, cy = rc * math.cos(phi), rc * math.sin(phi)
        return min((math.hypot(x - cx, y - cy), q) for x, y, q in fl)

    near = _flank_angle(rc, rb, theta0)          # center on the flank: distance 0
    far  = near + side * 4.0 * rho / rc          # well clear of the flank
    for _ in range(60):
        mid = 0.5 * (near + far)
        if nearest(mid)[0] < rho:
            near = mid
        else:
            far = mid
    phi = 0.5 * (near + far)
    return phi, nearest(phi)[1]


def _arc_points(rc, phi, p_from, p_to, n):
    """n+1 polar points on the short arc about the center (rc, phi), from
    polar point p_from to polar point p_to."""
    cx, cy = rc * math.cos(phi), rc * math.sin(phi)
    ax, ay = p_from[0] * math.cos(p_from[1]) - cx, p_from[0] * math.sin(p_from[1]) - cy
    bx, by = p_to[0] * math.cos(p_to[1]) - cx, p_to[0] * math.sin(p_to[1]) - cy
    rad = 0.5 * (math.hypot(ax, ay) + math.hypot(bx, by))
    a0 = math.atan2(ay, ax)
    da = math.atan2(ax * by - ay * bx, ax * bx + ay * by)
    out = []
    for i in range(n + 1):
        a = a0 + da * i / n
        x, y = cx + rad * math.cos(a), cy + rad * math.sin(a)
        out.append((math.hypot(x, y), math.atan2(y, x)))
    return out


def tooth_flanks(N, rad, alpha_t, backlash_cm, root_fillet_cm=0.0, tip_break_cm=0.0):
    """Polar points (radius, angle) of flank A (root -> tip) and flank B
    (tip -> root) of one tooth centered on angle 0.

    Flank A runs from the root circle (rf) to the tip circle (ra): root
    fillet, involute (radial below the base circle), tip break."""
    r, rb, ra, rf = rad['r'], rad['rb'], rad['ra'], rad['rf']
    inv_at = math.tan(alpha_t) - alpha_t
    half   = math.pi / (2.0 * N) - backlash_cm / (2.0 * r)
    theta0 = -(half + inv_at)

    # Root fillet: tangent to the root circle and to the flank
    # The fillet is seated 4% of its radius below the root circle (about 5
    # microns). It then crosses the root cylinder at ~16 deg instead of meeting
    # it exactly tangent, which is what solid joins handle badly.
    r_lo, head = rf, []
    if root_fillet_cm > 1e-9:
        rho = root_fillet_cm
        rs = rf - 0.04 * rho
        phi, r_lo = _tangent_circle(rs + rho, rho, -1.0, rb, theta0, rs, rs + 3.0 * rho)
        if phi <= -math.pi / N:
            raise RuntimeError('ROOT_FILLET is too large for the {}T tooth space.'.format(N))
        head = _arc_points(rs + rho, phi, (rs, phi),
                           (r_lo, _flank_angle(r_lo, rb, theta0)), 8)

    # Tip break: tangent to the flank and to the tip circle
    r_hi, tail = ra, []
    if tip_break_cm > 1e-9:
        rho = tip_break_cm
        phi, r_hi = _tangent_circle(ra - rho, rho, +1.0, rb, theta0, ra - 3.0 * rho, ra)
        if phi >= 0.0:
            raise RuntimeError('Tip break is too large for the {}T tooth tip.'.format(N))
        tail = _arc_points(ra - rho, phi, (r_hi, _flank_angle(r_hi, rb, theta0)),
                           (ra, phi), 5)

    # Flank between the two tangent points. Sampled evenly in roll angle above
    # the base circle, plus the radial run below it.
    mid = []
    if r_lo < rb:
        k = 3
        for i in range(k):
            q = r_lo + (min(rb, r_hi) - r_lo) * i / k
            mid.append((q, theta0))
    t0 = math.sqrt(max((max(r_lo, rb) / rb) ** 2 - 1.0, 0.0))
    t1 = math.sqrt((r_hi / rb) ** 2 - 1.0)
    for i in range(INVOLUTE_PTS + 1):
        t = t0 + (t1 - t0) * i / INVOLUTE_PTS
        mid.append((rb * math.hypot(1.0, t), theta0 + t - math.atan(t)))

    flankA = (head[:-1] if head else []) + mid + (tail[1:] if tail else [])
    flankB = [(rr, -th) for (rr, th) in reversed(flankA)]
    return flankA, flankB


# ------------------------------ Fusion helpers --------------------------------

def draw_tooth(sketch, flankA, flankB, rot, r_close):
    """One closed tooth profile in `sketch`, tooth centered on angle `rot`.
    The flanks start on the root circle; two short radial lines carry the
    profile down to r_close so the tooth overlaps the root cylinder."""
    def pt(rr, th):
        th += rot
        return adsk.core.Point3D.create(rr * math.cos(th), rr * math.sin(th), 0)

    curves = sketch.sketchCurves
    center = adsk.core.Point3D.create(0, 0, 0)

    def spline(pts):
        col = adsk.core.ObjectCollection.create()
        for rr, th in pts:
            col.add(pt(rr, th))
        return curves.sketchFittedSplines.add(col)

    rootA, tipA = flankA[0], flankA[-1]
    tipB, rootB = flankB[0], flankB[-1]
    curves.sketchLines.addByTwoPoints(pt(r_close, rootA[1]), pt(*rootA))
    spline(flankA)
    curves.sketchArcs.addByCenterStartSweep(center, pt(*tipA), tipB[1] - tipA[1])
    spline(flankB)
    curves.sketchLines.addByTwoPoints(pt(*rootB), pt(r_close, rootB[1]))
    curves.sketchArcs.addByCenterStartSweep(
        center, pt(r_close, rootB[1]), rootA[1] - rootB[1])


def offset_plane(comp, z):
    """Construction plane parallel to XY at height z (cm)."""
    if abs(z) < 1e-9:
        return comp.xYConstructionPlane
    pin = comp.constructionPlanes.createInput()
    pin.setByOffset(comp.xYConstructionPlane, adsk.core.ValueInput.createByReal(z))
    return comp.constructionPlanes.add(pin)


def build_teeth(comp, N, hand, phase, geom, tip_break_cm=0.0, make_core=True):
    """Root cylinder plus N helical teeth, Z = 0 .. face width.
    hand: +1 = RH, -1 = LH.  phase: angle of a tooth center at Z = 0.
    make_core=False: the root cylinder already exists, only add the teeth."""
    rad = gear_radii(N, geom)
    fw = geom['fw']
    twist = hand * fw * math.tan(geom['beta']) / rad['r']
    feats = comp.features
    origin = adsk.core.Point3D.create(0, 0, 0)

    # Root cylinder
    if make_core:
        sk_cyl = comp.sketches.add(comp.xYConstructionPlane)
        sk_cyl.sketchCurves.sketchCircles.addByCenterRadius(origin, rad['rf'])
        ext_in = feats.extrudeFeatures.createInput(
            sk_cyl.profiles.item(0), adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        ext_in.setDistanceExtent(False, adsk.core.ValueInput.createByReal(fw))
        feats.extrudeFeatures.add(ext_in)

    # One tooth, lofted through several stations so it follows a true helix
    flankA, flankB = tooth_flanks(N, rad, geom['alpha_t'], geom['backlash'],
                                  ROOT_FILLET * geom['mn'], tip_break_cm)
    n_sec = max(2, int(LOFT_SECTIONS))
    loft_in = feats.loftFeatures.createInput(adsk.fusion.FeatureOperations.JoinFeatureOperation)
    for k in range(n_sec):
        f = k / (n_sec - 1.0)
        sk = comp.sketches.add(offset_plane(comp, fw * f))
        draw_tooth(sk, flankA, flankB, phase + twist * f, rad['r_close'])
        loft_in.loftSections.add(sk.profiles.item(0))
    loft_in.isSolid = True
    loft = feats.loftFeatures.add(loft_in)

    # Pattern the tooth
    coll = adsk.core.ObjectCollection.create()
    coll.add(loft)
    pat_in = feats.circularPatternFeatures.createInput(coll, comp.zConstructionAxis)
    pat_in.quantity    = adsk.core.ValueInput.createByString(str(N))
    pat_in.totalAngle  = adsk.core.ValueInput.createByString('360 deg')
    pat_in.isSymmetric = False
    feats.circularPatternFeatures.add(pat_in)
    return rad


def _near(sp, p3d):
    g = sp.geometry
    return math.hypot(math.hypot(g.x - p3d.x, g.y - p3d.y), g.z - p3d.z)


def only_this_body(feature_input, body):
    """Limit a cut/join to one body. Both parts are built at the origin before
    being placed, so without this a cut on one part can also cut the other."""
    if body is None:
        return
    try:
        feature_input.participantBodies = [body]
    except:
        pass


def revolve_xz(comp, path, operation, about_first_line=False, body=None):
    """Revolve a closed profile drawn on the XZ plane.

    path: [(x, z), seg, seg, ...] in cm, model coordinates. Each seg is
      ('L', (x, z))                      line to the point
      ('A', (xm, zm), (x, z))            arc through the mid point to the point
    The path is closed back to its first point with a line. The second entry
    must be a line. Axis = component Z axis, or (about_first_line) the first
    line of the path, which is how the cross holes are made."""
    sk = comp.sketches.add(comp.xZConstructionPlane)
    lines = sk.sketchCurves.sketchLines
    arcs  = sk.sketchCurves.sketchArcs

    def P(xz):
        return sk.modelToSketchSpace(adsk.core.Point3D.create(xz[0], 0, xz[1]))

    prev = P(path[0])
    first_sp = None
    first_line = None
    for seg in path[1:]:
        if seg[0] == 'L':
            ln = lines.addByTwoPoints(prev, P(seg[1]))
            if first_line is None:
                first_line = ln
                first_sp = ln.startSketchPoint
            prev = ln.endSketchPoint
        else:
            end = P(seg[2])
            arc = arcs.addByThreePoints(prev, P(seg[1]), end)
            a, b = arc.startSketchPoint, arc.endSketchPoint
            prev = a if _near(a, end) < _near(b, end) else b
    lines.addByTwoPoints(prev, first_sp)

    axis = first_line if about_first_line else comp.zConstructionAxis
    revs = comp.features.revolveFeatures
    rin = revs.createInput(sk.profiles.item(0), axis, operation)
    rin.setAngleExtent(False, adsk.core.ValueInput.createByString('360 deg'))
    only_this_body(rin, body)
    return revs.add(rin)


def add_cosmetic_thread(comp, feature, radius_cm):
    """Cosmetic thread on the cylindrical face of `feature` with this radius.
    Returns True on success. Never raises."""
    try:
        face = None
        for f in feature.faces:
            g = f.geometry
            if g.surfaceType == adsk.core.SurfaceTypes.CylinderSurfaceType \
                    and abs(g.radius - radius_cm) < 1e-5:
                face = f
                break
        if face is None:
            return False
        threads = comp.features.threadFeatures
        info = threads.createThreadInfo(True, G_THREAD[0], G_THREAD[1], G_THREAD[2])
        try:
            faces = adsk.core.ObjectCollection.create()
            faces.add(face)
            tin = threads.createInput(faces, info)
        except:
            tin = threads.createInput(face, info)
        tin.isFullLength = True
        threads.add(tin)
        return True
    except:
        return False


# --------------------------------- the parts ----------------------------------

def build_pinion(root, geom, phase):
    N = geom['N1']
    occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    comp = occ.component
    comp.name = 'Pinion_Wide Base_{}T_RH_Helical'.format(N)
    Join = adsk.fusion.FeatureOperations.JoinFeatureOperation
    Cut  = adsk.fusion.FeatureOperations.CutFeatureOperation

    New  = adsk.fusion.FeatureOperations.NewBodyFeatureOperation

    rad = gear_radii(N, geom)
    fw  = geom['fw']
    rf  = rad['rf']

    hub = rf - P_HUB_BELOW_ROOT * MM
    fil = P_HUB_FILLET * MM
    zb, zt = P_FLANGE_Z_BOT * MM, P_FLANGE_Z_TOP * MM
    R = P_FLANGE_R * MM
    if hub - P_BORE_LARGE_R * MM < 1.0 * MM:
        raise RuntimeError('Pinion hub wall under 1 mm. Use more pinion teeth '
                           'or a smaller P_HUB_BELOW_ROOT.')
    if hub + fil > rf:
        raise RuntimeError('Pinion hub plus its fillet is larger than the tooth root.')

    # Flange + hub (with its 0.2 fillets) + root cylinder as ONE solid, so the
    # toothed section and the hub cannot come out as separate bodies.
    revolve_xz(comp, [
        (0, zb),
        ('L', (R, zb)),
        ('L', (R, zt)),
        ('L', (hub + fil, zt)),
        ('A', (hub + fil - fil * S45, zt + fil - fil * S45), (hub, zt + fil)),
        ('L', (hub, -fil)),
        ('A', (hub + fil - fil * S45, -fil + fil * S45), (hub + fil, 0)),
        ('L', (rf, 0)),
        ('L', (rf, fw)),
        ('L', (0, fw)),
    ], New)

    # Teeth, joined onto that solid
    build_teeth(comp, N, +1.0, phase, geom, PINION_TIP_BREAK * MM, make_core=False)
    body = comp.bRepBodies.item(0)

    # Stepped bore
    e = 0.5 * MM
    rs, rl, zs = P_BORE_SMALL_R * MM, P_BORE_LARGE_R * MM, P_BORE_STEP_Z * MM
    revolve_xz(comp, [
        (0, zb - e),
        ('L', (rs, zb - e)),
        ('L', (rs, zs)),
        ('L', (rl, zs)),
        ('L', (rl, fw + e)),
        ('L', (0, fw + e)),
    ], Cut, body=body)

    # Flange bolt holes: sketch at mid flange, cut symmetric so direction is moot
    sk = comp.sketches.add(offset_plane(comp, 0.5 * (zb + zt)))
    for k in range(P_BOLT_COUNT):
        a = math.radians(P_BOLT_START_DEG) + 2.0 * math.pi * k / P_BOLT_COUNT
        c = sk.modelToSketchSpace(adsk.core.Point3D.create(
            P_BOLT_CIRCLE_R * MM * math.cos(a), P_BOLT_CIRCLE_R * MM * math.sin(a),
            0.5 * (zb + zt)))
        sk.sketchCurves.sketchCircles.addByCenterRadius(c, P_BOLT_HOLE_R * MM)
    profs = adsk.core.ObjectCollection.create()
    for i in range(sk.profiles.count):
        profs.add(sk.profiles.item(i))
    ex_in = comp.features.extrudeFeatures.createInput(profs, Cut)
    ex_in.setSymmetricExtent(
        adsk.core.ValueInput.createByReal((zt - zb) + 0.6 * MM), True)
    only_this_body(ex_in, body)
    comp.features.extrudeFeatures.add(ex_in)

    # Radial hub hole along local +X, bore to outside, one wall only
    zc, rc = P_CROSS_HOLE_Z * MM, P_CROSS_HOLE_R * MM
    x0, x1 = 0.5 * rl, hub + 1.0 * MM
    revolve_xz(comp, [
        (x0, zc),
        ('L', (x1, zc)),
        ('L', (x1, zc + rc)),
        ('L', (x0, zc + rc)),
    ], Cut, about_first_line=True, body=body)

    return occ, rad, hub


def build_gear(root, geom, phase):
    N = geom['N2']
    occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    comp = occ.component
    comp.name = 'Gear_{}T_LH_Helical'.format(N)
    Join = adsk.fusion.FeatureOperations.JoinFeatureOperation
    Cut  = adsk.fusion.FeatureOperations.CutFeatureOperation

    New  = adsk.fusion.FeatureOperations.NewBodyFeatureOperation

    rad = gear_radii(N, geom)
    fw  = geom['fw']
    rf  = rad['rf']

    Rb, ztop = G_BOSS_R * MM, G_BOSS_Z_TOP * MM
    rc, dc = G_CBORE_R * MM, G_CBORE_DEPTH * MM
    r1, r2 = G_BORE_R * MM, G_BORE_BOSS_R * MM
    ri, ro = G_POCKET_R_IN * MM, G_POCKET_R_OUT * MM
    d, q = G_POCKET_DEPTH * MM, G_POCKET_FILLET * MM
    if ro + q > rf - 1.0 * MM:
        raise RuntimeError('G_POCKET_R_OUT leaves under 1 mm of rim.')

    # Root cylinder, top boss, stepped bore, bottom counterbore and bottom
    # pocket (with its three 1 mm radii) as ONE revolved solid. Nothing is cut
    # afterwards along the axis, so no cut can reach the pinion, which sits at
    # the same origin until both parts are placed.
    revolve_xz(comp, [
        (r1, dc),
        ('L', (rc, dc)),                                                 # counterbore floor
        ('L', (rc, 0)),
        ('L', (ri, 0)),
        ('L', (ri, d - q)),
        ('A', (ri + q - q * S45, d - q + q * S45), (ri + q, d)),         # inner floor fillet
        ('L', (ro - q, d)),
        ('A', (ro - q + q * S45, d - q + q * S45), (ro, d - q)),         # outer floor fillet
        ('L', (ro, q)),
        ('A', (ro + q - q * S45, q - q * S45), (ro + q, 0)),             # mouth round
        ('L', (rf, 0)),
        ('L', (rf, fw)),
        ('L', (Rb, fw)),
        ('L', (Rb, ztop)),
        ('L', (r2, ztop)),
        ('L', (r2, fw)),
        ('L', (r1, fw)),
    ], New)

    # Teeth, joined onto that solid
    build_teeth(comp, N, -1.0, phase, geom, GEAR_TIP_BREAK * MM, make_core=False)
    body = comp.bRepBodies.item(0)

    # Cross hole through the boss. Entry side (-X): spotface + clearance.
    zc = G_XHOLE_Z * MM
    xs = G_XHOLE_SPOT_X * MM
    xo = Rb + 1.0 * MM
    xi = 0.5 * r2
    revolve_xz(comp, [
        (-xo, zc),
        ('L', (-xi, zc)),
        ('L', (-xi, zc + G_XHOLE_CLEAR_R * MM)),
        ('L', (xs, zc + G_XHOLE_CLEAR_R * MM)),
        ('L', (xs, zc + G_XHOLE_SPOT_R * MM)),
        ('L', (-xo, zc + G_XHOLE_SPOT_R * MM)),
    ], Cut, about_first_line=True, body=body)
    # Far wall (+X): tap drill, then cosmetic M2.5x0.45
    tap = revolve_xz(comp, [
        (xi, zc),
        ('L', (xo, zc)),
        ('L', (xo, zc + G_XHOLE_TAP_R * MM)),
        ('L', (xi, zc + G_XHOLE_TAP_R * MM)),
    ], Cut, about_first_line=True, body=body)
    threaded = add_cosmetic_thread(comp, tap, G_XHOLE_TAP_R * MM)

    return occ, rad, threaded


def placement(clock, tx):
    """Occurrence transform. Component: axis = local Z, teeth bottom at Z = 0,
    rotated `clock` about its own axis, axis located at X = tx."""
    c, s = math.cos(clock), math.sin(clock)
    m = adsk.core.Matrix3D.create()
    if PLACE_LIKE_STEP:
        # local X -> world X, local Y -> world -Z, local Z -> world +Y
        m.setWithArray([c, -s, 0, tx,
                        0,  0, 1, STEP_TEETH_BASE_Y * MM,
                        -s, -c, 0, 0,
                        0,  0, 0, 1])
    else:
        m.setWithArray([c, -s, 0, tx,
                        s,  c, 0, 0,
                        0,  0, 1, 0,
                        0,  0, 0, 1])
    return m


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui  = app.userInterface

        geom = gear_geometry()
        N1, N2 = geom['N1'], geom['N2']
        if abs(N2 - PINION_TEETH * GEAR_RATIO) > 1e-9:
            raise RuntimeError('PINION_TEETH * GEAR_RATIO must be a whole number '
                               '(use an even PINION_TEETH for 3.5:1).')

        app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        root   = design.rootComponent

        # Mesh phase. In the placed assembly the gear is on the pinion's +X side.
        # Pinion: a tooth on the line of centers at Z = 0. Its component is built
        # with the hub hole on local +X and then clocked, so undo the clock here.
        clock = math.radians(P_CLOCK_DEG)
        pin_phase  = -clock
        # Gear: a tooth space pointing at the pinion (-X) at Z = 0.
        gear_phase = math.pi + math.pi / N2

        occ1, rad1, hub = build_pinion(root, geom, pin_phase)
        # Hide the finished pinion while the gear is built on the same origin
        try:
            occ1.isLightBulbOn = False
        except:
            pass
        occ2, rad2, threaded = build_gear(root, geom, gear_phase)
        try:
            occ1.isLightBulbOn = True
        except:
            pass

        for occ, m in ((occ1, placement(clock, -CENTER_DISTANCE * MM)),
                       (occ2, placement(0.0, 0.0))):
            try:
                occ.transform2 = m
            except:
                occ.transform = m

        app.activeViewport.fit()
        ui.messageBox(
            'Helical gear pair created.\n\n'
            'Ratio: {}:1  ({}T / {}T)\n'
            'Center distance: {:.5f} mm (held)\n'
            'Normal module: {:.5f} mm   Transverse: {:.5f} mm\n'
            'Helix: {} deg (pinion RH / gear LH)   Face: {} mm\n\n'
            'Pinion  pitch dia {:.3f}  OD {:.3f}  root dia {:.3f}  hub dia {:.3f}\n'
            'Gear    pitch dia {:.3f}  OD {:.3f}  root dia {:.3f}\n\n'
            'Root fillet {:.3f} mm   Tip break: pinion {} mm, gear {} mm\n\n'
            'M2.5x0.45 cosmetic thread: {}'.format(
                GEAR_RATIO, N2, N1, CENTER_DISTANCE,
                geom['mn'] / MM, geom['mt'] / MM, HELIX_ANGLE, FACE_WIDTH,
                2 * rad1['r'] / MM, 2 * rad1['ra'] / MM, 2 * rad1['rf'] / MM, 2 * hub / MM,
                2 * rad2['r'] / MM, 2 * rad2['ra'] / MM, 2 * rad2['rf'] / MM,
                ROOT_FILLET * geom['mn'] / MM, PINION_TIP_BREAK, GEAR_TIP_BREAK,
                'added' if threaded else
                'NOT added (hole is at tap-drill size 2.0755 mm, add the thread by hand)'))

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
