# Assitance - AI Assistant Platform

Assitance is a multi-purpose AI assistant platform offering flexible support for multiple LLM providers, including OpenAI, Anthropic Claude, Google Gemini, and local Ollama models. The architecture pairs a Python FastAPI backend with a modern React web interface, featuring a robust multi-agent orchestration system, document knowledge base (RAG), real-time heartbeat monitoring, and a node-based workflow engine.

## Latest Updates (2026-03-13)

### Phase 9: Orchestration Silence & Heartbeat Context Debugging 🚧 IN-PROGRESS
- **Janny Model Correction**: Updated the System Agent (Janny) from an invalid preview model to a stable Gemini 2.5 Flash ID in the database.
- **Orchestration Resiliency**: Refactored `OrchestrationEngine` with centralized model resolution and robust error handling for delegation turns.
- **Tool Context Debugging**: Investigating `agent_id` propagation issues in `ChatService` and adding execution tracing to `ScheduleTool`.

### Phase 8: Heartbeat Transparency, Autonomous Scheduling & Brave Search ✅ COMPLETED
- **Centralized Resolution**: `ModelRegistryService` ensures limits are linked to canonical models via DB lookups.
- **Dynamic Enforcement**: `LLMGateway` puls RPM/TPM/RPD limits per-request with adaptive 5s retry loops.
- **HUD & Sidebar Overhaul**: Redesigned the `ChatSidebarDashboard` to match the premium aesthetics of the main system dashboard, including real-time progress bars and pulsing status indicators.
- **System Health Restoration**: Fixed the global RPM/TPM reporting by unifying the `RateLimitManager` singleton and registering missing models like `gemini-3.1-flash-lite`.
- **Performance Optimization**: Increased autonomous loop and tool execution timeouts to resolve bottlenecks in complex data aggregation tasks.
- **Environment Sync**: Recreated the backend virtual environment and aligned all hardcoded ports to `8322`.

### Phase 6: Observability & Rate Limit Calibration ✅ COMPLETED
- **Live Chat Dashboards**: Real-time System Metrics (RPM/TPM), Active Tasks, and Recent Workflows merged into the chat sidebar.
- **Model Resolution Calibration**: Fixed agent model precedence and specific Gemini 3.1 Flash Lite model resolution issues.
- **Editable Model Registry**: New dashboard in Settings -> Capabilities to edit RPM, TPM, and Context Window per model.
- **Unlimited Rate Limits**: Support for blank values to set "unlimited" (null) rate limits, bypassing local throttling.
- **Model Registry Cleanup**: Redundant legacy Gemini 2.5 models removed for a cleaner model selection.

### Phase 1-5: Previous 2026-03-12 Updates

### Phase 1-2: Per-Agent Context Window Controls ✅ COMPLETED
- **Per-Agent Configurable Limits**: Each agent has its own context window setting (60k-256k tokens) via a dedicated slider in Agent Settings.
- **Database Persistence**: `context_window_tokens` field in agents table with alembic migration v9f32a1b6aa10.
- **Prune-Only Sync**: Identity, Soul, and Mind are refreshed **only when pruning occurs**, never sent preemptively.

### Phase 3: Context Pruning System Upgrade ✅ COMPLETED
- **Three-Threshold Model**: SOFT (60%) warns, ACTIVE (80%) summarises, EMERGENCY (99%) hard-truncates.
- **Dynamic Recent Window**: 6k-token budget for recent messages (floor=3, ceiling=10 messages).
- **Summary Drift Protection**: `SummaryManager` extends existing summaries instead of re-summarising them.
- **Multi-Agent Safe**: Agent identities and delegation history preserved through pruning.
- **ContextAssembler**: Layered context: System Prompt → Semantic Memory → Task State → Turns.

### Phase 4: Multi-Agent Memory + Agent Limit Architecture ✅ COMPLETED
- **Hard Agent Cap**: `MAX_AGENTS = 60` system-wide; `POST /agents` returns HTTP 429 when at capacity.
- **Redis Agent Registry**: `agents:active` SET; `SADD` on create, `SREM` on delete, `sync_from_db()` at startup.
- **3-Tier Memory**: Active context (in-LLM) → Semantic Memory (`agent_memories` table) → Archive (`conversation_archive` table).
- **MemoryCompactor**: LLM extracts `fact/decision/summary` objects from 20-message chunks; ~70% token reduction.

