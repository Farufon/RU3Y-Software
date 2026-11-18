# 17 - Pack power in `live.py`: hall sensor + Nano

Replaces the LCD watt meter with something the dashboard can read. A Hall
current sensor in the positive pack lead, a resistor divider for pack volts,
and a third Nano printing CSV over USB. `live.py --power-port` shows watts,
volts and amps beside thrust, draws a 90 s strip, and capture fills `volts`
and `amps` from it so the run log stops depending on your eyes and the LCD.

One stand, one pack, one sensor. The two-nacelle package carries a
two-channel version of this sketch; this one is single-channel, on A0/A1.

## Why a Hall sensor and not a shunt

A shunt meter puts a small resistor in the negative lead and measures the
drop across it. On this bench the thrust Nano, the FT232H tach board and
the Mac all share a ground through the USB hub, and the ESC shares its
with the pack. Break the negative lead with a shunt and the USB cables become
a second path around it: a few hundred milliamps through the hub at full
load, noise on every channel. The Hall sensor passes the positive lead
through a magnetic core, the negative lead stays unbroken, and the sensor's
output side is galvanically isolated from the current path. Problem gone.

## Parts

| | part | where | approx |
|---|---|---|---|
| Current | Pololu ACS724 Current Sensor Carrier, -50 A to +50 A, item **4049** (Allegro ACS724LLCTR-50AB, 40 mV/A, 4 oz copper) | pololu.com | $11.49 |
| Board | Elegoo Nano V3, same as the thrust and torque boards | you have spares | |
| Divider | 100 kΩ and 10 kΩ, 1% metal film, plus a 100 nF ceramic | parts bin | |
| Leads | 12 AWG silicone, two XT90 (one male, one female) to make a pigtail | parts bin | |
| Housing | a small printed box; the sensor board has two 2 mm mounting holes | Fusion | |

Why 50 A bidirectional rather than 30 A unidirectional: hover is about 20 A
but the top of the throttle range can pass 30 A, and the 50 A board is the
one with the heavy copper. The price in resolution is small (see below).

## Wiring

```
pack +  ----XT90F----[ IP+  ACS724  IP- ]----XT90M----  nacelle +
pack -  ----XT90F---------------------------XT90M----  nacelle -   (unbroken)

ACS724  VCC -> Nano 5V,  GND -> Nano GND,  OUT -> Nano A0

nacelle + (after sensor) --- 100k ---+--- 10k --- Nano GND
                                     |
                                  Nano A1   (100 nF to GND here)
```

- Solder the 12 AWG leads directly to the IP+ / IP- pads. Pololu's ring
  terminal option also works but adds resistance.
- Current direction: IP+ toward the pack. Backwards reads negative; the
  sign tells you.
- The divider returns to Nano GND, so the pack negative is referenced to USB
  ground through 10 kΩ. It already shares a reference through the Castle RPM
  lead and the USB hub, so this adds nothing new. Use thin wire (22 to 24
  AWG) for the divider legs so they can never carry motor current if
  something else lets go.
- Keep the sensor away from the motor and from the pack leads; it reads
  magnetic field and a 20 A conductor an inch away adds a few hundred
  milliamps of offset. `z` cancels a static offset, not one that changes
  with where the leads lie.

## Firmware

`firmware/power_meter/power_meter.ino`. Same IDE setup as docs 10 and 13
(IDE 1.8.19, Nano, plain ATmega328P). Stream row:

```
# n,ms,volts,amps,watts,rawI,rawV
1234,61700,24.112,18.354,442.6,660.8,448.2
```

Volts, amps, watts, then the raw ADC counts. 20 rows per second, each from
16 oversampled ADC reads per input. The ADC and the ACS724 are both
ratiometric to the Nano's 5 V, so a sagging USB rail does not move the
**amps**. The divider is not ratiometric: the tap voltage is absolute, so
its count scales with 1/VCC and a rail 2% low would read pack volts, and
watts, 2% high. The firmware therefore measures VCC against the ATmega's
internal 1.1 V bandgap on every row and uses that instead of assuming
5.000 V. `d` shows the measured rail as `vcc (bandgap)`. Expect 4.7 to
5.1 V depending on hub load; what matters is that it no longer leaks into
the volts.

