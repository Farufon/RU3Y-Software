# 05 - Calibration

The cell is only as honest as what you calibrated it against. Do this before any data goes
to Vermont.

## What calibration actually is

The HX711 returns raw counts. Calibration establishes one number, `calFactor`, in **counts
per pound of force**. The sketch stores it in EEPROM so it survives power cycles.

Tare and calibration are different things:

- **Tare** sets the zero point. It changes every run.
- **Calibration** sets the slope. It changes only if you change the mechanical setup.

## Which way the cell is loaded, and why `f` is mandatory

The stack is: **legs, post, S-beam load cell bolted to the top of the post, nacelle bolted
on top of the cell.** Everything above the cell's upper face is what gets measured.

The cell is **bolted through studs and jam nuts at both ends**. It is not resting on
anything and nothing is resting loose on it. That is what makes the rig read **tension as
well as compression**, which this measurement requires: nacelle dead weight pushes **down**
on the cell, and rotor thrust pulls **up** on it, and the cell passes continuously through
zero between them.

Consequences that run through the whole procedure:

- **You tare with the nacelle mounted and the motor off.** That sets zero at the dead-weight
  compression point, so every later reading is pure thrust.
- **Calibration is done in compression**, by stacking known weight on the nacelle mount.
  There is nowhere to hang a weight for a tension pull, and the post prevents inverting the
  stand.
- **`c` always makes the calibration direction positive.** So calibrating in compression
  makes *downward* positive, and thrust pulling up would log as negative.
- **Therefore `f` is required after every calibration.** Not "if it reads negative". Always.
  It is the step that makes thrust positive on this geometry.

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
8. Send `d`. Confirm `calFactor` is no longer `1.0000`.
9. Remove the weight. Reading should return to near zero.
10. Apply a **second, different** known weight and send `r`. It should read close to that
    weight. This is the check that the factor is real rather than merely stored.

### Choosing the weight

Use something in the **10 to 15 lbf** range if you can. The cell is 20 kg (44.1 lbf full
scale, 150% safe overload), so 15 lbf is about a third of range and carries no risk, and it
sits just above your expected peak thrust rather than being extrapolated up to it. A 3 lb
weight will produce a working factor, but the noise band is a larger fraction of it.

**Gravity is the only accurate force reference on the bench.** Spring gauges, luggage
scales and fish scales are all less accurate than the cell you are calibrating, so do not
pull by hand against one. On this rig the weight is **stacked on the nacelle mount**, not
hung: the cell is under the nacelle, so there is nothing below it to hang from.

Water is a good cheap standard: one US gallon is **8.345 lb**, it is self-levelling so the
centre of mass behaves, and adding it a gallon at a time gives you a multi-point linearity
check for free instead of a single point. Weigh the empty container and include it.

**Do not try to calibrate in tension.** The post is in the way, so the stand cannot be
inverted, and converting a hanging weight into an upward pull needs a pulley. A plain
bushing pulley eats two or three percent in friction, which reads as a systematically light
calibration and leaves no trace in the data. Calibrate in compression and flip the sign;
the next section explains why that is sound rather than a compromise.

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

Push down on the nacelle mount by hand. Note the sign. Now **lift** it. The sign must
reverse. If it does not, the cell is not seeing axial load properly, or one of the two studs
is not carrying tension, and something in the stack is shunting force around the cell.

That both directions read at all is the point of bolting the cell at both ends. A cell that
merely had weight resting on it would read compression and then unload to zero, and you
would lose every reading above dead weight, which is most of the useful range.

With the calibration done and `f` sent, **thrust must read positive.** Confirm it by hand
before the first spin.

### `f` is required, it is not a fallback

`c` sets the sign from whichever way the signal moved. On this rig you calibrate in
compression, because that is the only direction you can apply a known force. So `c` makes
**down** positive, and thrust pulling **up** would log negative for the whole campaign.

Send `f` once after every `c`, then confirm: `d` shows `sign : -1`, and lifting the mount by
hand gives a positive `r`.

**Do not use the green/white wire swap instead.** It reaches the same place, but then a
future recalibration plus `f` would flip you back the wrong way. Keep the wiring as
documented and let `f` carry the sign.

**Order matters, and this is easy to get wrong.** `c` re-derives the sign every time it
runs, so any recalibration silently undoes a previous `f`. The sequence is always:

1. `t` with the rig settled
2. apply the known weight, `c <lbf>`
3. `f`
4. `d`, confirm the sign
5. lift by hand, `r`, confirm positive

Do `f` last, every time.

Calibrating in compression is not a compromise. An S-beam is a symmetric structure and this
cell's linearity is specified at 0.03% of full scale, so its counts per lbf are the same in
both directions to well inside anything you can measure here. And as the next section
explains, this rig crosses zero mid-sweep regardless, so you are using both sides whichever
way you calibrate.

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

You cannot apply a known tension force on this geometry without rigging a pulley, and the
stand cannot be inverted because the post is under it. So the working answer is:

1. Calibrate in **compression**, weights stacked on the nacelle mount, then `f`.
2. **Trust the cell, check the joints.** An S-beam is a symmetric structure and this cell is
   specified at 0.03% of full scale for linearity, so its counts per lbf are the same in
   both directions to far inside anything you can resolve here. What is *not* guaranteed
   symmetric is your load path: a joint that takes compression through a shoulder but
   tension through a thread will behave differently either side of zero. That is a
   mechanical fault, and no amount of calibrating finds it. The through-zero sweep below
   does.
3. **Optional, once:** if you want the tension scale factor measured rather than assumed,
   take the cell off the rig and bench-test it on a table with a hook in each end. Use a
   ball-bearing sheave and a truly vertical cord. This validates the cell but not the
   installed load path, so it is the lesser of the two checks.

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
