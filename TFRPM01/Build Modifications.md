
## 1. Rebuild workflow now that everything is set up

Your environment (as we’ve “frozen” it):

* Repo: `/Users/redfour/Austin_PX4/PX4-Autopilot`
* Toolchain: `/Applications/ArmGNUToolchain/13.3.rel1/…`
* Host tools (like `gencromfs`) are now correctly built for x86_64 inside `platforms/nuttx/NuttX/nuttx/tools` and used by the build.

### A. For small / normal code changes

Use this for:

* Editing existing modules/drivers
* Updating message definitions, parameters, etc., **without** changing the board config name.

**Steps:**

1. **Go to the repo root**

   ```bash
   cd /Users/redfour/Austin_PX4/PX4-Autopilot
   ```

2. **Pull or drop in new code**

   * `git pull` from your boss’s branch, or
   * copy modified files into `src/…`, `boards/…`, etc.

3. **Incremental rebuild**

   ```bash
   make px4_fmu-v6xrt_default -j8
   ```

   * Use `-j8` (8-core Xeon) or bump to `-j12` if you want it more aggressive.
   * You’re looking for the same style finish you just saw:

     * `Built target px4`
     * `Built target px4_package`
     * And the memory summary.

4. **Resulting firmware files**

   After a successful build, you care about:

   ```text
   build/px4_fmu-v6xrt_default/px4_fmu-v6xrt_default.px4  ← for QGroundControl / make upload
   build/px4_fmu-v6xrt_default/px4_fmu-v6xrt_default.bin  ← raw binary (J-Link etc.)
   ```

   You do **not** need to touch `gencromfs` anymore unless you blow away the NuttX tools directory.

---

### B. When you change low-level stuff heavily

Use this if:

* You change board config files in `boards/px4/fmu-v6xrt/…`
* You change ROMFS content, startup scripts, etc. heavily
* The build starts acting weird / can’t reconfigure.

**Steps:**

1. From repo root:

   ```bash
   cd /Users/redfour/Austin_PX4/PX4-Autopilot
   ```

2. **Delete only the build for this config** (keep NuttX tools!):

   ```bash
   rm -rf build/px4_fmu-v6xrt_default
   ```

3. **Rebuild from scratch**:

   ```bash
   make px4_fmu-v6xrt_default -j8
   ```

4. Again, firmware appears at:

   ```text
   build/px4_fmu-v6xrt_default/px4_fmu-v6xrt_default.px4
   ```

That’s your loop: modify → `make px4_fmu-v6xrt_default` → flash.

---

## 2. Flashing the Pixhawk 6XRT with this firmware (driver included)

Your driver is now compiled into the firmware image. Flashing = deploying that image to the 6XRT.

You’ve got two clean options:

---

### Option A: Flash via QGroundControl (recommended, cleanest)

1. **Connect the 6XRT via USB** to your Mac.

2. **Put it into bootloader mode**
   Do whatever Holybro / Pixhawk 6XRT docs say; usually:

   * Hold the boot / safety button while plugging in USB, or
   * Press reset in a specific pattern.
     (Once you’ve done it once, it becomes muscle memory.)

3. **Open QGroundControl** on macOS.

4. Go to the **Firmware** / **Vehicle Setup → Firmware** section.

   * There’s an **“Advanced”** or **“Custom firmware file”** option.

5. **Select your built `.px4` file:**

   * Navigate to:

     ```text
     /Users/redfour/Austin_PX4/PX4-Autopilot/build/px4_fmu-v6xrt_default/px4_fmu-v6xrt_default.px4
     ```

6. **Confirm and flash**

   * QGC will erase, upload, verify, and reboot the board.

Once it reboots, it’s running the new firmware with your I²C RPM driver baked in.

---

### Option B: Flash from the PX4 build system (`make upload`)

This uses PX4’s own uploader script.

1. **Connect 6XRT over USB** and put into bootloader as above.

2. From repo root:

   ```bash
   cd /Users/redfour/Austin_PX4/PX4-Autopilot
   make px4_fmu-v6xrt_default upload
   ```

