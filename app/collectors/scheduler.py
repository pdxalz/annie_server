"""Runs each collector on its own interval; one failing source never stops the others."""
from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable

import httpx

from . import nws, openmeteo, tides

log = logging.getLogger("collectors")

# (name, function, interval seconds)
JOBS: list[tuple[str, Callable[[httpx.AsyncClient], Awaitable[int]], int]] = [
    ("nws", nws.collect, 600),
    ("openmeteo", openmeteo.collect, 3600),
    ("tides", tides.collect, 6 * 3600),
]
MAX_BACKOFF = 1800


async def _run_job(name, fn, interval, client: httpx.AsyncClient) -> None:
    failures = 0
    while True:
        try:
            count = await fn(client)
            log.info("%s: %d new rows", name, count)
            failures = 0
            delay = interval
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            failures += 1
            delay = min(interval * 2 ** (failures - 1), MAX_BACKOFF)
            log.warning("%s failed (%s: %s); retrying in %ds", name, type(exc).__name__, exc, delay)
        await asyncio.sleep(delay)


async def run_forever() -> None:
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        tasks = [asyncio.create_task(_run_job(n, f, i, client)) for n, f, i in JOBS]
        try:
            await asyncio.gather(*tasks)
        finally:
            for t in tasks:
                t.cancel()
