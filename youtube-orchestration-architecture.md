# Multi-Level Autonomous YouTube Channel Orchestration System
### Full Architecture & Implementation Design

---

## 1. Analysis: Ambiguities & Architectural Risks (Read First)

Before locking the design, these need explicit decisions:

| # | Ambiguity | Decision Made | Rationale |
|---|---|---|---|
| 1 | Are agents separate processes, threads, or just LLM calls? | Agents are **stateless worker functions/services** invoked by the Channel Manager via a task queue, not long-running processes. Only the Channel Manager and Master Orchestrator are persistent, stateful services. | Keeps 100+ channels × 6 agents from becoming 600+ always-on processes. Compute is consumed only when work exists. |
| 2 | Where does the actual video rendering happen (compute-heavy)? | Delegated to a **rendering worker pool** (separate from the "Video Maker agent," which is the *planning* brain — it produces a render spec, a dedicated renderer executes it). | LLMs are bad/expensive at literally encoding video. Split "creative decision" (LLM) from "execution" (deterministic renderer, e.g. FFmpeg/Remotion). |
| 3 | What happens if 100 channels all want to produce at 9am? | Global **rate/resource governor** in the Master Orchestrator issues production "slots" to Channel Managers; Channel Managers queue locally and pull slots. | Prevents thundering-herd on YouTube API, TTS API, and render workers. |
| 4 | Is "one video maker agent" really one LLM agent for both visuals AND assembly? | Split conceptually into **Visual Planner** (LLM: decides shots/assets) and **Video Assembler** (deterministic worker: renders). Both live under the "Agent 3" umbrella so the 6-agent contract in the spec is preserved. | Keeps the spec's "6 agents" promise while being realistic about what should and shouldn't be an LLM call. |
| 5 | Human-in-the-loop? | Configurable **approval gates** (topic approval, script approval, pre-upload approval) — default OFF for trusted channels, ON for new/low-trust channels. | Full autonomy is the goal but you don't want channel #47 auto-uploading garbage on day one. |
| 6 | Credential blast radius | Each Channel Manager's uploader agent gets a **scoped, short-lived token**, never the raw OAuth client secret, fetched just-in-time from a secrets manager keyed by `channel_id`. | Prevents one compromised worker from touching every channel. |
| 7 | What is "the Master Orchestrator" technically — another LLM agent? | It is mostly **non-LLM** (a control-plane service: scheduler, aggregator, alerting). It calls an LLM only for narrow reasoning tasks (e.g. "given these 20 channel reports, what's the one strategic recommendation?"). | An LLM should not be your load balancer, DB, or scheduler — direction from the spec ("should not micromanage") means most of its job is boring control-plane logic, with LLM calls layered on top for judgment calls. |
| 8 | Duplicate topic detection across agents/channels | Topic Generators check against a **channel-scoped vector store** of past topics (embeddings), not the whole system — cross-channel topic overlap is fine (different audiences). | Matches the isolation requirement while still being useful. |

**Key architectural risk called out explicitly:** if every "agent" is implemented as a full autonomous LLM loop, cost and latency balloon linearly with channel count, and failures become hard to debug. The design below treats **Channel Manager = stateful orchestrator (code)**, **Agents = short-lived, single-purpose LLM or deterministic tasks invoked as functions**, and **Master Orchestrator = control plane + occasional LLM reasoning**. This is what makes 100+ channels tractable.


---

## 2. High-Level Architecture

```
                              ┌───────────────────────────┐
                              │     MASTER ORCHESTRATOR     │
                              │  (control plane, no LLM     │
                              │   loop; LLM used narrowly)  │
                              │                             │
                              │  - Channel Registry         │
                              │  - Global Scheduler/Governor│
                              │  - Health Aggregator        │
                              │  - Alerting/Escalation      │
                              │  - Global Analytics         │
                              │  - Cost Tracker             │
                              └──────────────┬──────────────┘
                                             │ gRPC/HTTP + event bus (async)
                    ┌────────────────────────┼────────────────────────┐
                    │                        │                        │
                    ▼                        ▼                        ▼
          ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
          │ CHANNEL MANAGER A │     │ CHANNEL MANAGER B │     │ CHANNEL MANAGER C │
          │ (stateful worker  │     │                    │     │                    │
          │  service, 1/chan) │     │                    │     │                    │
          │ - Task queue       │     │                    │     │                    │
          │ - Channel memory   │     │                    │     │                    │
          │ - Pipeline FSM     │     │                    │     │                    │
          │ - Agent dispatcher │     │                    │     │                    │
          └─────────┬─────────┘     └────────────────────┘     └────────────────────┘
                    │ dispatches tasks to stateless agent workers via task queue
     ┌───────┬───────┼───────┬───────┬───────┐
     ▼       ▼       ▼       ▼       ▼       ▼
   TG1      TG2      SW    VO/VM     YT      WA
 (topic)  (topic) (script) (voice/  (upload) (notify)
                            video)
```