3. The PX4 uploader will:

   * Find the board’s USB serial
   * Push the corresponding firmware (`px4_fmu-v6xrt_default.px4`)
   * Reboot the board.

If it ever complains about not finding the port, unplug/replug, ensure only one PX4 is connected, and rerun the same command.

---

## 3. After flashing: wiring & parameter sanity

Once the firmware with your driver is on the board:

1. **Wire the RPM sensor / Thunderfly board** to the correct I²C port you designed for.
2. In QGroundControl → Parameters:

   * Search for `RPM` and `I2C` / the driver name.
   * Enable the RPM driver, set the correct I²C bus, pulses-per-rev, etc.
3. Reboot the FC once after parameter changes to make sure the driver starts clean.

From then on, your workflow for changes is:

1. Edit / pull new code.
2. `cd /Users/redfour/Austin_PX4/PX4-Autopilot`
3. `make px4_fmu-v6xrt_default -j8`
4. Flash via QGC custom firmware or `make px4_fmu-v6xrt_default upload`.

That’s the whole loop.





# SETTING UP THE PCF8583 DRIVER FOR PX4 BUILD


## 0. Do you flash now or edit code first?

**Recommendation:**
Flash the firmware you just built **now** and prove:

1. Pixhawk 6XRT accepts your `.px4` file.
2. QGC can talk to it.
3. The `pcf8583` RPM driver is either:

   * already present and starts, or
   * clearly missing (so we know *exactly* what to edit next).

Once we know if `pcf8583` is there, *then* we edit the board config if needed.
You can always go back and flash your boss’s firmware afterwards; flashing is reversible.

So: **yes, upload this build first.**

---

## 1. Hardware setup (Castle ESC → ThunderFly → Pixhawk)

Do this once; then we can focus on firmware/driver.

### 1.1 Configure Castle ESC

1. Connect ESC to **Castle Link** on your PC.
2. In Castle Link:

   * Find **AUX Line Mode**.
   * Set **AUX Line Mode = RPM OUT**.
3. Save settings to the ESC.

This makes the **white wire** output a pulse train proportional to motor e-RPM.

### 1.2 Wire ESC → TFRPM01

On the ESC side:

* **White** = AUX / RPM OUT
* **Black/Brown** = GND
* **Red** (BEC +5 V) = *leave unconnected to Pixhawk/TFRPM01 5 V* (we only want one 5 V domain).

Connections:

* ESC **White** → TFRPM01 pin **“RPM IN”**
* ESC **Black/Brown (GND)** → TFRPM01 **GND**

Optional (noise protection, nice but not mandatory at first):

* Add a **1 kΩ series resistor** between ESC white and RPM IN.

### 1.3 Wire TFRPM01 → Pixhawk I²C

Use a JST-GH I²C cable from Pixhawk 6XRT:

Pixhawk I²C port (4-pin) → TFRPM01:

* **SCL** → SCL
* **SDA** → SDA
* **5V** → VCC / +5
* **GND** → GND

Important:
All grounds are common now: ESC GND ↔ TFRPM01 GND ↔ Pixhawk GND.

By default the TFRPM01 is at I²C address **0x50**. (Jumper moves it to 0x51 if needed.)

---

## 2. Flash the firmware you just built

You already built:

```text
/Users/redfour/Austin_PX4/PX4-Autopilot/build/px4_fmu-v6xrt_default/px4_fmu-v6xrt_default.px4
```

### Option A – Flash from PX4 build system

1. Connect Pixhawk 6XRT to your Mac via USB.

2. Put it in **bootloader mode** (whatever your 6XRT requires: boot button + power/reset).

3. From the repo root:

   ```bash
   cd /Users/redfour/Austin_PX4/PX4-Autopilot
   make px4_fmu-v6xrt_default upload
   ```

4. Wait for it to say upload complete and the board reboots.

### Option B – Flash from QGroundControl (if you prefer GUI)

1. Connect Pixhawk via USB and enter bootloader mode.

2. Open **QGroundControl**.

