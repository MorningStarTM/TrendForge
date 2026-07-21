from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import httpx

if TYPE_CHECKING:
    import fasttext

logger = logging.getLogger(__name__)

MODEL_URL = "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz"
MODEL_PATH = Path.home() / ".cache" / "trendforge" / "lid.176.ftz"

LanguageTag = Literal["ar", "en", "other"]


def _ensure_model_downloaded() -> Path:
    if not MODEL_PATH.exists():
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Downloading fastText language ID model to %s", MODEL_PATH)
        tmp_path = MODEL_PATH.with_suffix(".tmp")
        with httpx.stream("GET", MODEL_URL, timeout=60.0, follow_redirects=True) as response:
            response.raise_for_status()
            with tmp_path.open("wb") as f:
                for chunk in response.iter_bytes():
                    f.write(chunk)
        tmp_path.rename(MODEL_PATH)
    return MODEL_PATH


@lru_cache
def _get_model() -> fasttext.FastText._FastText:
    import fasttext

    path = _ensure_model_downloaded()
    return fasttext.load_model(str(path))


def detect_language(text: str) -> LanguageTag:
    """Tag `text` as ar/en/other using fastText's lid.176 model (runs locally, no API cost).

    Mixed-language text is tagged by its single most probable (dominant) language.
    """
    cleaned = text.replace("\n", " ").strip()
    if not cleaned:
        return "other"

    model = _get_model()
    labels, _ = model.predict(cleaned, k=1)
    code = labels[0].removeprefix("__label__")
    return code if code in ("ar", "en") else "other"
