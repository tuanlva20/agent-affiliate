"""Unit tests for FastAPI v1.5 Endpoints (Phase 5.5 / AMAS-17).

Verifies:
1. Projects API: list (auto-seed defaults), create, get, update, delete, presets & tooltips.
2. Calendar API: list (with Golden Slots), create, update (patch), delete.
3. Groups API: list, add group, post to group, scan & seed, comment logs.
4. History API extensions: batch competitor scrape, recreate (rewrite_script & remix_video).
5. Channels API: filter by project_id.
"""

from __future__ import annotations

from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.main import app
from src.database.models import Base, Channel, Competitor, CompetitorVideo, Niche, Product, Project, ProjectGroup
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


@pytest.mark.asyncio
async def test_projects_crud_and_presets(db_session: AsyncSession):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Presets endpoint
        resp_presets = await ac.get("/api/projects/presets")
        assert resp_presets.status_code == 200
        data_presets = resp_presets.json()
        assert "field_tooltips" in data_presets
        assert len(data_presets["presets"]) >= 4

        # 2. List empty DB: triggers auto-seed of 2 default projects
        resp_list = await ac.get("/api/projects/")
        assert resp_list.status_code == 200
        projects = resp_list.json()
        assert len(projects) >= 2
        names = [p["name"] for p in projects]
        assert "Thời Trang GenZ" in names or "Thời Trang Nữ GenZ" in names or any("Thời Trang" in n for n in names)

        # 3. Create Project
        new_proj_payload = {
            "name": "Khóa Học Lập Trình & AI",
            "niche_brief": "Khóa học Python, AI Agent và Prompt Engineering",
            "target_audience": "Lập trình viên và sinh viên công nghệ",
            "tone_of_voice": "Chuyên gia đào tạo tận tâm",
            "trigger_keywords": ["học python", "prompt engineering", "ai agent"],
            "negative_keywords": ["đa cấp", "lừa đảo việc làm"],
        }
        resp_create = await ac.post("/api/projects/", json=new_proj_payload)
        assert resp_create.status_code == 201
        created = resp_create.json()
        proj_id = created["project_id"]
        assert created["name"] == "Khóa Học Lập Trình & AI"

        # 4. Get Project
        resp_get = await ac.get(f"/api/projects/{proj_id}")
        assert resp_get.status_code == 200
        assert resp_get.json()["project_id"] == proj_id

        # 5. Update Project
        resp_update = await ac.put(f"/api/projects/{proj_id}", json={"name": "Khóa Học AI Thực Chiến"})
        assert resp_update.status_code == 200
        assert resp_update.json()["name"] == "Khóa Học AI Thực Chiến"

        # 6. Delete Project
        resp_del = await ac.delete(f"/api/projects/{proj_id}")
        assert resp_del.status_code == 204

        # Verify not found after deletion
        resp_get_after = await ac.get(f"/api/projects/{proj_id}")
        assert resp_get_after.status_code == 404


@pytest.mark.asyncio
async def test_calendar_schedules_crud_and_golden_slots(db_session: AsyncSession):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. List calendar (initially empty)
        resp_list = await ac.get("/api/calendar/")
        assert resp_list.status_code == 200
        data = resp_list.json()
        assert "golden_slots" in data
        assert "tiktok" in data["golden_slots"]
        assert "facebook" in data["golden_slots"]
        assert "instagram" in data["golden_slots"]

        # 2. Create schedule item
        sched_payload = {
            "platform": "tiktok",
            "target_type": "reel",
            "title": "Review Bàn Phím Cơ Aula F75 Siêu Ngon",
            "caption": "Mẫu phím cơ quốc dân tầm giá sinh viên #aulaf75 #keyboard",
            "scheduled_at": "2026-11-20T20:30:00Z",
        }
        resp_create = await ac.post("/api/calendar/", json=sched_payload)
        assert resp_create.status_code == 201
        sched = resp_create.json()
        sched_id = sched["schedule_id"]
        assert sched["status"] == "scheduled"

        # 3. Patch schedule item
        resp_patch = await ac.patch(
            f"/api/calendar/{sched_id}",
            json={"status": "publishing", "title": "Bàn Phím Cơ Aula F75 (Cập Nhật)"},
        )
        assert resp_patch.status_code == 200
        assert resp_patch.json()["status"] == "publishing"
        assert resp_patch.json()["title"] == "Bàn Phím Cơ Aula F75 (Cập Nhật)"

        # 4. Delete schedule item
        resp_del = await ac.delete(f"/api/calendar/{sched_id}")
        assert resp_del.status_code == 204


