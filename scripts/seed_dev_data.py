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

with db.connect() as conn:
    conn.execute("DELETE FROM observations")
    conn.execute("DELETE FROM tide_events")
    conn.execute("DELETE FROM forecasts")

# Annie: 3 days of 10-minute readings with a smooth daily thermal cycle.
# Shift phase relative to `now` so the last 6 hours always show an active afternoon-style breeze.
peak_offset_h = ((now / 3600) - 2.5) % 24
for i in range(3 * 144, 0, -1):
    t = now - i * 600
    phase = ((t / 3600) - peak_offset_h + 4.5) % 24
    base = 5 + 12 * math.sin(phase / 9 * math.pi) if 0 <= phase <= 9 else 5
    speed = max(2, base + random.uniform(-1.2, 1.2))
    gust = round(speed + random.uniform(3, 6))
    lull = max(1, round(speed - random.uniform(1.5, 3)))
    direction = int(250 + 35 * math.sin(i / 20) + random.randint(-8, 8)) % 360
    db.insert_observation("annie", t, round(speed), gust, lull, direction)

# Upriver & model stations: hourly, slightly ahead of Sauvie.
for key, shift, lead_h in (("st_helens_model", 1.05, 0.5), ("kspb", 0.95, 0.8), ("kkls", 1.15, 1.2)):
    for i in range(3 * 24, 0, -1):
        t = now - i * 3600 + 1800
        phase = ((t / 3600) - peak_offset_h + 4.5 + lead_h) % 24
        base = 4 + 12 * math.sin(phase / 9 * math.pi) if 0 <= phase <= 9 else 4
        spd = round(base * shift, 1)
        gst = None if random.random() < 0.4 else round(spd + 5, 1)
        db.insert_observation(key, t, spd, gst, None, int(240 + random.randint(-20, 20)) % 360)

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
