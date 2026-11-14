"""E2E Integration Test Suite for Social Competitor Scraper & Dynamic Data Sync (Phase 8.4 / AMAS-27).

Validates:
1. Scenario 1: Multi-Social Scraper Batch Ingest (TikTok, Facebook Reels, Instagram) with UPSERT & project_id.
2. Scenario 2: Competitor Video Recreate Workflow (rewrite_script 3-part script + remix_video VideoJob).
3. Scenario 3: Multi-Project Workspace Isolation across competitor videos, channels, schedules, and groups.
4. Scenario 4: Channels & Dynamic Operations (Cookie import, Warmup, Captcha Unlock, Content Calendar schedule).
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
    VideoJob,
)
from src.database.session import get_async_engine, get_session_factory

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = get_async_engine(TEST_DB_URL, force_new=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with get_session_factory(TEST_DB_URL)() as session:
        # Seed default niches so channel and product foreign keys always resolve
        session.add(Niche(niche_id="thoi_trang_nu", name="Thời Trang Nữ"))
        session.add(Niche(niche_id="gia_dung", name="Đồ Gia Dụng"))
        session.add(Niche(niche_id="niche_default", name="Default Niche"))
        await session.commit()
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ==============================================================================
# Kịch bản 1 — Cào Batch Link Social Đối Thủ, Lưu CSDL & Cơ Chế UPSERT
# ==============================================================================

@pytest.mark.asyncio
async def test_scenario_1_social_scraper_batch_and_upsert(db_session: AsyncSession):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Khởi tạo Project Workspace
        proj_resp = await ac.post(
            "/api/projects/",
            json={
                "name": "Thời Trang Streetwear Y2K",
                "niche_brief": "Thời trang nữ Y2K cá tính",
                "target_audience": "Nữ 18-24 tuổi",
                "tone_of_voice": "GenZ hài hước",
                "trigger_keywords": ["áo thun", "quần túi hộp"],
                "negative_keywords": ["hàng lỗi"],
            },
        )
        assert proj_resp.status_code == 201
        proj_id = proj_resp.json()["project_id"]

        # 2. Cào batch đa nền tảng mạng xã hội: TikTok, Facebook Reels, Instagram
        sample_urls = [
            "https://www.tiktok.com/@trend.fashion.bkk/video/73111222333",
            "https://www.facebook.com/reel/9876543210123",
            "https://www.instagram.com/reel/C1234567890",
        ]

        scrape_resp = await ac.post(
            "/api/history/competitors/scrape",
            json={
                "project_id": proj_id,
                "urls": sample_urls,
                "scrape_interval_hours": 4,
                "force": True,
            },
        )
        assert scrape_resp.status_code == 200
        scrape_data = scrape_resp.json()
        assert scrape_data["success"] is True
        assert scrape_data["total_requested"] == 3
        assert len(scrape_data["results"]) == 3
        for res in scrape_data["results"]:
            assert res["stored"] is True
            assert "video_id" in res
            assert res["is_duplicate_updated"] is False

        # 3. Lấy danh sách video đối thủ đã lưu theo project_id
        list_resp = await ac.get(f"/api/history/competitor-videos?project_id={proj_id}")
        assert list_resp.status_code == 200
        videos = list_resp.json()
        assert len(videos) == 3
        platforms = {v["platform"] for v in videos}
        assert "tiktok" in platforms
        assert "facebook" in platforms
        assert "instagram" in platforms

        # 4. Kiểm tra cơ chế UPSERT (cào lại cùng URL cập nhật bản ghi cũ)
        scrape_again_resp = await ac.post(
            "/api/history/competitors/scrape",
            json={
                "project_id": proj_id,
                "urls": [sample_urls[0]],
                "scrape_interval_hours": 4,
                "force": True,
            },
        )
        assert scrape_again_resp.status_code == 200
        again_data = scrape_again_resp.json()
        assert again_data["results"][0]["is_duplicate_updated"] is True

        # Tổng số video vẫn là 3, không bị duplicate
        list_after = await ac.get(f"/api/history/competitor-videos?project_id={proj_id}")
        assert len(list_after.json()) == 3


# ==============================================================================
# Kịch bản 2 — Quy Trình Làm Lại Nội Dung (rewrite_script & remix_video)
# ==============================================================================

@pytest.mark.asyncio
async def test_scenario_2_recreate_competitor_content(db_session: AsyncSession):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Tạo project và cào video mẫu
        proj_resp = await ac.post(
            "/api/projects/",
            json={
                "name": "Review Đồ Gia Dụng Thông Minh",
                "niche_brief": "Kệ xoay, nồi chiên không dầu",
                "target_audience": "Nội trợ và người độc thân",
                "tone_of_voice": "Chuyên gia gia dụng thực tế",
            },
        )
        proj_id = proj_resp.json()["project_id"]

        await ac.post(
            "/api/history/competitors/scrape",
            json={
                "project_id": proj_id,
                "urls": ["https://www.tiktok.com/@homelife/video/739999999"],
            },
        )

        videos = (await ac.get(f"/api/history/competitor-videos?project_id={proj_id}")).json()
        target_video = videos[0]
        video_id = target_video["video_id"]

        # 2. Gọi Recreate mode 'rewrite_script' (Sinh kịch bản 3 khúc: Hook 3s, Body, CTA)
        script_resp = await ac.post(
            f"/api/history/competitor-videos/{video_id}/recreate",
            json={"mode": "rewrite_script", "project_id": proj_id},
        )
        assert script_resp.status_code == 200
        script_data = script_resp.json()
        assert script_data["mode"] == "rewrite_script"
        assert "hook_script" in script_data
        assert "body_script" in script_data
        assert "cta_script" in script_data
        assert len(script_data["hook_script"]) > 0
        assert len(script_data["body_script"]) > 0
        assert len(script_data["cta_script"]) > 0

        # 3. Gọi Recreate mode 'remix_video' (Tạo VideoJob chuyển sang Tab 1 Studio)
        remix_resp = await ac.post(
            f"/api/history/competitor-videos/{video_id}/recreate",
            json={"mode": "remix_video", "project_id": proj_id},
        )
        assert remix_resp.status_code == 200
        remix_data = remix_resp.json()
        assert remix_data["mode"] == "remix_video"
        assert "job_id" in remix_data
        assert "segments_data" in remix_data
        assert len(remix_data["segments_data"]) == 4
        assert remix_data["status"] == "created"


# ==============================================================================
# Kịch bản 3 — Cách Ly Dữ Liệu Tuyệt Đối Giữa Các Project Khác Nhau
# ==============================================================================

@pytest.mark.asyncio
async def test_scenario_3_multi_project_data_isolation(db_session: AsyncSession):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Tạo Project A (Thời Trang) và Project B (Công Nghệ)
        p_a = (await ac.post("/api/projects/", json={"name": "Project Thời Trang", "niche_brief": "Váy xinh"})).json()
        p_b = (await ac.post("/api/projects/", json={"name": "Project Công Nghệ", "niche_brief": "Củ sạc GaN"})).json()

        id_a = p_a["project_id"]
        id_b = p_b["project_id"]

        # 2. Cào video riêng cho từng Project
        await ac.post(
            "/api/history/competitors/scrape",
            json={"project_id": id_a, "urls": ["https://tiktok.com/@fashion/video/111"]},
        )
        await ac.post(
            "/api/history/competitors/scrape",
            json={"project_id": id_b, "urls": ["https://tiktok.com/@tech/video/222"]},
        )

        # 3. Tạo Channels riêng cho từng Project
        await ac.post(
            "/api/channels/",
            json={
                "project_id": id_a,
                "niche_id": "thoi_trang_nu",
                "platform": "tiktok",
                "browser_profile_id": "prof_a",
            },
        )
        await ac.post(
            "/api/channels/",
            json={
                "project_id": id_b,
                "niche_id": "gia_dung",
                "platform": "facebook",
                "browser_profile_id": "prof_b",
            },
        )

        # 4. Tạo Schedules riêng cho từng Project
        await ac.post(
            "/api/calendar/",
            json={
                "project_id": id_a,
                "platform": "tiktok",
                "target_type": "reel",
                "title": "Video Fashion Lookbook",
                "scheduled_at": "2026-11-20T12:00:00Z",
            },
        )
        await ac.post(
            "/api/calendar/",
            json={
                "project_id": id_b,
                "platform": "facebook",
                "target_type": "reel",
                "title": "Video Review Sạc Nhanh",
                "scheduled_at": "2026-11-20T19:00:00Z",
            },
        )

        # 5. Xác minh cách ly dữ liệu:
        # - Competitor videos:
        vids_a = (await ac.get(f"/api/history/competitor-videos?project_id={id_a}")).json()
        vids_b = (await ac.get(f"/api/history/competitor-videos?project_id={id_b}")).json()
        assert len(vids_a) == 1
        assert len(vids_b) == 1
        assert vids_a[0]["video_url"] != vids_b[0]["video_url"]

        # - Channels:
        chans_a = (await ac.get(f"/api/channels/?project_id={id_a}")).json()
        chans_b = (await ac.get(f"/api/channels/?project_id={id_b}")).json()
        assert len(chans_a) == 1
        assert len(chans_b) == 1
        assert chans_a[0]["platform"] == "tiktok"
        assert chans_b[0]["platform"] == "facebook"

        # - Calendar schedules:
        cal_a = (await ac.get(f"/api/calendar/?project_id={id_a}")).json()
        cal_b = (await ac.get(f"/api/calendar/?project_id={id_b}")).json()
        assert len(cal_a["schedules"]) == 1
        assert len(cal_b["schedules"]) == 1
        assert cal_a["schedules"][0]["title"] == "Video Fashion Lookbook"
        assert cal_b["schedules"][0]["title"] == "Video Review Sạc Nhanh"


# ==============================================================================
# Kịch bản 4 — Đồng Bộ Thao Tác Kênh & Lịch Đăng (Cookie, Warmup, Captcha)
# ==============================================================================

@pytest.mark.asyncio
async def test_scenario_4_channel_lifecycle_and_calendar_sync(db_session: AsyncSession):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Tạo kênh ở trạng thái warming
        chan_resp = await ac.post(
            "/api/channels/",
            json={
                "niche_id": "thoi_trang_nu",
                "platform": "tiktok",
                "account_type": "profile",
                "browser_profile_id": "prof_lifecycle_test",
            },
        )
        assert chan_resp.status_code == 201
        chan_id = chan_resp.json()["channel_id"]

        # 2. Nạp cookie để kích hoạt kênh lên ready_to_post
        cookie_resp = await ac.post(
            f"/api/channels/{chan_id}/import-cookies",
            json={"cookies": "sessionid=test_cookie_value; domain=.tiktok.com; path=/"},
        )
        assert cookie_resp.status_code == 200
        assert cookie_resp.json()["lifecycle_status"] == "ready_to_post"

        # 3. Kích hoạt phiên nuôi Warmup
        warmup_resp = await ac.post(
            f"/api/channels/{chan_id}/warmup",
            json={"duration_minutes": 5},
        )
        assert warmup_resp.status_code == 200
        assert warmup_resp.json()["new_lifecycle_status"] == "ready_to_post"

        # 4. Mở khóa Captcha
        unlock_resp = await ac.post(f"/api/channels/{chan_id}/unlock")
        assert unlock_resp.status_code == 200
        assert unlock_resp.json()["lifecycle_status"] == "ready_to_post"

        # 5. Lên lịch xuất bản và cập nhật trạng thái
        sched_resp = await ac.post(
            "/api/calendar/",
            json={
                "channel_id": chan_id,
                "platform": "tiktok",
                "target_type": "reel",
                "title": "Video Affiliate Siêu Bão Đơn",
                "scheduled_at": "2026-11-25T11:30:00Z",
            },
        )
        assert sched_resp.status_code == 201
        sched_id = sched_resp.json()["schedule_id"]

        patch_resp = await ac.patch(
            f"/api/calendar/{sched_id}",
            json={"status": "published"},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["status"] == "published"
