# Nacelle Thrust Stand

An axial-post thrust stand for measuring single-nacelle thrust, electrical power, and
ground-effect behaviour on a 914 mm-disc (R = 457 mm) VTOL tilt-rotor nacelle.

Built for a two-nacelle, 15 lb tilt-rotor VTOL. Hover thrust per nacelle is 7.5 lbf.
The deliverable this rig produces is a family of curves: **electrical watts required to
produce 7.5 lbf, as a function of rotor height above ground.**

---

## Start here

- Never used an Arduino? -> `docs/10-arduino-first-time.md`
- Already have the parts and want one page? -> `docs/00-quickstart.md`
- Want to try the software before parts arrive? -> `python3 tools/bench.py --simulate`
- **Before the first spin** -> `docs/09-safety.md`

## Arduino and serial: the working configuration

Everything below is proven on the actual hardware. If the board will not flash or
will not talk, this is the section to read. Same text as
`docs/13-arduino-working-config.md`.

Elegoo Nano V3.0 (ATmega328P / CH340) on Intel Mac, macOS 15.7.5.

### The rule

**Use Arduino IDE 1.8.19. Do not use 2.3.10 for uploads.**

2.3.10 ships avrdude 8.0, which cannot write flash to this board.
1.8.19 ships avrdude 6.3, which writes it in 0.23 seconds.

### Settings

| Item | Value |
|---|---|
| IDE | Arduino 1.8.19 (the app named `Arduino`, not `Arduino IDE`) |
| Board | Tools > Board > Arduino AVR Boards > Arduino Nano |
| Processor | Tools > Processor > **ATmega328P** (NOT Old Bootloader) |
| Port | Tools > Port > `/dev/cu.usbserial-XXXX` |
| Verify after upload | Can stay on. Read-back verifies clean on the soldered board. |
| Serial Monitor baud | 115200 for `thrust_stand.ino`, line ending New Line |

Old Bootloader sets 57600 and fails to sync. Plain ATmega328P sets 115200 and works.

### Before every upload

- Quit Arduino IDE 2.3.10 if it is open. Only one program can hold the port.
- Close the Serial Monitor. It holds the port too.
- Nothing connected to D0 (RX) or D1 (TX).
- Re-check Tools > Port after any replug. The name changes.

### Good log looks like

```
avrdude: Version 6.3-20190619
avrdude: Device signature = 0x1e950f (probably m328p)
avrdude: writing flash (924 bytes):
Writing | ############################ | 100% 0.23s
avrdude: 924 bytes of flash written
```

If the version line says `8.0-arduino.1`, you are in the wrong IDE. Stop.

### Known cosmetic errors, safe to ignore

- `the selected serial port does not exist or your board is not connected`
  appended after a successful upload. 1.8.19 concatenating error strings.

### Talking to the board without the Arduino IDE

The firmware does not care what is on the other end of the wire. Any serial
terminal at 115200 baud that sends a newline on Return will work. macOS has
one built in.

#### Find the port

```
ls /dev/cu.usbserial-*
```

If that comes back empty, or you want to see everything:

```
ls /dev/cu.*
```

Ignore `cu.Bluetooth-Incoming-Port` and anything Bluetooth-related. The Nano
is the `cu.usbserial-` entry. If more than one shows up, unplug the Nano,
run it again, plug back in, run it again, and take the one that appeared.

Always use `cu.`, never `tty.`. The `tty.` device blocks waiting for carrier
detect and will hang.

#### Open it

```
screen /dev/cu.usbserial-1480 115200
```

Substitute the actual name from the `ls`. The board resets when the port
opens, so the banner prints a second or so later. Return sends a newline
already, so `t`, `c 3.11`, `d` and `r` all work as typed.

#### Quit

