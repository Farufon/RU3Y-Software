Yes, daisy-chaining two TFRPM01 boards on I²C is correct and supported.
It behaves exactly the same as using a splitter, as long as:
	•	Each board has a unique I²C address (0x50 and 0x51)
	•	All boards share SDA, SCL, GND, and 5V
	•	Total cable length stays reasonable

⸻

Why this works (important mental model)

I²C is:
	•	Open-drain
	•	Multi-drop
	•	Bus-based

That means:
	•	SDA and SCL are shared wires
	•	Devices do not drive HIGH, they only pull LOW
	•	Addressing determines who responds

So whether you do this:

Pixhawk → Splitter → Board A
                   → Board B

or this:

Pixhawk → Board A → Board B

Electrically, the bus looks the same.

⸻

Correct daisy-chain wiring

Pixhawk I²C
   |
   |--- SDA ----> TFRPM01 #1 SDA ----> TFRPM01 #2 SDA
   |--- SCL ----> TFRPM01 #1 SCL ----> TFRPM01 #2 SCL
   |--- +5V ----> TFRPM01 #1 VCC ----> TFRPM01 #2 VCC
   |--- GND ----> TFRPM01 #1 GND ----> TFRPM01 #2 GND

Each board independently gets:
	•	One ESC white wire → RPM IN
	•	ESC ground → GND (shared ground is correct)

⸻

Addressing (this is the only thing that matters)

Board	Jumper	Address	Decimal
#1	Open	0x50	80
#2	Closed	0x51	81

PX4 does not care how they’re wired, only the address.

⸻

Starting both drivers (correct sequence)

From NSH or MAVLink Console:

pcf8583 start -X -a 80
pcf8583 start -X -a 81

Then verify:

pcf8583 status

You should see two instances, one per address.

⸻

Listening to both RPM streams

PX4 publishes multiple instances of the same uORB topic.

listener rpm        # instance 0 (0x50)
listener rpm 1      # instance 1 (0x51)

That is exactly how PX4 expects multi-engine setups to work.

⸻

Parameters (per-sensor)

PX4 auto-indexes parameters by instance:

Sensor	Parameter
#1	PCF8583_MAGNET
#2	PCF8583_MAGNET_1

Set them independently if needed.

⸻

Grounding — you are doing this correctly

This is important and you got it right:
	•	ESC white + ESC ground → TFRPM01
	•	TFRPM01 ground → Pixhawk ground
	•	Maestro ground (if used) → same ground

That creates one clean reference plane.

⚠️ Just do not feed multiple 5V sources into the Pixhawk rail.

⸻

Practical cautions (read once)
	•	Keep I²C cables short (≤30–40 cm total)
	•	Do not add extra pull-ups unless required (Pixhawk already has them)
	•	If you see bus errors later, lower I²C speed — but you are fine for now

⸻

Bottom line

✔ Daisy-chain = splitter = valid
✔ Two TFRPM01s on one Pixhawk I²C bus = correct
✔ PX4 + pcf8583 fully supports this
✔ You are wiring and thinking about this exactly right
