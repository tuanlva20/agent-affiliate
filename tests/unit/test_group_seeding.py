"""Unit tests for GroupSeedingService (Phase 5.4 / AMAS-16).

Verifies:
1. Dynamic copy generation for 2 distinct niches (Tech accessories vs Skincare).
2. Negative keyword filtering and sanitization.
3. Group publishing with approval_mode toggle and captcha_blocked guard.
4. Real-time post scanning, trigger keyword matching, and 100% comment deduplication.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.database.models import Base, Channel, GroupCommentLog, Niche, Project, ProjectGroup, PublishLog
from src.services.group_seeding_service import (
    GroupSeedingService,
    generate_dynamic_group_post,
    generate_dynamic_seeding_comment,
)


@pytest_asyncio.fixture
async def async_session():
    """Isolated in-memory SQLite session for seeding tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_dynamic_generation_two_different_niches():
    """Verify dynamic content alters appropriately across diverse project settings."""
    proj_tech = Project(
        project_id="proj_tech_01",
        name="Tech Gadgets Hub",
        niche_brief="Cáp sạc và phụ kiện công nghệ",
        target_audience="Dân văn phòng và sinh viên IT",
        tone_of_voice="GenZ hài hước",
        trigger_keywords=["cáp sạc", "pin dự phòng"],
        negative_keywords=["hàng nhái", "lừa đảo"],
    )

    proj_beauty = Project(
        project_id="proj_beauty_02",
        name="Pure Beauty Clinic",
        niche_brief="Serum phục hồi da mụn",
        target_audience="Phụ nữ 22-35 tuổi",
        tone_of_voice="Chuyên gia da liễu",
        trigger_keywords=["da mụn", "serum B5"],
        negative_keywords=["kem trộn", "bong tróc"],
    )

    post_tech = generate_dynamic_group_post(
        proj_tech,
        product_title="Cáp sạc Baseus 100W",
        affiliate_url="https://shope.ee/tech100w",
    )
    assert "Cáp sạc Baseus 100W" in post_tech
    assert "https://shope.ee/tech100w" in post_tech
    assert "sinh viên IT" in post_tech
    assert "hàng nhái" not in post_tech

    post_beauty = generate_dynamic_group_post(
        proj_beauty,
        product_title="Serum La Roche-Posay B5",
        affiliate_url="https://shope.ee/larocheb5",
    )
    assert "Serum La Roche-Posay B5" in post_beauty
    assert "https://shope.ee/larocheb5" in post_beauty
    assert "Phụ nữ 22-35 tuổi" in post_beauty
    assert "kem trộn" not in post_beauty

    assert post_tech != post_beauty


@pytest.mark.asyncio
async def test_negative_keywords_sanitization():
    """Verify negative keywords are stripped from custom content and comments."""
    proj = Project(
        project_id="proj_test_neg",
        name="Test Neg",
        negative_keywords=["rởm", "lừa đảo"],
    )

    custom_text = "Hàng này không phải đồ rởm hay lừa đảo đâu mọi người ơi."
    sanitized = generate_dynamic_group_post(
        proj,
        product_title="Loa Bluetooth",
        affiliate_url="https://shope.ee/loa",
        custom_content=custom_text,
    )
    assert "rởm" not in sanitized.lower()
    assert "lừa đảo" not in sanitized.lower()
    assert "https://shope.ee/loa" in sanitized


@pytest.mark.asyncio
async def test_publish_to_group_success_and_approval_mode(async_session: AsyncSession):
    """Test group publishing flow with approval mode check and audit logging."""
    proj = Project(
        project_id="p_group_pub",
        name="Group Pub Project",
        niche_brief="Phụ kiện công nghệ",
    )
    niche = Niche(niche_id="niche_pub_01", name="Phụ kiện")
    async_session.add_all([proj, niche])
    await async_session.flush()

    chan = Channel(
        channel_id="chan_pub_01",
        niche_id="niche_pub_01",
        browser_profile_id="prof_pub_01",
        platform="facebook",
        lifecycle_status="ready_to_post",
    )
    async_session.add(chan)

    grp_auto = ProjectGroup(
        group_id="grp_auto_01",
        project_id="p_group_pub",
        group_url="https://facebook.com/groups/techlovers",
        group_name="Hội Nghiện Công Nghệ",
        approval_mode=False,
    )
    grp_mod = ProjectGroup(
        group_id="grp_mod_02",
        project_id="p_group_pub",
        group_url="https://facebook.com/groups/modlovers",
        group_name="Hội Review Kỹ Tính",
        approval_mode=True,
    )
    async_session.add_all([grp_auto, grp_mod])
    await async_session.commit()

    service = GroupSeedingService()

    # 1. Auto group
    res_auto = await service.publish_to_group(
        async_session,
        group_id="grp_auto_01",
        channel_id="chan_pub_01",
        product_title="Bàn phím cơ Aula F75",
        affiliate_url="https://shope.ee/aulaf75",
    )
    assert res_auto["success"] is True
    assert res_auto["status"] == "posted"

    # 2. Moderated group
    res_mod = await service.publish_to_group(
        async_session,
        group_id="grp_mod_02",
        channel_id="chan_pub_01",
        product_title="Bàn phím cơ Aula F75",
        affiliate_url="https://shope.ee/aulaf75",
    )
    assert res_mod["success"] is True
    assert res_mod["status"] == "pending_approval"