**Isolation boundary:** everything under a Channel Manager (its queue, memory namespace, credentials, agent invocations) is namespaced by `channel_id`. No component reaches across that namespace except the Master Orchestrator reading aggregated reports.


---

## 3. Component Responsibilities (Summary Table)

| Component | Type | Runs | Talks to |
|---|---|---|---|
| Master Orchestrator | Control-plane service (+ narrow LLM calls) | Always-on, single instance (HA pair) | All Channel Managers (via events + RPC), global DB, dashboard API |
| Channel Manager | Stateful workflow service | One logical instance per channel (can be a lightweight actor/durable workflow, not necessarily a dedicated VM) | Its own agent workers, its own DB partition, Master Orchestrator |
| Topic Generator ×2 | Stateless LLM task | Invoked on demand | Channel Manager only |
| Script Writer | Stateless LLM task | Invoked on demand | Channel Manager only |
| Voice Over | Stateless task (TTS API call + LLM for SSML/pacing) | Invoked on demand | Channel Manager only |
| Video Maker + Visuals | LLM planning step + deterministic render worker | Invoked on demand | Channel Manager only |
| YouTube Uploader | Stateless task, scoped credentials | Invoked on demand | Channel Manager only, YouTube API |
| WhatsApp Notifier | Stateless task | Invoked on demand | Channel Manager only, WhatsApp Business API |

---

## 4. Task Lifecycle (Single Video, End-to-End)

```
CREATED (by scheduler slot)
   → TOPIC_RESEARCH (TG1 ∥ TG2 run concurrently)
   → TOPIC_EVALUATION (Channel Manager scores/picks, or human gate)
   → TOPIC_APPROVED
   → SCRIPT_DRAFTING (Script Writer)
   → SCRIPT_APPROVED (auto or human gate)
   → PRODUCTION_FANOUT
        ├─ VOICE_OVER_IN_PROGRESS → VOICE_OVER_DONE
        └─ VISUAL_PLANNING_IN_PROGRESS → RENDER_IN_PROGRESS → VIDEO_DONE
   → PRODUCTION_JOIN (waits for both branches)
   → QUALITY_CHECK
        ├─ PASS → UPLOAD_IN_PROGRESS → UPLOAD_DONE
        └─ FAIL → back to relevant stage (SCRIPT/ VOICE/ VIDEO) with reason
   → NOTIFY (WhatsApp)
   → REPORTED (Channel Manager → Master Orchestrator)
   → CLOSED
```

Each state transition is a **durable event** (see §6 schema) — this makes the pipeline resumable after a crash: the Channel Manager can rehydrate a task from its last committed state rather than restarting from scratch.


---

## 5. Communication Protocol & Message Schema

**Transport:** async event bus (e.g. NATS/Kafka/Redis Streams) for fan-out/fan-in and status events, plus direct RPC (gRPC or internal HTTP) for synchronous request/response (e.g. Channel Manager asking Master Orchestrator "can I have a production slot now?").

**Canonical envelope** (extends the one in the spec):

```json
{
  "message_id": "uuid-v4",
  "task_id": "task_9f1c...",
  "channel_id": "channel-001",
  "agent_id": "script-writer-001",
  "message_type": "TASK_COMPLETED",
  "status": "success",
  "timestamp": "2026-08-09T10:22:31Z",
  "retry_count": 0,
  "idempotency_key": "task_9f1c-script-v1",
  "payload": {},
  "error": null,
  "trace_id": "otel-trace-id"
}
```

