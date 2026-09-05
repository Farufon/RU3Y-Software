


# RU3Y PRM Option B (No extra board): Feed Castle AUX (white) → Pixhawk capture pin

PX4 can read a raw pulse train as RPM using a **timer capture** input. On the Pixhawk 6X/6X-RT family the **FMU\_CAP1** pin is exposed on the **AD\&IO** port.

## Wire

* **Signal**: Castle **white AUX** → **FMU\_CAP1** (AD\&IO port **pin 2**, label `PI0`).
* **Ground**: Castle GND → Pixhawk GND.
* **Level**: FMU pins are **3.3 V logic**; if the Castle AUX is 5 V, add a **divider** (e.g., 20 kΩ top / 10 kΩ bottom) or a small logic-level shifter/opto. Keep leads short. ([PX4 Docs][9])

> Where is FMU\_CAP1 on Pixhawk 6X/6X-RT?
> In the PX4 board docs: **AD\&IO port, pin 2 = FMU\_CAP1 (PI0)**. ([PX4 Docs][9])

## PX4 / QGroundControl setup

1. In **QGC → Parameters**, enable the **Tachometer / RPM** (capture) driver for your board (PX4 “Tachometers” docs). Exact parameter names vary slightly by release; after enabling, a small set of RPM parameters appears (source/capture pin, pulses-per-rev, filter). ([PX4 Docs][8])
2. Set **source** to the **capture input** (FMU\_CAP1).
3. Set **pulses per rev** for Castle AUX (start with **6 × pole-pairs**, then refine using an optical tach).
4. **Reboot** the FC.
5. **Verify**:

   * QGC **MAVLink Inspector** → watch **RPM** update. ([QGroundControl Documentation][6])
   * Add **Instrument Panel** tile for RPM. ([QGroundControl Documentation][7])

**Notes & tips**

* The Castle AUX line “toggles at every electrical commutation”. Mechanical RPM = (commutation edges per second) ÷ (pole-pairs) × (60 s/min). Depending on whether you count toggles, rising edges only, etc., you may be off by a factor (2 or 6). That’s why setting “pulses per rev” and checking with an optical tach once is smart. (This behavior is widely cited by Castle users.) ([PX4 Forum][10])
* Keep the wiring short; add a **1 kΩ series** resistor and small **1 nF** cap to ground at the Pixhawk side if the signal is noisy.

---

# Which should you choose?

* **Need it working quickly & robustly inside QGC?** → **Option A (TFRPM01)**. It’s supported, documented, and designed for PX4. ([PX4 Docs][5])
* **Want the lightest BOM (no extra board)?** → **Option B (FMU\_CAP1)**. Clean, but you must get the level shifting right and set the pulses-per-rev correctly.

---

## FAQ

**Can I still use the FT232H for I²C later?**
Yes—FT232H is great as a **PC-side I²C/SPI/GPIO *master*** for bench tools and scripts. It just **can’t act as an I²C slave** that Pixhawk can poll. If later you want a PC to inject telemetry into PX4, use MAVLink over a serial/UDP link, or a microcontroller that emulates a supported I²C sensor as a **slave**. ([Adafruit Forums][1])

**Where do I see RPM in QGroundControl?**
Use **Analyze → MAVLink Inspector** to confirm the **RPM** stream is present, then add it to the **Instrument Panel** via the edit (pencil) tool. ([QGroundControl Documentation][6])

**Is Pixhawk 6X/6X-RT confirmed to have a capture pin for this?**
Yes. The docs call out **FMU\_CAP1** on the **AD\&IO** port (pin 2). ([PX4 Docs][9])

---

## Handy links (for reference)

* **FT232H is I²C Master (not slave)**: Adafruit/FTDI references and forum notes; FTDI AN\_255. ([Adafruit Forums][1])
* **PX4 Tachometers overview** (what’s supported/behavior): ([PX4 Docs][8])
* **ThunderFly TFRPM01 docs & purchase** (PX4 driver, how to wire): ([PX4 Docs][5])
* **Pixhawk 6X/6X-RT board pages** (FMU\_CAP1 on AD\&IO): ([PX4 Docs][9])
* **QGC – MAVLink Inspector & Instrument Panel** (how to see/add RPM): ([QGroundControl Documentation][6])

---

If you want, I can tailor a one-page “build card” for either Option A (TFRPM01) or Option B (FMU\_CAP1) with the exact connector pinouts for your specific Pixhawk 6X-RT baseboard and a BOM (cables, resistors, shifter).

[1]: https://forums.adafruit.com/viewtopic.php?t=77969&utm_source=chatgpt.com "ft232h breakout as an i2c-slave"
[2]: https://www.tindie.com/products/thunderfly/tfrpm01-drone-rpm-tachometer-sensor/?utm_source=chatgpt.com "TFRPM01: Drone RPM tachometer sensor"
[3]: https://docs.thunderfly.cz/avionics/TFRPM01/probe?utm_source=chatgpt.com "Probe options"
[4]: https://www.tindie.com/stores/thunderfly/items/?utm_source=chatgpt.com "ThunderFly on Tindie"
[5]: https://docs.px4.io/main/en/sensor/thunderfly_tachometer?utm_source=chatgpt.com "ThunderFly TFRPM01 Revolution Counter - PX4 docs"
[6]: https://docs.qgroundcontrol.com/Stable_V4.3/en/qgc-user-guide/analyze_view/mavlink_inspector.html?utm_source=chatgpt.com "MAVLink Inspector | QGC Guide (4.3)"
[7]: https://docs.qgroundcontrol.com/master/en/qgc-user-guide/fly_view/instrument_panel.html?utm_source=chatgpt.com "Instrument Panel | QGC Guide (master)"
[8]: https://docs.px4.io/main/en/sensor/tachometers.html?utm_source=chatgpt.com "Tachometers (Revolution Counters) | PX4 Guide (main)"
[9]: https://docs.px4.io/main/en/flight_controller/pixhawk6x "Holybro Pixhawk 6X | PX4 Guide (main)"
[10]: https://discuss.px4.io/t/rpm-reading-for-esc-castle-edge/8394?utm_source=chatgpt.com "RPM reading for ESC Castle Edge - PX4 Discussion Forum"
