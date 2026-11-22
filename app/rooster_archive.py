"""Rolling archive of unique RoosterCam JPEG frames."""
from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import Optional

from . import config

log = logging.getLogger("rooster_archive")

FRAME_RE = re.compile(r"^(\d+)\.jpg$")

_last_digest: Optional[bytes] = None
_last_archive_dir: Optional[Path] = None


def _is_complete_jpeg(data: bytes) -> bool:
    """True when data starts with SOI (FFD8) and contains EOI (FFD9) near the end."""
    return len(data) >= 4 and data[:2] == b"\xff\xd8" and b"\xff\xd9" in data[-16:]


def _sorted_frame_files() -> list[Path]:
    if not config.ROOSTER_ARCHIVE_DIR.exists():
        return []
    files = [p for p in config.ROOSTER_ARCHIVE_DIR.iterdir() if p.is_file() and FRAME_RE.match(p.name)]
    files.sort(key=lambda p: int(p.stem))
    return files


def snapshot_if_new() -> bool:
    """Copy camera0.jpg into the rolling archive if it is a complete, new JPEG."""
    global _last_digest, _last_archive_dir

    if not config.ROOSTER_IMAGE.exists():
        return False

    try:
        st = config.ROOSTER_IMAGE.stat()
        data = config.ROOSTER_IMAGE.read_bytes()
    except OSError:
        return False

    if not _is_complete_jpeg(data):
        return False

    digest = hashlib.sha256(data).digest()
    archive_dir = config.ROOSTER_ARCHIVE_DIR
    archive_dir.mkdir(parents=True, exist_ok=True)

    existing = _sorted_frame_files()
    if _last_archive_dir != archive_dir:
        _last_archive_dir = archive_dir
        _last_digest = hashlib.sha256(existing[-1].read_bytes()).digest() if existing else None

    if digest == _last_digest:
        return False

    ts = int(st.st_mtime)
    if existing:
        latest_ts = int(existing[-1].stem)
        if ts <= latest_ts:
            ts = latest_ts + 1

    dest = archive_dir / f"{ts}.jpg"
    tmp = archive_dir / f".{ts}.tmp"
    tmp.write_bytes(data)
    tmp.replace(dest)
    _last_digest = digest

    existing.append(dest)
    overflow = len(existing) - config.ROOSTER_ARCHIVE_MAX
    for old in existing[: max(0, overflow)]:
        try:
            old.unlink()
        except OSError:
            pass
    return True


def list_frames() -> list[dict]:
    """Return archived frames sorted oldest -> newest."""
    try:
        snapshot_if_new()
    except Exception:
        log.exception("Failed to snapshot RoosterCam image")
    return [
        {"id": p.name, "t": int(p.stem), "url": f"/api/v1/roostercam/frames/{p.name}"}
        for p in _sorted_frame_files()
    ]


def get_frame_path(frame_id: str) -> Optional[Path]:
    if not FRAME_RE.match(frame_id):
        return None
    p = config.ROOSTER_ARCHIVE_DIR / frame_id
    return p if p.is_file() else None


async def collect(_client=None) -> int:
    return 1 if snapshot_if_new() else 0
