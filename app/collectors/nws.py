"""National Weather Service airport observations (real sensors)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

import httpx

from .. import config, db

URL = "https://api.weather.gov/stations/{}/observations/latest"
# Free-text station id -> our station key
NWS_STATIONS = {"kspb": "KSPB", "kkls": "KKLS"}

_TO_MPH = {
    "wmoUnit:km_h-1": 0.621371,
    "wmoUnit:m_s-1": 2.236936,
}


def _mph(quantity: Optional[dict]) -> Optional[float]:
    if not quantity or quantity.get("value") is None:
        return None
    factor = _TO_MPH.get(quantity.get("unitCode"))
    if factor is None:
        return None
    return round(quantity["value"] * factor, 1)


def parse_observation(doc: dict) -> Optional[tuple[int, Optional[float], Optional[float], Optional[int]]]:
    """Return (ts_utc, speed_mph, gust_mph, dir_deg) or None if there is no wind speed."""
    props = doc.get("properties", {})
    speed = _mph(props.get("windSpeed"))
    if speed is None or not props.get("timestamp"):
        return None
    ts = int(datetime.fromisoformat(props["timestamp"]).timestamp())
    gust = _mph(props.get("windGust"))
    direction = (props.get("windDirection") or {}).get("value")
    return ts, speed, gust, None if direction is None else int(round(direction))


async def collect(client: httpx.AsyncClient) -> int:
    """Fetch the latest observation for each station. Returns number of new rows."""
    new = 0
    for key, icao in NWS_STATIONS.items():
        resp = await client.get(
            URL.format(icao),
            headers={"User-Agent": config.NWS_USER_AGENT, "Accept": "application/geo+json"},
        )
        resp.raise_for_status()
        parsed = parse_observation(resp.json())
        if parsed is None:
            continue
        ts, speed, gust, direction = parsed
        # Duplicate timestamps are ignored by the primary key.
        if db.insert_observation(key, ts, speed, gust, None, direction):
            new += 1
    return new
