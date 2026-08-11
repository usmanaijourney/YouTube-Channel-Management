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

## Deploy (Railway)

Two services off this one repo. The dashboard API and the Master Orchestrator run **in the same service** — they share one SQLite file, and a Railway volume attaches to exactly one service, so they cannot be split without moving to Postgres first.

The video pipeline (`run.py`) stays local. It needs ffmpeg, the YouTube OAuth token in `secrets/`, and answers to its interactive approval gates — none of which survive a container, and nothing triggers it on a schedule yet.

**Service 1 — backend** (root directory `/`)

| Variable | Value |
|---|---|
| `DASHBOARD_API_KEY` | a long random string; the frontend needs the same value |
| `DB_PATH` | `/data/youtube_orchestration.db` |
| `PORT` | `8000` |

Attach a volume mounted at `/data`, or every redeploy starts from an empty database. Both processes are started by [scripts/start_backend.sh](scripts/start_backend.sh), which binds `0.0.0.0` — binding `::` returns 502 on every request even though uvicorn logs a healthy bind, because a v6 socket only accepts IPv4 connections when the container's `bindv6only` is off. `BIND_HOST` overrides it.

[railway.json](railway.json) and [nixpacks.toml](nixpacks.toml) carry the start command and an ffmpeg package. The platform may pick its own builder and ignore the nixpacks file; either way ffmpeg and ffprobe report healthy on `/api/integrations`, which really shells out to them.

**Service 2 — frontend** (root directory `frontend`)

| Variable | Value |
|---|---|
| `BACKEND_API_BASE_URL` | `http://<backend-service>.railway.internal:8000` |
| `BACKEND_API_KEY` | same value as `DASHBOARD_API_KEY` |

Set the service's root directory to `frontend`, and generate a public domain for this service only. The backend needs no public domain — the browser never talks to it directly, only the frontend's server-side proxy route does. If private networking gives you trouble, the backend's own public URL works as `BACKEND_API_BASE_URL` too; the API is key-protected either way.

One trap worth knowing: if the shell you set `BACKEND_API_KEY` from writes a UTF-8 BOM, the value is unusable as an HTTP header and every proxied request fails with a 502 that looks exactly like a networking fault. The proxy route reports the underlying cause now, which is what makes that distinguishable.

**What reports as unavailable in a deployment:** the Integrations page shows `youtube_api` as an error, because the OAuth refresh token lives in `secrets/` on your machine and is never committed. The dashboard is read-only, so this affects nothing else.

## Status

Phase 0 MVP. All three approval gates (topic, script, pre-upload) are on by default, the dashboard is read-only, and runs are triggered manually — there is no automatic scheduler yet. Known gaps are listed in [frontend/README.md](frontend/README.md#known-limitations).
