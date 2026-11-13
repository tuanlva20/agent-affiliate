"""AMAS v1.4.0 — Proxy Manager Service (Phase 2.2 / AMAS-6).

Manages residential / datacenter proxy pools:
1. Health checks: latency measurement, alive/dead status detection.
2. Proxy assignment & intelligent rotation for multi-channel operations.
3. Integration with Channel anti-detect browser profiles.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import aiohttp
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Channel, Proxy

logger = logging.getLogger("amas.services.proxy_manager")


class ProxyManagerError(Exception):
    """Base exception for ProxyManager operations."""
    pass


class ProxyManagerService:
    """Service to monitor, test, assign, and rotate proxies."""

    CHECK_ENDPOINT = "https://httpbin.org/ip"
    DEFAULT_TIMEOUT_SEC = 5.0

    def __init__(self, mock_mode: Optional[bool] = None, timeout: float = DEFAULT_TIMEOUT_SEC) -> None:
        self.mock_mode = (
            mock_mode
            if mock_mode is not None
            else bool(os.environ.get("PROXY_MANAGER_MOCK", "1") == "1")
        )
        self.timeout = timeout

    async def check_proxy_health(self, proxy: Proxy) -> Tuple[bool, int]:
        """Check latency and connectivity of a single proxy."""
        if self.mock_mode:
            # Deterministic simulation based on proxy_url
            is_alive = "9999" not in proxy.proxy_url  # port 9999 simulates dead in test
            latency = 120 if is_alive else 9999
            return is_alive, latency

        start_time = time.monotonic()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.CHECK_ENDPOINT,
                    proxy=proxy.proxy_url,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as resp:
                    if resp.status == 200:
                        elapsed_ms = int((time.monotonic() - start_time) * 1000)
                        return True, elapsed_ms
                    return False, 9999
        except Exception as exc:
            logger.debug(f"Proxy check failed for {proxy.proxy_url} — {exc}")
            return False, 9999

    async def update_proxy_status(self, session: AsyncSession, proxy_id: str) -> Proxy:
        """Runs health check on proxy and updates database state."""
        proxy = await session.get(Proxy, proxy_id)
        if not proxy:
            raise ProxyManagerError(f"Proxy not found: {proxy_id}")

        is_alive, latency = await self.check_proxy_health(proxy)
        proxy.status = "alive" if is_alive else "dead"
        proxy.last_checked_at = datetime.now(timezone.utc)
        await session.flush()
        return proxy

    async def assign_proxy_to_channel(
        self,
        session: AsyncSession,
        channel_id: str,
        proxy_id: str,
    ) -> Proxy:
        """Assigns specific proxy to channel via channel metadata."""
        channel = await session.get(Channel, channel_id)
        if not channel:
            raise ProxyManagerError(f"Channel not found: {channel_id}")

        proxy = await session.get(Proxy, proxy_id)
        if not proxy:
            raise ProxyManagerError(f"Proxy not found: {proxy_id}")

        # Store in channel's platform_metadata
        meta = dict(channel.platform_metadata or {})
        meta["assigned_proxy_id"] = proxy_id
        meta["assigned_proxy_url"] = proxy.proxy_url
        channel.platform_metadata = meta

        proxy.assigned_count += 1
        await session.flush()
        return proxy

    async def rotate_proxy_for_channel(
        self,
        session: AsyncSession,
        channel_id: str,
    ) -> Optional[Proxy]:
        """Assigns the least loaded alive proxy to channel."""
        channel = await session.get(Channel, channel_id)
        if not channel:
            raise ProxyManagerError(f"Channel not found: {channel_id}")

        current_meta = dict(channel.platform_metadata or {})
        current_proxy_id = current_meta.get("assigned_proxy_id")

        stmt_available = (
            select(Proxy)
            .where(
                Proxy.status == "alive",
                Proxy.proxy_id != current_proxy_id if current_proxy_id else True,
            )
            .order_by(Proxy.assigned_count.asc())
            .limit(1)
        )
        res = await session.execute(stmt_available)
        best_proxy = res.scalars().first()

        if best_proxy:
            await self.assign_proxy_to_channel(session, channel_id, best_proxy.proxy_id)

        return best_proxy

    async def get_channel_proxy(
        self,
        session: AsyncSession,
        channel_id: str,
    ) -> Optional[Proxy]:
        """Retrieves assigned proxy for a channel."""
        channel = await session.get(Channel, channel_id)
        if not channel or not channel.platform_metadata:
            return None
        proxy_id = channel.platform_metadata.get("assigned_proxy_id")
        if not proxy_id:
            return None
        return await session.get(Proxy, proxy_id)
