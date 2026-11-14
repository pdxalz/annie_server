"""Parsers are tested against real responses captured on 2026-11-13."""
from datetime import datetime, timezone

from app import db
from app.collectors import nws, openmeteo, tides


def utc(s):
    return int(datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).timestamp())


NWS_KSPB = {
    "properties": {
        "timestamp": "2026-11-13T20:50:00+00:00",
        "windDirection": {"unitCode": "wmoUnit:degree_(angle)", "value": 150},
        "windSpeed": {"unitCode": "wmoUnit:km_h-1", "value": 14.832},
        "windGust": {"unitCode": "wmoUnit:km_h-1", "value": None},
    }
}


def test_nws_parse_converts_kmh_to_mph_and_handles_null_gust():
    ts, speed, gust, direction = nws.parse_observation(NWS_KSPB)
    assert ts == utc("2026-11-13 20:50")
    assert speed == 9.2  # 14.832 km/h
    assert gust is None
    assert direction == 150


def test_nws_parse_handles_metres_per_second_and_calm():
    doc = {
        "properties": {
            "timestamp": "2026-11-13T21:00:00+00:00",
            "windDirection": {"value": None},
            "windSpeed": {"unitCode": "wmoUnit:m_s-1", "value": 5.0},
            "windGust": {"unitCode": "wmoUnit:m_s-1", "value": 9.0},
        }
    }
    _, speed, gust, direction = nws.parse_observation(doc)
    assert (speed, gust, direction) == (11.2, 20.1, None)


def test_nws_parse_returns_none_without_speed():
    assert nws.parse_observation({"properties": {"timestamp": "2026-11-13T21:00:00+00:00", "windSpeed": {"value": None}}}) is None


def test_nws_station_rows_are_deduplicated():
    ts, speed, gust, direction = nws.parse_observation(NWS_KSPB)
    assert db.insert_observation("kspb", ts, speed, gust, None, direction) is True
    assert db.insert_observation("kspb", ts, speed, gust, None, direction) is False


OPEN_METEO = {
    "hourly": {
        "time": ["2026-11-13T21:00", "2026-11-13T22:00", "2026-11-13T23:00"],
        "wind_speed_10m": [11.7, None, 9.6],
        "wind_gusts_10m": [28.6, None, 24.4],
        "wind_direction_10m": [168, None, 164],
    }
}


def test_open_meteo_parse_skips_missing_hours():
    rows = openmeteo.parse_forecast(OPEN_METEO, issued_utc=0)
    assert rows == [(utc("2026-11-13 21:00"), 11.7, 28.6, 168), (utc("2026-11-13 23:00"), 9.6, 24.4, 164)]


def test_open_meteo_retired_model_is_all_null():
    nam = {"hourly": {"time": ["2026-11-13T21:00"], "wind_speed_10m": [None], "wind_gusts_10m": [None], "wind_direction_10m": [None]}}
    assert openmeteo.parse_forecast(nam, 0) == []


def test_tide_parse():
    doc = {"predictions": [
        {"t": "2026-11-13 03:10", "v": "3.356", "type": "H"},
        {"t": "2026-11-13 11:11", "v": "-0.212", "type": "L"},
    ]}
    rows = tides.parse_hilo(doc)
    assert rows[0] == (utc("2026-11-13 03:10"), "H", 3.356)
    assert rows[1][1:] == ("L", -0.212)


def test_water_temp_parse():
    assert tides.parse_water_temp({"data": [{"t": "x", "v": "52.3"}]}) == 52.3
    assert tides.parse_water_temp({"error": {"message": "no data"}}) is None
