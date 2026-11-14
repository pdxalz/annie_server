"""Pretend to be Annie: publish a random-walk wind reading to MQTT.

    python scripts/mock_annie.py --host localhost --interval 10
"""
import argparse
import json
import random
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

p = argparse.ArgumentParser()
p.add_argument("--host", default="localhost")
p.add_argument("--port", type=int, default=1883)
p.add_argument("--user")
p.add_argument("--password")
p.add_argument("--interval", type=float, default=10, help="seconds between messages")
p.add_argument("--topic", default="zimbuktu/wind")
args = p.parse_args()

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="mock_annie")
if args.user:
    client.username_pw_set(args.user, args.password)
client.connect(args.host, args.port)
client.loop_start()

wind, direction = 12.0, 270
try:
    while True:
        wind = min(35, max(2, wind + random.uniform(-2, 2)))
        direction = (direction + random.randint(-12, 12)) % 360
        gust = round(wind + random.uniform(3, 9))
        lull = max(0, round(wind - random.uniform(2, 5)))
        msg = {
            "t": datetime.now(timezone.utc).strftime("%m/%d/%y %H:%M"),
            "d": direction, "a": round(wind), "g": gust, "l": lull,
        }
        client.publish(args.topic, json.dumps(msg), qos=1)
        print("sent", msg)
        time.sleep(args.interval)
except KeyboardInterrupt:
    client.loop_stop()
