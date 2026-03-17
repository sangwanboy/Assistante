# Changelog

## 2026-03-17 — Runtime Stability Snapshot: Phase 16

### Context Sync
- Synchronized project context memory after full platform QA pass to preserve a clean handoff baseline.

### Authoritative Runtime Ports
- Frontend dev server: `127.0.0.1:5173`
- Backend API server: `127.0.0.1:8321`

### Proxy and WebSocket Alignment
- Confirmed frontend API proxy and agent-status WebSocket must target backend port `8321` (not `8322`).
- This alignment resolves repeated API error toast floods and missing live agent status updates.

### Health Baseline
- Verified core API paths are reachable via frontend proxy:
  - `/api/agents`
  - `/api/system/dashboard`
  - `/api/system/metrics`
  - `/api/tools`
  - `/api/workflows`

### Environment Note
- Redis may be unavailable locally; backend runs in in-memory fallback mode and remains operational for UI workflows.

## 2026-03-13 — Observability & Rate Limit Calibration: Phase 6 Completion

### Live Chat Dashboards
- Integrated **System Metrics**, **Active Tasks**, and **Recent Workflows** into a unified dashboard component in the Chat sidebar.
- Enabled real-time 5-second polling for global RPM/TPM and agent-specific resource usage.
- Added smooth transitions and interactive stat cards for task and workflow monitoring from within any chat session.

### Model Registry & Capability Controls
- **Editable Capabilities**: Added support for updating `rpm`, `tpm`, and `context_window` directly via the Settings dashboard.
- **Unlimited Rate Limits**: Updated database schema and API to support `NULL` values for rate limits. Empty input fields now translate to "Unlimited", bypassing local throttling logic.
- **PUT /api/models/{model_id}/capability**: New endpoint for persistent capability updates in the SQLite/PostgreSQL registry.
- **Improved Validation**: Frontend validation ensures only numbers or blank values are accepted, while backend `ModelCapabilityUpdate` schema handles optional fields.

### Resolution & Registry Cleanup
- **Gemini Model Calibration**: Fixed a bug where `agent.model` precedence was ignored. Corrected `Gemini 3.1 Flash Lite` name resolution for native audio and high-concurrency tasks.
- **Registry Vacuuming**: Removed redundant Gemini 2.5 and legacy Ollama models from the default registry to reduce UI clutter and selection errors.
- **Diagnostic Scripts**: Added `backend/cleanup_models.py` and `backend/list_db_models.py` for persistent registry health monitoring.


## 2026-03-12 (part 3) — Multi-Agent Memory Architecture: Phase 5 Completion

### Agent Lifecycle Status (Section 4)
- Added `status: str` column to `agents` table (`active | idle | paused | deleted`).
  - `active`  — fully operational, receives tasks
  - `idle`    — waiting; capacity still reserved
  - `paused`  — temporarily suspended; capacity reserved
  - `deleted` — soft-deleted; frees capacity via Redis SREM
- Added `AgentStatus` enum class to `app/models/agent.py`.
- **Soft Delete**: `DELETE /agents/{id}` now sets `status='deleted'` and `is_active=False` instead of hard-deleting the row (capacity freed via Redis SREM; row retained for audit).
- `list_agents` and `discover_agents` filter out `status='deleted'` agents.
- `get_total_agent_count()` now counts `WHERE status != 'deleted'` (only non-deleted agents consume capacity).
- New Alembic migration `b4c9e2a7f1d3_add_agent_status_lifecycle.py` — idempotent, backfills existing rows.

### Token Budget Management (Section 10)
Added five `TOKEN_BUDGET_*` constants in `chat_service.py` that define how each layer of the context window is allocated:
```
TOKEN_BUDGET_SYSTEM_PCT        = 0.10   (10%) system prompt
TOKEN_BUDGET_RECENT_PCT        = 0.30   (30%) recent conversation turns
TOKEN_BUDGET_SEMANTIC_MEM_PCT  = 0.20   (20%) Tier-2 semantic memory injection
TOKEN_BUDGET_USER_MSG_PCT      = 0.10   (10%) current user message
TOKEN_BUDGET_REASONING_PCT     = 0.30   (30%) model reasoning buffer
```
All five sum to exactly 1.0 (100% of `context_window_tokens`).

