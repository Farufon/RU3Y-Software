
# Castle ESC, RPM Out to Pixhawk 6XRT

## Ru3y Nacelle "Version Three"


ThunderFly TFRPM01 I²C Tachometer (Pixhawk-ready)
https://docs.thunderfly.cz/avionics/TFRPM01/

Product page/store (ThunderFly/Tindie): $75–$90 range.

JST-GH I²C cable for Pixhawk (ThunderFly sells matching lengths). 
https://www.tindie.com/stores/thunderfly/items/

The ThunderFly **TFRPM01** doesn’t care *where* the pulses come from.  It’s essentially a **universal frequency counter** that speaks I²C. In PX4 it shows up as an RPM sensor.

By default, most hobby people use it with a **probe** (IR or Hall sensor + magnet), but electrically it can just as well count **logic-level pulses** from your Castle ESC AUX (white) wire — as long as:


### Conditions to feed Castle AUX → TFRPM01

1. **Signal voltage**

   * Castle AUX “RPM Out” is a 0–5 V TTL-like pulse.
   * TFRPM01 input is **5 V tolerant** (designed for Hall sensors). Direct connect is usually fine.
   * For extra safety, put a **1 kΩ series resistor** in line.

2. **Common ground**

   * Connect Castle ESC GND ↔ TFRPM01 GND ↔ Pixhawk GND.

3. **Clean signal**

   * If noise shows up at higher RPM, add a tiny RC filter (e.g., 1 kΩ series + 1 nF cap to ground at the TFRPM01 input).


### 🛠 Wiring

* Castle **white AUX (RPM Out)** → **TFRPM01 “probe signal” pin** (through 1 kΩ resistor).
* Castle **black (GND)** → **TFRPM01 GND**.
* TFRPM01 → Pixhawk I²C port (JST-GH 4-pin: 5V, GND, SDA, SCL).


###  PX4 / QGroundControl Setup

1. In **QGC → Parameters**, set the TFRPM01 driver to enabled.

   * The driver will auto-detect the TFRPM01 at its I²C address.
2. Set **pulses per revolution**.

   * The Castle AUX toggles once per commutation. Mechanical RPM = (edges/sec × 60) ÷ pole pairs.
   * Start with **pulses per rev = motor pole pairs × 6** (since there are 6 commutations per electrical cycle).
   * Then confirm with an optical tach and tweak the parameter.
3. Reboot the Pixhawk.
4. Verify in QGC:

   * **Analyze → MAVLink Inspector** → look for `RPM`.
   * Add an RPM tile in the **Instrument Panel**.


Bottom line: **Yes, you can use the TFRPM01 as an “ESC pulse to I²C bridge.”**
It saves you from writing custom firmware or using FT232H → I²C tricks, because PX4 already has a driver for it.


Do you want me to draw you a simple **wiring diagram** (Castle ESC → TFRPM01 → Pixhawk I²C) so it’s crystal-clear?




# Configure Castle ESC AUX = RPM OUT (Castle Link Classic)

> Props off. Bench test only.

## 1) Hardware hookup (in the right order)

1. **Unplug** the ESC **AUX/white** lead from any receiver/device. Castle specifically warns to disconnect AUX before linking. ([Castle Homepage][1])
2. Plug the ESC’s **3-wire throttle lead** into the **Castle Link USB** adapter. ([Castle Homepage][1])
3. Connect the Castle Link USB adapter to your **Windows PC** (Castle Link runs on Windows).
4. **Then** power the ESC from its main battery. (Castle notes applying main power after you’ve connected the USB link.) ([Castle Homepage][1])

> If Castle Link can’t “see” the ESC, recheck this order and that AUX is unplugged.

## 2) Open Castle Link (Classic)

* Launch **Castle Link Classic** (the “legacy” UI—distinct from Castle Link 2). Castle’s own article shows both Classic and the newer “Castle Link 2,” and confirms Classic is still used with the V3 USB kit. ([Castle Homepage][2])

> If you only have Castle Link 2 installed, no problem—the setting name is the same. The path may look a bit different visually.