Rules:
- **Idempotency:** every message carries `idempotency_key`; consumers dedupe on it (agent workers can be retried safely).
- **Traceability:** `trace_id` propagated end-to-end, feeding OpenTelemetry for cross-service tracing.
- **Validation:** JSON Schema (or protobuf) enforced at the bus boundary; malformed messages go to a dead-letter topic, not silently dropped.
- **Direction:** agents never publish directly to other agents' topics — only to their own Channel Manager's inbox topic (`channel.{id}.events`). The Channel Manager publishes summarized reports to `orchestrator.reports`.


---

## 6. Database Schema (Core Tables)

Relational store (Postgres) for structured state; vector store separate (see below).

```sql
-- Global (Master Orchestrator scope)
CREATE TABLE channels (
  channel_id       TEXT PRIMARY KEY,
  name             TEXT NOT NULL,
  niche            TEXT,
  status           TEXT CHECK (status IN ('active','paused','error','onboarding')),
  youtube_channel_ref TEXT,       -- pointer into secrets manager, not the token itself
  created_at       TIMESTAMPTZ DEFAULT now(),
  schedule_json    JSONB           -- e.g. {"videos_per_day": 2}
);

CREATE TABLE system_events (
  id BIGSERIAL PRIMARY KEY,
  channel_id TEXT REFERENCES channels(channel_id),
  event_type TEXT,
  severity   TEXT CHECK (severity IN ('info','warning','critical')),
  payload    JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Per-channel scope (logically partitioned/sharded by channel_id)
CREATE TABLE tasks (
  task_id     TEXT PRIMARY KEY,
  channel_id  TEXT NOT NULL,
  state       TEXT NOT NULL,          -- see lifecycle in §4
  topic       TEXT,
  created_at  TIMESTAMPTZ DEFAULT now(),
  updated_at  TIMESTAMPTZ DEFAULT now(),
  metadata    JSONB
);

CREATE TABLE task_events (
  id BIGSERIAL PRIMARY KEY,
  task_id TEXT REFERENCES tasks(task_id),
  from_state TEXT,
  to_state   TEXT,
  agent_id   TEXT,
  payload    JSONB,
  error      JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE agents (
  agent_id     TEXT PRIMARY KEY,
  channel_id   TEXT NOT NULL,
  agent_type   TEXT,   -- topic_generator | script_writer | voice_over | video_maker | uploader | notifier
  status       TEXT,   -- idle | busy | degraded | offline
  last_heartbeat TIMESTAMPTZ,
  last_success   TIMESTAMPTZ,
  last_failure   TIMESTAMPTZ,
  failure_count  INT DEFAULT 0,
  avg_exec_ms    INT,
  retry_count    INT DEFAULT 0
);

CREATE TABLE videos (
  video_id    TEXT PRIMARY KEY,
  task_id     TEXT REFERENCES tasks(task_id),
  channel_id  TEXT NOT NULL,
  youtube_video_id TEXT,
  youtube_url TEXT,
  title       TEXT,
  status      TEXT,   -- produced | uploaded | failed
  metrics     JSONB,  -- views/ctr/watch_time populated later by an analytics sync job
  created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE cost_ledger (
  id BIGSERIAL PRIMARY KEY,
  channel_id TEXT,
  task_id    TEXT,
  provider   TEXT,     -- 'llm' | 'tts' | 'render' | 'youtube_api'
  cost_usd   NUMERIC(10,4),
  created_at TIMESTAMPTZ DEFAULT now()
);
```

Vector store (per-channel namespace, e.g. one collection per channel or a shared collection with a `channel_id` metadata filter enforced at the query layer): stores topic embeddings + past-video embeddings for dedupe/style-consistency retrieval.


---

## 7. Memory Architecture

| Scope | Owner | Storage | Contents |
|---|---|---|---|
| Global Memory | Master Orchestrator | Postgres (`channels`, `system_events`) + object storage for reports | System config, policies, channel registry, cross-channel analytics (aggregated, anonymized where relevant) |
| Channel Memory | Channel Manager | Postgres partition/schema-per-channel or row-level security by `channel_id` + a per-channel vector namespace | Niche, audience, brand voice, strategy, topic/video history, style guide, publishing schedule |
| Agent (task) Memory | Individual task execution | Ephemeral — passed as part of the task payload, discarded after task completion (or archived to `task_events` for audit) | Whatever context that single script/video needed |

**Leak prevention:** enforced with row-level security (`WHERE channel_id = current_setting('app.channel_id')`) at the DB layer, plus separate vector collections/namespaces — not just "trust the app code."

---

## 8. Security & Credential Architecture

