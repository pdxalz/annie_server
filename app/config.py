"""Runtime configuration, read once from environment variables."""
from __future__ import annotations

import os
from pathlib import Path

# Persistent data (bind-mounted outside the container)
DATA_DIR = Path(os.environ.get("DATA_DIR", "/winddata"))
DATABASE = DATA_DIR / "test.db"
STATUS_FILE = DATA_DIR / "site_status.json"

# Stardot camera images, uploaded by the vsftpd container
ROOSTER_DIR = Path(os.environ.get("ROOSTER_DIR", "/rooster"))
ROOSTER_IMAGE = ROOSTER_DIR / "camera0.jpg"

# Static site
WEB_DIR = Path(os.environ.get("WEB_DIR", Path(__file__).resolve().parent.parent / "web"))

# MQTT (Annie)
MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
MQTT_USERNAME = os.environ.get("MQTT_USRNM")
MQTT_PASSWORD = os.environ.get("MQTT_PSWD")
MQTT_ENABLED = os.environ.get("MQTT_ENABLED", "1") != "0"
TOPIC_WIND = "zimbuktu/wind"

# Background collectors
COLLECTORS_ENABLED = os.environ.get("COLLECTORS_ENABLED", "1") != "0"
# NWS asks API users to identify themselves with a contact address.
NWS_USER_AGENT = os.environ.get("NWS_USER_AGENT", "(sauviewind.net, pdxalz@gmail.com)")

LOCAL_TZ = "America/Los_Angeles"

# Sauvie Island (forecast point) and NOAA stations
SAUVIE_LAT, SAUVIE_LON = 45.723, -122.816
TIDE_STATION = "9440171"
WATER_TEMP_STATION = "9440422"

# station id -> (label, kind). 'annie' is our own sensor, the rest are NWS airports.
STATIONS = {
    "annie": {"label": "Sauvie (Annie)", "source": "sensor", "stale_minutes": 30},
    "kspb": {"label": "St. Helens", "source": "nws", "stale_minutes": 120},
    "kkls": {"label": "Longview", "source": "nws", "stale_minutes": 120},
}