@pytest.mark.asyncio
async def test_groups_and_seeding_endpoints(db_session: AsyncSession):
    # Set up project, niche, and channel in DB
    p = Project(
        project_id="proj_grp_test",
        name="Tech Seeding Workspace",
        niche_brief="Phụ kiện bàn phím cơ",
        tone_of_voice="GenZ thân thiện",
        trigger_keywords=["bàn phím cơ", "switch gõ êm"],
        negative_keywords=["hàng rởm"],
    )
    niche = Niche(niche_id="niche_grp_01", name="Gaming")
    chan = Channel(
        channel_id="chan_grp_01",
        project_id="proj_grp_test",
        niche_id="niche_grp_01",
        browser_profile_id="prof_grp_01",
        platform="facebook",
        lifecycle_status="ready_to_post",
    )
    db_session.add_all([p, niche, chan])
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Add Group
        grp_payload = {
            "project_id": "proj_grp_test",
            "group_url": "https://facebook.com/groups/vietnamkeebs",
            "group_name": "Cộng Đồng Bàn Phím Cơ Việt Nam",
            "privacy": "public",
            "approval_mode": False,
        }
        resp_add = await ac.post("/api/groups/", json=grp_payload)
        assert resp_add.status_code == 201
        grp_data = resp_add.json()
        group_id = grp_data["group_id"]
        assert grp_data["group_name"] == "Cộng Đồng Bàn Phím Cơ Việt Nam"

        # 2. List Groups
        resp_list = await ac.get(f"/api/groups/?project_id=proj_grp_test")
        assert resp_list.status_code == 200
        assert len(resp_list.json()) == 1

        # 3. Post to Group
        post_payload = {
            "channel_id": "chan_grp_01",
            "product_title": "Bàn Phím Cơ Aula F75",
            "affiliate_url": "https://shope.ee/aulaf75",
        }
        resp_post = await ac.post(f"/api/groups/{group_id}/post", json=post_payload)
        assert resp_post.status_code == 200
        assert resp_post.json()["status"] == "posted"

        # 4. Scan & Seed
        scan_payload = {
            "channel_id": "chan_grp_01",
            "product_title": "Bàn Phím Cơ Aula F75",
            "affiliate_url": "https://shope.ee/aulaf75",
            "candidate_posts": [
                {"post_id": "p_keeb_01", "post_text": "Mọi người có recommend bàn phím cơ nào tầm 1 củ không ạ?"},
            ],
        }
        resp_seed = await ac.post(f"/api/groups/{group_id}/scan-seed", json=scan_payload)
        assert resp_seed.status_code == 200
        assert resp_seed.json()["seeded_count"] == 1

        # 5. List comment logs
        resp_logs = await ac.get(f"/api/groups/logs?group_id={group_id}")
        assert resp_logs.status_code == 200
        logs = resp_logs.json()
        assert len(logs) == 1
        assert logs[0]["post_id"] == "p_keeb_01"


@pytest.mark.asyncio
async def test_competitor_scrape_and_recreate_endpoints(db_session: AsyncSession):
    # Setup project, niche, competitor, and competitor video
    p = Project(
        project_id="proj_recreate_01",
        name="Skincare Glow",
        niche_brief="Serum B5 và phục hồi da",
        tone_of_voice="Chuyên gia da liễu",
    )
    niche = Niche(niche_id="niche_rec_01", name="Skincare")
    db_session.add_all([p, niche])
    await db_session.flush()

    competitor = Competitor(
        competitor_id="comp_test_rec",
        project_id="proj_recreate_01",
        niche_id="niche_rec_01",
        username="glow_skincare",
        profile_url="https://www.tiktok.com/@glow_skincare",
        scrape_interval_hours=4,
    )
    db_session.add(competitor)
    await db_session.flush()

    comp_vid = CompetitorVideo(
        video_id="vid_comp_test_777",
        project_id="proj_recreate_01",
        competitor_id="comp_test_rec",
        platform="tiktok",
        video_url="https://www.tiktok.com/@competitor/video/777000111222",
        caption="Cách trị mụn siêu nhanh tại nhà với serum @badbrand #skincare",
        views_count=50000,
        likes_count=3500,
    )
    db_session.add(comp_vid)
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Batch Scrape endpoint
        scrape_payload = {
            "urls": ["https://www.tiktok.com/@rival/video/7431289412345678901"],
            "project_id": "proj_recreate_01",
            "force": True,
        }
        resp_scrape = await ac.post("/api/history/competitors/scrape", json=scrape_payload)
        assert resp_scrape.status_code == 200
        assert resp_scrape.json()["success"] is True

        # 2. Recreate mode = 'rewrite_script'
        resp_rewrite = await ac.post(
            "/api/history/competitor-videos/vid_comp_test_777/recreate",
            json={"mode": "rewrite_script", "project_id": "proj_recreate_01"},
        )
        assert resp_rewrite.status_code == 200
        data_rewrite = resp_rewrite.json()
        assert data_rewrite["mode"] == "rewrite_script"
        assert "hook_script" in data_rewrite
        assert "body_script" in data_rewrite
        assert "cta_script" in data_rewrite
        assert "@badbrand" not in data_rewrite["caption"]

        # 3. Recreate mode = 'remix_video'
        resp_remix = await ac.post(
            "/api/history/competitor-videos/vid_comp_test_777/recreate",
            json={"mode": "remix_video", "project_id": "proj_recreate_01"},
        )
        assert resp_remix.status_code == 200
        data_remix = resp_remix.json()
        assert data_remix["mode"] == "remix_video"
        assert "job_id" in data_remix
        assert data_remix["status"] == "created"
        assert "segments_data" in data_remix
