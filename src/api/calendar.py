"""AMAS v1.5.0 — Content Calendar & Multi-Platform Publishing Schedule API (Phase 5.5 / AMAS-17).

Features:
1. Multi-platform publish scheduling (TikTok, Facebook, Instagram).
2. Target types: Reel, Feed Post, Facebook Group.
3. Golden hour recommendation presets (Golden Slots) based on peak affiliate engagement.
4. Flexible schedule modifications (drag-and-drop reschedule support).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db
from src.database.models import Channel, Project, PublishSchedule

router = APIRouter(prefix="/api/calendar", tags=["Calendar"])

GOLDEN_SLOTS = {
    "tiktok": [
        {"time": "11:30", "label": "Nghỉ trưa văn phòng / Học sinh", "engagement": "Rất cao"},
        {"time": "18:00", "label": "Tan sở / Chuẩn bị ăn tối", "engagement": "Cao"},
        {"time": "20:30", "label": "Khung giờ vàng lướt giải trí đêm", "engagement": "Đỉnh điểm"},
    ],
    "facebook": [
        {"time": "07:00", "label": "Buổi sáng thức dậy đọc tin tức", "engagement": "Khá cao"},
        {"time": "12:00", "label": "Nghỉ trưa lướt Reels & Groups", "engagement": "Cao"},
        {"time": "19:30", "label": "Khung giờ vàng mua sắm gia đình", "engagement": "Đỉnh điểm"},
    ],
    "instagram": [
        {"time": "12:00", "label": "Nghỉ trưa xem Story & Reels", "engagement": "Cao"},
        {"time": "17:30", "label": "Chiều tan làm check thông báo", "engagement": "Khá cao"},
        {"time": "21:00", "label": "Tối muộn mua sắm thời trang & mỹ phẩm", "engagement": "Đỉnh điểm"},
    ],
}


class CreateScheduleRequest(BaseModel):
    project_id: Optional[str] = None
    channel_id: Optional[str] = None
    platform: str = Field("facebook", description="tiktok, facebook, instagram")
    target_type: str = Field("reel", description="reel, post, group")
    title: str = Field(..., min_length=1, max_length=200)
    caption: Optional[str] = None
    job_id: Optional[str] = None
    scheduled_at: datetime


class UpdateScheduleRequest(BaseModel):
    scheduled_at: Optional[datetime] = None
    status: Optional[str] = Field(None, description="scheduled, publishing, published, failed")
    title: Optional[str] = None
    caption: Optional[str] = None


@router.get("/")
async def list_calendar_schedules(
    project_id: Optional[str] = None,
    platform: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Lists scheduled posts filtered by project and platform, with Golden Slots."""
    stmt = select(PublishSchedule).order_by(PublishSchedule.scheduled_at.asc())
    if project_id:
        stmt = stmt.where(PublishSchedule.project_id == project_id)
    if platform:
        stmt = stmt.where(PublishSchedule.platform == platform)

    res = await db.execute(stmt)
    schedules = res.scalars().all()

    return {
        "golden_slots": GOLDEN_SLOTS,
        "schedules": [
            {
                "schedule_id": s.schedule_id,
                "project_id": s.project_id,
                "channel_id": s.channel_id,
                "platform": s.platform,
                "target_type": s.target_type,
                "title": s.title,
                "caption": s.caption,
                "job_id": s.job_id,
                "scheduled_at": s.scheduled_at.isoformat() if s.scheduled_at else None,
                "status": s.status,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in schedules
        ],
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_schedule(
    req: CreateScheduleRequest,
    db: AsyncSession = Depends(get_db),
):
    """Creates a new scheduled publish item."""
    if req.platform not in {"tiktok", "facebook", "instagram"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported platform: {req.platform}",
        )
    if req.target_type not in {"reel", "post", "group"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported target_type: {req.target_type}",
        )

    sched_id = f"sched_{uuid.uuid4().hex[:10]}"
    sched = PublishSchedule(
        schedule_id=sched_id,
        project_id=req.project_id,
        channel_id=req.channel_id,
        platform=req.platform,
        target_type=req.target_type,
        title=req.title,
        caption=req.caption,
        job_id=req.job_id,
        scheduled_at=req.scheduled_at,
        status="scheduled",
    )
    db.add(sched)
    await db.commit()
    await db.refresh(sched)

    return {
        "schedule_id": sched.schedule_id,
        "project_id": sched.project_id,
        "channel_id": sched.channel_id,
        "platform": sched.platform,
        "target_type": sched.target_type,
        "title": sched.title,
        "caption": sched.caption,
        "scheduled_at": sched.scheduled_at.isoformat() if sched.scheduled_at else None,
        "status": sched.status,
    }


@router.patch("/{schedule_id}")
async def update_schedule(
    schedule_id: str,
    req: UpdateScheduleRequest,
    db: AsyncSession = Depends(get_db),
):
    """Updates schedule date, status or content."""
    sched = await db.get(PublishSchedule, schedule_id)
    if not sched:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule {schedule_id} not found",
        )

    if req.scheduled_at is not None:
        sched.scheduled_at = req.scheduled_at
    if req.status is not None:
        if req.status not in {"scheduled", "publishing", "published", "failed"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid schedule status: {req.status}",
            )
        sched.status = req.status
    if req.title is not None:
        sched.title = req.title
    if req.caption is not None:
        sched.caption = req.caption

    await db.commit()
    await db.refresh(sched)

    return {
        "schedule_id": sched.schedule_id,
        "scheduled_at": sched.scheduled_at.isoformat() if sched.scheduled_at else None,
        "status": sched.status,
        "title": sched.title,
    }


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(schedule_id: str, db: AsyncSession = Depends(get_db)):
    """Deletes a schedule item."""
    sched = await db.get(PublishSchedule, schedule_id)
    if not sched:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule {schedule_id} not found",
        )
    await db.delete(sched)
    await db.commit()
    return None
