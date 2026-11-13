"""
Helical Gear Pair Generator for Autodesk Fusion (3:1 ratio)
-----------------------------------------------------------
Creates two solid components in a new design:
  * Pinion  (right-hand helix, N teeth)
  * Gear    (left-hand helix, 3N teeth)
positioned at the correct center distance and phase-rotated so the
teeth mesh with zero backlash.

Method: true involute tooth profile (transverse plane), lofted between
a bottom sketch and a top sketch rotated by the helix twist angle,
then circular-patterned around the root cylinder.

Run via: Utilities > Add-Ins > Scripts and Add-Ins > create/paste this script.

All user parameters are in mm / degrees. (Fusion's API works in cm
internally; conversion is handled below.)
"""

import adsk.core, adsk.fusion, traceback, math

# ----------------------- USER PARAMETERS (mm / degrees) -----------------------
NORMAL_MODULE   = 2.0     # normal module, mm
PINION_TEETH    = 20      # gear teeth = PINION_TEETH * GEAR_RATIO
GEAR_RATIO      = 3       # 3:1
PRESSURE_ANGLE  = 20.0    # normal pressure angle, deg
HELIX_ANGLE     = 20.0    # helix angle, deg (pinion RH, gear LH)
FACE_WIDTH      = 25.0    # mm
PINION_BORE_DIA = 8.0     # mm, 0 = no bore
GEAR_BORE_DIA   = 16.0    # mm, 0 = no bore
BACKLASH        = 0.0     # circumferential backlash, mm (0 = perfect mesh)
INVOLUTE_PTS    = 14      # points sampled along each involute flank
# ------------------------------------------------------------------------------

MM = 0.1  # mm -> cm (Fusion API internal units)


def draw_tooth(sketch, N, r, rb, ra, r_close, alpha_t, rot, backlash_cm):
    """Draw one closed tooth profile (two involute flanks + tip arc + root
    closure arc) in the given sketch, with the tooth centered on angle `rot`."""
    inv_at = math.tan(alpha_t) - alpha_t              # involute function
    half   = math.pi / (2.0 * N) - backlash_cm / (2.0 * r)  # half tooth thickness angle at pitch circle
    theta0 = -(half + inv_at)                          # base angle where flank-A involute starts

    r_start = max(rb, r_close)
    t0 = math.sqrt(max((r_start / rb) ** 2 - 1.0, 0.0))
    t1 = math.sqrt((ra / rb) ** 2 - 1.0)

    # Flank A (negative-angle side), root -> tip, CCW involute
    flankA = []
    if rb > r_close + 1e-9:
        flankA.append((r_close, theta0))               # short radial run below base circle
    for i in range(INVOLUTE_PTS + 1):
        t = t0 + (t1 - t0) * i / INVOLUTE_PTS
        flankA.append((rb * math.hypot(1.0, t), theta0 + t - math.atan(t)))

    # Flank B is the mirror of A about the tooth centerline, traversed tip -> root
    flankB = [(rr, -th) for (rr, th) in reversed(flankA)]

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

    spline(flankA)
    tipA, tipB = flankA[-1], flankB[0]
    curves.sketchArcs.addByCenterStartSweep(center, pt(*tipA), tipB[1] - tipA[1])   # tip arc (CCW)
    spline(flankB)
    rootB, rootA = flankB[-1], flankA[0]
    curves.sketchArcs.addByCenterStartSweep(center, pt(*rootB), rootA[1] - rootB[1])  # root closure (CW)


