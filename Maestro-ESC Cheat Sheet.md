
# **Pololu Maestro + Castle ESC: Comprehensive Cheat Sheet**

---

**Wiring Diagram**

```plaintext
[Motor Battery] + ----> Castle ESC + 
[Motor Battery] – ----> Castle ESC –
                          |
[Castle ESC] Signal cable:
    White wire (Signal) ----> Maestro Servo Channel Signal Pin (e.g., Channel 0)
    Black wire (Ground) ----> Maestro Servo Channel Ground Pin

[Castle ESC] Red wire (BEC) DISCONNECTED (or safely pulled out of the plug if you are using separate receiver battery)

[Maestro] USB ----> PC (for programming and Control Center access)

Important:
- Castle ESC needs motor connected for initialization (it uses motor as a beeper).
- Maestro needs USB or external 5V logic power.
- Ground between Castle ESC and Maestro must be shared (common ground).
```

---

## 🛠️ **Maestro Control Center Configuration**

### 1️⃣ **Channel Settings Tab**

| Field          | Value           | Notes                        |
| -------------- | --------------- | ---------------------------- |
| Name           | "ESC Throttle"  | (optional)                   |
| Mode           | Servo           | **(Always Servo)**           |
| Rate           | 50 Hz           | Matches Castle expectations  |
| Min            | 992             | \~1000 µs, safe throttle-off |
| Max            | 2000            | \~2000 µs, full throttle     |
| **On startup** | 992             | PWM safe minimum on boot     |
| **Error**      | 992             | PWM safe minimum if error    |
| Speed          | 0               | No speed limit               |
| Acceleration   | 0               | No acceleration limit        |
| 8-bit Neutral  | (leave default) | Not needed                   |
| 8-bit Range    | (leave default) | Not needed                   |

---

### **Status Tab**

| Field        | Meaning                                                          |
| ------------ | ---------------------------------------------------------------- |
| Mode         | Servo                                                            |
| Target       | Shows current signal in **quarter-microseconds** (0.25 µs units) |
| Slider       | Move to control throttle output live                             |
| Speed        | 0 (no effect unless configured)                                  |
| Acceleration | 0 (no effect unless configured)                                  |

* **Target values:**

  * **4000** → 1000 µs → ESC throttle off
  * **8000** → 2000 µs → ESC full throttle
  * Intermediate Target = proportional throttle

 **You never manually type 4000 or 8000 — they are the live values as you move the slider.**

 **The slider automatically spans from Min to Max you set in Channel Settings.**

---

## **Castle ESC Safe Power-Up & Calibration**

###  **First Boot Setup**

1. **Connect motor** to Castle ESC.
2. **Power up Maestro** via USB (outputs 992 µs immediately — Target ≈ 4000).
3. **Connect motor battery** → Power Castle ESC second.
4. Castle ESC will beep tones to signal armed state (valid PWM received).
5. Slowly **move the Maestro slider** from low to high to test throttle.

---

### **Castle ESC Throttle Calibration (if needed)**

1. **Unplug motor battery** (ESC off).
2. **Set Maestro slider to full throttle** (Target ≈ 8000).
3. **Power up Maestro**.
4. **Connect motor battery** (ESC sees full throttle).
5. **Wait for Castle calibration tones** (usually a series of beeps).
6. **Move slider to full throttle-off** (Target ≈ 4000).
7. Wait for confirmation tones.
8. Power cycle ESC to save calibration.

 Now the Castle will accept 1000 µs = throttle off, 2000 µs = full throttle exactly as per your Maestro setup.

---

##  **Critical Safety Notes**

⚡ **Always power Maestro first** to ensure ESC sees valid zero-throttle PWM on boot.

⚡ **Always use On startup = 992** to ensure ESC boots safely.

⚡ **Do not exceed Min/Max** values (992–2000 µs) to avoid overdriving ESC.

⚡ **Never connect or disconnect motor when powered.**

⚡ **Ensure motor is secured** during first power-up — motor may spin.

---

#  **Summary Flow**

```plaintext
[Maestro Control Center]
→ Set Channel Settings:
   Mode: Servo
   Rate: 50 Hz
   Min: 992
   Max: 2000
   On startup: 992
   Error: 992
   Speed: 0
   Acceleration: 0
→ Save Settings

[Status Tab]
→ Move slider = live throttle control (Target ≈ 4000-8000)

[Hardware Flow]
→ Power up Maestro (USB first)
→ Motor connected
→ Power up Castle ESC (motor battery second)
→ ESC arms safely (beeps)
→ Use slider to control throttle.
```
