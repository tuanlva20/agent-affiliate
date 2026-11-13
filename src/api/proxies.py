"""AMAS v1.4.0 — Proxies API Endpoints (Phase 2.3 / AMAS-7)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db
from src.database.models import Proxy
from src.services.proxy_manager import ProxyManagerService

router = APIRouter(prefix="/api/proxies", tags=["Proxies"])


class CreateProxyRequest(BaseModel):
    proxy_id: Optional[str] = None
    proxy_url: str = Field(..., description="e.g. http://user:pass@1.2.3.4:8080")
    protocol: str = Field("http", description="http or socks5")


@router.get("/")
async def list_proxies(
    db: AsyncSession = Depends(get_db),
):
    """Lists proxies with status and usage."""
    stmt = select(Proxy).order_by(Proxy.assigned_count.asc())
    res = await db.execute(stmt)
    proxies = res.scalars().all()
    return [
        {
            "proxy_id": p.proxy_id,
            "proxy_url": p.proxy_url,
            "protocol": p.protocol,
            "status": p.status,
            "assigned_count": p.assigned_count,
            "last_checked_at": p.last_checked_at.isoformat() if p.last_checked_at else None,
        }
        for p in proxies
    ]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_proxy(
    req: CreateProxyRequest,
    db: AsyncSession = Depends(get_db),
):
    """Registers a new proxy."""
    px_id = req.proxy_id or f"proxy_{uuid.uuid4().hex[:8]}"
    proxy = Proxy(
        proxy_id=px_id,
        proxy_url=req.proxy_url,
        protocol=req.protocol,
        status="unchecked",
    )
    db.add(proxy)
    await db.commit()
    await db.refresh(proxy)
    return {
        "proxy_id": proxy.proxy_id,
        "proxy_url": proxy.proxy_url,
        "status": proxy.status,
    }


@router.post("/{proxy_id}/check")
async def check_proxy(
    proxy_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Runs health check on proxy."""
    service = ProxyManagerService(mock_mode=True)
    proxy = await service.update_proxy_status(db, proxy_id)
    await db.commit()
    return {
        "proxy_id": proxy.proxy_id,
        "status": proxy.status,
        "last_checked_at": proxy.last_checked_at.isoformat() if proxy.last_checked_at else None,
    }


@router.post("/rotate/{channel_id}")
async def rotate_channel_proxy(
    channel_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Rotates proxy for specified channel."""
    service = ProxyManagerService(mock_mode=True)
    proxy = await service.rotate_proxy_for_channel(db, channel_id)
    if not proxy:
        raise HTTPException(status_code=404, detail="No alive proxy available for rotation")
    await db.commit()
    return {
        "channel_id": channel_id,
        "assigned_proxy_id": proxy.proxy_id,
        "proxy_url": proxy.proxy_url,
    }
