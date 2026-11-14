# Sauvie Island Wind (sauviewind.net) server

FastAPI app that receives Annie's wind readings over MQTT, collects nearby NWS airport
observations, model forecasts and NOAA tides, stores everything in SQLite, and serves the website.

## Layout

| Path | Purpose |
|---|---|
| `app/main.py` | App entry point (starts MQTT subscriber + collectors) |
| `app/mqtt_sub.py` | Stores Annie's readings (`zimbuktu/wind`) |
| `app/collectors/` | NWS (St. Helens KSPB, Longview KKLS), Open-Meteo forecasts (HRRR, RRFS), NOAA tides + water temp |
| `app/routes/api.py` | JSON API under `/api/v1/` |
| `app/routes/legacy.py` | v1 routes kept for old bookmarks (`/wind`, `/roostercam.php`, ...) |
| `web/` | The website (plain HTML/CSS/JS, Chart.js bundled in `web/vendor/`) |
| `tests/` | `pytest` suite |
| `scripts/` | `mock_annie.py` (fake sensor), `seed_dev_data.py` (synthetic data) |

The app must run with **one** worker (the Dockerfile does this).

## Updating the production server

```bash
cd ~/annie_server && git pull
cd ~ && docker compose up -d --build anniedock
docker compose logs --tail=30 anniedock
```

The existing `~/docker-compose.yml` does not need to change.

## Maintenance / off-season banner

Create or edit `~/annie_server/winddata/site_status.json` on the server. Changes show up on the
next page refresh, no restart needed.

```json
{ "banner": { "enabled": true, "level": "warning", "message": "Annie is down for the season. See you in spring!" } }
```

* `level`: `info` (blue), `warning` (yellow) or `error` (red)
* Set `"enabled": false` (or delete the file) to remove the banner.
* Separately, the page shows "Annie is offline" automatically if no reading arrived for 30 minutes.
* `winddata/site_status.example.json` is a template.

## Local development

```bash
python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest

# Full stack with a throwaway broker, then fake an Annie:
docker compose up --build
python scripts/mock_annie.py
# http://localhost:8000

# Or look at the site on synthetic history without any broker:
DATA_DIR=./winddata-dev ROOSTER_DIR=./dev/rooster MQTT_ENABLED=0 COLLECTORS_ENABLED=0 \
  python scripts/seed_dev_data.py
DATA_DIR=./winddata-dev ROOSTER_DIR=./dev/rooster MQTT_ENABLED=0 COLLECTORS_ENABLED=0 \
  python -m uvicorn app.main:app --port 8000
```

## Configuration (`.env`, see `.env.example`)

`MQTT_HOST`, `MQTT_PORT`, `MQTT_USRNM`, `MQTT_PSWD`, `NWS_USER_AGENT`, `MQTT_ENABLED`, `COLLECTORS_ENABLED`.
Old variables such as `SERVER_URL` are no longer used and are ignored.

## Data

* `winddata/test.db` (SQLite). The legacy `wind` table is still written, so you can roll back to v1
  (`git checkout v1-final`) without losing readings. New tables: `observations`, `forecasts`,
  `tide_events`, `meta`.
* On first start the old `wind` rows are copied into `observations` (UTC) automatically.
* **Back up `test.db` before the first deploy of v2.**

## Notes on forecast models

Verified 2026-11-13 against Open-Meteo: `ncep_hrrr_conus` and `ncep_rrfs_conus` return data;
`ncep_nam_conus` returns only nulls (retired), so NAM is not used.
