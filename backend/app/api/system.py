from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone, timedelta
from app.db.engine import get_session
from app.services.container_pool import ContainerPool
from app.services.llm_gateway import get_gateway
from app.models.model_registry import ModelCapability
from app.models.agent import Agent
from app.models.agent_memory import SemanticMemory

router = APIRouter(prefix="/system", tags=["System"])

@router.get("/containers")
async def get_containers_status():
    """Retrieve the current status of the Docker worker container pool."""
    pool = ContainerPool.get_instance()
    # If the pool hasn't been initialized by the lifespan event yet, 
    # it might report 0 containers, but it will have available=True/False depending on docker daemon.
    status = pool.get_status()
    return status
@router.get("/metrics")
async def get_system_metrics(session: AsyncSession = Depends(get_session)):
    """Retrieve global system metrics including LLM rate limiting, memory, and pruning stats."""
    gateway = await get_gateway()

    # Fetch models
    stmt = select(ModelCapability).where(ModelCapability.is_active)
    res = await session.execute(stmt)
    models = res.scalars().all()

    model_ids = [m.id for m in models]
    live_metrics = await gateway.rate_limiter.get_current_metrics(model_ids)

    global_rpm = sum(metrics.get("rpm", 0) for metrics in live_metrics.values())
    global_tpm = sum(metrics.get("tpm", 0) for metrics in live_metrics.values())

    # Sum up the absolute limits
    total_rpm_limit = sum(m.rpm for m in models if m.rpm and m.rpm > 0)
    total_tpm_limit = sum(m.tpm for m in models if m.tpm and m.tpm > 0)

    # Agent counts — differentiate active/idle/paused vs total non-deleted
    total_agents = await session.scalar(
        select(func.count(Agent.id)).where(Agent.status != "deleted")
    ) or 0
    active_agents = await session.scalar(
        select(func.count(Agent.id)).where(Agent.status.in_(["active", "idle"]))
    ) or 0
    agent_capacity_used_pct = round((total_agents / 60) * 100, 1)

    # Token cost aggregation — total_cost from all agents (USD)
    total_cost = await session.scalar(
        select(func.sum(Agent.total_cost)).where(Agent.status != "deleted")
    ) or 0.0
    # Rough token estimate: ~$1 per 1M tokens at budget model rates
    total_tokens_estimated = int(total_cost * 1_000_000)

    # Memory compaction rate — SemanticMemory rows created in last 24h
    day_ago = datetime.now(timezone.utc) - timedelta(hours=24)
    compaction_24h = await session.scalar(
        select(func.count(SemanticMemory.id)).where(SemanticMemory.created_at >= day_ago)
    ) or 0
    compaction_rate_per_hour = round(compaction_24h / 24, 2)

    # Pruning event counters (in-process, resets on restart)
    from app.services.pruning_events import get_counters
    pruning_counters = get_counters()

    rate_limit_blocks = await gateway.rate_limiter.get_block_count()

    return {
        "active_agents": active_agents,
        "total_agents": 60, # Use static capacity limit as the total for UI bars
        "total_agents_actual": total_agents, # For info
        "agent_capacity": {
            "used": active_agents,
            "limit": 60,
            "used_pct": round((active_agents / 60) * 100, 1),
        },
        "global_rpm": global_rpm,
        "total_rpm_limit": total_rpm_limit,
        "global_tpm": global_tpm,
        "total_tpm_limit": total_tpm_limit,
        "rate_limit_blocks": rate_limit_blocks,
        # Token economy
        "token_usage_per_request": global_tpm,  # current sliding window TPM
        "total_tokens_estimated": total_tokens_estimated,
        "total_cost_usd": round(total_cost, 6),
        # Memory architecture metrics
        "memory_compaction": {
            "memories_created_24h": compaction_24h,
            "rate_per_hour": compaction_rate_per_hour,
        },
        # Pruning observability
        "pruning_events": {
            "soft": pruning_counters.get("soft", 0),
            "active": pruning_counters.get("active", 0),
            "emergency": pruning_counters.get("emergency", 0),
            "total": pruning_counters.get("total", 0),
        },
    }


