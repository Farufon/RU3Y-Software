# 14 - Torque stand (separate rig, second Nano)

Measures the reaction torque in the nacelle housing, which gives you shaft
watts directly instead of the assumed 79% drivetrain efficiency. Torque times
angular velocity is shaft power; divide by electrical watts and you have the
real number.

This is a **separate stand with its own board and its own USB port**. Nothing
here touches the thrust rig.

Diagrams, printable: `wiring-torque-stand.svg`, `torque-stand-elevation.svg`,
`torque-stand-plan.svg`, all in this folder.

## Principle

The rotor pushes air down and the housing feels the torque backwards. Let the
whole upper assembly rotate on a vertical axis, then stop it with an arm
pressing on a load cell at a known radius.

Nothing rotates in service. Full scale corresponds to a few thousandths of a
degree of cradle movement.

Torque is a free vector, so the cradle axis only has to be **parallel** to the
rotor shaft, not collinear with it. That is why the bearings can sit under the
nacelle rather than around it.

## Cell sizing

ATO micro S-type, 5 kg, M6 male thread both ends. At the 150 mm arm:

Sized against Austin's measured targets, both per nacelle: hover at 1800 rpm
and 446 W, cruise after transition at 1000 rpm and 185 W. Shaft power assumes
the nominal 0.95 ESC x 0.83 motor until this rig says otherwise.

| | torque | force at cell | % of 5 kg full scale |
|---|---|---|---|
| Cruise, 1000 rpm, 185 W | 1.39 N·m | 9.3 N | 18.9 |
| Hover, 1800 rpm, 446 W | 1.87 N·m | 12.4 N | 25.4 |
| Peak, same 1.6x over BEMT | 5.31 N·m | 35.4 N | 72.2 |
| Cell full scale | 7.35 N·m | 49.0 N | 100 |

Resolution is roughly 718,000 counts per N·m, so the 251-count noise floor is
0.00035 N·m, about 0.02% of working torque. Noise is nowhere near the limiting
error. The error budget below is.

A longer arm gives **less** force at the cell for the same torque, not more.
The arm is chosen so peak torque lands at 60 to 80% of full scale, and 150 mm
puts it at 72%. Do not shorten it. Against the old BEMT-derived numbers 97 mm
looked optimal; against the measured ones it would put that same peak at 112%
of full scale and destroy the cell.

## Mechanical

Bottom to top: base plate, fixed column, bearing tower, two bearings, hollow
shaft, cradle disc, nacelle.

**Base plate.** 400 x 340 x 10 mm minimum. The anchor block sits at
(150, 109) mm from the axis, so the plate has to reach x = 172 and y = 144
before any edge margin. The original 320 x 240 in the script left the anchor
hanging off two edges. That is now corrected, but 400 x 340 is past most print
beds, so **cut this one from aluminium tooling plate or 12 mm ply** and print
only the tower, cradle, arm and anchor.

**Bolt the base down.** Thrust on this rig is unmeasured but still there. At
7.5 lbf the rotor is trying to lift the entire stand off the bench.

**Bearings: 6004-ZZ, not 2RS.** Contact seals add stiction, and stiction on a
joint that moves a thousandth of a degree shows up as hysteresis in the
reading. Shielded bearings drag far less. 60 mm clear between them so the
pair can take the tipping moment from any in-plane rotor force.

**Axial retention.** Thrust pulls the cradle and shaft upward. A shaft collar
clamped under the lower bearing's inner race is the only thing stopping it.
The load path is collar to lower inner race, through the balls, to the outer
race, onto the tower shoulder. 33 N of axial load through a 6004 is nothing,
but the collar must actually be tight. Check it before every run.

**Hollow shaft, 20 OD x 12 ID.** The motor loom runs down the middle, on the
rotation axis, where twisting it costs almost nothing.

**Nothing else may touch the cradle.** Not a zip tie, not a tach wire, not a
throttle lead resting on the bench. Everything that crosses the joint goes
down the tube.

## Error budget, in order of size

1. **Loom stiffness.** This dominates. A stiff 12 AWG bundle leaving the
   cradle off-axis acts as a torsion spring in parallel with the load cell and
   reads as a fraction of the torque you are trying to measure. Run it on the
   axis, leave it slack, and dress it identically for every run. If you change
   the dress, re-tare and re-check.
2. **Bearing stiction.** ZZ bearings help. So does the rotor: at a few hundred
   Hz the vibration dithers the joint out of stiction, so the running
   measurement is better behaved than pushing the arm by hand. Do not judge
   the rig by how it feels statically.
3. **Rod end clearance.** Torque is one-signed in service. Arrange the
   geometry so the cell is always loaded the same way and never crosses zero,
   or the rod-end clearance becomes a dead band right where you are measuring.
   In the plan view above the arm swings away from the anchor, putting the cell
   in tension, which is what rod ends prefer.
4. **Tare drift.** Re-tare with the motor stopped between grid points.
5. **Arm flex.** Not an error in force, but it changes where the pin ends up.
   Keep the arm thick.

## Wiring

Identical to the thrust stand, on its own board.

