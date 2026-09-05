
# INITIAL INSTALLATION

Hi Jon,

You can install the latest development cut of the Flight Model release by running the installer with this command line option:

Install Name:
--install_name="X-Plane 12.5.0-d4-a11d9cdf"

Kind regards,

Marco Auer
Product Director | Laminar Research
X-Plane.com


On Mon, Apr 6, 2026 at 2:56 AM Austin Meyer <austin@x-plane.com> wrote:
hey marco plz get jon the latest 12.5 beta

thanks!!!!!!!!!!!!!!!!!!!!!!!!

jon here is ruby and need afls

flies EXACTLY like the real thing WHEN you use x-plane as the flite model wired to the REAL AIRPLANE for the flight control system (software in the loop testing)... not quite as accurate though when using the default x-plane flight contorl system which is not nearly so tuned....





# UPDATE


My work:
http://austinmeyer.com

The best book I've ever heard:
https://www.audible.com/pd/Concorde-Audiobook/B0B3L7Z8JB

Among the best MAKE-BELIEVE books I've ever heard:
https://www.audible.com/pd/Im-Starting-to-Worry-About-This-Black-Box-of-Doom-Audiobook/B0CT4JPXYF

What I'm listening to while coding X-Plane:
https://www.youtube.com/watch?v=NopDCRIdh4

Dear all,

I have a small patch for X-Plane 12.5.0 to get it to Development Cut 5.

Installation:
Install X-Plane 12.5.0 Development Cut 4
Download the X-Plane patch from our webpage and copy it into your X-Plane installation
https://files.x-plane.com/public/test_builds/X-Plane-12.5-d5_win.zip
https://files.x-plane.com/public/test_builds/X-Plane-12.5-d5_mac.zip
https://files.x-plane.com/public/test_builds/X-Plane-12.5-d5_lin.zip

Release Notes:
Restored compatibility for Special Controls (XPD-18010)
Some minor autopilot improvements
Fixed an issue where standing water caused tires to sink in (XPD-17992)
Improved Piper Cub wheel prone (XPD-18014)
Improved fuel intro time for engine start when starting a flight with engines running (XPD-17997)
Fixed prop swirl direction
Have a nice weekend!

Kind regards,

Marco Auer
Product Director | Laminar Research
X-Plane.com


On Thu, Apr 2, 2026 at 1:11 PM Marco Auer <marco@x-plane.com> wrote:
Dear all,

I created another Development Cut of the upcoming Flight Model Release. Please do not share any information about this release with anyone outside our organization.

Install Name:
--install_name="X-Plane 12.5.0-d4-a11d9cdf"

Release Notes:
## NOTAMS

> **⚠ Wake turbulence behavior has changed significantly**
>
> The wake turbulence simulation has been rebuilt from the ground up using first-principles physics. Aircraft in trail behind a heavy will experience more accurate and physically correct vortex effects. This is an intentional change — please share your feedback in the beta forum.

> **⚠ Propwash behavior has changed**
>
> The propwash swirl model has been significantly re-tuned in this release. High-power singles, taildraggers, and turboprops may feel different on takeoff and at low airspeeds. This is intentional. Please share your feedback in the beta forum.

## Flight Model
- Added propeller and rotor blade tracking, computing the induced velocity field across the rotor disc in real time. Press **Cmd+M** to visualize velocity overlays while a propeller or rotor is spinning.
- Rebuilt the wake turbulence simulation using first-principles physics. Vortex strength is now derived directly from the aircraft's induced drag, tracking every unit of energy from the wing through to the spinning air vortex. Wake turbulence now scales correctly with aircraft weight, speed, and wing configuration.
- Added wing upwash simulation. Previously only downwash was modeled. Aircraft with surfaces located ahead of the wing — such as canards or forward-mounted propellers — will now correctly experience the upwash effect.
- Improved seaplane hull dynamics. Each segment of the hull now correctly accounts for the water wake deflected by the segment ahead, improving pitch behavior, step taxi, and overall water handling accuracy.
- Improved stall modeling, resulting in more consistent and natural stall behavior with flowing stall waves.
- Improved electric motor modeling with a rewritten efficiency algorithm based on real-world motor data.
- Fixed an issue where propwash swirl was not correctly modeled, improving handling in high-power piston and turboprop aircraft.
- Added physics support for blimps, rigid airships, and high-altitude helium balloons, including ballonets for pitch and attitude control.
- Updated on-board generator modeling. The simulation now correctly applies the load of spinning a generator to the engine, affecting RPM and temperatures in a realistic manner.
- Fixed an issue where the helicopter engine governor was not functioning correctly, which prevented full power from being reached — particularly on one-engine-out scenarios in twin-engine helicopters.
- Fixed an issue where slung loads were positioned relative to the helicopter's CG rather than the correct wire attach point.
- Fixed an issue where a slung load object was no longer rendered after being released from the aircraft.
- Improved turn coordinator response time.

