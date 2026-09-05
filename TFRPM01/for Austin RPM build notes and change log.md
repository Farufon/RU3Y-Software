### 1. Find the drivers list in `default.px4board`

In your editor:

1. Use **Find** (⌘F) and search for:

   * `drivers/`
     or just
   * `"drivers"`

You’re looking for a **list of driver paths** near the bottom of the file. It will look like **one** of these general patterns:

#### Pattern A – JSON-style list

Something like:

```json
"drivers": [
    "drivers/barometer/ms5611",
    "drivers/pwm_out",
    "drivers/tone_alarm",
    ...
]
```

#### Pattern B – CMake-style list (inside a `config`/`cmake` block)

Something like:

```cmake
"config": {
    "nuttx-config": "nuttx_px4_fmu-v6xrt_default",
    "cmake-args": {
        "DRIVERS": [
            "drivers/barometer/ms5611",
            "drivers/pwm_out",
            "drivers/tone_alarm",
            ...
        ],
        "MODULES": [
            ...
        ]
    }
}
```

Or similarly named keys; the key point is there’s a list of `"drivers/..."`.

### 2. Add the PCF8583 RPM driver entry

Once you’ve found that **drivers list**, add this line into it:

```text
"drivers/rpm/pcf8583",
```

Specifically:

* Put it on its own line.
* Put a comma **after** it, except if it’s the very last entry in the list (follow whatever the surrounding lines are doing).
* Place it near other similar drivers (order doesn’t matter for correctness, it’s just for tidiness).

Example for Pattern A:

```json
"drivers": [
    "drivers/barometer/ms5611",
    "drivers/pwm_out",
    "drivers/tone_alarm",
    "drivers/rpm/pcf8583"
]
```

Example inside Pattern B:

```cmake
"cmake-args": {
    "DRIVERS": [
        "drivers/barometer/ms5611",
        "drivers/pwm_out",
        "drivers/rpm/pcf8583",
        "drivers/tone_alarm"
    ],
    "MODULES": [
        ...
    ]
}
```

**Do not** change anything else in the file.

Then **save** the file.

---

### 3. Rebuild with the updated board config

Back in Terminal:

```bash
cd /Users/redfour/Austin_PX4/PX4-Autopilot
make px4_fmu-v6xrt_default
```

Let it go all the way to `Built target px4_package` again.

If it errors, stop and paste the *first* error line to me; that will mean we only need to fix a tiny syntax issue (like a missing comma).

---

### 4. Re-flash this new firmware

You now have a new `.px4` that **should** include `pcf8583`.

From the repo root:

```bash
cd /Users/redfour/Austin_PX4/PX4-Autopilot
make px4_fmu-v6xrt_default upload
```

Or via QGroundControl:

* Vehicle Setup → **Firmware**
* Select **Custom firmware file**
* Pick:
  `/Users/redfour/Austin_PX4/PX4-Autopilot/build/px4_fmu-v6xrt_default/px4_fmu-v6xrt_default.px4`

Let it flash and reboot.

---

### 5. Confirm the driver exists on the board

Once it boots and QGC is connected:

1. Open **MAVLink Console**.

2. Type:

   ```text
   pcf8583 start -X -a 80
   ```

   * If you get something like `pcf8583: started` → we’re in business.
   * If it still says `pcf8583: command not found` → the board file change didn’t compile in, and we’ll adjust the exact spot you edited.

3. Then:

   ```text
   pcf8583 status
   ```

   to see the driver’s status.
