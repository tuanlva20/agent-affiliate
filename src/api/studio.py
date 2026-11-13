"""AMAS v1.4.0 — Studio API Endpoints (Phase 2.3 / AMAS-7)."""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db
from src.database.models import MotionAsset, VideoJob
from src.services.hybrid_swap_pipeline import HybridSwapPipeline
from src.services.motion_control_engine import MotionControlEngine
from src.services.scene_analyzer import SceneAnalyzerService

router = APIRouter(prefix="/api/studio", tags=["Studio"])


class PreprocessRequest(BaseModel):
    video_url_or_path: str = Field(..., description="Video URL or local filepath")
    cut_clips: bool = Field(False, description="Whether to extract video segment MP4 files")


class GenerateRequest(BaseModel):
    product_id: str
    niche_id: str
    channel_id: Optional[str] = None
    character_image_url: str
    product_image_url: Optional[str] = None
    script: Optional[str] = None
    segments_data: Optional[List[Dict[str, Any]]] = None


class FaceSwapRequest(BaseModel):
    product_id: str
    niche_id: str
    channel_id: Optional[str] = None
    source_video_path: str
    face_image_path: str
    script: Optional[str] = None


@router.post("/preprocess")
async def preprocess_video(
    req: PreprocessRequest,
    db: AsyncSession = Depends(get_db),
):
    """Deconstructs competitor video into 4 segments and saves MotionAsset."""
    service = SceneAnalyzerService(mock_mode=True)
    try:
        result = await service.analyze_and_segment(
            video_url_or_path=req.video_url_or_path,
            save_to_db=True,
            session=db,
            cut_clips=req.cut_clips,
        )
        await db.commit()
        return result.to_dict()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Video preprocessing failed: {exc}",
        )


@router.get("/motion-assets")
async def list_motion_assets(
    db: AsyncSession = Depends(get_db),
):
    """Retrieves list of saved motion assets."""
    stmt = select(MotionAsset).order_by(MotionAsset.created_at.desc())
    res = await db.execute(stmt)
    assets = res.scalars().all()
    return [
        {
            "asset_id": a.asset_id,
            "source_type": a.source_type,
            "source_url": a.source_url,
            "cover_url": a.cover_url,
            "duration": a.duration,
            "motion_features": a.motion_features,
            "is_official": a.is_official,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in assets
    ]


@router.post("/generate")
async def generate_motion_video(
    req: GenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Dispatches Kling v3 Motion Control video generation."""
    job_id = f"job_mc_{uuid.uuid4().hex[:10]}"
    job = VideoJob(
        job_id=job_id,
        product_id=req.product_id,
        niche_id=req.niche_id,
        channel_id=req.channel_id,
        character_image_url=req.character_image_url,
        product_image_url=req.product_image_url,
        script=req.script,
        status="created",
        motion_mode="kling_motion",
    )
    db.add(job)
    await db.flush()

    engine = MotionControlEngine(mock_mode=True)
    result = await engine.process_job(
        job_id=job_id,
        character_image_path=req.character_image_url,
        product_image_path=req.product_image_url,
        script=req.script,
        segments_data=req.segments_data,
        session=db,
    )
    await db.commit()
    return result


@router.post("/face-swap")
async def generate_hybrid_swap(
    req: FaceSwapRequest,
    db: AsyncSession = Depends(get_db),
):
    """Dispatches cost-effective hybrid face swap & anti-AI evasion."""
    job_id = f"job_hs_{uuid.uuid4().hex[:10]}"
    job = VideoJob(
        job_id=job_id,
        product_id=req.product_id,
        niche_id=req.niche_id,
        channel_id=req.channel_id,
        character_image_url=req.face_image_path,
        source_video_url=req.source_video_path,
        script=req.script,
        status="created",
        motion_mode="hybrid_swap",
    )
    db.add(job)
    await db.flush()

    pipeline = HybridSwapPipeline(mock_mode=True)
    result = await pipeline.process_hybrid_job(
        job_id=job_id,
        source_video_path=req.source_video_path,
        face_image_path=req.face_image_path,
        script=req.script,
        session=db,
    )
    await db.commit()
    return result


@router.get("/jobs/{job_id}")
async def get_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieves current execution status of a VideoJob."""
    job = await db.get(VideoJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": job.job_id,
        "product_id": job.product_id,
        "channel_id": job.channel_id,
        "status": job.status,
        "motion_mode": job.motion_mode,
        "output_video_path": job.output_video_path,
        "audio_path": job.audio_path,
        "script": job.script,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }


@router.get("/jobs/{job_id}/stream")
async def stream_job_progress(job_id: str):
    """Server-Sent Events (SSE) streaming progress of job rendering."""
    async def event_generator():
        stages = [
            {"step": "initialized", "progress": 10, "message": "Pre-processing references"},
            {"step": "motion_control", "progress": 50, "message": "Synthesizing motion frames"},
            {"step": "dubbing", "progress": 80, "message": "Layering voiceover and audio ducking"},
            {"step": "completed", "progress": 100, "message": "Video rendering complete"},
        ]
        for stage in stages:
            payload = json.dumps({"job_id": job_id, **stage})
            yield f"data: {payload}\n\n"
            await asyncio.sleep(0.05)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
