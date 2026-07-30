#!/usr/bin/env python3
"""Mission Control: one wall display for every station in the room.

Runs on a Pi Zero, a laptop, anything with Python 3. Zero dependencies.
Stations are Picos that joined the classroom router (drop wifi.json on
them, see this project's README). This server finds them by scanning
the subnet for anything answering /data, polls them every second, and
serves the wall dashboard at  http://<this machine>:8080

    python3 server.py
"""

# ---- config at the top, house rule ----------------------------------
SUBNET = "192.168.8"      # GL.iNet "WormHole" router default network
SCAN_FROM, SCAN_TO = 2, 254
STATIC_STATIONS = []      # extra addrs, e.g. ["192.168.8.57", "127.0.0.1:8181"]
POLL_SECONDS = 1.0        # per-station refresh
RESCAN_SECONDS = 20       # how often to hunt for new stations
STALE_SECONDS = 6         # no answer this long = flagged on the wall
SERVE_PORT = 8080

import json
import os
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# env overrides make testing easy: MC_STATIONS=127.0.0.1:8181 MC_NOSCAN=1
STATIC_STATIONS += [s for s in os.environ.get("MC_STATIONS", "").split(",") if s]
NOSCAN = os.environ.get("MC_NOSCAN") == "1"

stations = {}
lock = threading.Lock()


def fetch(addr, timeout=0.8):
    with urllib.request.urlopen("http://%s/data" % addr, timeout=timeout) as r:
        return json.loads(r.read().decode())


def probe(addr):
    try:
        d = fetch(addr, 0.6)
    except Exception:
        return
    with lock:
        st = stations.setdefault(addr, {})
        st["data"] = d
        st["ts"] = time.time()
    print("station found:", addr, "->", d.get("ssid", "?"))


def scan_once():
    candidates = list(STATIC_STATIONS)
    if not NOSCAN:
        candidates += ["%s.%d" % (SUBNET, i) for i in range(SCAN_FROM, SCAN_TO + 1)]
    threads = [threading.Thread(target=probe, args=(a,), daemon=True)
               for a in candidates if a not in stations]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


def poll_loop():
    while True:
        with lock:
            addrs = list(stations)
        for a in addrs:
            try:
                d = fetch(a)
                with lock:
                    stations[a]["data"] = d
                    stations[a]["ts"] = time.time()
            except Exception:
                pass
        time.sleep(POLL_SECONDS)


def scan_loop():
    while True:
        scan_once()
        time.sleep(RESCAN_SECONDS)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path.startswith("/all.json"):
            now = time.time()
            with lock:
                out = {"stale_after": STALE_SECONDS, "stations": [
                    {"addr": a,
                     "age": round(now - s.get("ts", 0), 1),
                     "data": s.get("data")}
                    for a, s in sorted(stations.items())]}
            body = json.dumps(out).encode()
            ctype = "application/json"
        else:
            here = os.path.dirname(os.path.abspath(__file__))
            with open(os.path.join(here, "dashboard.html"), "rb") as f:
                body = f.read()
            ctype = "text/html"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


def main():
    threading.Thread(target=scan_loop, daemon=True).start()
    threading.Thread(target=poll_loop, daemon=True).start()
    print("=" * 52)
    print("MISSION CONTROL")
    print("  scanning:   %s.%d-%d %s" % (SUBNET, SCAN_FROM, SCAN_TO,
          "(disabled)" if NOSCAN else ""))
    print("  static:     %s" % (STATIC_STATIONS or "none"))
    print("  wall page:  http://<this machine>:%d" % SERVE_PORT)
    print("=" * 52)
    ThreadingHTTPServer(("0.0.0.0", SERVE_PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
