# Thrust stand test procedure

Single-nacelle thrust stand (the `single` package, thrust only). Written 2026-11-25 from the grid point and spin test chat of 11 to 25 Nov 2026, the spin tests of 9 Nov 2026, and the archived terminal session. Revised the same day with the results of spin test 3 (15 Nov 2026). The stand is being rebuilt to add torque, so sections 1 and 2 describe the stand as it was in November 2026.

Read this first when returning to thrust testing. Sections 1 to 5 are the procedure. Section 6 is what the three spin tests showed, section 7 is the measured hover point, and section 8 is what is still open.

## Where things are

| What | Where |
|---|---|
| Stand software | `~/Documents/GitHub/RU3Y-Software/Thrust & Torque Stands/single`, VERSION 2026-10-28.1-single |
| Run logs | `single/tools/logs`: one `stream-`, `rpm-` and `power-` file per session, plus `run-log.csv` for captured points |
| Test 3 logs and report | `stream-`, `rpm-`, `power-20261110-192820.csv` and `Thrust_Test_3_Analysis.pdf` (16 Nov 2026) |
| Takes one and two analysis, 8 figures | `spin_test_analysis_2026-11-12.pdf`, on GitHub |
| Grid point guide, revision 2 | `grid_point_guide.pdf`, on GitHub |
| Pitch positions | `stbd_swash_selector_7pos.txt` and `claude/port_swash_selector_7pos.txt` in this project |
| Raw terminal session | `claude/test-procedure/shell-session-2026-10-26.txt` in this project |
| Software history | `claude/changelog-2026-10-26.md` in this project |

## 1. Start and stop the stand

```
cd ~/Documents/GitHub/RU3Y-Software/"Thrust & Torque Stands"/single
bash tools/start.sh
```

A healthy start prints these, in order:

- `thrust  # Nacelle Thrust Stand ready` for one Nano
- `power   # Nacelle Power Meter  ACS724 +-50A + divider  (A0/A1)` for the other
- `tach = 0` for the FT232H board
- `live.py   2026-10-28.1-single`
- `DASHBOARD   http://localhost:8765`, with a second address for the iPad

start.sh finds the boards itself on every start, so there is nothing to type about ports. If 8765 is busy, live.py steps to the next port and prints the link to use.

To stop: press Ctrl-C once in that terminal and wait for `stopped`. If a port or serial device stays busy afterward, run `bash tools/stop.sh`.

**Restart the dashboard before each test.** Log files are stamped with the time the dashboard was started, not the time of the test. Test 3 ran on 15 Nov inside a dashboard that had been up since 10 Nov, so its files are stamped 20261110-192820.

What went wrong in the archived session, and the fix:

| Typed | Result | Why | Fix |
|---|---|---|---|
| `start.sh` | command not found | the script is not on the shell's search path | `bash tools/start.sh` from `single` |
| `tools/start.sh` | permission denied | the file was not marked executable | `chmod +x tools/start.sh tools/stop.sh` once, from `single`. `bash tools/start.sh` never needs this |
| `chmod +x tools/start.sh` from inside `tools` | No such file | the path is relative to the folder you are in | `cd ..` first |
| `cd ~/Desktop/thrust-torque_deployed` | no such directory | both packages live under the GitHub folder | use the path in the table above |
| commands typed while the dashboard was running | nothing happened | the terminal is busy until live.py stops | Ctrl-C first, then type |
| `bash tools/start.sh` in `thrust-torque_deployed` | the two-nacelle dashboard (`layout dual`) | that is the port and starboard package | for one nacelle, be in `single` |

One run ended with `zsh: terminated  bash tools/start.sh`. That means it was stopped from outside its own terminal. start.sh kills any stale live.py before launching, so starting it in a second window is the likely cause.

To check the tach alone, with the dashboard stopped: `rpm/rpm_reader_static --index 0`. It prints 20 rows a second. All zeros with the rotor still is correct. Ctrl-C to stop.

