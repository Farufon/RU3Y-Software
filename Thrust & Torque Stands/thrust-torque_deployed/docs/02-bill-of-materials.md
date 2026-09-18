# 02 - Bill of Materials

Prices are indicative, US, as of writing. Verify before ordering.

## Sensing chain

| # | Item | Spec / notes | Approx |
|---|---|---|---|
| 1 | S-beam load cell, 20 kg | **ATO-LCS-DYLY-102.** 60 x 58 x 12 mm, **M8 x 1.25** both ends, 2.0 mV/V, 0.03% F.S., IP67, 2 m cable. See doc 11. | $30-83 |
| 2 | HX711 amplifier breakout | 24-bit. Generic green module ($1-3) or SparkFun SEN-13879 ($4.95). Either works; see doc 04. | $2-6 |
| 3 | Arduino Uno or Nano | Any 5 V AVR board. Elegoo Nano V3.0 (ATmega328P/CH340) confirmed suitable; see doc 10. | $12-28 |
| 4 | USB cable | **Mini-B for the Elegoo Nano**, and it must be a DATA cable. Powers and logs. Never power the board from the flight pack. | $5 |
| 5 | Shielded 4-conductor cable | Only if extending the cell's own cable. Keep the original if you can. | $10 |
| 5b | Header pins / solder | Elegoo Nano headers ship LOOSE. Four joints minimum: D3, D2, GND, 5V. | $2 |

### Load cell sources

- **ATO 20 kg S-Type**, Amazon: https://www.amazon.com/ATO-Length-Accuracy-Tension-Compression/dp/B07VM5VK8T
  2.0 mV/V, 5-15 V excitation, IP67, alloy steel, 2 m cable, tension and compression both.
  This is the straightforward pick.
- **ATO manufacturer page**, 5 kg to 500 kg: https://www.ato.com/tension-load-cell-s-type-5kg-to-500kg
- **ATO load cell catalog PDF** (dimensions and thread sizes by capacity, get this before
  you cut plates): https://www.ato.com/Content/doc/Load-cell-catalog.pdf
- **PT Global PT4000, 20 kg**: https://www.ptglobal.com/products/48-tension-load-cell-20kg-capacity-for-platform-scales-40M0020T000XXX
  3.0 mV/V in alloy tool steel, IP67, full range of mounting accessories. Step up in quality;
  the extra 1 mV/V is free signal.
- **Budget bundle, cell plus HX711**: https://www.amazon.com/FPBIGCHA-Sensor-Tension-Compression-Optional/dp/B0DMKCB4RF

### Amplifier reference

- **SparkFun HX711 hookup guide** (wiring, calibration, code, covers S-type specifically):
  https://learn.sparkfun.com/tutorials/load-cell-amplifier-hx711-breakout-hookup-guide/all

### Why 20 kg and not 10 kg

Peak measured load is not 7.5 lbf. It is whatever full throttle gives, call it 14 lbf or
6.4 kg. A 10 kg cell puts you at 64 percent of range, which is better for resolution. A
20 kg cell puts you at 32 percent, which costs a little resolution but buys vibration
margin and, more usefully, a larger body with a fatter thread. Your joint carries a small
bending moment and M8 is meaningfully stiffer than M5. Take the 20 kg.

Accuracy of **0.03 percent** full scale on a 20 kg cell is about 0.013 lb, or roughly
0.2 percent at your hover point. That is comfortably better than you need, and it is the
figure quoted for the ATO DYLY-102 in the table above and in doc 11. Note this is the cell
alone; a built system lands nearer plus or minus a few percent once mounting, temperature
and vibration are in play. See doc 05.

## Mechanical

| # | Item | Spec / notes |
|---|---|---|
| 6 | Adapter plates, 2 off | 6 mm (1/4 in) steel or aluminium, ~100 x 100 mm. Flat and clean; you need friction across the joints. |
| 7 | Studs, 2 off | **M8 x 1.25**, ~40 mm. Threaded rod or hex bolts. |
| 8 | Jam nuts, 4 off | M8. Two per stud. |
| 9 | Thread locker | Medium strength. |
| 10 | Dowel pin, 1 off | Optional anti-rotation, 5-6 mm, through both plates offset from centre. |
| 11 | Post tube | Round steel, 25-38 mm OD, wall 2-3 mm. Round for torsional stiffness and no preferred bending plane. |
| 12 | Post sections | Cut to the height ladder. See doc 06. Discrete sections beat a pinned telescope: no slop. |
| 13 | Legs, 3 off | Steel angle or tube. Feet must land **outside 700 mm radius** from the axis. Rotor is 457 mm today and Austin has said it grows; cut long once. |
| 14 | Feet, anchors or ballast | Bolt to concrete, or 25 lb per foot. |
| 15 | Yoke stock | To clamp the nacelle trunnion. Size from your own trunnion. Pinch bolts. |

**Do not build a solid base plate under the disc.** It becomes a false ground plane and
ground effect is the thing being measured. Three splayed legs, nothing solid underneath.

## Instrumentation for the power side

| # | Item | Notes |
|---|---|---|
| 16 | Inline watt meter or shunt | Between pack and ESC. **Size for 50 A per nacelle**. Hover is 21 A at 21 V (446 W, flight-tested), not the 13 A earlier versions of this table assumed, and you will be exploring the thrust ceiling well past that. ESC-reported current is often 5-10 percent off; do not trust it for the deliverable. |
| 17 | Optical or ESC telemetry tachometer | **Required, not optional.** The governor can droop off its setpoint under load, and `head_rpm_actual` is a required log column. |
| 17a | Blade pitch gauge | Digital-readout heli pitch gauge, clamps at 0.75R (r = 343 mm). This is the inner test axis; without it you are logging servo counts. See doc 05a. |
| 17b | Servo tester | To command specific microsecond values during the pitch calibration. Your transmitter will do if it can show the raw value. |
| 18 | Calibration weights | 2, 5 and 10 lb, or gym plates verified on a known-good scale. Non-negotiable. |
| 19 | Tape measure / height gauge | Rotor plane to floor, at each ladder step. |

## Consumables and safety

| # | Item |
|---|---|
| 20 | Hearing protection |
| 21 | Eye protection |
| 22 | Polycarbonate barrier or equivalent standoff, see doc 09 |
| 23 | Zip ties, tape for cable service loops |
| 24 | Torque wrench |

## Rough total

Sensing chain, $55 to $120. Mechanical, $80 to $200 depending on what is already in the
shop. Watt meter, $25 to $60. Call it $200 to $350 all in.

## Alternative worth knowing

Purpose-built RC thrust stands exist that log thrust, torque, RPM, voltage and current
together with their own software. They are around $1000 and up, and their fixtures are
designed for a bare motor, not a finished nacelle with a trunnion. For a one-off with a
custom nacelle interface, the rig in this package is cheaper and fits better. If you expect
to do this repeatedly for many nacelles, price one out.
