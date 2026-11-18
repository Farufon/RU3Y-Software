stbd_swash_selector_7pos.txt has the seven starboard positions from your sheet, with the channel 4 slider split into eight bands:

| Set channel 4 to | Position | FWD | AFT |
|---|---|---|---|
| 1000 | Park (startup) | 1500 | 1500 |
| 1187 | 0° neutral | 1236 | 1745 |
| 1312 | 3° | 1336 | 1645 |
| 1437 | 6° | 1436 | 1545 |
| 1562 | 9° | 1536 | 1445 |
| 1687 | 12° | 1636 | 1345 |
| 1812 | 15° | 1736 | 1245 |
| 1937 | 18° | 1836 | 1145 |

Setup and use are the same as the four-position version. Each change still ramps both servos together over 3 s.

Things I decided or noticed that you should check:

1. **I added an eighth band, Park, at the bottom of the slider.** Startup 1500/1500 isn't one of your seven positions, so without it the script would have no way to hold or return to the startup values. With channel 4 starting at 1000, running the script moves nothing until you move the slider.
2. **The bands are narrow now (125 µs each).** Typing the value into the channel 4 box is more reliable than dragging. Dragging slowly through several bands will step through each one.
3. **The "46° root angle" label on the startup column doesn't fit the rest of the sheet.** Your new numbers run 100 µs per 3°, which puts 1500/1500 at roughly 8° of pitch (about 66° root), between your 6° and 9° columns. So going from Park to 0° neutral drives pitch down by about 8°, not up. If the 46° label is left over from the old interpretation, nothing needs changing in the script; if 1500/1500 really is meant to be a low-pitch safe position, the startup values need revisiting.
4. **This is starboard only.** Port is the mirror (FWD 1745 down to 1145, AFT 1236 up to 1836). Tell me which channels port FWD and AFT are on and I'll make that file.

To trim a position later, edit its two numbers in the `go` section; they are microseconds times 4.