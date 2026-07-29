# Webserver: your Pico becomes a Wi-Fi hotspot with its own website.
#
# 1. Run this file. The terminal prints the network name.
# 2. On your phone, join that Wi-Fi network (no password).
# 3. Browse to http://192.168.4.1
#
# The page shows a visit counter and the Pico's own chip temperature,
# read from the sensor built into the RP2350. No extra hardware needed.
#
# NOTE: if several Picos run this in the same room, give each one its
# own SSID below (PicoWeb-1, PicoWeb-2, ...) so phones can tell them apart.

import socket
import time
import network
from machine import ADC

SSID = "PicoWeb"

# --- internal temperature sensor -------------------------------------
sensor = ADC(ADC.CORE_TEMP)


def chip_temp_c():
  reading = sensor.read_u16() * (3.3 / 65535)
  return 27 - (reading - 0.706) / 0.001721


# --- access point ----------------------------------------------------
ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.ifconfig(("192.168.4.1", "255.255.255.0", "192.168.4.1", "192.168.4.1"))
ap.config(essid=SSID, security=0)

while not ap.active():
  time.sleep(0.1)

print("\n" + "=" * 40)
print("Wi-Fi network up!")
print("SSID:     " + SSID)
print("Website:  http://192.168.4.1")
print("=" * 40)

# --- webserver -------------------------------------------------------
PAGE = """<!DOCTYPE html>
<html><head><title>Pico Webserver</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body {{ font-family: sans-serif; text-align: center; background: #0f172a;
         color: #f8fafc; padding: 40px 20px; }}
  .big {{ font-size: 48px; font-weight: 800; color: #38bdf8; }}
</style></head>
<body>
  <h1>Hello from your Pico 2 W!</h1>
  <p>This page is served by a $6 microcontroller.</p>
  <div class="big">{temp:.1f} &deg;C</div>
  <p>chip temperature</p>
  <p>You are visitor number <b>{count}</b>. Refresh me!</p>
</body></html>
"""

def make_server():
  """Open the listening socket, surviving "address in use" after a re-run.

  When you stop a program with Ctrl+C and run it again, the old listening
  socket can still own port 80 (the board never rebooted, so nothing let
  go of it). Instead of making you unplug the Pico, bounce the Wi-Fi
  stack, which frees every old socket, and try once more.
  """
  for attempt in range(2):
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
      s.bind(("0.0.0.0", 80))
      s.listen(2)
      return s
    except OSError as e:
      s.close()
      if e.errno != 98 or attempt:  # 98 = EADDRINUSE
        raise
      print("Port 80 busy (an old run still owns it). Recycling Wi-Fi...")
      ap.active(False)
      time.sleep(0.5)
      ap.active(True)
      ap.ifconfig(("192.168.4.1", "255.255.255.0", "192.168.4.1", "192.168.4.1"))
      ap.config(essid=SSID, security=0)
      while not ap.active():
        time.sleep(0.1)


server = make_server()

count = 0

while True:
  try:
    cl, addr = server.accept()
    cl.settimeout(0.5)
    try:
      cl.recv(512)
    except Exception:
      pass
    count += 1
    print("Visit", count, "from", addr[0])
    body = PAGE.format(temp=chip_temp_c(), count=count)
    cl.send("HTTP/1.0 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n")
    cl.send(body)
    cl.close()
  except OSError:
    pass
