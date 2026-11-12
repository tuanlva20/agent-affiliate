"""Tests for AMAS MCP Server (tool logic + real stdio MCP ClientSession handshake)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from src.database.models import Base, Channel, Metric, Niche, Product, VideoComment
from src.database.session import get_async_engine, get_session_factory
from src.mcp.amas_mcp_server import (
    amas_add_competitor,
    amas_add_product_from_link,
    amas_get_learning_insights,
    amas_get_status,
    amas_list_products,
    amas_review_product,
    amas_run_pipeline_step,
    amas_scout_products,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


async def _seed_sample_db(db_url: str) -> None:
    engine = get_async_engine(db_url, force_new=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = get_session_factory(db_url)
    async with factory() as session:
        session.add(Niche(niche_id="thoi_trang_nu", name="Thời trang nữ"))
        session.add(
            Channel(
                channel_id="chan_fashion_01",
                niche_id="thoi_trang_nu",
                browser_profile_id="prof_01",
                lifecycle_status="ready_to_post",
            )
        )
        session.add(
            Product(
                product_id="prod_mcp_01",
                niche_id="thoi_trang_nu",
                title="Váy midi chiết eo che bụng",
                price=199000.0,
                commission_rate=0.15,
                product_url="https://vt.tiktok.com/ZSmcp01/",
                sales_count=450,
                rating=4.8,
                evaluation_data={"score": 8.6, "hook_angle": "che bụng dưới cực đỉnh"},
                status="pending",
            )
        )
        session.add(
            Metric(
                metric_id="met_01",
                channel_id="chan_fashion_01",
                video_id="vid_01",
                views_count=12500,
                likes_count=840,
                comments_count=35,
                orders_count=18,
                estimated_revenue=3582000.0,
            )
        )
        session.add(
            VideoComment(
                comment_id="cmt_01",
                channel_id="chan_fashion_01",
                video_id="vid_01",
                author_id="u1",
                comment_text="Váy này 60kg mặc vừa không shop?",
                intent="ask_material_usage",
                reply_text="Dạ 60kg mặc size L thoải mái luôn nha bà ơi!",
                reply_status="replied",
            )
        )
        await session.commit()


@pytest.mark.asyncio
async def test_amas_mcp_tools_end_to_end(tmp_path: Path):
    db_path = tmp_path / "mcp_test.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"
    await _seed_sample_db(db_url)

    status = await amas_get_status(niche_id="thoi_trang_nu", database_url=db_url)
    assert status["channels_total"] == 1
    assert status["products_by_status"]["pending"] == 1

    listed = await amas_list_products(status="pending", database_url=db_url)
    assert listed["count"] == 1
    assert listed["products"][0]["product_id"] == "prod_mcp_01"

    review = await amas_review_product(
        product_id="prod_mcp_01", decision="approve", database_url=db_url
    )
    assert review["success"] is True
    assert review["job"]["product_id"] == "prod_mcp_01"

    scouted = await amas_scout_products(
        niche_id="thoi_trang_nu", limit=2, save_pending=True, send_cards=False, mock_mode=True, database_url=db_url
    )
    assert scouted["count"] >= 1

    missing_niche = await amas_add_competitor(
        profile_url="https://www.tiktok.com/@koc_thoitrang_test",
        database_url=db_url,
    )
    assert missing_niche["success"] is False
    assert missing_niche["needs_clarification"] is True
    assert missing_niche["missing"] == "niche_id"

    comp = await amas_add_competitor(
        profile_url="https://www.tiktok.com/@koc_thoitrang_test",
        niche_id="thoi_trang_nu",
        database_url=db_url,
    )
    assert comp["success"] is True
    assert comp["username"] == "koc_thoitrang_test"

    manual = await amas_add_product_from_link(
        video_url="https://www.tiktok.com/@koc_thoitrang_test/video/739000111222",
        niche_id="thoi_trang_nu",
        title="Váy xòe hack dáng test",
        send_card=False,
        database_url=db_url,
    )
    assert manual["success"] is True
    assert manual["source_video_url"] == "https://www.tiktok.com/@koc_thoitrang_test/video/739000111222"

    insights = await amas_get_learning_insights(days=7, database_url=db_url)
    assert insights["totals"]["views"] == 12500
    assert insights["totals"]["orders"] == 18
    assert insights["comment_intent_distribution"]["ask_material_usage"] == 1

    step_res = await amas_run_pipeline_step(
        "reply", {"comment": "Giá bao nhiêu vậy shop?"}, mock_mode=True
    )
    assert step_res["status"] == "success"
    assert step_res["reply"]


@pytest.mark.asyncio
async def test_amas_mcp_stdio_protocol_handshake(tmp_path: Path):
    db_path = tmp_path / "mcp_stdio.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"
    await _seed_sample_db(db_url)

    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(REPO_ROOT / "src" / "mcp" / "amas_mcp_server.py")],
        env={"DATABASE_URL": db_url, "PATH": ""},
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_res = await session.list_tools()
            tool_names = {t.name for t in tools_res.tools}
            assert {
                "amas_get_status",
                "amas_scout_products",
                "amas_add_competitor",
                "amas_add_product_from_link",
                "amas_list_products",
                "amas_review_product",
                "amas_get_learning_insights",
                "amas_run_pipeline_step",
            }.issubset(tool_names)

            call_res = await session.call_tool(
                "amas_get_status", {"niche_id": "all", "database_url": db_url}
            )
            is_err = getattr(call_res, "is_error", getattr(call_res, "isError", False))
            assert not is_err
            payload = json.loads(call_res.content[0].text)
            assert payload["channels_total"] == 1
