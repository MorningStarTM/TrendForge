"""Deduplication for normalized posts.

There's no separate dedup engine here — `app.services.ingestion.data_pool.DataPool`
already implements the two-level dedup the architecture doc calls for (2.4):
`DataPool.add()` rejects a post if its `content_hash` (cross-platform reposts)
or `(platform, platform_post_id)` pair (same-platform re-ingestion) has already
been seen. Normalized posts should be handed to `DataPool.add()`/`add_many()`
directly rather than deduplicated a second time here.
"""
