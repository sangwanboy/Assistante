# Assitance - AI Assistant Platform

Assitance is a multi-purpose AI assistant platform offering flexible support for multiple LLM providers, including OpenAI, Anthropic Claude, Google Gemini, and local Ollama models. The architecture pairs a Python FastAPI backend with a modern React web interface, featuring a robust agent system, document knowledge base (RAG), and a node-based workflow engine.

## Features

- **Multi-Provider Support**: Seamlessly switch between OpenAI, Anthropic, Google Gemini, and Ollama.
- **Agent System**: Create and manage specialized AI agents with distinct personalities, instructions, and enabled tools.
- **Tool Sandbox**: Agents have access to built-in tools like Web Search, File Management, Python Code Execution, and Date/Time utilities.
- **Knowledge Base (RAG)**: Upload documents (PDF, TXT, MD) which are automatically chunked, embedded, and stored in ChromaDB for AI reference.
- **Workflow Engine**: A node-based visual workflow editor (ReactFlow) supporting triggers (webhooks, etc.) and AI actions (summarize, email draft, notify).
- **Group Chat**: Invite multiple AI AI agents into a single chat session for collaborative broadcast streams.
- **Modern UI**: A responsive, colorful React frontend featuring an active workspace, real-time streaming, and interactive agents dashboard.

## Tech Stack

- **Backend**: Python 3.12, FastAPI, Uvicorn, SQLAlchemy (Async), SQLite, ChromaDB
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS v4, Zustand, ReactFlow
- **AI SDKs**: `openai`, `anthropic`, `google-genai`, `httpx` (Ollama)

## Prerequisites

- [uv](https://github.com/astral-sh/uv) (for Python package management)
- Node.js (for frontend npm management)
- Optional: Local Ollama instance running if you intend to use local models.

## How to Run Locally

To run the project, you need to spin up the backend and the frontend in two separate terminal windows.

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

## Architecture Notes

- The project uses `sqlite` at `backend/data/assitance.db`. The DB file, including all schemas and tables, will be auto-generated upon the first startup.
- The Knowledge Base vector database is stored locally via `ChromaDB` inside the backend directory.
- The UI mimics a desktop application aesthetic and is preparing for a future phase as an encapsulated Electron application.

## License

Private / All Rights Reserved.
