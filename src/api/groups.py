"""AMAS v1.5.0 — Facebook Groups & Auto Seeding API (Phase 5.5 / AMAS-17).

Provides endpoints for:
1. Managing monitored Facebook Groups per Project workspace.
2. Triggering automated group posting.
3. Triggering real-time keyword listening & auto-seeding.
4. Viewing audit comment interaction history (GroupCommentLog).
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
from src.database.models import GroupCommentLog, ProjectGroup
from src.services.group_seeding_service import GroupSeedingService

router = APIRouter(prefix="/api/groups", tags=["Groups"])


class AddGroupRequest(BaseModel):
    project_id: str
    group_url: str
    group_name: str
    privacy: str = Field("public", description="public or private")
    approval_mode: bool = False


class PublishToGroupRequest(BaseModel):
    channel_id: str
    product_title: str
    affiliate_url: str
    custom_content: Optional[str] = None


class ScanAndSeedRequest(BaseModel):
    channel_id: str
    product_title: str
    affiliate_url: str
    candidate_posts: Optional[List[Dict[str, Any]]] = None


@router.get("/")
async def list_groups(
    project_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Lists Facebook groups configured for a project."""
    stmt = select(ProjectGroup).order_by(ProjectGroup.created_at.desc())
    if project_id:
        stmt = stmt.where(ProjectGroup.project_id == project_id)

    res = await db.execute(stmt)
    groups = res.scalars().all()
    return [
        {
            "group_id": g.group_id,
            "project_id": g.project_id,
            "group_url": g.group_url,
            "group_name": g.group_name,
            "privacy": g.privacy,
            "approval_mode": g.approval_mode,
            "is_active": g.is_active,
            "last_scanned_at": g.last_scanned_at.isoformat() if g.last_scanned_at else None,
            "created_at": g.created_at.isoformat() if g.created_at else None,
        }
        for g in groups
    ]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def add_group(
    req: AddGroupRequest,
    db: AsyncSession = Depends(get_db),
):
    """Adds a new Facebook group to project."""
    group_id = f"grp_{uuid.uuid4().hex[:10]}"
    group = ProjectGroup(
        group_id=group_id,
        project_id=req.project_id,
        group_url=req.group_url,
        group_name=req.group_name,
        privacy=req.privacy,
        approval_mode=req.approval_mode,
    )
    db.add(group)
    await db.commit()
    await db.refresh(group)

    return {
        "group_id": group.group_id,
        "project_id": group.project_id,
        "group_url": group.group_url,
        "group_name": group.group_name,
        "privacy": group.privacy,
        "approval_mode": group.approval_mode,
        "is_active": group.is_active,
    }


@router.post("/{group_id}/post")
async def post_to_group(
    group_id: str,
    req: PublishToGroupRequest,
    db: AsyncSession = Depends(get_db),
):
    """Dispatches a dynamic group post."""
    service = GroupSeedingService()
    try:
        res = await service.publish_to_group(
            session=db,
            group_id=group_id,
            channel_id=req.channel_id,
            product_title=req.product_title,
            affiliate_url=req.affiliate_url,
            custom_content=req.custom_content,
            mock_mode=True,
        )
        return res
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/{group_id}/scan-seed")
async def scan_and_seed(
    group_id: str,
    req: ScanAndSeedRequest,
    db: AsyncSession = Depends(get_db),
):
    """Scans group for keyword triggers and posts dynamic seeding comments."""
    service = GroupSeedingService()
    try:
        results = await service.scan_and_seed_group(
            session=db,
            group_id=group_id,
            channel_id=req.channel_id,
            product_title=req.product_title,
            affiliate_url=req.affiliate_url,
            candidate_posts=req.candidate_posts,
            mock_mode=True,
        )
        return {"group_id": group_id, "seeded_count": len(results), "comments": results}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/logs")
async def list_seeding_logs(
    project_id: Optional[str] = None,
    group_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Retrieves comment seeding audit logs."""
    stmt = select(GroupCommentLog).order_by(GroupCommentLog.created_at.desc())
    if project_id:
        stmt = stmt.where(GroupCommentLog.project_id == project_id)
    if group_id:
        stmt = stmt.where(GroupCommentLog.group_id == group_id)

    res = await db.execute(stmt)
    logs = res.scalars().all()

    return [
        {
            "log_id": l.log_id,
            "group_id": l.group_id,
            "project_id": l.project_id,
            "post_id": l.post_id,
            "post_content": l.post_content,
            "matched_keyword": l.matched_keyword,
            "comment_text": l.comment_text,
            "channel_id": l.channel_id,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in logs
    ]
