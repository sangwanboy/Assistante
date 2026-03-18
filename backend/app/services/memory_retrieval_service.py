"""In-process metrics for semantic memory retrieval observability."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _RetrievalMetrics:
    queries: int = 0
    hits: int = 0
    misses: int = 0
    failures: int = 0


class MemoryRetrievalService:
    _metrics = _RetrievalMetrics()

    @classmethod
    def record_hit(cls) -> None:
        cls._metrics.queries += 1
        cls._metrics.hits += 1

    @classmethod
    def record_miss(cls) -> None:
        cls._metrics.queries += 1
        cls._metrics.misses += 1

    @classmethod
    def record_failure(cls) -> None:
        cls._metrics.queries += 1
        cls._metrics.failures += 1

    @classmethod
    def metrics(cls) -> dict:
        q = cls._metrics.queries
        hit_rate = (cls._metrics.hits / q) if q else 0.0
        return {
            "queries": q,
            "hits": cls._metrics.hits,
            "misses": cls._metrics.misses,
            "failures": cls._metrics.failures,
            "hit_rate": round(hit_rate, 4),
        }
