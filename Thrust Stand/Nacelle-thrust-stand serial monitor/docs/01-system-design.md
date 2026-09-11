# 01 - System Design

## The question this rig answers

Vermont has flying aircraft. The question is not "will it lift." The question is what the
power draw looks like through the takeoff transition, from sitting on the ground up to
free-air hover, where ground effect is real and where the pack sees its hardest moment.

So the measured output is:

> **Electrical watts to produce 7.5 lbf, as a function of rotor height above ground,
> minimised over the available combinations of head RPM and collective pitch.**

Not thrust at full throttle. Not thrust at one height. A curve of watts against height at
constant thrust. That is what sizes his pack and tells him what climb-out costs.

## Rotor definition - settled

This was ambiguous for a while and is now closed. From Austin's design source, 4 September:

```
tip_radius          = 457.0    // tip radius from hub centerline, mm
CENTER_HUB_to_FIBER =  31.0    // hub centreline to base of the grip
```

**457 mm is the rotor radius, measured from the hub centreline to the blade tip.** The blade
itself is 426 mm of physical length, running from r = 31 mm out to r = 457 mm.

The earlier `BLADETEST.step` file, 499.5 mm root face to tip, is **superseded**. Austin
identified it as one of an earlier family built while he was exploring longer radii. Do not
size anything from it. The current blade is the **SOLID CORE V49** pair, supplied as
`PROP_CORE_CW` and `PROP_CORE_CCW`.

### Measured blade geometry, V49 core

Taken directly off the supplied STL meshes rather than from the design intent.