@router.get("/dashboard")
async def get_system_dashboard():
    """Comprehensive system observability dashboard (Section 18)."""
    from app.db.engine import async_session
    from app.models.task import Task
    from app.models.chain import DelegationChain
    from app.models.agent import Agent
    from app.models.workflow import WorkflowRun
    from sqlalchemy import select, func
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(hours=24)

    async with async_session() as session:
        # Agent stats
        agents_total = await session.scalar(select(func.count(Agent.id)).where(Agent.status != "deleted"))
        agents_active = await session.scalar(select(func.count(Agent.id)).where(Agent.status.in_(["active", "idle"])))
        agents_system = await session.scalar(select(func.count(Agent.id)).where(Agent.is_system == True))

        # Task stats
        tasks_pending = await session.scalar(select(func.count(Task.id)).where(Task.status == "pending"))
        tasks_running = await session.scalar(select(func.count(Task.id)).where(Task.status == "running"))
        tasks_completed_24h = await session.scalar(
            select(func.count(Task.id)).where(Task.status == "completed", Task.completed_at >= day_ago)
        )
        tasks_failed_24h = await session.scalar(
            select(func.count(Task.id)).where(Task.status == "failed", Task.updated_at >= day_ago)
        )

        # Workflow stats
        wf_running = await session.scalar(select(func.count(WorkflowRun.id)).where(WorkflowRun.status == "running"))
        wf_completed_24h = await session.scalar(
            select(func.count(WorkflowRun.id)).where(WorkflowRun.status == "completed", WorkflowRun.ended_at >= day_ago)
        )
        wf_failed_24h = await session.scalar(
            select(func.count(WorkflowRun.id)).where(WorkflowRun.status == "failed", WorkflowRun.ended_at >= day_ago)
        )

        # Chain stats
        chains_active = await session.scalar(
            select(func.count(DelegationChain.id)).where(DelegationChain.state == "active")
        )
        avg_depth = await session.scalar(
            select(func.avg(DelegationChain.depth)).where(DelegationChain.state == "active")
        )

        # Token usage (sum from agents)
        total_cost = await session.scalar(select(func.sum(Agent.total_cost))) or 0.0

    # Rate limit info
    rate_limit_info = {"throttle_level": "NORMAL", "rpm_usage": "0%", "tpm_usage": "0%"}
    try:
        from app.services.master_heartbeat import MasterHeartbeat
        master = MasterHeartbeat.get_instance()
        monitor = master.resource_monitor
        if monitor:
            # ResourceMonitor has a build_metrics but let's see if we should just call check_resources or access last metrics
            # MasterHeartbeat already has latest metrics in self._metrics
            hb_metrics = master.get_metrics()
            res_metrics = hb_metrics.get("monitors", {}).get("resource", {})
            rate_limit_info = {
                "throttle_level": res_metrics.get("throttle_level", "NORMAL"),
                "rpm_usage": f"{res_metrics.get('max_utilization_pct', 0)}%",
                "tpm_usage": f"{res_metrics.get('max_utilization_pct', 0)}%", # Simplified for now
            }
    except Exception:
        pass

    # Queue stats
    queue_stats = {"queue_depth": 0, "dead_letter": 0}
    try:
        from app.services.task_worker import TaskWorker
        # TaskWorker may not be initialized as singleton yet
    except Exception:
        pass

    return {
        "agents": {
            "total": agents_total or 0,
            "active": agents_active or 0,
            "system": agents_system or 0,
            "capacity_pct": round(((agents_total or 0) / 60) * 100, 1),
        },
        "tasks": {
            "pending": tasks_pending or 0,
            "running": tasks_running or 0,
            "completed_24h": tasks_completed_24h or 0,
            "failed_24h": tasks_failed_24h or 0,
        },
        "workflows": {
            "running": wf_running or 0,
            "completed_24h": wf_completed_24h or 0,
            "failed_24h": wf_failed_24h or 0,
        },
        "delegation_chains": {
            "active": chains_active or 0,
            "avg_depth": round(avg_depth or 0, 1),
        },
        "tokens": {
            "total_cost": round(total_cost, 4),
        },
        "rate_limits": rate_limit_info,
        "queue": queue_stats,
        "heartbeat": {
            "uptime_seconds": int((now - MasterHeartbeat.get_instance()._start_time).total_seconds()) if MasterHeartbeat.get_instance()._start_time else 0,
            "last_tick": MasterHeartbeat.get_instance().get_metrics().get("timestamp", now.isoformat()),
        }
    }
