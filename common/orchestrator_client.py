"""Client for the Master Orchestrator's governor (doc §11) — how a Channel
Manager asks "can I have a production slot now?" over HTTP RPC (doc §5).
"""
from __future__ import annotations

import asyncio
import os
from typing import Optional

import httpx

DEFAULT_ORCHESTRATOR_URL = os.environ.get("ORCHESTRATOR_URL", "http://localhost:8100")
MAX_ATTEMPTS = 5
BASE_BACKOFF_SECONDS = 1.0


class OrchestratorUnavailable(Exception):
    """The orchestrator service couldn't be reached at all (not just slot-exhausted)."""


async def acquire_production_slot(channel_id: str, api_key: str,
                                   orchestrator_url: str = DEFAULT_ORCHESTRATOR_URL) -> Optional[str]:
    """Retries with backoff while slots are full; raises OrchestratorUnavailable if the
    service itself can't be reached (as opposed to reachable-but-no-slots-free)."""
    async with httpx.AsyncClient(timeout=10) as client:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = await client.post(
                    f"{orchestrator_url}/orchestrator/slots/acquire",
                    json={"channel_id": channel_id},
                    headers={"X-API-Key": api_key},
                )
            except httpx.RequestError as e:
                raise OrchestratorUnavailable(f"could not reach orchestrator at {orchestrator_url}: {e}") from e

            response.raise_for_status()
            data = response.json()
            if data["granted"]:
                return data["slot_id"]

            if attempt < MAX_ATTEMPTS:
                await asyncio.sleep(BASE_BACKOFF_SECONDS * (2 ** (attempt - 1)))

    return None


async def release_production_slot(slot_id: str, api_key: str,
                                   orchestrator_url: str = DEFAULT_ORCHESTRATOR_URL) -> None:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f"{orchestrator_url}/orchestrator/slots/release",
            json={"slot_id": slot_id},
            headers={"X-API-Key": api_key},
        )
        response.raise_for_status()
