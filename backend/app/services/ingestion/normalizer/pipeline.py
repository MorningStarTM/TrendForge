from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from app.services.ingestion.data_pool import DataPool, get_data_pool
from app.services.ingestion.normalizer.dead_letter import DeadLetterQueue, get_dead_letter_queue
from app.services.ingestion.normalizer.engagement import compute_engagement_rate
from app.services.ingestion.normalizer.language_detection import detect_language
from app.services.ingestion.normalizer.parsers import PLATFORM_PARSERS, MalformedPostError
from app.services.ingestion.normalizer.post_schema import Platform, RawPost


@dataclass
class NormalizationSummary:
    received: int
    malformed: int
    added_to_pool: int

    @property
    def duplicates(self) -> int:
        return self.received - self.malformed - self.added_to_pool


async def normalize_and_ingest(
    platform: Platform,
    raw_records: Iterable[dict[str, Any]],
    source_query: str,
    pool: DataPool | None = None,
    dead_letters: DeadLetterQueue | None = None,
) -> NormalizationSummary:
    """The Data Normalizer pipeline: parse -> detect language -> score engagement
    -> dedupe into the Data Pool (architecture doc 2.4).

    Malformed records are routed to the Dead Letter Queue instead of aborting
    the whole batch. The Data Pool itself only ever sees valid, fully
    normalized `RawPost`s.
    """
    pool = pool or get_data_pool()
    dead_letters = dead_letters or get_dead_letter_queue()
    parser = PLATFORM_PARSERS[platform]

    raw_list = list(raw_records)
    parsed: list[RawPost] = []
    malformed_count = 0

    for raw in raw_list:
        try:
            post = parser(raw, source_query)
        except MalformedPostError as exc:
            dead_letters.add(exc.platform, exc.reason, exc.raw)
            malformed_count += 1
            continue

        post.language = detect_language(post.text)
        post.engagement_rate = compute_engagement_rate(post.engagement, post.author_follower_count)
        parsed.append(post)

    added = await pool.add_many(parsed)

    return NormalizationSummary(
        received=len(raw_list), malformed=malformed_count, added_to_pool=added
    )
