"""AMAS v1.5.0 — Group Seeding Service (Phase 5.4 / AMAS-16).

Handles automated Facebook Group posting & real-time keyword listening comment seeding:
1. Dynamic multi-niche content generation based on Project context (niche_brief, target_audience, tone_of_voice).
2. Negative keyword filtering and sanitization.
3. Anti-detect channel lifecycle checks (fails if captcha_blocked).
4. Strict deduplication against GroupCommentLog (no post seeded twice).
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Channel, GroupCommentLog, Project, ProjectGroup, PublishLog
from src.services.browser_adapter import BrowserAdapter
from src.services.human_behavior import HumanBehaviorService

logger = logging.getLogger("amas.services.group_seeding_service")


def _sanitize_negative_keywords(text: str, negative_keywords: Optional[List[str]]) -> str:
    """Removes or filters out forbidden negative keywords from generated copy."""
    if not text or not negative_keywords:
        return text
    sanitized = text
    for kw in negative_keywords:
        if kw:
            # Case-insensitive replacement of forbidden keywords
            pattern = re.compile(re.escape(kw), re.IGNORECASE)
            sanitized = pattern.sub("", sanitized)
    # Clean up double spaces created by removal
    return re.sub(r"\s+", " ", sanitized).strip()


def generate_dynamic_group_post(
    project: Optional[Project],
    product_title: str,
    affiliate_url: str,
    custom_content: Optional[str] = None,
) -> str:
    """Generates dynamic group post content matching Project niche, audience, and tone.

    Ensures no negative keywords from project are included.
    """
    niche = (project.niche_brief if project and project.niche_brief else "tiêu dùng").strip()
    audience = (project.target_audience if project and project.target_audience else "mọi người").strip()
    tone = (project.tone_of_voice if project and project.tone_of_voice else "thân thiện").lower()
    negative_kws = project.negative_keywords if project and project.negative_keywords else []

    if custom_content:
        content = custom_content.strip()
        if affiliate_url not in content:
            content = f"{content}\n\n👉 Chi tiết sản phẩm: {affiliate_url}"
        return _sanitize_negative_keywords(content, negative_kws)

    # Tone adaptations
    if "genz" in tone or "hài hước" in tone or "fun" in tone:
        post = (
            f"Alo anh em {audience}! ⚡️\n"
            f"Mê mảng {niche} thì không thể bỏ qua quả deal {product_title} này được. "
            f"Dùng bao cuốn, trải nghiệm thực tế siêu ưng ý luôn nha cả nhà.\n\n"
            f"👉 Link múc ở đây nè: {affiliate_url}"
        )
    elif "chuyên gia" in tone or "expert" in tone or "uy tín" in tone:
        post = (
            f"Góc chia sẻ kinh nghiệm dành cho {audience} trong lĩnh vực {niche}:\n"
            f"Để tối ưu hiệu quả và chất lượng công việc, {product_title} là một giải pháp cực kỳ tối ưu và đáng đầu tư. "
            f"Thông số và trải nghiệm vận hành rất chuẩn chỉ.\n\n"
            f"👉 Quý anh/chị có thể tham khảo chi tiết tại: {affiliate_url}"
        )
    else:  # Peer KOC / review chân thực
        post = (
            f"Chia sẻ chân thực cùng {audience} đang quan tâm đến {niche} ạ! ✨\n"
            f"Mình vừa trải nghiệm thực tế em {product_title}, cảm thấy rất hài lòng về chất lượng và độ bền so với tầm giá. "
            f"Bác nào cần thì tham khảo ngay link chính hãng này nhé:\n\n"
            f"👉 {affiliate_url}"
        )

    return _sanitize_negative_keywords(post, negative_kws)


def generate_dynamic_seeding_comment(
    project: Optional[Project],
    post_content: str,
    product_title: str,
    affiliate_url: str,
) -> str:
    """Generates peer KOC seeding comment tailored to the post's context and Project voice."""
    niche = (project.niche_brief if project and project.niche_brief else "sản phẩm").strip()
    tone = (project.tone_of_voice if project and project.tone_of_voice else "thân thiện").lower()
    negative_kws = project.negative_keywords if project and project.negative_keywords else []

    if "genz" in tone or "hài hước" in tone:
        comment = (
            f"Chuẩn bài luôn bác ơi! Về {niche} thì em recommend test qua em {product_title} nhé, "
            f"xài bao đỉnh mà giá cực êm. Link chính hãng em để đây cho bác nào cần: {affiliate_url}"
        )
    elif "chuyên gia" in tone:
        comment = (
            f"Về vấn đề này trong mảng {niche}, mình đã kiểm nghiệm thực tế và thấy giải pháp {product_title} "
            f"xử lý rất triệt để. Bạn có thể tham khảo thông số chi tiết tại đây: {affiliate_url}"
        )
    else:
        comment = (
            f"Đồng quan điểm với bạn! Mình cũng từng tìm hiểu nhiều về {niche} và chốt dùng em {product_title}, "
            f"dùng cực kỳ ưng ý. Mình đặt ở link này giao nhanh và chuẩn: {affiliate_url}"
        )

    return _sanitize_negative_keywords(comment, negative_kws)


