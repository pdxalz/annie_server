"""Short-term model forecasts from Open-Meteo for the Sauvie Island location.

Verified 2026-11-13: ``ncep_hrrr_conus`` (hourly, ~18 h) and ``ncep_rrfs_conus`` return data;
``ncep_nam_conus`` now returns only nulls (retired), so NAM is not used.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import httpx

from .. import config, db

URL = "https://api.open-meteo.com/v1/forecast"
MODELS = {
    "hrrr": "ncep_hrrr_conus",   # micro term: hourly refresh
    "rrfs": "ncep_rrfs_conus",   # short term: NOAA's successor to NAM
}


def parse_forecast(doc: dict, issued_utc: int) -> list[tuple[int, float, float, int]]:
    """Return [(valid_utc, speed, gust, dir)] skipping hours with missing speed."""
    hourly = doc.get("hourly", {})
    rows = []
    for t, spd, gst, drc in zip(
        hourly.get("time", []),
        hourly.get("wind_speed_10m", []),
        hourly.get("wind_gusts_10m", []),
        hourly.get("wind_direction_10m", []),
    ):
        if spd is None:
            continue
        valid = int(datetime.fromisoformat(t).replace(tzinfo=timezone.utc).timestamp())
        rows.append((valid, spd, gst, drc))
    return rows


async def collect(client: httpx.AsyncClient) -> int:
    issued = db.now_epoch() // 3600 * 3600  # one forecast vintage per hour
    stored = 0
    for name, model in MODELS.items():
        resp = await client.get(
            URL,
            params={
                "latitude": config.SAUVIE_LAT,
                "longitude": config.SAUVIE_LON,
                "hourly": "wind_speed_10m,wind_gusts_10m,wind_direction_10m",
                "wind_speed_unit": "mph",
                "forecast_hours": 12,
                "models": model,
                "timezone": "GMT",
            },
        )
        resp.raise_for_status()
        rows = parse_forecast(resp.json(), issued)
        with db.connect() as conn:
            for valid, spd, gst, drc in rows:
                cur = conn.execute(
                    "INSERT OR IGNORE INTO forecasts VALUES (?, ?, ?, ?, ?, ?)",
                    (name, issued, valid, spd, gst, drc),
                )
                stored += cur.rowcount
    return stored


def parse_current(doc: dict) -> Optional[tuple[int, float, Optional[float], Optional[int]]]:
    """Return (ts_utc, speed_mph, gust_mph, dir_deg) from Open-Meteo's ``current`` block."""
    cur = doc.get("current") or {}
    speed = cur.get("wind_speed_10m")
    if speed is None or not cur.get("time"):
        return None
    ts = int(datetime.fromisoformat(cur["time"]).replace(tzinfo=timezone.utc).timestamp())
    gust = cur.get("wind_gusts_10m")
    direction = cur.get("wind_direction_10m")
    return ts, round(float(speed), 1), None if gust is None else round(float(gust), 1), None if direction is None else int(round(direction))


async def collect_st_helens_current(client: httpx.AsyncClient) -> int:
    """Fetch Open-Meteo's current-conditions model point for the St. Helens waterfront."""
    resp = await client.get(
        URL,
        params={
            "latitude": config.ST_HELENS_LAT,
            "longitude": config.ST_HELENS_LON,
            "current": "wind_speed_10m,wind_gusts_10m,wind_direction_10m",
            "wind_speed_unit": "mph",
            "timezone": "GMT",
        },
    )
    resp.raise_for_status()
    parsed = parse_current(resp.json())
    if parsed is None:
        return 0
    ts, speed, gust, direction = parsed
    return 1 if db.insert_observation("st_helens_model", ts, speed, gust, None, direction) else 0
