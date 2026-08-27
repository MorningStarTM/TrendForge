"""Image generation via Google Gemini (nano banana / gemini-2.5-flash-image).

Turns an image prompt (from Module 14) into a real PNG. Gemini returns the
image inline as bytes on a `generate_content` call; we pull the first
`inline_data` part out and hand back (mime_type, bytes).
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

DEFAULT_IMAGE_MODEL = "gemini-2.5-flash-image"


class ImageGenerationError(RuntimeError):
    """Gemini did not return an image."""


def generate_image(
    prompt: str,
    *,
    api_key: str,
    model: str = DEFAULT_IMAGE_MODEL,
) -> tuple[str, bytes]:
    """Generate one image from a text prompt. Returns (mime_type, raw_bytes)."""
    # Imported lazily so the dependency is only needed when image gen is used.
    from google import genai

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(model=model, contents=prompt)

    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", None) or []:
            inline = getattr(part, "inline_data", None)
            if inline is not None and getattr(inline, "data", None):
                logger.info(
                    "Gemini image: model=%s mime=%s bytes=%s",
                    model,
                    inline.mime_type,
                    len(inline.data),
                )
                return inline.mime_type or "image/png", inline.data

    # No image part — surface any text the model returned instead (e.g. a refusal).
    text = ""
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", None) or []:
            if getattr(part, "text", None):
                text += part.text
    raise ImageGenerationError(
        f"Gemini returned no image. Model said: {text[:300] or '(nothing)'}"
    )