## 3) Read the ESC & (optional) update firmware

* Wait for the software status bar to show your ESC is connected; use **Update/Read** to pull settings.
* If a firmware update prompt appears, you can accept it now for best compatibility. (Castle Link article covers firmware updating with Classic.) ([Castle Homepage][2])

## 4) Find the AUX Wire setting

* In **Castle Link Classic**, go to the menu/tab where **AUX / Auxiliary Wire Mode** is listed (on Edge/Edge Lite, AUX modes are selectable only via Castle Link). The Edge user guide states the **AUX line is disabled until a mode is selected** with Castle Link. ([Minicars][3])

> Depending on version, you’ll see AUX items among the advanced/other menus. Castle’s docs and product pages describe the AUX as the **“user-programmable white wire.”** ([Castle Homepage][4])

## 5) Select **RPM OUT**

* Choose **RPM OUT** for **AUX Wire Mode**.
* Castle’s Edge manuals and tech tip define RPM OUT as:
  **“The ESC toggles the AUX line at every electrical commutation. Divide by magnetic pole-pairs to get mechanical RPM.”** ([LeoMotion Download][5])

*(Optional)* Leave “Idle Datalog Erase” **off** unless you want AUX toggling at idle to clear logs. (Castle calls this out as an add-on behavior in Castle Link.) ([Castle Homepage][6])

## 6) Write settings & power-cycle

* Click **Update/Write** (or **Send Settings to Controller**) to save.
* **Disconnect** main power, then remove the USB link.
* Your **white wire now outputs a TTL pulse train** proportional to commutation. (You’ll use that for your FT232H reader, flight controller capture, or an I²C tach bridge.)

## 7) Verify the output (quick sanity)

* Re-power the ESC (still no prop), run the motor slowly, and probe the white wire vs GND with a scope or your working FT232H reader. You should see pulses that increase with throttle.
* Mechanical RPM ≈ *(edges/sec × 60) / pole-pairs*. (Pole-pairs = total magnets ÷ 2.) ([LeoMotion Download][5])

---

## Notes & references

* **AUX modes & RPM OUT definition (Edge manuals & tech tip)**: AUX is user-selectable; **RPM OUT toggles every electrical commutation**. ([LeoMotion Download][5])
* **Castle Link connection order & AUX disconnect warning** (downloads page): unplug AUX → connect Castle Link → then apply main power. ([Castle Homepage][1])
* **Classic vs Castle Link 2** (what you’re looking at): Castle’s “Castle Link Explained” article shows both UIs and when each is used. ([Castle Homepage][2])
* **Product pages reaffirm AUX = programmable white wire** on Edge series. ([Castle Homepage][7])


[1]: https://home.castlecreations.com/download-castle-link?utm_source=chatgpt.com "Castle Link: Program Your ESC or BEC | Free Download"
[2]: https://home.castlecreations.com/blog/2025/6/3/castle-link-explained-versions-updates-connection?utm_source=chatgpt.com "Castle Link Explained: Versions, Updates & Data Logs"
[3]: https://www.minicars.se/internt/artiklar/internal_documents/Phoenix-Edge-User-Guide.pdf?utm_source=chatgpt.com "Phoenix Edge Users Guide"
[4]: https://www.castlecreations.com/en/phoenix-edge-100-esc-010-0100-00?utm_source=chatgpt.com "Phoenix Edge 100 AMP ESC, 8S / 33.6V with 5 AMP BEC"
[5]: https://download.leomotion.com/Regler/Castle%20Edge%20HV%20Manual.pdf?utm_source=chatgpt.com "Castle Edge HV Manual.pdf"
[6]: https://home.castlecreations.com/blog/2015/08/aux-what?utm_source=chatgpt.com "TECH TIP: AUX WHAT???"
[7]: https://www.castlecreations.com/en/phoenix-edge-50-esc-010-0102-00?utm_source=chatgpt.com "Phoenix Edge 50 AMP ESC, 8S / 33.6V with 5 AMP BEC"