Devices as seen in that session: thrust Nano `/dev/cu.usbserial-1434110`, power Nano `/dev/cu.usbserial-14341440`, tach board index 0 with a blank serial, so its index follows the USB hub socket. Port 8000 is the video server and start.sh leaves it alone.

## 2. Before the first run of a session

1. Connect the pack through the power meter. Without it the dashboard reads "no pack on the meter" and a captured point has no watts.
2. Motor off: press **Zero amps** on the Power meter card.
3. Nacelle mounted, motor off, rig settled: press **Tare**.
4. If the load cell or mount was touched, run the calibration wizard: Tare, enter the known weight (15.0 lbf), Calibrate, confirm sign is -1, then lift the mount by hand and confirm the number goes positive. Tare again.

Values on the dashboard on 11 Nov 2026, for comparison only (they will change with the rebuild): calFactor 77808 counts per lbf, sign -1, tare 46329; power meter iZero 511.69 counts, iGain 8.1840 counts per A, vScale 11.5508; thrust noise at rest about 0.0006 lbf sd; stream rate about 9 Hz.

## 3. Pitch reference

Pitch is measured at the 0.75 R station: 343 mm from the shaft centerline, 312 mm from the blade root face. Zero is that chord level with the plane of rotation. At zero the tip sits a few degrees nose down.

Bench positions come from the Maestro selector script, channel 4. Type the "set to" value on the Status tab. Each change ramps over 3 seconds.

| Position | Ch 4 set to | STBD FWD / AFT (us) | PORT FWD / AFT (us) |
|---|---|---|---|
| Park (startup) | 1000 | 1500 / 1500 | 1500 / 1500 |
| 0 deg (flat) | 1187 | 1236 / 1745 | 1745 / 1236 |
| 3 deg | 1312 | 1336 / 1645 | 1645 / 1336 |
| 6 deg (hover point) | 1437 | 1436 / 1545 | 1545 / 1436 |
| 9 deg (stalls when static) | 1562 | 1536 / 1445 | 1445 / 1536 |
| 12 deg | 1687 | 1636 / 1345 | 1345 / 1636 |
| 15 deg | 1812 | 1736 / 1245 | 1245 / 1736 |
| 18 deg | 1937 | 1836 / 1145 | 1145 / 1836 |

Park is servo center, not a pitch station.

**The positions behave as labeled.** In test 3 the flat position made 0.75 lbf at 1780 RPM, 3 and 6 made clean lift, and 9 stalled. That rules out the worrying reading of the root-angle disagreement (a zero position that was really about 24 degrees up).

**The true blade angle at each position is still unmeasured.** Two sets of root-angle figures disagree on paper: those of 12 Nov (tip level at 46 degrees root, 0.75 R station then at +12.3) put zero at about 34 degrees root, and the swash pitch chart of 13 Nov lists 58 degrees root for the 0 degree position. Do not rig from root-angle labels or from the "old units" axis in Figure 1 of the takes one and two analysis. To settle it, set each position, hold a straightedge under the chord at the 312 mm mark, and read a digital angle gauge zeroed on a surface square to the main shaft. Both blades should agree within about half a degree. This matters most for comparing the stand against a model: a rough blade-element estimate needs about twice the labeled pitch change to produce the thrust measured, so the steps may be larger than 3 degrees. That estimate assumes chord and lift curve, so it is a reason to measure and not a finding.

## 4. Capture a grid point

A grid point is one test condition: a height, a commanded rotor RPM and a pitch. Capturing it writes one row to `run-log.csv` and puts one dot on the watts against thrust chart.

1. Bring the rotor to the commanded RPM.
2. Set the pitch position. Let it settle a few seconds.
3. With the rotor still spinning, fill in the Mark a grid point box.
4. Press **Capture point**.

| Field | Who fills it | Meaning |
|---|---|---|
| Height mm | you | rotor height above the ground surface |
| RPM cmd | you | rotor speed asked of the governor |
| Collective deg | you | pitch at 0.75 R: the selector position |
| Servo us | you | servo pulse width for that position |
| Throttle % | you | throttle setting that produced the RPM |
| Pack SOC | you | battery state of charge |
| Notes | you | anything unusual |
| RPM actual | tach | leave blank |
| Volts, Amps | power meter | leave blank unless the meter is down |
| Average over s | you | seconds averaged into the one row. 5 is the default |

