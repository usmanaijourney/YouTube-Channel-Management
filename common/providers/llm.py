"""Mocked LLM provider.

Stands in for direct Anthropic API calls (architecture doc §13: "direct API
calls wrapped in your own thin task functions", not a heavy agent framework).
Swap this module's implementation for a real `anthropic` client call later —
callers only depend on `call_llm(system_prompt, user_prompt) -> dict`.
"""
from __future__ import annotations

import asyncio
import random
from typing import Any

from common.errors import TransientError

_TOPIC_TITLES = [
    "5 Hidden Settings That Instantly Speed Up Your Phone",
    "Why Your Wi-Fi Router Placement Is Costing You Speed",
    "The USB Cable Trick Nobody Tells You About",
]


async def call_llm(system_prompt: str, user_prompt: str = "", *,
                    simulate_failure: bool = False) -> dict[str, Any]:
    """Returns a canned structured response keyed off the system prompt's intent.

    A real implementation would call the Anthropic Messages API and parse the
    response; agents that call this function don't need to change when that swap happens.
    """
    await asyncio.sleep(0)  # placeholder for network latency

    if simulate_failure:
        raise TransientError("mock LLM provider: simulated transient failure")

    prompt_lower = system_prompt.lower()

    if "topic generator" in prompt_lower:
        title = random.choice(_TOPIC_TITLES)
        return {
            "title": title,
            "research_notes": f"Angle: practical, surprising tip format. Seed topic: {title}",
        }

    if "script writer" in prompt_lower:
        return {
            "hook": f"Did you know {user_prompt.splitlines()[0] if user_prompt else 'this'} could change everything?",
            "sections": [
                {"heading": "The Problem", "body": "Most people never check this setting."},
                {"heading": "The Fix", "body": "Here's exactly where to find it and what to change."},
                {"heading": "Why It Works", "body": "A short technical explanation in plain language."},
            ],
            "cta": "Subscribe for more tips like this every week.",
        }

    if "voice" in prompt_lower or "ssml" in prompt_lower:
        return {
            "ssml": f"<speak>{user_prompt}</speak>",
            "pace": "medium",
        }

    if "video planner" in prompt_lower or "visual" in prompt_lower:
        return {
            "shots": [
                {"type": "stock", "query": "smartphone settings screen", "duration_s": 4},
                {"type": "stock", "query": "wifi router closeup", "duration_s": 3},
                {"type": "text_overlay", "text": "Try this today", "duration_s": 2},
            ],
            "template": "clean-tech-v2",
        }

    return {"raw": "mock response"}
