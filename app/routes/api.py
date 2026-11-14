"""JSON API used by the website."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from .. import config, db, status

router = APIRouter(prefix="/api/v1")

DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ALLOWED_HOURS = (3, 6, 12, 24)


def _station_list(stations: str) -> list[str]:
    keys = [s.strip().lower() for s in stations.split(",") if s.strip()]
    bad = [k for k in keys if k not in config.STATIONS]
    if bad:
        raise HTTPException(400, f"unknown station(s): {', '.join(bad)}")
    return keys


def _window(hours: Optional[int], date: Optional[str]) -> tuple[int, int]:
    """Resolve the query window to UTC epoch seconds [start, end)."""
    if date is not None:
        if not DAY_RE.match(date):
            raise HTTPException(400, "date must be YYYY-MM-DD")
        try:
            return db.local_day_bounds(date)
        except ValueError:
            raise HTTPException(400, "invalid date")
    if hours not in ALLOWED_HOURS:
        raise HTTPException(400, f"hours must be one of {ALLOWED_HOURS}")
    now = db.now_epoch()
    return now - hours * 3600, now + 1


@router.get("/status")
def get_status():
    banner = status.read_banner()
    with db.connect() as conn:
        row = conn.execute(
            "SELECT MAX(ts_utc) AS ts FROM observations WHERE station='annie'"
        ).fetchone()
    last = row["ts"]
    age = None if last is None else (db.now_epoch() - last) // 60
    limit = config.STATIONS["annie"]["stale_minutes"]
    return {
        "banner": banner,
        "sensor": {
            "last_reading_utc": last,
            "age_minutes": age,
            "offline": last is None or age > limit,
        },
    }


@router.get("/current")
def get_current():
    now = db.now_epoch()
    out = {}
    with db.connect() as conn:
        for key, meta in config.STATIONS.items():
            row = conn.execute(
                "SELECT * FROM observations WHERE station=? ORDER BY ts_utc DESC LIMIT 1", (key,)
            ).fetchone()
            if row is None:
                out[key] = {"label": meta["label"], "source": meta["source"], "available": False}
                continue
            age = (now - row["ts_utc"]) // 60
            out[key] = {
                "label": meta["label"],
                "source": meta["source"],
                "available": True,
                "ts_utc": row["ts_utc"],
                "age_minutes": age,
                "stale": age > meta["stale_minutes"],
                "speed": row["speed_mph"],
                "gust": row["gust_mph"],
                "lull": row["lull_mph"],
                "dir": row["dir_deg"],
            }
        wt = conn.execute("SELECT value, updated_utc FROM meta WHERE key='water_temp_f'").fetchone()
    return {
        "stations": out,
        "water_temp_f": float(wt["value"]) if wt else None,
    }


@router.get("/series")
def get_series(
    hours: Optional[int] = Query(None, description="3, 6, 12 or 24"),
    date: Optional[str] = Query(None, description="Pacific day, YYYY-MM-DD"),
    stations: str = "annie,kspb,kkls",
):
    keys = _station_list(stations)
    start, end = _window(hours, date)
    result = {}
    with db.connect() as conn:
        for key in keys:
            rows = conn.execute(
                "SELECT ts_utc, speed_mph, gust_mph, lull_mph, dir_deg FROM observations "
                "WHERE station=? AND ts_utc>=? AND ts_utc<? ORDER BY ts_utc",
                (key, start, end),
            ).fetchall()
            result[key] = {
                "t": [r["ts_utc"] for r in rows],
                "speed": [r["speed_mph"] for r in rows],
                "gust": [r["gust_mph"] for r in rows],
                "lull": [r["lull_mph"] for r in rows],
                "dir": [r["dir_deg"] for r in rows],
            }
    return {"start": start, "end": end, "stations": result}


@router.get("/first_date")
def get_first_date():
    with db.connect() as conn:
        row = conn.execute(
            "SELECT MIN(ts_utc) AS ts FROM observations WHERE station='annie'"
        ).fetchone()
    if row["ts"] is None:
        return {"first_date": None}
    day = datetime.fromtimestamp(row["ts"], db.LOCAL).strftime("%Y-%m-%d")
    return {"first_date": day}


@router.get("/forecast")
def get_forecast(hours: int = Query(8, ge=1, le=12)):
    """Latest forecast vintage of each model, from the current hour onward."""
    now = db.now_epoch()
    out = {}
    with db.connect() as conn:
        for model in ("hrrr", "rrfs"):
            issued = conn.execute(
                "SELECT MAX(issued_utc) AS i FROM forecasts WHERE model=?", (model,)
            ).fetchone()["i"]
            if issued is None:
                out[model] = {"issued_utc": None, "points": []}
                continue
            rows = conn.execute(
                "SELECT valid_utc, speed_mph, gust_mph, dir_deg FROM forecasts "
                "WHERE model=? AND issued_utc=? AND valid_utc>=? AND valid_utc<? ORDER BY valid_utc",
                (model, issued, now - 3600, now + hours * 3600),
            ).fetchall()
            out[model] = {
                "issued_utc": issued,
                "points": [
                    {"t": r["valid_utc"], "speed": r["speed_mph"], "gust": r["gust_mph"], "dir": r["dir_deg"]}
                    for r in rows
                ],
            }
    return {"models": out}


@router.get("/tides")
def get_tides(
    hours: Optional[int] = Query(None),
    date: Optional[str] = Query(None),
):
    """High/low events covering the window, plus the neighbours on each side so the
    chart can shade flood/ebb right up to the edges."""
    start, end = _window(hours, date)
    with db.connect() as conn:
        before = conn.execute(
            "SELECT ts_utc, kind, height_ft FROM tide_events WHERE ts_utc<? ORDER BY ts_utc DESC LIMIT 1",
            (start,),
        ).fetchall()
        inside = conn.execute(
            "SELECT ts_utc, kind, height_ft FROM tide_events WHERE ts_utc>=? AND ts_utc<? ORDER BY ts_utc",
            (start, end),
        ).fetchall()
        after = conn.execute(
            "SELECT ts_utc, kind, height_ft FROM tide_events WHERE ts_utc>=? ORDER BY ts_utc LIMIT 1",
            (end,),
        ).fetchall()
    events = [
        {"t": r["ts_utc"], "kind": r["kind"], "height": r["height_ft"]}
        for r in (*before, *inside, *after)
    ]
    return {"start": start, "end": end, "events": events}