Thrust has no field because the load cell always measures it.

Pitch and throttle are in none of the logs analyzed so far. In all three tests the pitch at each moment had to be inferred from steps in the data and from notes made at the stand. Fill in Collective deg, Servo us and Throttle % on every capture. Servo us takes one number: a workable convention is the FWD value there and the selector position in Notes.

## 5. Next runs and limits

Limits, from the three tests:

- The stall shows as RPM sagging and thrust falling within a second or two of adding pitch, while amps climb. Back the pitch out.
- Stop if pack amps pass 30. Hover is 13 A and the pushed point is 17 A, so anything near 30 means something is wrong.
- A quick check by eye, valid above about 3 lbf: thrust divided by kilowatts. Clean points run 21 to 26 lbf per kW. Stalled points run 14 or less. Below 3 lbf the number is low for a different reason: spinning the rotor costs about 125 W before any lift.

Runs worth doing next, in order of value:

1. **Find the optimum between 6 and 9.** Hold 7.5 lbf and step pitch 6.5, 7, 7.5, 8, adjusting throttle each time. The lowest wattage is the true sweet spot, and the RPM it lands at feeds the gearing choice. By linear interpolation the starboard FWD / AFT values are 1453 / 1528, 1469 / 1512, 1486 / 1495 and 1503 / 1478 (port mirrored). These go in as edits to a position's two numbers in the selector script.
2. **Spin the hub with no blades** at 1650 to 1850 RPM. That separates gearbox and motor loss from blade drag in the 125 W flat-pitch figure.
3. **Record throttle and ESC temperature**, and pull the ESC's own data log through Castle Link. See the gearing item in section 8.
4. **Capture grid points** as in section 4, so pitch and throttle are in the record.

Cruise at 1000 RPM cannot be reproduced on a static stand (see section 8).

## 6. What the spin tests showed

### Test 3, 15 Nov 2026: the hover point

3:1 gearing, fixed throttle with no governor, pitch stepped through the flat, 3, 6 and 9 degree positions. The motor ran for 10 minutes with no ESC shutdown. Rows are stamped 15 Nov, 15:59 to 16:11. The figures below were reduced again from the logs on 25 Nov and agree with the table in the test 3 report.

| Position | Rotor RPM | Thrust (lbf) | Volts | Amps | Watts | lbf per kW | Note |
|---|---|---|---|---|---|---|---|
| Flat | 1645 | 0.67 | 26.5 | 4.0 | 107 | 6 | |
| Flat | 1780 | 0.75 | 26.4 | 4.8 | 126 | 6 | |
| 3 deg | 1693 | 3.43 | 26.3 | 5.3 | 140 | 25 | |
| 3 deg | 1837 | 3.99 | 26.3 | 6.5 | 171 | 23 | |
| 6 deg | 1693 | 7.06 | 25.9 | 11.9 | 309 | 23 | just set |
| **6 deg** | **1760** | **7.51** | **25.7** | **13.1** | **337** | **22** | **hover point** |
| 9 deg | 1610 | 6.8 | 25.4 | 20.5 | 520 | 13 | stalled, tried twice |
| 6 deg | 1742 | 7.72 | 25.3 | 13.9 | 352 | 22 | after the 9 degree trials |
| 6 deg | 1711 | 7.24 | 24.7 | 13.0 | 322 | 22 | late in the hold |
| 6 deg | 1860 | 8.67 | 24.3 | 16.8 | 409 | 21 | pushed, held 70 s |

