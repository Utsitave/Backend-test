"""
Raspberry Pi sensor client — sends measurements to the IoT secure backend.

Setup:
  1. Copy certs/ca.crt from the backend VM to this directory.
  2. Register the device and get an API key (see README or admin endpoint).
  3. Edit the configuration block below.
  4. pip install requests
  5. python3 rpi_client.py

Uncomment the DHT22 block if you have that sensor wired up.
"""

import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import urllib3
import requests

# ── Configuration ─────────────────────────────────────────────────────────────
SERVER_URL   = "https://192.168.x.x:8443"  # backend VM IP and port
API_KEY      = "your-device-api-key-here"  # returned when device was registered
INTERVAL     = 30                          # seconds between readings
VERIFY_TLS   = False                       # set to "server.crt" if you copy it from the backend
# ──────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

if not VERIFY_TLS:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_session = requests.Session()
_session.headers["X-Device-API-Key"] = API_KEY
_session.verify = VERIFY_TLS


# ── Sensor readers ─────────────────────────────────────────────────────────────

def _read_cpu_temp() -> float:
    raw = Path("/sys/class/thermal/thermal_zone0/temp").read_text().strip()
    return int(raw) / 1000.0


def read_sensors() -> list[dict]:
    """
    Return a list of readings: {sensor_type, value, unit, extra_data?}
    Add or remove sensors here to match your hardware.
    """
    readings = []

    # CPU temperature — always available on RPi, good for baseline health check
    try:
        readings.append({
            "sensor_type": "cpu_temperature",
            "value": _read_cpu_temp(),
            "unit": "C",
        })
    except Exception as exc:
        log.warning("CPU temp read failed: %s", exc)

    # ── DHT22 temperature + humidity (uncomment if wired up) ──────────────────
    # Requires: pip install adafruit-circuitpython-dht
    #           sudo apt install libgpiod2
    #
    # import adafruit_dht, board
    # _dht = adafruit_dht.DHT22(board.D4)  # change D4 to your GPIO pin
    #
    # try:
    #     readings.append({
    #         "sensor_type": "temperature",
    #         "value": _dht.temperature,
    #         "unit": "C",
    #         "extra_data": {"sensor": "DHT22"},
    #     })
    #     readings.append({
    #         "sensor_type": "humidity",
    #         "value": _dht.humidity,
    #         "unit": "%",
    #         "extra_data": {"sensor": "DHT22"},
    #     })
    # except Exception as exc:
    #     log.warning("DHT22 read failed: %s", exc)
    # ──────────────────────────────────────────────────────────────────────────

    return readings


# ── Sending ────────────────────────────────────────────────────────────────────

def send_measurement(sensor_type: str, value: float, unit: str, extra_data: dict | None = None) -> bool:
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sensor_type": sensor_type,
        "value": value,
        "unit": unit,
    }
    if extra_data:
        payload["extra_data"] = extra_data

    try:
        resp = _session.post(f"{SERVER_URL}/api/v1/measurements", json=payload, timeout=10)
        resp.raise_for_status()
        ack = resp.json()
        log.info("OK  %s = %.2f %s  (id=%s)", sensor_type, value, unit, ack.get("measurement_id", "?"))
        return True
    except requests.exceptions.SSLError as exc:
        log.error("TLS error — is ca.crt the right file? %s", exc)
    except requests.exceptions.ConnectionError as exc:
        log.error("Cannot reach server: %s", exc)
    except requests.exceptions.HTTPError as exc:
        log.error("Server %s: %s", exc.response.status_code, exc.response.text[:200])
    except Exception as exc:
        log.error("Unexpected error: %s", exc)
    return False


def send_all(readings: list[dict]) -> None:
    for r in readings:
        send_measurement(r["sensor_type"], r["value"], r["unit"], r.get("extra_data"))


# ── Main loop ──────────────────────────────────────────────────────────────────

def main() -> None:
    if API_KEY == "your-device-api-key-here":
        log.error("Set API_KEY in the configuration block at the top of this file.")
        return

    log.info("IoT client started — server=%s  interval=%ds", SERVER_URL, INTERVAL)

    consecutive_failures = 0

    while True:
        readings = read_sensors()

        if not readings:
            log.warning("No sensor readings — check sensor connections")
        else:
            results = [
                send_measurement(r["sensor_type"], r["value"], r["unit"], r.get("extra_data"))
                for r in readings
            ]
            if all(results):
                consecutive_failures = 0
            else:
                consecutive_failures += 1

        # Back off if the server keeps failing (max 5 min)
        delay = min(INTERVAL * (2 ** consecutive_failures), 300) if consecutive_failures else INTERVAL
        if consecutive_failures:
            log.warning("Backing off — next attempt in %ds", delay)

        time.sleep(delay)


if __name__ == "__main__":
    main()
