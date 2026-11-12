"""AMAS MCP Server (stdio) — Bridges NousResearch Hermes Agent to AMAS v1.4.0.

Exposes deterministic orchestration, product approval, and self-learning analytics
tools over MCP stdio so Hermes Agent handles persistent memory (MEMORY.md),
skill self-improvement, and natural Telegram conversation while AMAS enforces
TikTok safety guards.
"""

from __future__ import annotations

import logging
import os
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure repository root is importable when launched as a subprocess by `hermes`.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# MCP stdio reserves stdout exclusively for JSON-RPC frames.
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

from dotenv import load_dotenv
try:
    from mcp.server.fastmcp import FastMCP as _MCPServer
except ImportError:
    from mcp.server.mcpserver import MCPServer as _MCPServer
from sqlalchemy import func, select

from src.agents.hermes_orchestrator import HermesOrchestrator
from src.bot.handlers import execute_callback
from src.core.config import AppConfig, load_config
from src.database.models import Channel, Competitor, Metric, Niche, Product, VideoComment, VideoJob
from src.database.session import get_db
from src.services.tiktok_scraper import InvalidTikTokURLError, TikTokScraper

mcp = _MCPServer(
    name="amas",
    instructions=(
        "AMAS TikTok Affiliate control & analytics tools. "
        "Use amas_get_learning_insights before updating MEMORY.md or skills; "
        "never publish to channels in warming/cooldown/captcha_blocked status."
    ),
)


def _get_config() -> AppConfig:
    cfg_path = REPO_ROOT / "config.yaml"
    return load_config(str(cfg_path)) if cfg_path.exists() else AppConfig()


def _get_db_url(config: AppConfig, database_url: Optional[str] = None) -> str:
    return (
        database_url
        or os.getenv("POSTGRES_URL")
        or os.getenv("DATABASE_URL")
        or config.database.url
    )


async def _group_counts(session: Any, column: Any) -> Dict[str, int]:
    rows = (await session.execute(select(column, func.count()).group_by(column))).all()
    return {str(key): int(cnt) for key, cnt in rows}


