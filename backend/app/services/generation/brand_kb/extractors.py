from __future__ import annotations

from collections.abc import Callable
from pathlib import PurePosixPath

# Pluggable text extraction: brand KB docs may arrive in mixed formats
# (architecture doc 12.1). Each extractor turns raw file bytes into plain
# text that the chunker can then split. Markdown/plaintext are supported now;
# PDF and DOCX are registered but not yet implemented — add a handler and the
# loader picks it up automatically.


class UnsupportedFormatError(Exception):
    """No extractor is registered for a file's extension."""


Extractor = Callable[[bytes], str]


def _extract_text(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")


def _extract_pdf(data: bytes) -> str:
    raise UnsupportedFormatError(
        "PDF extraction not implemented yet — add a pypdf-based handler to "
        "EXTRACTORS['.pdf'] in extractors.py"
    )


def _extract_docx(data: bytes) -> str:
    raise UnsupportedFormatError(
        "DOCX extraction not implemented yet — add a python-docx-based handler "
        "to EXTRACTORS['.docx'] in extractors.py"
    )


EXTRACTORS: dict[str, Extractor] = {
    ".md": _extract_text,
    ".markdown": _extract_text,
    ".txt": _extract_text,
    ".pdf": _extract_pdf,
    ".docx": _extract_docx,
}


def extract_text(filename: str, data: bytes) -> str:
    """Extract plain text from a brand KB file, dispatching on its extension."""
    suffix = PurePosixPath(filename).suffix.lower()
    extractor = EXTRACTORS.get(suffix)
    if extractor is None:
        raise UnsupportedFormatError(
            f"No extractor registered for '{suffix}' (file: {filename}). "
            f"Supported: {sorted(EXTRACTORS)}"
        )
    return extractor(data)


def is_supported(filename: str) -> bool:
    return PurePosixPath(filename).suffix.lower() in EXTRACTORS
