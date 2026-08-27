from __future__ import annotations

import asyncio

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.services import brand_kb_storage
from app.services.brand_kb_storage import BrandStorageError

router = APIRouter(prefix="/brand-kb")


@router.get("")
async def list_documents() -> dict:
    """List brand KB documents in S3, grouped by the category prefixes."""
    try:
        docs = await asyncio.to_thread(brand_kb_storage.list_documents)
    except BrandStorageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "documents": docs,
        "categories": brand_kb_storage.CATEGORIES,
    }


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form("guidelines"),
) -> dict:
    """Upload one brand-guideline file to the S3 brand KB."""
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file.")
    try:
        return await asyncio.to_thread(
            brand_kb_storage.upload_document, category, file.filename or "file", data
        )
    except BrandStorageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


class DeleteRequest(BaseModel):
    key: str


@router.post("/delete")
async def delete_document(req: DeleteRequest) -> dict:
    """Delete a brand KB document by its S3 key."""
    try:
        await asyncio.to_thread(brand_kb_storage.delete_document, req.key)
    except BrandStorageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "key": req.key}


@router.post("/rebuild")
async def rebuild() -> dict:
    """Re-index the brand KB from S3 (extract → chunk → embed). Returns chunk count."""
    try:
        chunks = await asyncio.to_thread(brand_kb_storage.rebuild_kb)
    except BrandStorageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - surface embedding/network errors
        raise HTTPException(status_code=502, detail=f"Rebuild failed: {exc}") from exc
    return {"chunks": chunks}
