"""E2E Integration Test Suite for OpenSEO 17 Screens & 5 Navigation Groups (AMAS-23 / Phase 7.3).

Validates 3 Mandatory Scenarios:
1. Scenario 1: Multi-Project Domain & Data Isolation:
   - Creates 2 distinct Projects with unique website_urls ("https://thoitranggenz.vn" vs "https://phukiencongnghe.vn").
   - Ensures strict workspace isolation: saved keywords, site audits, domain contexts, and reports never cross-leak.
2. Scenario 2: Comprehensive End-to-End Verification across all 5 Groups and 17 Functional Screens:
   - Overview: 01. Dashboard
   - Research: 02. Keyword Research, 03. Domain Overview, 04. Backlinks
   - AI Visibility: 05. Prompt Research, 06. Prompt Explorer, 07. Prompt Tracking
   - My Site: 08. GSC Insights, 09. Rank Tracking, 10. Local SEO Geo-Grid, 11. Saved Keywords, 12. Site Audit (OpenSEO-Audit/1.0 & Lighthouse)
   - AI Tools: 13. Reports, 14. Context (Two-Way Sync), 15. Agent Setup (MCP)
   - Global / Drawer: 16. SAM AI Assistant, 17. Project Settings & Integrations
3. Scenario 3: UI Component Architecture & Build Verification Check:
   - Validates OpenSEOTab.tsx includes all 5 navigation groups, 17 screens, and SAM drawer.
"""

from __future__ import annotations

import os
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.main import app
from src.database.models import Base, Project, SEOAuditReport, SEOSavedKeyword
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


# ==============================================================================
# Kịch bản 1 — Cô lập Domain & Dữ liệu OpenSEO theo Project
# ==============================================================================

