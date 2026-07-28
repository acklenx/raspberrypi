# BME280: Temperature, Humidity, Pressure

The environment sensor. Reads air temperature, relative humidity, and
barometric pressure over I2C. Also works with a BMP280 (its humidity-free
sibling; the demo reports humidity as n/a).

## Wiring

| BME280 pin | Pico |
| ---------- | ---- |
| VIN / VCC | 3V3 |
| GND | GND |
| SDA | GP0 |
| SCL | GP1 |

I2C address `0x76` or `0x77` (the demo finds either automatically).

## Two versions

| File | What it does |
| ---- | ------------ |
| `bench.py` | OLED + terminal only. No Wi-Fi. |
| `main.py` + `index.html` | Everything above plus the PicoLab-N access point with a live dashboard at http://192.168.4.1 and JSON at `/data`. |

Files needed on the board: the version you chose, plus `index.html` (web
version only), plus from `lib/`: `picolab.py`, `bme280.py`, `ssd1306.py`.

## Fault tolerance (all demos work this way)

- Boots and runs fine with no sensor, no display, or neither.
- Plug the sensor in mid-run: readings appear within ~2 seconds.
- Plug the display in mid-run: it lights up within ~3 seconds.
- Terminal shows a startup banner and first readings immediately, then a
  heartbeat line every 5 seconds.
