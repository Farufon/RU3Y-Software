# RU3Y LIVE RPM on I2C Port into Pixhawk for Austin PX4 Build


Assumptions:

* Currently reproducing builds of Austin's Version of PX4-Autopilot

* Castle ESC has been configured (Using Castle Link) for RPM OUT for it's white wire.  Use also ground when connecting to ESC white/ground → TFRPM01 Module “RPM IN”

* TFRPM01 Module I2C connected to Pixhawk I2C

ThunderFly TFRPM01 I²C Tachometer (Pixhawk-ready)
https://docs.thunderfly.cz/avionics/TFRPM01/

JST-GH I²C cable for Pixhawk (ThunderFly sells matching lengths). 
https://www.tindie.com/stores/thunderfly/items/

* Common ground essential. Don't duplicate 5V+!!


# CHANGE LOG...

## 1. Edit Drivers

### Open and edit, *default.px4board*


**ADD this** to the list in the drivers section:

```
CONFIG_DRIVERS_RPM_PCF8583=y
```

Example:

```
...
CONFIG_DRIVERS_POWER_MONITOR_INA228=y
CONFIG_DRIVERS_POWER_MONITOR_INA238=y
CONFIG_DRIVERS_POWER_MONITOR_PM_SELECTOR_AUTERION=y
CONFIG_DRIVERS_PWM_OUT=y
CONFIG_DRIVERS_PX4IO=y
CONFIG_DRIVERS_RC_INPUT=y
CONFIG_DRIVERS_RPM_PCF8583=y
CONFIG_DRIVERS_SAFETY_BUTTON=y
...

```
### Rebuild Austin's firmware

```
cd /Users/redfour/Austin_PX4/PX4-Autopilot

# remove the old build dir for this target
rm -rf build/px4_fmu-v6xrt_default

# rebuild
make px4_fmu-v6xrt_default
```

Flash new firmware

Using QGC, unplug then plug in, while in firmware tab, select Custom location

```
/Users/redfour/Austin_PX4/PX4-Autopilot/build/px4_fmu-v6xrt_default/px4_fmu-v6xrt_default.px4

```
In MAVLINK Console

```
pcf8583 start -X -a 80
```
-X = external I²C bus
-a 80 = decimal 80 = I²C address 0x50 (TFRPM01 default)

You should see

```
pcf8583: started
```
Once pcf8583 exists and starts, we’ll:

* Set PCF8583_MAGNET in QGC parameters (pulses per revolution).

* Spin the motor and confirm RPM shows up in QGC.

### In QGC, Parameters

Search for PCF8583_MAGNET

Formula (for Castle RPM OUT):
* White wire toggles once per electrical commutation.
* Approx rule:

pulses per rev = approx 3 times pole pairs

Example:
* Motor with 8 poles:
* 8 poles → 4 pole pairs
* PCF8583_MAGNET ≈ 3 × 4 = 12

Set PCF8583_MAGNET to your calculated value, write parameters, then reboot Pixhawk once (power cycle or QGC reboot command) so everything restarts clean.

```
PCF8583_MAGNET = 12
```

Set polling time

```
PCF8583_POOL = 100000   (100 ms)
```

Reboot Pixhawk, then run

```
pcf8583 start -X -a 80
```


### Now with the driver started

run this

```
listener rpm
```

You will see a STATIC output.  This is the MOTOR RPM.  Divide by 14:1 ratio for ROTOR

```
TOPIC: rpm #0
  rpm: 1234.5
  timestamp: 123456789
 ```

 Make it autostart.  Open...

 ```
 /Users/redfour/Austin_PX4/PX4-Autopilot/boards/px4/fmu-v6xrt/init/rc.board_sensors

```
Add a line near the other I²C sensor starts, something like:

```
# RPM sensor: TFRPM01 (PCF8583-compatible) on external I2C, addr 0x50
pcf8583 start -X -a 80
```

Rebuild again...

```
cd /Users/redfour/Austin_PX4/PX4-Autopilot
rm -rf build/px4_fmu-v6xrt_default
make px4_fmu-v6xrt_default
```
Flash the new build. 

### In MAVLINK Console

```
listener rpm
```

```
param show PCF8583*
```
You should see something like:
* PCF8583_MAGNET
* PCF8583_POOL
* (and possibly a reset-related param)

If you need to change, you can set in MAVLINK console here

