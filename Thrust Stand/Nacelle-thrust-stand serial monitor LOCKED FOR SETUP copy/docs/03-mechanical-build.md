# 03 - Mechanical Build

The load path, top to bottom:

```
        prop (914 mm disc, R = 457)
             |
        nacelle
             |
        trunnion axis  <-- clamped by yoke
             |
        yoke
             |
        upper adapter plate
             |
        stud + jam nut
             |
   ==== S-BEAM LOAD CELL ====   <-- everything above this is measured
             |
        stud + jam nut
             |
        lower adapter plate
             |
        post  (sets height z)    <-- everything below this is NOT measured
             |
        three splayed legs
             |
        floor
```

The line through the cell is the whole design. Anything above it appears in the reading.
Anything below it does not. That is why the cell goes **directly under the nacelle** and
not partway down the post.

---

## Blade and hub interface - locked, do not redesign

The rotor is Austin's **SOLID CORE V49** blade pair. The blade-to-grip interface is fixed
and is not something this stand gets to have an opinion about. It is recorded here because
it is easy to measure the wrong thing.

**The supplied STL files are printed CORES, not finished blades.** The carbon layup adds
**1.0 mm per side**. Every dimension below is core-versus-finished, and confusing the two
will make a correctly-designed joint look like an interference.

| | Width | Thickness |
|---|---|---|
| Core tang, measured off the STL | 14.25 mm | 7.00 mm |
| Plus 1.0 mm carbon per side | +2.0 | +2.0 |
| **Finished blade root** | **16.25 mm** | **9.00 mm** |

Against the grip:

| Feature | Value | Source |
|---|---|---|
| Grip outside diameter | 16.0 mm | drawing |
| Flats, across | 9.0 mm | drawing |
| Resulting flat face width | 13.2 mm | drawing, and 2*sqrt(8^2 - 4.5^2) = 13.23 confirms it |
| Grip length | 49 mm, r = 31 to 80 | drawing, and the STL tang measures exactly 49 mm |
| Bolt holes | 5.0 mm, at r = 40 and r = 65 | drawing, matching `CENTER_HUB_to_DIVOT1/2` |
| Bolt spacing | 25 mm | 65 - 40 |
| Outboard bolt to grip end | 15 mm | 80 - 65 |
| Bearings | 8 mm OD on 5 mm bolts | Austin's source |

Finished thickness of 9.00 mm sits **exactly** on the 9.0 mm flats. Finished width of
16.25 mm is 0.25 mm over the 16.0 mm diameter, which is precisely why Austin's source reads
`gripper_hgt = 9.0 - 0.25` with a note that he built it to 9 mm and sanded to fit.

**Do not scale anything off the STL root as though it were the finished part.** It is 2 mm
undersize in both directions by design.

### The one measurement that matters to this rig

The whole test matrix, the z/R ladder and every power figure in doc 01 are anchored to
**R = 457 mm, hub centreline to blade tip**.

The blade root face sits at r = 31 mm and the blade is 426 mm long, which is what produces
457. If your assembled hub puts the root face anywhere other than 31 mm from the rotor
centreline, **R is not 457 and the labels on your data are wrong.**

Measure it once, with calipers, on the assembled head. Write the number in the run log. If
it comes out other than 457, pass it to `reduce.py` with `--radius` and recompute the height
ladder as z/R times the measured value. Do not just carry on with the printed table.

## Step 1 - Build the yoke

Your nacelle already has a trunnion where the wing carries it. Build a U-shaped yoke that
captures that tube, with pinch bolts closing the open end.

You are not inventing a mount. You are copying the one the aircraft already uses, which is
the answer to the stability question: the trunnion is strong enough and stiff enough to
carry this nacelle in flight, so it is strong enough here.

Index the yoke so the **rotor axis is vertical** when the trunnion is clamped. Mark that
index position so you can return to it exactly after any disassembly.

Bonus: if you make the yoke indexable at intermediate tilt angles, the same fixture
characterises thrust and watts through the transition, not just at hover. That may be worth
more to Vermont than the hover number alone.

## Step 2 - Upper adapter plate

The yoke bolts to a flat plate, minimum three bolts. One bolt will wobble and rotate; three
on a plate is a stand. The underside of this plate is the mating face for the load cell, so
it must be flat and clean. You need friction across that joint.

