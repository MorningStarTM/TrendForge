"""Recent-posts sync for the Brand KB (architecture doc 12.5).

The doc runs this weekly as a Celery Beat task: pull the last ~100 published
Papa John's posts, chunk/embed them, and upsert into the KB so the RAG layer
reflects recent brand voice. We have no Celery (single-process) and no wired
source of published PJ posts yet, so this is a plain callable to invoke
manually / on a schedule once those exist, rather than a background task.
"""

from __future__ import annotations

import logging

from app.services.generation.brand_kb.chunking import BrandChunk
from app.services.generation.brand_kb.retrieval import BrandKB, get_brand_kb

logger = logging.getLogger(__name__)


def sync_recent_posts(posts_text: list[tuple[str, str]], kb: BrandKB | None = None) -> int:
    """Embed recent published posts into the KB. Returns the number added.

    `posts_text` is a list of (post_id, caption) pairs — a thin stand-in for
    the real "pull last 100 PJ posts" source, which isn't wired yet. Each post
    becomes one chunk under a synthetic source_doc so retrieval can surface
    recent on-brand phrasing alongside the guideline docs.
    """
    kb = kb or get_brand_kb()
    chunks = [
        BrandChunk(
            source_doc=f"recent-posts/{post_id}",
            section_title="recent published post",
            content_text=caption,
        )
        for post_id, caption in posts_text
        if caption.strip()
    ]
    added = kb.add_chunks(chunks)
    logger.info("Synced %s recent posts into the Brand KB", added)
    return added