Resolution: 10-bit ADC, 40 mV/A, so 0.12 A per count, finer after
oversampling. Volts: 0.054 V per count. Both well inside the 1 to 2% you
need. Accuracy is set by calibration, below.

**A Nano still carrying the two-channel sketch** (from the two-nacelle
package) prints twelve-field rows. `live.py` accepts them and uses the first
channel, A0/A1, and the power card says so. Flash this package's sketch when
convenient; it picks up the first channel's calibration from EEPROM and
tells you on the banner. Then press **Write** once to store it in the new
layout.

## Calibration, once

The ACS724's zero point is 2.5 V nominal and its gain 40 mV/A nominal; real
parts sit a percent or two off and the zero drifts a little with
temperature. From the dashboard's power console or the Arduino serial
monitor:

1. **`z`** with the pack plugged in and the motor off, nothing drawing. Do
   this at the start of every session (the **Zero amps** button).
2. **`kv 24.87`** where 24.87 is what a multimeter reads across the pack at
   that moment. Sets the divider ratio (nominal 11.0 for 100k/10k; stored as
   `vScale`). Once. The rail at that moment is folded in, so the bandgap's
   own part-to-part spread cancels here and only rail changes afterwards are
   tracked.
3. **`ka 18.4`** while the motor holds a steady load, 18.4 being what the
   LCD watt meter (still inline for this step) or a clamp meter reads. Sets
   the gain. Once. A steady 15 to 25 A load is better than a small one.
4. **`w`** writes all three values to EEPROM.

`d` dumps the values and whether EEPROM had a calibration. The panel shows
NOT CALIBRATED until it does. With no pack connected rawV reads near zero
and the card says "no pack on the meter".

## Running

```
bash tools/start.sh
```

or by hand:

```
python3 live.py --port /dev/cu.usbserial-1480 --power-port /dev/cu.usbserial-1490
```

Three Nanos look alike in `--list`; the one that prints `# Nacelle Power
Meter` on open is the power meter. `start.sh` tells them apart by that
banner. `live.py` sends `s` itself on connect, so the meter streams as soon
as the page has it, and reconnects if the USB drops.

The power card: watts large, volts and amps and raw counts under it, 5 s
means, the calibration values and the measured rail. The strip shows watts
solid and amps (x10) dashed. Below: **Zero amps** (`z`), **Settings** (`d`),
**Write** (`w`), and the console box, which is where `ka` and `kv` go.

Capture: `volts` and `amps` in the run log are the meter's averages over the
same window as thrust. Typing a value in either box overrides the meter for
that row. `watts` in the run log and on the chart is the mean of
instantaneous V x I from the meter, which is the correct number under ESC
ripple; `reduce.py` prefers that column and falls back to volts x amps only
for typed rows.

## Log files

`logs/power-YYYYmmdd-HHMMSS.csv`, one row per meter sample, 20 per second:
`iso_time, epoch_s, board_ms, volts, amps, watts, rawI, rawV`.
`logs/stream-*.csv` carries `volts, amps` at the end of each thrust row,
latest meter values under a second old, else blank. `run-log.csv` carries
`volts, amps, watts`.

## When it is wrong

- **Amps read negative** under load: sensor is backwards. Swap IP+ and IP-.
- **Zero wanders by more than 0.3 A between sessions:** the sensor is near a
  current-carrying lead or a magnet. Move it. Re-`z`.
- **Volts right, amps off by a constant factor:** `ka` was done against a
  bad reference. The LCD meter's current reading is the weakest number it
  gives; a clamp meter on the pack lead is better.
- **Amps noisy, 1 A sd at steady load:** the ESC's input ripple is real and
  the sensor has 120 kHz bandwidth, so it sees it. Oversampling already
  averages 3.5 ms of it; the 5 s capture average is the number that matters.
  If it bothers the strip, add 1 µF from A0 to GND.
- **`disconnected` with the board plugged in:** another program has the
  port, or the Nano reset mid-stream. Check `--list`, run `tools/stop.sh`.
