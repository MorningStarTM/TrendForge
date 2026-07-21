# Data Normalizer

## What it is

The Data Normalizer is the pipeline stage that sits between raw ScrapeCreators
API responses and the [Data Pool](../backend/app/services/ingestion/data_pool.py).
Every platform (Instagram, TikTok, YouTube, ...) returns data in its own
inconsistent shape — different field names, different date formats, different
ways of representing engagement. The Normalizer's job is to turn all of that
into one canonical shape (`RawPost`) before anything reaches the Data Pool, so
every downstream consumer (Rule Engine, velocity scoring, dedup) only ever
has to deal with one schema.

Code lives in `backend/app/services/ingestion/normalizer/`.

## What it does

`normalize_and_ingest()` in `pipeline.py` is the single entry point. For each
raw record it runs:

1. **Parse** (`parsers.py`) — a platform-specific function
   (`parse_instagram_post`, `parse_tiktok_post`, `parse_youtube_post`)
   transforms the raw dict into a `RawPost`. If a record is missing a
   required field (e.g. no post ID), the parser raises `MalformedPostError`
   instead of raising an unhandled exception that would abort the whole
   batch.
2. **Route malformed records to the Dead Letter Queue** (`dead_letter.py`) —
   any `MalformedPostError` is caught per-record, logged into an in-memory
   `DeadLetterQueue` with the platform, the reason, and the original raw
   payload, and processing continues with the next record.
3. **Detect language** (`language_detection.py`) — the parsed post's `text`
   is tagged `"ar"`, `"en"`, or `"other"` using a locally-run fastText
   `lid.176` model (no API cost). Mixed-language text is tagged with its
   single most probable language.
4. **Score engagement** (`engagement.py`) — `compute_engagement_rate()`
   computes `(likes + comments + shares) / max(views, follower_count)` and
   the result is stored on the post (not just derivable on demand).
5. **Dedupe + store** — the fully normalized `RawPost`s are handed to
   `DataPool.add_many()`, which rejects anything whose `content_hash`
   (cross-platform reposts) or `(platform, platform_post_id)` pair
   (same-platform re-ingestion) has already been seen. There is no separate
   dedup step in the Normalizer itself — `deduplication.py` is intentionally
   just a pointer to this, so the logic isn't duplicated in two places.

Because `DataPool.add()`/`add_many()` only accept `RawPost` objects, and
`normalize_and_ingest()` is the only intended way to populate the pool, raw
scraper output can never end up in the Data Pool un-normalized.

## What it returns

```python
async def normalize_and_ingest(
    platform: Platform,
    raw_records: Iterable[dict[str, Any]],
    source_query: str,
    pool: DataPool | None = None,
    dead_letters: DeadLetterQueue | None = None,
) -> NormalizationSummary:
```

```python
@dataclass
class NormalizationSummary:
    received: int        # how many raw records came in
    malformed: int        # how many failed parsing and went to the DLQ
    added_to_pool: int    # how many were valid AND new (not duplicates)

    @property
    def duplicates(self) -> int:
        return self.received - self.malformed - self.added_to_pool
```

`pool` and `dead_letters` default to the process-wide singletons
(`get_data_pool()`, `get_dead_letter_queue()`) if not passed explicitly —
tests pass their own instances so they don't share state with each other.

## The `RawPost` schema

Defined in `post_schema.py`. This is the one shape every platform's data is
normalized into, and the Data Pool's unit of storage.

| Field | Type | Notes |
|---|---|---|
| `post_id` | `UUID` | Generated internally, not a platform ID |
| `platform` | `"instagram" \| "facebook" \| "tiktok" \| "youtube" \| "snapchat" \| "x"` | |
| `platform_post_id` | `str` | The native ID from the platform |
| `content_hash` | `str` | Auto-computed: `SHA-256(text + media_url)`. Cross-platform dedup key. |
| `text` | `str` | Caption / title / description |
| `language` | `str \| None` | Set by the Normalizer: `"ar"`, `"en"`, or `"other"` |
| `media_url` | `str \| None` | |
| `media_type` | `"image" \| "video" \| "carousel" \| "text_only" \| "story" \| None` | |
| `engagement` | `EngagementStats` | Raw counts: `likes`, `views`, `shares`, `comments`, `saves` |
| `hashtags` | `list[str]` | Extracted via regex from `text` (YouTube falls back to its `keywords` field if no `#tags` are present) |
| `audio_id` | `str \| None` | Not currently populated by any parser (ScrapeCreators doesn't expose a sound/music ID on these endpoints) |
| `geo` | `"KSA" \| "UAE" \| "BOTH" \| None` | Not currently populated — no geo signal in the wrapped endpoints yet |
| `author_follower_count` | `int \| None` | `None` for YouTube (not exposed on any wrapped endpoint) |
| `engagement_rate` | `float` | Set by the Normalizer: `(likes + comments + shares) / max(views, follower_count)`. Defaults to `0.0` until normalized. |
| `posted_at` | `datetime` | Parsed from the platform's own timestamp field |
| `scraped_at` | `datetime` | Defaults to "now" at construction time |
| `source_query` | `str \| None` | What produced this post, e.g. `"hashtag:pizza"` — a lightweight stand-in for a `scraper_config_id` FK, since there's no `scraper_configs` table yet |

`content_hash` is filled by a `model_validator` on `RawPost` itself (schema
concern), but `engagement_rate` is **not** auto-computed the same way — it's
a plain field the Normalizer sets explicitly. This was a deliberate split:
`engagement.py` needs `EngagementStats` from `post_schema.py`, so having
`post_schema.py` import back from `engagement.py` to auto-compute the rate
would create a circular import. Keeping "engagement normalization" as an
explicit pipeline step (matching how the architecture doc frames it) avoided
that entirely.

## Platform quirks handled

Real inconsistencies found in ScrapeCreators' own API (not assumptions —
verified against its actual OpenAPI spec and example responses):

- **YouTube's own endpoints disagree with each other.** `search` returns
  `publishedTime`; `shorts/trending` and `video` return `publishDate`
  instead. `parse_youtube_post` tries both.
- **TikTok's timestamp field varies by endpoint.** Hashtag search only
  returns `create_time_utc` (ISO string); keyword search and profile videos
  also include `create_time` (Unix epoch int). Both are tried, ISO first.
- **Instagram's post ID field varies.** Some records have `id`, others only
  `shortcode`. Both are tried; if neither is present the record is
  malformed.

## Language detection dependency note

`fasttext-wheel` 0.9.2 (the only actively-available fastText PyPI package)
crashes under numpy ≥ 2.0 — its `predict()` method calls
`np.array(probs, copy=False)`, which numpy 2.x rejects. Fixed by pinning
`numpy<2` in `backend/pyproject.toml`; `uv sync` resolved this cleanly
against the rest of the dependency set (torch, sentence-transformers, etc.).
The model file itself (`lid.176.ftz`, ~1MB) is not committed to the repo —
`language_detection.py` downloads it once from Meta's public hosting and
caches it at `~/.cache/trendforge/lid.176.ftz`.

## What's deliberately not here

- **Facebook, X, and Snapchat parsers don't exist yet.** ScrapeCreators has
  no hashtag/keyword search for these three platforms — only handle/URL
  lookups — so they were deprioritized when the scraper wrappers were built.
- **Media caching to S3** (architecture doc 2.4) isn't implemented — that
  depends on Module 2 infra (S3 buckets, credentials) that isn't wired up.
- **The Dead Letter Queue is in-memory only**, same as the Data Pool —
  consistent with the single-process, no-separate-workers architecture
  decision. It's for inspection/debugging, not a durable audit log.