@pytest.mark.asyncio
async def test_scenario_1_domain_and_data_isolation(db_session: AsyncSession):
    """Verifies that 2 projects with different website_urls maintain complete data isolation."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Tạo Project 1: Thời Trang GenZ
        resp_p1 = await ac.post(
            "/api/projects/",
            json={
                "name": "Thời Trang GenZ",
                "niche_brief": "Thời trang nữ Y2K cá tính",
                "target_audience": "Nữ 18-25 tuổi",
                "tone_of_voice": "Trẻ trung, năng động",
                "trigger_keywords": ["váy đẹp", "outfit y2k"],
                "negative_keywords": ["đồ lỗi"],
            },
        )
        assert resp_p1.status_code == 201
        p1_id = resp_p1.json()["project_id"]

        # Cập nhật website_url cho Project 1 qua context endpoint
        resp_c1 = await ac.put(
            f"/api/openseo/projects/{p1_id}/context",
            json={"website_url": "https://thoitranggenz.vn"},
        )
        assert resp_c1.status_code == 200
        assert resp_c1.json()["website_url"] == "https://thoitranggenz.vn"

        # 2. Tạo Project 2: Phụ Kiện Công Nghệ
        resp_p2 = await ac.post(
            "/api/projects/",
            json={
                "name": "Phụ Kiện Công Nghệ",
                "niche_brief": "Phụ kiện sạc cáp tai nghe cao cấp",
                "target_audience": "Nam/Nữ 20-35 tuổi đam mê công nghệ",
                "tone_of_voice": "Chuyên nghiệp, tin cậy",
                "trigger_keywords": ["sạc nhanh", "tai nghe bluetooth"],
                "negative_keywords": ["hàng giả"],
            },
        )
        assert resp_p2.status_code == 201
        p2_id = resp_p2.json()["project_id"]

        # Cập nhật website_url cho Project 2 qua context endpoint
        resp_c2 = await ac.put(
            f"/api/openseo/projects/{p2_id}/context",
            json={"website_url": "https://phukiencongnghe.vn"},
        )
        assert resp_c2.status_code == 200
        assert resp_c2.json()["website_url"] == "https://phukiencongnghe.vn"

        # 3. Lưu Saved Keywords riêng biệt cho Project 1
        p1_keywords = ["đầm y2k cá tính", "áo croptop ôm body", "chân váy tennis"]
        for kw in p1_keywords:
            resp_kw = await ac.post(
                f"/api/openseo/projects/{p1_id}/saved-keywords",
                json={
                    "keyword": kw,
                    "search_volume": 12500,
                    "keyword_difficulty": 28,
                    "cpc": 0.45,
                    "intent": "Commercial",
                },
            )
            assert resp_kw.status_code == 201

        # 4. Lưu Saved Keywords riêng biệt cho Project 2
        p2_keywords = ["cáp sạc type c 100w", "tai nghe chống ồn anc", "hub usb c đa năng"]
        for kw in p2_keywords:
            resp_kw = await ac.post(
                f"/api/openseo/projects/{p2_id}/saved-keywords",
                json={
                    "keyword": kw,
                    "search_volume": 24000,
                    "keyword_difficulty": 45,
                    "cpc": 0.85,
                    "intent": "Transactional",
                },
            )
            assert resp_kw.status_code == 201

        # 5. Xác minh dữ liệu Saved Keywords không bị lẫn (Cross-leak check)
        get_p1_kw = await ac.get(f"/api/openseo/projects/{p1_id}/saved-keywords")
        assert get_p1_kw.status_code == 200
        p1_list = get_p1_kw.json()
        p1_retrieved_names = [k["keyword"] for k in p1_list]
        for kw in p1_keywords:
            assert kw in p1_retrieved_names
        for kw in p2_keywords:
            assert kw not in p1_retrieved_names, f"Leaked {kw} from Project 2 into Project 1!"

        get_p2_kw = await ac.get(f"/api/openseo/projects/{p2_id}/saved-keywords")
        assert get_p2_kw.status_code == 200
        p2_list = get_p2_kw.json()
        p2_retrieved_names = [k["keyword"] for k in p2_list]
        for kw in p2_keywords:
            assert kw in p2_retrieved_names
        for kw in p1_keywords:
            assert kw not in p2_retrieved_names, f"Leaked {kw} from Project 1 into Project 2!"

        # 6. Chạy Audit riêng biệt và xác thực báo cáo không bị chồng chéo
        audit_p1 = await ac.post(f"/api/openseo/projects/{p1_id}/audit")
        assert audit_p1.status_code == 200
        assert audit_p1.json()["project_id"] == p1_id
        assert audit_p1.json()["website_url"] == "https://thoitranggenz.vn"

        audit_p2 = await ac.post(f"/api/openseo/projects/{p2_id}/audit")
        assert audit_p2.status_code == 200
        assert audit_p2.json()["project_id"] == p2_id
        assert audit_p2.json()["website_url"] == "https://phukiencongnghe.vn"

        # Kiểm tra Database cấp thấp trực tiếp
        db_p1_audits = (
            await db_session.execute(
                select(SEOAuditReport).where(SEOAuditReport.project_id == p1_id)
            )
        ).scalars().all()
        assert len(db_p1_audits) == 1
        assert db_p1_audits[0].website_url == "https://thoitranggenz.vn"

        db_p2_audits = (
            await db_session.execute(
                select(SEOAuditReport).where(SEOAuditReport.project_id == p2_id)
            )
        ).scalars().all()
        assert len(db_p2_audits) == 1
        assert db_p2_audits[0].website_url == "https://phukiencongnghe.vn"


# ==============================================================================
# Kịch bản 2 — Kiểm thử đầy đủ 5 Nhóm & 17 Phân hệ của OpenSEO
# ==============================================================================

@pytest.mark.asyncio
async def test_scenario_2_full_5_groups_17_screens(db_session: AsyncSession):
    """Comprehensive E2E test verifying all 5 navigation groups and 17 functional screens."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Khởi tạo Project thử nghiệm
        resp_p = await ac.post(
            "/api/projects/",
            json={
                "name": "E2E Master Store",
                "niche_brief": "Hệ thống bán lẻ thương mại điện tử đa kênh",
                "target_audience": "Người tiêu dùng toàn quốc",
                "tone_of_voice": "Chuyên nghiệp, hiện đại",
                "trigger_keywords": ["mua sắm", "khuyến mãi", "chính hãng"],
                "negative_keywords": ["kém chất lượng"],
            },
        )
        assert resp_p.status_code == 201
        p_id = resp_p.json()["project_id"]

        # Cấu hình website_url
        await ac.put(
            f"/api/openseo/projects/{p_id}/context",
            json={"website_url": "https://masterstore.vn"},
        )

        # ----------------------------------------------------------------------
        # NHÓM 1: OVERVIEW
        # ----------------------------------------------------------------------
        # Screen 01: Dashboard
        resp_s01 = await ac.get(f"/api/openseo/projects/{p_id}/dashboard")
        assert resp_s01.status_code == 200
        d01 = resp_s01.json()
        assert "kpis" in d01
        assert d01["kpis"]["health_score"] >= 0
        assert "gsc_quick_chart" in d01
        assert "audit_summary" in d01
        assert "recent_keywords" in d01
        assert "ai_visibility_snapshot" in d01

        # ----------------------------------------------------------------------
        # NHÓM 2: RESEARCH
        # ----------------------------------------------------------------------
        # Screen 02: Keyword Research
        resp_s02 = await ac.get("/api/openseo/keywords/research?query=tai+nghe+gaming&location=VN&language=vi")
        assert resp_s02.status_code == 200
        d02 = resp_s02.json()
        assert d02["total_ideas"] >= 1
        assert len(d02["keyword_ideas"]) >= 1
        first_idea = d02["keyword_ideas"][0]
        assert "keyword" in first_idea
        assert "search_volume" in first_idea
        assert "intent" in first_idea

        # Screen 03: Domain Overview
        resp_s03 = await ac.get("/api/openseo/domain/overview?domain=masterstore.vn")
        assert resp_s03.status_code == 200
        d03 = resp_s03.json()
        assert d03["domain"] == "masterstore.vn"
        assert d03["domain_rank"] > 0
        assert "ranked_distribution" in d03
        assert len(d03["top_pages"]) >= 1

        # Screen 04: Backlinks
        resp_s04 = await ac.get("/api/openseo/backlinks?domain=masterstore.vn&tab=backlinks")
        assert resp_s04.status_code == 200
        d04 = resp_s04.json()
        assert d04["stats"]["total_backlinks"] > 0
        assert "sub_tabs" in d04
        assert "referring_domains" in d04["sub_tabs"]
        assert "anchors" in d04["sub_tabs"]

        # ----------------------------------------------------------------------
        # NHÓM 3: AI VISIBILITY
        # ----------------------------------------------------------------------
        # Screen 05: Prompt Research
        resp_s05 = await ac.get("/api/openseo/ai-visibility/prompts?niche=E-Commerce")
        assert resp_s05.status_code == 200
        d05 = resp_s05.json()
        assert len(d05["popular_prompts"]) >= 1
        assert "monthly_volume" in d05["popular_prompts"][0]

        # Screen 06: Prompt Explorer
        resp_s06 = await ac.get("/api/openseo/ai-visibility/explore?prompt_query=Top+tai+nghe+gaming+tot+nhat")
        assert resp_s06.status_code == 200
        d06 = resp_s06.json()
        assert len(d06["llm_responses"]) >= 1
        assert "engine" in d06["llm_responses"][0]
        assert len(d06["llm_responses"][0]["citations"]) >= 1

        # Screen 07: Prompt Tracking
        resp_s07 = await ac.get(f"/api/openseo/projects/{p_id}/ai-visibility/tracking")
        assert resp_s07.status_code == 200
        d07 = resp_s07.json()
        assert "overall_share_of_voice" in d07
        assert len(d07["prompts"]) >= 1

        # ----------------------------------------------------------------------
        # NHÓM 4: MY SITE
        # ----------------------------------------------------------------------
        # Screen 08: GSC Insights
        resp_s08 = await ac.get(f"/api/openseo/projects/{p_id}/gsc")
        assert resp_s08.status_code == 200
        d08 = resp_s08.json()
        assert "clicks" in d08["totals"]
        assert len(d08["queries"]) >= 1
        assert len(d08["pages"]) >= 1

        # Screen 09: Rank Tracking
        resp_s09 = await ac.get(f"/api/openseo/projects/{p_id}/rank-tracking")
        assert resp_s09.status_code == 200
        d09 = resp_s09.json()
        assert d09["total_tracked"] > 0
        assert len(d09["keywords"]) >= 1

        # Screen 10: Local SEO Geo-Grid Heatmap
        resp_s10 = await ac.get("/api/openseo/local-seo/geogrid?business_name=Master+Store+HN&keyword=tai+nghe&grid_size=3")
        assert resp_s10.status_code == 200
        d10 = resp_s10.json()
        assert d10["grid_size"] == "3x3"
        assert len(d10["grid_points"]) == 9

        # Screen 11: Saved Keywords
        resp_s11_post = await ac.post(
            f"/api/openseo/projects/{p_id}/saved-keywords",
            json={
                "keyword": "tai nghe không dây pin trâu",
                "search_volume": 18200,
                "keyword_difficulty": 38,
                "cpc": 0.62,
                "intent": "Commercial",
            },
        )
        assert resp_s11_post.status_code == 201

        resp_s11_get = await ac.get(f"/api/openseo/projects/{p_id}/saved-keywords")
        assert resp_s11_get.status_code == 200
        saved_items = resp_s11_get.json()
        assert any(k["keyword"] == "tai nghe không dây pin trâu" for k in saved_items)

        # Screen 12: Site Audit (OpenSEO-Audit/1.0 & Lighthouse)
        resp_s12 = await ac.post(f"/api/openseo/projects/{p_id}/audit")
        assert resp_s12.status_code == 200
        d12 = resp_s12.json()
        assert d12["health_score"] >= 80
        assert "lighthouse" in d12["audit_data"]
        assert d12["audit_data"]["lighthouse"]["performance"] >= 80

        # ----------------------------------------------------------------------
        # NHÓM 5: AI TOOLS
        # ----------------------------------------------------------------------
        # Screen 13: Reports
        resp_s13 = await ac.get(f"/api/openseo/projects/{p_id}/reports")
        assert resp_s13.status_code == 200
        d13 = resp_s13.json()
        assert "executive_summary" in d13
        assert len(d13["key_recommendations"]) >= 1

        # Screen 14: Context (Two-Way Sync)
        resp_s14_get = await ac.get(f"/api/openseo/projects/{p_id}/context")
        assert resp_s14_get.status_code == 200
        assert resp_s14_get.json()["synced_two_way"] is True

        resp_s14_put = await ac.put(
            f"/api/openseo/projects/{p_id}/context",
            json={"website_url": "https://masterstore-official.com"},
        )
        assert resp_s14_put.status_code == 200
        assert resp_s14_put.json()["website_url"] == "https://masterstore-official.com"

        # Screen 15: Agent Setup (MCP)
        resp_s15 = await ac.get("/api/openseo/agent-setup")
        assert resp_s15.status_code == 200
        d15 = resp_s15.json()
        assert "openseo_keyword_research" in d15["available_tools"]
        assert "openseo_site_audit" in d15["available_tools"]
        assert "config_snippets" in d15

        # ----------------------------------------------------------------------
        # GLOBAL / DRAWER
        # ----------------------------------------------------------------------
        # Screen 16: SAM AI Assistant
        resp_s16 = await ac.post(
            f"/api/openseo/projects/{p_id}/sam",
            json={"message": "Phân tích đối thủ chính trong thị trường tai nghe gaming."},
        )
        assert resp_s16.status_code == 200
        d16 = resp_s16.json()
        assert "SAM" in d16["assistant"]
        assert len(d16["reply"]) > 10

        # Screen 17: Project Settings & Integrations
        resp_s17_get = await ac.get(f"/api/openseo/projects/{p_id}/settings")
        assert resp_s17_get.status_code == 200
        d17 = resp_s17_get.json()
        assert "integrations" in d17
        assert d17["integrations"]["dataforseo"]["status"] == "connected"
        assert d17["integrations"]["google_search_console"]["status"] == "connected"
        assert d17["website_url"] == "https://masterstore-official.com"


