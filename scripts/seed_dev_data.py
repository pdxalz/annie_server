"""Fill a dev database with believable synthetic data so the website can be viewed offline.

    DATA_DIR=./winddata-dev python scripts/seed_dev_data.py
"""
import math
import os
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import db  # noqa: E402

random.seed(7)
db.init_db()
now = int(time.time())
now -= now % 600

# Annie: 3 days of 10 minute readings with a sea-breeze style afternoon build-up.
for i in range(3 * 144, 0, -1):
    t = now - i * 600
    hour = ((t // 3600) - 8) % 24  # roughly Pacific local hour
    base = 4 + 14 * max(0, math.sin((hour - 9) / 9 * math.pi)) if 9 <= hour <= 18 else 3
    speed = max(0, base + random.uniform(-1.5, 1.5))
    db.insert_observation("annie", t, round(speed), round(speed + random.uniform(3, 8)), max(0, round(speed - random.uniform(2, 4))), int(250 + 40 * math.sin(i / 20) + random.randint(-10, 10)) % 360)

# NWS airports: hourly, a bit ahead of Sauvie.
for key, shift in (("kspb", 1.0), ("kkls", 1.3)):
    for i in range(3 * 24, 0, -1):
        t = now - i * 3600 + 1800
        hour = ((t // 3600) - 8) % 24
        base = 3 + 15 * max(0, math.sin((hour - 8) / 9 * math.pi)) if 8 <= hour <= 17 else 3
        db.insert_observation(key, t, round(base * shift, 1), None if random.random() < 0.5 else round(base * shift + 6, 1), None, int(240 + random.randint(-25, 25)) % 360)

# Tides: roughly every 6 h 12 min alternating H/L, two days back to four days ahead.
t, kind = now - 2 * 86400, "L"
with db.connect() as conn:
    while t < now + 4 * 86400:
        conn.execute("INSERT OR REPLACE INTO tide_events VALUES (?, ?, ?)", (t, kind, 3.0 if kind == "H" else 0.3))
        t += 6 * 3600 + 12 * 60
        kind = "H" if kind == "L" else "L"

# Forecasts: two models, next 12 h.
issued = now // 3600 * 3600
with db.connect() as conn:
    for model, bias in (("hrrr", 0), ("rrfs", 2)):
        for h in range(0, 12):
            valid = issued + h * 3600
            local_hour = ((valid // 3600) - 8) % 24
            spd = 4 + 14 * max(0, math.sin((local_hour - 9) / 9 * math.pi)) + bias
            conn.execute("INSERT OR IGNORE INTO forecasts VALUES (?, ?, ?, ?, ?, ?)", (model, issued, valid, round(spd, 1), round(spd + 8, 1), 250 + h * 3))

db.set_meta("water_temp_f", "52.3")
print("Seeded", os.environ.get("DATA_DIR"))
