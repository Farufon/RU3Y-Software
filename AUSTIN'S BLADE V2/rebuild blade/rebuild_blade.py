# rebuild_blade.py
# Autodesk Fusion 360 script.
#
# Rebuilds the propeller/airfoil blade as clean parametric geometry so the
# root junction is well defined and actually fillet-able, which it is not on
# the booleaned STEP import.
#
# What it does, in order:
#   1. Lofts the airfoil skin fresh through section curves sampled from your
#      current solid (data file: blade_rebuild_data.json).
#   2. Builds the mounting block from its outer profile as a clean prism.
#   3. Cuts the holes (VERIFY the HOLES table against your real design).
#   4. Joins block + blade so they weld into one body.
#   5. Fillets the ring where the block meets the blade at the root.
#
# The blade loft deliberately runs a few mm into the block so the join is
# manifold and the fillet has a real intersection ring to roll around. That
# is what kills the 72 degree kink on the low side: the seam now terminates
# inside the block instead of pinching at its face.
#
# HOW TO RUN
#   Utilities tab > Add-Ins > Scripts and Add-Ins > the green +, point it at
#   this .py, then Run. Keep blade_rebuild_data.json in the SAME folder, or
#   set DATA_FILE below to its full path.
#
# This has not been run inside Fusion by me. Expect one or two tweaks,
# most likely the fillet edge band or a section that needs a duplicate
# point removed. Both are called out in comments where they bite.

import adsk.core, adsk.fusion, traceback, json, os, math

# ------------------------------------------------------------------ PARAMETERS
DATA_FILE = ''            # blank = look for blade_rebuild_data.json next to this script

# Units. The JSON is in the blade's native mm (the ~10x-oversize frame you
# import at 0.1). Fusion's internal API unit is cm, hence 0.1. Set
# OVERALL_SCALE = 0.1 as well if you want the rebuild output at true 1/10 size.
MM_TO_CM       = 0.1
OVERALL_SCALE  = 1.0

FILLET_RADIUS_MM     = 1.5   # root junction blend radius, in model mm
JUNCTION_BAND_MM     = 10.0  # grab edges within this X-band of the junction for the fillet
BLADE_BLOCK_OVERLAP  = 4.0   # mm the blade root is pushed into the block for a clean weld

SECTION_STRIDE = 1     # use every Nth captured section (1 = all 46)
POINT_STRIDE   = 2     # thin each section loop by this factor (fewer, cleaner spline points)

DO_HOLES   = True      # set False to skip holes entirely and add them yourself
DO_FILLET  = True
# ---------------------------------------------------------------------------

S = MM_TO_CM * OVERALL_SCALE          # model mm -> Fusion cm
def c(v):  return v * S               # scale a scalar
def P(x, y, z):                       # scaled Point3D
    return adsk.core.Point3D.create(c(x), c(y), c(z))


def load_data():
    path = DATA_FILE
    if not path:
        here = os.path.dirname(os.path.realpath(__file__))
        path = os.path.join(here, 'blade_rebuild_data.json')
    with open(path, 'r') as f:
        return json.load(f)


def clean_loop(loop):
    """Thin the loop and drop near-duplicate consecutive points, then close it."""
    pts = loop[::POINT_STRIDE]
    out = []
    for p in pts:
        if not out or (abs(p[0]-out[-1][0]) + abs(p[1]-out[-1][1]) + abs(p[2]-out[-1][2])) > 1e-4:
            out.append(p)
    # close by repeating the first fit point (Fusion closes the spline on coincident ends)
    if out and (out[0] != out[-1]):
        out.append(out[0])
    return out


def make_section_profile(root, sketches, section):
    """Offset plane at the section X, closed fitted spline, return its profile."""
    x = section['x']
    planes = root.constructionPlanes
    pin = planes.createInput()
    pin.setByOffset(root.yZConstructionPlane,
                    adsk.core.ValueInput.createByReal(c(x)))
    plane = planes.add(pin)

    sk = sketches.add(plane)
    loop = clean_loop(section['loop'])
    coll = adsk.core.ObjectCollection.create()
    for pnt in loop:
        coll.add(sk.modelToSketchSpace(P(pnt[0], pnt[1], pnt[2])))
    sk.sketchCurves.sketchFittedSplines.add(coll)

    if sk.profiles.count == 0:
        # spline did not close into a region; caller handles it
        return None
    # largest-area profile, in case tiny slivers appear
    best = sk.profiles.item(0)
    try:
        ap = best.areaProperties(); ba = ap.area
        for i in range(1, sk.profiles.count):
            a2 = sk.profiles.item(i).areaProperties().area
            if a2 > ba:
                best, ba = sk.profiles.item(i), a2
    except:
        pass
    return best