@mcp.tool()
async def amas_get_status(
    niche_id: str = "all",
    database_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Return channel lifecycle counts, product queue counts, video job counts, and captcha alerts."""
    config = _get_config()
    db_url = _get_db_url(config, database_url)

    async with get_db(db_url) as session:
        channels_q = select(Channel)
        if niche_id not in ("", "all"):
            channels_q = channels_q.where(Channel.niche_id == niche_id)
        channels = (await session.execute(channels_q)).scalars().all()

        return {
            "niche_filter": niche_id,
            "channels_total": len(channels),
            "channels": [
                {
                    "channel_id": c.channel_id,
                    "niche_id": c.niche_id,
                    "lifecycle_status": c.lifecycle_status,
                    "warmup_days_completed": c.warmup_days_completed,
                    "browser_profile_id": c.browser_profile_id,
                }
                for c in channels
            ],
            "captcha_blocked_channels": [
                c.channel_id for c in channels if c.lifecycle_status == "captcha_blocked"
            ],
            "products_by_status": await _group_counts(session, Product.status),
            "video_jobs_by_status": await _group_counts(session, VideoJob.status),
        }


async def _close_orchestrator_resources(orchestrator: HermesOrchestrator) -> None:
    if getattr(orchestrator.base_scout, "kalodata_client", None) is not None:
        await orchestrator.base_scout.kalodata_client.close()
    bot = getattr(orchestrator.telegram_bot, "bot", None)
    if bot is not None and getattr(bot, "session", None) is not None:
        await bot.session.close()


@mcp.tool()
async def amas_scout_products(
    niche_id: str = "thoi_trang_nu",
    limit: int = 5,
    save_pending: bool = True,
    send_cards: bool = True,
    mock_mode: bool = False,
    database_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Discover and score products from saved competitors + Kalodata, save pending items, and send Telegram cards."""
    config = _get_config()
    db_url = _get_db_url(config, database_url)
    orchestrator = HermesOrchestrator(config=config, mock_mode=mock_mode)

    try:
        async with get_db(db_url) as session:
            return await orchestrator.discover_and_dispatch(
                niche_id=niche_id,
                limit=limit,
                save_pending=save_pending,
                send_cards=send_cards,
                db_session=session,
            )
    finally:
        await _close_orchestrator_resources(orchestrator)


def _require_valid_niche(niche_id: str, config: AppConfig) -> Optional[Dict[str, Any]]:
    valid_ids = [n.niche_id for n in config.niches] or ["thoi_trang_nu", "do_gia_dung"]
    clean = (niche_id or "").strip()
    if clean in valid_ids:
        return None
    return {
        "success": False,
        "needs_clarification": True,
        "missing": "niche_id",
        "allowed_niches": valid_ids,
        "message": f"Thiếu hoặc sai ngách. Hãy hỏi lại người dùng chọn 1 trong các ngách: {', '.join(valid_ids)}.",
    }


@mcp.tool()
async def amas_add_competitor(
    profile_url: str,
    niche_id: str = "",
    username: str = "",
    database_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Save a TikTok competitor channel URL into PostgreSQL for periodic video/product scanning."""
    config = _get_config()
    err = _require_valid_niche(niche_id, config)
    if err is not None:
        return err

    try:
        clean_url = TikTokScraper(mock_mode=True)._validate_channel_url(profile_url)
    except InvalidTikTokURLError as exc:
        return {"success": False, "needs_clarification": True, "missing": "profile_url", "error": str(exc)}

    handle = username.strip().lstrip("@") or clean_url.rstrip("/").split("/")[-1].lstrip("@") or "competitor"
    comp_id = f"comp_{niche_id}_{handle[:30]}"
    db_url = _get_db_url(config, database_url)

    async with get_db(db_url) as session:
        if not await session.scalar(select(Niche).where(Niche.niche_id == niche_id)):
            niche_cfg = config.get_niche(niche_id)
            session.add(Niche(niche_id=niche_id, name=niche_cfg.name if niche_cfg else niche_id))
            await session.flush()

        existing = await session.scalar(select(Competitor).where(Competitor.competitor_id == comp_id))
        if existing is None:
            session.add(
                Competitor(
                    competitor_id=comp_id,
                    niche_id=niche_id,
                    username=handle,
                    profile_url=clean_url,
                    track_status="active",
                )
            )
            created = True
        else:
            existing.profile_url = clean_url
            existing.track_status = "active"
            created = False

    return {
        "success": True,
        "created": created,
        "competitor_id": comp_id,
        "niche_id": niche_id,
        "username": handle,
        "profile_url": clean_url,
    }


@mcp.tool()
async def amas_add_product_from_link(
    video_url: str,
    niche_id: str = "",
    title: str = "",
    product_url: str = "",
    send_card: bool = True,
    database_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Save a TikTok video/product link directly into pending review and send an approval card to @amas_control_bot."""
    config = _get_config()
    err = _require_valid_niche(niche_id, config)
    if err is not None:
        return err

    scraper = TikTokScraper(mock_mode=False)
    try:
        clean_video = scraper._validate_video_url(video_url)
    except InvalidTikTokURLError as exc:
        return {"success": False, "needs_clarification": True, "missing": "video_url", "error": str(exc)}

    anchor = None
    meta_title = title.strip()
    try:
        meta = await scraper.download_video_metadata(clean_video)
        meta_title = meta_title or meta.title or meta.caption
        if meta.anchor_product_id:
            anchor = {
                "product_id": meta.anchor_product_id,
                "title": meta.anchor_product_title or meta_title,
                "product_url": f"https://shop.tiktok.com/view/product/{meta.anchor_product_id}",
            }
    except Exception:
        pass

    vid_slug = clean_video.rstrip("/").split("/")[-1].split("?")[0][:30] or "manual"
    prod_id = (anchor or {}).get("product_id") or f"link_{vid_slug}"
    final_title = (anchor or {}).get("title") or meta_title or f"Sản phẩm từ video {vid_slug}"
    final_prod_url = product_url.strip() or (anchor or {}).get("product_url") or clean_video

    db_url = _get_db_url(config, database_url)
    orchestrator = HermesOrchestrator(config=config)
    evaluator = orchestrator.fashion_scout if "thoi_trang" in niche_id else orchestrator.homelife_scout
    item_dict = {
        "product_id": prod_id,
        "niche_id": niche_id,
        "title": final_title,
        "price": 0.0,
        "commission_rate": 0.0,
        "product_url": final_prod_url,
        "source_video_url": clean_video,
        "source_type": "manual_link",
    }
    ev = evaluator.evaluate_product(item_dict)
    ev_dict = ev.to_dict()
    ev_dict["source_video_url"] = clean_video
    ev_dict["source_type"] = "manual_link"

    try:
        async with get_db(db_url) as session:
            if not await session.scalar(select(Niche).where(Niche.niche_id == niche_id)):
                niche_cfg = config.get_niche(niche_id)
                session.add(Niche(niche_id=niche_id, name=niche_cfg.name if niche_cfg else niche_id))
                await session.flush()

            existing = await session.scalar(select(Product).where(Product.product_id == prod_id))
            if existing is None:
                session.add(
                    Product(
                        product_id=prod_id,
                        niche_id=niche_id,
                        title=final_title,
                        price=0.0,
                        commission_rate=0.0,
                        product_url=final_prod_url,
                        evaluation_data=ev_dict,
                        status="pending",
                    )
                )

        if send_card:
            try:
                await orchestrator.telegram_bot.send_product_card(
                    product=item_dict, evaluation=ev, niche_id=niche_id
                )
            except Exception as exc:
                logger.warning("Failed to dispatch manual link card: %s", exc)
    finally:
        await _close_orchestrator_resources(orchestrator)

    return {
        "success": True,
        "product_id": prod_id,
        "niche_id": niche_id,
        "title": final_title,
        "source_video_url": clean_video,
        "product_url": final_prod_url,
        "status": "pending",
    }


@mcp.tool()
async def amas_list_products(
    status: str = "pending",
    niche_id: str = "",
    limit: int = 20,
    database_url: Optional[str] = None,
) -> Dict[str, Any]:
    """List affiliate products in PostgreSQL filtered by status and optional niche_id."""
    config = _get_config()
    db_url = _get_db_url(config, database_url)

    async with get_db(db_url) as session:
        stmt = select(Product).order_by(Product.created_at.desc()).limit(max(1, min(limit, 100)))
        if status and status != "all":
            stmt = stmt.where(Product.status == status)
        if niche_id:
            stmt = stmt.where(Product.niche_id == niche_id)
        rows = (await session.execute(stmt)).scalars().all()

        return {
            "count": len(rows),
            "products": [
                {
                    "product_id": p.product_id,
                    "niche_id": p.niche_id,
                    "title": p.title,
                    "price": p.price,
                    "commission_rate": p.commission_rate,
                    "sales_count": p.sales_count,
                    "status": p.status,
                    "evaluation_data": p.evaluation_data,
                }
                for p in rows
            ],
        }


@mcp.tool()
async def amas_review_product(
    product_id: str,
    decision: str = "approve",
    database_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Approve or reject a product via AMAS callback logic and enqueue approved VideoJobs."""
    normalized = (decision or "").strip().lower()
    if normalized not in ("approve", "reject"):
        return {"success": False, "error": "decision must be 'approve' or 'reject'"}

    config = _get_config()
    db_url = _get_db_url(config, database_url)
    admin_id = int(config.telegram.admin_id or 1)
    action = "approve_product" if normalized == "approve" else "reject_product"

    async with get_db(db_url) as session:
        return await execute_callback(
            callback_data=f"{action}:{product_id}",
            user_id=admin_id,
            admin_id=admin_id,
            session=session,
        )


@mcp.tool()
async def amas_get_learning_insights(
    days: int = 7,
    niche_id: str = "",
    database_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Aggregate recent video metrics, comment intents, and product outcomes for Hermes self-learning."""
    config = _get_config()
    db_url = _get_db_url(config, database_url)
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, days))

    async with get_db(db_url) as session:
        metrics = (
            await session.execute(
                select(Metric)
                .where(Metric.recorded_at >= cutoff)
                .order_by(Metric.estimated_revenue.desc())
                .limit(50)
            )
        ).scalars().all()

        comments = (
            await session.execute(
                select(VideoComment)
                .where(VideoComment.created_at >= cutoff)
                .order_by(VideoComment.created_at.desc())
                .limit(50)
            )
        ).scalars().all()

        prod_q = select(Product).order_by(Product.created_at.desc()).limit(30)
        if niche_id:
            prod_q = prod_q.where(Product.niche_id == niche_id)
        products = (await session.execute(prod_q)).scalars().all()

        intent_counts = Counter(c.intent or "unknown" for c in comments)

        return {
            "window_days": days,
            "totals": {
                "videos_tracked": len(metrics),
                "views": sum(m.views_count for m in metrics),
                "likes": sum(m.likes_count for m in metrics),
                "comments": sum(m.comments_count for m in metrics),
                "orders": sum(m.orders_count for m in metrics),
                "estimated_revenue": round(sum(m.estimated_revenue for m in metrics), 2),
            },
            "top_videos": [
                {
                    "video_id": m.video_id,
                    "channel_id": m.channel_id,
                    "views": m.views_count,
                    "orders": m.orders_count,
                    "revenue": m.estimated_revenue,
                }
                for m in metrics[:5]
            ],
            "comment_intent_distribution": dict(intent_counts),
            "sample_comments": [
                {
                    "intent": c.intent,
                    "comment_text": c.comment_text,
                    "reply_text": c.reply_text,
                }
                for c in comments[:10]
            ],
            "product_outcomes": [
                {
                    "product_id": p.product_id,
                    "niche_id": p.niche_id,
                    "title": p.title,
                    "status": p.status,
                    "score": (p.evaluation_data or {}).get("score"),
                    "hook_angle": (p.evaluation_data or {}).get("hook_angle"),
                }
                for p in products
            ],
        }


@mcp.tool()
async def amas_run_pipeline_step(
    step_name: str,
    payload: Optional[Dict[str, Any]] = None,
    mock_mode: bool = False,
) -> Dict[str, Any]:
    """Run a single HermesOrchestrator pipeline step (scout, evaluate, render, reply, publish)."""
    config = _get_config()
    orchestrator = HermesOrchestrator(config=config, mock_mode=mock_mode)
    result = await orchestrator.run_pipeline_step(step_name, payload or {})
    if "evaluation" in result and hasattr(result["evaluation"], "to_dict"):
        result["evaluation"] = result["evaluation"].to_dict()
    if "result" in result and hasattr(result["result"], "__dict__"):
        result["result"] = vars(result["result"])
    return result


def main() -> None:
    load_dotenv(REPO_ROOT / ".env")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