- **The 6 degree position is the hover point.** 7.5 lbf at 1760 RPM for 337 W and 13.1 A. About 7 minutes were spent at 6 degrees, including one unbroken hold of 3.4 minutes at fixed throttle.
- **It has headroom.** Pushed to 8.7 lbf at 1860 RPM for 409 W and 16.8 A and held for 70 seconds, with the same efficiency as at 7.5 lbf. Across every 6 degree point thrust follows RPM squared: 2.4 to 2.5 lbf per (1000 RPM) squared.
- **The 9 degree position is past the stall.** At the same throttle, thrust fell from 7.5 to 6.8 lbf, power rose from 337 to about 520 W, current rose from 13 to 20.5 A and RPM sagged from 1760 to 1610. It did the same thing both times. The stall lies between the 6 and 9 positions and this test does not locate it.
- **Spinning the rotor costs about 125 W before any lift.** That is the flat-pitch figure at 1780 RPM, over a third of hover power. It is why 3 degrees loses at equal thrust: scaled to 7.5 lbf, the 3 degree position would need about 2520 RPM and 440 W against 337 W at 6. Slower and steeper is cheaper, up to the stall.
- **The ESC was never near its limit.** 13 A at hover, 17 A pushed, and one momentary peak of 34 A while the throttle was being raised for the pushed hold. This supports the reading of takes one and two: those cuts came from over-pitch.
- **Pack.** 26.75 V at rest before the run and 24.7 V after. Under hover load it ran from 25.7 V down to 24.3 V, not 22 to 24 V. Lowest sample 23.0 V, momentary. About 2.0 Ah and 49 Wh used.
- **The figures noted at the stand hold up.** Sweet spot 7.5 lbf, 1750 RPM, 325 W, 13 A; limit 1850 RPM, 8.5 lbf, 400 W, 17 A. The 325 W is the late-hold figure, when thrust had eased to 7.2 lbf as the pack sagged.

Measurement notes from test 3:

- **The power meter restarted four times** within 36 seconds during the pushed hold, losing about 5 seconds of power data each time. RPM and thrust kept logging and the rotor kept turning, so this is the logger and not the ESC. It did not happen at 20.5 A in the 9 degree trials, so current alone does not explain it. The lowest voltage sample of the run (23.0 V) falls inside the same cluster. Cause not established.
- **Thrust carries a ripple** of 0.1 to 0.2 lbf amplitude, 0.3 to 0.5 lbf peak to peak. The test 3 report ties it to once per rev (blade track or balance). Thrust is sampled at 8.7 Hz and the rotor turns at about 29 Hz, so the true size is likely larger than logged.
- **Thrust drifts down** 0.1 to 0.25 lbf per minute during a hold: part pack sag at fixed throttle, part creep or recirculation. Allow about 3% on any single thrust figure.
- Load cell zero moved from 0.00 to +0.05 lbf across the run.
- One tach count is 29 rotor RPM in a 50 ms window. Averages are sound, single samples are not.

### Takes one and two, 9 Nov 2026: the ESC cuts

Software and hardware worked. The ESC (Castle Phoenix Edge Lite 50) shut down abruptly in both takes.

| | Take one | Take two |
|---|---|---|
| Log tag | 20261109-143501 | 20261109-152111 |
| Time of cut | 14:41:15 | 15:28:30.3 |
| Pack amps at the cut | about 51 A, peak 54.5 | 49 A, peak 51.6 |
| Pack volts | 23.7 V | 23.1 V |
| Electrical power | about 1215 W | 1132 W |
| Rotor RPM | 1539 | 1453 |
| Thrust | 5.9 lbf | 5.808 lbf |

- **Cause: over-current.** Both cuts came within a second of pack current reaching about 50 A, the ESC rating. The pack never went below 22.5 V, so it was not low voltage. Not confirmed from the ESC's own log.
- **Why the current got there: stalled blades.** The linkages had been rigged with the tip level as zero, so every setting was far too steep. More pitch gave less thrust for more power.
- **Clean points before stall:** 6.1 lbf at 1797 RPM for 245 W (take two), and 6.7 lbf at 1627 RPM for 283 W (take one). Both sit on the same watts-against-thrust line as the 6 degree points of test 3.
- **Target thrust was reached once, stalled:** 7.8 lbf at 1752 RPM for 701 W, about twice what test 3 needed for the same thrust.
- The power meter's hall sensor is a +-50 A part. Readings near 50 A are at the top of its range.

