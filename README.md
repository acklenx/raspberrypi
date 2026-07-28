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
| `lib/` | Drivers: `ssd1306.py` (OLED) and `vl53l0x.py` (laser distance sensor) |
| `projects/distance-station` | The full class build: distance sensor + OLED + live web dashboard |

Work top to bottom. Each example is one idea bigger than the last, and the
project at the end uses all of them at once.

## Installing the drivers

Projects that use the OLED or the distance sensor need the files in `lib/`
copied onto the board. Two ways:

- **Viper IDE:** upload `ssd1306.py` and `vl53l0x.py` to the board alongside
  your `main.py`.
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
