# Soil Temperature: DS18B20 Waterproof Probes

Reads temperature from DS18B20 probes: the steel-tipped waterproof ones
made to bury in a worm bin. They speak the 1-Wire protocol, which means
MANY probes can share one single data wire and the demo reads them all,
each with its own factory-burned serial number.

## Wiring

| Probe wire | Pico |
| ---------- | ---- |
| Red | 3V3 (pin 36) |
| Black | GND (any GND pin, e.g. 38) |
| Yellow (data) | GP22 (pin 29) |

**Required:** a 4.7k ohm resistor between GP22 and 3V3 (the bus pullup).
Without it you get no probes found or garbage CRC errors. One resistor
serves the whole bus no matter how many probes you add.

## Two versions

| File | What it does |
| ---- | ------------ |
| `bench.py` | OLED + terminal only. No Wi-Fi. |
| `main.py` + `index.html` | Everything above plus the PicoLab-N access point with a live dashboard at http://192.168.4.1 and JSON at `/data`. |

Files needed on the board: the version you chose, plus `index.html` (web
version only), plus from `lib/`: `picolab.py`, `ssd1306.py`. The 1-Wire
drivers (`onewire`, `ds18x20`) are built into MicroPython.

## Fault tolerance (all demos work this way)

- Boots and runs fine with no probes, no display, or neither.
- Plug a probe in mid-run: readings appear within a couple of seconds.
- Probes are found by scanning the wire. The scan happens on every
  reconnect, so if you ADD a probe mid-run, unplug and replug the data
  wire (or any probe) and the rescan will discover the newcomer.
- Readings never block the loop: the DS18B20 needs 750 ms to convert,
  so the demo reads the finished conversion and immediately starts the
  next one in the background.
- Terminal shows a startup banner and first readings immediately, then a
  heartbeat line every 5 seconds.
