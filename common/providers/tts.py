"""Real TTS provider using edge-tts (Microsoft Edge's neural voices).

No API key/account needed — chosen after ElevenLabs' free tier turned out to
block programmatic TTS access entirely (paid plan required for any API call,
not just library voices). Swap this module again if/when a paid TTS provider
gets wired up; the `synthesize_speech(...)` signature is what agents/voice_over.py
depends on, not the provider behind it.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import edge_tts

from common.errors import PermanentError, TransientError

_PACE_TO_RATE = {"slow": "-15%", "medium": "+0%", "fast": "+15%"}


async def _probe_duration_seconds(path: str) -> float:
    proc = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", path,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise PermanentError(f"ffprobe failed reading synthesized audio: {stderr.decode(errors='replace')[-500:]}")
    return float(json.loads(stdout)["format"]["duration"])


async def synthesize_speech(text: str, voice_id: str, pace: str, out_path: str) -> dict[str, Any]:
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    rate = _PACE_TO_RATE.get(pace, "+0%")

    try:
        communicate = edge_tts.Communicate(text, voice_id, rate=rate)
        await communicate.save(out_path)
    except edge_tts.exceptions.NoAudioReceived as e:
        raise TransientError(f"edge-tts returned no audio: {e}") from e
    except Exception as e:
        raise TransientError(f"edge-tts request failed: {e}") from e

    if not Path(out_path).exists() or Path(out_path).stat().st_size == 0:
        raise TransientError("edge-tts produced an empty audio file")

    duration_seconds = await _probe_duration_seconds(out_path)
    return {"audio_path": out_path, "duration_seconds": duration_seconds}