def loft_blade(root, data):
    sketches = root.sketches
    sections = data['blade']['sections'][::SECTION_STRIDE]
    profiles = []
    missed = []
    for i, sec in enumerate(sections):
        prof = make_section_profile(root, sketches, sec)
        if prof is None:
            missed.append(round(sec['x'], 1))
        else:
            profiles.append(prof)
    if len(profiles) < 2:
        raise RuntimeError('Not enough closed section profiles to loft (got %d).' % len(profiles))

    loft = root.features.loftFeatures
    li = loft.createInput(adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    for prof in profiles:
        li.loftSections.add(prof)
    li.isSolid = True
    feat = loft.add(li)
    return feat.bodies.item(0), missed


def build_block(root, data):
    blk = data['block']
    sections = data['blade']['sections']
    root_x = sections[0]['x']                       # inboard-most blade station
    x_max  = root_x + BLADE_BLOCK_OVERLAP           # push block past blade root -> clean weld
    x_min  = blk['x_min']

    # outer profile lives in the Y-Z plane at some X; draw it on a plane at x_max
    planes = root.constructionPlanes
    pin = planes.createInput()
    pin.setByOffset(root.yZConstructionPlane, adsk.core.ValueInput.createByReal(c(x_max)))
    plane = planes.add(pin)
    sk = root.sketches.add(plane)

    coll = adsk.core.ObjectCollection.create()
    prof_pts = blk['outer_profile_yz'][::2]
    for y, z in prof_pts:
        coll.add(sk.modelToSketchSpace(P(x_max, y, z)))
    if coll.count and prof_pts[0] != prof_pts[-1]:
        coll.add(sk.modelToSketchSpace(P(x_max, prof_pts[0][0], prof_pts[0][1])))
    sk.sketchCurves.sketchFittedSplines.add(coll)
    if sk.profiles.count == 0:
        raise RuntimeError('Block outer profile did not close.')
    prof = sk.profiles.item(0)

    ext = root.features.extrudeFeatures
    ei = ext.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    dist = adsk.core.ValueInput.createByReal(c(x_min - x_max))   # negative -> toward -X
    ei.setDistanceExtent(False, dist)
    feat = ext.add(ei)
    return feat.bodies.item(0)


def cut_holes(root, block_body, data):
    """Cut each hole with a temporary cylinder, orientation-agnostic."""
    tbm = adsk.fusion.TemporaryBRepManager.get()
    holes = data['block'].get('hole_candidates', [])
    combines = root.features.combineFeatures
    for h in holes:
        r = c(h['dia'] / 2.0)
        ax = h['axis_point']; d = h['axis_dir']
        n = math.sqrt(d[0]**2 + d[1]**2 + d[2]**2) or 1.0
        d = [d[0]/n, d[1]/n, d[2]/n]
        L = c(60.0)                                  # long enough to pass fully through
        base = adsk.core.Point3D.create(c(ax[0]) - d[0]*L, c(ax[1]) - d[1]*L, c(ax[2]) - d[2]*L)
        top  = adsk.core.Point3D.create(c(ax[0]) + d[0]*L, c(ax[1]) + d[1]*L, c(ax[2]) + d[2]*L)
        cyl = tbm.createCylinderOrCone(base, r, top, r)

        base_feat = root.features.baseFeatures.add()
        base_feat.startEdit()
        tool = root.bRepBodies.add(cyl, base_feat)
        base_feat.finishEdit()

        tools = adsk.core.ObjectCollection.create(); tools.add(tool)
        ci = combines.createInput(block_body, tools)
        ci.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
        ci.isKeepToolBodies = False
        combines.add(ci)


def join_bodies(root, target, tool):
    combines = root.features.combineFeatures
    tools = adsk.core.ObjectCollection.create(); tools.add(tool)
    ci = combines.createInput(target, tools)
    ci.operation = adsk.fusion.FeatureOperations.JoinFeatureOperation
    ci.isKeepToolBodies = False
    combines.add(ci)
    return target


def fillet_junction(root, body, data):
    """Fillet edges sitting within a band of the junction X. Adjust the band
    or replace with a hand-picked edge selection if it grabs too much/little."""
    jx = c(data['junction_x'])
    band = c(JUNCTION_BAND_MM)
    edges = adsk.core.ObjectCollection.create()
    for e in body.edges:
        bb = e.boundingBox
        cx = 0.5 * (bb.minPoint.x + bb.maxPoint.x)
        if abs(cx - jx) <= band:
            edges.add(e)
    if edges.count == 0:
        return None
    fil = root.features.filletFeatures
    fi = fil.createInput()
    fi.addConstantRadiusEdgeSet(edges, adsk.core.ValueInput.createByReal(c(FILLET_RADIUS_MM)), True)
    try:
        return fil.add(fi)
    except:
        # If the full band fails, the offending edges are usually the thin
        # trailing-edge ones. Retry with a smaller radius or narrow the band.
        return None


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        root = design.rootComponent

        data = load_data()

        blade, missed = loft_blade(root, data)
        block = build_block(root, data)

        if DO_HOLES:
            cut_holes(root, block, data)

        joined = join_bodies(root, blade, block)   # weld block into blade

        filleted = fillet_junction(root, joined, data) if DO_FILLET else None

        msg = 'Blade rebuilt.\n'
        msg += 'Sections lofted: %d\n' % (len(data['blade']['sections'][::SECTION_STRIDE]) - len(missed))
        if missed:
            msg += 'Sections that did not close (add a point or reduce POINT_STRIDE): %s\n' % missed
        msg += 'Holes cut: %s\n' % ('yes' if DO_HOLES else 'skipped')
        msg += 'Junction fillet: %s\n' % ('applied' if filleted else 'not applied (widen/narrow JUNCTION_BAND_MM or hand-pick edges)')
        ui.messageBox(msg)

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