`Control-A` then `Control-\` then `y`. Or `Control-A` then `k` then `y`.

**Quit properly.** Closing the Terminal window leaves `screen` holding the
port and the next thing that tries to open it will fail. If that happens:

```
screen -ls
screen -X -S <the-session-name> quit
```

#### Logging to a file

`screen` scrollback is awkward. To capture a session:

```
screen -L -Logfile ~/thrust-run.txt /dev/cu.usbserial-1480 115200
```

#### Alternatives

- **CoolTerm** (free, GUI): scrollback, logging, timestamps. Easier than
  `screen` for long runs.
- **`tools/bench.py`** in this package is the right answer for actual test
  runs. It drives the same port, prompts through the height / RPM /
  collective grid, and writes `data/run-log.csv` directly. No transcribing
  numbers by hand.

### Firmware command reference (`thrust_stand.ino`)

115200 baud, line ending **New Line**. Commands are single letters, case
insensitive, one per line. Anything unrecognised returns `! unknown command`.

| Cmd | Does | Output starts with |
|---|---|---|
| `h` | Help. `?` works too. | `=== Nacelle Thrust Stand ===` |
| `t` | **Tare.** Zeroes to current load, 32 samples. | `# taring, hold still...` |
| `r` | One reading, 8 samples averaged. | `# n,ms,lbf,N,raw` |
| `s` | Toggle streaming. Real rate is ~1.2 Hz on RATE=L. | `# streaming ON` / `OFF` |
| `c <lbf>` | **Calibrate** against a hung known weight, 32 samples. | `# calibrating against ...` |
| `f` | **Flip sign. Required on this rig, every calibration.** | `# sign now -1` |
| `z` | Raw counts, unscaled, 32 samples. Diagnostics. | `# raw counts = ` |
| `d` | Dump settings. | `calFactor (counts/lbf) :` |
| `w` | Force-write settings to EEPROM. | `# settings written` |

#### Reading format

```
# n,ms,lbf,N,raw
4,1106238,3.0906,13.748,444579
```

| Field | Meaning |
|---|---|
| `n` | Sample counter. Resets to 0 when streaming starts. |
| `ms` | `millis()` since boot. Not wall clock. |
| `lbf` | Change from tare, in pounds force. **Meaningless until calibrated.** |
| `N` | Same value in newtons (lbf x 4.4482216). |
| `raw` | Raw HX711 counts, 2 samples. Absolute, not tare-relative. |

`raw` is the field to trust before calibration and the field to watch for
drift after.

#### What survives a power cycle, and what does not

Stored in EEPROM: **calFactor** and **sign**. Both reload at boot.

**NOT stored: the tare offset.** `setup()` re-tares on every boot, 32 samples,
against whatever is sitting on the cell at that instant.

Consequences:

- Do not power up with a load hanging. The board will treat that load as zero.
- The boot banner tells you which state you are in. Either
  `# calibration loaded from EEPROM, calFactor = ...` or
  `# NO CALIBRATION STORED.`
- You still tare with `t` at the start of every run, per the protocol. The
  boot tare is not a substitute, the rig will not have settled yet.

#### Calibration sequence

1. Nacelle mounted, nothing else on it, rig settled. `t`
2. Stack the known weight on the nacelle mount. `c 15.0`
3. `d` and confirm calFactor is no longer `1.0000`.
4. `r` with the weight still on. Should read close to the known value.
5. Swap in a second known weight. `r`. Should read close to that one.
6. Remove all added weight. **`f`.**
7. `d`, confirm `sign : -1`. Lift the mount by hand, `r`, confirm **positive**.

**`f` is not optional on this stand.** The cell sits on top of the post with the
nacelle above it, so dead weight is compression and thrust is tension. `c`
always makes the calibration direction positive, so calibrating with weight
stacked on the mount makes compression positive and thrust would read negative.
Send `f` after every `c`. See `docs/05-calibration.md`.

Guards in the code: `c` with a non-positive number is rejected. `c` with less
than 1000 counts of signal is rejected as "signal too small", which means the
weight is not actually on the cell or the wiring is broken.

#### Per-run procedure

`t` motor off and settled, `s` to stream, run the collective staircase at a
governed RPM, `s` to stop, `t` again and check the zero. **If the second tare
has wandered, discard the run.**

### macOS Terminal command reference

| Command | Does |
|---|---|
| `ls /dev/cu.usbserial-*` | Find the Nano. |
| `ls /dev/cu.*` | List every serial device if the above is empty. |
| `screen /dev/cu.usbserial-1480 115200` | Open the connection. |
| `Control-A` then `Control-\` then `y` | Quit screen properly. |
| `Control-A` then `k` then `y` | Kill the window, same effect. |
| `Control-A` then `Control-A` | Send a literal Control-A to the board. |
| `screen -ls` | List sessions left running. |
| `screen -X -S <name> quit` | Kill an orphaned session holding the port. |
| `screen -L -Logfile ~/run.txt /dev/cu.usbserial-1480 115200` | Open and log to file. |
| `lsof /dev/cu.usbserial-1480` | Find what process is holding the port. |
| `system_profiler SPUSBDataType \| grep -A8 -i ch34` | Confirm the CH340 enumerated at all. |

`screen` does not echo what you type. You will see the board's replies but not
your own keystrokes. That is normal, not a dead connection.

### Cable length

USB 2.0 passive cable tops out at about 5 m (16 ft). Beyond that, expect
intermittent dropouts. For a long run to the stand use an **active** USB
extension (repeater chip in the connector) or a **mains-powered** hub at the
midpoint. A bus-powered hub on a long cable is worse than no hub.

A hub does not change the device identity. The CH340 keeps its vendor and
product ID and still enumerates as `cu.usbserial-`. Only the number changes,
same as it does on any replug.

Lengthen the USB, never the load cell leads. Those carry millivolt analog
signal and will pick up ESC and motor noise. Nano and HX711 stay at the stand.

### Do not

- Do not install the WCH CH34x driver. Current setup works. Leave it alone.
- Do not buy a USBasp. Bootloader is fine, signature reads clean.
- Do not use Old Bootloader.
- Do not use `/dev/tty.usbserial-*`. Use `/dev/cu.usbserial-*`.

---

## What is in this package

```
README.md                          this file

