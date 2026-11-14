"""E2E Integration Test Suite for AMAS v1.5.0 Workspace Expansion (Phase 6.3 / AMAS-20).

Validates 5 Mandatory Scenarios:
1. Scenario 1: Multi-Project Isolation (Workspace Isolation between Fashion and Tech).
2. Scenario 2: Deduplication UPSERT on Forced Scrape across multi-social links.
3. Scenario 3: Quick Cookie Import & Channel Activation to ready_to_post.
4. Scenario 4: Auto Group Post & Dynamic Context Comment Seeding with Deduplication.
5. Scenario 5: Recreate Content (rewrite_script & remix_video) & Content Calendar.
"""

from __future__ import annotations

from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.main import app
from src.database.models import (
    Base,
    Channel,
    Competitor,
    CompetitorVideo,
    GroupCommentLog,
    Niche,
    Product,
    Project,
    ProjectGroup,
    PublishSchedule,
)
from src.database.session import get_async_engine, get_session_factory

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = get_async_engine(TEST_DB_URL, force_new=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with get_session_factory(TEST_DB_URL)() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ==============================================================================
# Kịch bản 1 — Cô lập dữ liệu Multi-Project (Workspace Isolation)
# ==============================================================================

@pytest.mark.asyncio
async def test_scenario_1_multi_project_isolation(db_session: AsyncSession):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Tạo 2 Projects thuộc 2 ngành khác nhau
        resp_p1 = await ac.post(
            "/api/projects/",
            json={
                "name": "Thời Trang GenZ",
                "niche_brief": "Thời trang streetwear Y2K",
                "target_audience": "Nữ giới 18-24 tuổi",
                "tone_of_voice": "GenZ hài hước bắt trend",
                "trigger_keywords": ["váy xinh", "outfit"],
                "negative_keywords": ["hàng lỗi"],
            },
        )
        assert resp_p1.status_code == 201
        p1 = resp_p1.json()
        proj_fashion_id = p1["project_id"]

        resp_p2 = await ac.post(
            "/api/projects/",
            json={
                "name": "Phụ Kiện Công Nghệ",
                "niche_brief": "Cáp sạc, tai nghe bluetooth, bàn phím cơ",
                "target_audience": "Dân IT và game thủ",
                "tone_of_voice": "KOC công nghệ nhiệt huyết",
                "trigger_keywords": ["tai nghe", "sạc nhanh 65W"],
                "negative_keywords": ["hàng fake"],
            },
        )
        assert resp_p2.status_code == 201
        p2 = resp_p2.json()
        proj_tech_id = p2["project_id"]

        # 2. Thêm Groups vào từng Project
        g1_resp = await ac.post(
            "/api/groups/",
            json={
                "project_id": proj_fashion_id,
                "group_name": "Góc Review Váy Xinh Hà Nội",
                "group_url": "https://facebook.com/groups/vayxinhhanoi",
                "approval_mode": False,
            },
        )
        assert g1_resp.status_code == 201

        g2_resp = await ac.post(
            "/api/groups/",
            json={
                "project_id": proj_tech_id,
                "group_name": "Cộng Đồng Setup & Gear VN",
                "group_url": "https://facebook.com/groups/setupgearvn",
                "approval_mode": False,
            },
        )
        assert g2_resp.status_code == 201

        # 3. Thêm Calendar Schedules vào từng Project
        sch1 = await ac.post(
            "/api/calendar/",
            json={
                "project_id": proj_fashion_id,
                "platform": "tiktok",
                "target_type": "reel",
                "title": "OOTD Đi Chơi Phố Đi Bộ",
                "scheduled_at": "2026-11-20T19:30:00Z",
            },
        )
        assert sch1.status_code == 201

        sch2 = await ac.post(
            "/api/calendar/",
            json={
                "project_id": proj_tech_id,
                "platform": "tiktok",
                "target_type": "reel",
                "title": "Review Củ Sạc Nhanh 65W GaN",
                "scheduled_at": "2026-11-20T20:30:00Z",
            },
        )
        assert sch2.status_code == 201

        # 4. Kiểm tra cô lập dữ liệu (Workspace Isolation)
        # Groups filter
        list_g_fashion = await ac.get(f"/api/groups/?project_id={proj_fashion_id}")
        assert list_g_fashion.status_code == 200
        g_fashion_items = list_g_fashion.json()
        assert len(g_fashion_items) == 1
        assert g_fashion_items[0]["group_name"] == "Góc Review Váy Xinh Hà Nội"

        list_g_tech = await ac.get(f"/api/groups/?project_id={proj_tech_id}")
        assert list_g_tech.status_code == 200
        g_tech_items = list_g_tech.json()
        assert len(g_tech_items) == 1
        assert g_tech_items[0]["group_name"] == "Cộng Đồng Setup & Gear VN"

        # Calendar filter
        cal_fashion = await ac.get(f"/api/calendar/?project_id={proj_fashion_id}")
        assert cal_fashion.status_code == 200
        cal_fashion_items = cal_fashion.json()["schedules"]
        assert len(cal_fashion_items) == 1
        assert cal_fashion_items[0]["title"] == "OOTD Đi Chơi Phố Đi Bộ"

        cal_tech = await ac.get(f"/api/calendar/?project_id={proj_tech_id}")
        assert cal_tech.status_code == 200
        cal_tech_items = cal_tech.json()["schedules"]
        assert len(cal_tech_items) == 1
        assert cal_tech_items[0]["title"] == "Review Củ Sạc Nhanh 65W GaN"


# ==============================================================================
# Kịch bản 2 — Chống trùng lặp dữ liệu (Deduplication UPSERT) khi Cào Cưỡng Bức
# ==============================================================================

@pytest.mark.asyncio
async def test_scenario_2_deduplication_upsert_on_scrape(db_session: AsyncSession):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        target_url = "https://www.tiktok.com/@trendsetter/video/738899112233"
        payload = {
            "urls": [target_url],
            "force": True,
            "scrape_interval_hours": 4,
        }

        # Lần 1: Cào lần đầu
        resp1 = await ac.post("/api/history/competitors/scrape", json=payload)
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert data1["success"] is True
        assert len(data1["results"]) == 1
        assert data1["results"][0]["stored"] is True
        video_id = data1["results"][0]["video_id"]
        assert data1["results"][0]["is_duplicate_updated"] is False

        # Lần 2: Cào lại ngay lập tức với force=True
        resp2 = await ac.post("/api/history/competitors/scrape", json=payload)
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["success"] is True
        assert len(data2["results"]) == 1
        assert data2["results"][0]["video_id"] == video_id
        # Xác minh UPSERT: được cập nhật thay vì tạo dòng mới
        assert data2["results"][0]["is_duplicate_updated"] is True

        # Xác minh trong DB chỉ có đúng 1 bản ghi duy nhất cho video_id đó
        stmt = select(CompetitorVideo).where(CompetitorVideo.video_id == video_id)
        records = (await db_session.execute(stmt)).scalars().all()
        assert len(records) == 1


# ==============================================================================
# Kịch bản 3 — Nạp nhanh Cookie/Token & Kích hoạt Kênh
# ==============================================================================

@pytest.mark.asyncio
async def test_scenario_3_quick_cookie_import_and_activation(db_session: AsyncSession):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        niche = Niche(niche_id="niche_e2e_test", name="E2E Test Niche")
        db_session.add(niche)
        await db_session.flush()

        chan = Channel(
            channel_id="chan_e2e_warming_01",
            niche_id=niche.niche_id,
            platform="facebook",
            browser_profile_id="prof_e2e_01",
            lifecycle_status="warming",
            platform_metadata={},
        )
        db_session.add(chan)
        await db_session.commit()

        # Nạp Cookie hợp lệ
        cookie_payload = {
            "cookies": "c_user=100098765432; xs=30%3Amock%3A2; fr=0abc123;",
            "format": "auto",
        }
        resp = await ac.post("/api/channels/chan_e2e_warming_01/import-cookies", json=cookie_payload)
        assert resp.status_code == 200
        result = resp.json()
        assert result["channel_id"] == "chan_e2e_warming_01"
        assert result["lifecycle_status"] == "ready_to_post"
        assert result["authenticated"] is True
        assert result["cookie_count"] == 3

        # Kiểm tra lại trực tiếp trong DB sau khi reload
        await db_session.refresh(chan)
        assert chan.lifecycle_status == "ready_to_post"


# ==============================================================================
# Kịch bản 4 — Auto Đăng Bài Group & Tự Động Seeding Comment theo Ngữ Cảnh Động
# ==============================================================================

@pytest.mark.asyncio
async def test_scenario_4_group_seeding_and_deduplication(db_session: AsyncSession):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Tạo Project công nghệ
        resp_p = await ac.post(
            "/api/projects/",
            json={
                "name": "Tech Gadgets Workspace",
                "niche_brief": "Củ sạc GaN và tai nghe bluetooth",
                "target_audience": "Dân công nghệ và sinh viên IT",
                "tone_of_voice": "KOC vui tính, nhiệt tình",
                "trigger_keywords": ["tai nghe", "sạc nhanh"],
                "negative_keywords": ["hàng fake", "nổ pin"],
            },
        )
        assert resp_p.status_code == 201
        proj_id = resp_p.json()["project_id"]

        # Tạo Niche và Channel cho bot
        niche = Niche(niche_id="niche_tech_e2e", name="Tech")
        db_session.add(niche)
        await db_session.flush()

        bot_chan = Channel(
            channel_id="chan_bot_tech_01",
            niche_id=niche.niche_id,
            platform="facebook",
            browser_profile_id="prof_bot_01",
            lifecycle_status="ready_to_post",
            platform_metadata={},
        )
        db_session.add(bot_chan)
        await db_session.commit()

        # Thêm Group vào Project
        resp_g = await ac.post(
            "/api/groups/",
            json={
                "project_id": proj_id,
                "group_name": "Hội Bàn Phím Cơ & Gear Sạc",
                "group_url": "https://facebook.com/groups/gearsacvn",
                "approval_mode": False,
            },
        )
        assert resp_g.status_code == 201
        group_id = resp_g.json()["group_id"]

        # Chuẩn bị danh sách bài viết trong Group
        sample_posts = [
            {"post_id": "fb_post_001", "post_text": "Cần tìm tai nghe chống ồn học bài tầm 500k-1tr"},
            {"post_id": "fb_post_002", "post_text": "Hôm nay trời đẹp quá, mọi người đi cafe đâu?"},
        ]

        # Lần 1: Scan & Seed
        resp_scan1 = await ac.post(
            f"/api/groups/{group_id}/scan-seed",
            json={
                "channel_id": "chan_bot_tech_01",
                "product_title": "Tai Nghe Chống Ồn ANC 2026",
                "affiliate_url": "https://affiliate.amas.vn/tainghe",
                "candidate_posts": sample_posts,
            },
        )
        assert resp_scan1.status_code == 200
        scan1_data = resp_scan1.json()

        # Bài 1 khớp từ khóa 'tai nghe' -> seeded
        assert scan1_data["seeded_count"] == 1
        assert scan1_data["comments"][0]["matched_keyword"] == "tai nghe"

        # Lần 2: Scan & Seed lại trên cùng danh sách bài viết -> Deduplication chống comment trùng
        resp_scan2 = await ac.post(
            f"/api/groups/{group_id}/scan-seed",
            json={
                "channel_id": "chan_bot_tech_01",
                "product_title": "Tai Nghe Chống Ồn ANC 2026",
                "affiliate_url": "https://affiliate.amas.vn/tainghe",
                "candidate_posts": sample_posts,
            },
        )
        assert resp_scan2.status_code == 200
        scan2_data = resp_scan2.json()
        assert scan2_data["seeded_count"] == 0  # Bài 1 đã comment, không comment lại


# ==============================================================================
# Kịch bản 5 — Làm Lại Nội Dung & Lịch Đăng Bài (Content Calendar)
# ==============================================================================

@pytest.mark.asyncio
async def test_scenario_5_recreate_content_and_calendar(db_session: AsyncSession):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        niche = Niche(niche_id="niche_recreate_01", name="Fashion")
        db_session.add(niche)
        await db_session.flush()

        comp = Competitor(
            competitor_id="comp_e2e_recreate",
            niche_id=niche.niche_id,
            username="rival_creator",
            profile_url="https://tiktok.com/@rival_creator",
            scrape_interval_hours=4,
        )
        db_session.add(comp)
        await db_session.flush()

        cv = CompetitorVideo(
            video_id="cv_e2e_recreate_01",
            competitor_id=comp.competitor_id,
            platform="tiktok",
            video_url="https://tiktok.com/@rival_creator/video/998877",
            caption="Visual Hook 3s cực cuốn của mẫu đầm hoa nhí",
            views_count=150000,
        )
        db_session.add(cv)
        await db_session.commit()

        # 1. Gọi /recreate mode 'rewrite_script'
        resp_script = await ac.post(
            "/api/history/competitor-videos/cv_e2e_recreate_01/recreate",
            json={"mode": "rewrite_script"},
        )
        assert resp_script.status_code == 200
        data_script = resp_script.json()
        assert data_script["mode"] == "rewrite_script"
        assert "hook_script" in data_script
        assert "body_script" in data_script
        assert "cta_script" in data_script

        # 2. Gọi /recreate mode 'remix_video'
        resp_remix = await ac.post(
            "/api/history/competitor-videos/cv_e2e_recreate_01/recreate",
            json={"mode": "remix_video"},
        )
        assert resp_remix.status_code == 200
        data_remix = resp_remix.json()
        assert data_remix["mode"] == "remix_video"
        assert data_remix["status"] == "created"
        assert "job_id" in data_remix

        # 3. Tạo lịch đăng trên /api/calendar
        resp_cal_create = await ac.post(
            "/api/calendar/",
            json={
                "platform": "tiktok",
                "target_type": "reel",
                "title": "Đầm Hoa Nhí Remix 2026",
                "caption": data_script["caption"],
                "scheduled_at": "2026-11-22T20:00:00Z",
            },
        )
        assert resp_cal_create.status_code == 201
        cal_item = resp_cal_create.json()
        sched_id = cal_item["schedule_id"]
        assert cal_item["status"] == "scheduled"

        # 4. Đổi giờ đăng qua PATCH /api/calendar/{schedule_id}
        resp_patch = await ac.patch(
            f"/api/calendar/{sched_id}",
            json={"scheduled_at": "2026-11-23T20:30:00Z", "status": "publishing"},
        )
        assert resp_patch.status_code == 200
        updated_item = resp_patch.json()
        assert updated_item["status"] == "publishing"
        assert "2026-11-23" in updated_item["scheduled_at"]