| Quantity | Value |
|---|---|
| Rotor radius R | 457.0 mm |
| Blade physical length | 426.0 mm (r = 31 to 457) |
| Blades per rotor | 2 |
| Max chord | 33.84 mm at r/R = 0.75 |
| Reference chord (Austin's source) | 35.0 mm |
| Built-in twist, r/R 0.22 to tip | 33.3 degrees, washout |
| Thickness ratio | 17.7% at r/R 0.22, tapering to 12.2% at the tip |
| Geometric solidity | 0.0286 |
| Thrust-weighted solidity | 0.0388 |
| Thrust-weighted equivalent chord | 27.8 mm |
| Disc area | 0.656 m^2 |
| Disc loading at 7.5 lbf | 50.8 N/m^2 |
| Root airfoil | GOE 601 |
| Tip airfoil | DEFIANT CANARD |

The CW and CCW files were checked against each other and are an **exact mirror pair**, zero
deviation after reflection. The handed set is correct; you are not about to build two rotors
of the same hand.

Note these are the **printed cores**. The finished blade carries carbon over them, two to
five plies per side depending on span station, which adds a little thickness and a little
chord. The aerodynamic effect is small and is inside the uncertainty of the drag polar.

## Expected power at hover

Blade-element momentum analysis against the measured V49 geometry, tip-loss corrected,
trimmed to 7.5 lbf per nacelle, with 0.95 gearbox and 0.83 combined motor and ESC
efficiency.

| Head RPM | Tip speed m/s | Collective at 0.75R | Shaft W | FM | Electrical W | A at 21 V | Max thrust lbf | Margin |
|---|---|---|---|---|---|---|---|---|
| 1500 | 71.8 | 20.5 | 228 | 0.666 | 290 | 13.8 | 7.5 | **1.00** |
| 1600 | 76.6 | 16.1 | 217 | 0.699 | 276 | 13.1 | 8.6 | 1.14 |
| 1700 | 81.4 | 14.1 | 218 | 0.698 | 276 | 13.2 | 9.7 | 1.29 |
| **1800** | 86.1 | 12.6 | 221 | 0.688 | **280** | 13.3 | 10.8 | 1.44 |
| 1900 | 90.9 | 11.3 | 226 | 0.673 | 286 | 13.6 | 12.1 | 1.61 |
| 2000 | 95.7 | 10.3 | 232 | 0.655 | 294 | 14.0 | 13.4 | 1.78 |

At 1400 rpm this rotor **cannot reach 7.5 lbf at all** before the blade stalls.

Two things to take from this table.

**The 280 W figure is confirmed.** At Austin's stated design RPM of 1800 the model returns
280 W electrical, against his measured 280 W. That is closer than the method deserves and it
should not be over-read, but it does mean the aerodynamic model and the real rotor agree
about this aircraft. Across a sensible range of drag-polar and stall assumptions the
prediction moves only between 267 and 295 W, so the agreement is not an artefact of one
lucky coefficient choice.

**Power is nearly flat with RPM; thrust margin is not.** Between 1600 and 2000 rpm hover
power varies by under 7 percent, but maximum thrust nearly doubles, from 8.6 to 13.4 lbf.
RPM on this rotor buys control authority far more than it costs efficiency.

> **Retraction.** Earlier in this project, working from the superseded 499.5 mm blade with
> its 46.3 degree twist, I recommended exploring **lower** head RPM on the grounds that
> 1600 was above the figure-of-merit optimum and perhaps 7 percent was available by slowing
> down. **That recommendation does not survive the corrected geometry.** The V49 blade is
> shorter, less twisted and substantially lower solidity. On this rotor the FM peak sits
> near 1600 to 1700 rpm and is very flat, while thrust margin falls away steeply below it.
> Slowing this head down is the wrong move. The sweep in doc 06 therefore runs upward from
> 1600 rather than downward from it.

### A live discrepancy worth resolving

Austin's design source says `RPM = 1800.0`. The figure quoted for the nacelles earlier in
this project was **1600**. Those are not the same operating point:

- At 1600 rpm, maximum thrust is 8.6 lbf against a 7.5 lbf hover requirement. That is a
  **1.14 margin**, and it is thin. It leaves very little for control, gust response, or a
  hot day.
- At 1800 rpm the margin is 1.44, which is defensible for a tiltrotor.

This does not block the test - the grid in doc 06 spans 1600 to 2000 and will settle it with
measurements. But it is worth asking Austin directly which number the nacelle governor is
actually set to, because if it is 1600 the aircraft has less margin than the airframe
probably wants.

## Ground effect, and why the height ladder matters

The classic Cheeseman-Bennett relation gives the thrust benefit at constant power:

```
T_IGE / T_OGE  =  1 / (1 - (R / 4z)^2)
```

where `z` is rotor height above ground and `R` is rotor radius. At R = 457 mm:

| z/R | z (mm) | z (in) | T_IGE / T_OGE |
|---|---|---|---|
| 0.5 | 229 | 9.0 | 1.333 |
| 0.75 | 343 | 13.5 | 1.125 |
| 1.0 | 457 | 18.0 | 1.067 |
| 1.25 | 571 | 22.5 | 1.042 |
| 1.5 | 686 | 27.0 | 1.029 |
| 2.0 | 914 | 36.0 | 1.016 |

**The model breaks down below z/R = 0.5.** At z/R = 0.33 the formula returns a 2.35x thrust
benefit, which is physically nonsense. Below half a radius, measure and do not predict. This
is one of the reasons the rig exists.

Two things follow:

1. Ground effect is essentially gone by z/R = 2. The residual benefit there is 1.6 percent,
   which is smaller than your measurement scatter. **The ladder therefore stops at z/R = 2**
   rather than running out to 3. At R = 457 that caps the top of the sweep at 914 mm, which
   is what makes indoor testing practical.
2. **Read the data at constant thrust, not constant power.** The table above is a thrust
   benefit. Vermont does not care that thrust rises near the ground. He cares that at his
   hover thrust the wattage is lower near the ground and climbs as the aircraft leaves it.

A caution on interpretation: ground effect reduces **induced** power only. Profile power is
unchanged. At the confirmed disc loading of 50.8 N/m^2, blade-element analysis puts induced
power at **79 percent** of shaft total at hover. So a 7 percent thrust benefit does not buy
7 percent off the watts. It buys less, though the gap is narrower than a rule of thumb
suggests. Measure it rather than scaling it.

## Why the rotor is now governed, and what that does to the test

The head is **variable pitch with a governed RPM**. The ESC reads RPM and Austin's software
holds it at a setpoint. This changes the shape of the test fundamentally:

> **Throttle percentage is an RPM setpoint, not a power setting.** Thrust comes from
> collective pitch, not from throttle.

The original throttle staircase in this package measured nothing useful under a governor;
walking throttle up simply commanded a series of RPMs while the governor absorbed the
difference. The inner loop is now a **two-dimensional grid of head RPM against collective
pitch**, and the deliverable at each height is the (RPM, pitch) pair that produces 7.5 lbf
for the fewest watts. See doc 06.

## Build the rig parametric

Austin has said plainly that the radius **will increase later**, and that he will want
deeper gear ratios as props grow. Two consequences for the build:

- Splay the legs so the feet clear a **700 mm radius** rotor, not a 457 mm one. Recutting
  legs later is annoying; cutting them long now is free.
- Express the height ladder as **z/R with a fill-in millimetre column**, not as hard-coded
  millimetres. `reduce.py` takes `--radius` for exactly this reason.
- Plan floor-to-ceiling clearance for **4.2 m** so the same room still works at a larger
  radius. At R = 457 you need far less, but you do not want to move rooms.

Post sections get recut per prop. That is expected and cheap.

## Why an axial post

The nacelle mounts on top of a single vertical post that runs down the thrust axis,
directly beneath the hub. The prop sits above the motor in hover attitude, so the entire
volume below the nacelle is clear and the post never approaches the blades.

- **No lever arm.** Load is purely axial. There is no arm ratio to measure and therefore no
  arm ratio to get wrong.
- **Height is an independent variable.** You pin it and walk away. Nothing swings.
- **Almost nothing in the flow is measured.** The load cell sits directly under the nacelle.
  It only registers what is between it and the nacelle. The post, legs and base are below
  the cell and outside the load path, so their drag does not appear in the reading.

For scale on that last point: induced velocity at the disc is about 4.5 m/s at hover, rising
to roughly 9 m/s in the contracted wake. A 25 mm tube running two feet down through that
would carry roughly a tenth of a pound of download. Below the cell, it is exactly zero.

## The load reversal - read this before you build

The nacelle is about 1200 g. With the yoke and adapter plate the dead weight above the cell
is roughly **4.5 to 5 lb, acting downward in compression**. Thrust acts upward. So as you
walk the collective up, the cell passes through **zero net load at about 4.8 lbf of thrust**,
which is 64 percent of hover and sits in the middle of every sweep you will run.

This is not a nuisance detail. It has three consequences that are handled elsewhere in the
package and are listed here so the reason is in one place:

1. Any clearance in the threaded joints shows up as a **discontinuity right in the middle of
   the data**, and it looks convincingly like real aerodynamics. This is why the jam-nut
   preload and the no-rod-ends rule in doc 03 are load-bearing requirements rather than good
   practice.
2. The cell must be calibrated in **both directions**, and continuity through zero verified.
   See doc 05.
3. The hold-down must resist roughly **8 lbf of uplift** at peak thrust.

An optional 10 lb ballast above the cell keeps it in compression throughout, but it lowers
the fixture's resonant frequency toward 2/rev, which at 1800 rpm is 60 Hz. Try preload
first.

## What this rig cannot tell you

State these plainly in the delivery note.

1. **Fountain flow.** Two rotors on a wing, in ground effect, throw wake inward and upward
   against the underside of the wing. That download exists on the real aircraft and cannot
   appear in single-nacelle data.
2. **Rotor-to-rotor interference.** Same reason.
3. **Wing download in free-air hover.** The wing sits in the wake. Not reproduced here.
4. **Trim and control margin.** This measures thrust available, not authority remaining.

What you are delivering is **isolated per-nacelle performance, in and out of ground effect,
as a function of height, at the best available RPM and pitch combination.** Airframe
integration is Vermont's problem, and saying so up front protects both of you.
