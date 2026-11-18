import json

from app import db, mqtt_sub

GOOD = json.dumps({"t": "11/13/26 18:30", "d": 310, "a": 14, "g": 22, "l": 9}).encode()


def test_wind_message_is_stored_in_both_tables():
    assert mqtt_sub.handle_wind_payload(GOOD) is True
    with db.connect() as conn:
        obs = conn.execute("SELECT * FROM observations WHERE station='annie'").fetchall()
        legacy = conn.execute("SELECT * FROM wind").fetchall()
    assert len(obs) == 1 and len(legacy) == 1
    assert (obs[0]["speed_mph"], obs[0]["gust_mph"], obs[0]["lull_mph"], obs[0]["dir_deg"]) == (14, 22, 9, 310)
    # 18:30 UTC on Nov 13 is 10:30 Pacific (PST)
    assert legacy[0]["time"] == "2026-11-13 10:30"


def test_duplicate_message_is_ignored():
    assert mqtt_sub.handle_wind_payload(GOOD) is True
    assert mqtt_sub.handle_wind_payload(GOOD) is False
    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM wind").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 1


def test_malformed_messages_do_not_raise():
    for bad in (b"not json", b"{}", b'{"t": "garbage", "d": 1, "a": 1, "g": 1, "l": 1}', b'{"t":"11/13/26 18:30","d":"x","a":1,"g":1,"l":1}'):
        assert mqtt_sub.handle_wind_payload(bad) is False
    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 0


def test_health_message_stores_latest_sample():
    payload = json.dumps({"pwr": [[4170, 54.1], [4165, 53.3]]}).encode()
    assert mqtt_sub.handle_health_payload(payload) is True
    with db.connect() as conn:
        rows = conn.execute("SELECT mv, temp_f FROM sensor_health").fetchall()
    assert len(rows) == 1
    assert (rows[0]["mv"], rows[0]["temp_f"]) == (4170, 54.1)


def test_malformed_health_messages_do_not_raise():
    for bad in (b"bad", b"{}", b'{"pwr": []}', b'{"pwr": [[0, 50.0]]}'):
        assert mqtt_sub.handle_health_payload(bad) is False
