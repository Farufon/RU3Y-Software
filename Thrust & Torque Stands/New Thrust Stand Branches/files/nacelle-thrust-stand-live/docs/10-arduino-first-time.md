# 10 - Arduino, First Time

Written assuming you have never opened the Arduino IDE. If you have, skip to
"Install the HX711 library."

> **This board has been through bring-up. It works.** The settings below are the
> ones that were proven on the actual hardware, not the ones the internet
> recommends. `docs/13-arduino-working-config.md` is the short version; read that
> if you just need to get running again. This document explains why.

## What the board actually is

An Arduino is a small microcontroller board. You write a program on your laptop, press
Upload, and the program is transferred over USB into the chip and runs there forever, with
or without the laptop attached. The program is called a **sketch** and lives in a `.ino`
file.

Your sketch does one job: read the HX711 and print numbers over USB.

## Uno or Nano?

Both work. Identical wiring, identical sketch, no changes needed.

| | Uno | Nano |
|---|---|---|
| Size | Credit card | Postage stamp |
| USB | Type B, chunky | Mini or Micro USB |
| Pins | Headers, easy to probe | Header pins, usually needs soldering or a breakout |
| Driver | None needed | None needed on this Mac. See step 2. |
| Best for | Learning, first build | Permanent install in a small box |

**You own Elegoo Nanos, so use those.** They are entirely capable of this job. Step 2 below
is written specifically for them and covers the cable and the loose headers. If
you also have an Uno lying around it is marginally easier to probe with a meter, but it is
not worth buying one.

## Step 1: install the IDE

**Install Arduino IDE 1.8.19, not 2.x.** Get it from **arduino.cc/en/software**, in the
"Legacy IDE (1.8.X)" section further down that page. Free, all platforms.

This is not nostalgia. IDE 2.3.10 ships **avrdude 8.0**, and on this Mac and this
CH340 board avrdude 8.0 syncs with the bootloader, reads the device signature cleanly,
then times out at 0% of the flash write every single time. IDE 1.8.19 ships **avrdude
6.3**, which writes the same hex in about 0.2 seconds and verifies it. Nothing else
differs: same board, same cable, same port, same bootloader.

You can have both installed. They are different applications: 1.8.19 is named
**`Arduino`**, 2.3.10 is named **`Arduino IDE`**. Upload from `Arduino`.

Install and open it. You get a code window with `void setup()` and `void loop()` already in
it. Ignore that for now.

> **Trap.** Installing 1.8.19 is not sufficient on its own. If the AVR core was installed
> through Boards Manager, 1.8.19 may still reach for that core's avrdude 8.0. After any
> upload, check the version line in the log. It must say `6.3-20190619`. If it says
> `8.0-arduino.1`, stop; see doc 13.

## Step 2: your specific board, the Elegoo Nano V3.0

You have the **Elegoo Nano V3.0, 3-pack, without USB cable** (ASIN B0713XK923, Elegoo part
EL-CB-005). Everything below is specific to that board.

### Three things it needs that an Uno does not

**1. The USB serial chip.** This board uses ATmega328P and **CH340** rather than the
FT232 on official Arduinos.

**On this Mac, no driver is needed and none should be installed.** macOS 15.7.5 enumerates
the board on its own as `/dev/cu.usbserial-XXXX`. This was verified on the actual hardware:
the port appears, uploads succeed, and the serial monitor works, with no third-party
driver present.

Do not install the WCH CH34x driver. It is not on the Mac App Store, approving a driver
extension requires physical presence at the machine (so it cannot be done over VPN anyway),
and the setup works without it. Adding a driver to a working USB stack is a way to break it.

On Linux the driver is already in the kernel and you need nothing.

Full Elegoo manual, if you want it: https://m.media-amazon.com/images/I/B1RN92-vT4L.pdf

**2. A Mini-B USB cable.** Not Micro, not USB-C. Your box says "Without USB Cable" so you
have to supply one, and it must be a **data** cable. A charge-only cable is the single most
common reason a board never appears in the port list. If you have a pile of old cables,
the Mini-B is the trapezoidal one from 2000s-era digital cameras.

**3. The headers are loose.** Your listing specifies "Loose Headers", meaning the pin strips
come in the bag unsoldered. You have two options:

