"""CLI entrypoint for running one video through the Phase 0 MVP pipeline end-to-end.

Matches doc §20 MVP scope: no dashboard yet, CLI/logs only.
"""
from __future__ import annotations

import argparse
import asyncio
import json

from channel_manager.config_schema import load_channel_config
from channel_manager.workflow import run_pipeline
from common.db import models as db
from common.orchestrator_client import (
    DEFAULT_ORCHESTRATOR_URL,
    OrchestratorUnavailable,
    acquire_production_slot,
    release_production_slot,
)
from dashboard.api.auth import get_expected_api_key

DB_PATH = db.DEFAULT_DB_PATH


async def _cli_approval(task_id: str, stage: str, payload: dict) -> bool:
    print(f"\n--- Approval gate: {stage} (task {task_id}) ---")
    print(json.dumps(payload, indent=2, default=str))
    answer = input(f"Approve {stage}? [y/N]: ").strip().lower()
    return answer == "y"


async def _auto_approval(task_id: str, stage: str, payload: dict) -> bool:
    print(f"\n--- Auto-approving gate: {stage} (task {task_id}) ---")
    return True


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run one video through the channel pipeline.")
    parser.add_argument("--channel-config", default="config/channels/channel-001.yaml")
    parser.add_argument("--auto-approve", action="store_true", help="Skip interactive approval prompts")
    parser.add_argument("--no-orchestrator", action="store_true",
                         help="Skip requesting a production slot from the Master Orchestrator "
                              "(for quick local testing without that service running)")
    parser.add_argument("--orchestrator-url", default=DEFAULT_ORCHESTRATOR_URL)
    args = parser.parse_args()

    await db.init_db(DB_PATH)
    channel_config = load_channel_config(args.channel_config).model_dump()
    channel_id = channel_config["channel_id"]

    slot_id: str | None = None
    if not args.no_orchestrator:
        print(f"\n--- Requesting a production slot from the orchestrator at {args.orchestrator_url} ---")
        try:
            slot_id = await acquire_production_slot(channel_id, get_expected_api_key(), args.orchestrator_url)
        except OrchestratorUnavailable as e:
            raise SystemExit(
                f"{e}\nStart it with: uvicorn master_orchestrator.app:app --port 8100\n"
                f"or pass --no-orchestrator to skip this for local testing."
            ) from e
        if slot_id is None:
            raise SystemExit("No production slot available (all slots busy) — try again shortly.")
        print(f"--- Slot granted: {slot_id} ---")

    try:
        async with db.connect(DB_PATH) as conn:
            await db.upsert_channel(
                conn, channel_config["channel_id"], channel_config["name"],
                channel_config["niche"], channel_config["status"], channel_config["schedule"],
            )
            await db.upsert_schedule_config(
                conn, channel_config["channel_id"], enabled=(channel_config["status"] == "active"),
                preferred_hours_utc=channel_config["schedule"]["preferred_hours_utc"],
            )

            await db.mark_schedule_running(conn, channel_config["channel_id"])
            approval = _auto_approval if args.auto_approve else _cli_approval
            result = await run_pipeline(conn, channel_config, approval_callback=approval)
            await db.mark_schedule_result(
                conn, channel_config["channel_id"],
                "completed" if result["status"] == "success" else "failed",
            )

            print("\n=== Pipeline result ===")
            print(json.dumps(result, indent=2, default=str))

            events = await db.get_task_events(conn, result["task_id"])
            print(f"\n=== Task event log ({len(events)} transitions) ===")
            for e in events:
                agent = f"  [agent={e['agent_id']}]" if e["agent_id"] else ""
                print(f"  {e['from_state']} -> {e['to_state']}{agent}")
    finally:
        if slot_id is not None:
            await release_production_slot(slot_id, get_expected_api_key(), args.orchestrator_url)
            print(f"\n--- Slot released: {slot_id} ---")


if __name__ == "__main__":
    asyncio.run(main())