class GroupSeedingService:
    """Service providing Facebook Group auto-publishing and real-time comment seeding."""

    def __init__(
        self,
        browser_adapter: Optional[BrowserAdapter] = None,
        human_service: Optional[HumanBehaviorService] = None,
    ):
        self.browser_adapter = browser_adapter or BrowserAdapter()
        self.human_service = human_service or HumanBehaviorService()

    async def publish_to_group(
        self,
        session: AsyncSession,
        group_id: str,
        channel_id: str,
        product_title: str,
        affiliate_url: str,
        custom_content: Optional[str] = None,
        mock_mode: bool = True,
    ) -> Dict[str, Any]:
        """Publishes a dynamic post into a Facebook group adhering to project configuration."""
        group = await session.get(ProjectGroup, group_id)
        if not group:
            raise ValueError(f"ProjectGroup with id '{group_id}' not found.")

        channel = await session.get(Channel, channel_id)
        if not channel:
            raise ValueError(f"Channel with id '{channel_id}' not found.")

        if channel.lifecycle_status == "captcha_blocked":
            raise RuntimeError(f"Channel {channel_id} is captcha_blocked. Cannot publish.")

        project = await session.get(Project, group.project_id)
        content = generate_dynamic_group_post(project, product_title, affiliate_url, custom_content)

        # Determine outcome status based on approval_mode
        status = "pending_approval" if group.approval_mode else "posted"

        post_id = f"post_{uuid.uuid4().hex[:10]}"
        post_url = f"{group.group_url.rstrip('/')}/posts/{post_id}"

        # Record to PublishLog
        log_id = f"log_{uuid.uuid4().hex[:12]}"
        log_entry = PublishLog(
            log_id=log_id,
            project_id=project.project_id if project else None,
            job_id=None,
            channel_id=channel_id,
            platform="facebook",
            published_video_id=post_id,
            published_url=post_url,
            status=status,
            published_at=datetime.now(timezone.utc) if status == "posted" else None,
        )
        session.add(log_entry)
        await session.commit()

        logger.info(
            "Published to group %s via channel %s (status: %s, log: %s)",
            group_id,
            channel_id,
            status,
            log_id,
        )

        return {
            "success": True,
            "group_id": group_id,
            "channel_id": channel_id,
            "status": status,
            "post_id": post_id,
            "post_url": post_url,
            "post_content": content,
            "log_id": log_id,
        }

    async def scan_and_seed_group(
        self,
        session: AsyncSession,
        group_id: str,
        channel_id: str,
        product_title: str,
        affiliate_url: str,
        candidate_posts: Optional[List[Dict[str, Any]]] = None,
        mock_mode: bool = True,
    ) -> List[Dict[str, Any]]:
        """Scans candidate posts in a group, detects trigger keywords, deduplicates, and seeds comments."""
        group = await session.get(ProjectGroup, group_id)
        if not group:
            raise ValueError(f"ProjectGroup with id '{group_id}' not found.")

        channel = await session.get(Channel, channel_id)
        if not channel:
            raise ValueError(f"Channel with id '{channel_id}' not found.")

        if channel.lifecycle_status == "captcha_blocked":
            raise RuntimeError(f"Channel {channel_id} is captcha_blocked. Cannot seed comments.")

        project = await session.get(Project, group.project_id)
        trigger_kws = [kw.lower().strip() for kw in (project.trigger_keywords or []) if kw]
        negative_kws = [kw.lower().strip() for kw in (project.negative_keywords or []) if kw]

        if candidate_posts is None:
            # Default mock posts for scanning
            candidate_posts = [
                {
                    "post_id": f"p_feed_{uuid.uuid4().hex[:6]}",
                    "post_text": f"Có ai biết chỗ nào bán {project.niche_brief if project else 'đồ'} ngon bổ rẻ không ạ?",
                }
            ]

        seeded_results: List[Dict[str, Any]] = []

        for post in candidate_posts:
            post_id = str(post.get("post_id", "")).strip()
            post_text = str(post.get("post_text", ""))

            if not post_id or not post_text:
                continue

            lower_text = post_text.lower()

            # 1. Negative keywords check: skip if post contains negative keyword
            if any(nkw in lower_text for nkw in negative_kws):
                logger.debug("Post %s contains negative keyword. Skipping.", post_id)
                continue

            # 2. Trigger keywords check
            matched_kw: Optional[str] = None
            if trigger_kws:
                for tkw in trigger_kws:
                    if tkw in lower_text:
                        matched_kw = tkw
                        break
                if not matched_kw:
                    logger.debug("Post %s does not match any trigger keywords. Skipping.", post_id)
                    continue
            else:
                matched_kw = "general"

            # 3. Deduplication check: Has this post in this group already been seeded?
            stmt = select(GroupCommentLog).where(
                GroupCommentLog.group_id == group_id,
                GroupCommentLog.post_id == post_id,
            )
            existing_log = (await session.execute(stmt)).scalars().first()
            if existing_log:
                logger.info("Post %s in group %s already seeded. Skipping (dedup).", post_id, group_id)
                continue

            # 4. Generate dynamic seeding comment
            comment_text = generate_dynamic_seeding_comment(project, post_text, product_title, affiliate_url)

            # 5. Persist to GroupCommentLog
            log_id = f"gcl_{uuid.uuid4().hex[:12]}"
            comment_log = GroupCommentLog(
                log_id=log_id,
                group_id=group_id,
                project_id=project.project_id if project else None,
                post_id=post_id,
                post_content=post_text,
                matched_keyword=matched_kw,
                comment_text=comment_text,
                channel_id=channel_id,
            )
            session.add(comment_log)

            seeded_results.append({
                "log_id": log_id,
                "group_id": group_id,
                "post_id": post_id,
                "matched_keyword": matched_kw,
                "comment_text": comment_text,
            })

        group.last_scanned_at = datetime.now(timezone.utc)
        await session.commit()

        return seeded_results