# ==============================================================================
# Kịch bản 3 — Kiểm thử UI Component & Build Verification Check
# ==============================================================================

def test_scenario_3_ui_component_architecture():
    """Validates that OpenSEOTab.tsx integrates 100% of 5 groups and 17 screens."""
    ui_component_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "web",
        "components",
        "OpenSEOTab.tsx",
    )
    assert os.path.exists(ui_component_path), f"File not found: {ui_component_path}"

    with open(ui_component_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Kiểm tra 5 Navigation Groups
    expected_groups = [
        "Overview",
        "Research",
        "AI Visibility",
        "My Site",
        "AI Tools",
    ]
    for group in expected_groups:
        assert group in content, f"Navigation group '{group}' missing from OpenSEOTab.tsx"

    # 2. Kiểm tra 17 Functional Screen IDs
    expected_screens = [
        "dashboard",
        "keyword_research",
        "domain_overview",
        "backlinks",
        "prompt_research",
        "prompt_explorer",
        "prompt_tracking",
        "gsc_insights",
        "rank_tracking",
        "local_seo",
        "saved_keywords",
        "site_audit",
        "reports",
        "brand_context",
        "agent_setup",
        "sam_assistant",
        "settings",
    ]
    for screen in expected_screens:
        assert f"'{screen}'" in content or f'"{screen}"' in content, (
            f"Screen ID '{screen}' missing from OpenSEOTab.tsx"
        )

    # 3. Kiểm tra SAM AI Assistant Drawer và Design system compliance
    assert "SAM AI Assistant" in content
    assert "#41AA6C" in content, "Emerald growth accent (#41AA6C) missing in OpenSEOTab.tsx"
