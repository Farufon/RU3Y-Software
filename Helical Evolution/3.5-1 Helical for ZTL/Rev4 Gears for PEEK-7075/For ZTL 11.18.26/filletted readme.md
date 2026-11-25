3p5-to-1_helical.py now has the root fillets and tip break built in. It replaces the earlier 3.5:1 script; everything else is unchanged. This revision has not been run in Fusion.

Three new parameters at the top:

| Parameter | Default | What it does |
|---|---|---|
| `ROOT_FILLET` | 0.2 | Root fillet radius as a fraction of the module, both gears. Works out to 0.133 mm here. |
| `PINION_TIP_BREAK` | 0.05 | Radius in mm on the pinion tip corners. |
| `GEAR_TIP_BREAK` | 0.0 | Same for the gear. Left sharp, since the plastic part does not need it. |

Setting any of them to 0 gives the old sharp corner back.

Both features are drawn into the tooth profile itself, so they run the full face width along the helix rather than being added as fillet features afterward.

What I checked:

- **No interference.** The filleted pair meshes with zero overlap through a full tooth cycle. The gear's sharp tips clear the pinion's root fillets, and the reverse.
- **Room to grow.** The root fillet can go up to 0.38 of the module (a nearly full-round root) without interference, if you want more strength in the plastic gear.

One thing to watch on the first run: each tooth sketch now has six curves instead of four, so the loft is the step most likely to complain. If it fails, paste the error and I'll fix it.

The tooth-end edges, where each tooth meets the top and bottom faces, are still sharp in the model. Those are easier to break at the machine than in CAD.