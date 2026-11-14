"""Maintenance / off-season banner, controlled by a JSON file you edit on the server."""
from __future__ import annotations

import json
import logging
from typing import Any

from . import config

log = logging.getLogger("status")

LEVELS = {"info", "warning", "error"}
EMPTY = {"enabled": False, "level": "info", "message": ""}


def read_banner() -> dict[str, Any]:
    """Read ``site_status.json`` on every call so edits apply without a restart."""
    try:
        raw = json.loads(config.STATUS_FILE.read_text(encoding="utf-8"))
        banner = raw.get("banner", {})
        message = str(banner.get("message", "")).strip()
        level = banner.get("level", "warning")
        return {
            "enabled": bool(banner.get("enabled")) and bool(message),
            "level": level if level in LEVELS else "warning",
            "message": message,
        }
    except FileNotFoundError:
        return dict(EMPTY)
    except (ValueError, AttributeError, OSError) as exc:
        log.error("Bad %s: %s", config.STATUS_FILE, exc)
        return dict(EMPTY)
