import json
import time

from app import config, db


def seed_annie(minutes_ago_list):
    now = int(time.time())
    for i, m in enumerate(minutes_ago_list):
        db.insert_observation("annie", now - m * 60, 10 + i, 20 + i, 5, 270)


def test_current_reports_age_and_staleness(client):
    seed_annie([5])
    db.insert_observation("kspb", int(time.time()) - 300 * 60, 8, None, None, 200)
    data = client.get("/api/v1/current").json()["stations"]
    assert data["annie"]["available"] and not data["annie"]["stale"]
    assert data["annie"]["age_minutes"] in (5, 4)
    assert data["kspb"]["stale"]  # 5 hours old
    assert data["kkls"]["available"] is False


def test_series_hours_window(client):
    seed_annie([10, 120, 400])  # 400 min ago is outside 3 h but inside 12 h
    s3 = client.get("/api/v1/series?hours=3&stations=annie").json()["stations"]["annie"]
    s12 = client.get("/api/v1/series?hours=12&stations=annie").json()["stations"]["annie"]
    assert len(s3["t"]) == 2
    assert len(s12["t"]) == 3
    assert s3["t"] == sorted(s3["t"])


def test_series_by_date_uses_pacific_day(client):
    # 2026-07-01 23:30 Pacific (PDT) == 2026-07-02 06:30 UTC: belongs to July 1
    ts = db.local_to_utc_epoch("2026-07-01 23:30")
    db.insert_observation("annie", ts, 12, 18, 6, 300)
    on_day = client.get("/api/v1/series?date=2026-07-01&stations=annie").json()["stations"]["annie"]
    next_day = client.get("/api/v1/series?date=2026-07-02&stations=annie").json()["stations"]["annie"]
    assert on_day["speed"] == [12] and next_day["speed"] == []


def test_series_validation(client):
    assert client.get("/api/v1/series?hours=5").status_code == 400
    assert client.get("/api/v1/series").status_code == 400
    assert client.get("/api/v1/series?date=../../etc/passwd").status_code == 400
    assert client.get("/api/v1/series?hours=3&stations=bogus").status_code == 400


def test_first_date(client):
    assert client.get("/api/v1/first_date").json() == {"first_date": None}
    db.insert_observation("annie", db.local_to_utc_epoch("2025-05-04 09:00"), 1, 2, 0, 90)
    assert client.get("/api/v1/first_date").json() == {"first_date": "2025-05-04"}


def test_forecast_returns_latest_vintage_only(client):
    now = int(time.time())
    hour = now // 3600 * 3600
    with db.connect() as conn:
        conn.executemany(
            "INSERT INTO forecasts VALUES (?, ?, ?, ?, ?, ?)",
            [
                ("hrrr", hour - 3600, hour + 3600, 5, 9, 200),   # old vintage
                ("hrrr", hour, hour + 3600, 12, 20, 270),        # latest vintage
                ("hrrr", hour, hour + 7200, 14, 22, 275),
                ("rrfs", hour, hour + 3600, 13, 21, 260),
            ],
        )
    models = client.get("/api/v1/forecast?hours=6").json()["models"]
    assert [p["speed"] for p in models["hrrr"]["points"]] == [12, 14]
    assert models["rrfs"]["points"][0]["gust"] == 21


def test_tides_include_neighbouring_events(client):
    now = int(time.time())
    with db.connect() as conn:
        conn.executemany(
            "INSERT INTO tide_events VALUES (?, ?, ?)",
            [(now - 20 * 3600, "L", 0.1), (now - 2 * 3600, "H", 3.0), (now + 4 * 3600, "L", 0.5), (now + 20 * 3600, "H", 3.2)],
        )
    events = client.get("/api/v1/tides?hours=6").json()["events"]
    # window is the last 6 h: one event before it, one inside, and only the NEXT one after it
    assert [e["kind"] for e in events] == ["L", "H", "L"]
    assert len(events) == 3


class TestStatusBanner:
    def write(self, text):
        config.STATUS_FILE.write_text(text, encoding="utf-8")

    def test_missing_file_means_no_banner(self, client):
        assert client.get("/api/v1/status").json()["banner"]["enabled"] is False

    def test_banner_on_and_off_without_restart(self, client):
        self.write(json.dumps({"banner": {"enabled": True, "level": "warning", "message": "Down for the season"}}))
        b = client.get("/api/v1/status").json()["banner"]
        assert b == {"enabled": True, "level": "warning", "message": "Down for the season"}
        self.write(json.dumps({"banner": {"enabled": False, "message": "Down for the season"}}))
        assert client.get("/api/v1/status").json()["banner"]["enabled"] is False

    def test_malformed_file_is_safe(self, client):
        self.write("{ this is not json")
        assert client.get("/api/v1/status").json()["banner"]["enabled"] is False

    def test_empty_message_never_shows(self, client):
        self.write(json.dumps({"banner": {"enabled": True, "message": "  "}}))
        assert client.get("/api/v1/status").json()["banner"]["enabled"] is False

    def test_unknown_level_falls_back(self, client):
        self.write(json.dumps({"banner": {"enabled": True, "level": "<script>", "message": "x"}}))
        assert client.get("/api/v1/status").json()["banner"]["level"] == "warning"


def test_sensor_offline_flag(client):
    assert client.get("/api/v1/status").json()["sensor"]["offline"] is True  # no data at all
    seed_annie([3])
    assert client.get("/api/v1/status").json()["sensor"]["offline"] is False
    with db.connect() as conn:
        conn.execute("DELETE FROM observations")
    seed_annie([90])
    assert client.get("/api/v1/status").json()["sensor"]["offline"] is True


# ------------------------------------------------------------- legacy + pages
def test_legacy_wind_route_keeps_v1_shape(client):
    db.insert_legacy_wind("2026-07-01 09:00", 270, 10, 15, 6)
    db.insert_legacy_wind("2026-07-01 09:10", 280, 11, 16, 7)
    body = client.get("/wind?day=2026-07-01").json()  # v1 returns a JSON *string*
    data = json.loads(body)
    assert data["avg"] == [10, 11] and data["gust"] == [15, 16] and data["dir"] == [270, 280]
    assert client.get("/first_date").json() == {"first_date": "2026-07-01"}


def test_roostercam_routes(client):
    page = client.get("/roostercam.php")
    assert page.status_code == 200 and "text/html" in page.headers["content-type"]
    assert client.get("/roostercam").status_code == 200  # falls back to the 404 image
    (config.ROOSTER_DIR / "camera0.jpg").write_bytes(b"\xff\xd8fake")
    assert client.get("/roostercam").content == b"\xff\xd8fake"
    assert client.get("/roostercam").headers["cache-control"].startswith("no-cache")


def test_main_page_and_retired_pages(client):
    assert client.get("/").status_code == 200
    for old in ("/history.html", "/images.html", "/index.html"):
        r = client.get(old, follow_redirects=False)
        assert r.status_code == 301 and r.headers["location"] == "/"


def test_retired_image_routes_are_gone(client):
    for path in ("/delete_image?filename=x", "/take_image?size=small", "/list_images", "/images/x.jpg"):
        assert client.get(path).status_code == 404


def test_database_file_is_not_downloadable(client):
    for path in ("/static/../test.db", "/static/%2e%2e/test.db", "/rooster/../test.db", "/test.db"):
        assert client.get(path).status_code in (404, 400)
