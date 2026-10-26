#!/usr/bin/env python3
"""
torque_cradle.py - Autodesk Fusion script

Builds a reaction-torque cradle for the nacelle thrust stand.

PRINCIPLE
    The rotor's torque appears as an equal and opposite reaction in the
    nacelle housing. Let the whole upper assembly (nacelle + mount + post +
    S-beam thrust cell) rotate about a vertical axis on two bearings, then
    stop it with an arm pressing on a second load cell. Torque = force x arm.
    Nothing rotates in service; the cradle moves a fraction of a degree.

    Torque is a free vector, so the cradle axis does not have to be collinear
    with the rotor shaft. It only has to be PARALLEL to it (vertical) and
    the two bearings must be spaced far enough apart to take the tipping
    moment from any in-plane rotor force.

    The thrust load path is untouched: the S-beam and everything above it
    ride around with the cradle.

PARTS PRODUCED (each in its own component, one body each)
    1  base_plate      bolts to the bench, carries the tower and the anchor
    2  bearing_tower   separate part so both bearings install from outside
    3  cradle_arm      rotating disc + torque arm, the post bolts on top
    4  cell_anchor     fixed clevis that holds the far end of the load cell
    5  REF_*           bearings, shaft tube and load cell as reference solids
                       (delete before printing; they are there to eyeball fits)

HOW TO RUN
    Fusion > Utilities > Scripts and Add-Ins > Scripts > green + > pick this
    file > Run. It opens a NEW document each run, so it never damages work.

PARAMETRIC NOTE
    Fusion user parameters are created for reference, but the geometry is
    built from the Python values below rather than driven by sketch
    dimensions. That keeps the script readable and its failure modes
    obvious. To change a dimension, edit the value here and re-run. It
    regenerates in a couple of seconds.

UNITS
    All values below are millimetres. The Fusion API works internally in
    centimetres, hence the MM factor.
"""

import math
import traceback

import adsk.core
import adsk.fusion

MM = 0.1  # Fusion internal length unit is cm


# ============================================================== PARAMETERS ==
# --- MEASURE THESE TWO BEFORE THE FIRST RUN --------------------------------
POST_BOLT_PCD = 80.0      # bolt circle on the existing nacelle-mount base
POST_BOLT_N = 4           # number of bolts in that circle
POST_BOLT_DIA = 6.6       # clearance hole, 6.6 = M6 clearance
POST_SPIGOT_DIA = 0.0     # raised register for the post, 0 = none

# --- TORQUE GEOMETRY -------------------------------------------------------
ARM_R = 150.0             # axis to load-cell pin.
#   NOTE: longer arm = LESS force at the cell for the same torque (F = T/r).
#   Pick it so peak torque lands at 60-80 % of cell full scale. For the 5 kg
#   cell that would be about 97 mm. 150 mm is deliberate headroom for the
#   spool-up transient, and it shrinks the relative error in the measured
#   calibration radius.
ARM_W = 25.0              # arm width
ARM_T = 14.0              # arm thickness (this is the stiffness that matters)

# --- LOAD CELL (ATO micro S-type, 5 kg, M6 both ends) ----------------------
CELL_BODY_L = 45.0        # body height between the two stud faces
CELL_BODY_W = 25.0        # body width, for clearance only
CELL_ROD_END = 32.0       # length each rod end adds, stud face to pin centre
CELL_PIN_DIA = 6.6        # pin through the rod end bore
CELL_LEN = CELL_BODY_L + 2 * CELL_ROD_END   # pin centre to pin centre

# --- BEARINGS (6004-2RS: 20 id x 42 od x 12 w) -----------------------------
BRG_ID = 20.0
BRG_OD = 42.0
BRG_W = 12.0
BRG_GAP = 60.0            # clear air between the two bearings
BRG_FIT = 0.10            # add to OD for a printed press fit; tune per printer

# --- SHAFT (20 od x 12 id tube, so the loom can pass down the axis) --------
SHAFT_OD = 20.0
SHAFT_ID = 12.0
SHAFT_FIT = 0.15          # add to bore in the cradle for a bonded slip fit

# --- TOWER -----------------------------------------------------------------
TOWER_WALL = 8.0
TOWER_BORE = 30.0         # middle relief; both bearings seat on this shoulder
TOWER_FLANGE_DIA = 92.0
TOWER_FLANGE_T = 9.0
TOWER_BOLT_PCD = 76.0
TOWER_BOLT_N = 4
TOWER_BOLT_DIA = 4.5      # M4 clearance

