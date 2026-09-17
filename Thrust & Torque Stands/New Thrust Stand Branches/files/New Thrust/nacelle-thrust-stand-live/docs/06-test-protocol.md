# 06 - Test Protocol

## What changed, and why

This head is **variable pitch with a governed RPM**. The ESC reads RPM and Austin's software
holds it at a setpoint.

> **Throttle percentage is an RPM setpoint, not a power setting. Thrust comes from
> collective pitch.**

An earlier version of this document walked throttle from 30 to 100 percent at each height.
Under a governor that measures nothing useful: you are commanding a series of RPMs and the
governor is absorbing the difference by changing power on its own terms. That staircase is
gone.

## The three axes

| Axis | Role | Values |
|---|---|---|
| Rotor height | outer loop | z/R = 0.5, 0.75, 1.0, 1.25, 1.5, 2.0 |
| Head RPM | middle loop | 1600, 1700, 1800, 1900, 2000 |
| Collective pitch | inner loop | staircase in degrees at 0.75R |

At each height you are looking for the **(RPM, pitch) pair that produces 7.5 lbf for the
fewest electrical watts**. That pair is not necessarily the same at every height, which is
one of the more interesting things this rig can tell you.

### Height ladder

Rotor radius is **457 mm**. Measure **rotor plane to floor** with a tape at every step. Do
not trust the cut post length.

| Step | z/R | z (mm) | z (in) | Measured (fill in) | Purpose |
|---|---|---|---|---|---|
| 1 | 0.5 | 229 | 9.0 | | Deep in ground effect |
| 2 | 0.75 | 343 | 13.5 | | |
| 3 | 1.0 | 457 | 18.0 | | |
| 4 | 1.25 | 571 | 22.5 | | |
| 5 | 1.5 | 686 | 27.0 | | |
| 6 | 2.0 | 914 | 36.0 | | **OGE baseline** |

The ladder stops at z/R = 2. The residual Cheeseman-Bennett benefit there is 1.6 percent,
which is below your scatter, so running out to z/R = 3 costs a taller room and buys nothing.

Optional step below z/R = 0.5 if Vermont wants the very-low-hover case. The Cheeseman-Bennett
model is invalid there, which is precisely why it is worth measuring. Expect it to be noisy:
recirculation gets unsteady close to the ground.

**If the radius changes later**, recompute this table as z/R times the new R. Do not reuse
the millimetre column.

### RPM ladder

| Setpoint | Tip speed | Predicted hover W | Predicted max thrust | Margin |
|---|---|---|---|---|
| 1600 | 76.6 m/s | 276 | 8.6 lbf | 1.14 |
| 1700 | 81.4 m/s | 276 | 9.7 lbf | 1.29 |
| 1800 | 86.1 m/s | 280 | 10.8 lbf | 1.44 |
| 1900 | 90.9 m/s | 286 | 12.1 lbf | 1.61 |
| 2000 | 95.7 m/s | 294 | 13.4 lbf | 1.78 |

Predicted hover power is nearly flat across this range, so **do not expect a dramatic
optimum**. If the measured spread across the RPM ladder is under about 5 percent, that is
the real answer and not a failed experiment. The finding in that case is "RPM is free, so
choose it for thrust margin," which is a perfectly good result to hand Vermont.

Run the full RPM ladder at the **OGE baseline height** and at **one low height**. At the
intermediate heights you can run only the two or three best RPMs from those, unless the
optimum is moving with height, in which case run them all.

### Collective staircase

At each height and each RPM, step collective in **degrees at 0.75R**, using the calibration
from doc 05a. Suggested steps, adjusted to bracket 7.5 lbf with points either side:

| RPM | Suggested collective steps at 0.75R (deg) |
|---|---|
| 1600 | 6, 9, 11, 13, 15, 17 |
| 1700 | 5, 8, 10, 12, 14, 16 |
| 1800 | 4, 7, 9, 11, 13, 15 |
| 1900 | 4, 6, 8, 10, 12, 14 |
| 2000 | 3, 6, 8, 10, 12, 14 |

Predicted hover pitch is 16.1 degrees at 1600 rpm falling to 10.3 at 2000. You need at least
two measured points **below** and one **above** 7.5 lbf at each RPM so the interpolation is
bracketed rather than extrapolated.

Hold each step **five seconds** and record the **settled** value, not the peak. Run the
staircase up and then back down, so you can see hysteresis and thermal drift.

## Before any run: two calibrations you cannot skip

These are done once, on the bench, and are documented in **doc 05a**.

1. **Servo microseconds to blade pitch at 0.75R**, on both blades, with a tracking check.
2. **Throttle command to governed RPM**, at flat pitch.

Without the first you have no inner axis, only servo counts. Without the second you cannot
confirm the governor is doing what you asked. Do them in that order.

The load cell calibration in doc 05 must also be complete, **in both directions**, with
continuity through zero verified. This rig passes through zero net load at around 4.8 lbf of
thrust and it does so in the middle of every sweep.

## Per-run sequence

1. Set the post section. **Measure and record the actual rotor height.**
2. Bring the rig to full running configuration and power it for **two minutes** so it
   settles thermally before you tare against it.