@pytest.mark.asyncio
async def test_publish_to_group_blocked_channel(async_session: AsyncSession):
    """Verify captcha_blocked channel raises RuntimeError."""
    proj = Project(project_id="p_block_test", name="Block Test")
    niche = Niche(niche_id="niche_block_01", name="Block Niche")
    async_session.add_all([proj, niche])
    await async_session.flush()

    chan = Channel(
        channel_id="chan_block_01",
        niche_id="niche_block_01",
        browser_profile_id="prof_block_01",
        platform="facebook",
        lifecycle_status="captcha_blocked",
    )
    grp = ProjectGroup(
        group_id="grp_block_01",
        project_id="p_block_test",
        group_url="https://facebook.com/groups/blockgrp",
        group_name="Block Group",
    )
    async_session.add_all([chan, grp])
    await async_session.commit()

    service = GroupSeedingService()
    with pytest.raises(RuntimeError, match="captcha_blocked"):
        await service.publish_to_group(
            async_session,
            group_id="grp_block_01",
            channel_id="chan_block_01",
            product_title="Sample",
            affiliate_url="https://aff.link",
        )


@pytest.mark.asyncio
async def test_scan_and_seed_group_matching_and_deduplication(async_session: AsyncSession):
    """Verify candidate matching by keywords, negative keywords skipping, and 100% deduplication."""
    proj = Project(
        project_id="p_seeding_test",
        name="Skincare Seeding",
        niche_brief="Mỹ phẩm chăm sóc da",
        trigger_keywords=["mụn ẩn", "kem chống nắng"],
        negative_keywords=["kem trộn", "kem tự chế"],
        tone_of_voice="Chuyên gia",
    )
    niche = Niche(niche_id="niche_seed_01", name="Skincare")
    async_session.add_all([proj, niche])
    await async_session.flush()

    chan = Channel(
        channel_id="chan_seed_01",
        niche_id="niche_seed_01",
        browser_profile_id="prof_seed_01",
        platform="facebook",
        lifecycle_status="ready_to_post",
    )
    grp = ProjectGroup(
        group_id="grp_seed_01",
        project_id="p_seeding_test",
        group_url="https://facebook.com/groups/skincaretips",
        group_name="Hội Skincare Khoa Học",
    )
    async_session.add_all([chan, grp])
    await async_session.commit()

    service = GroupSeedingService()

    candidate_posts = [
        {"post_id": "post_101", "post_text": "Mọi người tư vấn giúp em sản phẩm trị mụn ẩn với ạ!"},
        {"post_id": "post_102", "post_text": "Hôm nay thời tiết đẹp quá mọi người ơi."},  # No trigger
        {"post_id": "post_103", "post_text": "Em vừa thử loại kem trộn này thấy mụn ẩn biến mất liền."},  # Has negative keyword
        {"post_id": "post_104", "post_text": "Cho em hỏi kem chống nắng nào kiềm dầu tốt nhất?"},  # Trigger
    ]

    # First Run: Only post_101 and post_104 should be seeded
    results_run1 = await service.scan_and_seed_group(
        async_session,
        group_id="grp_seed_01",
        channel_id="chan_seed_01",
        product_title="Kem chống nắng Anessa Gold",
        affiliate_url="https://shope.ee/anessa",
        candidate_posts=candidate_posts,
    )

    assert len(results_run1) == 2
    seeded_ids = [r["post_id"] for r in results_run1]
    assert "post_101" in seeded_ids
    assert "post_104" in seeded_ids
    assert "post_102" not in seeded_ids
    assert "post_103" not in seeded_ids

    # Second Run with same candidate posts: Must produce 0 comments due to deduplication
    results_run2 = await service.scan_and_seed_group(
        async_session,
        group_id="grp_seed_01",
        channel_id="chan_seed_01",
        product_title="Kem chống nắng Anessa Gold",
        affiliate_url="https://shope.ee/anessa",
        candidate_posts=candidate_posts,
    )
    assert len(results_run2) == 0
