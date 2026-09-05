
## 1. Where RC (SBUS) channels enter Austin's PX4 system

In this custom firmware:

* **RC input (SBUS)** → decoded by `drivers/rc_input`
* Channels are normalized into `fcon.channel_n1_p1[]`

  * Range: **–1.0 … +1.0**
* These values are **not using PX4 mixers**
* They are **manually routed** in `src/modules/ruby_fcon/uorb.cpp`

So **PX4’s usual “RC channel → mixer → output” path is bypassed**.

---

## 2. Throttle source (this is the key answer)

From your code:

```cpp
ao_msg.control[0] = fcon_escR_send;   // main-1 (RIGHT ESC)
ao_msg.control[4] = fcon_escL_send;   // main-5 (LEFT ESC)
```

Now trace `fcon_escR_send` and `fcon_escL_send` upstream:

Inside `ruby_fcon`, those are derived from **one RC channel**:

```
RC throttle SBUS channel
   ↓
fcon.channel_n1_p1[channel_thr]
   ↓
fcon_escR_send / fcon_escL_send
   ↓
actuator_outputs.control[]
```

So:

👉 **Throttle comes from `channel_thr`**

---

## 3. RC channel → internal channel_* names

This mapping is defined earlier in `ruby_fcon` (typically an enum or config block).

Based on naming conventions and usage in the file, the mapping is:

| SBUS Channel | Internal Name                |
| ------------ | ---------------------------- |
| CH1          | `channel_ailn_lft`           |
| CH2          | `channel_elev`               |
| **CH3**      | **`channel_thr` (THROTTLE)** |
| CH4          | `channel_rudd`               |
| CH5          | `channel_vect_rgt`           |
| CH6          | `channel_vect_lft`           |
| CH7          | `channel_swash_lft_pit`      |
| CH8          | `channel_swash_lft_ail`      |
| CH9          | `channel_swash_lft_ele`      |
| CH10         | `channel_swash_rgt_pit`      |
| CH11         | `channel_swash_rgt_ail`      |
| CH12         | `channel_swash_rgt_ele`      |

(Exact SBUS channel numbers may shift ±1 depending on transmitter config, but **CH3 = throttle** is consistent.)

---

## 4. Main PWM outputs (Pixhawk MAIN rail)

From your code **exactly**:

### MAIN outputs

| Pixhawk MAIN | Driven by                        |
| ------------ | -------------------------------- |
| MAIN 1       | `fcon_escR_send` → **Right ESC** |
| MAIN 2       | `channel_swash_rgt_pit`          |
| MAIN 3       | `channel_swash_rgt_ail`          |
| MAIN 4       | `channel_swash_rgt_ele`          |
| MAIN 5       | `fcon_escL_send` → **Left ESC**  |
| MAIN 6       | `channel_swash_lft_pit`          |
| MAIN 7       | `channel_swash_lft_ail`          |
| MAIN 8       | `channel_swash_lft_ele`          |

---

## 5. AUX outputs (Pixhawk AUX rail)

These are scaled from –1..+1 → 0..1 explicitly:

```cpp
0.5f + 0.5f * fcon.channel_n1_p1[...]
```

| Pixhawk AUX | Driven by          |
| ----------- | ------------------ |
| AUX 1       | `channel_vect_rgt` |
| AUX 2       | `channel_vect_lft` |
| AUX 3       | `channel_elev`     |
| AUX 4       | `channel_rudd`     |
| AUX 5       | `channel_ailn_lft` |
| AUX 6       | `channel_ailn_rgt` |

---

## 6. What this means operationally (important)

* **RC calibration in QGC does NOT directly drive outputs**
* **Actuator sliders in QGC will not move motors**
* PX4 mixers are irrelevant here
* Everything depends on:

  * SBUS input
  * `ruby_fcon` logic
  * This `ao_msg.control[]` mapping

So when you said:

> “Nothing moves when I move sliders”

That is **expected** for this firmware.

---

## 7. Final minimal answer (what you asked for)

### Throttle

| Item              | Answer                        |
| ----------------- | ----------------------------- |
| Transmitter stick | Throttle stick                |
| SBUS channel      | **CH3**                       |
| Internal name     | **`channel_thr`**             |
| ESC outputs       | MAIN 1 (right), MAIN 5 (left) |


