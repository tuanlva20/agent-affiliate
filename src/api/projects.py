"""AMAS v1.5.0 — Projects Management API (Phase 5.5 / AMAS-17).

Provides:
1. Google Cloud Console style Workspace Projects CRUD.
2. Default automatic seeding of initial workspaces (Fashion GenZ & Smart Home) if empty.
3. Quick Presets (Templates) for at least 4 major affiliate niches with field tooltips.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db
from src.database.models import Project

router = APIRouter(prefix="/api/projects", tags=["Projects"])

DEFAULT_PRESETS = [
    {
        "id": "preset_fashion_genz",
        "name": "Thời Trang GenZ",
        "niche_brief": "Thời trang GenZ xu hướng Y2K, đồ công sở trẻ và phong cách đường phố (streetwear)",
        "target_audience": "Nữ giới 18-26 tuổi, học sinh, sinh viên và người mới đi làm",
        "tone_of_voice": "GenZ gần gũi, hài hước, bắt trend TikTok, dùng từ ngữ thân thuộc",
        "trigger_keywords": ["váy xinh", "outfit", "set đồ", "phối đồ", "áo thun form rộng"],
        "negative_keywords": ["hàng lỗi", "vải mỏng rách", "kém chất lượng", "lừa đảo"],
    },
    {
        "id": "preset_smart_home",
        "name": "Đồ Gia Dụng Tiện Ích",
        "niche_brief": "Đồ gia dụng thông minh, giải pháp tiện ích cho nhà bếp và không gian sống gọn gàng",
        "target_audience": "Người nội trợ, gia đình trẻ và dân văn phòng từ 24-42 tuổi",
        "tone_of_voice": "Chuyên gia uy tín, đánh giá thực tế, chân thành, tập trung tính ứng dụng",
        "trigger_keywords": ["tiện ích", "thông minh", "máy hút bụi", "nồi chiên không dầu", "hộp đựng thực phẩm"],
        "negative_keywords": ["hàng dỏm", "cháy nổ", "nhanh hỏng", "hàng nhái"],
    },
    {
        "id": "preset_beauty_skincare",
        "name": "Mỹ Phẩm & Skincare",
        "niche_brief": "Mỹ phẩm chăm sóc da khoa học, phục hồi da mụn, chống nắng và dưỡng sáng da",
        "target_audience": "Nam & Nữ từ 18-35 tuổi quan tâm đến chăm sóc da an toàn",
        "tone_of_voice": "Bác sĩ / Chuyên gia da liễu thân thiện, dẫn chứng thành phần khoa học (KOL/KOC uy tín)",
        "trigger_keywords": ["da mụn", "serum B5", "kem chống nắng", "kiềm dầu", "phục hồi"],
        "negative_keywords": ["kem trộn", "bong tróc", "bào mòn da", "rượu thuốc"],
    },
    {
        "id": "preset_tech_accessories",
        "name": "Phụ Kiện Công Nghệ",
        "niche_brief": "Củ sạc nhanh, cáp sạc, tai nghe bluetooth, phụ kiện setup góc làm việc và gaming",
        "target_audience": "Dân công nghệ, game thủ, sinh viên IT và dân văn phòng 18-32 tuổi",
        "tone_of_voice": "KOC công nghệ nhiệt huyết, phân tích thông số kỹ thuật rõ ràng, dí dỏm",
        "trigger_keywords": ["cáp sạc", "sạc nhanh 65W", "tai nghe chống ồn", "bàn phím cơ", "chuột không dây"],
        "negative_keywords": ["hàng fake", "nổ pin", "nhanh cháy", "chập điện"],
    },
]

FIELD_TOOLTIPS = {
    "name": "Tên không gian làm việc của dự án affiliate để phân loại sản phẩm và kênh",
    "niche_brief": "Mô tả chi tiết ngách ngành hàng mục tiêu giúp AI định hướng nội dung video & kịch bản",
    "target_audience": "Chân dung khách hàng mục tiêu để điều chỉnh cách xưng hô và điểm chạm tâm lý",
    "tone_of_voice": "Văn phong thương hiệu của AI khi sinh kịch bản video và seeding comment trong hội nhóm",
    "trigger_keywords": "Các từ khóa kích hoạt comment seeding tự động khi xuất hiện trong bài viết Facebook Group",
    "negative_keywords": "Các từ cấm tuyệt đối không được xuất hiện trong nội dung video, caption hoặc comment",
}


class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    niche_brief: Optional[str] = None
    target_audience: Optional[str] = None
    tone_of_voice: Optional[str] = None
    trigger_keywords: Optional[List[str]] = None
    negative_keywords: Optional[List[str]] = None


class ProjectUpdateRequest(BaseModel):
    name: Optional[str] = None
    niche_brief: Optional[str] = None
    target_audience: Optional[str] = None
    tone_of_voice: Optional[str] = None
    trigger_keywords: Optional[List[str]] = None
    negative_keywords: Optional[List[str]] = None


@router.get("/presets")
async def get_project_presets():
    """Returns quick template presets and field tooltip guidance."""
    return {
        "field_tooltips": FIELD_TOOLTIPS,
        "presets": DEFAULT_PRESETS,
    }


@router.get("/")
async def list_projects(db: AsyncSession = Depends(get_db)):
    """Lists all workspace projects. Auto-seeds defaults if empty."""
    stmt = select(Project).order_by(Project.name.asc())
    res = await db.execute(stmt)
    projects = res.scalars().all()

    if not projects:
        # Seed 2 default projects
        p1 = Project(
            project_id=f"proj_fashion_{uuid.uuid4().hex[:6]}",
            name=DEFAULT_PRESETS[0]["name"],
            niche_brief=DEFAULT_PRESETS[0]["niche_brief"],
            target_audience=DEFAULT_PRESETS[0]["target_audience"],
            tone_of_voice=DEFAULT_PRESETS[0]["tone_of_voice"],
            trigger_keywords=DEFAULT_PRESETS[0]["trigger_keywords"],
            negative_keywords=DEFAULT_PRESETS[0]["negative_keywords"],
        )
        p2 = Project(
            project_id=f"proj_smart_{uuid.uuid4().hex[:6]}",
            name=DEFAULT_PRESETS[1]["name"],
            niche_brief=DEFAULT_PRESETS[1]["niche_brief"],
            target_audience=DEFAULT_PRESETS[1]["target_audience"],
            tone_of_voice=DEFAULT_PRESETS[1]["tone_of_voice"],
            trigger_keywords=DEFAULT_PRESETS[1]["trigger_keywords"],
            negative_keywords=DEFAULT_PRESETS[1]["negative_keywords"],
        )
        db.add_all([p1, p2])
        await db.commit()
        projects = [p1, p2]

    return [
        {
            "project_id": p.project_id,
            "name": p.name,
            "niche_brief": p.niche_brief,
            "target_audience": p.target_audience,
            "tone_of_voice": p.tone_of_voice,
            "trigger_keywords": p.trigger_keywords or [],
            "negative_keywords": p.negative_keywords or [],
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in projects
    ]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_project(
    req: ProjectCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Creates a new workspace project."""
    project_id = f"proj_{uuid.uuid4().hex[:10]}"
    project = Project(
        project_id=project_id,
        name=req.name,
        niche_brief=req.niche_brief,
        target_audience=req.target_audience,
        tone_of_voice=req.tone_of_voice,
        trigger_keywords=req.trigger_keywords or [],
        negative_keywords=req.negative_keywords or [],
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)

    return {
        "project_id": project.project_id,
        "name": project.name,
        "niche_brief": project.niche_brief,
        "target_audience": project.target_audience,
        "tone_of_voice": project.tone_of_voice,
        "trigger_keywords": project.trigger_keywords or [],
        "negative_keywords": project.negative_keywords or [],
        "created_at": project.created_at.isoformat() if project.created_at else None,
    }


@router.get("/{project_id}")
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieves a single project by ID."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )
    return {
        "project_id": project.project_id,
        "name": project.name,
        "niche_brief": project.niche_brief,
        "target_audience": project.target_audience,
        "tone_of_voice": project.tone_of_voice,
        "trigger_keywords": project.trigger_keywords or [],
        "negative_keywords": project.negative_keywords or [],
        "created_at": project.created_at.isoformat() if project.created_at else None,
    }


@router.put("/{project_id}")
async def update_project(
    project_id: str,
    req: ProjectUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Updates project properties."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    if req.name is not None:
        project.name = req.name
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

    await db.commit()
    await db.refresh(project)

    return {
        "project_id": project.project_id,
        "name": project.name,
        "niche_brief": project.niche_brief,
        "target_audience": project.target_audience,
        "tone_of_voice": project.tone_of_voice,
        "trigger_keywords": project.trigger_keywords or [],
        "negative_keywords": project.negative_keywords or [],
    }


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """Deletes a workspace project."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )
    await db.delete(project)
    await db.commit()
    return None
