from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services import content_generation, trend_detection

router = APIRouter()


class IngestionRequest(BaseModel):
    platforms: list[str] = []
    query: str = "pizza"
    static_only: bool = False
    target_posts: int = trend_detection.DEFAULT_TARGET_POSTS
    window_hours: int = 24


@router.post("/ingestion/start")
async def start_ingestion(req: IngestionRequest) -> dict:
    """Real pull → normalize → detect. Spends ScrapeCreators credits."""
    return await trend_detection.run_pull_and_detect(
        req.platforms, req.query, req.static_only, req.target_posts, req.window_hours
    )


@router.get("/ingestion")
def last_ingestion() -> dict | None:
    return trend_detection.get_last_run()


@router.get("/credits")
def credits() -> dict:
    """Live ScrapeCreators credit balance."""
    return {"credits": trend_detection.get_credit_balance()}


@router.get("/trends")
def list_trends() -> list[dict]:
    return trend_detection.get_trends()


@router.get("/trends/{trend_id}")
def get_trend(trend_id: str) -> dict:
    trend = trend_detection.get_trend(trend_id)
    if trend is None:
        raise HTTPException(status_code=404, detail="Trend not found")
    return trend


@router.post("/trends/{trend_id}/generate")
async def generate_content(trend_id: str) -> dict:
    """Classify (Haiku) → captions + image prompts (Sonnet) via Bedrock.

    Runs the blocking LLM chain off the event loop. Spends Bedrock tokens.
    """
    try:
        return await asyncio.to_thread(content_generation.generate_for_trend, trend_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Trend not found") from exc
    except Exception as exc:  # noqa: BLE001 - surface Bedrock/model errors to the UI
        raise HTTPException(status_code=502, detail=f"Generation failed: {exc}") from exc


@router.get("/trends/{trend_id}/generated")
def get_generated(trend_id: str) -> dict | None:
    return content_generation.get_generated(trend_id)


@router.post("/trends/{trend_id}/variants/{index}/image")
async def generate_variant_image(trend_id: str, index: int) -> dict:
    """Render an image (Gemini nano banana) for one caption variant.

    Returns the PNG as a base64 data URL the UI can display and download.
    Spends a Gemini image-generation call.
    """
    import base64

    try:
        mime, data = await asyncio.to_thread(
            content_generation.generate_image_for_variant, trend_id, index
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Variant not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - surface Gemini errors to the UI
        raise HTTPException(status_code=502, detail=f"Image generation failed: {exc}") from exc

    encoded = base64.b64encode(data).decode("ascii")
    return {"mime_type": mime, "data_url": f"data:{mime};base64,{encoded}"}
