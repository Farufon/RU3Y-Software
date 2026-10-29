# Arduino Nano Upload: Working Configuration

Elegoo Nano V3.0 (ATmega328P / CH340) on Intel Mac, macOS 15.7.5.

## The rule

**Use Arduino IDE 1.8.19. Do not use 2.3.10 for uploads.**

2.3.10 ships avrdude 8.0, which cannot write flash to this board.
1.8.19 ships avrdude 6.3, which writes it in 0.23 seconds.

## Settings

| Item | Value |
|---|---|
| IDE | Arduino 1.8.19 (the app named `Arduino`, not `Arduino IDE`) |
| Board | Tools > Board > Arduino AVR Boards > Arduino Nano |
| Processor | Tools > Processor > **ATmega328P** (NOT Old Bootloader) |
| Port | Tools > Port > `/dev/cu.usbserial-XXXX` |
| Verify after upload | Can stay on. Read-back verifies clean on the soldered board. |
| Serial Monitor baud | 115200 for `thrust_stand.ino`, line ending New Line |

Old Bootloader sets 57600 and fails to sync. Plain ATmega328P sets 115200 and works.

## Before every upload

- Quit Arduino IDE 2.3.10 if it is open. Only one program can hold the port.
- Close the Serial Monitor. It holds the port too.
- Nothing connected to D0 (RX) or D1 (TX).
- Re-check Tools > Port after any replug. The name changes.

## Good log looks like

```
avrdude: Version 6.3-20190619
avrdude: Device signature = 0x1e950f (probably m328p)
avrdude: writing flash (924 bytes):
Writing | ############################ | 100% 0.23s
avrdude: 924 bytes of flash written
```

If the version line says `8.0-arduino.1`, you are in the wrong IDE. Stop.

## Known cosmetic errors, safe to ignore

- `the selected serial port does not exist or your board is not connected`
  appended after a successful upload. 1.8.19 concatenating error strings.

## Talking to the board without the Arduino IDE

The firmware does not care what is on the other end of the wire. Any serial
terminal at 115200 baud that sends a newline on Return will work. macOS has
one built in.

### Find the port

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

### Open it

```
screen /dev/cu.usbserial-1480 115200
```

Substitute the actual name from the `ls`. The board resets when the port
opens, so the banner prints a second or so later. Return sends a newline
already, so `t`, `c 3.11`, `d` and `r` all work as typed.

### Quit

`Control-A` then `Control-\` then `y`. Or `Control-A` then `k` then `y`.

**Quit properly.** Closing the Terminal window leaves `screen` holding the
port and the next thing that tries to open it will fail. If that happens:

```
screen -ls
screen -X -S <the-session-name> quit
```

### Logging to a file

`screen` scrollback is awkward. To capture a session:

```
screen -L -Logfile ~/thrust-run.txt /dev/cu.usbserial-1480 115200
```

### Alternatives

- **CoolTerm** (free, GUI): scrollback, logging, timestamps. Easier than
  `screen` for long runs.
- **`tools/live.py`** is the best option in this branch. A browser dashboard
  with a live number, a strip chart, rolling noise statistics, one-click tare
  and calibrate, automatic logging, and a chart of your points against the
  BEMT prediction. It also works from an iPad over the VPN, which `screen`
  cannot. See `docs/12-live-readout.md`.
- **`tools/bench.py`** walks the height / RPM / collective grid as a guided
  menu session and writes `data/run-log.csv` directly.

Only one program can hold the port. Pick one.

## Firmware command reference (`thrust_stand.ino`)

115200 baud, line ending **New Line**. Commands are single letters, case
insensitive, one per line. Anything unrecognised returns `! unknown command`.

| Cmd | Does | Output starts with |
|---|---|---|
| `h` | Help. `?` works too. | `=== Nacelle Thrust Stand ===` |
| `t` | **Tare.** Zeroes to current load, 32 samples. | `# taring, hold still...` |
| `r` | One reading, 8 samples averaged. | `# n,ms,lbf,N,raw` |
| `s` | Toggle streaming. Send again to stop. Real rate below. | `# streaming ON` / `OFF` |
| `c <lbf>` | **Calibrate** against a hung known weight, 32 samples. | `# calibrating against ...` |
| `f` | **Flip sign. Required on this rig, after every `c`.** | `# sign now -1` |
| `z` | Raw counts, unscaled, 32 samples. Diagnostics. | `# raw counts = ` |
| `d` | Dump settings. | `calFactor (counts/lbf) :` |
| `w` | Force-write settings to EEPROM. | `# settings written` |

**Streaming rate is not 10 Hz.** The firmware asks for 10 Hz (`STREAM_MS = 100`),
but each reported value averages 8 HX711 conversions and the **RATE switch is on
L**, which is 10 SPS. Eight conversions take 800 ms, so `s` delivers about
**1.2 Hz** and the loop blocks while collecting. Move the RATE switch to **H**
(80 SPS) to get the intended 10 Hz with no code change. `tools/live.py` displays the
measured rate, which is the number to trust.

### Reading format

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

### What survives a power cycle, and what does not

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

### Calibration sequence

1. Nacelle mounted, nothing else on it, rig settled. `t`
2. Stack the known weight on the nacelle mount. `c 15.0`
3. `d` and confirm calFactor is no longer `1.0000`.
4. `r` with the weight still on. Should read close to the known value.
5. Swap in a second known weight. `r`. Should read close to that one.
6. Remove the added weight. **`f`.**
7. `d`, confirm `sign : -1`. Lift the mount by hand, `r`, confirm **positive**.

**`f` is not optional on this stand.** The cell is bolted to the top of the
post with the nacelle bolted above it, so dead weight is compression and thrust
is tension. `c` always makes the calibration direction positive, and compression
is the only direction you can apply a known force in. So `c` makes down
positive, and thrust would read negative. Send `f` after every `c`.

Guards in the code: `c` with a non-positive number is rejected. `c` with less
than 1000 counts of signal is rejected as "signal too small", which means the
weight is not actually on the cell or the wiring is broken.

### Per-run procedure

`t` motor off and settled, `s` to stream, run the collective staircase at a
governed RPM, `s` to stop, `t` again and check the zero. **If the second tare
has wandered, discard the run.**

## macOS Terminal command reference

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

## Cable length

USB 2.0 passive cable tops out at about 5 m (16 ft). Beyond that, expect
intermittent dropouts. For a long run to the stand use an **active** USB
extension (repeater chip in the connector) or a **mains-powered** hub at the
midpoint. A bus-powered hub on a long cable is worse than no hub.

A hub does not change the device identity. The CH340 keeps its vendor and
product ID and still enumerates as `cu.usbserial-`. Only the number changes,
same as it does on any replug.

Lengthen the USB, never the load cell leads. Those carry millivolt analog
signal and will pick up ESC and motor noise. Nano and HX711 stay at the stand.

## Do not

- Do not install the WCH CH34x driver. Current setup works. Leave it alone.
- Do not buy a USBasp. Bootloader is fine, signature reads clean.
- Do not use Old Bootloader.
- Do not use `/dev/tty.usbserial-*`. Use `/dev/cu.usbserial-*`.