# --- BASE PLATE ------------------------------------------------------------
# The anchor sits at (ARM_R, CELL_LEN) = (150, 109) and its foot is
# ANCHOR_FOOT_W x ANCHOR_FOOT_L, so the plate must reach x=172 and y=144
# before any edge margin. 320 x 240 did not; it left the anchor hanging off
# two edges. 400 x 340 is past most print beds: cut this one from 10 mm
# aluminium or 12 mm ply and print only the tower, cradle and anchor.
BASE_L = 400.0            # along the arm (X)
BASE_W = 340.0            # across it (Y)
BASE_T = 12.0
BASE_MOUNT_DIA = 8.5      # M8 clearance, to the bench
BASE_MOUNT_INSET = 22.0

# --- CRADLE ----------------------------------------------------------------
CRADLE_DIA = 150.0
CRADLE_T = 14.0
CRADLE_GAP = 3.0          # air between tower top and cradle underside
CRADLE_FUNNEL_DIA = 30.0  # counterbore on top, guides the loom into the tube
CRADLE_FUNNEL_T = 4.0

# --- ANCHOR ----------------------------------------------------------------
ANCHOR_FOOT_L = 70.0
ANCHOR_FOOT_W = 44.0
ANCHOR_FOOT_T = 10.0
ANCHOR_EAR_T = 8.0
ANCHOR_BOLT_DIA = 6.6

# --- DERIVED ---------------------------------------------------------------
TOWER_H = 2 * BRG_W + BRG_GAP
TOWER_OD = BRG_OD + 2 * TOWER_WALL
CRADLE_Z = BASE_T + TOWER_H + CRADLE_GAP
CLEVIS_GAP = 14.0         # slot width for the rod end
PIN_Z = CRADLE_Z + ARM_T / 2.0    # cell axis height, level with the arm


NEW = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
JOIN = adsk.fusion.FeatureOperations.JoinFeatureOperation
CUT = adsk.fusion.FeatureOperations.CutFeatureOperation


# ================================================================ HELPERS ==
def new_comp(root, name):
    occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    occ.component.name = name
    return occ.component


def plane_at(comp, z):
    """Construction plane parallel to XY at height z (mm)."""
    pin = comp.constructionPlanes.createInput()
    pin.setByOffset(comp.xYConstructionPlane,
                    adsk.core.ValueInput.createByReal(z * MM))
    return comp.constructionPlanes.add(pin)


def sk_at(comp, z):
    return comp.sketches.add(plane_at(comp, z))


def circle(sk, cx, cy, dia):
    sk.sketchCurves.sketchCircles.addByCenterRadius(
        adsk.core.Point3D.create(cx * MM, cy * MM, 0), dia / 2.0 * MM)
    return sk


def rect(sk, x0, y0, x1, y1):
    sk.sketchCurves.sketchLines.addTwoPointRectangle(
        adsk.core.Point3D.create(x0 * MM, y0 * MM, 0),
        adsk.core.Point3D.create(x1 * MM, y1 * MM, 0))
    return sk


def push(comp, sk, h, op):
    """Extrude every profile in the sketch by h (mm, signed)."""
    profs = adsk.core.ObjectCollection.create()
    for i in range(sk.profiles.count):
        profs.add(sk.profiles.item(i))
    return comp.features.extrudeFeatures.addSimple(
        profs, adsk.core.ValueInput.createByReal(h * MM), op)


def cyl(comp, z, dia, h, op, cx=0.0, cy=0.0):
    return push(comp, circle(sk_at(comp, z), cx, cy, dia), h, op)


def box(comp, z, x0, y0, x1, y1, h, op):
    return push(comp, rect(sk_at(comp, z), x0, y0, x1, y1), h, op)


def bolt_circle(comp, z, pcd, n, dia, depth, phase=0.0):
    sk = sk_at(comp, z)
    for i in range(n):
        a = phase + 2.0 * math.pi * i / n
        circle(sk, pcd / 2.0 * math.cos(a), pcd / 2.0 * math.sin(a), dia)
    return push(comp, sk, depth, CUT)


