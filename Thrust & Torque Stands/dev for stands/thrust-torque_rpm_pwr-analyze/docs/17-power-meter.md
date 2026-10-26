# 17 - Pack power in `live.py`: hall sensor + Nano

Replaces the LCD watt meter with something the dashboard can read. A Hall
current sensor in the positive pack lead, a resistor divider for pack volts,
and a third Nano printing CSV over USB. `live.py --power-port` shows watts,
volts and amps beside thrust, draws a 90 s strip, and capture fills `volts`
and `amps` from it so the run log stops depending on your eyes and the LCD.

## Why a Hall sensor and not a shunt

A shunt meter puts a small resistor in the negative lead and measures the
drop across it. On this bench the thrust Nano, the two FT232H tach boards and
the Mac all share a ground through the USB hub, and the ESCs share theirs
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
| Divider | 100 kΩ and 10 kΩ, 1% metal film, plus one 100 nF ceramic | parts bin | |
| Leads | 12 AWG silicone, two XT90 (one male, one female) to make a pigtail | parts bin | |
| Housing | a small printed box; the sensor board has two 2 mm mounting holes | Fusion | |

Why 50 A bidirectional rather than 30 A unidirectional: hover is about 20 A
but the top of the throttle range can pass 30 A, and the 50 A board is the
one with the heavy copper. The price in resolution is small (see below).

## Wiring

```
LiPo +  ----XT90F----[ IP+  ACS724  IP- ]----XT90M----  aircraft +
LiPo -  ----XT90F--------------------------XT90M----  aircraft -   (unbroken)

ACS724  VCC -> Nano 5V
        GND -> Nano GND
        OUT -> Nano A0

aircraft + (after the sensor) --- 100k ---+--- 10k --- Nano GND
                                          |
                                       Nano A1   (100 nF to GND here)
```

- Solder the 12 AWG leads directly to the IP+ / IP- pads; the pads are big
  for a reason. Pololu's ring-terminal option also works but adds resistance.
- Current direction: IP+ toward the pack. Backwards reads negative, which
  the firmware will happily report; the sign tells you.
- The divider is the only galvanic link between pack and Nano, 110 kΩ of it.
  Fine. Do not connect pack negative to Nano GND separately; it is already
  there through the aircraft side if the Nano shares the USB hub, and if it
  is not, 110 kΩ is all the reference it needs.
- Keep the sensor away from the motor and from the heavy pack leads; it
  reads magnetic field and a 20 A conductor an inch away will add a few
  hundred milliamps of offset. The 'z' command cancels a static offset, not
  one that changes with where the leads lie.

## Firmware

`firmware/power_meter/power_meter.ino`. Same IDE setup as docs 10 and 13
(IDE 1.8.19, Nano, plain ATmega328P). Stream row:

```
# n,ms,volts,amps,watts,rawI,rawV
1234,61700,24.112,18.354,442.6,660.8,448.2
```

20 rows per second, each from 32 oversampled ADC reads per channel. The
ADC and the sensor are both ratiometric to the Nano's 5 V, so a sagging USB
rail does not move the reading.

Resolution: 10-bit ADC, 40 mV/A, so 0.12 A per count, 0.02 A after
oversampling. Volts: 0.054 V per count. Both well inside the 1 to 2% you
need. Accuracy is set by calibration, below.

## Calibration, once

The ACS724's zero point is 2.5 V nominal and its gain 40 mV/A nominal; real
parts sit a percent or two off and the zero drifts a little with
temperature. Three commands, from the dashboard's power console or the
Arduino serial monitor:

1. **`z`** with the pack plugged in and the motor off, nothing drawing. Sets
   the zero. Do this at the start of every session.
2. **`kv 24.87`** where 24.87 is what a multimeter reads across the pack at
   that moment. Sets the divider scale. Once.
3. **`ka 18.4`** while the motor holds a steady load, 18.4 being what the
   LCD watt meter (still inline for this one step) or a clamp meter reads.
   Sets the gain. Once. A steady 15 to 25 A load is better than a small one.
4. **`w`** writes all three to EEPROM.

`d` dumps the current values and whether EEPROM had a calibration. The
panel shows NOT CALIBRATED until it does.

## Running

```
python3 live.py --port /dev/cu.usbserial-1480 --power-port /dev/cu.usbserial-1490
```

Three Nanos look alike in `--list`; the one that prints `# Nacelle Power
Meter` on open is the power meter. Label the cable. `live.py` sends `s`
itself on connect, so the meter streams as soon as the page has it, and
reconnects if the USB drops.

The power card: watts large, volts and amps and raw counts under it, 5 s
means, calibration state. Buttons: **Zero amps** (`z`), **Settings** (`d`),
**Write** (`w`). The console box takes any command, which is where `ka` and
`kv` go. The strip shows watts and amps (x10) on one axis.

Capture: volts and amps come from the meter's average over the same window
as thrust. Typing a value in either box overrides the meter for that row.
`watts` on the chart is the mean of instantaneous V x I from the meter,
which is the correct number under ESC ripple; for typed values it is
V_mean x I_mean, as before.

## Log files

`logs/power-YYYYmmdd-HHMMSS.csv`, one row per meter sample, 20 per second.
`logs/stream-*.csv` gains `volts, amps` at the end of each thrust row,
latest meter values under a second old, else blank. `run-log.csv` is
unchanged in schema; the `volts` and `amps` columns are now filled by the
meter instead of by hand.

## When it is wrong

- **Amps read negative** under load: sensor is backwards. Swap IP+ and IP-,
  or live with it and set gain with a negative `ka` (the firmware rejects
  that, so swap the wires).
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
