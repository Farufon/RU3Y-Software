# Vector gear train: measurements, loads and replacement gear data

2026-11-23. Source: `nacelle vector system.step`. All dimensions mm.

## What the existing gears are (measured from the STEP)

| Gear | Part | Teeth | Tip dia | Root dia | Base dia | Tooth face |
|---|---|---|---|---|---|---|
| G01 | Vector 01 (servo pinion) | 12 | 14.452 | 9.974 | 11.404 | 8.33 |
| G02 | Vector 02 03, large | 25 | 27.876 | 23.431 | 23.756 | 4.16 |
| G03 | Vector 02 03, small | 10 | 12.394 | 7.947 | 9.502 | 5.70 |
| G04 | Vector 04 Unified (output) | 46 | 49.548 | 45.125 | 43.712 | 4.16 |

- Centers: 19.0967 (servo to idler), 28.9032 (idler to axle). Ratio 9.5833.
- Working module 1.032, working pressure angle 23.0 deg, no profile shift.
- The flanks are already true involutes: the base circle implied by the flank normals is constant to within 0.003 mm on all four gears.
- The pairs roll without interference in a 2D mesh simulation, with 0.035 to 0.055 mm normal backlash.
- Weak point: the 10T pinion. With no profile shift its root is relieved below the base circle, necking to 1.40 mm, with a sharp corner at the root.
- Overlapping face width is 4.16 mm in both stages.

## Tooth loads

Method: Lewis bending at the tooth root, full load applied at the tip of one tooth (no load sharing), measured tooth geometry, 4.16 mm face. No stress concentration factor, so sharp root corners are worse than the number shown. Stress scales linearly with torque at the axle.

| | Existing | Set A | Set B |
|---|---|---|---|
| Worst root bending, MPa per N·m at the axle | 59.1 (G03) | 24.0 (G03) | 36.7 (G04) |
| At servo stall, 7.4 V (1.06 N·m at servo) | 599 MPa at 10.2 N·m | 243 MPa at 10.2 N·m | 383 MPa at 10.4 N·m |
| At servo stall, 6.0 V (0.92 N·m at servo) | 520 MPa at 8.8 N·m | 211 MPa at 8.8 N·m | 332 MPa at 9.0 N·m |
| Axle torque at which Tough 2000 V2 reaches its 40 MPa tensile strength | 0.68 N·m | 1.69 N·m | 1.10 N·m |
| Axle torque at which 7075-T6 reaches 503 MPa yield | 8.5 N·m | 21.0 N·m | 13.7 N·m |

Servo: goBILDA 2000-0025-0503, stall 130 oz-in at 6.0 V, 150 oz-in at 7.4 V. Tough 2000 V2 post-cured: 40.4 MPa ultimate tensile, 67 MPa flexural, HDT 57 C at 1.8 MPa (Formlabs data sheet).

### Flight torque about the tilt axis (estimates, not measurements)

The thrust stand measured force along the rotor axis. It did not measure moment about the tilt axle, so the items below are estimates and each needs a dimension from the nacelle CAD.

- Thrust line offset from the tilt axis: 33.4 N (7.5 lbf) times the offset. 0.33 N·m per 10 mm.
- Gyroscopic: rotor angular momentum times aircraft rate about the axis perpendicular to both the rotor axis and the tilt axis (roll in hover, yaw in cruise). Assuming 25 g per blade (not weighed), about 1.2 N·m per 100 deg/s at 1800 rpm and 0.7 N·m per 100 deg/s at 1000 rpm.
- Nacelle mass offset from the tilt axis: 0.098 N·m per kg, per 10 mm, per g of load factor.
- Rotor torque reaction (about 2.4 N·m) and thrust both act across the axle. They load the bearings and bend the axle. They do not load the gear teeth.
- Upper bound from the servo side: 8.8 to 10.2 N·m at the axle. Design the teeth to this, so the servo and not a tooth is the limit.

## Replacement sets