# ============================================================ PART BUILDERS ==
def build_base_plate(root):
    c = new_comp(root, "1_base_plate")
    box(c, 0.0, -BASE_L / 2.0, -BASE_W / 2.0, BASE_L / 2.0, BASE_W / 2.0,
        BASE_T, NEW)

    # wire pass-through under the shaft tube
    cyl(c, 0.0, TOWER_BORE, BASE_T, CUT)

    # tapped/clearance holes for the tower flange
    bolt_circle(c, 0.0, TOWER_BOLT_PCD, TOWER_BOLT_N, TOWER_BOLT_DIA,
                BASE_T, math.radians(45))

    # bench mounting holes, one near each corner
    sk = sk_at(c, 0.0)
    for sx in (-1, 1):
        for sy in (-1, 1):
            circle(sk,
                   sx * (BASE_L / 2.0 - BASE_MOUNT_INSET),
                   sy * (BASE_W / 2.0 - BASE_MOUNT_INSET),
                   BASE_MOUNT_DIA)
    push(c, sk, BASE_T, CUT)

    # tapped holes for the anchor foot
    sk = sk_at(c, 0.0)
    for dy in (-1, 1):
        circle(sk, ARM_R, CELL_LEN + dy * (ANCHOR_FOOT_L / 2.0 - 14.0),
               ANCHOR_BOLT_DIA)
    push(c, sk, BASE_T, CUT)
    return c


def build_tower(root):
    """Separate part. Bottom bearing loads from below, top from above,
    both seating on the TOWER_BORE shoulder. Bolts down to the base plate,
    which then retains the lower bearing."""
    c = new_comp(root, "2_bearing_tower")
    z0 = BASE_T
    cyl(c, z0, TOWER_OD, TOWER_H, NEW)
    cyl(c, z0, TOWER_FLANGE_DIA, TOWER_FLANGE_T, JOIN)

    cyl(c, z0, TOWER_BORE, TOWER_H, CUT)                       # through bore
    cyl(c, z0, BRG_OD + BRG_FIT, BRG_W, CUT)                   # lower pocket
    cyl(c, z0 + TOWER_H, BRG_OD + BRG_FIT, -BRG_W, CUT)        # upper pocket

    bolt_circle(c, z0, TOWER_BOLT_PCD, TOWER_BOLT_N, TOWER_BOLT_DIA,
                TOWER_FLANGE_T, math.radians(45))
    return c


def build_cradle_arm(root):
    c = new_comp(root, "3_cradle_arm")
    cyl(c, CRADLE_Z, CRADLE_DIA, CRADLE_T, NEW)

    # torque arm, out along +X
    box(c, CRADLE_Z, 0.0, -ARM_W / 2.0, ARM_R + ARM_W / 2.0, ARM_W / 2.0,
        ARM_T, JOIN)

    # clevis at the tip: slot it, leaving two ears
    box(c, CRADLE_Z + (ARM_T - CLEVIS_GAP) / 2.0,
        ARM_R - ARM_W, -ARM_W / 2.0 - 1.0,
        ARM_R + ARM_W / 2.0 + 1.0, ARM_W / 2.0 + 1.0,
        CLEVIS_GAP, CUT)
    # ...which needs the ears back as vertical plates
    for sy in (-1, 1):
        y_out = sy * ARM_W / 2.0
        y_in = sy * (ARM_W / 2.0 - (ARM_T - CLEVIS_GAP) / 2.0)
        box(c, CRADLE_Z, ARM_R - ARM_W, min(y_in, y_out),
            ARM_R + ARM_W / 2.0, max(y_in, y_out), ARM_T, JOIN)

    # pin hole, vertical, so the rod end pivots freely about Z
    cyl(c, CRADLE_Z, CELL_PIN_DIA, ARM_T, CUT, cx=ARM_R)

    # shaft bore and loom funnel
    cyl(c, CRADLE_Z, SHAFT_OD + SHAFT_FIT, CRADLE_T, CUT)
    cyl(c, CRADLE_Z + CRADLE_T, CRADLE_FUNNEL_DIA, -CRADLE_FUNNEL_T, CUT)

    # bolt pattern for the existing nacelle-mount post
    if POST_BOLT_N > 0 and POST_BOLT_PCD > 0:
        bolt_circle(c, CRADLE_Z, POST_BOLT_PCD, POST_BOLT_N, POST_BOLT_DIA,
                    CRADLE_T)
    if POST_SPIGOT_DIA > 0:
        cyl(c, CRADLE_Z + CRADLE_T, POST_SPIGOT_DIA, 4.0, JOIN)
        cyl(c, CRADLE_Z + CRADLE_T, SHAFT_OD + SHAFT_FIT, 4.0, CUT)
    return c


