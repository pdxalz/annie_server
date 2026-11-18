"""Routes that existed in v1 and must keep working (bookmarks, other clients)."""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import FileResponse, RedirectResponse, Response

from .. import config, db

router = APIRouter()

DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
NO_CACHE = {"Cache-Control": "no-cache, max-age=0"}


def _hours_minutes(time_str: str) -> str:
    dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
    return dt.strftime("%I:%MPM").lstrip("0") if dt.minute == 0 else dt.strftime("%I:%M").lstrip("0")


@router.get("/wind")
def wind(day: Optional[str] = None):
    """v1 format: a JSON *string* with parallel arrays (kept byte-compatible)."""
    with db.connect() as conn:
        if day is not None:
            if not DAY_RE.match(day):
                return Response("invalid day", status_code=400)
            rows = conn.execute("SELECT * FROM wind WHERE date(time) = ?", (day,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM wind").fetchall()
    return json.dumps(
        {
            "time": [_hours_minutes(r[0]) for r in rows],
            "dir": [r[1] for r in rows],
            "avg": [r[2] for r in rows],
            "gust": [r[3] for r in rows],
            "lull": [r[4] for r in rows],
        }
    )


@router.get("/first_date")
def first_date():
    with db.connect() as conn:
        row = conn.execute("SELECT date(time) FROM wind ORDER BY time ASC LIMIT 1").fetchone()
    return {"first_date": row[0]} if row else {"error": "No data found"}


@router.api_route("/roostercam", methods=["GET", "HEAD"])
def roostercam_image():
    if config.ROOSTER_IMAGE.exists():
        return FileResponse(config.ROOSTER_IMAGE, headers=NO_CACHE)
    return FileResponse(config.WEB_DIR / "img" / "404.jpg", headers=NO_CACHE)


@router.get("/roostercam.php")
def roostercam_page():
    # Many people have bookmarked this odd name; keep serving it.
    db.record_page_hit("/roostercam.php")
    return FileResponse(config.WEB_DIR / "roostercam.html", headers=NO_CACHE)


@router.get("/")
def index():
    db.record_page_hit("/")
    return FileResponse(config.WEB_DIR / "index.html", headers=NO_CACHE)


@router.get("/status")
def status_page():
    return FileResponse(config.WEB_DIR / "status.html", headers=NO_CACHE)


# v1 pages that no longer exist as separate pages: send people to the main page.
@router.get("/index.html")
@router.get("/history.html")
@router.get("/images.html")
def retired_pages():
    return RedirectResponse("/", status_code=301)
