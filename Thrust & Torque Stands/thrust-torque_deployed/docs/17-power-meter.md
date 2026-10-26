# 17 - Pack power in `live.py`: hall sensors + Nano, two channels

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
| Current | **two** Pololu ACS724 Current Sensor Carriers, -50 A to +50 A, item **4049** (Allegro ACS724LLCTR-50AB, 40 mV/A, 4 oz copper), one per nacelle | pololu.com | $11.49 each |
| Board | Elegoo Nano V3, same as the thrust and torque boards | you have spares | |
| Divider | two of: 100 kΩ and 10 kΩ, 1% metal film, plus a 100 nF ceramic | parts bin | |
| Leads | 12 AWG silicone, four XT90 (two male, two female) to make two pigtails | parts bin | |
| Housing | a small printed box; the sensor board has two 2 mm mounting holes | Fusion | |

Why 50 A bidirectional rather than 30 A unidirectional: hover is about 20 A
but the top of the throttle range can pass 30 A, and the 50 A board is the
one with the heavy copper. The price in resolution is small (see below).

## Wiring

Each nacelle has its own pack, so each gets its own sensor and its own
divider. Both go to one Nano. One board means one USB cable, one zero per
session, and port and stbd sampled on the same clock in the same CSV row.

```
PORT pack +  ----XT90F----[ IP+  ACS724 #1  IP- ]----XT90M----  port nacelle +
PORT pack -  ----XT90F------------------------------XT90M----  port nacelle -   (unbroken)

STBD pack +  ----XT90F----[ IP+  ACS724 #2  IP- ]----XT90M----  stbd nacelle +
STBD pack -  ----XT90F------------------------------XT90M----  stbd nacelle -   (unbroken)

ACS724 #1  VCC -> Nano 5V,  GND -> Nano GND,  OUT -> Nano A0     (port)
ACS724 #2  VCC -> Nano 5V,  GND -> Nano GND,  OUT -> Nano A2     (stbd)

port nacelle + (after sensor) --- 100k ---+--- 10k --- Nano GND
                                          |
                                       Nano A1   (100 nF to GND here)

stbd nacelle + (after sensor) --- 100k ---+--- 10k --- Nano GND
                                          |
                                       Nano A3   (100 nF to GND here)
```

- Solder the 12 AWG leads directly to the IP+ / IP- pads. Pololu's ring
  terminal option also works but adds resistance.
- Current direction: IP+ toward the pack on both. Backwards reads negative;
  the sign tells you.
- The two dividers both return to Nano GND, so the two pack negatives are
  tied together through 10 kΩ each. They already share a reference through
  the Castle RPM leads and the USB hub, so this adds nothing new. Use thin
  wire (22 to 24 AWG) for the divider legs so they can never carry motor
  current if something else lets go. Do NOT run a separate heavy ground
  between the packs.
- Keep both sensors away from the motors and from each other's pack leads;
  they read magnetic field and a 20 A conductor an inch away adds a few
  hundred milliamps of offset. `z` cancels a static offset, not one that
  changes with where the leads lie. Mount the two sensors a few inches
  apart.
- Label the pigtails PORT and STBD at both ends. The firmware has no way to
  know which is which.

## Firmware

`firmware/power_meter/power_meter.ino`. Same IDE setup as docs 10 and 13
(IDE 1.8.19, Nano, plain ATmega328P). Stream row:

```
# n,ms,vP,aP,wP,vS,aS,wS,rawIP,rawVP,rawIS,rawVS
1234,61700,24.112,18.354,442.6,23.980,17.611,422.3,660.8,448.2,655.1,445.7
```

Port volts/amps/watts, then stbd, then the raw ADC counts for both. 20 rows
per second, each from 16 oversampled ADC reads per channel (four channels). The
ADC and the sensor are both ratiometric to the Nano's 5 V, so a sagging USB
rail does not move the reading.

Resolution: 10-bit ADC, 40 mV/A, so 0.12 A per count, 0.02 A after
oversampling. Volts: 0.054 V per count. Both well inside the 1 to 2% you
need. Accuracy is set by calibration, below.

## Calibration, once

The ACS724's zero point is 2.5 V nominal and its gain 40 mV/A nominal; real
parts sit a percent or two off and the zero drifts a little with
temperature. Each channel is calibrated separately, from the dashboard's
power console or the Arduino serial monitor:

1. **`z`** with both packs plugged in and both motors off, nothing drawing.
   Zeroes both channels at once. Do this at the start of every session.
2. **`kv p 24.87`** where 24.87 is what a multimeter reads across the port
   pack at that moment; then **`kv s 24.91`** for stbd. Sets each divider
   scale. Once.
3. **`ka p 18.4`** while the port motor holds a steady load, 18.4 being what
   the LCD watt meter (still inline for this step) or a clamp meter reads;
   then **`ka s 18.1`** for stbd. Sets each gain. Once. A steady 15 to 25 A
   load is better than a small one.
4. **`w`** writes all six values to EEPROM.

`d` dumps the values for both channels and whether EEPROM had a
calibration. The panel shows NOT CALIBRATED until it does. A channel with
no pack connected reads rawV near zero and the card shows "no pack on this
channel"; that is normal when only one nacelle is on the stand.

## Running

```
python3 live.py --port /dev/cu.usbserial-1480 --power-port /dev/cu.usbserial-1490
```

Three Nanos look alike in `--list`; the one that prints `# Nacelle Power
Meter` on open is the power meter. Label the cable. `live.py` sends `s`
itself on connect, so the meter streams as soon as the page has it, and
reconnects if the USB drops.

Two power cards, port and stbd: watts large, volts and amps and raw counts
under it, 5 s means, that channel's calibration values. The strip shows
both channels, watts solid and amps (x10) dashed, port red and stbd green
to match the RPM cards. Below: **Zero amps** (`z`), **Settings** (`d`),
**Write** (`w`), and the console box, which is where `ka p`, `ka s`,
`kv p`, `kv s` go.

Capture: `volts` and `amps` in the run log are the port channel's averages
over the same window as thrust; typing a value in either box overrides the
meter for that row. `volts_stbd` and `amps_stbd` are the stbd channel's
averages, filled only when a pack is on that channel. `watts` on the chart
is the mean of instantaneous V x I from the meter, which is the correct
number under ESC ripple; the captured-points table shows port / stbd watts
when both are live.

## Log files

`logs/power-YYYYmmdd-HHMMSS.csv`, one row per meter sample, 20 per second:
`iso_time, epoch_s, board_ms, volts_port, amps_port, watts_port, volts_stbd,
amps_stbd, watts_stbd, rawI_port, rawV_port, rawI_stbd, rawV_stbd`.
`logs/stream-*.csv` gains `volts, amps` (port) at the end of each thrust
row, latest meter values under a second old, else blank. `run-log.csv`
gains `volts_stbd, amps_stbd` at the end; older run logs are widened in
place on first use, as with the rpm columns.

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
