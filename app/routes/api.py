"""JSON API used by the website."""
from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from .. import config, db, rooster_archive, status

router = APIRouter(prefix="/api/v1")
_STARTED_UTC = db.now_epoch()

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


def _db_size_bytes() -> int:
    total = 0
    for suffix in ("", "-wal", "-shm"):
        p = Path(str(config.DATABASE) + suffix)
        if p.exists():
            total += p.stat().st_size
    return total


@router.get("/system_status")
def get_system_status(hours: int = Query(24, ge=1, le=168)):
    """Server health, storage, page hits, and Annie battery/temperature history."""
    now = db.now_epoch()
    today_day = datetime.now(db.LOCAL).strftime("%Y-%m-%d")
    usage = shutil.disk_usage(config.DATA_DIR)

    if config.ROOSTER_IMAGE.exists():
        st = config.ROOSTER_IMAGE.stat()
        rooster = {"exists": True, "size_bytes": st.st_size, "mtime_utc": int(st.st_mtime)}
    else:
        rooster = {"exists": False, "size_bytes": 0, "mtime_utc": None}

    with db.connect() as conn:
        counts = {
            tbl: conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
            for tbl in ("observations", "forecasts", "tide_events", "sensor_health")
        }
        last_obs = {
            r["station"]: r["ts"]
            for r in conn.execute(
                "SELECT station, MAX(ts_utc) AS ts FROM observations GROUP BY station"
            ).fetchall()
        }
        last_forecast = conn.execute("SELECT MAX(issued_utc) FROM forecasts").fetchone()[0]
        last_health_row = conn.execute(
            "SELECT ts_utc, mv, temp_f FROM sensor_health ORDER BY ts_utc DESC LIMIT 1"
        ).fetchone()
        health_rows = conn.execute(
            "SELECT ts_utc, mv, temp_f FROM sensor_health WHERE ts_utc>=? ORDER BY ts_utc",
            (now - hours * 3600,),
        ).fetchall()

        all_time_rows = conn.execute(
            "SELECT path, SUM(hits) AS total FROM page_hits GROUP BY path"
        ).fetchall()
        daily_rows = conn.execute(
            "SELECT day, path, hits FROM page_hits "
            "WHERE day >= date(?, '-29 days') ORDER BY day DESC, path",
            (today_day,),
        ).fetchall()

    all_time_map = {r["path"]: r["total"] for r in all_time_rows}
    daily_map: dict[str, dict[str, int]] = {}
    for r in daily_rows:
        bucket = daily_map.setdefault(r["day"], {"total": 0})
        bucket[r["path"]] = r["hits"]
        bucket["total"] += r["hits"]
    today_counts = daily_map.get(today_day, {"total": 0})

    latest_health = None
    if last_health_row is not None:
        latest_health = {
            "ts_utc": last_health_row["ts_utc"],
            "mv": last_health_row["mv"],
            "volts": round(last_health_row["mv"] / 1000.0, 2) if last_health_row["mv"] is not None else None,
            "temp_f": last_health_row["temp_f"],
        }

    return {
        "server": {
            "started_utc": _STARTED_UTC,
            "uptime_seconds": max(0, now - _STARTED_UTC),
            "disk": {
                "total_bytes": usage.total,
                "used_bytes": usage.used,
                "free_bytes": usage.free,
            },
            "db_bytes": _db_size_bytes(),
            "roostercam": rooster,
            "counts": counts,
            "last_updates_utc": {
                "annie_wind": last_obs.get("annie"),
                "annie_health": latest_health["ts_utc"] if latest_health else None,
                "kspb": last_obs.get("kspb"),
                "st_helens_model": last_obs.get("st_helens_model"),
                "kkls": last_obs.get("kkls"),
                "forecast": last_forecast,
            },
        },
        "hits": {
            "today_day": today_day,
            "today": today_counts,
            "all_time": {"total": sum(all_time_map.values()), **all_time_map},
            "daily": [{"day": d, **vals} for d, vals in daily_map.items()],
        },
        "sensor_health": {
            "latest": latest_health,
            "series": {
                "t": [r["ts_utc"] for r in health_rows],
                "mv": [r["mv"] for r in health_rows],
                "temp_f": [r["temp_f"] for r in health_rows],
            },
        },
    }


@router.get("/roostercam/frames")
def get_roostercam_frames():
    """List archived RoosterCam frames (oldest -> newest)."""
    return {"frames": rooster_archive.list_frames()}


@router.get("/roostercam/frames/{frame_id}")
def get_roostercam_frame(frame_id: str):
    path = rooster_archive.get_frame_path(frame_id)
    if path is None:
        raise HTTPException(404, "frame not found")
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400, immutable"})