## 7. Hover operating point

The hypothesis of 12 Nov, written before the rotor had been run at a correct pitch, against what test 3 measured:

| Variable | Hypothesis | Measured in test 3 |
|---|---|---|
| Thrust | 7.5 lbf | 7.51 lbf |
| Rotor RPM | 1800 | 1760 |
| Pitch | 8 deg (6 to 10) | the 6 degree position |
| Electrical power | 335 W (310 to 370) | 337 W |
| Pack amps | 14 A (13 to 17) | 13.1 A at 25.7 V |
| Motor RPM at 3:1 | 5400 | 5281 |
| Throttle | about 75% | 48% command noted at the stand; ESC output not logged |

At exactly 1800 RPM the 6 degree position would make about 7.9 lbf for about 360 W. That is scaled from the 1760 point, not measured.

Usable range at the 6 degree position on this stand: 7.5 lbf at 1760 RPM up to at least 8.7 lbf at 1860 RPM.

## 8. Open items

- **Gearing.** Tested at 3:1 only. The gearing table in the test 3 report took the 48% throttle noted at hover as the ESC's output duty and from that inferred a motor constant near 480 RPM per volt. The motor is rated 320 KV, and at 48% duty it would need at least 428 to turn 5281 RPM on 25.7 V. So the 48% is the throttle command, not the duty, and the report's ceilings (21, 19 and 16 lbf) are too high. Estimates with 320 KV, good to roughly 10%:

  | | 3:1 | 3.5:1 | 4:1 |
  |---|---|---|---|
  | ESC duty at hover, pack 25.7 V down to 24.0 V | 70 to 77% | 80 to 88% | 90 to 98% |
  | ESC duty for the pushed point, 1860 RPM at 24.3 V | about 80% | about 90% | not reachable |
  | Full-throttle thrust ceiling at 6 degrees, pack 26 V down to 24 V | 13.5 to 11 lbf | 11 to 9 lbf | 9 to 7.5 lbf |
  | No-load rotor RPM at 24 V | 2560 | 2194 | 1920 |

  On these numbers 4:1 cannot hold the pushed point and has no margin at hover on a part-used pack. 3.5:1 moves the ESC from about 70% to about 80% duty at hover and costs about 2 lbf of ceiling. Because the stall sits just above 6 degrees, extra pitch cannot make up much of that. The deciding number is the peak static thrust each nacelle must make. The ESC's data log, read through Castle Link, should include output power percent, which would replace the assumption. No decision is recorded.
- **The optimum between 6 and 9.** Not located. Run 1 in section 5.
- **True blade angles.** Section 3.
- **Power meter restarts under load.** Check its USB cable routing, supply and grounds before the next high-power run.
- **Thrust ripple.** Check blade track and balance. A thrust sample rate above 100 Hz would let the once-per-rev tone be measured directly.
- **The gap to 446 W.** The stand needs 337 W for 7.5 lbf. Austin's flight figure is 446 W per nacelle at 1800 RPM. On the measured 6 degree curve, 446 W is 9.05 lbf at 1930 RPM. Candidates: the wing in the downwash, other loads in the flight watts, a steeper pitch in flight, ground effect on the stand, thrust calibration. Not separable from present data.
- **ESC cause in takes one and two.** Test 3 makes over-pitch the working explanation. The Edge data log through Castle Link would confirm over-current against over-temperature.
- **Cruise.** Retracted: the "10 to 14 degrees" cruise pitch in the grid point guide. Cruise pitch depends on airspeed (about 33 degrees at 0.75 R at 20 m/s and 1000 RPM) and cannot be tested statically. With air flowing through the disk the blades unload and the best pitch moves higher, so the 6 degree figure is a hover figure only. Austin's cruise airspeed decides how much collective travel is needed.
- **Two-nacelle package.** In `thrust-torque_deployed`, the port finder reports `STBD = -` while live.py prints `port=0  stbd=1`. Worth checking that live.py does not try to open a second tach board that is not there.
- **After the torque rebuild.** Sections 1 and 2 will need revising for the new board and port.
