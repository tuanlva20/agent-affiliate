"""AMAS v1.5.0 — OpenSEO FastAPI Endpoints (Phase 7.1 / AMAS-21).

Provides REST endpoints for all 5 Navigation Groups and 17 Screens of OpenSEO:
1. Overview: Dashboard (01)
2. Research: Keyword Research (02), Domain Overview (03), Backlinks (04)
3. AI Visibility: Prompt Research (05), Prompt Explorer (06), Prompt Tracking (07)
4. My Site: GSC Insights (08), Rank Tracking (09), Local SEO Geo-Grid (10), Saved Keywords (11), Site Audit (12)
5. AI Tools: Reports (13), Brand Context (14), Agent Setup MCP (15)
6. Global / Drawer: SAM AI Assistant (16), Project Settings & Integrations (17)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db
from src.database.models import Project
from src.services.openseo_engine import OpenSEOEngine

router = APIRouter(prefix="/api/openseo", tags=["OpenSEO"])
engine = OpenSEOEngine()


async def _get_project_or_404(project_id: str, db: AsyncSession) -> Project:
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id '{project_id}' not found.",
        )
    return project


# =============================================================================
# 1. Overview
# =============================================================================

@router.get("/projects/{project_id}/dashboard")
async def get_project_dashboard(project_id: str, db: AsyncSession = Depends(get_db)):
    """01. Dashboard: Overall KPI, GSC performance chart, health score & recent keywords."""
    project = await _get_project_or_404(project_id, db)
    return engine.get_dashboard(project)


# =============================================================================
# 2. Research
# =============================================================================

@router.get("/keywords/research")
async def research_keywords(
    query: str = Query(..., min_length=1),
    location: str = Query("VN"),
    language: str = Query("vi"),
):
    """02. Keyword Research: Volume, KD %, CPC, Search Intent & 12-month Trend."""
    return engine.research_keywords(query=query, location=location, language=language)


@router.get("/domain/overview")
async def get_domain_overview(domain: str = Query(..., min_length=1)):
    """03. Domain Overview: Organic traffic, Ranked keywords, Top pages, Competitor gap."""
    return engine.get_domain_overview(domain=domain)


@router.get("/backlinks")
async def get_backlinks(
    domain: str = Query(..., min_length=1),
    tab: str = Query("backlinks"),
):
    """04. Backlinks: Referring domains, Backlinks count, Domain rank, Dofollow ratio."""
    return engine.get_backlinks(domain=domain, tab=tab)


# =============================================================================
# 3. AI Visibility
# =============================================================================

@router.get("/ai-visibility/prompts")
async def research_prompts(niche: str = Query("Thời Trang GenZ")):
    """05. Prompt Research: Popular prompts asked to LLMs in the target niche."""
    return engine.research_prompts(industry_niche=niche)


@router.get("/ai-visibility/explore")
async def explore_prompt(prompt_query: str = Query(..., min_length=1)):
    """06. Prompt Explorer: Actual LLM answers, mentioned brand names, cited sources."""
    return engine.explore_prompt(prompt_query=prompt_query)


@router.get("/projects/{project_id}/ai-visibility/tracking")
async def track_prompt_visibility(project_id: str, db: AsyncSession = Depends(get_db)):
    """07. Prompt Tracking: AI Share of Voice & rank positioning over time."""
    project = await _get_project_or_404(project_id, db)
    return engine.track_prompt_visibility(project_id=project.project_id)


# =============================================================================
# 4. My Site
# =============================================================================

@router.get("/projects/{project_id}/gsc")
async def get_gsc_performance(
    project_id: str,
    date_range: str = Query("last_28_days"),
    db: AsyncSession = Depends(get_db),
):
    """08. GSC Insights: Total clicks, impressions, CTR, average position."""
    project = await _get_project_or_404(project_id, db)
    return engine.get_gsc_performance(project=project, date_range=date_range)


@router.get("/projects/{project_id}/rank-tracking")
async def get_rank_tracking(project_id: str, db: AsyncSession = Depends(get_db)):
    """09. Rank Tracking: Daily SERP rank tracking (Desktop & Mobile)."""
    project = await _get_project_or_404(project_id, db)
    return engine.get_rank_tracking(project_id=project.project_id)


@router.get("/local-seo/geogrid")
async def get_local_seo_geogrid(
    business_name: str = Query("AMAS Flagship Store"),
    keyword: str = Query("thời trang nữ"),
    grid_size: int = Query(5, ge=3, le=9),
):
    """10. Local SEO: Local Map Pack Geo-Grid Heatmap coordinates."""
    return engine.get_local_seo_geogrid(
        business_name=business_name, keyword=keyword, grid_size=grid_size
    )


class SaveKeywordRequest(BaseModel):
    keyword: str = Field(..., min_length=1)
    search_volume: int = 0
    keyword_difficulty: int = 0
    cpc: float = 0.0
    intent: str = "Commercial"


@router.get("/projects/{project_id}/saved-keywords")
async def list_saved_keywords(project_id: str, db: AsyncSession = Depends(get_db)):
    """11. Saved Keywords: List saved keywords for project."""
    project = await _get_project_or_404(project_id, db)
    return await engine.get_saved_keywords(session=db, project_id=project.project_id)


@router.post("/projects/{project_id}/saved-keywords", status_code=status.HTTP_201_CREATED)
async def save_keyword(
    project_id: str,
    req: SaveKeywordRequest,
    db: AsyncSession = Depends(get_db),
):
    """11. Saved Keywords: Save a target keyword."""
    project = await _get_project_or_404(project_id, db)
    return await engine.save_keyword(
        session=db,
        project_id=project.project_id,
        keyword=req.keyword,
        search_volume=req.search_volume,
        keyword_difficulty=req.keyword_difficulty,
        cpc=req.cpc,
        intent=req.intent,
    )


@router.post("/projects/{project_id}/audit")
async def run_site_audit(project_id: str, db: AsyncSession = Depends(get_db)):
    """12. Site Audit: Run OpenSEO-Audit/1.0 & Lighthouse crawler."""
    project = await _get_project_or_404(project_id, db)
    return await engine.run_site_audit(session=db, project=project)


# =============================================================================
# 5. AI Tools
# =============================================================================

@router.get("/projects/{project_id}/reports")
async def generate_seo_report(
    project_id: str,
    report_type: str = Query("monthly_summary"),
    db: AsyncSession = Depends(get_db),
):
    """13. Reports: Automated AI SEO analysis report."""
    project = await _get_project_or_404(project_id, db)
    return engine.generate_seo_report(project=project, report_type=report_type)


class UpdateBrandContextRequest(BaseModel):
    niche_brief: Optional[str] = None
    target_audience: Optional[str] = None
    tone_of_voice: Optional[str] = None
    trigger_keywords: Optional[List[str]] = None
    negative_keywords: Optional[List[str]] = None
    website_url: Optional[str] = None


@router.get("/projects/{project_id}/context")
async def get_brand_context(project_id: str, db: AsyncSession = Depends(get_db)):
    """14. Context: Brand & Website context synced with Project settings."""
    project = await _get_project_or_404(project_id, db)
    return engine.get_brand_context(project)


@router.put("/projects/{project_id}/context")
async def update_brand_context(
    project_id: str,
    req: UpdateBrandContextRequest,
    db: AsyncSession = Depends(get_db),
):
    """14. Context: Update brand context and sync back to Project table."""
    project = await _get_project_or_404(project_id, db)
    if req.niche_brief is not None:
        project.niche_brief = req.niche_brief
    if req.target_audience is not None:
        project.target_audience = req.target_audience
    if req.tone_of_voice is not None:
        project.tone_of_voice = req.tone_of_voice
    if req.trigger_keywords is not None:
        project.trigger_keywords = req.trigger_keywords
    if req.negative_keywords is not None:
        project.negative_keywords = req.negative_keywords
    if req.website_url is not None:
        project.website_url = req.website_url

    await db.commit()
    await db.refresh(project)
    return engine.get_brand_context(project)


@router.get("/agent-setup")
async def get_mcp_agent_setup():
    """15. Agent setup: MCP Server configuration for coding agents."""
    return engine.get_mcp_agent_setup()


# =============================================================================
# 6. Global / Drawer
# =============================================================================

class SamChatRequest(BaseModel):
    message: str = Field(..., min_length=1)


@router.post("/projects/{project_id}/sam")
async def ask_sam_assistant(
    project_id: str,
    req: SamChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """16. SAM AI Assistant: Interactive AI SEO Advisor."""
    project = await _get_project_or_404(project_id, db)
    return engine.ask_sam_assistant(project=project, user_message=req.message)


@router.get("/projects/{project_id}/settings")
async def get_project_settings(project_id: str, db: AsyncSession = Depends(get_db)):
    """17. Project Settings & Integrations: DataForSEO, OpenRouter, GSC, GA4."""
    project = await _get_project_or_404(project_id, db)
    return engine.get_project_settings(project)