3. Go to **Vehicle Setup → Firmware**.

4. Choose **“Custom firmware file”**.

5. Select the file:

   ```text
   /Users/redfour/Austin_PX4/PX4-Autopilot/build/px4_fmu-v6xrt_default/px4_fmu-v6xrt_default.px4
   ```

6. Let QGC erase, flash, verify, and reboot.

Once it boots, you’re now running **your** 6XRT build.

---

## 3. Check if the `pcf8583` driver exists

Now we test: is your current firmware already built with the PCF8583 driver?

1. In QGroundControl, connect to the Pixhawk.

2. Go to **Widgets → MAVLink Console** (or “Analyze Tools → MAVLink Console” depending on your QGC version).

3. In the console, type:

   ```text
   pcf8583 start -X -a 80
   ```

   * `-X` = external I²C bus (Pixhawk’s I²C port).
   * `-a 80` = decimal 80 = 0x50 (TFRPM01 default).

4. Watch the response:

   * If you see something like:
     `pcf8583: started`
     → Great. Driver is present and running.

   * If you get:
     `command not found` or `unknown command "pcf8583"`
     → The driver isn’t compiled into this firmware.
     **That’s when we go edit the board config and rebuild.**

5. Check status:

   ```text
   pcf8583 status
   ```

   * If present, it should show device, address, and some internal info.
   * If absent, again, that confirms we need to add the driver to the build.

For now, we just needed to know that. (If it’s missing, next step is: I’ll walk you through exactly which file to edit and what line to add.)

---

## 4. Set pulses-per-rev parameter (PCF8583_MAGNET)

Assuming the driver **did** start:

1. In QGC, go to **Parameters**.

2. Search for:

   ```text
   PCF8583_MAGNET
   ```

3. Compute pulses per mechanical revolution:

   Castle RPM OUT toggles on each *electrical commutation*. Approx rule:

   [
   \text{pulses per rev} \approx 3 \times \text{pole pairs}
   ]

   Example:

   * 14-pole motor → 7 pole pairs
   * Pulses per rev ≈ (3 \times 7 = 21)

4. Set:

   ```text
   PCF8583_MAGNET = <your value, e.g. 21>
   ```

5. Write parameters and **reboot** the Pixhawk once so the driver restarts clean.

---

## 5. See RPM in QGroundControl

With everything wired + driver running:

1. Ensure:

   * Pixhawk powered
   * ESC powered
   * Motor installed **without blades** (just motor on bench for now).

2. Arm via QGC (or bench-test method) and gently bring up throttle so the motor spins.

3. In QGC:

   * Open **Analyze → MAVLink Inspector** (or the “Analyze” widget).
   * Look for a message/field called **`rpm`** (PX4 `rpm` uORB topic mapped into MAVLink).
   * Alternatively, in MAVLink Console:

     ```text
     listener rpm
     ```

     This should print the RPM topic periodically with a current RPM value.

4. Sanity check:

   * If RPM ≈ expected (within a factor of 2–3), adjust only **PCF8583_MAGNET**.
   * If RPM is **exactly** 2× or 0.5× what you expect → halve or double `PCF8583_MAGNET`.
   * If it’s ~6× off, adjust by ×6/÷6.

Once that works, you have the **full physical chain** proven:
Castle → TFRPM01 → I²C → Pixhawk → PX4 driver → QGC.

---

## 6. When to bring in your boss’s firmware and code edits

After the above:

* If `pcf8583` **was available and works**:

  * Great. We only need minor tweaks (parameters, possibly logging or control use).
  * You can now:

    * Either keep using your firmware, or
    * Flash your boss’s `.px4` and repeat the `pcf8583 start` test to see if his build also includes it.

* If `pcf8583` **was missing**:

  * Next move is to:

    * Edit the 6XRT board config to include `drivers/rpm/pcf8583`.
    * Rebuild with `make px4_fmu-v6xrt_default`.
    * Re-flash and repeat the steps above.
  * Once that’s stable, you can port those config changes into your boss’s repo/branch so his firmware also includes the RPM path.

