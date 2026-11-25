# Thrust stand test procedure

Single-nacelle thrust stand (the `single` package, thrust only). Written 2026-11-25 from the grid point and spin test chat of 11 to 25 Nov 2026, the two spin tests of 9 Nov 2026, and the archived terminal session. The stand is being rebuilt to add torque, so sections 1 and 2 describe the stand as it was in November 2026.

Read this first when returning to thrust testing. Sections 1 to 5 are the procedure. Sections 6 to 8 are what the first two spin tests showed and what is still open.

## Where things are

| What | Where |
|---|---|
| Stand software | `~/Documents/GitHub/RU3Y-Software/Thrust & Torque Stands/single`, VERSION 2026-10-28.1-single |
| Run logs | `single/tools/logs`: one `stream-`, `rpm-` and `power-` file per session, plus `run-log.csv` for captured points |
| Grid point guide, revision 2 | `grid_point_guide.pdf`, on GitHub |
| Spin test analysis, 8 figures | `spin_test_analysis_2026-11-12.pdf`, on GitHub |
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

**Check this before every test series.** Set the 0 degree position, hold a straightedge under the chord at the 312 mm mark, and read a digital angle gauge that was zeroed on a surface square to the main shaft. It should read 0, and both blades should agree within about half a degree. Then step to 3 and 6 and confirm the gauge follows.

The reason to trust the gauge and not a root-angle label: the figures given on 12 Nov (tip level at 46 degrees root, 0.75 R station then at +12.3) put zero at about 34 degrees root, while the swash pitch chart of 13 Nov lists 58 degrees root for the 0 degree position. Those two do not agree. The "old units" axis in Figure 1 of the spin test analysis predates the linkage trim and should not be used for rigging.

Bench positions come from the Maestro selector script, channel 4. Type the "set to" value on the Status tab. Each change ramps over 3 seconds.

| Position | Ch 4 set to | STBD FWD / AFT (us) | PORT FWD / AFT (us) |
|---|---|---|---|
| Park (startup) | 1000 | 1500 / 1500 | 1500 / 1500 |
| 0 deg | 1187 | 1236 / 1745 | 1745 / 1236 |
| 3 deg | 1312 | 1336 / 1645 | 1645 / 1336 |
| 6 deg | 1437 | 1436 / 1545 | 1545 / 1436 |
| 9 deg | 1562 | 1536 / 1445 | 1445 / 1536 |
| 12 deg | 1687 | 1636 / 1345 | 1345 / 1636 |
| 15 deg | 1812 | 1736 / 1245 | 1245 / 1736 |
| 18 deg | 1937 | 1836 / 1145 | 1145 / 1836 |

Park is servo center, not a pitch station.

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

Pitch was not logged in either spin test, which is why the analysis could only place it at the two points given afterward. Fill in Collective deg and Servo us on every capture. Servo us takes one number: a workable convention is the FWD value there and the selector position in Notes.

## 5. Sweep plan and limits

- Hold 1800 rotor RPM. Start at the 0 degree position and go up one position at a time: 0, 3, 6, 9. Capture each.
- Stop if pack amps pass 30.
- Stop if thrust stops rising while watts keep climbing. That is stall.
- A quick check by eye: thrust divided by kilowatts. The clean plateaus on 9 Nov ran 24 to 26 lbf per kW. The stalled ones were under 14.
- Where thrust crosses 7.5 lbf, note the watts. That number is the answer the stand exists to give.

Then repeat at other RPMs as the grid requires. Cruise at 1000 RPM cannot be reproduced on a static stand (see section 8).

## 6. What the two spin tests showed (9 Nov 2026)

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

- **Cause: over-current.** Both cuts came within a second of pack current reaching about 50 A, the ESC rating. The pack never went below 22.5 V, so it was not low voltage. Not yet confirmed from the ESC's own log.
- **Why the current got there: stalled blades.** The linkages had been rigged with the tip level as zero. On the figures given on 12 Nov, take two ended at about 26 degrees at the 0.75 R station. More pitch gave less thrust for more power.
- **Clean points before stall:** 6.1 lbf at 1797 RPM for 245 W (take two), and 6.7 lbf at 1627 RPM for 283 W (take one).
- **Target thrust was reached once, stalled:** 7.8 lbf at 1752 RPM for 701 W.
- **At the take two cut**, about 800 of the 1132 W was going into churned air, and the estimated current in the motor windings was about 67 A against a 44.2 A motor rating, because the ESC was at about 73% throttle.
- The power meter's hall sensor is a +-50 A part. Readings near 50 A are at the top of its range.

## 7. Hover hypothesis for the static stand

Not yet confirmed. The next sweep confirms or corrects it.

| Variable | Best guess | Range | Basis |
|---|---|---|---|
| Rotor RPM | 1800 | fixed | Austin's flight tests |
| Thrust | 7.5 lbf | target | per nacelle |
| Pitch at 0.75 R | 8 deg | 6 to 10 | blade theory, not measured. The softest number |
| Electrical power | 335 W | 310 to 370 | interpolated between the two clean points |
| Pack amps | 14 A | 13 to 17 | at 24 V |
| Motor RPM at 3:1 | 5400 | | about 75% throttle |

The swash pitch chart of 13 Nov marks the 3 and 6 degree positions as hover and 9 and up as cruise, with this 335 W point at the 6 to 9 boundary.

## 8. Open items

- **Zero check.** The root-angle disagreement in section 3. Settle it with the gauge at the 0.75 R station before the next spin.
- **ESC cause.** Read the last error tone, or the Edge data log through Castle Link, to confirm over-current against over-temperature.
- **Gearing.** Tested at 3:1. On 13 Nov the recommendation was 3.5:1, which puts the governor at about 86% throttle at 24 V. 4:1 needs about 23.3 V at full throttle to hold 1800 RPM, so it has no headroom on a sagging 6S pack. No decision is recorded.
- **The gap to 446 W.** The hypothesis is 335 W against Austin's 446 W flight figure. On the clean curve, 446 W corresponds to about 9 lbf. Candidates: the wing in the downwash, other loads in the flight watts, ground effect on the stand, thrust calibration. Not separable from present data.
- **Cruise.** Retracted: the "10 to 14 degrees" cruise pitch in the grid point guide. Cruise pitch depends on airspeed (about 33 degrees at 0.75 R at 20 m/s and 1000 RPM) and cannot be tested statically. Austin's cruise airspeed decides how much collective travel is needed.
- **Stall margin.** Unknown. The highest clean point scales to 8.2 lbf at 1800 RPM.
- **Two-nacelle package.** In `thrust-torque_deployed`, the port finder reports `STBD = -` while live.py prints `port=0  stbd=1`. Worth checking that live.py does not try to open a second tach board that is not there.
- **After the torque rebuild.** Sections 1 and 2 will need revising for the new board and port.
