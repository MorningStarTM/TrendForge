from __future__ import annotations

import pytest
from app.services.generation.brand_kb.chunking import BrandChunk, chunk_document
from app.services.generation.brand_kb.extractors import (
    UnsupportedFormatError,
    extract_text,
    is_supported,
)
from app.services.generation.brand_kb.loader import load_brand_kb, load_chunks_from_s3
from app.services.generation.brand_kb.retrieval import BrandKB
from app.services.generation.brand_kb.sync import sync_recent_posts

# ---- extractors ----


def test_extract_text_decodes_markdown_and_txt() -> None:
    assert extract_text("guidelines/voice.md", b"# Voice\nBe bold") == "# Voice\nBe bold"
    assert extract_text("notes.txt", b"plain text") == "plain text"


def test_extract_text_raises_on_unknown_extension() -> None:
    with pytest.raises(UnsupportedFormatError):
        extract_text("brand.pptx", b"data")


def test_pdf_and_docx_are_registered_but_not_yet_implemented() -> None:
    assert is_supported("book.pdf") is True
    assert is_supported("book.docx") is True
    with pytest.raises(UnsupportedFormatError):
        extract_text("book.pdf", b"%PDF-1.4")


# ---- chunking ----


def test_chunk_document_splits_on_markdown_headings() -> None:
    text = (
        "# Voice\nBe playful and bold.\n\n"
        "## Dos\nUse local references.\n\n"
        "## Donts\nAvoid politics."
    )

    chunks = chunk_document(text, source_doc="guidelines/brand.md")

    titles = [c.section_title for c in chunks]
    assert titles == ["Voice", "Dos", "Donts"]
    assert all(c.source_doc == "guidelines/brand.md" for c in chunks)
    assert "playful" in chunks[0].content_text


def test_chunk_document_groups_pre_heading_content_under_empty_title() -> None:
    chunks = chunk_document("Intro line with no heading.", source_doc="d.md")

    assert len(chunks) == 1
    assert chunks[0].section_title == ""


def test_oversized_section_is_split_on_paragraphs() -> None:
    big_paragraph = "word " * 300  # ~1500 chars -> ~375 tokens each
    text = f"# Big\n{big_paragraph}\n\n{big_paragraph}\n\n{big_paragraph}"

    chunks = chunk_document(text, source_doc="d.md", max_tokens=400)

    # 3 paragraphs of ~375 tokens each can't all fit in one 400-token chunk
    assert len(chunks) > 1
    assert all(c.section_title == "Big" for c in chunks)


# ---- retrieval ----


def _fake_embedder_factory() -> object:
    table = {
        "voice bold playful": [1.0, 0.0, 0.0],
        "halal imagery": [0.0, 1.0, 0.0],
        "avoid competitors": [0.0, 0.0, 1.0],
        "bold playful trend": [0.95, 0.05, 0.0],  # closest to voice
    }

    def embed(text: str) -> list[float]:
        return table[text]

    return embed


def test_retrieve_returns_top_k_by_cosine() -> None:
    embed = _fake_embedder_factory()
    kb = BrandKB(embedder=embed)  # type: ignore[arg-type]
    kb.add_chunks(
        [
            BrandChunk(source_doc="g.md", section_title="Voice", content_text="voice bold playful"),
            BrandChunk(source_doc="g.md", section_title="Halal", content_text="halal imagery"),
            BrandChunk(source_doc="g.md", section_title="Comp", content_text="avoid competitors"),
        ]
    )

    results = kb.retrieve("bold playful trend", k=2)

    assert len(results) == 2
    assert results[0].chunk.section_title == "Voice"
    assert results[0].score > results[1].score


def test_retrieve_k_caps_results() -> None:
    embed = _fake_embedder_factory()
    kb = BrandKB(embedder=embed)  # type: ignore[arg-type]
    kb.add_chunks(
        [BrandChunk(source_doc="g.md", section_title="Voice", content_text="voice bold playful")]
    )

    assert len(kb.retrieve("bold playful trend", k=5)) == 1


# ---- loader (mocked S3) ----


class _FakeBody:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def read(self) -> bytes:
        return self._data


class _FakeS3Client:
    def __init__(self, objects: dict[str, bytes]) -> None:
        self._objects = objects

    def list_objects_v2(self, Bucket: str, Prefix: str, **kwargs: object) -> dict[str, object]:
        contents = [{"Key": key} for key in self._objects if key.startswith(Prefix)]
        return {"Contents": contents, "IsTruncated": False}

    def get_object(self, Bucket: str, Key: str) -> dict[str, object]:
        return {"Body": _FakeBody(self._objects[Key])}


def test_load_chunks_from_s3_extracts_and_chunks_supported_files() -> None:
    s3 = _FakeS3Client(
        {
            "guidelines/voice.md": b"# Voice\nBe bold.",
            "dos-and-donts/rules.txt": b"Do use local references.",
            "guidelines/brandbook.pdf": b"%PDF-1.4 binary",  # supported ext but not implemented
            "guidelines/logo.png": b"\x89PNG",  # unsupported ext
        }
    )

    chunks = load_chunks_from_s3(s3, bucket="brand-kb", prefixes=("guidelines/", "dos-and-donts/"))

    sources = {c.source_doc for c in chunks}
    # md + txt chunked; pdf skipped (not implemented); png skipped (unsupported)
    assert sources == {"guidelines/voice.md", "dos-and-donts/rules.txt"}


def test_load_brand_kb_populates_the_store() -> None:
    s3 = _FakeS3Client({"guidelines/voice.md": b"# Voice\nBe bold and playful."})
    kb = BrandKB(embedder=lambda text: [float(len(text))])  # trivial embedder

    class _Settings:
        s3_bucket_brand_kb = "brand-kb"

    added = load_brand_kb(settings=_Settings(), kb=kb, s3_client=s3)  # type: ignore[arg-type]

    assert added == 1
    assert kb.size == 1


# ---- sync ----


def test_sync_recent_posts_adds_non_empty_captions() -> None:
    kb = BrandKB(embedder=lambda text: [float(len(text))])
    posts = [("p1", "Fresh dough daily"), ("p2", "   "), ("p3", "Order now")]
    added = sync_recent_posts(posts, kb=kb)

    assert added == 2
    assert kb.size == 2
