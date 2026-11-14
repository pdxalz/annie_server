"""Application entry point: ``uvicorn app.main:app --workers 1``.

Run a single worker: the MQTT subscriber and collectors live inside this process.
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import config, db, mqtt_sub
from .collectors import scheduler
from .routes import api, legacy

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    mqtt_sub.start()
    task = None
    if config.COLLECTORS_ENABLED:
        task = asyncio.create_task(scheduler.run_forever())
    log.info("Sauviewind started")
    try:
        yield
    finally:
        if task:
            task.cancel()
        mqtt_sub.stop()


app = FastAPI(title="Sauvie Island Wind", lifespan=lifespan, docs_url=None, redoc_url=None)

app.include_router(api.router)
app.include_router(legacy.router)
app.mount("/static", StaticFiles(directory=config.WEB_DIR), name="static")

config.ROOSTER_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/rooster", StaticFiles(directory=config.ROOSTER_DIR), name="rooster")