```
HX711 VIN -> Nano 5V        Cell red   -> E+
HX711 GND -> Nano GND       Cell black -> E-
HX711 DAT -> Nano D2        Cell green -> A+
HX711 SCK -> Nano D3        Cell white -> A-
HX711 VIO    unconnected    Cell shield-> Nano GND, at the Nano end only
RATE switch on L
```

Verify the wire colours with a meter rather than trusting them. Measure all
six pairs. The two highest readings are the diagonals; of those two the
excitation pair reads higher than the signal pair. Adjacent pairs read about
three quarters of that.

## Firmware

`firmware/torque_stand/torque_stand.ino`. Same library (Bogdan Necula's HX711
Arduino Library), same IDE 1.8.19 recipe as doc 13, same command set as the
thrust sketch with two additions.

Reading line: `n,ms,Nm,N,raw`. The fourth column is the tangential force at
the cell pin, there so you can see how close you are to overloading it.

```
h ?          help
t            tare (32 samples)
r            one reading (8)
s            toggle stream
c <N.m>      calibrate against a known applied torque (32)
a <mm>       set arm radius, for the force column only
f            flip sign
z            raw counts (32)
d            dump settings
w            force EEPROM write
```

`calFactor` is stored in **counts per N·m**, so the arm radius never enters
the torque maths. `a` exists only to compute the force column.

## Calibration

You cannot do this by hanging a weight off the arm. A vertical load on a
horizontal arm is a bending moment about a horizontal axis, and the cradle
does not respond to that. You need a **horizontal** force.

1. Assemble everything, loom dressed exactly as it will be for the run.
2. Attach a string to the arm, run it horizontally over a ball-bearing pulley
   clamped at the bench edge, and hang a known mass off the end.
3. The string must leave the arm **tangentially**, that is perpendicular to
   the line from the axis. Measure the perpendicular distance from the axis to
   the string with calipers. Call it `r_cal` in metres.
4. Pull in the **same direction the rotor will**, so no sign flip is needed.
5. `t` to tare with the string slack, then hang the mass.
6. Applied torque = mass in kg x 9.80665 x `r_cal`. Send `c <that number>`.
7. `d` and confirm `sign : 1`. Lift the mass off and back on a few times and
   watch for hysteresis; more than a percent means stiction or a sloppy rod
   end.

A 1.41 kg mass at 150 mm gives 2.07 N·m, nicely inside the range.

Because the calibration maps counts straight to newton metres, an error in the
**cell's** arm radius cancels out completely. The only radius that matters is
`r_cal`, and you measured that with calipers.

`c` forces the calibration direction positive, exactly as on the thrust stand.
If you pull the wrong way, follow with `f`.

## Running two stands

Two boards, two USB ports, two programs. The consequence: **you cannot record
thrust and torque at the same instant for the same operating point.** One
board keeps its own samples simultaneous by construction; two boards do not.

Do not try to solve this by repeating the whole height sweep twice. The torque
rig's job is to measure drivetrain efficiency, not to redo the campaign. Run a
small matrix on the torque stand at one convenient height, spanning 1000 to
2000 rpm and the collective range, derive shaft watts against electrical
watts, and apply that efficiency to the thrust stand data. One height is enough because the
efficiency of the ESC and motor is a function of RPM and load, not of how far
the rotor is off the floor.

`tools/live.py` will run against the torque board today with no code change:

```
python3 live.py --port /dev/cu.usbserial-XXXX --http-port 8766 --logdir logs-torque
```

The strip chart, statistics and CSV logging all work, because the line format
has the same shape. The column is **labelled lbf and is actually N·m**, and
the BEMT power overlay is meaningless on that instance. Read past it, or ask
for a proper torque mode.

## Shaft watts

```
P_shaft = torque_Nm * rpm * 2 * pi / 60
```

The point of the exercise. At 1800 rpm the BEMT predicts the rotor needs
216 W of shaft power to hold 7.5 lbf, which is 1.15 N·m. Austin measures
446 W electrical. Either the rotor is far worse than modelled and is really
taking 352 W of shaft power (1.87 N·m, figure of merit 0.43), or the rotor is
close to the model and the drivetrain is running at 48% rather than 79%.
Electrical watts alone cannot tell those apart. Torque can, and that decides
whether the fix is in the blades or in the motor and ESC.

**Cruise is out of reach of this rig.** After transition the rotor works as a
propeller with axial inflow, and statically at 1000 rpm the BEMT tops out at
3.34 lbf and 88 W electrical at 21.9 degrees collective, which is 0.66 N·m.
Cruise wants 1.39 N·m at the same rpm. You run out of collective at about half
the torque. If the head will take pitch well past 21.9 degrees you can still
load the motor to 1.39 N·m in deep stall and get the drivetrain efficiency,
which is all that transfers anyway. The aerodynamics of that condition mean
nothing; the electrical measurement is still valid.

## Safety

Everything in doc 09 applies, plus: the cradle is deliberately free to rotate.
Before power-up, confirm the arm is actually bearing on the cell and cannot
swing. A cradle that comes loose while the rotor is turning puts the whole
nacelle into a spin against whatever the loom is attached to.