- Solder the full strips. Twenty minutes, and the board then works on a breadboard.
- **Solder only the four pins this project uses.** Faster, and perfectly adequate.

If you take the second option, the pins you need are conveniently placed:

| Pin | Which side | Note |
|---|---|---|
| D3 | digital side | |
| D2 | digital side | adjacent to D3 |
| GND | digital side | adjacent to D2 |
| 5V | analog side | opposite edge, between A7 and RST |

**D3, D2 and GND are three consecutive pads on the digital side.** Only the 5V pin is on
the far edge. Four joints total.

### IDE settings for this board

| Setting | Value |
|---|---|
| Tools > Board | `Arduino AVR Boards > Arduino Nano` |
| Tools > Processor | **`ATmega328P`** (plain) |
| Tools > Port | `/dev/cu.usbserial-XXXX` |

**Use plain `ATmega328P`. Do not use Old Bootloader.** The common advice is the opposite,
and it is wrong for these particular boards. Old Bootloader sets the upload baud to 57600;
these Elegoo Nanos run Optiboot at **115200**, which is what the plain setting uses. On Old
Bootloader every sync attempt comes back `resp=0x00` and the upload never starts.

This matters more than it sounds. Hours were spent testing cables, USB ports and three
separate boards while the processor setting was wrong, and every one of those tests was run
at the wrong baud and therefore proved nothing.

**Use `cu.`, never `tty.`** The `tty.` device blocks waiting for carrier detect and hangs.

**No reset button press is needed.** Hold-and-release reset versus no reset at all produced
byte-identical logs on this board. If an upload fails, the reset button is not the answer;
the avrdude version is.

### Power note that matters for measurement

The Nano can take power from Mini-B USB, from 7-12 V unregulated on VIN, or from 5 V
regulated on the 5V pin, and it automatically selects the highest source. For this project:
**USB from the laptop only.** Never from the flight pack.

Some good news on supply quality. The HX711 is a **ratiometric** converter: it uses the same
rail to excite the load cell bridge and to reference the ADC, so if your 5V rail is actually
4.7 V the two effects cancel and your reading does not shift. What you cannot tolerate is a
rail that sags so far the HX711's internal analogue regulator loses headroom. In practice
that means: plug into a real USB port on the laptop, not a cheap unpowered hub, and use a
short thick cable. Slow unexplained drift is often a thin two-metre USB cable.

## Step 3: smoke test with Blink

Do this before touching the load cell. It proves the toolchain works, so that when the real
sketch misbehaves you know it is not the toolchain.

1. Plug the board in with USB.
2. **File > Examples > 01.Basics > Blink**
3. **Tools > Board**:
   - Uno: `Arduino AVR Boards > Arduino Uno`
   - Nano: `Arduino AVR Boards > Arduino Nano`
4. **Tools > Processor** (Nano only): plain `ATmega328P`. For your Elegoo boards this is
   the setting that works. Do **not** use `ATmega328P (Old Bootloader)`.
5. **Tools > Port**: pick the one that appeared when you plugged in. If unsure, unplug,
   look at the list, plug in, look again. The new entry is your board.
6. Press the **Upload** arrow (top left).

The onboard LED should blink once per second. If it does, everything downstream is your
wiring or your code, not your setup.

### If upload fails

| Symptom in the log | Cause and fix |
|---|---|
| `unable to write flash (rc = -1)`, after the signature read succeeded | **avrdude 8.0.** Check the version line. You are in IDE 2.3.10, or 1.8.19 is using the Boards Manager core. Use IDE 1.8.19's own toolchain. This is the big one. |
| `stk500_recv(): programmer is not responding`, `resp=0x00` on all 10 attempts | Wrong processor. Set plain `ATmega328P`, not Old Bootloader. |
| No port appears at all | Charge-only cable, or not a Mini-B cable. **Not** a missing driver; none is required on this Mac. |
| `Permission denied /dev/ttyUSB0` (Linux) | `sudo usermod -a -G dialout $USER` then log out and back in |
| `Port busy` / `Access denied` | Close the Serial Monitor, close `bench.py`, close `live.py`, quit any stray `screen` session, then upload |
| Uploads but nothing happens | Wrong board selected under Tools > Board |

A good log reads:

```
avrdude: Version 6.3-20190619
avrdude: Device signature = 0x1e950f (probably m328p)
Writing | ################## | 100% 0.23s
```

