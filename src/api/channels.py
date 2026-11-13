"""AMAS v1.4.0 — Channels API Endpoints (Phase 2.3 / AMAS-7)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db
from src.database.models import Channel, VideoJob
from src.services.facebook_publisher import FacebookPublisher

router = APIRouter(prefix="/api/channels", tags=["Channels"])


class CreateChannelRequest(BaseModel):
    channel_id: Optional[str] = None
    niche_id: str
    platform: str = Field("tiktok", description="tiktok or facebook")
    account_type: str = Field("profile", description="profile or fanpage")
    browser_profile_id: str
    browser_provider: str = "adspower"
    platform_metadata: Optional[Dict[str, Any]] = None


class WarmupRequest(BaseModel):
    duration_minutes: int = Field(5, ge=1, le=60)


class PublishRequest(BaseModel):
    job_id: str
    caption: str
    affiliate_url: Optional[str] = None


@router.get("/")
async def list_channels(
    platform: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Lists channels, optionally filtered by platform."""
    stmt = select(Channel)
    if platform:
        stmt = stmt.where(Channel.platform == platform)
    res = await db.execute(stmt)
    channels = res.scalars().all()
    return [
        {
            "channel_id": c.channel_id,
            "niche_id": c.niche_id,
            "platform": c.platform,
            "account_type": c.account_type,
            "browser_provider": c.browser_provider,
            "browser_profile_id": c.browser_profile_id,
            "proxy_url": c.proxy_url,
            "lifecycle_status": c.lifecycle_status,
            "platform_metadata": c.platform_metadata,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in channels
    ]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_channel(
    req: CreateChannelRequest,
    db: AsyncSession = Depends(get_db),
):
    """Registers a new channel."""
    chan_id = req.channel_id or f"chan_{uuid.uuid4().hex[:8]}"
    channel = Channel(
        channel_id=chan_id,
        niche_id=req.niche_id,
        platform=req.platform,
        account_type=req.account_type,
        browser_provider=req.browser_provider,
        browser_profile_id=req.browser_profile_id,
        lifecycle_status="warming",
        platform_metadata=req.platform_metadata or {},
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)
    return {
        "channel_id": channel.channel_id,
        "platform": channel.platform,
        "lifecycle_status": channel.lifecycle_status,
    }


@router.post("/{channel_id}/warmup")
async def trigger_warmup(
    channel_id: str,
    req: WarmupRequest,
    db: AsyncSession = Depends(get_db),
):
    """Triggers feed browsing and warmup session."""
    publisher = FacebookPublisher(mock_mode=True)
    res = await publisher.warmup_feed_session(db, channel_id, duration_minutes=req.duration_minutes)
    await db.commit()
    return res


@router.post("/{channel_id}/unlock")
async def unlock_captcha(
    channel_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Unlocks a captcha-blocked channel."""
    publisher = FacebookPublisher(mock_mode=True)
    channel = await publisher.unlock_captcha(db, channel_id)
    await db.commit()
    return {
        "channel_id": channel.channel_id,
        "lifecycle_status": channel.lifecycle_status,
    }


@router.post("/{channel_id}/publish")
async def publish_video(
    channel_id: str,
    req: PublishRequest,
    db: AsyncSession = Depends(get_db),
):
    """Dispatches video publishing to channel."""
    publisher = FacebookPublisher(mock_mode=True)
    result = await publisher.publish_reel(
        session=db,
        channel_id=channel_id,
        job_id=req.job_id,
        caption=req.caption,
        affiliate_url=req.affiliate_url,
    )
    await db.commit()
    return {
        "success": result.success,
        "post_id": result.post_id,
        "post_url": result.post_url,
        "comment_status": result.comment_status,
        "channel_status": result.channel_status,
    }
