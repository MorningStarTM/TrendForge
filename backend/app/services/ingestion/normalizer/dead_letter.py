from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any


@dataclass
class DeadLetterRecord:
    platform: str
    reason: str
    raw: dict[str, Any]
    failed_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class DeadLetterQueue:
    """In-memory holding pen for raw records that failed normalization.

    Mirrors the Data Pool's single-process, temporary design (architecture
    doc 2.4: "malformed records go to a dead letter table for manual
    inspection") — this isn't a durable audit log, just a place to inspect
    and debug malformed scraper output instead of silently dropping it.
    """

    def __init__(self) -> None:
        self._records: list[DeadLetterRecord] = []

    def add(self, platform: str, reason: str, raw: dict[str, Any]) -> None:
        self._records.append(DeadLetterRecord(platform=platform, reason=reason, raw=raw))

    def all(self) -> list[DeadLetterRecord]:
        return list(self._records)

    def clear(self) -> int:
        count = len(self._records)
        self._records.clear()
        return count

    @property
    def size(self) -> int:
        return len(self._records)


@lru_cache
def get_dead_letter_queue() -> DeadLetterQueue:
    """The single shared DeadLetterQueue instance for this process."""
    return DeadLetterQueue()
