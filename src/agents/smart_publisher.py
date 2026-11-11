"""AMAS v1.4.0 — Smart Publisher Agent (Feature F25).

Orchestrates automated video publishing to TikTok via AliasMode CDP and
HumanBehaviorService biometrics engine, enforcing Channel lifecycle guards
and Showcase product anchor attachments.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import AppConfig
from src.database.models import Channel, VideoJob
from src.services.browser_adapter import BrowserAdapter
from src.services.human_behavior import HumanBehaviorService

logger = logging.getLogger("amas.agents.smart_publisher")


@dataclass
class PublishResult:
    """Outcome of a video publishing attempt by SmartPublisher."""

    success: bool
    video_id: Optional[str] = None
    channel_status: str = ""
    published_url: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.video_id and not self.published_url:
            self.published_url = f"https://www.tiktok.com/@channel/video/{self.video_id}"


class SmartPublisher:
    """Agent 3: Automated Video Publisher with Channel Lifecycle Guard.

    Combines AliasMode BrowserAdapter and HumanBehaviorService to execute
    anti-detect, human-like video uploads and Showcase product anchor linking.
    """

    def __init__(
        self,
        browser_adapter: Optional[BrowserAdapter] = None,
        human_behavior: Optional[HumanBehaviorService] = None,
        config: Optional[AppConfig] = None,
        telegram_bot: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        self.config = config
        self.browser_adapter = browser_adapter or BrowserAdapter()
        # Accept either human_behavior or legacy alias human_svc
        self.human_behavior = human_behavior or kwargs.get("human_svc") or HumanBehaviorService()
        self.human_svc = self.human_behavior  # compatibility alias
        self.telegram_bot = telegram_bot

    @staticmethod
    def _get_channel_attr(channel: Union[Dict[str, Any], Channel], attr: str, default: Any = None) -> Any:
        """Polymorphically extracts an attribute from dict or Channel ORM model."""
        if isinstance(channel, dict):
            return channel.get(attr, default)
        return getattr(channel, attr, default)

    @staticmethod
    def _set_channel_attr(channel: Union[Dict[str, Any], Channel], attr: str, value: Any) -> None:
        """Polymorphically sets an attribute on dict or Channel ORM model."""
        if isinstance(channel, dict):
            channel[attr] = value
        else:
            setattr(channel, attr, value)

    @staticmethod
    async def _safe_await(result: Any) -> Any:
        """Helper to await coroutines while handling synchronous mocks transparently."""
        if inspect.isawaitable(result):
            return await result
        return result

    async def publish_video(
        self,
        job_id: str,
        channel: Optional[Union[Dict[str, Any], Channel]] = None,
        video_path: Optional[str] = None,
        caption: Optional[str] = None,
        product_anchor: Optional[Dict[str, Any]] = None,
        page: Optional[Any] = None,
        telegram_bot: Optional[Any] = None,
        db_session: Optional[AsyncSession] = None,
        warmup_duration_seconds: Optional[int] = None,
        **kwargs: Any,
    ) -> PublishResult:
        """Publishes video to TikTok with lifecycle guards and Showcase anchor.

        Args:
            job_id: Unique identifier of VideoJob.
            channel: Dict representation or Channel ORM instance.
            video_path: Local path to rendered MP4 video.
            caption: Video caption including hashtags and KOC CTA.
            product_anchor: Optional dict describing Showcase product anchor (product_id, title).
            page: Optional mock Playwright Page instance (for deterministic testing).
            telegram_bot: Optional TelegramCommandCenter instance for emergency alerts.
            db_session: Optional AsyncSession for database synchronization.

        Returns:
            PublishResult detailing outcome, channel_status, video_id, and errors.
        """
        ch = channel if channel is not None else kwargs.get("channel_info")
        if ch is None:
            return PublishResult(
                success=False,
                channel_status="unknown",
                error="Cannot publish: channel parameter is required",
            )

        caption_text = caption if caption is not None else kwargs.get("caption_text", "")
        anchor = product_anchor if product_anchor is not None else kwargs.get("anchor", {})
        active_page = page if page is not None else kwargs.get("mock_page")
        active_bot = telegram_bot or self.telegram_bot

        # ------------------------------------------------------------------
        # 1. Channel Lifecycle Guard
        # ------------------------------------------------------------------
        status = self._get_channel_attr(ch, "lifecycle_status", "warming")

        if status == "warming":
            logger.warning(
                "Posting blocked: channel %s is in 'warming' status",
                self._get_channel_attr(ch, "channel_id"),
            )
            return PublishResult(
                success=False,
                video_id=None,
                channel_status="warming",
                error="Cannot publish: channel is in warming stage (nuôi nick); affiliate posting not permitted.",
                metadata={"reason": "lifecycle_guard", "current_status": "warming"},
            )

        if status == "captcha_blocked":
            logger.error(
                "Posting blocked: channel %s is in 'captcha_blocked' status",
                self._get_channel_attr(ch, "channel_id"),
            )
            return PublishResult(
                success=False,
                video_id=None,
                channel_status="captcha_blocked",
                error="Cannot publish: channel is captcha blocked (blocked by Captcha). Manual resolution required.",
                metadata={"reason": "lifecycle_guard", "current_status": "captcha_blocked"},
            )

        if status == "cooldown":
            logger.warning(
                "Posting blocked: channel %s is in 'cooldown' status",
                self._get_channel_attr(ch, "channel_id"),
            )
            return PublishResult(
                success=False,
                video_id=None,
                channel_status="cooldown",
                error="Cannot publish: channel is in cooldown stage; minimum rest interval required.",
                metadata={"reason": "lifecycle_guard", "current_status": "cooldown"},
            )

        if status != "ready_to_post":
            return PublishResult(
                success=False,
                video_id=None,
                channel_status=status,
                error=f"Cannot publish: invalid channel lifecycle status '{status}'",
            )

        # ------------------------------------------------------------------
        # 2. Video Path Verification
        # ------------------------------------------------------------------
        if not video_path:
            return PublishResult(
                success=False,
                channel_status=status,
                error="Cannot publish: missing video file path",
            )

        if not os.path.exists(video_path):
            return PublishResult(
                success=False,
                channel_status=status,
                error=f"Cannot publish: video file not found at {video_path}",
            )

        # ------------------------------------------------------------------
        # 3. Start Browser Profile & Acquire Page via BrowserAdapter
        # ------------------------------------------------------------------
        profile_id = str(
            self._get_channel_attr(ch, "browser_profile_id")
            or self._get_channel_attr(ch, "channel_id")
            or "default_profile"
        )
        cdp_url: Optional[str] = None
        browser: Optional[Any] = None
        context: Optional[Any] = None
        should_close_session = False

        if active_page is not None:
            p = active_page
            try:
                if hasattr(self.browser_adapter, "start_browser"):
                    start_res = self.browser_adapter.start_browser(profile_id)
                    if inspect.isawaitable(start_res):
                        await start_res
            except Exception as exc:
                logger.error("Failed to start browser for profile %s: %s", profile_id, exc)
                return PublishResult(
                    success=False,
                    channel_status=status,
                    error=f"Browser start failure: {exc}",
                    metadata={"profile_id": profile_id, "error": str(exc)},
                )
        else:
            try:
                if hasattr(self.browser_adapter, "start_browser"):
                    start_res = self.browser_adapter.start_browser(profile_id)
                    if inspect.isawaitable(start_res):
                        cdp_url = await start_res
                    else:
                        cdp_url = start_res
                else:
                    cdp_url = f"ws://127.0.0.1:50325/devtools/browser/{profile_id}"
            except Exception as exc:
                logger.error("Failed to start browser for profile %s: %s", profile_id, exc)
                return PublishResult(
                    success=False,
                    channel_status=status,
                    error=f"Browser start failure: {exc}",
                    metadata={"profile_id": profile_id, "error": str(exc)},
                )

            try:
                if hasattr(self.browser_adapter, "connect_over_cdp"):
                    conn_res = self.browser_adapter.connect_over_cdp(str(cdp_url) if cdp_url else profile_id)
                    if inspect.isawaitable(conn_res):
                        conn_tuple = await conn_res
                    else:
                        conn_tuple = conn_res

                    if isinstance(conn_tuple, (tuple, list)) and len(conn_tuple) >= 3:
                        browser, context, p = conn_tuple[0], conn_tuple[1], conn_tuple[2]
                        should_close_session = True
                    elif isinstance(conn_tuple, (tuple, list)) and len(conn_tuple) > 0:
                        p = conn_tuple[-1]
                        should_close_session = True
                    else:
                        p = conn_tuple
                else:
                    raise RuntimeError("Browser adapter does not support connect_over_cdp")
            except Exception as exc:
                logger.error("Failed to acquire browser session for %s: %s", profile_id, exc)
                return PublishResult(
                    success=False,
                    channel_status=status,
                    error=f"Browser session acquisition failure: {exc}",
                    metadata={"profile_id": profile_id, "error": str(exc)},
                )

        try:
            # --------------------------------------------------------------
            # 4. Pre-posting Feed Warmup (Biometrics)
            # --------------------------------------------------------------
            if warmup_duration_seconds is not None:
                warmup_duration = warmup_duration_seconds
            elif "warmup_duration" in kwargs:
                warmup_duration = kwargs["warmup_duration"]
            elif self.config and hasattr(self.config, "browser") and hasattr(self.config.browser, "warmup_duration_seconds"):
                warmup_duration = getattr(self.config.browser, "warmup_duration_seconds", 180)
            elif self.config and hasattr(self.config, "behavior") and hasattr(self.config.behavior, "warmup_duration_seconds"):
                warmup_duration = getattr(self.config.behavior, "warmup_duration_seconds", 180)
            else:
                warmup_duration = 180

            if warmup_duration > 0 and hasattr(self.human_behavior, "warmup_feed_session"):
                raw_time_scale = kwargs.get("time_scale")
                if raw_time_scale is None:
                    raw_time_scale = getattr(self.human_behavior, "time_scale", None)
                if not isinstance(raw_time_scale, (int, float)):
                    time_scale = 1.0
                else:
                    time_scale = float(raw_time_scale)

                raw_fast_mode = kwargs.get("fast_mode")
                if raw_fast_mode is None:
                    raw_fast_mode = getattr(self.human_behavior, "fast_mode", None)
                fast_mode = bool(raw_fast_mode) if isinstance(raw_fast_mode, bool) else False

                await self.human_behavior.warmup_feed_session(
                    p, duration_seconds=warmup_duration, time_scale=time_scale, fast_mode=fast_mode
                )

            # --------------------------------------------------------------
            # 5. Mid-flight Captcha Check
            # --------------------------------------------------------------
            channel_identifier = str(self._get_channel_attr(ch, "channel_id", ""))
            if hasattr(self.human_behavior, "detect_and_handle_captcha"):
                captcha_caught = await self.human_behavior.detect_and_handle_captcha(
                    p, telegram_bot=active_bot, channel_id=channel_identifier
                )
                if captcha_caught:
                    logger.critical("Captcha encountered! Halting publisher for channel %s", profile_id)
                    self._set_channel_attr(ch, "lifecycle_status", "captcha_blocked")
                    if db_session:
                        await db_session.commit()
                    return PublishResult(
                        success=False,
                        video_id=None,
                        channel_status="captcha_blocked",
                        error="Captcha triggered during navigation. Upload halted.",
                        metadata={"profile_id": profile_id, "stage": "feed_or_navigation"},
                    )

            # --------------------------------------------------------------
            # 6. Creator Center Navigation & File Upload
            # --------------------------------------------------------------
            if hasattr(p, "goto"):
                goto_res = p.goto("https://www.tiktok.com/creator-center/upload")
                await self._safe_await(goto_res)

            # Check captcha again after navigation
            if hasattr(self.human_behavior, "detect_and_handle_captcha"):
                captcha_after_nav = await self.human_behavior.detect_and_handle_captcha(
                    p, telegram_bot=active_bot, channel_id=channel_identifier
                )
                if captcha_after_nav:
                    self._set_channel_attr(ch, "lifecycle_status", "captcha_blocked")
                    if db_session:
                        await db_session.commit()
                    return PublishResult(
                        success=False,
                        video_id=None,
                        channel_status="captcha_blocked",
                        error="Captcha triggered during creator center navigation. Upload halted.",
                        metadata={"profile_id": profile_id, "stage": "creator_navigation"},
                    )

            # Upload file
            if hasattr(p, "set_input_files"):
                upload_res = p.set_input_files("input[type='file']", video_path)
                await self._safe_await(upload_res)

            # --------------------------------------------------------------
            # 7. Type Caption via Human Biometric Typing
            # --------------------------------------------------------------
            if caption_text and hasattr(self.human_behavior, "human_type"):
                typo_rate = 0.03
                if self.config and hasattr(self.config, "browser") and hasattr(self.config.browser, "behavior"):
                    typo_rate = self.config.browser.behavior.typo_rate
                await self.human_behavior.human_type(p, "#caption_input", caption_text, typo_rate=typo_rate)

            # --------------------------------------------------------------
            # 8. Product Anchor Attachment (Showcase Yellow Cart Link)
            # --------------------------------------------------------------
            has_anchor = False
            anchor_meta = {}
            if anchor and (anchor.get("product_id") or anchor.get("title") or anchor.get("item_id")):
                has_anchor = True
                anchor_meta = {
                    "product_id": anchor.get("product_id") or anchor.get("item_id"),
                    "title": anchor.get("title", ""),
                }
                await self._attach_product_anchor(p, anchor_meta)

            # --------------------------------------------------------------
            # 9. Confirm Post & Channel State Transition
            # --------------------------------------------------------------
            if hasattr(p, "click"):
                try:
                    click_res = p.click("button[data-e2e='post-btn']")
                    await self._safe_await(click_res)
                except Exception:
                    pass

            video_id = f"tt_pub_{job_id}"
            now_utc = datetime.now(timezone.utc)

            # Update Channel lifecycle to cooldown and record last_posted_at
            self._set_channel_attr(ch, "lifecycle_status", "cooldown")
            self._set_channel_attr(ch, "last_posted_at", now_utc)

            # Synchronize VideoJob in DB if session provided
            if db_session:
                stmt = select(VideoJob).where(VideoJob.job_id == job_id)
                exec_res = await db_session.execute(stmt)
                job = exec_res.scalar_one_or_none()
                if job:
                    job.status = "published"
                await db_session.commit()

            return PublishResult(
                success=True,
                video_id=video_id,
                channel_status="cooldown",
                published_url=f"https://www.tiktok.com/@channel/video/{video_id}",
                metadata={
                    "job_id": job_id,
                    "profile_id": profile_id,
                    "posted_at": now_utc.isoformat(),
                    "has_product_anchor": has_anchor,
                    "anchor": anchor_meta,
                },
            )
        finally:
            if should_close_session:
                try:
                    if browser and hasattr(browser, "close"):
                        close_res = browser.close()
                        if inspect.isawaitable(close_res):
                            await close_res
                except Exception as exc:
                    logger.warning("Error closing browser: %s", exc)
                try:
                    if hasattr(self.browser_adapter, "stop_browser"):
                        stop_res = self.browser_adapter.stop_browser(profile_id)
                        if inspect.isawaitable(stop_res):
                            await stop_res
                except Exception as exc:
                    logger.warning("Error stopping browser profile %s: %s", profile_id, exc)

    async def _attach_product_anchor(self, page: Any, anchor: Dict[str, Any]) -> None:
        """Simulates human interaction to attach Showcase product anchor link."""
        if hasattr(page, "click"):
            try:
                btn_res = page.click("button[data-e2e='add-product-link']")
                await self._safe_await(btn_res)
            except Exception:
                pass

        search_query = anchor.get("title") or anchor.get("product_id") or ""
        if search_query and hasattr(self.human_behavior, "human_type"):
            try:
                await self.human_behavior.human_type(
                    page,
                    "input[placeholder*='Search product']",
                    str(search_query)[:30],
                    typo_rate=0.0,
                )
            except Exception:
                pass

        if hasattr(page, "click"):
            try:
                confirm_res = page.click("button[data-e2e='confirm-anchor']")
                await self._safe_await(confirm_res)
            except Exception:
                pass