def build_gear(root, name, N, hand, bore_dia, geom):
    """Build one helical gear in its own component. hand: +1 = RH, -1 = LH."""
    occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    comp = occ.component
    comp.name = name

    mn, mt, alpha_t, beta, fw = geom['mn'], geom['mt'], geom['alpha_t'], geom['beta'], geom['fw']
    r  = mt * N / 2.0            # pitch radius (transverse)
    rb = r * math.cos(alpha_t)   # base radius
    ra = r + mn                  # tip radius (addendum = 1.0 * mn)
    rf = r - 1.25 * mn           # root radius (dedendum = 1.25 * mn)
    r_close = rf - 0.05 * mn     # tooth closure slightly inside root cyl (clean boolean)
    twist = hand * fw * math.tan(beta) / r   # angular twist across face width

    feats    = comp.features
    sketches = comp.sketches
    origin   = adsk.core.Point3D.create(0, 0, 0)

    # 1) Root cylinder
    sk_cyl = sketches.add(comp.xYConstructionPlane)
    sk_cyl.sketchCurves.sketchCircles.addByCenterRadius(origin, rf)
    ext_in = feats.extrudeFeatures.createInput(
        sk_cyl.profiles.item(0), adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    ext_in.setDistanceExtent(False, adsk.core.ValueInput.createByReal(fw))
    feats.extrudeFeatures.add(ext_in)

    # 2) Tooth profile sketches: bottom (z=0) and top (z=fw, rotated by twist)
    sk_bot = sketches.add(comp.xYConstructionPlane)
    draw_tooth(sk_bot, N, r, rb, ra, r_close, alpha_t, 0.0, geom['backlash'])

    plane_in = comp.constructionPlanes.createInput()
    plane_in.setByOffset(comp.xYConstructionPlane, adsk.core.ValueInput.createByReal(fw))
    top_plane = comp.constructionPlanes.add(plane_in)
    sk_top = sketches.add(top_plane)
    draw_tooth(sk_top, N, r, rb, ra, r_close, alpha_t, twist, geom['backlash'])

    # 3) Loft one helical tooth and join to the cylinder
    loft_in = feats.loftFeatures.createInput(adsk.fusion.FeatureOperations.JoinFeatureOperation)
    loft_in.loftSections.add(sk_bot.profiles.item(0))
    loft_in.loftSections.add(sk_top.profiles.item(0))
    loft_in.isSolid = True
    loft = feats.loftFeatures.add(loft_in)

    # 4) Circular-pattern the tooth around the axis
    coll = adsk.core.ObjectCollection.create()
    coll.add(loft)
    pat_in = feats.circularPatternFeatures.createInput(coll, comp.zConstructionAxis)
    pat_in.quantity   = adsk.core.ValueInput.createByString(str(N))
    pat_in.totalAngle = adsk.core.ValueInput.createByString('360 deg')
    pat_in.isSymmetric = False
    feats.circularPatternFeatures.add(pat_in)

    # 5) Optional center bore
    if bore_dia > 1e-9:
        sk_b = sketches.add(comp.xYConstructionPlane)
        sk_b.sketchCurves.sketchCircles.addByCenterRadius(origin, bore_dia / 2.0)
        cut_in = feats.extrudeFeatures.createInput(
            sk_b.profiles.item(0), adsk.fusion.FeatureOperations.CutFeatureOperation)
        cut_in.setDistanceExtent(False, adsk.core.ValueInput.createByReal(fw))
        feats.extrudeFeatures.add(cut_in)

    return occ


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui  = app.userInterface

        app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        root   = design.rootComponent

        # Derived geometry (transverse system from normal module + helix angle)
        mn      = NORMAL_MODULE * MM
        beta    = math.radians(HELIX_ANGLE)
        alpha_n = math.radians(PRESSURE_ANGLE)
        mt      = mn / math.cos(beta)                          # transverse module
        alpha_t = math.atan(math.tan(alpha_n) / math.cos(beta))  # transverse pressure angle
        N1 = PINION_TEETH
        N2 = PINION_TEETH * GEAR_RATIO
        geom = dict(mn=mn, mt=mt, alpha_t=alpha_t, beta=beta,
                    fw=FACE_WIDTH * MM, backlash=BACKLASH * MM)

        occ1 = build_gear(root, 'Pinion_{}T_RH'.format(N1), N1, +1.0, PINION_BORE_DIA * MM, geom)
        occ2 = build_gear(root, 'Gear_{}T_LH'.format(N2),   N2, -1.0, GEAR_BORE_DIA * MM, geom)

        # Position the gear: correct center distance + half-pitch phase so teeth
        # fall into the pinion's tooth spaces.
        center_dist = mt * (N1 + N2) / 2.0
        phase = (math.pi / N2) if (N2 % 2 == 0) else 0.0
        m = adsk.core.Matrix3D.create()
        m.setToRotation(phase, adsk.core.Vector3D.create(0, 0, 1),
                        adsk.core.Point3D.create(0, 0, 0))
        m.translation = adsk.core.Vector3D.create(center_dist, 0, 0)
        try:
            occ2.transform2 = m
        except:
            occ2.transform = m

        app.activeViewport.fit()
        ui.messageBox(
            'Helical gear pair created.\n\n'
            'Ratio: {}:1  ({}T / {}T)\n'
            'Normal module: {} mm   Helix: {} deg (RH/LH)\n'
            'Transverse module: {:.4f} mm\n'
            'Center distance: {:.4f} mm\n'
            'Face width: {} mm'.format(
                GEAR_RATIO, N2, N1, NORMAL_MODULE, HELIX_ANGLE,
                mt / MM, center_dist / MM, FACE_WIDTH))

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))