### Phase 5: Agent Lifecycle, Memory Wiring & Observability ✅ COMPLETED
- **Agent Lifecycle Status**: `active | idle | paused | deleted` — soft delete frees capacity without destroying the row.
- **Memory Pipeline Active**: Semantic memory now injected into **all 3 chat paths** before every LLM call.
- **Token Budget System**: Context window partitioned: System 10% / Recent 30% / Semantic 20% / User 10% / Reasoning 30%.
- **Redis Context Buffer**: `memory:agent:{id}:context` key (24h TTL) for active conversation caching.
- **Full Observability**: `/system/metrics` exposes `agent_capacity`, token usage, compaction rate, pruning counters.


## Features

### Core
- **Multi-Provider Support**: Seamlessly switch between OpenAI, Anthropic, Google Gemini 2.5/3.0, and Ollama.
- **Agent System**: Create and manage specialized AI agents with distinct personalities (Soul/Mind/Memory), instructions, and enabled tools.
- **Persistent Agent Model**: Agents are persistent digital workers — not temporary task executors. Each agent has four internal layers:
  - **Soul**: Personality traits, tone, and behavioral style.
  - **Mind**: Reasoning style, planning strategy, and decision rules.
  - **Memory**: Long-term knowledge, past tasks, and learned context that accumulate over time.
  - **Identity**: Unique role and group membership within the system.
  - **Agent Discovery**: Search agents by role, tools, group, or capability via `GET /api/agents/discover`.
  - **Agent Evolution**: Agents learn and evolve after tasks via `POST /api/agents/{id}/evolve`, appending to memory and strategy.
  - **Creation Safety Limits**: Maximum **60** total agents. HTTP 429 returned when at capacity. Soft-delete frees capacity (row retained for audit). `can_create_agent()` uses Redis fast-path (O(1) SCARD) then DB count as fallback.
  - **Lifecycle States**: Agents transition through `idle → working → learning → offline` states tracked in real-time.
- **Tool Sandbox**: Agents have access to built-in tools like Web Search, File Management, Python Code Execution, Command Execution, and Date/Time utilities.
- **Knowledge Base (RAG)**: Upload documents (PDF, TXT, MD) which are automatically chunked, embedded, and stored in ChromaDB for AI reference.
- **Workflow Engine**: A robust DAG-based visual workflow editor (ReactFlow) supporting 20+ dynamic node types (Agent Calls, Logic Branching, HTTP Requests). Includes real-time execution observability via WebSockets and agent-integrated workflow actions (agents can natively generate and execute workflows).
- **Voice I/O**: Continuous conversational immersive Voice Mode overlay. Speech-to-text natively using Gemini 2.5 Flash backend, text-to-speech auto-read responses via edge-tts.
- **Modern UI**: A responsive, dark-themed React frontend featuring real-time streaming, interactive agents dashboard, and glassmorphism styling.

### Multi-Agent Orchestration
- **Unified Channel Chat**: Single chat system merging previous P2P and LLM modes. All group communication flows through unified channels.
- **@mention-Selective Routing**: Only agents explicitly tagged with `@AgentName` respond to a message. Type `@` for an autocomplete dropdown with agent status dots.
- **System Agent Orchestration**: The System Agent acts as a master orchestrator with hybrid auto/manual delegation modes.
  - **Autonomous mode**: System Agent analyzes tasks, produces a JSON delegation plan with `group_id` for parallel execution, runs agent groups concurrently via `asyncio.gather`, and synthesizes a final aggregated response.
  - **Manual mode**: Only the System Agent responds unless explicit @mentions are used.
