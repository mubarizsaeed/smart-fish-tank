# ESP32 nodes (planned)

Two ESP32 jobs are on the roadmap. Neither is wired yet; this page is the plan
so the next build session starts from a spec instead of a blank breadboard.
Everything marked *proposed* can change once the parts are in hand (the rule
from the feeder build applies: verify against the real hardware, not the
datasheet).

The interactive 3D model in [`../docs/esp32_node_3d.html`](../docs/esp32_node_3d.html)
shows where both nodes sit on the tank. A still of it is in the main README.

## 1. Water-quality node

An ESP32 that lives **dry, behind the back glass**, in a small printed probe
saddle that hooks over the rim next to the feeder. Only the probes go in the
water. It reports to the feeder Pi over Wi-Fi and shows up as a second data
source on the feed page.

### Sensors

| Measurement | Part | Interface | Why |
|---|---|---|---|
| Temperature | DS18B20 waterproof stainless probe | 1-Wire, 4.7 kΩ pull-up | Cherry barbs want roughly 23 to 27 °C; the lab HVAC drifts on weekends |
| pH | Glass pH electrode (BNC) + analog conditioning board | ADC, 2-point calibration with pH 4 and 7 buffers | API liquid test kit today; this makes it continuous |
| Water level | Float switch on a short stem at the waterline | Digital input, internal pull-up | Evaporation in a rimless tank; the feeder's drop hole needs water under it |

Later candidates: TDS probe, and a leak sensor on the desk under the back glass.

### Proposed pin map (ESP32 DevKitC)

| Signal | GPIO | Note |
|---|---|---|
| DS18B20 data | 4 | 4.7 kΩ to 3V3 |
| pH analog | 34 | ADC1 only (ADC2 is unusable while Wi-Fi is on) |
| Float switch | 27 | `INPUT_PULLUP`, closed = water OK |
| Status LED | 2 | on-board LED |
| Power | 5 V on VIN | USB-C from a wall adapter, not from the Pi |

### Data path

```
probes -> ESP32 (reads every 60 s) -> Wi-Fi -> MQTT broker on the feeder Pi
       -> SQLite log + latest values on the feed page -> alert if out of band
```

Topics (proposed): `tank/water/temperature`, `tank/water/ph`,
`tank/water/level`, plus `tank/node/water/status` as an MQTT last-will so the
Pi notices when the node drops off. Alert bands start at 22 to 28 °C and pH
6.5 to 7.5 and get tightened once there is a week of baseline data.

### Build stages

1. **Breadboard** on the bench with the probes in a cup of tank water. Verify
   the DS18B20 against the lab thermometer and the pH board against the
   buffer solutions.
2. **Protoboard** inside the printed probe saddle, probes routed over the rim
   with a drip loop so water cannot track down the cable into the enclosure.
3. **KiCad 2-layer PCB** once the circuit has run for a month without changes.

## 2. Camera pan head

The v5 camera mount (desk clamp, telescoping post, slide-in dock) is designed
and ready to print. A later revision motorizes it: a second 28BYJ-48 and
ULN2003 sit stationary inside an enclosed pod in the clamp base, a shaft runs
up the column to a drum the camera rides on, and a spare ESP32 drives the
stepper over Wi-Fi. One USB-C cable from the Pi powers the pod.

- About 350° of sweep with a soft stop, so the camera's own USB cable never
  winds up.
- Lets the same Arducam pan between the tank and a second robot project on the
  floor behind it.
- Control: a tiny HTTP endpoint on the ESP32 (`/pan?deg=`), called from the
  vision Pi; the stepper code is the same half-step sequence as
  [`../feeder/feeder.py`](../feeder/feeder.py), ported to C++.

Renders of the mount: [`../docs/images/renders/camera-mount-v5.png`](../docs/images/renders/camera-mount-v5.png),
pod cutaway, dock and clamp detail in the same folder.

## Parts to buy

| Qty | Part |
|---|---|
| 2 | ESP32 DevKitC (one per node) |
| 1 | DS18B20 waterproof probe, 1 m |
| 1 | pH electrode + analog board (BNC) and pH 4 / 7 buffer sachets |
| 1 | Vertical float switch, PP, M10 thread |
| 1 | 28BYJ-48 + ULN2003 (pan head) |
| 1 | Half-size protoboard, 4.7 kΩ resistor, JST leads |

Firmware is not committed yet: it gets written against the breadboard in
stage 1, so nothing untested lands in this repo.
