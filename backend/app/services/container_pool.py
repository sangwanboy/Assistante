"""Container Pool Service for Agent Workspaces.

Manages a pool of pre-warmed, long-lived Docker containers (`crossclaw-worker`)
that contain a full environment (Python, Node, Playwright, etc.).
This avoids the overhead of spinning up a fresh container per script execution,
while maintaining isolation between tasks via directory-scoped execution.

The pool mounts `data/workspaces/` to `/workspaces` inside all containers,
and `DockerCodeExecutorTool` will execute code with `cwd=/workspaces/{task_id}`.
"""

import asyncio
import logging
import os
import docker
from typing import Optional

logger = logging.getLogger(__name__)

WORKER_IMAGE_NAME = "crossclaw-worker:latest"
POOL_SIZE = 3

_instance: Optional['ContainerPool'] = None


class ContainerPool:
    """Manages a pool of long-lived Docker containers for code execution."""

    def __init__(self):
        self.pool_size = POOL_SIZE
        self.containers = []  # List of dicts: {'id': str, 'in_use': bool, 'task_id': None}
        self.lock = asyncio.Lock()
        
        # Ensure workspaces dir exists before mounting
        self.workspaces_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "workspaces"))
        os.makedirs(self.workspaces_dir, exist_ok=True)
        
        self.docker_client = None
        self._is_docker_available = False
        
        try:
            import docker
            self.docker_client = docker.from_env()
            self.docker_client.ping()
            self._is_docker_available = True
        except Exception as e:
            logger.warning("Docker unvailable for ContainerPool: %s", e)

    @classmethod
    def get_instance(cls) -> 'ContainerPool':
        global _instance
        if _instance is None:
            _instance = cls()
        return _instance

    async def initialize(self):
        """Build the worker image if missing and spin up the pool."""
        if not self._is_docker_available:
            return

        logger.info("Initializing ContainerPool (size=%d)...", self.pool_size)
        
        # 1. Check if image exists, build if not
        try:
            self.docker_client.images.get(WORKER_IMAGE_NAME)
        except docker.errors.ImageNotFound:  # type: ignore
            logger.info("Building %s image. This may take a few minutes...", WORKER_IMAGE_NAME)
            dockerfile_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
            dockerfile_path = os.path.join(dockerfile_dir, "Dockerfile.worker")
            
            if not os.path.exists(dockerfile_path):
                logger.error("Dockerfile.worker not found at %s. Cannot build worker image.", dockerfile_path)
                return

            def _build():
                self.docker_client.images.build(
                    path=dockerfile_dir,
                    dockerfile="Dockerfile.worker",
                    tag=WORKER_IMAGE_NAME,
                    rm=True,
                )
            
            # Build sync operation in executor (it takes time)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _build)
            logger.info("Successfully built %s", WORKER_IMAGE_NAME)

        # 2. Spin up containers
        def _start_containers():
            # Clean up old containers from previous runs
            old_containers = self.docker_client.containers.list(all=True, filters={"label": "crossclaw.role=worker"})
            for c in old_containers:
                logger.info("Removing old worker container: %s", c.id[:12])
                c.remove(force=True)

            for i in range(self.pool_size):
                container = self.docker_client.containers.run(
                    image=WORKER_IMAGE_NAME,
                    command=["tail", "-f", "/dev/null"], # Keep alive
                    labels={"crossclaw.role": "worker"},
                    volumes={self.workspaces_dir: {"bind": "/workspaces", "mode": "rw"}},
                    network_disabled=False, # We allow network in workers for API/scraping (unlike old strict sandbox)
                    mem_limit="512m",
                    cpu_period=100000,
                    cpu_quota=50000,  # 50% of one CPU
                    cap_drop=["ALL"],
                    stop_signal="SIGKILL",
                    pids_limit=256,
                    detach=True,
                )
                self.containers.append({
                    "id": container.id,
                    "in_use": False,
                    "task_id": None,
                })
                logger.debug("Started worker container %s", container.id[:12])
                
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _start_containers)
        logger.info("ContainerPool initialized %d workers.", len(self.containers))

    async def acquire(self, task_id: str) -> Optional[str]:
        """Acquire a container for a specific task.
        
        If no containers are free, returns None (caller should fallback to subprocess
        or wait).
        """
        if not self._is_docker_available or not self.containers:
            return None
            
        async with self.lock:
            # First, check if task already has a container assigned
            for c in self.containers:
                if c["task_id"] == task_id:
                    c["in_use"] = True
                    return c["id"]
                    
            # Check for a totally free container
            for c in self.containers:
                if not c["in_use"] and c["task_id"] is None:
                    c["in_use"] = True
                    c["task_id"] = task_id
                    return c["id"]
                    
            # Check for a container that is not currently running code,
            # but is assigned to a different task (we can steal it)
            for c in self.containers:
                if not c["in_use"]:
                    old_task = c["task_id"]
                    c["in_use"] = True
                    c["task_id"] = task_id
                    logger.debug("Reclaimed container %s from task %s for task %s", c["id"][:12], old_task, task_id)
                    return c["id"]

        logger.warning("ContainerPool depleted! No free containers available for task %s.", task_id)
        return None

    async def release(self, container_id: str):
        """Mark a container as no longer actively running code.
        
        The container stays assigned to the task_id to optimize subsequent calls
        for the same task, unless stolen by another task in `acquire()`.
        """
        async with self.lock:
            for c in self.containers:
                if c["id"] == container_id:
                    c["in_use"] = False
                    break

    async def shutdown(self):
        """Kill all worker containers."""
        if not self._is_docker_available or not self.containers:
            return
            
        logger.info("Shutting down ContainerPool...")
        def _stop():
            for c_info in self.containers:
                try:
                    c = self.docker_client.containers.get(c_info["id"])
                    c.remove(force=True)
                except Exception as e:
                    logger.error("Failed to remove container %s on shutdown: %s", c_info["id"][:12], e)
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _stop)
        self.containers.clear()
        
    def get_status(self) -> dict:
        """Return the current metrics and status of the container pool."""
        total = self.pool_size
        if not self._is_docker_available:
            return {
                "available": False,
                "total": total,
                "active": 0,
                "idle": 0,
                "error": "Docker is not available"
            }
            
        active = sum(1 for c in self.containers if c["in_use"])
        idle = len(self.containers) - active
        return {
            "available": True,
            "total": total,
            "active": active,
            "idle": idle,
        }
