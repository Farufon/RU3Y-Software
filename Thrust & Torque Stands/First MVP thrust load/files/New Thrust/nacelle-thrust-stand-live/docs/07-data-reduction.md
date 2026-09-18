# 07 - Data Reduction

## Running the script

```
source ~/venvs/forcerigs/bin/activate
cd tools
python3 reduce.py ../data/my-runs.csv --thrust 7.5 --radius 457
```

Standard library only, no install, so this one will run on any Python 3 whether or
not the environment is active. Activate it anyway, so there is one habit rather than
three rules. See `docs/15-python-venv.md`.

## What it does

For each height **and each governed RPM**, the script sorts that cell's plateaus by thrust
and **interpolates the electrical power at your target thrust**. Then, for each height, it
picks the RPM that got there for the fewest watts.

That converts a set of thrust-vs-collective curves into the single curve Vermont asked for:
watts vs height at constant thrust, at the best available operating point.

Sample output shape:

```
   z mm    z/R    watts  best RPM  pitch@0.75R   vs OGE  C-B thrust
-------------------------------------------------------------------
    229   0.50    228.4      1700        12.48    0.822       1.333
    343   0.75    255.6      1700        14.79    0.920       1.125
    457   1.00    268.9      1700        15.60    0.968       1.067
    571   1.25    273.1      1800        15.98    0.983       1.042
    686   1.50    275.2      1800        16.18    0.991       1.029
    914   2.00    277.6      1800        16.38    1.000       1.016
```

The `vs OGE` column is the answer. It says how much cheaper hover is near the ground, at
constant thrust, relative to the free-air baseline. The climb-out cost is the same number
read in the other direction.

`--by-rpm` prints the full height-by-RPM grid instead of only the winning cell. Use it: if
the best RPM shifts with height, that is a real result and worth reporting.

The script also **warns on any row where commanded and actual RPM differ by more than
2 percent.** Those rows are not the operating point their label claims, and they are the
most common way this test goes quietly wrong.

## Reading it correctly

**Constant thrust, not constant power.** This is the interpretation error that would ruin
the deliverable. The Cheeseman-Bennett column is a *thrust* ratio at constant power, and it
is included only as a sanity reference. Your measured `vs OGE` is a *power* ratio at
constant thrust. They are not the same quantity and should not be compared directly.

**The power saving is always smaller than the thrust benefit.** Ground effect reduces
induced power only; profile power is unchanged. Blade-element analysis of the actual blade
puts induced power at **70 to 82 percent** of the shaft total at hover, so a 7 percent thrust
benefit buys less than 7 percent off the watts. If your measured saving is close to the C-B
thrust ratio, be suspicious.

**Below z/R = 0.5 the model gives nonsense** and the script prints `n/a` rather than a
number. At z/R = 0.33 the formula returns a 2.35x benefit, which is physically impossible.
Measure that region; do not predict it.

## Sanity checks before delivery

| Check | Expected |
|---|---|
| OGE watts at 7.5 lbf | **267 to 295 W** per nacelle across 1600-2000 rpm. Predicted 280 W at 1800. See doc 01. |
| Monotonicity | Watts should rise smoothly with height and flatten past z/R = 2 |
| Collective at hover | 16 deg at 0.75R at 1600 rpm, falling to about 10 deg at 2000. Far outside that range, check the doc 05a pitch calibration. |
| Thrust margin | Max thrust should reach 8.6 lbf at 1600 rpm and 13.4 at 2000. Much less means the pitch calibration or the blade is not what we think. |
| Up vs down staircase | Curves should overlay. Divergence means hysteresis, thermal drift, or a loose joint. |
| Through the load reversal | No step or kink near 4.8 lbf. If there is one, it is joint clearance, not aerodynamics. See doc 05. |
| Second tare | Returns to the first. If not, discard the run. |

If OGE lands much above 330 W, suspect the pitch calibration, a KV mismatch, or ESC timing.
If it lands below 250 W, recheck the load cell calibration before believing it.

Austin's independently measured figure for this nacelle is **280 W**, and the blade-element
prediction lands on 280 W at his stated 1800 rpm. Two methods agreeing that closely is
partly luck, but it does mean a measurement far from 280 W deserves suspicion before it
deserves a press release.

## What goes in the delivery note

State plainly:

1. **What was measured.** Per-nacelle static thrust and electrical power at the pack, as a
   function of rotor height above ground, at a stated pack voltage and state of charge.
2. **How it was measured.** Axial post, S-beam inline directly under the nacelle,
   calibration traceable to known weights, linearity checked.
3. **What was not measured.** Fountain flow, rotor-to-rotor interference, wing download,
   control margin. Single-nacelle isolated data does not contain them.
4. **The known error budget.** Cell accuracy class, watt meter accuracy, height measurement
   tolerance, and observed run-to-run repeatability.

Point 3 is the one that protects you. Airframe integration is his side of the line, and
saying so up front is not a hedge, it is accurate scoping.

## Plotting

The script prints a table rather than drawing a chart, deliberately: the table pastes
straight into a spreadsheet or an email. If you want a chart, plot `watts` against `z (mm)`
with a horizontal reference line at the OGE baseline. That one picture is the whole
deliverable.
