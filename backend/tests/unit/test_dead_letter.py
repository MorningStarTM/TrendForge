from __future__ import annotations

from app.services.ingestion.normalizer.dead_letter import DeadLetterQueue, get_dead_letter_queue


def test_add_records_platform_reason_and_raw_payload() -> None:
    dlq = DeadLetterQueue()

    dlq.add("instagram", "missing id and shortcode", {"caption": "broken"})

    assert dlq.size == 1
    record = dlq.all()[0]
    assert record.platform == "instagram"
    assert record.reason == "missing id and shortcode"
    assert record.raw == {"caption": "broken"}


def test_clear_empties_the_queue_and_returns_previous_count() -> None:
    dlq = DeadLetterQueue()
    dlq.add("tiktok", "no aweme_id", {})
    dlq.add("youtube", "no id", {})

    cleared = dlq.clear()

    assert cleared == 2
    assert dlq.size == 0


def test_get_dead_letter_queue_returns_the_same_instance() -> None:
    assert get_dead_letter_queue() is get_dead_letter_queue()