- **Parallel Agent Execution**: Agents within the same `group_id` execute concurrently with proper fan-out workflow edges, frozen payload snapshots, and per-agent error handling (`return_exceptions=True`).
- **Orchestration Plan Display**: Visual plan banner showing delegation steps with active step highlighting.
- **Delegation Chain Graph**: Real-time ReactFlow-based node graph showing the execution chain (User -> System -> Agent A -> Agent B) with animated edges and status indicators. Supports parallel fan-out visualization.
- **Strict Communication Rules**: Standard agents cannot DM each other, cannot self-assign tasks, and can only respond when @mentioned. Only System Agent can delegate.
- **Safety Limits**: Max delegation depth (5), circular invocation detection, configurable token budget per chain (100k default), and task timeout handling.
- **6-Stage Task Lifecycle**: Tasks progress through PLAN → DECOMPOSE → ASSIGN → EXECUTE → VERIFY → FINALIZE stages with full observability.
- **Capability-Based Routing**: Agent selection uses weighted scoring (domain expertise, tool overlap, success rate) via CapabilityRegistry.
- **Three-Layer Memory**: Working Memory (ephemeral), Episodic Memory (task summaries), Long-Term Memory (ChromaDB vector search).
- **Distributed Priority Queue**: Redis-backed task queue with URGENT/NORMAL/LOW priorities, distributed locking, and dead-letter handling.
- **Skill Discovery & Governance**: Agents can discover reusable patterns from task execution. Skills follow a governance lifecycle (proposed → sandbox testing → security review → approved → deployed).
- **Autonomous Agent Execution Loop**: Implements a continuous **PLAN → ACT → OBSERVE → REFLECT → UPDATE PLAN** cycle via `AutonomousExecutionLoop`. Complex tasks are auto-upgraded from single-turn to multi-step execution (up to 6 steps, 15 tool calls, 120s timeout). Includes LLM-based completion detection, step history tracking, and real-time autonomous step events streamed to the UI. Backed by the **Tool Governor** to halt infinite repetitive tool failures and **Supervisor Fallback** to reassign deadlocked tasks.
- **Gemini 2.0 Thought Persistence**: Robust handling of Gemini's `thought` and `thought_signature` fields, enabling seamless multi-turn tool calling without API crashes.
- **Task Execution Monitor**: Real-time Heads-Up-Display tracking active task Planner states, Steps, and Tokens used dynamically linked to active tasks.
- **Orchestration Execution History**: Guaranteed persistence of delegated agent tasks as dynamically generated Workflows, now fully trackable and inspectable via the Workflows Dashboard.

### Master Heartbeat Architecture
The platform is supervised by a centralized `MasterHeartbeat` service that runs a continuous 2-second tick loop, coordinating five distinct sub-monitors:
- **Agent Monitor**: Detects stalled or unresponsive agents (20s timeout), initiating restart and auto-reassignment to the System Agent.
- **Task Monitor**: Ensures tasks to not hang indefinitely. Warns at 60s of inactivity, reassigns at 90s, and escalates at 120s.
- **Workflow Monitor**: Tracks active DAG node executions, detecting stuck nodes (90s timeout) and executing a `retry -> skip -> reroute` recovery strategy.
- **Resource Monitor**: Tracks API rate-limit utilization (RPM/TPM/RPD) and strictly enforces a 4-tier concurrency throttling system (Normal -> Warn -> Throttle -> Critical) based on utilization thresholds.
- **Communication Monitor**: Ensures no message or mention is ignored. Tracks unacknowledged `@mentions` (5s timeout), pending broadcast announcements, and message queue latency.
- **Execution Watchdog**: A hard limit circuit breaker that forcefully terminates any agent task exceeding 10 minutes to prevent infinite loops.
- **Frontend Dashboard**: A live 'System Health' panel integrated directly into the UI via the `/api-ws/agents/status` WebSocket, visualizing agent states, active workflows, and resource limits in real-time.

