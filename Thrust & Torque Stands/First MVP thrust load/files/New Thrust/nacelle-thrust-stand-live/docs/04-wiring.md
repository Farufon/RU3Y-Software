# 04 - Wiring

> **Read this first if your board says VIN / VIO / GND / SCK / DAT / RATE.**
> That is the **Adafruit HX711 24-bit ADC (product 5974)**, and it is wired differently from
> the generic green module this document originally assumed. Jump to
> [Board A](#board-a---adafruit-hx711-24-bit-adc-product-5974). The single most important
> difference: **VIO is an output. Do not connect it to anything.**

There are two families of HX711 breakout in circulation and they do not share a pinout or a
pin-naming convention. Work out which one you have before you strip a single wire.

| If the silkscreen says... | You have | Wires to Arduino |
|---|---|---|
| VIN, VIO, GND, SCK, DAT, RATE - and RATE is a **slide switch** | **Board A**, Adafruit 5974 | 4 |
| VCC, VDD, DAT, CLK, GND - and a **YLW** pad near the terminals | **Board B**, SparkFun SEN-13879 | 5 (VCC and VDD both fed) |
| VCC, GND, DT, SCK - small green PCB, no VDD | **Board B**, generic green module | 4 |

The chip inside is the same in all three. The sketch does not care which you use. Only the
wiring differs.

Diagrams: `wiring-adafruit-hx711.svg` (Board A) and `wiring-generic-hx711.svg` (Board B).
Print the one that matches your board and keep it at the bench.

---

## Load cell to HX711

This part is the same on every board.

| Cell wire | HX711 pad | Function |
|---|---|---|
| Red | E+ | Bridge excitation, positive |
| Black | E- | Bridge excitation, negative |
| Green | A+ | Signal, positive |
| White | A- | Signal, negative |
| Shield / bare | **YLW** pad if present, otherwise GND | Ground at the HX711 end **only** |

Use **channel A**. The Adafruit board breaks out a second channel as B+ and B-; leave it
empty. Channel B has a fixed gain of 32 against channel A's 128, so a cell on B reads at a
quarter of the resolution. The sketch reads A only.

Colour convention is near-universal but not guaranteed. If your cell's datasheet disagrees,
follow the datasheet. Some cells substitute blue for green, or yellow for black.

If your cell has five wires, the fifth is the shield and is not part of the bridge. If it has
four, there is no shield, and you should consider running the cable inside a grounded braid,
because you are working next to motor phase leads carrying tens of amps of switched PWM.

**If the reading comes out negative when you expected positive, do not remount anything.**
Send `f` to the sketch to flip the sign in software. Do **not** swap green and white on
this rig: `f` is already load-bearing in the calibration procedure (see doc 05), and using
both fixes cancels them out. A reversed
reading means nothing except reversed wiring.

> Because this stand passes through **zero net load** partway up the thrust sweep, with the
> nacelle dead weight in compression below and thrust in tension above, sign handling is not
> cosmetic here. See doc 05 for the bidirectional calibration and the through-zero continuity
> check.

---

## Board A - Adafruit HX711 24-bit ADC (product 5974)

**Four wires. Not five.**

| Adafruit pin | Arduino pin | Wire |
|---|---|---|
| VIN | 5V | red |
| GND | GND | black |
| DAT | D2 | green |
| SCK | D3 | violet |
| **VIO** | **- nothing -** | leave unconnected |
| **RATE** | **- nothing -** | it is a switch, see below |

### VIO is an output, not an input

This is the one that bites, because the name looks like a supply input and on a different
board it would be.

On the Adafruit board, **VIO is the on-chip regulator's digital-supply output**, brought to a
pad so you can measure it or borrow it for something else. It is not asking to be fed.
Jumpering it to VIN ties the regulator's output to your 5 V rail and puts them in opposition.

The confusion is understandable: SparkFun's board has a **VDD** pin that genuinely is a logic
level input you must feed, and plenty of hookup guides say "short VCC and VDD together."
That advice is correct for that board and wrong for this one.

**Leave VIO unconnected and the board just works.**

### VIN sets the logic level

Feed VIN the same voltage as your microcontroller's logic. The Nano is a 5 V part, so VIN
goes to the Nano's 5V pin. On a 3.3 V board you would give VIN 3.3 V instead. There is no
separate level pin to worry about, which is precisely why VIO is not one.

### RATE is a slide switch

There is no RATE wire to run. On the right-hand edge of the board is a slide switch marked
Rate, with positions L and H.

- **L gives 10 samples per second.** This is what the supplied sketch expects. **Set it to L.**
- H gives 80 SPS.

If you later want 80 SPS for more averaging, that is a reasonable change, but move the switch
and adjust the sketch's timing together, not one without the other.

### Terminal blocks

The Adafruit board ships with the screw terminals pre-soldered, which is genuinely convenient
for a stand that will be assembled and disassembled repeatedly as post sections change. Six
positions: E+, E-, A+, A-, B+, B-. Strip about 6 mm, insert, tighten, and **tug each wire**.
A screw terminal that looks seated and is not is a fault that appears only under vibration,
which is to say only when the rotor is turning.

---

## Board B - SparkFun SEN-13879 and generic green modules

| HX711 pin | Arduino pin |
|---|---|
| VCC | 5V |
| **VDD** | **5V** (SparkFun only - jumper to VCC) |
| GND | GND |
| DAT / DT / DOUT | D2 |
| CLK / SCK | D3 |

**DAT, DT and DOUT are three silkscreen names for one pin.** SparkFun prints DAT, generic
green boards print DT or DOUT, and the sketch calls it `PIN_DOUT`. All the same signal.

**VCC versus VDD on the SparkFun board.** VCC is the analogue supply that excites the cell;
VDD sets the digital logic level. For a 5 V Nano, jumper them together and feed both from 5V.
They are separate only so a 3.3 V microcontroller can run VCC at 5 V for bridge headroom
while keeping VDD at 3.3 V for safe logic. Not your case.

Generic green modules have a single VCC and no VDD pad at all. Nothing to jumper.

**RATE on Board B** is pin 15 of the bare chip. Green modules usually tie it low at 10 SPS
from the factory, which is what you want. Changing it means lifting a pin, and it is not
worth the surgery.

---

## Pin assignment conflict - read before you follow any other guide

SparkFun's hookup guide and their example sketches use `DAT = 3, CLK = 2`.
**This package uses `DAT = D2, SCK = D3`.** They are transposed.

Neither is more correct; the HX711 works on any two GPIO pins. But if you wire to one
convention and run the other's software, **you get nothing and no error message.** It looks
exactly like a dead board, and people replace perfectly good hardware over it.

Pick one and stay with it. To follow SparkFun's convention instead, swap two lines at the top
of `thrust_stand.ino`:

```cpp
const uint8_t PIN_DOUT = 3;   // was 2
const uint8_t PIN_SCK  = 2;   // was 3
```

Nothing else in the sketch is affected.

**Do not use D0 or D1** on any board. Those are the hardware serial pins the USB connection
uses, and anything on them fights the serial link.

---

## Elegoo Nano V3.0 specifics

The headers ship loose, so you can solder only the four pads this project needs. They are
placed conveniently:

```
   ANALOG SIDE                        DIGITAL SIDE
   ...                                ...
   A6                                 D4
   A7                                 D3   <-- SCK
 > 5V   <-- HX711 VIN (or VCC)        D2   <-- DAT
   RST                                GND  <-- HX711 GND
   GND                                RST
   VIN                                RX0   (do not use)
                                      TX1   (do not use)
```

**D3, D2 and GND are three consecutive pads** on the digital side. Only 5V is on the opposite
edge. Four solder joints total.

Note the collision of names: the **Nano** also has a pin called VIN, and it is the raw
unregulated input, typically 7 to 12 V. **Never connect the HX711's VIN to the Nano's VIN.**
HX711 VIN goes to the Nano's **5V** pad. On a stand sitting next to a 6S pack this is not a
theoretical hazard.

---

## Supply quality

The HX711 is a **ratiometric** converter. It excites the bridge from the same rail it uses as
the ADC reference, so a rail sitting at 4.7 V instead of 5.0 V does not shift your reading.
The two effects cancel.

What it will not tolerate is a rail sagging far enough that the internal analogue regulator
runs out of headroom. Practically: plug into a real USB port on the laptop, not an unpowered
hub, and use a short thick cable. A thin two-metre USB cable is a common and very annoying
cause of slow unexplained drift.

---

## Power and grounding, and this matters

**Power the Arduino from the laptop USB. Do not power it from the flight pack.**

You are reading a millivolt-level bridge inches from motor phase wires carrying tens of amps
of switched PWM. Every rule below exists to keep that noise out.

- Ground the cell's shield at the **HX711 end only.** Grounding both ends makes a loop antenna.
- Run the cell cable down the **opposite side of the post** from the motor phase leads.
- If they must cross, cross at 90 degrees.
- Keep the HX711 close to the cell and put the long run on the **digital** side. Signal from
  the cell is millivolts; signal from the HX711 is logic level and far more robust.
- Leave a **service loop** in the cell cable, taped to the post, so cable tension never enters
  the load path. A taut cable is a spring in parallel with your load cell.

**Diagnostic:** if readings are clean with the motor off and turn to hash under power, it is
one of the above. Almost always the shield or the cable routing.

---

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `HX711 ready: no` | DAT and SCK swapped, or on the wrong pins for the sketch. Check the transposition warning above. |
| Board warm, no data | VIO jumpered to VIN on an Adafruit board. Remove that wire. |
| Reads but sign inverted | Expected after calibrating. Send `f`. Do not swap the wires. |
| Readings drift slowly, no load | Thin or long USB cable; unpowered hub; or cable tension in the load path. |
| Clean cold, hash under power | Shield grounded at both ends, or cell cable routed alongside phase leads. |
| Value frozen, never changes | SCK stuck high - HX711 enters power-down after 60 µs of SCK high. Check the D3 joint. |
| Steps or jumps mid-sweep | Not electrical. Threaded-joint clearance at the load reversal. See doc 03 preload and doc 05. |

---

## Sample rate

10 SPS suits this test: plateaus are five seconds long, so you get roughly fifty samples per
point. 80 SPS gives the software more to average vibration out of, which is mildly preferable
on a thrust stand, but it is not worth changing the sketch timing for. On Board A it is one
switch; on Board B it is surgery. Either works.

---

## Diagram files

- `wiring-adafruit-hx711.svg` - Board A, Adafruit 5974
- `wiring-generic-hx711.svg` - Board B, SparkFun and generic green

Both show the full chain: load cell, HX711, Arduino, and the shield path. Print the one that
matches your board.

---

## Optional additions

- **SD card module** for standalone logging without a laptop. SPI, pins 10 to 13 on an Uno.
- **OLED display** if you want a number at the bench. I2C, A4 and A5 on an Uno.

Neither is in the supplied sketch. Serial to a laptop is simpler and gives you the log file
you actually need.

---

## The power side

Thrust and electrical power are measured by **separate instruments** and that is fine.

Put an inline watt meter or a shunt between the pack and the ESC. Do not use ESC-reported
current for the deliverable; it is commonly 5 to 10 percent off.

Size the meter for **50 A per nacelle**, not for the hover figure. Hover is around 12 to 13 A
at 21 V, but peak thrust draw is roughly double that, and a meter clipping at peak loses you
exactly the data point that matters for control authority.

You do **not** need synchronised instruments. Because the test is a staircase with five second
plateaus, you read the settled value off each device independently and write the row. The
plateau does the synchronising for you. This saves an enormous amount of grief and costs
nothing in data quality.
