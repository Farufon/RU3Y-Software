
I've uploaded two files.  A python script that you helped me create that makes a raw, 3:1 helical gear in Autodesk Fusion. 

The second file is a step of the finished (AND SIZED AXEL TO AXEL DISTANCE), geometry needed for the two gears to work/fit in the assembly. 

I need another python script, assuming the identical axel distance, heights and hole patterns and threads.  

EXCEPT, the new gear must be 4:1 ratio.  Note, I need to add more teeth, (grow), the larger gear more than reducing too many teeth on the main smaller drive gear.  it's already approaching too few teeth.  

3-to-1_helical.py
3-to-1_current_helical.step



4:1 RESPONSE

4-to-1_helical.py builds both finished parts at 4:1 on the same 31.87997 mm axle distance, with every height, bore, hole and the M2.5x0.45 thread taken from the STEP. I could not run it in Fusion here, so the first run is the real test.

**One constraint you can't get around.** A fixed axle distance plus an exact 4:1 ratio fixes both pitch diameters regardless of tooth count: the pinion drops from 15.94 to 12.75 mm and the gear grows from 47.82 to 51.01 mm. Tooth count only decides how big the teeth are. So I kept the pinion at 20 teeth and put all of the change in the gear (60 to 80), which makes the teeth 20% smaller. `PINION_TEETH` is one line if you would rather trade the other way:

| Pinion / gear | Normal module | Pinion OD | Gear OD |
|---|---|---|---|
| 20 / 80 (default) | 0.599 mm | 13.95 mm | 52.21 mm |
| 18 / 72 | 0.666 mm | 14.08 mm | 52.34 mm |
| 16 / 64 | 0.749 mm (current tooth size) | 14.25 mm | 52.51 mm |
| 20 / 60 (current 3:1) | 0.749 mm | 17.44 mm | 49.32 mm |

At a 20 degree helix, undercut starts below about 15 teeth, so all three options are clean.

**Things to check before you print:**

- **Gear OD.** It grows about 1.45 mm on the radius. Make sure the housing has room.
- **Pinion hub.** I shrank it from 13.08 to 10.26 mm diameter, keeping it the same distance below the tooth root as the current part. At the old diameter the larger gear would overlap it in plan with only 0.2 mm of axial gap. The wall at the radial 2.5 mm hole is now 2.13 mm instead of 3.54 mm.
- **Gear pocket.** Left identical, so the rim is 5.0 mm thick instead of 3.2 mm. `G_POCKET_R_OUT` thins it if you want the weight back.
- **Threads.** The STEP carries no thread data. The only thread-sized hole is the 2.0755 mm one in the gear boss, which I rebuilt as a cosmetic M2.5x0.45. Every other small hole is a plain 2.5 mm. If any of those are tapped M3 in your Fusion file, tell me which.

**A problem in the current 3:1 parts.** The old script lofted each tooth between only two sketches, which makes straight-line teeth rather than a true helix. Sectioning your STEP shows it: the pinion tip is 0.20 mm low at mid face and the teeth are thinner there, so the current pair only bears at the two ends of the face. The new script lofts through nine sections and should bear across the full face. The side effect is that the accidental mid-face slack is gone, so if the new pair runs tight, set `BACKLASH` (it is 0, as before).

**Checked here:** the profiles mesh with zero overlap through a full tooth cycle at the bottom, middle and top of the face, and the placement math puts the flange holes and hub hole within a micron of their STEP positions. With `PLACE_LIKE_STEP = True` both parts land where the 3:1 parts sit in your assembly.

