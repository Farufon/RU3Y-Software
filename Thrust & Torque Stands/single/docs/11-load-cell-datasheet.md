# 11 - Load Cell Reference: ATO-LCS-DYLY-102, 20 kg

Confirmed from ATO's manufacturer page. Use for CAD, not the Amazon listing.

- **Model:** ATO-LCS-DYLY-102
- **SKU:** ATO-LC-S02
- **Amazon ASIN:** B07VM5VK8T
- **Direct price:** $82.59 from ato.com (Amazon is usually less)

## Dimensions, 20 kg

The 20 kg falls inside ATO's **2 to 30 kg** body size, which is shared across that whole
capacity band. So a 10 kg or 30 kg cell has the identical envelope if you change your mind.

| Dim | Value |
|---|---|
| W (width) | 60 mm |
| H (height) | 58 mm |
| B (thickness) | 12 mm |
| M1 (thread, both ends) | **M8 x 1.25** |
| Cable length | 2 m |

M8 x 1.25 is standard coarse pitch, so studs and jam nuts are off-the-shelf.

**Not published, measure on arrival:** thread depth, cable exit position, and the exact
corner radii. Model the 60 x 58 x 12 envelope and the M8 holes on the vertical centreline,
leave your adapter plates undrilled until the cell is in your hand.

Full capacity range and body sizes, if useful:

| Capacity | W | H | B | Thread |
|---|---|---|---|---|
| 0-1 kg | 60 | 58 | 12 | M6 x 1.25 |
| **2-30 kg** | **60** | **58** | **12** | **M8 x 1.25** |
| 50-200 kg | 70 | 64 | 20 | M12 x 1.75 |
| 300-500 kg | 70 | 64 | 20 | M12 x 1.75 |

## Electrical

| Spec | Value |
|---|---|
| Accuracy | **0.03% F.S.** (linearity + hysteresis + repeatability) |
| Sensitivity | 2.0 +/- 0.05 mV/V |
| Creep | +/- 0.03% F.S. / 30 min |
| Zero output | +/- 1% F.S. |
| Temp effect on zero | +/- 0.03% F.S. / 10 C |
| Temp effect on output | +/- 0.03% F.S. / 10 C |
| Operating temp | -20 to +65 C |
| Input impedance | 350 +/- 20 ohm |
| Output impedance | 350 +/- 5 ohm |
| Safety overload | 150% F.S. |
| Bridge voltage | DC 5-15 V, ATO suggest 10 V |
| Material | 42CrMo alloy steel |
| Protection | IP67 |

**Wiring:** EXC+ red, EXC- black, SIG+ green, SIG- white. Fifth uncoloured wire is the
shield. ATO say it may be left unconnected, or tied in with E-. Given you are working
beside motor phase leads, connect it: to the YLW pad if your HX711 board has one, otherwise
to GND at the HX711 end only.

If the reading comes out negative, ATO's own guidance is to swap the green and white signal
wires. Same as the `f` command in the sketch.

## Two things ATO tell you that need context

**"You can't connect it to an Arduino directly, you need a transmitter."** This appears in
ATO's own product Q&A. It is true and also an upsell for their $81 transmitter. The HX711
**is** the transmitter. A $2 HX711 module does the same job for this application. Ignore it.

**Excitation.** ATO specify DC 5-15 V and suggest 10 V. The HX711 delivers about 4.3 V from
its internal analogue regulator, marginally under their stated minimum. This is standard
practice and works. You get roughly half the millivolts the datasheet implies, but the
24-bit converter has resolution to spare, and because the HX711 is ratiometric the accuracy
does not suffer. It just means your raw counts look smaller than ATO's numbers suggest.

Impedance is a non-issue: 350 ohm is exactly what the HX711 is designed to drive.

## CORRECTION: off-axis load is not harmless

Earlier in this project I said that if the nacelle CG sits off the post axis, the resulting
constant bending moment gets absorbed by the tare and you need not counterweight anything.

**The first half is true, the second half was wrong.** The tare does remove the constant
offset from the *reading*. But ATO's own application guidance is explicit:

> The sensor must be installed horizontally or vertically without transverse load.
> Do not let the load be applied offset from the centre axis, otherwise the sensor is
> easy to damage.

Their stated transverse load limit is 100% F.S. So off-axis loading is a **mechanical
survival** issue, not just a measurement one. An S-beam is designed to be loaded along its
axis and is comparatively fragile in bending.

Revised guidance for the build:

1. Get the nacelle CG on the post centreline. Balance the assembly on the post with the
   motor off and shim until it sits without wanting to fall one way.
2. If you cannot get it close, add a counterweight to the fixture. It costs you nothing in
   measurement, because the tare removes it either way, and it protects the cell.
3. Never let the fixture apply a side load, a twist, or a pry. No levering the nacelle into
   position with the cell in the stack.

Doc 03 has been updated accordingly.

## Accuracy, revised upward

An earlier note in this package quoted 0.3% F.S., which came from ATO's DYMH-103 micro cell,
a different part. The DYLY-102 is **0.03% F.S.**, ten times better.

That is 6 g, or about 0.013 lb, on a 20 kg cell. At your 7.5 lbf hover point it is under
0.2 percent. The cell is not going to be your limiting error source. Your mounting, your
calibration weights, and your watt meter will be.
