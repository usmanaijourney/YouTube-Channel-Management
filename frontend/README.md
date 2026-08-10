# Master Control — Dashboard Frontend

A Next.js (App Router) + TypeScript + Tailwind dashboard for the multi-agent YouTube automation platform. Talks to the FastAPI backend in `../dashboard/api` through a server-side proxy route, so the backend's API key never reaches the browser.

## Setup

```bash
cd frontend
npm install
cp .env.example .env.local
```

Edit `.env.local`:

```
BACKEND_API_BASE_URL=http://localhost:8000
BACKEND_API_KEY=<contents of ../secrets/dashboard_api_key.txt>
```

## Run

Make sure the backend is running first (from the project root):

```bash
.venv\Scripts\python.exe -m uvicorn dashboard.api.app:app --port 8000
```

The Master Orchestrator service is optional for the dashboard itself (only `run.py` requires it, and only unless you pass `--no-orchestrator`), but the Orchestrator page shows real data only once it's running and has completed at least one 30s health cycle:

```bash
.venv\Scripts\python.exe -m uvicorn master_orchestrator.app:app --port 8100
```

Then, from `frontend/`:

```bash
npm run dev
```

Open http://localhost:3000 — it redirects to `/overview`.

## Test

```bash
npm run test      # vitest — API client, StatusBadge, ErrorState, Channels page (incl. interactions)
npm run lint       # eslint
npx tsc --noEmit   # type-check
```

## Architecture

- **`src/app/api/proxy/[...path]/route.ts`** — the only place `BACKEND_API_KEY` is used. All client-side data fetching goes through `/api/proxy/*`, same-origin, so there's no CORS to configure and no key exposure.
- **`src/lib/api.ts`** — typed client wrapping the proxy, throws `ApiError` with the backend's status/detail on failure.
- **`src/lib/hooks.ts`** — SWR hooks per endpoint, 15s polling. `useAllAgents`/`useAllTasks` aggregate client-side across every channel (see Limitations below).
- **`src/components/shell/`** — sidebar (13 nav items, active-route highlighting, live critical-alert badge) + top bar (breadcrumbs, manual refresh via SWR's global `mutate`).
- **`src/components/ui/`** — `StatusBadge` (green/blue/amber/red/gray per the spec), `Panel`/`StatTile`, and loading/empty/error/unavailable states used consistently across every page.

## Implemented Pages (real backend data)

| Page | Backend endpoint(s) used |
|---|---|
| Overview | `/api/system/health`, `/api/integrations`, `/api/channels`, `/api/alerts`, aggregated agents |
| Channels | `/api/channels` |
| Channel Detail | `/api/channels/{id}`, `/api/channels/{id}/tasks/{task_id}` (for the pipeline visualization), `/api/alerts` (client-filtered) |
| Agents | aggregated from `/api/channels` + `/api/channels/{id}` per channel |
| Agent Detail | `/api/channels/{id}/agents/{agent_type}` |
| Tasks | aggregated from `/api/channels/{id}` per channel (`recent_tasks`, capped at 20/channel) |
| Task Detail | `/api/channels/{id}/tasks/{task_id}` |
| Alerts | `/api/alerts` |
| Schedules | `/api/schedules` |
| Integrations | `/api/integrations` |
| Analytics | partial — cost/success-rate/video-counts from existing endpoints; real YouTube metrics honestly marked unavailable |
| Settings | server-rendered local config display only (no settings backend exists) |
| Orchestrator | `/api/orchestrator` (backed by a real `master_orchestrator` service — see below) |

## Honestly-Unavailable Pages

These show a clear explanation instead of fabricated data, because the backend has no supporting endpoint:

- **Workflows** — no separate "workflow definition" concept exists distinct from a task; points to Tasks.
- **Production** — no video-listing endpoint (`GET /api/channels/{id}/videos` doesn't exist; only aggregate counts do).
- **Logs** — no structured/searchable log store; points to Task/Agent detail event timelines instead.
- **Infrastructure** — no CPU/memory/queue-depth metrics endpoint; points to Integrations (the closest real equivalent).

## Known Limitations

1. **No global, paginated task or agent list endpoints.** The Tasks and Agents pages aggregate client-side across every channel's `/api/channels/{id}` call. This works fine at the current single/few-channel scale but won't scale to 50+ channels or high task volume — each channel is currently capped at its 20 most recent tasks.
2. **No write/action endpoints.** Retry, restart, pause, resume, clear queue, acknowledge, resolve, and mute controls are all rendered but disabled with a "not available" tooltip — the backend has no corresponding endpoints yet (this is also why `audit_logs`, which exists as a table, has nothing writing to it).
3. **No real YouTube Analytics integration.** Views, watch time, subscribers, CTR, and retention require a different OAuth scope than the upload access already wired; Analytics shows only what's genuinely available today (cost, task success rate, video counts).
4. **No automatic scheduler.** `/api/schedules` reflects real state, and the Master Orchestrator's governor (`master_orchestrator/governor.py`) now really gates concurrent production slots, but nothing yet *triggers* a run automatically on a cron/interval — each run is still a manual `python run.py` invocation (which does request a real slot from the orchestrator first).
5. **No light mode.** Dark theme only, despite the spec asking for an optional light mode — deprioritized given everything else in scope.
6. **Orchestrator "current objectives" and CPU/memory aren't tracked.** The service is a single lightweight Python process; doc §19's `strategic_review_weekly` (a narrow LLM call for cross-channel strategy) is design-only, not implemented.

## Recommended Next API Additions

In priority order, based on what the frontend most wants and doesn't have:

1. `GET /api/tasks` — global, paginated, filterable task list (replaces the client-side aggregation hack).
2. `GET /api/channels/{id}/videos` and `GET /api/channels/{id}/videos/{video_id}` — powers the Production page and a real "recent videos" section on Channel Detail.
3. Write endpoints for at least `retry` and `pause`, each writing to `audit_logs` — the highest-value action pair, and the thing that finally gives the audit table a purpose.
4. `GET /api/agents` — global agent list (same aggregation problem as tasks).
5. A simple `GET /api/logs` backed by `task_events` joined across all channels, even without a dedicated logs table yet.
