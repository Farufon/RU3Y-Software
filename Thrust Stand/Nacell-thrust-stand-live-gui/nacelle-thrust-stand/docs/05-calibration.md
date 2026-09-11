# 05 - Calibration

The cell is only as honest as what you calibrated it against. Do this before any data goes
to Vermont.

## What calibration actually is

The HX711 returns raw counts. Calibration establishes one number, `calFactor`, in **counts
per pound of force**. The sketch stores it in EEPROM so it survives power cycles.

Tare and calibration are different things:

- **Tare** sets the zero point. It changes every run.
- **Calibration** sets the slope. It changes only if you change the mechanical setup.

## Procedure

Assemble the stand fully, **prop removed**, in the same orientation you will test in.
Calibrating in a different orientation gives you a different answer.

1. Connect USB, open the serial monitor at **115200 baud**, set line ending to Newline.
2. Send `d`. Confirm `HX711 ready : yes`. If not, check DT/SCK and 5V/GND.
3. Let it sit powered for two minutes. Strain gauges drift with temperature and you want
   the electronics in a settled thermal state.
4. Send `t` to tare. Everything settled, nothing touching the rig.
5. Send `r` a few times. Should read within a few hundredths of zero. If it wanders, you
   have a mechanical or noise problem. Fix it before continuing.
6. Hang or apply a **known weight** at the nacelle mount, along the post axis.
7. Send `c 5.0` (substitute your actual weight in lbf). The sketch computes and saves
   `calFactor`, and flips the sign automatically if the signal came out negative.
8. Remove the weight. Reading should return to near zero.

## Two-point plus linearity

The above is a two-point calibration: zero and one known load. Now verify the middle.

| Applied | Made from | Expected | Measured | Error |
|---|---|---|---|---|
| 0 lb | — | 0.00 | | |
| 2 lb | 2 | 2.00 | | |
| 5 lb | 5 | 5.00 | | |
| 7 lb | 2 + 5 | 7.00 | | |
| 10 lb | 10 | 10.00 | | |
| 12 lb | 2 + 10 | 12.00 | | |
| 0 lb | — | 0.00 | | |

Every row is buildable from the 2, 5 and 10 lb weights in the bill of materials. The 12 lb
row is worth doing because it brackets your expected peak thrust rather than interpolating
to it.

Fill this in. Two things to look for:

- **Linearity.** Errors should be small and not systematically curved. The cell itself is
  good to about 0.013 lb, so anything over 0.1 lb is coming from your mounting or your
  reference weights, not the sensor. Over 0.25 lb wants investigating properly.
- **Return to zero.** The last row matters as much as the others. If it does not come back,
  something is slipping, creeping, or the cell was overloaded.

## Direction check

Push down on the nacelle mount by hand. Note the sign. Now lift it. The sign should reverse.
If it does not, the cell is not seeing axial load properly and something in the stack is
shunting force around it.

Thrust should read **positive**. If it reads negative during a spin test, send `f` to flip
the sign, or swap the green and white wires. Do not remount anything.

## Bidirectional calibration - required on this rig

**Read this before you calibrate.** This stand does not stay in tension.

The nacelle is about 1200 g. With the yoke and adapter plate, roughly **4.5 to 5 lb of dead
weight sits on the cell in compression** before the rotor turns at all. Thrust acts upward,
against that. So as collective comes up, net load on the cell falls, reaches **zero at about
4.8 lbf of thrust**, and then reverses into tension.

That zero crossing is at **64 percent of hover thrust**. It is not at the edge of the range
where you could ignore it. It is in the middle of every sweep you will run.

Three things follow.

### Calibrate in both directions

A single-direction calibration is not enough. Do this:

1. Calibrate in **compression** as normal, using the procedure above with weights stacked on
   the nacelle mount.
2. Then calibrate in **tension**, pulling down through the mount, or by inverting the
   fixture if that is easier to rig.
3. Compare the two scale factors. They should agree within about **1 percent**. A larger
   difference means the load path is not symmetric, usually a joint that takes compression
   through a shoulder but tension through a thread.

### Verify continuity through zero

This is the check that matters most and it takes two minutes.

1. Load the cell to roughly **3 lb compression**.
2. Remove load in small increments, perhaps 0.25 lb, reading at each step, **through zero**
   and on into about 2 lb of tension.
3. Plot it or just read down the column.

You are looking for a **step, flat spot, or kink at the crossing**. Any of those is
mechanical clearance in a threaded joint taking up as the load reverses.

> **This is the failure that ruins the deliverable.** A joint with a few thou of clearance
> produces a discontinuity right at 4.8 lbf of thrust, in the middle of your collective
> sweep, and it looks exactly like a real aerodynamic effect. It is smooth, repeatable, and
> entirely fictional. You will be tempted to explain it. Do not; find it and remove it.

If you see it: check the jam nut preload on both studs, confirm nothing in the stack is
relying on a thread to carry tension, and confirm there are no rod ends anywhere in the load
path. Doc 03 covers all three. Re-run this check until the curve through zero is clean.

### Hold-down

At peak thrust the rig sees about **8 lbf of uplift** net of dead weight. Anchor for it.

### Optional ballast, and why it is second choice

Adding about 10 lb of ballast above the cell keeps it in compression across the whole sweep,
which sidesteps the reversal entirely. The cost is that it lowers the fixture's resonant
frequency toward 2/rev, which at 1800 rpm is 60 Hz, and a fixture resonance sitting on a
rotor harmonic will contaminate every reading you take.

Try preload and a clean load path first. Use ballast only if the through-zero check will not
come clean.

## Realistic accuracy of an installed system

The ATO DYLY-102 quotes **0.03 percent of full scale**, which is about 6 g or 0.013 lb on a
20 kg cell. That is the cell alone, on a bench, in a lab, and it is very good.

SparkFun's guide gives a more honest figure for a **built system**: load cell measurements
can be off by roughly plus or minus 5 percent once you account for temperature, creep,
vibration, drift, and assorted electrical and mechanical interference.

Five percent of 7.5 lbf is 0.375 lb. That is worth knowing before you quote a number to
Vermont, and it is the reason the protocol insists on re-taring every run, checking the
zero afterwards, and running the collective staircase both up and down. Those steps are what pull you
back from the 5 percent figure toward the 0.03 percent one.

Put your observed run-to-run repeatability in the delivery note rather than the datasheet
number. It is the honest figure and it is one you actually measured.

## When to recalibrate

- Anything in the stack was unbolted and rebolted
- The cell was overloaded, dropped, or the stud bottomed out
- The ambient temperature changed a lot between sessions
- Readings look implausible

Tare, by contrast, happens **every single run**. See doc 06.

## Common failures

| Symptom | Likely cause |
|---|---|
| Reads zero always, `HX711 ready: NO` | DT/SCK swapped, or no 5V/GND |
| Wildly noisy with motor off | Bad solder on the cell wires, or shield grounded at both ends |
| Clean with motor off, hash under power | Cable routing near motor phase leads. See doc 04. |
| Signal too small during `c` | Weight not actually applied along the axis, or load shunted by a brace |
| Zero drifts steadily | Thermal, if slow. Mechanical creep or a loose joint, if fast. |
| Reading only a fraction of applied weight | Something bridges the cell. Load is bypassing it. |
