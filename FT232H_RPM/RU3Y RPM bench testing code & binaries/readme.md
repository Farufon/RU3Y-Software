
##  Pre-Run Hardware Setup

1. **Connections**

   * ESC white signal/tach (AUX) → **1 kΩ resistor** → FT232H **AD0 (D0)**
   * ESC GND → FT232H GND
   * Do **not** connect main PWM throttle line to FT232H (use only AUX/tach output).

2. **Power**

   * Motor/ESC powered by flight battery (watch props/rotor, secure heli or remove blades for bench test).
   * FT232H powered via USB to your Mac/PC.

3. **Safety**

   * Strap heli down or remove main/tail blades during first tests.
   * Wear eye protection — ESCs/motors can surge unexpectedly.

---

##  Software / Command Setup

1. Open Terminal:

   ```bash
   cd ~/Desktop/FT232H_RPM
   ```

2. Run test with **raw motor RPM only**:

   ```bash
   ./rpm_reader_static --poles 8 --ratio 1.0 --index 0 --window 0.05
   ```

   * `--poles 8` = Align 470MX motor (8 poles).
   * `--ratio 1.0` = just motor speed.
   * `--index 0` = first FT232H device.
   * `--window 0.05` = 50 ms averaging window.

3. Run with **gear ratio compensation (rotor head RPM)**:

   ```bash
   ./rpm_reader_static --poles 8 --ratio 8.0 --index 0 --window 0.05
   ```

---

##  Output Verification

Sample output:

```
# t_s, edges, edges_per_s, motor_rpm, rotor_rpm
0.050,120,2400.0,20571,2571
0.100,118,2360.0,20228,2529
```

* `edges` should scale with throttle smoothly.
* `motor_rpm` should be \~20k+ at full throttle (check motor Kv × voltage).
* `rotor_rpm` should be \~2.4–2.6k at 8:1 ratio (matches typical head speeds).

---

##  Sanity Checks

* **Idle / Low Throttle**: rotor\_rpm should rise linearly with throttle.
* **No Throttle**: output should show near zero (a few stray edges OK).
* **Full Throttle**: compare `motor_rpm ≈ Kv × Voltage` and ensure rotor\_rpm ≈ motor\_rpm ÷ ratio.

  * Example: 1800 Kv × 22.2 V ≈ 40k rpm (no load). With 8:1 gear, rotor ≈ 5k rpm max (likely lower under load).

---

 **Tip**: If you see motor RPM correct but rotor RPM looks wrong, double-check `--ratio`.
 If both look wrong, double-check `--poles`.




## LOG TO CSV

Good timing — your program already prints CSV-style lines to `stdout`. You can **tee** or **redirect** them so you get both: live on screen *and* saved to a CSV file.

---

###  Option 1: Tee to File

Keeps live output on screen *and* writes to file:

```bash
./rpm_reader_static --poles 8 --ratio 8.0 --index 0 --window 0.05 | tee rpm_log.csv
```

---

###  Option 2: Redirect to File (no live screen)

Writes only to file (silent on screen):

```bash
./rpm_reader_static --poles 8 --ratio 8.0 --index 0 --window 0.05 > rpm_log.csv
```

---

###  Option 3: Append (multiple runs into one file)

```bash
./rpm_reader_static --poles 8 --ratio 8.0 --index 0 --window 0.05 | tee -a rpm_log.csv
```

---

###  Notes

* The first line of the output (`# t_s, edges, edges_per_s, motor_rpm, rotor_rpm`) will serve as your CSV header.
* If you plan to import into Excel/Numbers, you may want to remove the `#` from the header afterward.

