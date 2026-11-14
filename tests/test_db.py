from datetime import datetime, timezone

from app import db


def utc(s):
    return int(datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).timestamp())


def test_local_to_utc_standard_and_daylight():
    # PST (UTC-8) in winter, PDT (UTC-7) in summer
    assert db.local_to_utc_epoch("2026-01-15 12:00") == utc("2026-01-15 20:00")
    assert db.local_to_utc_epoch("2026-07-15 12:00") == utc("2026-07-15 19:00")


def test_fall_back_hour_is_not_duplicated():
    # 2026-11-01: 01:00-01:59 Pacific happens twice. Rows arrive in order.
    first = db.local_to_utc_epoch("2026-11-01 01:30")
    assert first == utc("2026-11-01 08:30")  # PDT, first pass
    second = db.local_to_utc_epoch("2026-11-01 01:30", prev_epoch=first)
    assert second == utc("2026-11-01 09:30")  # PST, second pass
    # An ordinary later row is unaffected
    assert db.local_to_utc_epoch("2026-11-01 02:00", prev_epoch=second) == utc("2026-11-01 10:00")


def test_backfill_converts_rows_and_is_idempotent():
    with db.connect() as conn:
        conn.executemany(
            "INSERT INTO wind VALUES (?, ?, ?, ?, ?)",
            [
                ("2026-11-01 01:20", 180, 10, 15, 6),
                ("2026-11-01 01:40", 190, 11, 16, 7),
                ("2026-11-01 01:20", 200, 12, 17, 8),  # second pass through the hour
                ("not a date", 0, 0, 0, 0),
            ],
        )
    assert db.backfill_from_legacy() == 3
    assert db.backfill_from_legacy() == 0
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT ts_utc, speed_mph, dir_deg FROM observations WHERE station='annie' ORDER BY ts_utc"
        ).fetchall()
    assert [r["ts_utc"] for r in rows] == [
        utc("2026-11-01 08:20"),
        utc("2026-11-01 08:40"),
        utc("2026-11-01 09:20"),
    ]
    assert rows[2]["speed_mph"] == 12 and rows[2]["dir_deg"] == 200


def test_local_day_bounds_handles_dst_length():
    s, e = db.local_day_bounds("2026-03-08")  # spring forward: 23 hours
    assert (e - s) == 23 * 3600
    s, e = db.local_day_bounds("2026-11-01")  # fall back: 25 hours
    assert (e - s) == 25 * 3600
