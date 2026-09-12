# 09 - Safety

Read before the first spin.

## The energy involved

A 914 mm disc producing 7.5 lbf at hover holds serious rotational energy. A carbon blade
leaving the hub departs tangentially at rotor tip speed and carries enough energy to
penetrate drywall and to be lethal to a person.

Concrete numbers for this rotor, R = 457 mm:

| Head RPM | Tip speed | Rotor kinetic energy |
|---|---|---|
| 1600 | 76.6 m/s (171 mph) | roughly 100 to 170 J |
| 1800 | 86.1 m/s (193 mph) | roughly 120 to 210 J |
| 2000 | 95.7 m/s (214 mph) | roughly 150 to 260 J |

The range spans the uncertainty in finished blade mass; the cores measure 30.3 cm^3 each and
the carbon layup adds to that. For scale, a 9 mm pistol round carries about 500 J and a .22
LR about 160 J. **A departing blade at 2000 rpm is in the same energy class as a .22.**

The protocol in doc 06 deliberately walks collective up to find the thrust ceiling, so you
will be spending time at the top of this table, not the bottom.

**The blade failure plane is a disc, not a cone.** A departing blade travels in the plane of
rotation, outward in every direction. Standing "off to the side" is standing in it.
Standing above or below is safe. This is the single most misunderstood thing about rotor
testing.

## Standoff and barrier

- Nobody in the plane of rotation during a spin. Not you, not an observer.
- Operate from **above or below** the disc plane, behind a barrier.
- Polycarbonate, at least 6 mm, or a masonry wall, or plain distance measured in tens of
  metres with everyone behind the rotor plane.
- Plywood is not a blade barrier. Carbon goes through it.

## Before every spin

- [ ] Prop bolts to torque, checked by hand
- [ ] Blades inspected for cracks, delamination, chips at the root
- [ ] Prop balanced
- [ ] Rig anchored or ballasted, no rock, no walk
- [ ] All stack fasteners torqued, jam nuts locked
- [ ] Nothing loose on or near the rig: tools, rags, zip tie tails, cable slack
- [ ] Cell cable and motor leads secured and clear of the disc
- [ ] Floor clear for three rotor diameters
- [ ] Everyone briefed on where the rotor plane is

## During

- Hearing protection. This is louder than you expect indoors.
- Eye protection.
- No loose clothing, no lanyards, no long hair unsecured.
- Keep a hand on the kill switch. Know how to cut power without walking toward the rig.
- Arm the ESC only with everyone clear and positioned.
- If the sound changes, cut power. Do not investigate a running rotor.

## Electrical

- **Never power the Arduino from the flight pack.** USB from the laptop only.
- Lithium packs: charge and store in a fire-safe bag, away from the test area.
- Have a means of disconnecting the pack that does not require reaching past the disc.
- Watch pack and motor temperature between runs. Let things cool.

## Failure modes specific to this rig

| Mode | Consequence | Mitigation |
|---|---|---|
| Stud bottomed in the cell | Cell zero permanently shifted, quiet bad data | Doc 03, thread engagement rule |
| Cell overloaded by shock | Cell damaged or nonlinear | 20 kg rating gives margin; do not drop it |
| Leg not anchored | Rig walks or tips under thrust | Anchor or ballast, verify by hand before spin |
| Post section not fully seated | Rig collapses under load | Visual and hand check every height change |
| Yoke pinch bolts loose | Nacelle rotates or releases | Torque check every run |

## A note on running indoors

Indoors is tempting for a controlled environment and it is fine at low heights, but watch
for recirculation off walls and ceilings, which corrupts the ground effect measurement.
Keep three rotor diameters of clearance to any surface other than the floor. If you cannot,
note it in the delivery, because the data will not be comparable to a free-field run.
