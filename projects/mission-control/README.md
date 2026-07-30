# Mission Control

**[Open this project in Viper IDE](https://viper-ide.org/?install=github:acklenx/raspberrypi/projects/mission-control/package.json)**: one click puts a connected Pico on the classroom network.

One wall display for every station in the room. Stations keep running
their normal demos; the only change is WHERE they serve: instead of
each Pico opening its own PicoLabN hotspot, they all join the classroom
router, and an aggregator (a Pi Zero, or any laptop) finds them, polls
them once a second, and projects everything on one page.

## The classroom network

| Setting | Value |
| ------- | ----- |
| Router | GL.iNet GL-SFT1200 (the classroom kit) |
| SSID | `WormHole` |
| Password | `supersecret` |
| Subnet | 192.168.8.x (the GL.iNet default) |

## Station side (each Pico): one file

Installing this project drops `wifi.json` onto the board:

```json
{"ssid": "WormHole", "password": "supersecret"}
```

That is the whole switch. When `picolab.WebApp` starts and finds
`wifi.json`, it JOINS that network and serves its dashboard on its
DHCP address (printed in the terminal and shown on the wall). If the
router is off, or the file is missing, the station opens its own
PicoLabN hotspot exactly as before, so nothing ever breaks at home.
Delete `wifi.json` to go back to hotspot mode.

## Wall side: one command

On the Pi Zero (or any machine on WormHole):

```
python3 server.py
```

Open `http://<that machine>:8080` and put it on the projector. The
server scans 192.168.8.x for anything answering `/data`, adds new
stations as they appear, polls each every second, and flags any tile
red when a station stops answering. Config knobs (subnet, poll rate,
static station list) are at the top of `server.py`.

Raw aggregate for your own experiments: `/all.json`.

## Testing without hardware

```
MC_NOSCAN=1 MC_STATIONS=127.0.0.1:8181,127.0.0.1:8182 python3 server.py
```

points it at fake stations (anything serving `/data` JSON).

---

Fresh board? Flash the [tested MicroPython build](https://github.com/acklenx/raspberrypi/raw/main/firmware/RPI_PICO2_W-20260406-v1.28.0.uf2) first: hold BOOTSEL while plugging in, drop the file on the drive that appears, done. Details in [firmware/](../../firmware).
