# Raspberry Pi Pico 2 W Samples

MicroPython samples for the Raspberry Pi Pico 2 W, used in
[Maker Lab Kids](https://MakerLabKids.com) workshops. Everything here is
written to run from [Viper IDE](https://viper-ide.org), a MicroPython IDE
that runs entirely in your browser. Nothing to install.

## Quickstart

1. **Get MicroPython on the board (one time).** Hold the BOOTSEL button while
   plugging the Pico into USB. It appears as a flash drive. Drag on the
   Pico 2 W firmware (`.uf2`) from
   [micropython.org/download/RPI_PICO2_W](https://micropython.org/download/RPI_PICO2_W/).
   The drive disappears and the board reboots into MicroPython.
2. **Open [viper-ide.org](https://viper-ide.org)** in Chrome or Edge.
3. Click the **connect** button (top right), pick **USB**, and choose the
   Pico from the list.
4. Use the file panel to create or upload files, and the terminal panel to
   run them and to use the REPL.

A file saved to the board as `main.py` runs automatically every time the
board powers up. That is how a finished project "ships."

## What's here

| Folder | What it teaches |
| ------ | --------------- |
| `examples/01-hello-world` | Run your first program, read output in the terminal |
| `examples/02-repl` | Talk to the board live at the `>>>` prompt, scan I2C |
| `examples/03-blink` | Control real hardware: the onboard LED |
| `examples/04-webserver` | The Pico becomes a Wi-Fi hotspot serving its own website |
| `lib/` | Shared code: drivers plus `picolab.py`, the fault-tolerance framework all sensor demos use |
| `projects/` | One demo per sensor, plus the servo. See the table below |
| `docs/` | The branded lab guide (GitHub Pages site) |

Work top to bottom. Each example is one idea bigger than the last, and the
projects use all of them at once.

## Sensor demo projects

Every project (except the original `distance-station`) comes in two
versions: `bench.py` (OLED + terminal, no Wi-Fi) and `main.py` +
`index.html` (adds the PicoLab-N access point with a live dashboard at
http://192.168.4.1 and JSON at `/data`). All of them are fault tolerant:
they run with the sensor missing, the display missing, or both, and pick
parts up the moment they are plugged in, no restart needed.

| Project | Sensor / actuator | Signal |
| ------- | ----------------- | ------ |
| `projects/distance-station` | VL53L0X laser distance (the original demo) | I2C `0x29` |
| `projects/bme280` | BME280 temperature + humidity + pressure | I2C `0x76/0x77` |
| `projects/soil-moisture` | Capacitive soil moisture v1.2 | GP26 (ADC0) |
| `projects/soil-temperature` | DS18B20 waterproof probes (many per wire) | GP22 + 4.7k pullup |
| `projects/servo` | SG90 servo, driven from the web dashboard | GP16 (PWM), VBUS power |
| `projects/light-basic` | GL5528 photoresistor divider | GP28 (ADC2) |
| `projects/light-lux` | BH1750 lux sensor | I2C `0x23` |
| `projects/sound` | MAX9814 mic amp, sound level meter | GP27 (ADC1) |

## Installing the drivers

Projects need some of the files in `lib/` copied onto the board (each
project's README lists exactly which). Two ways:

- **Viper IDE:** upload the needed `lib/` files to the board alongside
  your `main.py`. All sensor demos need `picolab.py` and `ssd1306.py`,
  plus the sensor's own driver if it has one.
- **mip, from the REPL** (needs the Pico joined to a Wi-Fi network that has
  internet; our classroom access points do not, so use the upload method
  in class):

  ```python
  import mip
  mip.install("github:acklenx/raspberrypi")
  ```

## Wiring used throughout

All I2C devices share one bus on I2C0:

| Signal | Pico pin |
| ------ | -------- |
| SDA | GP0 (pin 1) |
| SCL | GP1 (pin 2) |
| Power | 3V3 |
| Ground | GND |

Device addresses: OLED `0x3C`, VL53L0X distance sensor `0x29`. Check your
wiring any time with two lines in the REPL:

```python
i2c = machine.I2C(0, sda=machine.Pin(0), scl=machine.Pin(1))
i2c.scan()
```

Learn. Make. Share.
