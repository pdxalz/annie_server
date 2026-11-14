"""Subscribes to Annie's wind messages and stores them."""
from __future__ import annotations

import json
import logging
import random
from datetime import datetime
from typing import Optional

from . import config, db

log = logging.getLogger("mqtt")


def handle_wind_payload(payload: bytes) -> bool:
    """Parse one Annie message and store it. Returns True if a new row was stored.

    Payload (UTC time): {"t": "11/13/26 18:30", "d": 310, "a": 14, "g": 22, "l": 9}
    """
    try:
        msg = json.loads(payload)
        when = datetime.strptime(msg["t"], "%m/%d/%y %H:%M").replace(tzinfo=db.UTC)
        direction, avg, gust, lull = (int(msg[k]) for k in ("d", "a", "g", "l"))
    except (ValueError, KeyError, TypeError) as exc:
        log.warning("Ignoring malformed wind message %r: %s", payload[:200], exc)
        return False

    ts = int(when.timestamp())
    stored = db.insert_observation("annie", ts, avg, gust, lull, direction)
    if stored:
        # Dual write: keep the v1 table current so rolling back loses nothing.
        local = when.astimezone(db.LOCAL).strftime("%Y-%m-%d %H:%M")
        db.insert_legacy_wind(local, direction, avg, gust, lull)
        log.info("Annie %s: %s g%s lull %s dir %s", local, avg, gust, lull, direction)
    return stored


_client = None


def start() -> Optional[object]:
    """Connect in a background thread (auto-reconnects if the broker is down)."""
    global _client
    if not config.MQTT_ENABLED:
        log.info("MQTT disabled")
        return None
    import paho.mqtt.client as mqtt

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2, client_id=f"sauviewind_{random.randint(0, 99999)}"
    )
    if config.MQTT_USERNAME and config.MQTT_PASSWORD:
        client.username_pw_set(config.MQTT_USERNAME, config.MQTT_PASSWORD)

    def on_connect(c, userdata, flags, reason_code, properties):
        if reason_code == 0:
            log.info("Connected to MQTT broker %s:%s", config.MQTT_HOST, config.MQTT_PORT)
            c.subscribe(config.TOPIC_WIND, qos=1)
        else:
            log.error("MQTT connection refused: %s (check MQTT_USRNM / MQTT_PSWD)", reason_code)

    def on_message(c, userdata, message):
        if message.topic == config.TOPIC_WIND:
            try:
                handle_wind_payload(message.payload)
            except Exception:  # never let a bad message kill the network thread
                log.exception("Failed to store wind message")

    client.on_connect = on_connect
    client.on_message = on_message
    client.reconnect_delay_set(min_delay=1, max_delay=60)
    client.connect_async(config.MQTT_HOST, config.MQTT_PORT, keepalive=60)
    client.loop_start()
    _client = client
    return client


def stop() -> None:
    if _client is not None:
        _client.loop_stop()
        _client.disconnect()
