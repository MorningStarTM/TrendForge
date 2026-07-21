# Engineering Docs

Technical documentation of how TrendForge is actually built: the components
that exist, what they do, and the reasoning behind non-obvious decisions.

This is separate from `docs/` (the original client-facing planning/architecture
documents, which are gitignored and not meant to be tracked). Everything here
is meant to be committed and kept up to date as the system grows.

## Contents

- [data-normalizer.md](data-normalizer.md) — the pipeline that turns raw
  scraper output into validated, deduplicated `RawPost` records in the Data
  Pool: parsing, language detection, engagement scoring, and the dead-letter
  queue for malformed records.
