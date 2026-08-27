from __future__ import annotations

import re
from uuid import uuid4

from pydantic import BaseModel, Field

# Architecture doc 12.2: chunk brand documents into ~500-token passages, each
# with chunk_id, source_doc, section_title, content_text.
#
# We chunk structure-aware rather than fixed-size: markdown headings mark
# natural section boundaries in brand docs (voice / colors / dos / don'ts /
# regional tone), so each heading's body becomes one chunk with a real
# section_title. A section longer than the token budget is sub-split on
# paragraph boundaries so no single chunk blows the caption prompt's budget.
#
# "~500 tokens" is approximated as chars/4 (a common rule of thumb) to avoid
# pulling in a tokenizer dependency — chunk sizing doesn't need exactness.
APPROX_CHARS_PER_TOKEN = 4
DEFAULT_MAX_TOKENS = 500

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


class BrandChunk(BaseModel):
    chunk_id: str = Field(default_factory=lambda: str(uuid4()))
    source_doc: str
    section_title: str
    content_text: str


def _approx_tokens(text: str) -> int:
    return len(text) // APPROX_CHARS_PER_TOKEN


def _split_into_sections(text: str) -> list[tuple[str, str]]:
    """Split markdown into (section_title, body) pairs on headings.

    Content before the first heading (or in a doc with no headings) is grouped
    under an empty title.
    """
    sections: list[tuple[str, str]] = []
    current_title = ""
    current_lines: list[str] = []

    def flush() -> None:
        body = "\n".join(current_lines).strip()
        if body:
            sections.append((current_title, body))

    for line in text.splitlines():
        match = HEADING_RE.match(line)
        if match:
            flush()
            current_title = match.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)
    flush()
    return sections


def _split_oversized(body: str, max_tokens: int) -> list[str]:
    """Split a too-long section body on blank-line paragraph boundaries."""
    if _approx_tokens(body) <= max_tokens:
        return [body]

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    pieces: list[str] = []
    buffer: list[str] = []
    for paragraph in paragraphs:
        candidate = "\n\n".join([*buffer, paragraph])
        if buffer and _approx_tokens(candidate) > max_tokens:
            pieces.append("\n\n".join(buffer))
            buffer = [paragraph]
        else:
            buffer.append(paragraph)
    if buffer:
        pieces.append("\n\n".join(buffer))
    return pieces


def chunk_document(
    text: str, source_doc: str, max_tokens: int = DEFAULT_MAX_TOKENS
) -> list[BrandChunk]:
    """Chunk one brand document's extracted text into BrandChunks (doc 12.2)."""
    chunks: list[BrandChunk] = []
    for section_title, body in _split_into_sections(text):
        for piece in _split_oversized(body, max_tokens):
            chunks.append(
                BrandChunk(
                    source_doc=source_doc,
                    section_title=section_title,
                    content_text=piece,
                )
            )
    return chunks
