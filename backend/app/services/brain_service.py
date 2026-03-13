"""
File-based Agent Brain Service.

Each agent gets a dedicated folder under data/agents/<slug>/ containing:
- IDENTITY.md   — who the agent is (name, role, emoji)
- SOUL.md        — personality values, boundaries, communication style
- MEMORY.md      — long-term persistent memory (facts, knowledge)
- memory/        — daily logs (YYYY-MM-DD.md)

These files ARE the agent's brain. The DB stores config; files store identity.
"""
import re
import uuid
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# Base directory for all agent brain files
AGENTS_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "agents"

# Default scaffold templates
DEFAULT_IDENTITY = """# IDENTITY.md - Who Am I?

- **Name:** {name}
- **Role:** {description}
- **Emoji:** 🤖

---
This file defines who you are. Update it as you evolve.
"""

DEFAULT_SOUL = """# SOUL.md - Who You Are

_Your core values and personality._

## Core Truths

**Be genuinely helpful, not performatively helpful.** Skip filler — just help.

**Be resourceful before asking.** Try to figure it out first. Read the context. Then ask if stuck.

**Earn trust through competence.** Be careful with external actions. Be bold with internal ones.

## Boundaries

- Private things stay private.
- When in doubt, ask before acting externally.
- Never send half-baked replies.

## Vibe

Be concise when needed, thorough when it matters.

---
_This file is yours to evolve. As you learn who you are, update it._
"""

DEFAULT_MEMORY = """# MEMORY.md

_Long-term persistent memory. Facts, knowledge, and context that persist across sessions._

---
"""


