"""Real FFmpeg-based deterministic video renderer (doc §1 risk #2/#4, §13).

Executes the render spec produced by the (LLM) Video Planner — no LLM involved
here, purely deterministic assembly. Since no stock/generated asset API is
wired yet, each shot is rendered as a solid-color card with its query/text
drawn on it rather than real footage — swap `_build_filtergraph` for real
asset compositing once a stock API is integrated (doc §13's asset_source).

Real narration (TTS) isn't wired yet either (see common/providers/tts.py), so
the audio track muxed in here is synthetic silence at the correct duration —
once TTS produces real audio files, pass that path in and this renderer will
mux it in unchanged; only the "no real audio yet" branch below needs to go.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from common.errors import PermanentError

_PALETTE = ["1B998B", "2D3142", "E94F37", "3F88C5", "F7B32B", "6A4C93", "118AB2"]
_FONT_FILE = r"C:/Windows/Fonts/arial.ttf"
_RESOLUTION = "1280x720"


def _escape_drawtext(text: str) -> str:
    text = text.replace("\\", "\\\\")
    text = text.replace(":", "\\:")
    text = text.replace("'", "\u2019")  # sidesteps drawtext's gnarly apostrophe escaping
    text = text.replace("%", "\\%")
    return text


def _font_path_for_filter() -> str:
    # drawtext parses ':' as an option separator, so the Windows drive-letter
    # colon has to be escaped even though the rest of the path uses '/'.
    return _FONT_FILE.replace(":", "\\:")


async def _run_ffmpeg(args: list[str]) -> None:
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-hide_banner", "-y", *args,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise PermanentError(f"ffmpeg failed (exit {proc.returncode}): {stderr.decode(errors='replace')[-2000:]}")


def _build_render_args(shots: list[dict[str, Any]], out_path: str, total_duration: float) -> list[str]:
    args: list[str] = []
    filters: list[str] = []

    for i, shot in enumerate(shots):
        duration = shot["_duration_s"]
        color = _PALETTE[i % len(_PALETTE)]
        args += ["-f", "lavfi", "-i", f"color=c=0x{color}:s={_RESOLUTION}:d={duration:.3f}"]

        label = shot.get("text") or shot.get("query") or shot.get("type", "shot")
        text = _escape_drawtext(str(label))
        filters.append(
            f"[{i}:v]drawtext=fontfile='{_font_path_for_filter()}':text='{text}':"
            f"fontcolor=white:fontsize=54:x=(w-text_w)/2:y=(h-text_h)/2:"
            f"box=1:boxcolor=black@0.5:boxborderw=20[v{i}]"
        )

    audio_index = len(shots)
    args += ["-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo:d={total_duration:.3f}"]

    concat_inputs = "".join(f"[v{i}]" for i in range(len(shots)))
    filters.append(f"{concat_inputs}concat=n={len(shots)}:v=1:a=0[vout]")
    filter_complex = ";".join(filters)

    args += [
        "-filter_complex", filter_complex,
        "-map", "[vout]", "-map", f"{audio_index}:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
        "-shortest", out_path,
    ]
    return args


async def render_video(render_spec: dict[str, Any], voice_over_path: str, voice_over_duration_s: float,
                        out_path: str) -> dict[str, Any]:
    shots = list(render_spec.get("shots", []))
    if not shots:
        raise PermanentError("renderer: render spec has no shots")

    durations = [max(float(s.get("duration_s", 0)), 0.1) for s in shots]
    shot_sum = sum(durations)
    video_duration = max(shot_sum, voice_over_duration_s, 0.1)
    if video_duration > shot_sum:
        durations[-1] += video_duration - shot_sum
    for shot, duration in zip(shots, durations, strict=True):
        shot["_duration_s"] = duration

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    render_args = _build_render_args(shots, out_path, video_duration)
    await _run_ffmpeg(render_args)

    thumbnail_path = str(Path(out_path).with_suffix(".jpg"))
    await _run_ffmpeg([
        "-i", out_path, "-ss", f"{video_duration / 2:.3f}",
        "-frames:v", "1", thumbnail_path,
    ])

    return {"video_path": out_path, "duration_seconds": video_duration, "thumbnail_path": thumbnail_path}
