"""Unit tests for OpenSEO Engine & API Endpoints (Phase 7.1 / AMAS-21).

Verifies 100% of the 5 Navigation Groups and 17 Screens:
1. Overview: Dashboard (01)
2. Research: Keyword Research (02), Domain Overview (03), Backlinks (04)
3. AI Visibility: Prompt Research (05), Prompt Explorer (06), Prompt Tracking (07)
4. My Site: GSC Insights (08), Rank Tracking (09), Local SEO Geo-Grid (10), Saved Keywords (11), Site Audit (12)
5. AI Tools: Reports (13), Context (14), Agent Setup MCP (15)
6. Global / Drawer: SAM AI Assistant (16), Project Settings & Integrations (17)
"""

from __future__ import annotations

from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.main import app
from src.database.models import Base, Project
from src.database.session import get_async_engine, get_session_factory
from src.services.openseo_engine import OpenSEOEngine

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


@pytest.fixture
def openseo_engine() -> OpenSEOEngine:
    return OpenSEOEngine()


@pytest.mark.asyncio
async def test_openseo_all_17_screens_api(db_session: AsyncSession):
    """E2E verification across all 17 OpenSEO endpoints through FastAPI."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create test project
        p_res = await ac.post(
            "/api/projects/",
            json={
                "name": "Thời Trang GenZ Online",
                "niche_brief": "Thời trang GenZ Y2K",
                "target_audience": "Nữ giới 18-24 tuổi",
                "tone_of_voice": "Trẻ trung, bắt trend",
                "trigger_keywords": ["váy xinh", "outfit"],
                "negative_keywords": ["lừa đảo"],
            },
        )
        assert p_res.status_code == 201
        project_id = p_res.json()["project_id"]

        # =====================================================================
        # 1. Overview
        # =====================================================================
        # Screen 01: Dashboard
        resp_01 = await ac.get(f"/api/openseo/projects/{project_id}/dashboard")
        assert resp_01.status_code == 200
        d01 = resp_01.json()
        assert "kpis" in d01
        assert "gsc_quick_chart" in d01
        assert "audit_summary" in d01
        assert "recent_keywords" in d01
        assert "ai_visibility_snapshot" in d01

        # =====================================================================
        # 2. Research
        # =====================================================================
        # Screen 02: Keyword Research
        resp_02 = await ac.get("/api/openseo/keywords/research?query=váy+lụa&location=VN&language=vi")
        assert resp_02.status_code == 200
        d02 = resp_02.json()
        assert d02["total_ideas"] >= 1
        assert d02["keyword_ideas"][0]["intent"] == "Commercial"
        assert len(d02["keyword_ideas"][0]["trend_12m"]) == 12

        # Screen 03: Domain Overview
        resp_03 = await ac.get("/api/openseo/domain/overview?domain=thoitranggenz.vn")
        assert resp_03.status_code == 200
        d03 = resp_03.json()
        assert d03["domain_rank"] > 0
        assert "top_3" in d03["ranked_distribution"]
        assert len(d03["top_pages"]) >= 1

        # Screen 04: Backlinks
        resp_04 = await ac.get("/api/openseo/backlinks?domain=thoitranggenz.vn&tab=backlinks")
        assert resp_04.status_code == 200
        d04 = resp_04.json()
        assert d04["stats"]["total_backlinks"] > 0
        assert "referring_domains" in d04["sub_tabs"]
        assert "anchors" in d04["sub_tabs"]

        # =====================================================================
        # 3. AI Visibility
        # =====================================================================
        # Screen 05: Prompt Research
        resp_05 = await ac.get("/api/openseo/ai-visibility/prompts?niche=Thời+Trang+GenZ")
        assert resp_05.status_code == 200
        d05 = resp_05.json()
        assert len(d05["popular_prompts"]) >= 1

        # Screen 06: Prompt Explorer
        resp_06 = await ac.get("/api/openseo/ai-visibility/explore?prompt_query=Top+shop+váy+đẹp")
        assert resp_06.status_code == 200
        d06 = resp_06.json()
        assert len(d06["llm_responses"]) >= 1
        assert len(d06["llm_responses"][0]["citations"]) >= 1

        # Screen 07: Prompt Tracking
        resp_07 = await ac.get(f"/api/openseo/projects/{project_id}/ai-visibility/tracking")
        assert resp_07.status_code == 200
        d07 = resp_07.json()
        assert "overall_share_of_voice" in d07
        assert len(d07["prompts"]) >= 1

        # =====================================================================
        # 4. My Site
        # =====================================================================
        # Screen 08: GSC Insights
        resp_08 = await ac.get(f"/api/openseo/projects/{project_id}/gsc")
        assert resp_08.status_code == 200
        d08 = resp_08.json()
        assert "clicks" in d08["totals"]
        assert len(d08["queries"]) >= 1
        assert len(d08["countries"]) >= 1

        # Screen 09: Rank Tracking
        resp_09 = await ac.get(f"/api/openseo/projects/{project_id}/rank-tracking")
        assert resp_09.status_code == 200
        d09 = resp_09.json()
        assert d09["total_tracked"] > 0
        assert len(d09["keywords"]) >= 1

        # Screen 10: Local SEO Geo-Grid Heatmap
        resp_10 = await ac.get("/api/openseo/local-seo/geogrid?business_name=Shop+Genz&keyword=vay+xinh&grid_size=5")
        assert resp_10.status_code == 200
        d10 = resp_10.json()
        assert d10["grid_size"] == "5x5"
        assert len(d10["grid_points"]) == 25

        # Screen 11: Saved Keywords
        resp_11_list = await ac.get(f"/api/openseo/projects/{project_id}/saved-keywords")
        assert resp_11_list.status_code == 200
        d11_list = resp_11_list.json()
        assert len(d11_list) >= 1

        resp_11_create = await ac.post(
            f"/api/openseo/projects/{project_id}/saved-keywords",
            json={
                "keyword": "đầm y2k cá tính",
                "search_volume": 9800,
                "keyword_difficulty": 32,
                "cpc": 0.35,
                "intent": "Commercial",
            },
        )
        assert resp_11_create.status_code == 201
        assert resp_11_create.json()["keyword"] == "đầm y2k cá tính"

        # Screen 12: Site Audit (OpenSEO-Audit/1.0 & Lighthouse)
        resp_12 = await ac.post(f"/api/openseo/projects/{project_id}/audit")
        assert resp_12.status_code == 200
        d12 = resp_12.json()
        assert d12["health_score"] > 80
        assert "lighthouse" in d12["audit_data"]
        assert len(d12["audit_data"]["issues"]) >= 1

        # =====================================================================
        # 5. AI Tools
        # =====================================================================
        # Screen 13: Reports
        resp_13 = await ac.get(f"/api/openseo/projects/{project_id}/reports")
        assert resp_13.status_code == 200
        d13 = resp_13.json()
        assert "executive_summary" in d13
        assert len(d13["key_recommendations"]) >= 1

        # Screen 14: Context (Two-Way Sync)
        resp_14_get = await ac.get(f"/api/openseo/projects/{project_id}/context")
        assert resp_14_get.status_code == 200
        d14 = resp_14_get.json()
        assert d14["synced_two_way"] is True

        resp_14_put = await ac.put(
            f"/api/openseo/projects/{project_id}/context",
            json={"website_url": "https://thoitranggenz-official.vn"},
        )
        assert resp_14_put.status_code == 200
        assert resp_14_put.json()["website_url"] == "https://thoitranggenz-official.vn"

        # Screen 15: Agent setup (MCP)
        resp_15 = await ac.get("/api/openseo/agent-setup")
        assert resp_15.status_code == 200
        d15 = resp_15.json()
        assert "mcpServers" in d15["config_snippets"]["claude_code"]
        assert "openseo_keyword_research" in d15["available_tools"]

        # =====================================================================
        # 6. Global / Drawer
        # =====================================================================
        # Screen 16: SAM AI Assistant
        resp_16 = await ac.post(
            f"/api/openseo/projects/{project_id}/sam",
            json={"message": "Tôi nên chọn từ khóa nào để SEO nhanh nhất?"},
        )
        assert resp_16.status_code == 200
        d16 = resp_16.json()
        assert "SAM" in d16["assistant"]
        assert len(d16["reply"]) > 20

        # Screen 17: Project Settings & Integrations
        resp_17 = await ac.get(f"/api/openseo/projects/{project_id}/settings")
        assert resp_17.status_code == 200
        d17 = resp_17.json()
        assert "dataforseo" in d17["integrations"]
        assert "google_search_console" in d17["integrations"]
