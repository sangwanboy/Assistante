# Assitance - AI Assistant Platform

Assitance is a multi-purpose AI assistant platform offering flexible support for multiple LLM providers, including OpenAI, Anthropic Claude, Google Gemini, and local Ollama models. The architecture pairs a Python FastAPI backend with a modern React web interface, featuring a robust multi-agent orchestration system, document knowledge base (RAG), real-time heartbeat monitoring, and a node-based workflow engine.

## Features

### Core
- **Multi-Provider Support**: Seamlessly switch between OpenAI, Anthropic, Google Gemini, and Ollama.
- **Agent System**: Create and manage specialized AI agents with distinct personalities (Soul/Mind/Memory), instructions, and enabled tools.
- **Tool Sandbox**: Agents have access to built-in tools like Web Search, File Management, Python Code Execution, Command Execution, and Date/Time utilities.
- **Knowledge Base (RAG)**: Upload documents (PDF, TXT, MD) which are automatically chunked, embedded, and stored in ChromaDB for AI reference.
- **Workflow Engine**: A node-based visual workflow editor (ReactFlow) supporting triggers (webhooks, etc.) and AI actions (summarize, email draft, notify).
- **Modern UI**: A responsive, dark-themed React frontend featuring real-time streaming, interactive agents dashboard, and glassmorphism styling.

### Multi-Agent Orchestration
- **Unified Channel Chat**: Single chat system merging previous P2P and LLM modes. All group communication flows through unified channels.
- **@mention-Selective Routing**: Only agents explicitly tagged with `@AgentName` respond to a message. Type `@` for an autocomplete dropdown with agent status dots.
- **System Agent Orchestration**: The System Agent acts as a master orchestrator with hybrid auto/manual delegation modes.
  - **Autonomous mode**: System Agent analyzes tasks, produces a JSON delegation plan, chains agent execution, and synthesizes a final aggregated response.
  - **Manual mode**: Only the System Agent responds unless explicit @mentions are used.
- **Orchestration Plan Display**: Visual plan banner showing delegation steps with active step highlighting.
- **Delegation Chain Graph**: Real-time ReactFlow-based node graph showing the execution chain (User -> System -> Agent A -> Agent B) with animated edges and status indicators.
- **Strict Communication Rules**: Standard agents cannot DM each other, cannot self-assign tasks, and can only respond when @mentioned. Only System Agent can delegate.
- **Safety Limits**: Max delegation depth (5), circular invocation detection, configurable token budget per chain (100k default), and task timeout handling.

### Three-Layer Heartbeat Architecture
- **Layer 1 - Agent Process Heartbeat**: Redis pub/sub based heartbeat with 60s TTL. Agents transition through states: `offline -> initializing -> idle -> busy -> error`.
- **Layer 2 - Task Execution Heartbeat**: Per-task progress tracking (0-100%) with checkpoints, timeout detection, and auto-retry (up to 3 retries).
- **Layer 3 - Delegation Chain Heartbeat**: Chain lifecycle tracking (active/completed/halted/failed) with depth and agent involvement monitoring.
- **Recovery Protocol**: Automatic task requeue on agent failure, escalation after 3 consecutive failures, failure count reset on success.

### Safety & Intelligence
- **Human-in-the-Loop (HITL)**: Sensitive tool executions (code, commands) pause and wait for user approval via inline chat UI.
- **Token Economy & Cost Tracking**: Real-time token usage parsing and cost calculation per agent, streamed to the UI.
- **Context Window Pruning**: Automatic summarization of old conversation history to prevent context overflow.
- **Self-Correction**: Tool errors are fed back to agents for automatic retry and self-correction.
- **Voice I/O**: Speech-to-text via Gemini 2.0 Flash, text-to-speech via edge-tts.

### Integrations & Automation
- **Omnichannel**: Telegram, Discord, Slack, and WhatsApp adapter support.
- **Proactive Heartbeat Schedules**: Background scheduled agent tasks at configurable intervals.
- **Skill Marketplace**: Pre-built skill catalog with one-click install.
- **Agent-Driven Tool/Skill Creation**: Agents can create custom tools and skills during conversations.
- **Docker Sandboxing**: Containerized code execution with network isolation, RAM/CPU caps.

## Tech Stack

- **Backend**: Python 3.12, FastAPI, Uvicorn, SQLAlchemy (Async), SQLite, ChromaDB, Redis
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS v4, Zustand, ReactFlow, Framer Motion
- **AI SDKs**: `openai`, `anthropic`, `google-genai`, `httpx` (Ollama)

## Prerequisites

- [uv](https://github.com/astral-sh/uv) (for Python package management)
- Node.js (for frontend npm management)
- Redis server (for heartbeat and real-time state; optional -- falls back to in-memory if unavailable)
- Optional: Local Ollama instance running if you intend to use local models.
- Optional: Docker for containerized code execution sandboxing.

## How to Run Locally

To run the project, you need to spin up Redis (optional), the backend, and the frontend.

### 0. Redis (Optional)

```bash
# Using Docker
docker run -d -p 6379:6379 redis:alpine

# Or install natively for your platform
```

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

## Architecture Notes

- The project uses `sqlite` at `backend/data/assitance.db`. The DB file, including all schemas and tables, will be auto-generated upon the first startup.
- Redis is used for real-time agent heartbeats, task queue state, and delegation chain tracking. If Redis is unavailable, the system gracefully falls back to in-memory operation.
- The Knowledge Base vector database is stored locally via `ChromaDB` inside the backend directory.
- The Orchestration Engine creates delegation chains with depth limits and circular invocation detection to prevent runaway agent loops.
- The UI features a unified channel chat with @mention-selective routing, replacing the previous dual P2P/LLM system.

## API Endpoints

| Category | Endpoints |
|----------|-----------|
| Health | `GET /api/health` (includes agent statuses, task/chain counts) |
| Chat | `POST /api/chat`, `WS /ws/chat/{id}` |
| Agents | `CRUD /api/agents`, `POST /api/agents/generate-personality` |
| Channels | `CRUD /api/channels`, agent assignment |
| Tasks | `GET /api/tasks/active`, `GET /api/tasks/{id}` |
| Chains | `GET /api/chains/active`, `GET /api/chains/{id}` |
| Knowledge | `GET/POST/DELETE /api/knowledge` |
| Workflows | `CRUD /api/workflows` |
| Tools | `GET /api/tools`, `CRUD /api/custom-tools` |
| Skills | `CRUD /api/skills`, marketplace |
| Integrations | `CRUD /api/integrations` |
| Schedules | `CRUD /api/schedules` |

## License

Private / All Rights Reserved.