Drill the centre for the stud, and if you are fitting an anti-rotation dowel, drill for it
now, offset from centre.

## Step 3 - Fit the load cell

Thread a stud into the cell's upper hole. The ATO 20 kg cell is **M8 x 1.25**, standard
coarse pitch, so studs and jam nuts are off-the-shelf. Get about **1.5 diameters of
engagement**, so roughly 12 mm.

Cell envelope for your CAD: 60 mm wide, 58 mm tall, 12 mm thick, threaded holes on the
vertical centreline. Full table in `docs/11-load-cell-datasheet.md`.

**Do not let the stud bottom out in the hole.** If it bottoms and you keep turning, you jack
the cell body apart from the inside and permanently shift its zero. Run it until snug on the
plate face, then lock with the jam nut.

Repeat at the bottom into the lower adapter plate.

Rules that are not optional:

- **Nothing clamps the middle of the cell.** That is where the strain gauges live. It has to
  stay free to flex.
- **No compliance in the joints.** No rod ends, no rubber, no crush washers. Compliance
  shows up as lag and hysteresis in your data.
- **No brace bridges the cell.** If you brace the post, the brace attaches below the cell.
  A brace across the cell shunts load around it and you measure a fraction of the truth
  without knowing it.

## Step 4 - Anti-rotation

Motor torque at hover is about 1 N-m, under a foot-pound, trying to unscrew the stack.
Friction from a properly preloaded M8 on a flat plate face handles it easily.

Check your prop rotation direction against the thread hand. If reaction torque wants to
unscrew the joint, fit the dowel pin through both plates offset from centre and stop
worrying about it. Thread locker on both studs regardless.

## Step 5 - Alignment

This is the one thing that can silently corrupt the reading.

The cell's measuring axis must be **vertical and coincident with the rotor axis**. Thrust
then arrives as pure axial load, which is what an S-beam measures well. Check with a level
on the plate faces and a plumb line from the hub.

**Get the CG on the post centreline.** Balance the assembly on the post with the motor off
and shim until it sits without wanting to fall one way. If you cannot get it close, add a
counterweight to the fixture.

This matters for two separate reasons and they are worth separating:

- **Measurement:** a constant bending moment from an offset CG is absorbed by the tare, so
  it does not corrupt the reading. This part is genuinely forgiving.
- **Survival:** ATO's own guidance for this cell is explicit that it must be installed
  without transverse load, and that load applied offset from the centre axis damages the
  sensor. Their transverse load limit is 100% F.S. An S-beam is built to be loaded along
  its axis and is comparatively weak in bending.

So do not skip alignment on the grounds that the tare handles it. The tare protects your
data, not your cell. Never lever the nacelle into position with the cell in the stack, and
never let the fixture apply a side load or a twist.

Beyond that, the geometry only needs to hold still between tare and run. No slop, nothing
shifting, and re-tare after anything is bumped.

## Step 6 - Post and height sections

Round steel tube, 25-38 mm OD. Round because it is stiff in torsion and has no preferred
bending plane.

Cut discrete sections for each height in the ladder rather than using a pinned telescope.
A pinned telescope has a few thou of slop, and slop between tare and run is exactly the
error mode you are trying to avoid. If you must telescope, use a clamping collar, not a pin.

Post length is measured so that the **rotor plane** lands at the target height, not the top
of the post. Account for the stack height of plates, cell and nacelle. Measure the actual
assembled rotor height with a tape at every ladder step and record it. Do not trust the cut
length.

## Step 7 - Legs

Three legs, splayed, feet landing **outside 700 mm radius** from the axis so nothing solid
sits under the rotor.

Anchor to concrete, or ballast each foot with 25 lb. The rig must not walk, rock or ring.

Again: no solid base plate under the disc. It would act as a false ground plane and corrupt
the exact measurement you are making.

## Step 8 - Pre-flight mechanical check

Before power, with the prop fitted:

- [ ] Rotor axis vertical, plumbed from hub
- [ ] All plate bolts to torque
- [ ] Jam nuts locked, thread locker cured
- [ ] Nothing bridging the cell
- [ ] Cell cable strain-relieved with a service loop, not tight
- [ ] Legs anchored or ballasted, no rock
- [ ] Prop bolts to torque, prop balanced
- [ ] Rotor height measured and written down
- [ ] Floor clear for three rotor diameters, roughly 1.8 m each way
