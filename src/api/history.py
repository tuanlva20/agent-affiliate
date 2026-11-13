"""AMAS v1.4.0 — History & Competitor Data API Endpoints (Phase 2.3 / AMAS-7)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db
from src.database.models import CompetitorVideo, PublishLog, VideoComment

router = APIRouter(prefix="/api/history", tags=["History"])


class ReplyCommentRequest(BaseModel):
    reply_text: str = Field(..., description="KOC response text")


@router.get("/publishes")
async def list_publishes(
    platform: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Retrieves publishing history."""
    stmt = select(PublishLog).order_by(PublishLog.created_at.desc())
    if platform:
        stmt = stmt.where(PublishLog.platform == platform)
    res = await db.execute(stmt)
    logs = res.scalars().all()
    return [
        {
            "log_id": l.log_id,
            "job_id": l.job_id,
            "channel_id": l.channel_id,
            "platform": l.platform,
            "published_video_id": l.published_video_id,
            "published_url": l.published_url,
            "status": l.status,
            "error_message": l.error_message,
            "published_at": l.published_at.isoformat() if l.published_at else None,
        }
        for l in logs
    ]


@router.get("/comments")
async def list_comments(
    intent: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Retrieves received comments and intent classification."""
    stmt = select(VideoComment).order_by(VideoComment.created_at.desc())
    if intent:
        stmt = stmt.where(VideoComment.intent == intent)
    res = await db.execute(stmt)
    comments = res.scalars().all()
    return [
        {
            "comment_id": c.comment_id,
            "channel_id": c.channel_id,
            "video_id": c.video_id,
            "author_id": c.author_id,
            "author_name": c.author_name,
            "comment_text": c.comment_text,
            "intent": c.intent,
            "reply_text": c.reply_text,
            "reply_status": c.reply_status,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "replied_at": c.replied_at.isoformat() if c.replied_at else None,
        }
        for c in comments
    ]


@router.post("/comments/{comment_id}/reply")
async def reply_comment(
    comment_id: str,
    req: ReplyCommentRequest,
    db: AsyncSession = Depends(get_db),
):
    """Dispatches KOC conversion reply to comment."""
    comment = await db.get(VideoComment, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    comment.reply_text = req.reply_text
    comment.reply_status = "replied"
    comment.replied_at = datetime.now(timezone.utc)
    await db.commit()
    return {
        "comment_id": comment.comment_id,
        "reply_status": comment.reply_status,
        "reply_text": comment.reply_text,
    }


@router.get("/competitor-videos")
async def list_competitor_videos(
    competitor_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Retrieves scraped competitor videos."""
    stmt = select(CompetitorVideo).order_by(CompetitorVideo.scraped_at.desc())
    if competitor_id:
        stmt = stmt.where(CompetitorVideo.competitor_id == competitor_id)
    res = await db.execute(stmt)
    videos = res.scalars().all()
    return [
        {
            "video_id": v.video_id,
            "competitor_id": v.competitor_id,
            "video_url": v.video_url,
            "caption": v.caption,
            "views_count": v.views_count,
            "likes_count": v.likes_count,
            "product_url": v.product_url,
            "scraped_at": v.scraped_at.isoformat() if v.scraped_at else None,
        }
        for v in videos
    ]
