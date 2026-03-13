"""Resource usage monitor for the Master Heartbeat system.

Tracks API rate-limit usage (RPM/TPM/RPD) and applies concurrency
throttling at configurable thresholds to prevent rate-limit violations.
"""

import logging
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class ThrottleLevel(str, Enum):
    NORMAL = "normal"       # < 60% usage
    WARN = "warn"           # 60-80% usage
    THROTTLE = "throttle"   # 80-95% usage — reduce concurrency
    CRITICAL = "critical"   # > 95% usage — queue new requests


# Default model limits (can be overridden per-model)
DEFAULT_LIMITS = {
    "rpm": 60,      # Requests per minute
    "tpm": 250000,  # Tokens per minute
    "rpd": 10000,   # Requests per day
}

# Threshold percentages
WARN_THRESHOLD = 0.60
THROTTLE_THRESHOLD = 0.80
CRITICAL_THRESHOLD = 0.95


class ResourceMonitor:
    """Monitors API resource usage and controls concurrency throttling.
    
    Called by MasterHeartbeat every 30 seconds.
    
    Reads current RPM/TPM from RateLimitManager and applies thresholds:
    - < 60%: Normal operation
    - 60-80%: Warning — log advisory
    - 80-95%: Throttle — reduce max concurrent agent tasks
    - > 95%: Critical — queue new requests
    """

    def __init__(self):
        self._throttle_level = ThrottleLevel.NORMAL
        self._current_metrics: dict = {}
        self._model_limits: dict[str, dict] = {}
        self._last_check = datetime.now(timezone.utc)
        self._max_concurrent_tasks_default = 10
        self._max_concurrent_tasks = self._max_concurrent_tasks_default

    def configure_model_limits(self, model_id: str, rpm: int = 60, tpm: int = 250000, rpd: int = 10000):
        """Set rate limits for a specific model."""
        self._model_limits[model_id] = {"rpm": rpm, "tpm": tpm, "rpd": rpd}

    def get_limits(self, model_id: str) -> dict:
        """Get limits for a model, with fallback to defaults."""
        return self._model_limits.get(model_id, DEFAULT_LIMITS)

    @property
    def throttle_level(self) -> ThrottleLevel:
        return self._throttle_level

    @property
    def max_concurrent_tasks(self) -> int:
        return self._max_concurrent_tasks

    def should_queue_request(self) -> bool:
        """Returns True if requests should be queued (critical throttle)."""
        return self._throttle_level == ThrottleLevel.CRITICAL

    def should_reduce_concurrency(self) -> bool:
        """Returns True if concurrency should be reduced."""
        return self._throttle_level in (ThrottleLevel.THROTTLE, ThrottleLevel.CRITICAL)

    async def check_resources(self, rate_limiter=None) -> dict:
        """Check current resource usage and update throttle level.
        
        Returns metrics dict for broadcasting.
        """
        self._last_check = datetime.now(timezone.utc)

        if rate_limiter is None:
            return self._build_metrics()

        # Get active model IDs
        try:
            model_ids = list(self._model_limits.keys()) if self._model_limits else ["gemini/gemini-2.5-flash"]
            metrics = await rate_limiter.get_current_metrics(model_ids)
            self._current_metrics = metrics
        except Exception as exc:
            logger.debug("Resource monitor metrics fetch failed: %s", exc)
            return self._build_metrics()

        # Calculate worst-case utilization across all models
        max_utilization = 0.0
        utilization_details = {}

        for model_id, usage in metrics.items():
            limits = self.get_limits(model_id)
            rpm_util = usage.get("rpm", 0) / max(limits["rpm"], 1)
            tpm_util = usage.get("tpm", 0) / max(limits["tpm"], 1)
            model_util = max(rpm_util, tpm_util)
            utilization_details[model_id] = {
                "rpm_usage": usage.get("rpm", 0),
                "rpm_limit": limits["rpm"],
                "rpm_util": round(rpm_util * 100, 1),
                "tpm_usage": usage.get("tpm", 0),
                "tpm_limit": limits["tpm"],
                "tpm_util": round(tpm_util * 100, 1),
            }
            max_utilization = max(max_utilization, model_util)

        # Determine throttle level
        old_level = self._throttle_level
        if max_utilization >= CRITICAL_THRESHOLD:
            self._throttle_level = ThrottleLevel.CRITICAL
            self._max_concurrent_tasks = max(1, self._max_concurrent_tasks_default // 4)
        elif max_utilization >= THROTTLE_THRESHOLD:
            self._throttle_level = ThrottleLevel.THROTTLE
            self._max_concurrent_tasks = max(2, self._max_concurrent_tasks_default // 2)
        elif max_utilization >= WARN_THRESHOLD:
            self._throttle_level = ThrottleLevel.WARN
            self._max_concurrent_tasks = self._max_concurrent_tasks_default
        else:
            self._throttle_level = ThrottleLevel.NORMAL
            self._max_concurrent_tasks = self._max_concurrent_tasks_default

        # Log transitions
        if old_level != self._throttle_level:
            logger.info(
                "[ResourceMonitor] Throttle level changed: %s → %s (utilization: %.0f%%, "
                "max_concurrent: %d)",
                old_level.value, self._throttle_level.value,
                max_utilization * 100, self._max_concurrent_tasks
            )

        return self._build_metrics(utilization_details, max_utilization)

    def _build_metrics(self, details: dict | None = None, utilization: float = 0.0) -> dict:
        return {
            "throttle_level": self._throttle_level.value,
            "max_utilization_pct": round(utilization * 100, 1),
            "max_concurrent_tasks": self._max_concurrent_tasks,
            "model_details": details or {},
            "last_check": self._last_check.isoformat(),
        }