def build_anchor(root):
    c = new_comp(root, "4_cell_anchor")
    x0 = ARM_R - ANCHOR_FOOT_W / 2.0
    y0 = CELL_LEN - ANCHOR_FOOT_L / 2.0
    box(c, BASE_T, x0, y0, x0 + ANCHOR_FOOT_W, y0 + ANCHOR_FOOT_L,
        ANCHOR_FOOT_T, NEW)

    # two ears straddling the rod end, pin axis vertical
    top = PIN_Z + CELL_PIN_DIA
    for sy in (-1, 1):
        y_in = CELL_LEN + sy * CLEVIS_GAP / 2.0
        y_out = y_in + sy * ANCHOR_EAR_T
        box(c, BASE_T,
            ARM_R - ANCHOR_FOOT_W / 2.0, min(y_in, y_out),
            ARM_R + ANCHOR_FOOT_W / 2.0, max(y_in, y_out),
            top - BASE_T, JOIN)

    sk = sk_at(c, BASE_T)
    for dy in (-1, 1):
        circle(sk, ARM_R, CELL_LEN + dy * (ANCHOR_FOOT_L / 2.0 - 14.0),
               ANCHOR_BOLT_DIA)
    push(c, sk, ANCHOR_FOOT_T, CUT)

    cyl(c, BASE_T, CELL_PIN_DIA, top - BASE_T, CUT,
        cx=ARM_R, cy=CELL_LEN)
    return c


def build_reference(root):
    """Not for printing. Sanity-check clearances by eye, then delete."""
    c = new_comp(root, "5_REF_do_not_print")
    z0 = BASE_T
    for z in (z0, z0 + TOWER_H - BRG_W):
        cyl(c, z, BRG_OD, BRG_W, NEW)
        cyl(c, z, BRG_ID, BRG_W, CUT)

    shaft_top = CRADLE_Z + CRADLE_T
    cyl(c, z0 - 6.0, SHAFT_OD, shaft_top - (z0 - 6.0), NEW)
    cyl(c, z0 - 6.0, SHAFT_ID, shaft_top - (z0 - 6.0), CUT)

    # load cell body, centred between the two pins
    cyl(c, PIN_Z - CELL_BODY_W / 2.0, CELL_BODY_W, CELL_BODY_W, NEW,
        cx=ARM_R, cy=CELL_LEN / 2.0)
    return c


# =================================================================== PARAMS ==
def publish_params(design):
    table = [
        ("arm_R", ARM_R, "axis to load-cell pin"),
        ("cell_len", CELL_LEN, "pin centre to pin centre"),
        ("brg_gap", BRG_GAP, "clear air between bearings"),
        ("tower_H", TOWER_H, "base plate top to tower top"),
        ("cradle_Z", CRADLE_Z, "underside of rotating cradle"),
        ("pin_Z", PIN_Z, "load cell axis height"),
        ("post_bolt_pcd", POST_BOLT_PCD, "MEASURE: existing post bolt circle"),
    ]
    for name, val, note in table:
        try:
            design.userParameters.add(
                name, adsk.core.ValueInput.createByString("%.3f mm" % val),
                "mm", note)
        except Exception:
            pass  # name already exists


# ====================================================================== RUN ==
def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = app.activeProduct
        design.rootComponent.name = "torque_cradle"
        root = design.rootComponent

        publish_params(design)
        build_base_plate(root)
        build_tower(root)
        build_cradle_arm(root)
        build_anchor(root)
        build_reference(root)

        fs_nm = 5.0 * 9.80665 * ARM_R / 1000.0
        ui.messageBox(
            "torque_cradle built.\n\n"
            "Arm radius      %.0f mm\n"
            "Cell full scale %.2f N.m at 5 kg\n"
            "Cruise 1.17 N.m %.0f %% of full scale\n"
            "Peak   3.33 N.m %.0f %% of full scale\n\n"
            "Set POST_BOLT_PCD and POST_SPIGOT_DIA at the top of the script,\n"
            "then re-run. Delete component 5_REF before printing."
            % (ARM_R, fs_nm, 100 * 1.17 / fs_nm, 100 * 3.33 / fs_nm))

    except Exception:
        if ui:
            ui.messageBox("Failed:\n%s" % traceback.format_exc())