```
Secrets Manager (e.g. AWS Secrets Manager / HashiCorp Vault)
   ├── channel-001/youtube_oauth   (refresh token, client id/secret)
   ├── channel-001/whatsapp_token
   ├── channel-002/youtube_oauth
   └── ...
```

- Channel Manager requests a **short-lived, scoped access token** just-in-time when the Uploader agent needs to run; the token is injected into the task payload and never persisted in logs or task DB rows (redact on write).
- Each Channel Manager process/service identity has an IAM policy allowing it to read **only its own `channel-{id}/*` secret path** — enforced at the secrets-manager layer, not just app logic, so a bug can't cross-read another channel's credentials.
- Full audit log of every secret access (who/what/when), separate from application logs.
- Secret rotation handled by the secrets manager natively (e.g., YouTube OAuth refresh token rotation on schedule).
- No credentials ever appear in an LLM prompt — the uploader agent's LLM component (if any, e.g. for writing metadata) never sees the token; the token is used only in the deterministic API-call step.

---

## 9. Failure Handling

```
Agent task fails
   → Channel Manager catches exception, classifies error
       (transient: network/rate-limit  vs  permanent: invalid input/policy violation)
   → transient  → retry with exponential backoff (max N attempts)
   → permanent  → do NOT retry blindly; route to recovery strategy
                   (e.g. regenerate script instead of re-running with same bad input)
   → still failing after policy → mark task FAILED, push to dead-letter queue,
                                    emit CRITICAL event to Master Orchestrator
   → Master Orchestrator decides: auto-pause channel? human alert? nothing (isolated, non-critical)?
```

Guarantees:
- One task's failure never blocks other tasks in the same channel's queue (per-task isolation, not a single blocking pipeline).
- One channel's failure never touches another channel's queue (separate queue namespace + separate DB partition + separate credentials = failure cannot propagate).
- All state transitions are persisted before side effects where possible (e.g. mark `UPLOAD_IN_PROGRESS` before calling YouTube API) so a crash mid-upload is detectable and reconcilable on restart (check YouTube for the video before re-uploading — avoids duplicate uploads).


---

## 10. Monitoring, Heartbeats & Reporting

Heartbeat: each active agent invocation reports `{agent_id, channel_id, status, ts}` to its Channel Manager on start/every N seconds for long tasks/completion. Channel Manager rolls this into a per-channel health snapshot every cycle (e.g. 30s) and pushes to the Master Orchestrator's `orchestrator.health` topic.

Master Orchestrator maintains, per channel:
`online/offline, current_task_count, queue_length, tasks_completed, tasks_failed, avg_task_duration, videos_produced, videos_uploaded, upload_failures, cost_today`

and per agent: the fields in the `agents` table above.

Dashboard example report generation (matches spec §14 format) is just a SQL rollup:

```sql
SELECT
  count(*) FILTER (WHERE status='active') AS active_channels,
  count(*) FILTER (WHERE status='error')  AS channels_with_problems
FROM channels;
```

---

## 11. Scheduling & Resource Governance

- Each channel has a target cadence (`videos_per_day` / `videos_per_week`) stored in `channels.schedule_json`.
- Channel Manager computes when its next task should be `CREATED` and requests a **production slot** from the Master Orchestrator's governor.
- The governor caps concurrent renders/TTS calls/LLM calls system-wide (configurable, e.g. "max 20 concurrent renders") and issues slots fairly (round-robin or priority-weighted) — this is the mechanism that prevents the Master Orchestrator from becoming a bottleneck while still preventing resource stampedes: it's a lightweight token-bucket check, not a per-task approval workflow.

---

## 12. Quality Control Gate

Before `UPLOAD_IN_PROGRESS`, a deterministic (non-LLM, fast) checklist runs in the Channel Manager:

```python
def quality_check(task):
    checks = [
        task.script is not None and len(task.script.strip()) > 0,
        task.voice_over_path and audio_is_valid(task.voice_over_path),
        task.video_path and video_is_valid(task.video_path),
        video_duration_ok(task.video_path, task.channel.min_max_duration),
        task.thumbnail_path is not None,
        av_sync_ok(task.video_path, task.voice_over_path),
        task.metadata.title and task.metadata.description,
        task.channel_id == task.uploader_target_channel_id,  # anti-cross-post check
    ]
    return all(checks), [c for c in checks if not c]
```
Failures route back to the specific failed stage with the failure reason attached, not a blind full restart.


