# GL5528 LDR: Basic Light Level

The cheap-and-cheerful light demo. A GL5528 photoresistor (LDR) changes
resistance with light; putting it in a voltage divider turns that into a
voltage the Pico's ADC can read. More light = lower LDR resistance =
higher voltage on the pin.

## Wiring

| Part | Connection |
| ---- | ---------- |
| LDR leg 1 | 3V3 (pin 36) |
| LDR leg 2 | GP28 (pin 34, and one leg of the 10k resistor) |
| 10k resistor | GP28 (pin 34) to GND |

GP28 is ADC2. The LDR has no polarity; either leg can face 3V3.

## Two versions

| File | What it does |
| ---- | ------------ |
| `bench.py` | OLED + terminal only. No Wi-Fi. |
| `main.py` + `index.html` | Everything above plus the PicoLab-N access point with a live dashboard at http://192.168.4.1 and JSON at `/data`. |

Files needed on the board: the version you chose, plus `index.html` (web
version only), plus from `lib/`: `picolab.py`, `ssd1306.py`.

## Fault tolerance (all demos work this way)

- Boots and runs fine with no display; the OLED lights up within ~3
  seconds of being plugged in mid-run.
- One honest limitation: an ADC pin cannot tell whether the divider is
  actually wired up. If nothing is connected, the floating pin reads
  electrical noise, so the numbers wander instead of reporting
  "unplugged". That is a good discussion point in class.
- Terminal shows a startup banner and first readings immediately, then a
  heartbeat line every 5 seconds.
