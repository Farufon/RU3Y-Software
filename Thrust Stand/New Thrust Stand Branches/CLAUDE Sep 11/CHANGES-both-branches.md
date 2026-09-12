# Changes, both branches

## 1. Working config is now in the README, up front

`arduino-nano-working-config.md` is inserted into `README.md` as section
**"Arduino and serial: the working configuration"**, immediately after "Start
here" and before the package contents. Full text: IDE rule, settings table,
pre-upload checklist, good-log sample, cosmetic errors, `screen` usage, the
firmware command reference, EEPROM behaviour, the macOS Terminal table, cable
length, and the "do not" list.

It also remains as `docs/13-arduino-working-config.md`. **The two are
duplicates.** If you edit one, edit both, or delete doc 13 and keep the README
as the single source.

Two lines were corrected in the embedded copy rather than shipped as written:
the `s` streaming rate (10 Hz claimed, ~1.2 Hz actual on RATE=L), and
"`f` is rarely needed", which is the opposite of true on this rig.

## 2. The load path, corrected everywhere

Previously the docs treated `f` as a fallback for a reversed wire. On this
geometry it is a required calibration step.

The stack: legs, post, **S-beam bolted to the top of the post**, **nacelle bolted
on top of the cell**. Both studs carry load. Dead weight is compression, thrust
is tension, and the cell reads continuously through zero. Nothing rests loose.

Because compression is the only direction a known force can be applied in, `c`
always makes *down* positive, so thrust would log negative. `f` after every `c`.
And `c` re-derives the sign each time, so recalibrating silently undoes a
previous `f`: **`f` goes last, every time.**

| File | Change |
|---|---|
| `README.md` | Short version steps 1, 4, 5 rewritten: bolted both ends, calibrate in compression, `f`, tare with nacelle on |
| `docs/00-quickstart.md` | Calibrate section: stack not hang, `f` required, confirm `sign : -1` |
| `docs/03-mechanical-build.md` | Both studs are the tension path; a loose stud loses every reading above dead weight |
| `docs/04-wiring.md` | Do not swap green/white on this rig; `f` carries the sign. Both fixes together cancel out |
| `docs/05-calibration.md` | New section "Which way the cell is loaded, and why `f` is mandatory". Weight is stacked, not hung. Tension calibration removed as impractical. Direction check rewritten |
| `docs/06-test-protocol.md` | Step 3 tare is with the nacelle mounted. New step 3a: confirm the sign before the first run of the day |
| `docs/10`, `docs/13` | `f` reference lines, calibration sequence with the flip and the confirmation |
| `docs/12` (live branch) | `sign` is on the settings line; check it reads `-1` before a run |
| `thrust_stand.ino` | Help text: `f` is REQUIRED after every `c` |
| `tools/bench.py` | **Wizard never sent `f` at all.** Added steps 4 and 5: send `f`, then lift the mount and verify the reading is positive, with a hard warning if it is not |

Advice removed as wrong for this geometry: inverting the fixture (the post is
under it), calibrating in tension by pulling down through the mount, and rigging
a pulley as the normal path. Pulley friction is still documented, as the reason
not to.

## 3. Earlier corrections, from the previous pass

IDE 1.8.19 not 2.x; plain `ATmega328P` not Old Bootloader in four places; no
CH340 driver needed or wanted; troubleshooting table keyed on log text rather
than "press reset"; streaming rate; EEPROM stores calFactor and sign but not
the tare, so do not power up or open a serial port with a load hanging.

## 4. Still open

- **Dead weight is unresolved.** `docs/05` says the nacelle is ~1200 g and dead
  weight on the cell is 4.5 to 5 lb, putting the load reversal at 4.8 lbf, which
  it calls 64% of hover thrust. You have said 2.5 lb, then 3.5 lb. Weigh the
  assembled nacelle plus adapter and the crossing point and that percentage both
  move. It matters: doc 05 warns that a bad joint at the crossing fakes a
  convincing aerodynamic effect.
- **Linearity table** in doc 05 assumes 2, 5 and 10 lb reference weights from the
  BOM. Rebuild it around what you actually own.

## Branch difference

Identical except:

    tools/live.py                 live branch only
    tools/bemt_curves_v49.json    live branch only
    docs/12-live-readout.md       live branch only
    README.md, docs/10, docs/13, tools/requirements.txt   wording only

Firmware, wiring, calibration, protocol, mechanical build and reduction are
byte-identical. A fix to either copies straight across.