### Safety & Intelligence
- **Human-in-the-Loop (HITL)**: Sensitive tool executions (code, commands) pause and wait for user approval via a contextual inline chat UI widget.
- **Execution Observability**: Transient loading states ("Waiting for tool...") and persistent colored log cards render directly within the chat for all autonomous and user-approved tool executions.
- **Token Economy & Cost Tracking**: Real-time token usage parsing and cost calculation per agent, streamed to the UI.
- **Context Window Pruning**: Per-agent pruning with configurable 60k-256k windows. **Three-threshold model** (60% soft warn → 80% active prune → 99% emergency truncate). Semantic memories from prior sessions (Tier 2) injected before each LLM call. Token budget partitioned: System 10% / Recent 30% / Semantic 20% / User 10% / Reasoning 30%.
- **Self-Correction**: Tool errors are fed back to agents for automatic retry and self-correction.
- **Secret Protection**: API keys encrypted at rest using Fernet symmetric encryption. Keys accessed only through SecretManager.
- **Security Hardening**: Docker containers run read-only with all capabilities dropped. Command executor blocks dangerous patterns (`rm -rf`, `format`, etc.).
- **Storm Prevention**: Maximum 3 simultaneous responding agents in group chat, enforced via semaphore.

### Integrations & Automation
- **Omnichannel**: Telegram, Discord, Slack, and WhatsApp adapter support.
- **Proactive Heartbeat Schedules**: Background scheduled agent tasks at configurable intervals.
- **Skill Marketplace**: Pre-built skill catalog with one-click install.
- **Agent-Driven Tool/Skill Creation**: Agents can create custom tools and skills during conversations.
- **Worker Container Pool (Docker)**: High-performance, pre-warmed pool of long-lived Docker containers (`crossclaw-worker`) containing full dev environments (Python, Node, Git, Playwright) avoiding cold-start latency. 
- **Subprocess Execution Fallback**: Instant local subprocess code execution fallback when Docker is unavailable on the host machine.

## Tech Stack

- **Backend**: Python 3.12, FastAPI, Uvicorn, SQLAlchemy (Async), PostgreSQL (asyncpg) / SQLite (aiosqlite), Alembic, ChromaDB, Redis
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS v4, Zustand, ReactFlow, Framer Motion
- **AI SDKs**: `openai`, `anthropic`, `google-genai`, `httpx` (Ollama)

## Prerequisites