## Ground Handling
- Added wet and icy runway physics. Wet or icy pavement reduces braking effectiveness in affected areas.
- Added puddle physics on paved surfaces. Standing water creates areas of increased rolling drag. If the aircraft exceeds the hydroplane speed for its tire pressure, braking drag drops away and the aircraft hydroplanes.
- Added mud physics on unpaved surfaces. Standing water on grass, gravel, or dirt creates mud zones with significantly increased rolling drag, deteriorated braking, and wheel sinking. As X-Plane is fully force-based, the sinking effect is felt physically in cockpit views.

## Systems
- Improved hydraulic pressurization and de-pressurization speed to better match real aircraft behavior.
- Added control surface droop when hydraulic pressure is lost. This can be configured per surface in Plane Maker.
- Fixed a throttle dead-band issue affecting PT-6 turboprop engines.
- Added several engine start failure modes, including: starter failed, starter stuck on, insufficient fuel flow (hung start), and excessive fuel flow (hot start).
- Improved start fuel flow and engine temperature modeling. Hot starts are now more clearly indicated. The G1000 now displays a blinking temperature warning during a hot start.
- Improved CHT and oil temperature cool-down and warm-up behavior after shutdown and on cold starts.
- Fixed an issue where stowable propellers on motor gliders were not correctly positioned out of the airflow.
- Improved pressurization modeling. Cabin pressure loss rate is now influenced by cabin leakage, configurable in Plane Maker.
- Improved fuel flow indication accuracy when operating a piston engine significantly outside its optimal mixture ratio.
- Multiple generators can now be assigned to a single engine.
- Added improved artificial stability for quadcopters and drones.

## Fuel System
- Added support for up to 18 individual fuel tanks per aircraft.
- Improved readability of fuel system data throughout the simulator.
- Fixed an issue where fuel ramped up too early during engine start. (XPD-17970)
- Added new commands for quick fuel and electrical management: re-fuel to default, re-fuel to half, re-fuel to full, recharge batteries, and attach payload.

## Aircraft
### Beechcraft Baron B58
- Fixed an issue with engine asymmetry.

### F-14 Tomcat
- Fixed an issue with the autopilot CWS (Control Wheel Steering) mode.

## AI Aircraft
- Improved formation flying behavior. AI aircraft now perform more maneuvers, making formation flying more engaging to follow.
- Added instructor-triggerable traffic incursion for use in training scenarios.

## Plane Maker
- Fixed a long-standing issue where RSC was incorrectly labeled in Plane Maker.
- Added improvements to make starting a new aircraft from a blank template easier.
- Improved viewport display of CG position, view point, reference point, and aircraft forward direction.
- Corrected labels and added documentation and diagnostics for the hydraulic system.
- Added flap layout help tips to assist with configuring correct flap systems.

## User Interface & Controls
- Fixed an issue where the torque HUD readout displayed torque as a percentage of the thermodynamic limit rather than the torque limit.
- Fixed an issue where large numbers were displayed without comma separators.
- Added new data refs for tire skidding.

## SDK
- Added battery wattage output data ref.
- Added new plugin data refs to allow modification of AFL aerodynamic coefficients at runtime.
- Added new commands: `sim/fuel/re-fuel_default`, `sim/fuel/re-fuel_half`, `sim/fuel/re-fuel_full`, `sim/flight_controls/attach_payload`, `sim/electrical/recharge`.

## Bug Fixes
- Fixed an issue where smoke was incorrectly emitted forward from skidding landing gear.

Thanks,
Marco

Marco Auer
Product Director | Laminar Research
X-Plane.com