---

## 13. Recommended Technology Stack

| Layer | Recommendation | Alternatives Considered | Why |
|---|---|---|---|
| LLM orchestration | Direct Anthropic API calls wrapped in your own thin task functions (not a heavy agent framework) | LangGraph, CrewAI, AutoGen | At this scale you want deterministic, debuggable control flow (a state machine per task) — heavy agent frameworks add abstraction overhead and make cost/latency harder to reason about. Use a framework only if your team wants faster prototyping and accepts the black-box tradeoff. |
| Backend | Python (FastAPI) for services; or Node/TypeScript if your team prefers it | Go | Python has the best ecosystem for LLM/TTS/video-tooling glue; FastAPI gives async I/O needed for many concurrent channel workflows. |
| Workflow engine (Channel Manager's FSM) | Temporal or a custom durable-execution layer on Postgres | Airflow, Prefect, raw Celery | Temporal gives you crash-safe, resumable multi-step workflows (exactly the topic→script→voice/video→upload chain) with built-in retries/backoff — this maps almost 1:1 onto your pipeline requirements. Custom Postgres-backed FSM is a leaner fallback if you don't want another infra dependency. |
| Database | PostgreSQL (with row-level security for channel isolation) | MongoDB | Strong consistency for task state, relational structure fits schema above, RLS gives real tenant isolation. |
| Vector database | Qdrant or pgvector (Postgres extension) | Pinecone, Weaviate | pgvector avoids a second database if you're already on Postgres and scale is moderate; Qdrant/Pinecone if you need dedicated performance at very large scale. |
| Message/task queue | Redis Streams (small/medium scale) or Kafka (large scale, 50+ channels) | RabbitMQ, SQS | Redis Streams is simplest to operate for moderate throughput; Kafka once you need durable replay and very high fan-out across 100+ channels. |
| Scheduler | Temporal's built-in scheduling, or a simple cron + governor service | Airflow | Reuses the workflow engine rather than adding a second scheduling system. |
| Object/file storage | S3 (or GCS) | — | Standard for video/audio assets; use lifecycle rules to purge intermediate render files. |
| API gateway | Managed gateway (e.g. AWS API Gateway) in front of the dashboard/admin API | Kong | Only the dashboard and admin API need external exposure — everything else is internal. |
| AuthN/AuthZ (admin/dashboard) | OAuth2/OIDC (e.g. Auth0 or your IdP) + RBAC | — | Standard; separate concern from per-channel YouTube OAuth. |
| Secrets management | HashiCorp Vault or AWS Secrets Manager | — | Both support fine-grained per-path IAM and rotation. |
| Monitoring/metrics | Prometheus + Grafana | Datadog | Prometheus is the standard for this shape of system (many services, per-channel metrics); Datadog if you want a managed alternative and are willing to pay for it. |
| Logging/tracing | OpenTelemetry → Loki/Tempo (or Datadog) | ELK | OTel gives you the trace_id propagation described in §5 for free across services. |
| Dashboard | Next.js/React admin app talking to a read API over the Postgres rollups | Retool/internal tool builder | Custom gives you the drill-down UX in §14 of the spec; Retool is faster to bootstrap if you want an MVP dashboard in days not weeks. |
| YouTube | YouTube Data API v3 (OAuth per channel) | — | Only real option. |
| WhatsApp | WhatsApp Business Platform (Cloud API via Meta, or a BSP like Twilio) | — | Twilio is easier to integrate quickly; direct Meta Cloud API is cheaper at scale. |
| Video generation | FFmpeg/Remotion (deterministic renderer) driven by a "render spec" the Video Maker/Visuals agent produces; stock/generated assets from an image API as needed | Full generative video API | Deterministic assembly from planned assets is far cheaper, faster, and more controllable than end-to-end generative video for a channel that needs consistent visual identity and daily throughput. |
| Voice generation | A TTS provider (e.g. ElevenLabs or a cloud TTS) selected per channel's configured voice | — | Keep this pluggable per channel via config, not hardcoded. |
| Image/visual generation | Stock APIs first (cheaper, faster, more consistent) with generative image fallback for custom needs | — | Cost control — pure generative visuals for every frame of every video at 100-channel scale gets expensive fast. |


---

## 14. Dashboard Architecture

Read-only rollup API (`/api/dashboard/*`) backed by materialized views over the tables in §6, refreshed on a short interval (e.g. every 15–30s) rather than hitting live tables for every dashboard load. Drill-down matches spec §17:

```
GET /api/system/health
GET /api/channels                      -> list + status
GET /api/channels/{id}                 -> channel detail + agent statuses
GET /api/channels/{id}/agents/{agent}  -> agent detail + recent tasks
GET /api/channels/{id}/tasks/{task_id} -> task detail + full event log
GET /api/alerts?severity=critical
```

---

## 15. Folder / Project Structure

```
youtube-orchestration/
├── master_orchestrator/
│   ├── app.py                  # FastAPI service
│   ├── governor.py             # slot/resource allocation
│   ├── health_aggregator.py
│   ├── alerting.py
│   ├── analytics.py
│   └── llm_reasoning.py        # narrow LLM calls (strategy suggestions)
├── channel_manager/
│   ├── workflow.py             # Temporal workflow definition (pipeline FSM)
│   ├── dispatcher.py           # invokes agent tasks
│   ├── quality_check.py
│   ├── memory.py                # channel memory access layer
│   └── config_schema.py
├── agents/
│   ├── topic_generator.py
│   ├── script_writer.py
│   ├── voice_over.py
│   ├── video_planner.py        # LLM: produces render spec
│   ├── video_renderer.py       # deterministic: executes render spec
│   ├── youtube_uploader.py
│   └── whatsapp_notifier.py
├── common/
│   ├── message_schema.py       # pydantic models for the envelope in §5
│   ├── db/
│   │   ├── models.py
│   │   └── migrations/
│   ├── secrets.py              # secrets-manager client wrapper
│   ├── telemetry.py            # OTel setup
│   └── errors.py                # error classification (transient/permanent)
├── dashboard/
│   ├── api/                    # rollup endpoints
│   └── web/                    # Next.js app
├── config/
│   ├── channels/
│   │   ├── channel-001.yaml
│   │   └── channel-002.yaml
│   └── global.yaml
├── infra/
│   ├── terraform/
│   └── k8s/
└── tests/
    ├── unit/
    ├── integration/
    └── e2e/
```


---

## 16. Example Configuration File (`config/channels/channel-001.yaml`)

```yaml
channel_id: channel-001
name: "TechExplained Daily"
niche: "consumer tech explainers"
status: active

schedule:
  videos_per_day: 2
  preferred_hours_utc: [9, 16]

content_strategy:
  target_audience: "18-34, tech-curious, non-expert"
  tone: "energetic, clear, slightly humorous"
  video_length_minutes: [6, 9]
  approval_gates:
    topic: false
    script: false
    pre_upload: true      # human approves upload until channel is "trusted"

voice:
  provider: elevenlabs
  voice_id: "voice_ref_xyz"
  pace: "medium"

visual_style:
  template: "clean-tech-v2"
  brand_colors: ["#0B0B0F", "#38BDF8"]
  asset_source: stock_then_generated

credentials_ref:
  youtube: "vault://channel-001/youtube_oauth"
  whatsapp_recipient: "vault://channel-001/whatsapp_notify_target"

notifications:
  on_upload_success: true
  on_failure: true
  daily_summary: true
  weekly_summary: true
```

---

## 17. Example Agent Definition (Script Writer)

```python
# agents/script_writer.py
from common.message_schema import TaskEnvelope, AgentResult

SYSTEM_PROMPT_TEMPLATE = """You are the Script Writer for the YouTube channel "{channel_name}".
Tone: {tone}. Audience: {audience}. Target length: {length_min}-{length_max} minutes.
Follow the channel's brand voice exactly. Do not mention you are an AI.
Return structured JSON: {{"hook": "...", "sections": [...], "cta": "..."}}
"""

def run(envelope: TaskEnvelope) -> AgentResult:
    channel = envelope.payload["channel_config"]
    topic = envelope.payload["approved_topic"]

    prompt = SYSTEM_PROMPT_TEMPLATE.format(
        channel_name=channel["name"],
        tone=channel["content_strategy"]["tone"],
        audience=channel["content_strategy"]["target_audience"],
        length_min=channel["content_strategy"]["video_length_minutes"][0],
        length_max=channel["content_strategy"]["video_length_minutes"][1],
    )

    try:
        script = call_llm(prompt, user_input=topic["title"] + "\n" + topic["research_notes"])
        validate_script_schema(script)   # raises on malformed output
        return AgentResult(status="success", payload={"script": script})
    except TransientError as e:
        raise   # let Channel Manager's retry policy handle it
    except ValidationError as e:
        return AgentResult(status="failed", error={"type": "permanent", "message": str(e)})
```

---

## 18. Example Channel Manager Workflow (Simplified Temporal-Style Pseudocode)

```python
# channel_manager/workflow.py
async def channel_video_pipeline(task_id: str, channel_id: str):
    channel = load_channel_config(channel_id)

    topics = await gather([
        run_agent("topic_generator", channel, agent_id="tg1"),
        run_agent("topic_generator", channel, agent_id="tg2"),
    ])
    approved_topic = evaluate_and_select_topic(topics, channel)  # or human gate
    if channel.approval_gates.topic:
        approved_topic = await wait_for_human_approval(task_id, approved_topic)

    script = await run_agent("script_writer", channel, payload={"approved_topic": approved_topic})
    if channel.approval_gates.script:
        script = await wait_for_human_approval(task_id, script)

    voice_over, visual_plan = await gather([
        run_agent("voice_over", channel, payload={"script": script}),
        run_agent("video_planner", channel, payload={"script": script}),
    ])
    video = await run_agent("video_renderer", channel, payload={
        "visual_plan": visual_plan, "voice_over": voice_over
    })

    ok, failed_checks = quality_check(script, voice_over, video, channel)
    if not ok:
        await route_back_to_stage(failed_checks, task_id)
        return  # workflow re-entered at the failed stage

    if channel.approval_gates.pre_upload:
        await wait_for_human_approval(task_id, video)

    upload_result = await run_agent("youtube_uploader", channel, payload={"video": video, "script": script})
    await run_agent("whatsapp_notifier", channel, payload={"event": "upload_success", "result": upload_result})

    await report_to_master_orchestrator(task_id, channel_id, upload_result)
```


---

## 19. Example Master Orchestrator Workflow (Simplified)

```python
# master_orchestrator/health_aggregator.py
async def monitoring_loop():
    while True:
        for channel in registry.active_channels():
            health = await fetch_channel_health(channel.id)  # from channel.{id}.health topic snapshot
            upsert_channel_status(channel.id, health)

            if health.upload_failures_today > THRESHOLD:
                emit_alert(severity="critical", channel_id=channel.id,
                           message="Repeated upload failures")

            if health.status == "offline" and health.last_heartbeat_age_s > 300:
                emit_alert(severity="warning", channel_id=channel.id,
                           message="Channel Manager unresponsive")

        await update_global_dashboard_rollups()
        await sleep(30)

async def strategic_review_weekly():
    reports = collect_weekly_channel_reports()
    # narrow, deliberate LLM use — not a live control loop
    recommendation = await call_llm(
        "Given these per-channel performance summaries, identify the "
        "single highest-leverage cross-channel optimization.",
        data=reports
    )
    store_recommendation(recommendation)
    notify_admin(recommendation)
```

---

## 20. MVP Definition

To validate the architecture before building all 100 channels' worth of infra:

**MVP scope (Phase 0):**
1. One Channel Manager, one channel, all 6 agents, manual approval gates ON for everything.
2. Postgres schema from §6 (no sharding/RLS complexity yet — single schema).
3. No Temporal yet — a simple in-process async pipeline with a Postgres-backed task state table (durable enough to prove the flow).
4. No dashboard — CLI/logs + one Grafana panel.
5. Real YouTube upload to a real (test) channel, real WhatsApp notification.
6. Manual "add a second channel" to prove isolation (separate config, separate credentials, separate task queue) before automating the onboarding flow in §21 of the spec.

**Graduate to Phase 1 (multi-channel)** once: pipeline runs unattended for 5+ videos with <5% failure rate, quality checks catch the deliberately-broken test cases you throw at it, and cost-per-video is known and acceptable.

---

## 21. Scaling Strategy

- 1 → 10 channels: single Postgres instance, Redis Streams, single Master Orchestrator process. Channel Managers as Temporal workflows (cheap, no dedicated servers needed).
- 10 → 50: move to Kafka if event volume demands it; read replicas for Postgres; horizontally scale agent worker pools (they're stateless, trivially scalable).
- 50 → 100+: shard Postgres by channel_id range or move to a multi-tenant-aware managed DB; scale the render worker pool (usually the real bottleneck, not the LLM calls) with a GPU/CPU worker autoscaler; consider per-region deployment if channels target different geographies/latency needs.
- At every stage: the **governor** (§11) is what actually protects you from resource exhaustion — scale it thoughtfully rather than just adding capacity.

## 22. Cost-Control Strategy

- Per-task cost tracked in `cost_ledger` (LLM tokens, TTS minutes, render compute, API calls) — visible per channel in the dashboard.
- Budget caps per channel (`max_daily_cost_usd` in config) enforced by the governor — a channel that exceeds budget gets throttled, not silently left to overspend.
- Prefer smaller/cheaper models for high-volume, low-stakes steps (topic scoring, metadata generation) and reserve stronger models for script writing/quality-sensitive steps.
- Cache topic research and reuse across candidate scripts where possible; avoid redundant LLM calls for the same research.
- Stock-asset-first visual strategy (§13) to avoid per-frame generative image costs at scale.

## 23. Testing Strategy

- **Unit:** each agent function tested with mocked LLM/API responses, including malformed-output cases (script schema validation, TTS failure, etc.).
- **Integration:** Channel Manager workflow tested end-to-end against a sandboxed YouTube test channel and a WhatsApp sandbox.
- **Contract tests:** message envelope schema (§5) validated on both producer and consumer sides so a schema change can't silently break another service.
- **Chaos/failure injection:** deliberately fail one agent mid-pipeline and assert the failure is isolated (other channels unaffected, task recoverable, alert fired).
- **Load tests:** simulate N concurrent channels hitting the governor to confirm no thundering-herd against YouTube/TTS rate limits.

## 24. Deployment Architecture

- Containerized services (Docker) on Kubernetes: Master Orchestrator (2+ replicas, leader-elected for the scheduler part), Temporal cluster (or managed Temporal Cloud), agent worker pools (horizontally scaled Deployments with HPA on queue depth), dashboard API + web.
- Blue/green or canary deploys for agent workers so a bad prompt/model change can be rolled back without downtime.
- Secrets injected via the cluster's secrets-manager integration (e.g. Vault Agent sidecar / External Secrets Operator) — never baked into images.
- Separate environments: dev (fake YouTube/WhatsApp), staging (sandboxed real APIs), production.


---

## 25. Step-by-Step Implementation Plan

1. Stand up Postgres schema (§6) and secrets manager; define the message envelope (§5) as shared pydantic/protobuf models.
2. Build the 6 agent functions as pure, testable units against mocked providers.
3. Build the Channel Manager pipeline (MVP: simple async orchestrator, no Temporal yet) implementing the lifecycle in §4.
4. Wire one real channel end-to-end with all approval gates ON; validate against real YouTube/WhatsApp sandbox.
5. Add the quality-check gate (§12) and failure-routing logic (§9).
6. Add heartbeats + health rollups (§10) and a minimal dashboard (even just Grafana).
7. Turn approval gates OFF one at a time as confidence grows; measure failure rate.
8. Introduce the Master Orchestrator as a real service (health aggregator, alerting, governor) once you have ≥2 channels to coordinate.
9. Migrate Channel Manager to Temporal (or equivalent durable workflow engine) for crash-safety before scaling past a handful of channels.
10. Formalize the onboarding flow from spec §15 (`create config → register → provision credentials → start`) as an API + CLI command.
11. Add the full dashboard (§14/§17), cost ledger, and budget enforcement.
12. Load-test the governor, then scale channel count incrementally (10 → 50 → 100+), monitoring the render worker pool and API rate limits as the primary scaling constraints.
13. Add chaos tests and formalize the runbook for the escalation paths defined in §9.

---

## Summary of What Makes This Production-Grade (vs. a Prompt Collection)

- Master Orchestrator and Channel Manager are **real stateful services with durable state**, not prompts that "remember" via chat history.
- Agents are **narrow, stateless, retryable functions** — the intelligence is scoped tightly so failures are debuggable and costs are predictable.
- Isolation is enforced at the **infrastructure layer** (DB row-level security, per-channel secrets paths, per-channel queues) — not just by convention in application code.
- The pipeline is a **durable state machine**, so crashes are recoverable rather than requiring a full restart.
- Cost, health, and quality are **measured and gated**, not assumed.

