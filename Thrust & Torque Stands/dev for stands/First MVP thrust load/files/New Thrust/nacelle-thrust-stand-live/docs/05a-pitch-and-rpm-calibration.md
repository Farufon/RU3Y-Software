# 05a - Pitch and RPM Calibration

Do this **before** the load cell work in doc 05 is put to use, and certainly before any run
in doc 06. It is bench work, no rotor spinning for part one.

Two calibrations:

1. Servo microseconds to **blade pitch at 0.75R**
2. Throttle command to **governed RPM**

Neither takes long. Skipping either means your inner test axis is servo counts, which are
meaningless to anyone reading the report and not comparable between builds.

---

## Part 1 - Servo microseconds to blade pitch

### Why 0.75R

Blade pitch varies continuously along the span; this blade has **33.3 degrees** of built-in
washout between r/R 0.22 and the tip. So "the pitch" is not a number unless you say where.
The rotor convention is the three-quarter radius station, and that is what the predictions in
doc 01 and doc 06 are quoted at.

At R = 457 mm, **0.75R is r = 343 mm from the hub centreline**. Mark it on the blade with a
fine pen before you start. On the supplied V49 blade the chord there is 33.8 mm, essentially
the widest part of the blade.

### What you need

- A pitch gauge that clamps on the blade. A digital-readout heli pitch gauge is ideal.
- A servo tester or your transmitter, able to command specific microsecond values.
- A way to hold the head still with the blades free to feather.

### Procedure

1. Support the nacelle so the head cannot rotate but the blades can pitch freely.
2. Level the reference. Most pitch gauges zero against the shaft or the head; follow the
   gauge's own convention and **write down which one you used.**
3. Clamp the gauge at the 0.75R mark on **blade A**.
4. Command a series of servo values across the working range and record pitch at each:

| Servo (us) | Pitch at 0.75R, blade A | Pitch at 0.75R, blade B | Difference |
|---|---|---|---|
| 1100 | | | |
| 1200 | | | |
| 1300 | | | |
| 1400 | | | |
| 1500 | | | |
| 1600 | | | |
| 1700 | | | |
| 1800 | | | |
| 1900 | | | |

5. Repeat every row on **blade B without moving anything else.**

### What good looks like

- **Linearity.** Pitch against microseconds should be close to a straight line over the
  working range. Some curvature at the extremes is normal; a kink in the middle is not, and
  usually means a linkage is binding or a ball link is at the end of its travel.
- **Tracking.** Blade A and blade B should agree within about **0.2 degrees** at every step.
  A constant offset means one pitch link needs adjusting. An offset that **grows** with
  collective means the two links are at different geometry, which is worse and needs fixing
  before you fly, never mind before you test.
- **Range.** You need to reach at least 18 degrees at 0.75R to find the thrust ceiling at
  1600 rpm. Confirm you have it before you build the test matrix.

Fit a straight line to the blade-A column and keep the slope and intercept. That is your
conversion for the whole test campaign. Write it at the top of the run log.

> **The 45 degree pitch-link phase advance is a different thing.** The control system has a
> 45 degree advance to counter rotor lag. That is about *when* in the rotation a control
> input arrives, not *how much* pitch a servo command produces. It has no bearing on this
> calibration. Do not let the number 45 and the number 33.3 (the blade's built-in twist) get
> mixed together in your notes; they are unrelated quantities that happen to be similar in
> magnitude.

---

## Part 2 - Throttle command to governed RPM

This part does spin. Read doc 09 first, and do it at the **OGE height** with the rig fully
tied down.

### Procedure

1. Set collective to **minimum**. You want the governor working against as little load as
   possible so it can hold the setpoint cleanly.
2. Spool up gently to the lowest setpoint you intend to use.
3. Let it settle a full **ten seconds**. Governors take longer to settle than you expect.
4. Record commanded throttle and **measured** RPM, from an optical tach or telemetry.
5. Step through the ladder:

| Throttle cmd | Target RPM | Measured RPM (flat pitch) | Delta |
|---|---|---|---|
| | 1600 | | |
| | 1700 | | |
| | 1800 | | |
| | 1900 | | |
| | 2000 | | |

6. Spool down.

### What good looks like

- Measured RPM within about **2 percent** of target at flat pitch. If it cannot hold the
  setpoint with no aerodynamic load on it, it certainly will not hold it at 15 degrees of
  collective.
- **Stable.** Watch for hunting: a slow periodic surge in RPM and current. On a rigid stand
  there is no airframe mass to damp the loop, so a governor that is perfectly well behaved in
  flight can oscillate here. If it hunts, reduce the governor gain and note the value you
  used, because it is part of the test conditions.

### Repeat under load, once

After the pitch calibration is done and you have run one height, come back and check the
governor holds its setpoint at **hover collective**, not just flat pitch. This is the
condition that matters and it is the one where saturation shows up.

If the governor droops under load, every row in your data is mislabelled. That is why
`head_rpm_actual` is a required column in the run log and not an optional one.

---

## Record these before the first test run

Put all of this at the top of the run log, or in a file beside it:

- Pitch gauge reference convention (shaft, head, or flat plate)
- Servo microseconds to pitch: slope and intercept, blade A
- Blade A to blade B tracking error, worst case across the range
- Throttle command for each RPM setpoint, at flat pitch
- Governor gain, if you changed it
- Ambient temperature, and pack chemistry and cell count

None of it is interesting on its own. All of it is the difference between a result someone
can reproduce and a spreadsheet nobody can defend.