- [uv](https://github.com/astral-sh/uv) (for Python package management)
- Node.js (for frontend npm management)
- Redis server (for heartbeat and real-time state; optional -- falls back to in-memory if unavailable)
- PostgreSQL 16+ (for production; SQLite used as fallback for development). Docker: `docker run -d --name assitance-db -e POSTGRES_USER=assitance -e POSTGRES_PASSWORD=assitance -e POSTGRES_DB=assitance -p 5432:5432 postgres:16-alpine`
- Optional: Local Ollama instance running if you intend to use local models.
- Optional: Docker for containerized code execution sandboxing.

## Code Quality & Strict Linting
The platform adheres to strict structural and typological standards:
- **Backend**: Strict compliance with `ruff` formatting, eliminating all cross-module implicit imports and large `E701` violations. Run `uv run ruff check .` to verify 0 errors.
- **Frontend**: Strict compilation and `eslint` enforcement via `TypeScript`. Run `npm run lint` and `tsc -b` to guarantee 0 errors and 0 warnings. All `any` types are either replaced with proper types/`unknown` or suppressed with `// eslint-disable-next-line @typescript-eslint/no-explicit-any` where `any` is genuinely required (e.g., ReactFlow node types, deeply-nested API responses, HTML input value bindings).
- **Production Build**: `npm run build` produces a clean Vite binary (`✓ built in ~10s`). Always run `tsc -b && npm run build && npm run lint` as a triple-check before shipping.
- **Database Migrations**: Alembic baseline established at revision `fc305b3c7c1b`. Run `uv run alembic revision --autogenerate -m "description"` for any schema changes. Run `uv run alembic upgrade head` to apply.

## How to Run Locally

To run the project, you need to spin up Redis (optional), the backend, and the frontend.

### 0. Redis (Optional)

```bash
# Using Docker
docker run -d -p 6379:6379 redis:alpine

# Or install natively for your platform
```

### 0b. PostgreSQL (Production)

For production deployments, use PostgreSQL:

```bash
docker run -d --name assitance-db \
  -e POSTGRES_USER=assitance \
  -e POSTGRES_PASSWORD=assitance \
  -e POSTGRES_DB=assitance \
  -p 5432:5432 postgres:16-alpine

# After starting the backend dependencies, run migrations:
cd backend && uv run alembic upgrade head
```

*SQLite is used by default for development (no PostgreSQL required).*

### 1. Backend Setup & Run

The backend API runs on port 8321.

```bash
cd backend

# Install dependencies and start the FastAPI server via uv
uv run uvicorn app.main:app --host 127.0.0.1 --port 8321
```

*The Swagger API documentation will be available at `http://127.0.0.1:8321/docs`.*

### 2. Frontend Setup & Run

The frontend React app connects to the proxy at port 8321.

```bash
cd frontend

# Install dependencies (only required the first time)
npm install

# Start the Vite development server
npm run dev
```

*Your frontend will typically be accessible at `http://localhost:5173` (or the port Vite outputs in the console).*

## Configuration

Environment variables and API keys can be configured in two ways:
1. Creating a `.env` file in the `backend/` directory (you can copy `.env.example`).
2. Live via the **Settings** panel in the frontend web interface.

Supported environment variables:
- `ASSITANCE_OPENAI_API_KEY`
- `ASSITANCE_ANTHROPIC_API_KEY`
- `ASSITANCE_GEMINI_API_KEY`
- `ASSITANCE_OLLAMA_BASE_URL` (defaults to http://localhost:11434)
- `ASSITANCE_REDIS_URL` (defaults to redis://localhost:6379/0)
- `ASSITANCE_DATABASE_URL` (defaults to sqlite+aiosqlite:///./data/assitance.db; for PostgreSQL: postgresql+asyncpg://assitance:assitance@localhost:5432/assitance)
- `ASSITANCE_SECRET_KEY` (Fernet encryption key for API key protection; auto-generated if not set)

## Architecture Notes

- The project supports PostgreSQL (production) and SQLite (development). Database URL is configurable via `ASSITANCE_DATABASE_URL`. Migrations are managed via Alembic (`cd backend && uv run alembic upgrade head`). Connection pooling: pool_size=20, max_overflow=10 for PostgreSQL.
- Redis is used for real-time agent heartbeats, task queue state, and delegation chain tracking. If Redis is unavailable, the system gracefully falls back to in-memory operation.
- The Knowledge Base vector database is stored locally via `ChromaDB` inside the backend directory.
- The Orchestration Engine creates delegation chains with depth limits and circular invocation detection to prevent runaway agent loops.
- The UI features a unified channel chat with @mention-selective routing, replacing the previous dual P2P/LLM system.
- API keys are encrypted at rest using Fernet symmetric encryption via `SecretManager`. Keys are never stored in plaintext.
- Agent task routing uses a capability-based scoring system (CapabilityRegistry) weighing domain expertise, tools, and success rate.
- Three-layer agent memory: Working Memory (ephemeral), Episodic Memory (task summaries), Long-Term Memory (ChromaDB vectors).
- Task lifecycle follows 6 stages: PLAN → DECOMPOSE → ASSIGN → EXECUTE → VERIFY → FINALIZE.
- Distributed task queue uses Redis ZADD sorted sets with URGENT/NORMAL/LOW priorities and SETNX locking.
- Skill governance lifecycle: PROPOSED → SANDBOX_TESTING → SECURITY_REVIEW → APPROVED → DEPLOYED.

## API Endpoints

| Category | Endpoints |
|----------|-----------|
| Health | `GET /api/health` (includes agent statuses, task/chain counts) |
| Chat | `POST /api/chat`, `WS /ws/chat/{id}` |
| Agents | `CRUD /api/agents`, `GET /api/agents/discover`, `POST /api/agents/{id}/evolve`, `POST /api/agents/generate-personality` |
| Channels | `CRUD /api/channels`, agent assignment |
| Tasks | `GET /api/tasks/active`, `GET /api/tasks/{id}` |
| Chains | `GET /api/chains/active`, `GET /api/chains/{id}` |
| Knowledge | `GET/POST/DELETE /api/knowledge` |
| Workflows | `CRUD /api/workflows` |
| Tools | `GET /api/tools`, `CRUD /api/custom-tools` |
| Skills | `CRUD /api/skills`, marketplace |
| Integrations | `CRUD /api/integrations` |
| Schedules | `CRUD /api/schedules` |
| System | `GET /api/system/dashboard`, `GET /api/system/containers` |

## License

Private / All Rights Reserved.
