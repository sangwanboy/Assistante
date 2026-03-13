import time
import logging
import uuid
import asyncio
from collections import defaultdict, deque

from app.services.redis_client import RedisClient

logger = logging.getLogger(__name__)


class RateLimitManager:
    """Manages LLM API Rate Limits using Redis sliding windows."""

    def __init__(self, redis_client: RedisClient):
        self._rc = redis_client
        # Local fallback when Redis is unavailable.
        self._local_buckets: dict[str, deque[tuple[float, int]]] = defaultdict(deque)
        self._local_lock = asyncio.Lock()
        self._block_count = 0

    async def _check_bucket_local(self, key: str, limit: int, window: int, amount: int = 1) -> bool:
        if limit <= 0:
            return True

        now = time.time()
        window_start = now - window

        async with self._local_lock:
            bucket = self._local_buckets[key]

            while bucket and bucket[0][0] < window_start:
                bucket.popleft()

            current_amount = sum(entry_amount for _, entry_amount in bucket)
            if current_amount + amount > limit:
                return False

            bucket.append((now, amount))
            logger.debug(f"RateLimitManager [LOCAL]: Added {amount} to {key}. Current bucket size: {len(bucket)}")
            return True

    async def _check_bucket(self, key: str, limit: int, window: int, amount: int = 1) -> bool:
        """Check if adding `amount` to `key` within `window` exceeds `limit`."""
        if limit <= 0:
            return True

        if not self._rc.available:
            return await self._check_bucket_local(key, limit, window, amount)

        redis = self._rc.redis
        now = time.time()
        window_start = now - window
        
        # Cleanup old entries and get current members, atomic pipeline
        async with redis.pipeline(transaction=True) as pipe:
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zrange(key, 0, -1)
            result = await pipe.execute()
            
            members = result[1]
            current_amount = 0
            for m in members:
                try:
                    current_amount += int(m.decode().split(':')[1])
                except (IndexError, ValueError, AttributeError):
                    pass
                    
            if current_amount + amount > limit:
                return False
            
            # Add new request with UUID to ensure uniqueness
            req_id = str(uuid.uuid4())
            mapping = {f"{req_id}:{amount}": now}
            
            pipe.zadd(key, mapping)
            pipe.expire(key, window)
            await pipe.execute()

        return True

    async def check_limits(self, model_id: str, rpm: int, tpm: int, rpd: int, estimated_tokens: int) -> str:
        """
        Check constraints. Returns "allow", "delay", or "block".
        """
        rpd_key = f"rate_limit:rpd:{model_id}"
        rpm_key = f"rate_limit:rpm:{model_id}"
        tpm_key = f"rate_limit:tpm:{model_id}"
        
        # 1. Check RPD (Requests Per Day - 86400s)
        if rpd > 0:
            allowed = await self._check_bucket(rpd_key, rpd, 86400, 1)
            if not allowed:
                logger.warning(f"Rate Limit EXCEEDED (Block): {model_id} hit RPD limit {rpd}.")
                self._block_count += 1
                if self._rc.available:
                    try:
                        await self._rc.redis.incr("rate_limit:global_blocks")
                    except Exception: pass
                return "block"
                
        # 2. Check TPM (Tokens Per Minute - 60s)
        if tpm > 0:
            allowed = await self._check_bucket(tpm_key, tpm, 60, estimated_tokens)
            if not allowed:
                logger.warning(f"Rate Limit HIT (Delay): {model_id} hit TPM limit {tpm}.")
                return "delay"
                
        # 3. Check RPM (Requests Per Minute - 60s)
        if rpm > 0:
            allowed = await self._check_bucket(rpm_key, rpm, 60, 1)
            if not allowed:
                logger.warning(f"Rate Limit HIT (Delay): {model_id} hit RPM limit {rpm}.")
                return "delay"
                
        return "allow"

    async def get_block_count(self) -> int:
        if self._rc.available:
            try:
                val = await self._rc.redis.get("rate_limit:global_blocks")
                return int(val) if val else self._block_count
            except Exception:
                return self._block_count
        return self._block_count

    async def check_limits_adaptive(self, model_id: str, rpm: int, tpm: int, rpd: int, estimated_tokens: int) -> tuple[str, str]:
        """
        Check constraints with adaptive thresholds.
        Returns (action, throttle_level) where:
        - action: "allow", "delay", or "block"
        - throttle_level: "normal", "warn", "throttle", or "critical"
        """
        if not self._rc.available:
            action = await self.check_limits(model_id, rpm, tpm, rpd, estimated_tokens)
            return action, "normal"

        # Get current usage metrics
        try:
            metrics = await self.get_current_metrics([model_id])
            model_metrics = metrics.get(model_id, {})
        except Exception:
            return "allow", "normal"

        # Calculate utilization percentages
        rpm_util = model_metrics.get("rpm", 0) / max(rpm, 1) if rpm > 0 else 0
        tpm_util = model_metrics.get("tpm", 0) / max(tpm, 1) if tpm > 0 else 0
        max_util = max(rpm_util, tpm_util)

        # Determine throttle level
        if max_util >= 0.95:
            throttle_level = "critical"
        elif max_util >= 0.90:
            throttle_level = "throttle"
        elif max_util >= 0.80:
            throttle_level = "warn"
        else:
            throttle_level = "normal"

        # Run standard check
        action = await self.check_limits(model_id, rpm, tpm, rpd, estimated_tokens)

        # Override action based on adaptive thresholds
        if throttle_level == "critical" and action == "allow":
            action = "delay"  # Force delay at critical levels

        return action, throttle_level

    async def get_current_metrics(self, model_ids: list[str]) -> dict:
        """Returns the aggregate metric counts for RPM and TPM across provided models."""
        if not model_ids:
            return {}
            
        if not self._rc.available:
            # Local fallback metrics
            now = time.time()
            window_start = now - 60
            metrics = {}
            async with self._local_lock:
                for model_id in model_ids:
                    rpm_key = f"rate_limit:rpm:{model_id}"
                    tpm_key = f"rate_limit:tpm:{model_id}"
                    
                    # RPM count
                    rpm_bucket = self._local_buckets[rpm_key]
                    while rpm_bucket and rpm_bucket[0][0] < window_start:
                        rpm_bucket.popleft()
                    rpm_count = sum(amount for _, amount in rpm_bucket)
                    
                    # TPM count
                    tpm_bucket = self._local_buckets[tpm_key]
                    while tpm_bucket and tpm_bucket[0][0] < window_start:
                        tpm_bucket.popleft()
                    tpm_count = sum(amount for _, amount in tpm_bucket)
                    
                    metrics[model_id] = {"rpm": rpm_count, "tpm": tpm_count}
            return metrics
            
        redis = self._rc.redis
        now = time.time()
        window_start = now - 60
        
        metrics = {}
        async with redis.pipeline(transaction=True) as pipe:
            for model_id in model_ids:
                rpm_key = f"rate_limit:rpm:{model_id}"
                tpm_key = f"rate_limit:tpm:{model_id}"
                
                # Cleanup and fetch
                pipe.zremrangebyscore(rpm_key, 0, window_start)
                pipe.zrange(rpm_key, 0, -1)
                
                pipe.zremrangebyscore(tpm_key, 0, window_start)
                pipe.zrange(tpm_key, 0, -1)
                
            results = await pipe.execute()
            
            for i, model_id in enumerate(model_ids):
                rpm_members = results[i * 4 + 1]
                tpm_members = results[i * 4 + 3]
                
                rpm_count = 0
                for m in rpm_members:
                    try:
                        rpm_count += int(m.decode().split(':')[1])
                    except (AttributeError, ValueError, IndexError):
                        pass
                        
                tpm_count = 0
                for m in tpm_members:
                    try:
                        tpm_count += int(m.decode().split(':')[1])
                    except (AttributeError, ValueError, IndexError):
                        pass
                        
                metrics[model_id] = {
                    "rpm": rpm_count,
                    "tpm": tpm_count
                }
                
        return metrics
