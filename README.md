# YouTube Channel Management

A multi-agent system that takes a YouTube channel from topic idea to published video, with human approval gates at each risky step. Python/FastAPI backend, SQLite state store, Next.js dashboard.

The full design spec lives in [youtube-orchestration-architecture.md](youtube-orchestration-architecture.md).

## Layout

| Path | What it is |
|---|---|
| `agents/` | One module per pipeline stage — topic generator, script writer, video planner, voice-over, renderer, YouTube uploader, WhatsApp notifier |
| `channel_manager/` | Per-channel pipeline: config schema, dispatcher, workflow, quality checks |
| `master_orchestrator/` | Cross-channel service — production-slot governor and health aggregation |
| `dashboard/api/` | FastAPI read API backing the dashboard |
| `frontend/` | Next.js + Tailwind dashboard (see [frontend/README.md](frontend/README.md)) |
| `common/` | Shared DB models/migrations, provider adapters (LLM, TTS, renderer, YouTube, WhatsApp), secrets, scheduling |
| `config/channels/` | Per-channel YAML config |
| `scripts/` | One-off operator scripts, e.g. YouTube OAuth authorization |
| `tests/` | Unit tests plus integration tests that hit real ffmpeg/services |

## Setup

```bash
python -m venv .venv
.venv\Scripts\pip.exe install -r requirements.txt
```

Secrets are read from `secrets/` (gitignored) — see `common/secrets.py` for the expected filenames. Authorize YouTube uploads once per channel:

```bash
.venv\Scripts\python.exe scripts/authorize_youtube.py
```

## Run

Master Orchestrator (grants production slots):

```bash
.venv\Scripts\python.exe -m uvicorn master_orchestrator.app:app --port 8100
```

Dashboard API:

```bash
.venv\Scripts\python.exe -m uvicorn dashboard.api.app:app --port 8000
```

One video through the pipeline:

```bash
.venv\Scripts\python.exe run.py --channel-config config/channels/channel-001.yaml
```

Add `--auto-approve` to skip the interactive approval gates, or `--no-orchestrator` to run without the slot service.

## Test

```bash
.venv\Scripts\python.exe -m pytest tests/unit
```

`tests/integration/` requires ffmpeg and live service credentials.

## Status

Phase 0 MVP. All three approval gates (topic, script, pre-upload) are on by default, the dashboard is read-only, and runs are triggered manually — there is no automatic scheduler yet. Known gaps are listed in [frontend/README.md](frontend/README.md#known-limitations).
