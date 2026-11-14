"""NOAA CO-OPS tide predictions (high/low) and water temperature."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from .. import config, db

API = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"


def parse_hilo(doc: dict) -> list[tuple[int, str, float]]:
    """NOAA returns {'predictions': [{'t': 'YYYY-MM-DD HH:MM' (GMT), 'v': '3.356', 'type': 'H'}]}."""
    rows = []
    for p in doc.get("predictions", []):
        ts = int(datetime.strptime(p["t"], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).timestamp())
        rows.append((ts, p["type"], float(p["v"])))
    return rows


def parse_water_temp(doc: dict) -> Optional[float]:
    try:
        return float(doc["data"][0]["v"])
    except (KeyError, IndexError, ValueError, TypeError):
        return None


async def collect(client: httpx.AsyncClient) -> int:
    today = datetime.now(timezone.utc).date()
    resp = await client.get(
        API,
        params={
            "begin_date": (today - timedelta(days=2)).strftime("%Y%m%d"),
            "end_date": (today + timedelta(days=4)).strftime("%Y%m%d"),
            "station": config.TIDE_STATION,
            "product": "predictions",
            "datum": "mllw",
            "time_zone": "gmt",
            "units": "english",
            "interval": "hilo",
            "format": "json",
        },
    )
    resp.raise_for_status()
    rows = parse_hilo(resp.json())
    with db.connect() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO tide_events VALUES (?, ?, ?)", rows
        )

    wt = await client.get(
        API,
        params={
            "date": "latest",
            "station": config.WATER_TEMP_STATION,
            "product": "water_temperature",
            "units": "english",
            "time_zone": "gmt",
            "format": "json",
        },
    )
    wt.raise_for_status()
    temp = parse_water_temp(wt.json())
    if temp is not None:
        db.set_meta("water_temp_f", str(temp))
    return len(rows)