3. **Tare** with the motor off, nacelle mounted, rig completely settled. Send `t`. Record
   the raw offset. The tare is what removes the nacelle's dead-weight compression, so every
   reading after it is pure thrust.
3a. **Confirm the sign before the first run of the day.** Send `d` and check `sign : -1`,
   then lift the nacelle mount by hand and confirm `r` goes **positive**. If it goes
   negative, someone recalibrated and did not send `f`. Fix it now; a whole campaign logged
   with the sign backwards looks perfectly plausible until you plot it.
4. Watch the zero for **30 seconds**. If it walks, stop and find out why. Do not proceed.
5. Send `s` to start streaming.
6. Spool up to the target governed RPM **at minimum collective**.
7. Confirm the governor has settled at the setpoint. Record the **flat-pitch point**: thrust
   should be near zero and the watts you see there are drivetrain and profile drag. This
   point is useful and free.
8. Walk the collective staircase up, five seconds per step. At each step log thrust, volts,
   amps, and the **actual** RPM, not just the commanded one.
9. Walk it back down through the same steps.
10. Return to minimum collective, spool down.
11. Motor off, rig settled. **Tare again** and confirm the zero returns.

Then repeat from step 6 for the next RPM setpoint. Height is the outer loop, so you only
move the post once per height.

## The same sequence in `tools/live.py`

The steps above are written as raw serial commands, which is what you send from the Arduino
Serial Monitor or `screen`. In the browser dashboard they map to controls, and three of them
get easier rather than just different.

| Step | In `live.py` |
|---|---|
| 3, tare | **Tare** button |
| 3a, confirm the sign | The settings line under the live number shows `sign` continuously. Lift the mount and watch the big number go positive. No `d` needed |
| 4, watch the zero for 30 s | The strip chart and the **30 s** statistics line. Read the standard deviation and the peak-to-peak band instead of eyeballing a scrolling column of text |
| 5, 10, start and stop streaming | **Stream** button, lit while active |
| 8, log each plateau | **Capture point**. Fill in height, RPM, collective, throttle, volts, amps. It averages the last 5 seconds and writes the `run-log.csv` row, computing `z_over_R` for you |
| 11, tare again | **Tare**, then compare against the offset you recorded at step 3 |

Three things worth knowing that change how you run the sequence:

**Step 4 gets a real criterion.** "If it walks, stop" is a judgement call when you are
reading numbers scroll past. The statistics panel gives you a number: note the 30 s standard
deviation with the rig cold and settled, and treat any later drift well outside that band as
the zero walking.

**Step 8 stops being transcription.** You are averaging five seconds automatically rather
than picking a plateau value by eye, and the row lands in the CSV in the schema `reduce.py`
expects. The captured points also appear on the power chart as you go, so you can see the
campaign taking shape against the BEMT prediction and notice a bad point while the rig is
still at that height.

**Everything is logged regardless.** `logs/stream-*.csv` records every sample that arrives,
whether or not you captured a point. If a run looks wrong afterwards you still have the raw
trace of it.

What does not change: the tare discipline, the sign check, the flat-pitch point at step 7,
walking the staircase both up and down, and discarding the run if the second tare has
wandered. None of those are about the readout tool.

Step 11 is the one people skip. If the second tare has wandered, something shifted mid-test
and the run is not trustworthy. Throw it out and find out what moved. Ten seconds of work
that catches the failures which otherwise look like real data.

## Two governor failure modes to watch

**Saturation.** If the governor runs out of authority it will droop below the setpoint while
still reporting that it is trying. You are then silently off the grid: your "1800 rpm" row
is actually 1650. This is why step 8 logs actual RPM. If actual departs from commanded by
more than about 2 percent, the row is not what its label says.

**Hunting.** On a rigid stand there is no airframe mass to damp the governor loop, so it can
oscillate in a way it never would in flight. It shows as a periodic wobble in both thrust
and current. This is a **gain problem, not a load cell problem**, and chasing it in the
mechanical build will waste your afternoon. If it appears, back the governor gain off and
note it in the log.

## What to record per plateau

Fill in `data/run-log-template.csv`.

| Field | Source | Note |
|---|---|---|
| height_mm | tape measure | measured, not nominal |
| z_over_R | computed | height divided by 457 |
| head_rpm_cmd | your setpoint | what you asked for |
| head_rpm_actual | tach or telemetry | **what you got.** These differ. |
| collective_deg | doc 05a calibration | degrees at 0.75R |
| servo_us | servo command | the raw number, for traceability |
| throttle_pct | transmitter | now only a governor setpoint record |
| thrust_lbf | load cell, settled value | |
| volts | inline watt meter | **under load**, not resting voltage |
| amps | inline watt meter | not ESC telemetry |
| pack_soc | your note | state of charge at start of run |
| notes | you | vibration, sound changes, drift, anything odd |

`collective_deg` and `head_rpm_actual` are the two new columns that make the reduction
possible. Without them the run is not analysable.

## Safety note specific to this protocol

You will be spending time at **high collective and high RPM** looking for the thrust
ceiling. At 2000 rpm this rotor can produce over 13 lbf on a stand that weighs a few pounds.
Read doc 09 before the first spin, and hold the rig down properly.
