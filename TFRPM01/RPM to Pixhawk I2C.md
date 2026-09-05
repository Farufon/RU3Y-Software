
# Converting Castle ESC White-Wire RPM Out to I²C Input for Pixhawk

This guide explains, in extreme detail, how to convert the **Castle Phoenix Edge ESC’s white-wire RPM OUT** signal into an **I²C input** that the **Pixhawk** can read, with two practical paths:

- **Path A (buy-and-wire):** Use a ready-made **I²C RPM counter (ThunderFly TFRPM01)**.  
- **Path B (DIY):** Build a small I²C device that emulates a **PCF8583 tachometer**, which PX4 already supports.

---

## 0. What the Castle White Wire Outputs

On **Phoenix Edge ESCs**, setting the AUX (white) wire to **RPM OUT** makes it **toggle at every electrical commutation**.  

From Castle’s guide:  
> “The ESC toggles the AUX LINE at every electrical commutation. Divide this number by your number of magnetic pole pairs for mechanical RPM.”  

This means the white wire is **not serial**. It’s a **TTL pulse train** proportional to motor eRPM. To feed Pixhawk over I²C, you need hardware that **counts pulses** and exposes them on the bus.

---

## 1. Path A — Using ThunderFly TFRPM01

**What it is:**  
- A tiny board that **counts incoming pulses** and presents them via **I²C**.  
- Directly supported in PX4 through the `pcf8583` driver.   

### Buy
- [ThunderFly TFRPM01 I²C Tachometer](https://github.com/ThunderFly-aerospace/TFRPM01?utm_source=chatgpt.com)  
  - Address selectable: **0x50** or **0x51**.

### Why it works
- Input accepts **0–5 V TTL** with a **Schmitt trigger** and pull-up—perfect for Castle AUX.    
- Powered from **Pixhawk I²C 5 V rail**, not the ESC.  

### Step-by-step wiring

**A. Configure the ESC**  
1. Use Castle Link software.  
2. Set **AUX Line Mode = RPM OUT**.  

**B. Connect Castle ESC to TFRPM01**  

ESC White (AUX pulse) → TFRPM01 “RPM IN”

ESC Black/Brown (GND) → TFRPM01 GND

ESC Red (+5V)         → leave unconnected

- Optional: add **1 kΩ resistor** inline with signal.

**C. Connect TFRPM01 to Pixhawk**  
- Plug TFRPM01 into **Pixhawk I²C port** with JST-GH cable.  
- Default address = `0x50`. Move jumper **JP1** for `0x51`.  

---

## 2. PX4 Firmware Setup

PX4 supports this device using the **`pcf8583` driver**.

### Start the driver
In **QGroundControl → MAVLink Console**:
```bash
pcf8583 start -X -a 80

	•	-X = external I²C bus
	•	-a 80 = 0x50 address (decimal). Use -a 81 for 0x51.

Check status

pcf8583 status

If driver is missing
	•	Enable drivers/rpm/pcf8583 in board config and rebuild PX4.

⸻

3. Pulses-per-Revolution Setup

TFRPM01 counts edges, PX4 converts pulses to RPM using pulses-per-rev (param: PCF8583_MAGNET).

For Castle AUX RPM OUT:
	•	Toggles at every commutation.
	•	Approx formula:
[
\text{pulses per rev} \approx 3 \times \text{pole pairs}
]
	•	Example: 14-pole motor → 7 pole pairs → 21 pulses/rev.

Set:

PCF8583_MAGNET = 21

Sanity check
	•	If RPM is 2× too high → double/halve value.
	•	If 6× off → adjust by ×/÷6.
	•	Confirm once with optical tach and lock value.

⸻

4. Validation
	•	Arm Pixhawk (no blades).
	•	Watch RPM in QGC → Widgets → Analyze.
	•	PX4 logs RPM in uLog files (visible in Flight Review).

⸻

5. Safety Notes
	•	Common ground required: ESC GND ↔ TFRPM01 GND ↔ Pixhawk GND.
	•	Do not connect ESC’s +5 V to Pixhawk.
	•	Use short wires.
	•	Optional: add optocoupler for extra isolation if noise issues.

⸻

6. Path B — DIY I²C Converter

If you prefer to build:

Hardware
	•	MCU with I²C slave (ATmega, STM32, RP2040).
	•	Input pin with Schmitt trigger or resistor divider.
	•	Powered from Pixhawk I²C 5 V.

Firmware outline
	1.	Count rising edges of Castle AUX.
	2.	Expose count via I²C registers that mimic PCF8583 event-counter.
	3.	Default I²C address = 0x50.

PX4
	•	Use the same pcf8583 driver.
	•	Set PCF8583_MAGNET pulses-per-rev as above.

⸻

7. ArduPilot Alternative

If you run ArduPilot on Pixhawk, you don’t need I²C at all.
	•	Connect AUX pulse directly to a Pixhawk AUX pin.
	•	Configure:

RPM_TYPE = 1
RPM_PIN  = <AUX pin>


	•	ArduPilot handles scaling internally.

For bused solutions, use AP_Periph → DroneCAN RPM node.

⸻

8. Example Setup

Motor: 14 poles (7 pole pairs)
Gear ratio: 10:1
	•	Start driver:

pcf8583 start -X -a 80


	•	Set:

PCF8583_MAGNET = 21


	•	PX4 reports motor RPM.
	•	Rotor RPM = motor RPM ÷ 10.

⸻

9. Troubleshooting
	•	No RPM: AUX not set to RPM OUT, or driver not running.
	•	No driver: enable pcf8583 and rebuild.
	•	Noisy values: shorten wires, add series resistor, or optocoupler.
	•	Wrong value: adjust PCF8583_MAGNET.

⸻

References
	•	Castle ESC AUX RPM definition
	•	ThunderFly TFRPM01 hardware and PX4 integration
	•	PX4 pcf8583 driver docs
	•	PX4 parameters including PCF8583_MAGNET
	•	ArduPilot RPM sensor docs
	•	DroneCAN RPM option

⸻

Summary
	•	Fastest path: Castle AUX → TFRPM01 → Pixhawk I²C → PX4 pcf8583.
	•	DIY path: emulate pcf8583 in your own MCU I²C slave.
	•	ArduPilot path: skip I²C, wire to AUX pin directly.

Once configured, Pixhawk logs true RPM in real time, derived from the Castle white-wire output.