### Memory Retrieval Pipeline Wired (Sections 6, 7, 9)
`MemoryCompactor` and `ContextAssembler` are now active in every chat path:
- `ChatService.__init__` instantiates `self.compactor` and `self.assembler`.
- New `ChatService._build_context_with_memory(agent, prompt, messages, cw_tokens)`:
  1. Calls `MemoryCompactor.retrieve_for_context()` to fetch Tier-2 semantic memories.
  2. Applies semantic memory token budget (`cw_tokens × 0.20`).
  3. Calls `ContextAssembler.build()` to inject memory as a dedicated system layer.
- Applied to **all 3 chat paths**: non-streaming (`chat()`), streaming (`stream_chat()`), and group multi-agent (`_handle_agent_turn()`).

### Redis Context Buffer (Section 8)
- Added `CONTEXT_CACHE_KEY = "memory:agent:{agent_id}:context"` to `memory_compactor.py`.
- Added `CONTEXT_CACHE_TTL = 86400` (24 hours).
- New `MemoryCompactor.cache_context(agent_id, messages)` — writes context to Redis, excludes system messages, TTL 24h.
- New `MemoryCompactor.get_cached_context(agent_id)` — reads from Redis; returns `list[dict]` or `None`.
- `MemoryCompactor.__init__` now accepts optional `redis_client` parameter for Redis-backed caching.

### Observability Metrics (Section 14)
`GET /system/metrics` completely rebuilt:
- `active_agents` / `total_agents` now correctly differentiated using `status` field.
- `agent_capacity: {used, limit: 60, used_pct}` — shows how full the 60-agent system is.
- `token_usage_per_request` — current sliding-window TPM from rate limiter.
- `total_tokens_estimated` — from agent `total_cost` (budget model proxy).
- `memory_compaction.memories_created_24h` — SemanticMemory rows created in last 24 hours.
- `memory_compaction.rate_per_hour` — compaction rate normalized per hour.
- `pruning_events: {soft, active, emergency, total}` — live counters from `pruning_events.py`.

`pruning_events.py` now maintains module-level counters (`_counters`) incremented in `emit()`:
- `soft` / `active` / `emergency` / `total` — resets on process restart.
- `get_counters()` function returns a snapshot dict for the metrics endpoint.

### Dashboard Endpoint Update
`GET /system/dashboard` now uses `status` field for agent counts:
- `agents.total` — all non-deleted agents.
- `agents.active` — agents with `status in (active, idle)`.
- `agents.capacity_pct` — percentage of 60-agent limit consumed.



### Hard Agent Cap (60)
- `agent_limits.py`: `MAX_AGENTS_TOTAL` set to **60** (hard system limit covering active, idle, and paused agents).
- `POST /agents` now calls `can_create_agent()` before insert; returns **HTTP 429** with `AGENT_LIMIT_REACHED` detail when at capacity.
- `DELETE /agents/{id}` removes agent from the Redis registry, freeing capacity immediately.
- `can_create_agent()` accepts optional `redis_client`; performs Redis fast-check first, then definitive DB count.

### Redis Agent Registry
- New `backend/app/services/redis_agent_registry.py` — maintains `agents:active` Redis SET.
  - `SADD agents:active {agent_id}` on create.
  - `SREM agents:active {agent_id}` on delete.
  - `SCARD agents:active` — O(1) capacity pre-check.
  - `sync_from_db()` populates the SET from DB at startup (transparent across restarts).
  - `app.state.agent_registry` exposed on the FastAPI app state.

### Semantic Memory Compaction (Tier 2)
- New DB tables in `backend/app/models/agent_memory.py`:
  - `agent_memories` (`SemanticMemory`): extracted knowledge — `memory_type` / `topic` / `summary` / `embedding` (JSON float[]).
  - `conversation_archive` (`ConversationArchive`): full raw message archive — never sent to LLM.
- New `backend/app/services/memory_compactor.py` (`MemoryCompactor`):
  - Chunks older messages (20 per batch); extracts `fact | decision | summary` objects via cheap LLM.
  - Persists to `agent_memories`; archives raw to `conversation_archive`.
  - `retrieve_for_context()` builds a concise Tier-2 injection block for the system prompt.
  - Target: **~70 % token reduction** vs full history replay.

### Context Pruning Tuning
- `context_pruner.py` default `prune_trigger_ratio` updated **0.9 → 0.8** (spec: prune at 80 % of limit).

### 3-Tier Memory Architecture
| Tier | Store | Sent to LLM |
|------|-------|-------------|
| 1 — Active context | In-LLM (system prompt + last 5 messages) | Yes |
| 2 — Semantic memory | `agent_memories` (PostgreSQL) | Selected excerpts |
| 3 — Archive | `conversation_archive` (PostgreSQL) | No |