```
param set PCF8583_MAGNET 12
param set PCF8583_POOL 100000
```

### Live Updates

Go in MAVLINK Inspector instead of Console

type

```
rpm
```
you will see an RPM stream

NOW in MAVLINK Console

```
watch -n 0.1 listener rpm
```

### MONITORING TWO RPM STREAMS FROM BOTH NACELLES

```
Pixhawk I2C ----> Splitter ----> TFRPM01 #1 (Addr 0x50)
                       |-------> TFRPM01 #2 (Addr 0x51)
```
Signal pins:

* SCL → SCL
* SDA → SDA
* +5V → VCC
* GND → GND

Each TFRPM01:

* ESC #1 White → RPM IN #1
* ESC #1 GND → RPM GND #1
* ESC #2 White → RPM IN #2
* ESC #2 GND → RPM GND #2



### Start two instances of the PCF8583 driver

The pcf8583 driver supports multiple sensors with unique addresses.

Start board #1 (default 0x50):

```
pcf8583 start -X -a 80
```

Start board #2 (0x51):

```
pcf8583 start -X -a 81
```

(80 decimal → 0x50, 81 decimal → 0x51)

Confirm both:

```
pcf8583 status

```

You will see two devices listed:

```
pcf8583#0 on I2C bus 6 address 0x50
pcf8583#1 on I2C bus 6 address 0x51
```

⸻

### Listen to both RPM streams

PX4 publishes a separate RPM topic for each instance:

Device 1:

```
listener rpm
```
You will see:

```
rpm.indicated_frequency_rpm [instance 0]
```

Device 2:

```
listener rpm 1
```

You will see:
```
rpm.indicated_frequency_rpm [instance 1]
```

Or view both in QGroundControl:

Analyze → MAVLink Inspector → search “rpm”

You will see:
	•	rpm[0].indicated_frequency_rpm
	•	rpm[1].indicated_frequency_rpm

Both update live.



### Set pulses-per-rev separately

Each sensor has its own parameter set:

For the first sensor:

```
PCF8583_MAGNET  (instance 0)
```

For the second sensor:

```
PCF8583_MAGNET_1  (instance 1)
```

Or in NSH:

```
param set PCF8583_MAGNET <value_for_sensor_1>
param set PCF8583_MAGNET_1 <value_for_sensor_2>
```

(Same for PCF8583_POOL, RESET, etc.)

Result

You now have:

Two ESCs
* Two RPM sensors
* One Pixhawk
* *Real-time dual RPM measurement

This works even if:
* Throttle comes from a Maestro
* ESC power is external
* Pixhawk is only powered by USB

| Component    | Sensor 1                       | Sensor 2                        |
|--------------|--------------------------------|---------------------------------|
| I²C Address  | `0x50`                         | `0x51`                          |
| Start command| `pcf8583 start -X -a 80`       | `pcf8583 start -X -a 81`        |
| Listen       | `listener rpm`                 | `listener rpm 1`                |
| Parameter    | `PCF8583_MAGNET`               | `PCF8583_MAGNET_1`              |





# Setting up Castle for RPM Out

* In **Castle Link Classic**, go to the menu/tab where **AUX / Auxiliary Wire Mode** is listed (on Edge/Edge Lite, AUX modes are selectable only via Castle Link). The Edge user guide states the **AUX line is disabled until a mode is selected** with Castle Link. ([Minicars][3])

> Depending on version, you’ll see AUX items among the advanced/other menus. Castle’s docs and product pages describe the AUX as the **“user-programmable white wire.”** ([Castle Homepage][4])

## Select **RPM OUT**

* Choose **RPM OUT** for **AUX Wire Mode**.
* Castle’s Edge manuals and tech tip define RPM OUT as:
  **“The ESC toggles the AUX line at every electrical commutation. Divide by magnetic pole-pairs to get mechanical RPM.”** ([LeoMotion Download][5])

*(Optional)* Leave “Idle Datalog Erase” **off** unless you want AUX toggling at idle to clear logs. (Castle calls this out as an add-on behavior in Castle Link.) ([Castle Homepage][6])

## Write settings & power-cycle

* Click **Update/Write** (or **Send Settings to Controller**) to save.
* **Disconnect** main power, then remove the USB link.
* Your **white wire now outputs a TTL pulse train** proportional to commutation. (You’ll use that for your FT232H reader, flight controller capture, or an I²C tach bridge.)