def _slugify(name: str) -> str:
    """Convert agent name to a filesystem-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9]+', '_', slug)
    slug = slug.strip('_')
    return slug or "unnamed_agent"


class AgentBrainService:
    """Manages file-based brain directories for agents."""

    @staticmethod
    def get_brain_dir(agent_name: str) -> Path:
        """Get the brain directory path for an agent."""
        return AGENTS_DATA_DIR / _slugify(agent_name)

    @staticmethod
    def ensure_brain_dir(agent_name: str, description: str = "a capable AI assistant") -> Path:
        """Create the brain directory and scaffold default files if they don't exist."""
        brain_dir = AgentBrainService.get_brain_dir(agent_name)
        memory_dir = brain_dir / "memory"

        # Create directories
        brain_dir.mkdir(parents=True, exist_ok=True)
        memory_dir.mkdir(exist_ok=True)

        # Scaffold default files (only if they don't exist)
        identity_path = brain_dir / "IDENTITY.md"
        if not identity_path.exists():
            identity_path.write_text(
                DEFAULT_IDENTITY.format(name=agent_name, description=description),
                encoding="utf-8"
            )

        soul_path = brain_dir / "SOUL.md"
        if not soul_path.exists():
            soul_path.write_text(DEFAULT_SOUL, encoding="utf-8")

        memory_path = brain_dir / "MEMORY.md"
        if not memory_path.exists():
            memory_path.write_text(DEFAULT_MEMORY, encoding="utf-8")

        logger.info(f"Brain directory ensured for '{agent_name}' at {brain_dir}")
        return brain_dir

    # ── READ operations ──

    @staticmethod
    def _safe_read(path: Path) -> str:
        """Safely read a file trying multiple encodings."""
        if not path.exists():
            return ""
        for enc in ["utf-8", "utf-16", "cp1252"]:
            try:
                return path.read_text(encoding=enc)
            except UnicodeError:
                continue
        # Fallback with replacement
        return path.read_text(encoding="utf-8", errors="replace")

    @staticmethod
    def read_identity(agent_name: str) -> str:
        """Read the agent's IDENTITY.md file."""
        return AgentBrainService._safe_read(AgentBrainService.get_brain_dir(agent_name) / "IDENTITY.md")

    @staticmethod
    def read_soul(agent_name: str) -> str:
        """Read the agent's SOUL.md file."""
        return AgentBrainService._safe_read(AgentBrainService.get_brain_dir(agent_name) / "SOUL.md")

    @staticmethod
    def read_memory(agent_name: str) -> str:
        """Read the agent's MEMORY.md file."""
        return AgentBrainService._safe_read(AgentBrainService.get_brain_dir(agent_name) / "MEMORY.md")

    @staticmethod
    def read_today_log(agent_name: str) -> str:
        """Read today's daily log file."""
        today = datetime.now().strftime("%Y-%m-%d")
        return AgentBrainService._safe_read(AgentBrainService.get_brain_dir(agent_name) / "memory" / f"{today}.md")

    @staticmethod
    def read_recent_logs(agent_name: str, days: int = 3) -> str:
        """Read the most recent N daily log files, concatenated."""
        memory_dir = AgentBrainService.get_brain_dir(agent_name) / "memory"
        if not memory_dir.exists():
            return ""

        # Collect all date-based log files
        log_files = sorted(
            list(f for f in memory_dir.glob("*.md") if re.match(r"\d{4}-\d{2}-\d{2}\.md", f.name)),
            key=lambda f: f.name,
            reverse=True
        )

        parts = []
        for log_file in log_files[:days]:
            content = AgentBrainService._safe_read(log_file).strip()
            if content:
                parts.append(f"### {log_file.stem}\n{content}")

        return "\n\n".join(parts)

    # ── WRITE operations ──

    @staticmethod
    def write_identity(agent_name: str, content: str) -> None:
        """Overwrite the agent's IDENTITY.md file."""
        brain_dir = AgentBrainService.ensure_brain_dir(agent_name)
        (brain_dir / "IDENTITY.md").write_text(content, encoding="utf-8")

    @staticmethod
    def write_soul(agent_name: str, content: str) -> None:
        """Overwrite the agent's SOUL.md file."""
        brain_dir = AgentBrainService.ensure_brain_dir(agent_name)
        (brain_dir / "SOUL.md").write_text(content, encoding="utf-8")

    @staticmethod
    def write_memory(agent_name: str, content: str) -> None:
        """Overwrite the agent's MEMORY.md file."""
        brain_dir = AgentBrainService.ensure_brain_dir(agent_name)
        (brain_dir / "MEMORY.md").write_text(content, encoding="utf-8")

    @staticmethod
    def append_memory(agent_name: str, fact: str) -> int:
        """Append a fact to the agent's MEMORY.md. Returns total line count."""
        brain_dir = AgentBrainService.ensure_brain_dir(agent_name)
        memory_path = brain_dir / "MEMORY.md"

        current = ""
        if memory_path.exists():
            current = AgentBrainService._safe_read(memory_path)

        if current and not current.endswith("\n"):
            current += "\n"
        current += f"- {fact}\n"

        memory_path.write_text(current, encoding="utf-8")
        return len(current.splitlines())

    @staticmethod
    def write_daily_log(agent_name: str, content: str) -> str:
        """Write/overwrite today's daily log. Returns the file path."""
        brain_dir = AgentBrainService.ensure_brain_dir(agent_name)
        today = datetime.now().strftime("%Y-%m-%d")
        log_path = brain_dir / "memory" / f"{today}.md"
        log_path.write_text(content, encoding="utf-8")
        return str(log_path)

    @staticmethod
    def append_daily_log(agent_name: str, entry: str) -> str:
        """Append an entry to today's daily log. Returns the file path."""
        brain_dir = AgentBrainService.ensure_brain_dir(agent_name)
        today = datetime.now().strftime("%Y-%m-%d")
        log_path = brain_dir / "memory" / f"{today}.md"

        current = ""
        if log_path.exists():
            current = AgentBrainService._safe_read(log_path)
        else:
            # Create header for new daily log
            current = f"# {agent_name} - Daily Log {today}\n\n"

        timestamp = datetime.now().strftime("%H:%M:%S")
        if current and not current.endswith("\n"):
            current += "\n"
        current += f"**[{timestamp}]** {entry}\n"

        log_path.write_text(current, encoding="utf-8")
        return str(log_path)

    # ── BULK operations ──

    @staticmethod
    def scaffold_all_agents(agents: list) -> None:
        """Scaffold brain directories for a list of agents.
        
        Args:
            agents: list of dicts or Agent models with 'name' and optionally 'description'
        """
        for agent in agents:
            if isinstance(agent, dict):
                name = str(agent.get("name") or "unnamed_agent")
                desc = str(agent.get("description", "a capable AI assistant"))
            else:
                name = str(getattr(agent, "name", "unnamed_agent") or "unnamed_agent")
                desc = str(getattr(agent, "description", "a capable AI assistant") or "a capable AI assistant")
            
            AgentBrainService.ensure_brain_dir(name, desc)

    @staticmethod
    def get_full_brain(agent_name: str) -> dict:
        """Read all brain files for an agent. Returns a dict with all content."""
        return {
            "identity": AgentBrainService.read_identity(agent_name),
            "soul": AgentBrainService.read_soul(agent_name),
            "memory": AgentBrainService.read_memory(agent_name),
            "today_log": AgentBrainService.read_today_log(agent_name),
            "recent_logs": AgentBrainService.read_recent_logs(agent_name, days=3),
        }

    # ── Three-Layer Memory (DB + Vector) ──

    CHROMA_PATH = Path(__file__).parent.parent.parent / "data" / "chroma"

    @staticmethod
    async def store_working_memory(agent_id: str, content: str):
        """Layer 1: Store ephemeral working memory (expires in 1 hour)."""
        from app.db.engine import async_session
        from app.models.agent_memory import WorkingMemory
        async with async_session() as session:
            entry = WorkingMemory(
                id=str(uuid.uuid4()),
                agent_id=agent_id,
                content=content,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
            session.add(entry)
            await session.commit()

    @staticmethod
    async def store_episodic_memory(
        agent_id: str, task_summary: str, outcome: str, task_id: str | None = None
    ):
        """Layer 2: Store a completed task summary as episodic memory."""
        from app.db.engine import async_session
        from app.models.agent_memory import EpisodicMemory
        async with async_session() as session:
            entry = EpisodicMemory(
                id=str(uuid.uuid4()),
                agent_id=agent_id,
                task_id=task_id,
                summary=task_summary,
                outcome=outcome,
            )
            session.add(entry)
            await session.commit()
        logger.info("Stored episodic memory for agent %s (outcome=%s)", agent_id, outcome)

    @staticmethod
    async def store_long_term_memory(agent_id: str, content: str):
        """Layer 3: Store content in ChromaDB with embeddings for semantic search."""
        try:
            import chromadb
            client = chromadb.PersistentClient(
                path=str(AgentBrainService.CHROMA_PATH)
            )
            collection = client.get_or_create_collection(
                name=f"agent_{agent_id}_memory",
                metadata={"hnsw:space": "cosine"},
            )
            doc_id = str(uuid.uuid4())
            collection.add(
                documents=[content],
                ids=[doc_id],
                metadatas=[{
                    "agent_id": agent_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }],
            )
            logger.info("Stored long-term memory for agent %s (doc=%s)", agent_id, doc_id)
        except Exception as exc:
            logger.warning("Failed to store long-term memory: %s", exc)

    @staticmethod
    async def retrieve_relevant_memories(
        agent_id: str, query: str, limit: int = 5
    ) -> list[str]:
        """Layer 3: Retrieve relevant long-term memories via semantic search."""
        try:
            import chromadb
            client = chromadb.PersistentClient(
                path=str(AgentBrainService.CHROMA_PATH)
            )
            try:
                collection = client.get_collection(name=f"agent_{agent_id}_memory")
            except Exception:
                return []

            results = collection.query(
                query_texts=[query],
                n_results=limit,
            )
            documents = results.get("documents", [[]])[0]
            return documents
        except Exception as exc:
            logger.warning("Failed to retrieve long-term memories: %s", exc)
            return []

    @staticmethod
    async def get_recent_episodic_memories(
        agent_id: str, limit: int = 5
    ) -> list[dict]:
        """Layer 2: Retrieve recent episodic memories for context."""
        from app.db.engine import async_session
        from app.models.agent_memory import EpisodicMemory
        from sqlalchemy import select

        async with async_session() as session:
            stmt = (
                select(EpisodicMemory)
                .where(EpisodicMemory.agent_id == agent_id)
                .order_by(EpisodicMemory.created_at.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            memories = result.scalars().all()
            return [
                {
                    "summary": m.summary,
                    "outcome": m.outcome,
                    "task_id": m.task_id,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in memories
            ]

    @staticmethod
    async def cleanup_expired_working_memory():
        """Remove expired working memory entries."""
        from app.db.engine import async_session
        from app.models.agent_memory import WorkingMemory
        from sqlalchemy import delete

        async with async_session() as session:
            stmt = delete(WorkingMemory).where(
                WorkingMemory.expires_at < datetime.now(timezone.utc)
            )
            result = await session.execute(stmt)
            await session.commit()
            if result.rowcount > 0:
                logger.info("Cleaned up %d expired working memory entries", result.rowcount)

    @staticmethod
    async def summarize_and_archive(agent_id: str):
        """Move expired working memory to episodic memory after summarization."""
        from app.db.engine import async_session
        from app.models.agent_memory import WorkingMemory
        from sqlalchemy import select

        async with async_session() as session:
            stmt = (
                select(WorkingMemory)
                .where(
                    WorkingMemory.agent_id == agent_id,
                    WorkingMemory.expires_at < datetime.now(timezone.utc),
                )
            )
            result = await session.execute(stmt)
            expired = result.scalars().all()

            if not expired:
                return

            # Concatenate expired working memories
            combined = "\n".join(e.content for e in expired)
            summary = f"Archived {len(expired)} working memory entries: {combined[:500]}"

            # Store as episodic
            await AgentBrainService.store_episodic_memory(
                agent_id, summary, "archived"
            )

            # Delete the expired entries
            from sqlalchemy import delete
            ids = [e.id for e in expired]
            del_stmt = delete(WorkingMemory).where(WorkingMemory.id.in_(ids))
            await session.execute(del_stmt)
            await session.commit()
            logger.info("Archived %d working memories for agent %s", len(expired), agent_id)