### Reliability and Runtime
- Improved chat WebSocket stability on frontend:
  - Reuse existing OPEN/CONNECTING socket for the same conversation.
  - Added heartbeat ping every 25 seconds.
  - Added reconnect backoff and robust timer cleanup on close/disconnect.
- Improved backend WebSocket streaming behavior:
  - Expected client disconnects now exit cleanly without noisy error cascades.
  - Disconnect-safe error-send path added.

### Error Logging and Signal Quality
- Confirmed rotating backend error log path at `backend/logs/app_error.log`.
- Reduced false alarm logging in LLM gateway:
  - Expected provider issues (quota/key/not-configured) downgraded to warning.
  - Unexpected provider/runtime failures remain error with traceback.

### Orchestrator Behavior
- Added deterministic contribution-recall handling for system-agent follow-up questions.
- Added intent gating so contribution queries are not misclassified as delegation commands.
- Improved delegation objective recovery for rerun/delegate control prompts.

### Agent Context Window Controls
- Added per-agent context window setting with a configurable range of 60k to 256k tokens.
- Agent settings UI now includes a slider for the context window / prune limit.
- Pruned conversations now carry the refreshed agent prompt plus prune-only sync metadata.
- Identity, Soul, and Mind are no longer re-sent just because context is large; they are re-synced only when pruning actually happens.

### Context Pruning System Upgrade (Phase 3) — COMPLETED

#### Three-Threshold Model
- **Soft (60%)** — log warning via `pruning_events.py`, no structural change (<1 ms).
- **Active (80%)** — summarise middle messages, refresh system prompt, emit INFO event.
- **Emergency (99%)** — hard truncate to system messages + last 3 turns, emit ERROR event.
- Old single `CONTEXT_PRUNE_TRIGGER_RATIO = 0.9` replaced by three constants in `chat_service.py`.
- All 3 call sites (non-stream, stream, group) updated to pass all three thresholds.

#### Dynamic Recent Token Window
- Replaced fixed 5-message keep count with a **6 000-token budget** calculation.
- `_calculate_keep_recent()`: keeps between 3 (floor) and 10 (ceiling) messages that fit the budget.
- Long messages → fewer kept; short messages → more kept, up to 10.

#### Multi-Agent Safe Summaries (`summary_manager.py`)
- Detects agent names via `[AgentName]:` patterns and explicit delegation history.
- Preserves all agent identities and contributions in the summary output.
- **Drift protection**: splits history at existing `[CONTEXT PRUNED SUMMARY]` blocks and extends rather than re-summarising.
- Preserves `[DELEGATION HISTORY]` chain in summary footer.

#### Layered Context Architecture (`context_assembler.py`)
- `ContextAssembler.build()` layers the context in order:
  `System Prompt → Semantic Memory → Task State → Conversation Turns`
- `inject_task_state()` and `inject_semantic_memory()` helpers for targeted injection.
- `TaskState` dataclass encapsulates task_id, status, progress %, delegated agents, workflow state.

#### Tool Result External Storage (`tool_memory_store.py`)
- Tool results > 10 KB compressed to `TOOL_RESULT_ID:{uuid} (tool=..., size=...)`.
- In-memory store (default) + Redis backend with 1-hour TTL.
- `expand_references()` restores full content on demand for retrieval flows.
- Opt-in: not wired into default chat flow; activate by calling `store.maybe_compress(messages)`.

#### Structured Observability (`pruning_events.py`)
- `PruneEvent` dataclass: agent_id, trigger_type, tokens_before/after, messages_before/after, summary_token_size, elapsed_ms, reduction_pct.
- Log routing: soft→DEBUG, active→INFO, emergency→ERROR.
- Attach a custom handler to the `pruning_events` logger to push events to Redis / WebSocket / Prometheus.

#### New Files
| File | Purpose |
|------|---------|
| `app/services/pruning_events.py` | Structured event logging |
| `app/services/summary_manager.py` | Multi-agent safe + drift-protected summarisation |
| `app/services/context_assembler.py` | Layered context builder + task state injection |
| `app/services/tool_memory_store.py` | TOOL_RESULT_ID extraction + external storage |

### Documentation Sync
- Updated project memory/docs to capture all above changes:
  - `CONTEXT_MEMORY.txt` — Phase 1-2 completion details + Phase 3 12-point specification with insertion points
  - `README.md` — Enhanced Latest Updates with prune-only sync behavior clarification
  - `App Documentation` — Comprehensive Phase 1-2 feature overview + Phase 3 architecture blueprint
