# Servo bench demo: an SG90 hobby servo sweeps from 0 to 180 degrees and
# back, forever (speed set by SPEED_DPS). No Wi-Fi. The OLED and terminal
# show the current angle.
#
# A servo gives no feedback, so this demo cannot tell if the servo is
# actually plugged in. It just keeps commanding angles; plug the servo
# in mid-run and it starts moving. The display stays optional too.
# The truth light (the onboard LED, short blink every cycle) proves the
# CODE is running; if the servo still does not move, check its wiring.
#
# Wiring: orange signal wire to GP16, red to VBUS (5V), brown to GND.
# On the board: this file (as main.py or run it from the IDE),
# lib/picolab.py, lib/ssd1306.py.

import gc
import time
from machine import PWM, Pin

import picolab

MIN_US = 600
MAX_US = 2400
# Sweep speed in degrees per second. Time-based, so this is the real speed
# regardless of loop timing. An SG90 tops out near 500 deg/s; 400 is fast.
SPEED_DPS = 400
SERVO_PIN = 16  # servo signal (orange lead); default GP16, physical pin 21

picolab.banner("Servo Bench Demo", [
    "Wiring: signal=GP16, power=VBUS 5V, GND",
    "Sweeps 0 to 180 and back, forever",
    "OLED optional at 0x3C",
])

pwm = PWM(Pin(SERVO_PIN))
pwm.freq(50)


def write_angle(angle):
  angle = max(0.0, min(180.0, angle))
  us = MIN_US + (angle / 180.0) * (MAX_US - MIN_US)
  pwm.duty_u16(int(us * 65535 / 20000))
  return angle


current = 0.0
target = 180.0
write_angle(current)
picolab.log("Servo sweep started at 0 degrees.")

display = picolab.Display()
light = picolab.StatusLight()
light.set_slots([True])
heartbeat = picolab.Throttle(5000)

last = time.ticks_ms()
while True:
  light.poll()
  now = time.ticks_ms()
  dt = time.ticks_diff(now, last) / 1000.0
  last = now
  if current < target:
    current = min(target, current + SPEED_DPS * dt)
  elif current > target:
    current = max(target, current - SPEED_DPS * dt)
  else:
    target = 0.0 if target == 180.0 else 180.0

  write_angle(current)

  display.show([
      "Servo bench",
      "sweep 0-180",
      "angle: %3d deg" % int(current),
  ], bar=current / 180.0)

  if heartbeat.ready():
    picolab.log("Servo angle:", int(current), "target:", int(target))

  time.sleep_ms(50)
  gc.collect()
