"""SQLite access, schema and the one-time backfill from the legacy ``wind`` table."""
from __future__ import annotations

import logging
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime
from typing import Iterator, Optional
from zoneinfo import ZoneInfo

from . import config

log = logging.getLogger("db")
LOCAL = ZoneInfo(config.LOCAL_TZ)
UTC = ZoneInfo("UTC")

SCHEMA = """
CREATE TABLE IF NOT EXISTS wind (            -- legacy table, kept for rollback to v1
  time STR, dir INT, avg INT, gust INT, lull INT
);
CREATE TABLE IF NOT EXISTS observations (
  station   TEXT    NOT NULL,
  ts_utc    INTEGER NOT NULL,
  speed_mph REAL, gust_mph REAL, lull_mph REAL, dir_deg INTEGER,
  PRIMARY KEY (station, ts_utc)
) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS forecasts (
  model TEXT NOT NULL, issued_utc INTEGER NOT NULL, valid_utc INTEGER NOT NULL,
  speed_mph REAL, gust_mph REAL, dir_deg INTEGER,
  PRIMARY KEY (model, issued_utc, valid_utc)
) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS tide_events (
  ts_utc INTEGER PRIMARY KEY, kind TEXT NOT NULL, height_ft REAL
);
CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY, value TEXT, updated_utc INTEGER
);
"""


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(str(config.DATABASE), timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(SCHEMA)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_wind_time ON wind(time)")
    backfill_from_legacy()


# ---------------------------------------------------------------- time helpers
def local_to_utc_epoch(local_str: str, prev_epoch: Optional[int] = None) -> int:
    """Convert a legacy Pacific 'YYYY-MM-DD HH:MM' string to a UTC epoch.

    At the autumn DST change one local hour happens twice. Rows are processed in
    insertion order, so if the result would go backwards in time we assume it is
    the second pass through that hour (fold=1).
    """
    naive = datetime.strptime(local_str, "%Y-%m-%d %H:%M")
    ts = int(naive.replace(tzinfo=LOCAL, fold=0).timestamp())
    if prev_epoch is not None and ts <= prev_epoch:
        ts_fold = int(naive.replace(tzinfo=LOCAL, fold=1).timestamp())
        if ts_fold > prev_epoch:
            ts = ts_fold
    return ts


def local_day_bounds(day: str) -> tuple[int, int]:
    """UTC epoch [start, end) of a Pacific calendar day given as 'YYYY-MM-DD'."""
    start = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=LOCAL)
    # Compute end via the next calendar day so 23/25-hour DST days are right.
    nxt = datetime.fromordinal(start.toordinal() + 1).replace(tzinfo=LOCAL)
    return int(start.timestamp()), int(nxt.timestamp())


def now_epoch() -> int:
    return int(time.time())


# ------------------------------------------------------------------- backfill
def backfill_from_legacy() -> int:
    """Copy legacy ``wind`` rows into ``observations`` (idempotent)."""
    with connect() as conn:
        if conn.execute("SELECT 1 FROM meta WHERE key='backfill_v1_done'").fetchone():
            return 0
        legacy = conn.execute("SELECT COUNT(*) FROM wind").fetchone()[0]
        done = conn.execute(
            "SELECT COUNT(*) FROM observations WHERE station='annie'"
        ).fetchone()[0]
        if legacy == 0 or done >= legacy:
            return 0
        inserted = 0
        prev: Optional[int] = None
        skipped = 0
        for row in conn.execute("SELECT time, dir, avg, gust, lull FROM wind ORDER BY rowid"):
            try:
                ts = local_to_utc_epoch(row["time"], prev)
            except (ValueError, TypeError):
                skipped += 1
                continue
            prev = ts
            cur = conn.execute(
                "INSERT OR IGNORE INTO observations VALUES ('annie', ?, ?, ?, ?, ?)",
                (ts, row["avg"], row["gust"], row["lull"], row["dir"]),
            )
            inserted += cur.rowcount
        conn.execute(
            "INSERT INTO meta VALUES ('backfill_v1_done', '1', ?) "
            "ON CONFLICT(key) DO UPDATE SET value='1', updated_utc=excluded.updated_utc",
            (now_epoch(),),
        )
        log.info("Backfill: %d inserted, %d unparsable rows skipped", inserted, skipped)
        return inserted


# --------------------------------------------------------------------- writes
def insert_observation(
    station: str,
    ts_utc: int,
    speed: Optional[float],
    gust: Optional[float],
    lull: Optional[float],
    direction: Optional[int],
) -> bool:
    with connect() as conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO observations VALUES (?, ?, ?, ?, ?, ?)",
            (station, ts_utc, speed, gust, lull, direction),
        )
        return cur.rowcount > 0


def insert_legacy_wind(local_time: str, direction: int, avg: int, gust: int, lull: int) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO wind (time, dir, avg, gust, lull) VALUES (?, ?, ?, ?, ?)",
            (local_time, direction, avg, gust, lull),
        )


def set_meta(key: str, value: str) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO meta VALUES (?, ?, ?) ON CONFLICT(key) DO UPDATE "
            "SET value=excluded.value, updated_utc=excluded.updated_utc",
            (key, value, now_epoch()),
        )
