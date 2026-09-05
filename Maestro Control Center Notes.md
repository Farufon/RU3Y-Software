# Maestro App Channel Settngs for Castle ESCs

### The fundamental difference:

* **Servos** are expecting:

  * 50 Hz (20 ms period)
  * Pulse width 1000 µs to 2000 µs (typical)
  * Some servos tolerate wider (500–2500 µs)

* **ESCs** (especially RC airplane ESCs like Castle) are also expecting:

  * 50 Hz (almost always — some are okay with 400 Hz but **Castle Lite 50 wants 50 Hz** by default)
  * Pulse width usually 1000–2000 µs (sometimes wider, but 1000–2000 µs is always safe for Castle)

---

### Your challenge:

The Maestro defaults to 50 Hz for all channels when in "servo" mode — **this is exactly what Castle wants**.
You do **not** need to change the "Mode" from *Servo* to *Output PWM* or *Input*.

---

## Maestro Settings for Driving Castle ESC:

### In **Channel Settings Tab** (Control Center):

| Setting               | Value                 | Notes                                                  |
| --------------------- | --------------------- | ------------------------------------------------------ |
| Mode                  | Servo                 | Keep as Servo                                          |
| Name                  | (optional)            | Name it "ESC Throttle"                                 |
| Rate                  | 50 Hz                 | Default (matches Castle)                               |
| Min                   | 992                   | Matches 1000 µs                                        |
| Max                   | 2000                  | Matches 2000 µs                                        |
| On startup            | (safe value, eg. 992) | Ensures low throttle on power-up                       |
| Error                 | (safe value, eg. 992) | Ensures ESC doesn’t receive full throttle during error |
| Speed                 | 0                     | No speed limit (direct output)                         |
| Accel                 | 0                     | No acceleration ramp                                   |
| 8-bit Neutral / Range | ignore for now        | Not used for Castle ESC                                |

---

> The important point:
> **Castle just needs to see a valid PWM signal between 1000–2000 µs at 50 Hz.**
> Your Maestro already outputs that when set to "Servo" mode.

---

### The problem most people run into:

* They change **Mode** to *PWM Output* thinking that’s for ESCs — that’s for driving non-servo PWM devices with duty cycle, which confuses Castle ESCs.
* Or they change **Rate** to higher than 50 Hz, which many Castle ESCs don't accept.
* Or they send On Startup value too high, accidentally arming at full throttle.

---

## Clean starting configuration:

| Parameter | Value |
| --------- | ----- |
| Mode      | Servo |
| Rate      | 50 Hz |
| Min       | 992   |
| Max       | 2000  |
| Startup   | 992   |

This maps Maestro’s control range of:

* **Target = 4000 → 992 µs (\~1000 µs = ESC off)**
* **Target = 8000 → 2000 µs (ESC full throttle)**

---

### Quick Test:

Power your Maestro (USB + logic power OK)

Connect ESC signal wire (white) to Maestro signal pin (channel you set above).

Ground between ESC battery negative and Maestro logic ground must be connected.

Motor connected to ESC.

Power up Maestro first, then ESC second.

In Control Center, use the slider for that channel:

Move slider up from 4000 → 8000 (this will map to 1000–2000 µs)

Watch Castle ESC initialize

If you hear Castle initialization tones: **you are in business.**


## **Channel Settings Tab (this is your ESC configuration zone):**

These are your *servo channel definitions* — they define the PWM range that the Maestro is allowed to output when you send commands via slider, script, serial, etc.

| Column                    | Value                           | Purpose                                |
| ------------------------- | ------------------------------- | -------------------------------------- |
| **Name**                  | (optional, e.g. "ESC Throttle") | For your own sanity                    |
| **Mode**                  | Servo                           | Always Servo for Castle ESC            |
| **Rate**                  | 50 Hz                           | Castle wants 50 Hz                     |
| **Min**                   | 992                             | Lower pulse limit = 992 µs (\~1000 µs) |
| **Max**                   | 2000                            | Upper pulse limit = 2000 µs            |
| **On startup**            | 992                             | Safe minimum on startup                |
| **Error**                 | 992                             | Safety setting during errors           |
| **Speed**                 | 0                               | No software speed limiting             |
| **Accel**                 | 0                               | No acceleration limiting               |
| **8-bit neutral / range** | leave as default                | (Not relevant for ESC use)             |

This defines your safe PWM operating range.

---

## **Status Tab (this is your live test slider):**

This is where you control the channel manually.

* The **slider itself** moves between:

  * **Min physical limit** (default 3968 = \~992 µs)
  * **Max physical limit** (default 8000 = 2000 µs)

* You **do not** need to change fields in the Status tab itself.
  The slider range automatically respects the Min/Max you set in Channel Settings.

When you move the slider between 4000 and 8000, you're sending PWM between 1000 and 2000 µs.

If you set Min = 992 and Max = 2000 in Channel Settings, your Status tab slider will automatically show 4000 to 8000 as its physical boundaries.

You don't manually set “center position” or "fields" in the Status tab for this application.

---

## **Default center position (1500 µs):**

* That’s simply a convenience for normal servos.
* For ESCs: you simply ignore "center."
* All you care about is:

  | Target | µs      | Effect                                                                     |
  | ------ | ------- | -------------------------------------------------------------------------- |
  | 4000   | 1000 µs | ESC motor off                                                              |
  | 8000   | 2000 µs | ESC full throttle                                                          |
  | 6000   | 1500 µs | Mid-throttle (only meaningful if ESC supports reverse or partial throttle) |

---

## **You never directly set 4000/8000 in any field.**

* You only set 992 and 2000 in Channel Settings → Min/Max
* Maestro internally converts that into the slider’s quarter-microsecond units.
* You use the slider to command throttle.

---

# TLDR Cheat Sheet:

| Where?               | You Enter | Units | Why?                         |
| -------------------- | --------- | ----- | ---------------------------- |
| Channel Settings Min | 992       | µs    | Safe minimum throttle        |
| Channel Settings Max | 2000      | µs    | Max throttle                 |
| Status Tab Slider    | 4000-8000 | ¼ µs  | Live manual throttle control |

---

**If you set 992 and 2000 in Channel Settings → your slider will automatically have the correct boundaries.**

 **The Status Tab is just your real-time way to "move the throttle stick."**

**You never manually type 4000 or 8000 anywhere.**

---

##  Once this is configured:

* You can safely use the Maestro as a Castle ESC throttle controller.
* You can also safely run throttle calibration using the Maestro (we can walk through that too if you want).

---

If you're ready, I can now generate for you:

* The **complete wiring diagram**
* The **exact calibration procedure for Castle ESC using Maestro**
* The **“safe test checklist” so you never burn anything up**