Both sets: true involute flanks generated from the ISO 53 basic rack (20 deg, 1.25 m dedendum, 0.38 m root fillet), same centers, same face widths, same bores, same servo spline, same hub and bolt pattern, tip diameters no larger than the existing parts except Set A G03 (+0.21 mm on diameter). Flank splines are within 0.00005 mm of the exact curves. 0.08 mm normal backlash per mesh, which is about 0.30 deg of free play at the axle (existing CAD: about 0.15 deg).

### Set A: module 1.0, 12/25 and 10/46, ratio 9.5833

| Gear | Part | Teeth | Shift x | Tip dia | Root dia | Base dia | Tip land | Span (teeth) |
|---|---|---|---|---|---|---|---|---|
| G01 | Vector 01 | 12 | +0.4000 | 14.452 | 10.300 | 11.276 | 0.59 | 4.830 (2) |
| G02 | Vector 02 03 (large) | 25 | +0.2624 | 27.400 | 23.025 | 23.492 | 0.66 | 7.870 (3) |
| G03 | Vector 02 03 (small) | 10 | +0.5000 | 12.600 | 8.500 | 9.397 | 0.50 | 4.870 (2) |
| G04 | Vector 04 Unified | 46 | +0.5026 | 48.800 | 44.505 | 43.226 | 0.72 | 17.185 (6) |

Stage 1: centers 19.0967 mm, working pressure angle 24.45 deg, contact ratio 1.24, tip clearance 0.36 / 0.25 mm.

Stage 2: centers 28.9032 mm, working pressure angle 24.45 deg, contact ratio 1.21, tip clearance 0.35 / 0.25 mm.

Servo travel for 94 deg of nacelle: 901 deg = 1001 us of pulse width (existing: 901 deg, 1001 us).

### Set B: module 0.75, 16/35 and 14/63, ratio 9.8438

| Gear | Part | Teeth | Shift x | Tip dia | Root dia | Base dia | Tip land | Span (teeth) |
|---|---|---|---|---|---|---|---|---|
| G01 | Vector 01 | 16 | +0.3000 | 13.800 | 10.575 | 11.276 | 0.44 | 3.603 (2) |
| G02 | Vector 02 03 (large) | 35 | -0.3375 | 27.250 | 23.869 | 24.667 | 0.56 | 7.904 (4) |
| G03 | Vector 02 03 (small) | 14 | +0.3500 | 12.394 | 9.150 | 9.867 | 0.38 | 3.608 (2) |
| G04 | Vector 04 Unified | 63 | -0.3123 | 48.274 | 44.907 | 44.400 | 0.58 | 14.853 (7) |

Stage 1: centers 19.0967 mm, working pressure angle 19.77 deg, contact ratio 1.49, tip clearance 0.26 / 0.18 mm.

Stage 2: centers 28.9032 mm, working pressure angle 20.15 deg, contact ratio 1.47, tip clearance 0.25 / 0.19 mm.

Servo travel for 94 deg of nacelle: 925 deg = 1028 us of pulse width (existing: 901 deg, 1001 us).
"Span" is the caliper measurement across that many teeth, including the backlash allowance.

## Checks run on the new parts

- 2D roll-through of each pair at the exact ratio: zero overlap, flank gap constant at 0.040 mm (half the backlash) through the whole mesh. Also clean with centers 0.05 mm closer.
- 3D: each new solid is valid, pairs do not intersect in the assembled pose, minimum distance 0.040 mm.
- Original bores, bosses, spline socket and hub features are all present in the new parts. Fits against the servo shaft and bearings are unchanged from the original CAD.
- Not checked: the housing, which is not in the STEP.

## Levers that lower tooth stress, in order of effect

1. Material. A steel or 7075 idler (Vector 02 03) removes the weakest part from the resin set.
2. Face width. Stress is inversely proportional. The output gear teeth can grow from 4.16 to 5.70 to match the idler pinion without touching another gear in this STEP.
3. Tooth size. Larger module is stronger at a fixed diameter. Finer teeth run smoother and are weaker.
