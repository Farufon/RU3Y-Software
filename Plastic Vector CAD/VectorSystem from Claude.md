## Vector 7075 Assembly, the servo group, vector hardware, and the four McMaster bearings (two 57155K552, the flanged 57155K623, and the ultra-thin flanged 4390N168).

What I'm carrying into your question:

- **Vector drive:** goBILDA 2000-0025-0503, 5-turn dual mode, through the gear train to the hex axle.
- **Travel:** about 94° at the output, covering the 0 to 90 hover-to-forward-flight vector. A STEP is a single pose, so I'm taking that figure from you, not from the file.
- **Wing:** Selig 3002-099-83 at the tip, 8" chord, 6 ft span, one nacelle per tip.
- **Mount:** hex axle into the power block, power block into the 1" x 2" void in the wing.
- **Thrust stand:** the same axle went straight onto the load cell, so the stand numbers are loads at that axle.

I'll measure the existing gears from your STEP first, work out the tooth loads, then cut new involute gears to the same centers and bores.

Yes, and both sets are built, but your instinct points the wrong way: at fixed gear diameters, more and smaller teeth are weaker. The real weak spot is the 10-tooth pinion on the idler, and the resin cannot carry this train in flight with either tooth size.

## What the STEP shows

- **Train:** 12T servo pinion to 25T, then 10T to 46T at the axle. Ratio is 9.583, so 94° of nacelle is 901° of servo.
- **Flanks:** already true involutes, constant base circle to within 0.003 mm, and they roll without interference. "Perfect involute" was not the problem.
- **Weak point:** the 10T pinion has no profile shift, so its root necks to 1.40 mm with a sharp corner.
- **Face width:** only 4.16 mm of overlap in both stages.

## Tooth loads

| | Existing | Set A | Set B |
|---|---|---|---|
| Teeth | 12/25, 10/46 | 12/25, 10/46 | 16/35, 14/63 |
| Module | 1.03 | 1.0, profile shifted | 0.75 |
| Ratio | 9.583 | 9.583 | 9.844 |
| Worst root stress per N·m at the axle | 59 MPa | 24 MPa | 37 MPa |
| At servo stall, 7.4 V (about 10 N·m at the axle) | 599 MPa | 243 MPa | 383 MPa |
| Axle torque where Tough 2000 reaches its 40 MPa strength | 0.7 N·m | 1.7 N·m | 1.1 N·m |
| Axle torque where 7075-T6 yields | 8.5 N·m | 21 N·m | 13.7 N·m |

These are conservative: full load on one tooth tip, no load sharing.

- **Set A** is my recommendation: same tooth counts and ratio, with the pinions shifted so the roots are thick and fully filleted. It is 2.5 times stronger than what you have.
- **Set B** is what you asked for. It is still 1.6 times stronger than the existing set, because it also fixes the pinion root, but it is weaker than A and needs 1028 µs of servo travel instead of 1001.
- **Existing aluminum set:** the servo at stall can put the 10T pinion past 7075 yield (599 MPa against 503).

## Flight torque

I cannot give you one number. The thrust stand measured force along the rotor axis, not moment about the tilt axle. The 7.5 lbf only loads the teeth through its offset from the tilt axis: 0.33 N·m per 10 mm. Gyroscopic load adds roughly 1.2 N·m per 100°/s of roll in hover, assuming 25 g blades, which I have not confirmed.

A few N·m in maneuvers is plausible, and the servo can push about 10 N·m into the teeth. Design to the 10 N·m.

## Material

Tough 2000 is fine for fit checks and bench rigging. For flight it fails by a factor of about six against servo stall, even in Set A, and it creeps under sustained load. Use 7075 at minimum for the idler (Vector 02 03), ideally steel. Widening the output gear teeth from 4.16 to 5.70 mm cuts stress another 27% and clears everything in this STEP.

## Caveats on the files

- **Housing:** it is not in the STEP, so I kept every tip diameter at or below the existing ones. The one exception is the Set A idler pinion, which is 0.21 mm larger on diameter.
- **Backlash:** I set 0.08 mm per mesh for printing, about 0.30° of play at the axle. Your CAD has about 0.15°. For milled aluminum I would tighten it; tell me the number and I will regenerate.
- **Hubs and bores:** bores, servo spline, hub and bolt pattern are carried over from your originals. The two "all three in place" STEP files drop into your assembly at the same origin.

The data sheet is also saved to the project as `claude/vector-gear-data-2026-11-23.md`.

Sources: [goBILDA 2000-0025-0503 specs](https://www.gobilda.com/2000-series-5-turn-dual-mode-servo-25-3-speed/), [Formlabs Tough 2000 V2 data sheet](https://formlabs-media.formlabs.com/datasheets/25011072-TDS-ENUS-0.pdf)