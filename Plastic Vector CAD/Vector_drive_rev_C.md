# Vector drive rev C: printed axle on a steel spine, wide gears

2026-11-23. Source: `RU3Y for Claude.step`. All x positions are mm from the rotor centerline, positive toward the wing. Wing mount face is at x = 101.46.

## Decisions

| Part | Material | How made | Mass |
|---|---|---|---|
| Vector 01, servo pinion 12T | PA12 | printed | 2.2 g |
| Vector 02 03, idler 25T / 10T | 7075-T6 | milled | 13.7 g |
| Vector 04, output gear 46T | 7075-T6 | milled | 36.7 g |
| Axle sleeve (journal, keys, hex) | PA12 | printed | 5.8 g |
| Axle spine tube | 4130 steel, 1/2 in OD x 0.028 in wall, 108.5 long | cut to length | 22.8 g |

Total 81 g per nacelle. The all-7075 set as drawn is 57 g. The wing mount is unchanged.

Retracted: the carbon tube spine I proposed earlier. A 0/90 roll-wrapped carbon tube that fits the mount twists about 0.5 deg per N·m between the output gear and the wing mount, so 1.5 deg of nacelle tilt error at 3 N·m. The steel tube twists 0.04 deg per N·m.

## Why the last stage is 7075

Root bending, same conservative method as the earlier sheet (full load on one tooth tip). PA12 strength taken as 48 MPa, 7075-T6 yield as 503 MPa.

| Case | Stress at 6 V stall (8.8 N·m at axle) | Stress at 7.4 V stall (10.15 N·m) | Verdict |
|---|---|---|---|
| Last stage in PA12, 12 mm wide | 73 MPa | 84 MPa | strips |
| Last stage in 7075, 8 mm wide (rev C) | 110 MPa | 127 MPa | margin 4 |
| First stage pinion in PA12, 12 mm wide (rev C) | 31 MPa | 36 MPa | margin 1.5 / 1.35 |

A PA12 last stage would need about 27 mm of width for a 1.5 margin at stall. A stripped tilt gear is a free-swinging nacelle, and a servo driven into a stop by a software fault produces exactly the stall load, so the last stage is metal.

Tooth form is Set A from the earlier sheet: module 1.0, 12/25 and 10/46, ratio 9.5833, same centers, 0.08 mm backlash per mesh.

## Axle

| | 7075 axle as drawn | PA12 axle as drawn | Rev C: PA12 sleeve on 4130 tube |
|---|---|---|---|
| Wire bore | 11.0 | 11.0 | 11.28 |
| Bending stress in hover | 15 MPa | 15 MPa | 54 MPa in the steel (yield 483) |
| Same at 3 times hover load | 44 MPa | 44 MPa, at the limit for nylon | 163 MPa, margin 3.0 |
| Nacelle droop plus yaw in hover | 0.16 deg | 6.7 deg | 0.24 deg |
| Twist, gear to wing mount, per N·m | 0.03 deg | 1.3 deg | 0.04 deg |

Loads used: 7.5 lbf (33.4 N) thrust at 101.46 mm from the mount face gives 3.39 N·m, and rotor torque of 2.37 N·m (446 W at 1800 rpm) acts at right angles to it, so 4.13 N·m resultant at the mount face.

- Sleeve outside shape is the existing axle: 14.96 journal, 14.66 hex, same keys, same notches. Bore is 12.85 for a 12.70 tube. Wall is 1.05 mm at the journal and 0.9 mm at the hex flats.
- The journal now runs to x = 99.0 and the hex starts there, so both bearings ride on round journal.
- Keys run x = 36.57 to 54.70 (were 7.1 long, now 18.1). At 7.4 V stall they see 13.6 MPa bearing and 8.8 MPa shear.
- Bore cannot reach 12 mm without rebuilding the wing mount: the hex socket caps the tube at about 13 mm outside.

## New positions

| Item | Was | Rev C | Shift |
|---|---|---|---|
| Servo pinion teeth | 37.96 to 46.29 | 37.96 to 51.19 | end +4.90 |
| Servo pinion outboard journal, its bearing, servo screw | | | +4.90 (screw 5 mm longer) |
| Idler large gear (25T) | 38.95 to 43.11 | 38.95 to 50.95 | 12.0 wide |
| Idler pinion (10T) | 43.11 to 48.81 | 50.95 to 59.95 | 9.0 long |
| Idler outboard end and bearing | 49.92 | 61.05 | +11.13 (pin 11.13 longer) |
| Output gear teeth | 43.98 to 48.14 | 51.45 to 59.45 | 8.0 wide |
| Output gear hub end | 49.57 | 60.88 | +11.31 |
| Main bearing | 50.00 to 57.00 | 61.31 to 68.31 | +11.31 |
| Second bearing (same part) | none | 90.00 to 97.00 | anywhere from 70 to 99 works |

Servo-side faces of all three gears are unchanged, so the servo and the inboard bearings stay where they are.

## Assembly notes

1. Cut the tube to 108.5 mm and deburr the bore well, since the wiring runs through it.
2. Abrade tube and sleeve bore, bond with a toughened epoxy, tube flush at both ends.
3. After cure, drill 2.1 mm through the two key screw holes (x = 38.87) into the tube wall. The output gear's two M2.5 screws then pin gear, key and tube together, so tilt torque does not depend on the glue.
4. The two locating pins in the wing mount top half graze the tube by 0.10 mm at x = 125. Touch the tube with a file there, or sand the pins.
5. Bare 7075 on 7075 needs grease. If the gears are hard anodized, tell me the coating thickness and I will recut the backlash.

## Checks run

- All five parts are valid solids. Gear pairs: zero overlap, 0.040 mm flank gap in the assembled pose.
- Output gear on sleeve: no overlap, 0.019 mm minimum gap at the keys. Sleeve to tube: 0.075 mm bond gap all round.
- Sleeve in the wing mount: no overlap. Tube in the wing mount: 0.27 mm³ overlap at the two pins (note 4).
- New parts against every other solid in the STEP: the only overlaps are the three bearings listed as moving, and the existing press fits.
- Not checked: the nacelle housing, which is not in the STEP. Nacelle mass and the housing's bearing seats are unknown to me.

## Open items

- Output gear is the heavy part. Pocketing the web would take roughly 10 g out of it.
- Idler bearings: at stall the idler pin sees roughly 570 N. Check that against the static rating of the two small bearings.
- Bending natural frequency of the nacelle on this axle is about 85 Hz if the nacelle is 1 kg (assumed). Rotor 2-per-rev is 60 Hz at 1800 rpm and 33 Hz at 1000 rpm. A tap test on the built nacelle settles it.