**Cosmetic error to ignore:** 1.8.19 sometimes appends `the selected serial port does not
exist or your board is not connected` to a **successful** upload. If the write and verify
lines are there, the upload worked.

The charge-only cable is a more common cause than people expect. If nothing appears in the
port list, try a different cable before anything else.

**Do not buy an ISP programmer.** If avrdude reads the device signature at all, the
bootloader is alive and an ISP would not have helped. That was nearly bought here.

## Step 4: install the HX711 library

The sketch needs one library.

1. **Tools > Manage Libraries** (or the books icon in the left sidebar)
2. Search **HX711**
3. Install **"HX711 Arduino Library" by Bogdan Necula**

There are several HX711 libraries. Get that one specifically; the sketch is written against
its API. It is the same library SparkFun's guide recommends, and it is tested on the
ATmega328P your Nano uses.

**Do not** also install SparkFun's example sketches and mix them with this package. Their
examples put DOUT on pin 3 and CLK on pin 2, which is the reverse of this package. See the
warning in `docs/04-wiring.md`.

## Step 5: upload the thrust stand sketch

1. **File > Open**, navigate to `firmware/thrust_stand/thrust_stand.ino`
2. The IDE will ask to put it in a folder of the same name. Say yes.
3. Confirm Board, Processor and Port are still set from step 3.
4. Upload.

## Step 6: talk to it

Open **Tools > Serial Monitor**. Two settings in the Serial Monitor window matter:

- Baud rate: **115200**
- Line ending: **New Line** (some IDE versions say "Newline")

If the line ending is wrong, you can type commands but the board will never act on them.
This trips up everyone once.

You should see the startup banner. Type `h` and press Enter for the command list.

At this point, with nothing wired to the HX711, you will see a complaint that the HX711 is
not responding. That is correct and expected.

## Step 7: wire it and use the laptop software

Wire per `docs/04-wiring.md`. Then **close the Serial Monitor** (only one program can hold
the port) and run the laptop application:

```
cd tools
pip3 install -r requirements.txt
python3 bench.py
```

It finds the port, gives you a menu, and walks you through taring, calibration and a full
guided run.

**Try it without hardware first:**

```
python3 bench.py --simulate
```

That runs a fake stand with synthetic thrust data so you can learn the workflow before the
parts arrive. At the menu, type `throttle` to move the fake motor, then use option 4 to walk
a full guided capture and see exactly what a bench session feels like.

Note that in the simulator, `throttle` is just a crude way to make the fake load cell read
something. On the real rig this head is **governed**: throttle sets RPM and thrust comes
from collective pitch. See doc 06.

## Sketch commands, quick reference

| Cmd | Does |
|---|---|
| `h` | Help |
| `t` | Tare. Motor off, rig settled. Every run. |
| `r` | One reading |
| `s` | Start / stop streaming. See the rate note below. |
| `c 5.0` | Calibrate against a known 5.0 lbf weight |
| `f` | Flip sign. **Required after every `c` on this rig.** See doc 05. |
| `z` | Raw counts, for diagnostics |
| `d` | Dump settings |
| `w` | Force-write settings to EEPROM |

**Streaming rate.** The firmware asks for 10 Hz, but each reported value averages 8 HX711
conversions, and with the RATE switch on **L** the HX711 converts at 10 SPS. So `s`
actually delivers about **1.2 Hz**. That is fine for steady-state hover points, where you
are averaging seconds anyway. Move the RATE switch to **H** (80 SPS) to get the intended
10 Hz with no code change. See `docs/04-wiring.md` and `docs/12-live-readout.md`.

**The tare offset is not stored in EEPROM.** `calFactor` and `sign` are; the tare is not.
The sketch re-tares at every boot against whatever is sitting on the cell at that instant,
so **do not power up with a load hanging**. Opening a serial port resets the board, which
means opening the Serial Monitor re-tares it too.

Calibration is saved in EEPROM and survives power cycles. Tare is not, and should not be:
you re-tare every run on purpose.

## Two things that will save you an evening

**Only one program can hold the serial port.** If bench.py says the port is busy, the Serial
Monitor is open. If the IDE says the port is busy, bench.py is running. Close one.

**The board resets when a program connects to it.** That is why bench.py waits about two
seconds after opening the port. If you see garbage on connect, that is the boot banner, and
it is harmless.