docs/00-quickstart.md              one page, if you already have the parts
docs/01-system-design.md           why this rig, what it measures, what it cannot
docs/02-bill-of-materials.md       parts, quantities, sources, links
docs/03-mechanical-build.md        step-by-step assembly
docs/04-wiring.md                  load cell to HX711 to Arduino, noise control
docs/05-calibration.md             load cell calibration, bidirectional, through-zero check
docs/05a-pitch-and-rpm-calibration.md
                                   servo->pitch and throttle->governed RPM. Do this first.
docs/06-test-protocol.md           the height / RPM / collective grid
docs/07-data-reduction.md          turning the raw log into the delivered curves
docs/08-post-vs-hinge.md           the argument, for the conversation with Vermont
docs/09-safety.md                  read before the first spin
docs/10-arduino-first-time.md      IDE setup, Uno vs Nano, upload errors, first bring-up
docs/11-load-cell-datasheet.md     ATO cell dimensions, specs, and CAD envelope
docs/13-arduino-working-config.md  THE PROVEN SETTINGS. Read this one first if stuck.
docs/wiring-adafruit-hx711.svg     printable wiring diagram - Adafruit 5974 board
docs/wiring-generic-hx711.svg      printable wiring diagram - SparkFun / generic green

firmware/thrust_stand/
    thrust_stand.ino               the sketch. tare, calibrate, stream.

tools/
    bench.py                       laptop app: menu, guided run capture, CSV logging
    reduce.py                      turns the run log into the deliverable table
    requirements.txt               pyserial, and nothing else

data/
    run-log-template.csv           the sheet, if you prefer filling it in by hand
```

## The software, in one paragraph

`thrust_stand.ino` runs on the Arduino and does one job: read the load cell and print
thrust over USB. `bench.py` runs on your laptop, drives the sketch, and walks you through
taring, calibration and a full collective staircase at a governed RPM, writing rows
    into a CSV as you go.
`reduce.py` reads that CSV and interpolates the watts required at 7.5 lbf for every height
you tested. That last table is what you send to Vermont.

## The short version

1. Build the post. Nacelle **bolted** on top, S-beam load cell **bolted** directly
   underneath it, post below that, three splayed legs reaching past the disc radius.
   Both studs carry load: dead weight presses the cell in compression, thrust pulls it in
   tension, and it reads continuously through zero between them.
2. Wire the cell to an HX711 to an Arduino. Flash the sketch (IDE 1.8.19, plain ATmega328P).
3. `pip3 install -r tools/requirements.txt`, then `python3 tools/bench.py`.
4. Calibrate once, in compression, with weight stacked on the nacelle mount. **Then send
   `f`.** It is required on this geometry, and any recalibration undoes it, so `f` goes last
   every time. Confirm `sign : -1` and that lifting the mount reads positive.
5. Per height: tare with the nacelle on and the motor off, run the staircase, log each
   plateau, tare again to verify.
6. `python3 tools/reduce.py data/runs.csv --thrust 7.5 --radius 457`

## Expect

267 to 295 W electrical per nacelle at 7.5 lbf, out of ground effect, depending on
head RPM. Predicted 280 W at 1800 rpm, which matches Austin's measured figure. Hover
collective
about 16 deg at 0.75R at 1600 rpm, falling to 10 deg at 2000. Ground effect will save real
power near the floor, but less than
the textbook thrust benefit suggests, because it reduces induced power only.

## Read first

`docs/09-safety.md`. A 914 mm disc at hover thrust holds enough energy to kill you if a
blade lets go. The blade-failure plane is a **disc, not a cone.** Do not stand in it.
