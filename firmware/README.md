# MicroPython Firmware for the Pico 2 W

Brand-new boards ship empty. This is the exact MicroPython build all the
demos in this repo are tested against, kept here so nobody has to hunt
for the right file on a workshop morning.

| File | Version | Source |
| ---- | ------- | ------ |
| `RPI_PICO2_W-20260406-v1.28.0.uf2` | v1.28.0 (2026-04-06) | [micropython.org/download/RPI_PICO2_W](https://micropython.org/download/RPI_PICO2_W/) |

SHA-256: `686f0d0bd427ca68d149016808f95765df7921c5845d22ff8ebaec287300fce4`
(byte-identical to the official micropython.org release; MicroPython is
MIT licensed).

## Flashing (about 15 seconds per board)

1. Hold the **BOOTSEL** button on the Pico while plugging it into USB.
2. It appears as a flash drive named `RP2350`.
3. Drag `RPI_PICO2_W-20260406-v1.28.0.uf2` onto the drive.
4. The drive disappears and the board reboots into MicroPython. Done:
   from here on, everything is Viper IDE and one-click installs.

Doing a classroom set? Leave the file on the desktop and do the boards
assembly-line style: hold, plug, drag, unplug, next.

This step is the one thing a browser cannot do: the bootloader is a
plain USB flash drive, so the file has to be copied on by hand (once per
board, ever).
