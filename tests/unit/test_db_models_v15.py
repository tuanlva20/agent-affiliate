"""Unit tests for AMAS v1.5 database models, multi-project workspace, and content calendar."""

from datetime import datetime, timezone
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    Base,
    Channel,
    Competitor,
    CompetitorVideo,
    GroupCommentLog,
    Metric,
    MotionAsset,
    Niche,
    Product,
    Project,
    ProjectGroup,
    Proxy,
    PublishLog,
    PublishSchedule,
    VideoComment,
    VideoJob,
)
from src.database.session import get_async_engine, get_session_factory

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def engine():
    return get_async_engine(TEST_DB_URL, force_new=True)


@pytest_asyncio.fixture(scope="function")
async def init_db(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def db_session(init_db, engine) -> AsyncGenerator[AsyncSession, None]:
    factory = get_session_factory(TEST_DB_URL)
    async with factory() as session:
        yield session


@pytest.mark.asyncio
async def test_models_v15_metadata(init_db, engine):
    """Verify all v1.5 tables and new columns are properly registered in Base.metadata."""
    tables = Base.metadata.tables

    # Check newly added and existing tables
    assert "projects" in tables
    assert "project_groups" in tables
    assert "group_comment_logs" in tables
    assert "publish_schedules" in tables
    assert "channels" in tables
    assert "competitors" in tables
    assert "competitor_videos" in tables
    assert "video_jobs" in tables
    assert "publish_logs" in tables

    # Check project_id on all 5 existing models
    assert "project_id" in Channel.__table__.columns
    assert "project_id" in Competitor.__table__.columns
    assert "project_id" in CompetitorVideo.__table__.columns
    assert "project_id" in VideoJob.__table__.columns
    assert "project_id" in PublishLog.__table__.columns

    # Check competitor extensions
    assert "platform" in Competitor.__table__.columns
    assert "scrape_interval_hours" in Competitor.__table__.columns
    assert "platform" in CompetitorVideo.__table__.columns


@pytest.mark.asyncio
async def test_project_crud_and_json_list_keywords(db_session: AsyncSession):
    """Test Project creation, list persistence, and in-place mutation using JSONListType."""
    project = Project(
        project_id="proj_tech_01",
        name="Tech Deals Workspace",
        niche_brief="High-ticket electronics affiliate marketing",
        target_audience="Tech enthusiasts 20-35",
        tone_of_voice="Authoritative and engaging",
        trigger_keywords=["gadget", "unboxing", "review"],
        negative_keywords=["scam", "broken", "fake"],
    )
    db_session.add(project)
    await db_session.commit()

    # Query back and verify
    stmt = select(Project).where(Project.project_id == "proj_tech_01")
    result = await db_session.execute(stmt)
    fetched = result.scalar_one()

    assert fetched.name == "Tech Deals Workspace"
    assert fetched.trigger_keywords == ["gadget", "unboxing", "review"]
    assert fetched.negative_keywords == ["scam", "broken", "fake"]
    assert fetched.created_at is not None

    # Test in-place list mutation with MutableList (JSONListType)
    fetched.trigger_keywords.append("specs")
    fetched.trigger_keywords.extend(["deals", "coupon"])
    fetched.negative_keywords.append("counterfeit")
    fetched.negative_keywords.extend(["damaged", "used"])
    await db_session.commit()

    # Verify mutation persisted
    db_session.expire_all()
    result = await db_session.execute(stmt)
    reloaded = result.scalar_one()
    assert reloaded.trigger_keywords == ["gadget", "unboxing", "review", "specs", "deals", "coupon"]
    assert reloaded.negative_keywords == ["scam", "broken", "fake", "counterfeit", "damaged", "used"]



@pytest.mark.asyncio
async def test_existing_models_backward_compatibility(db_session: AsyncSession):
    """Verify v1.4.0 models instantiate and persist cleanly without project_id (defaults to None)."""
    niche = Niche(niche_id="niche_compat", name="Compatibility Niche")
    db_session.add(niche)
    await db_session.flush()

    # Channel without project_id
    channel = Channel(
        channel_id="chan_compat_01",
        niche_id="niche_compat",
        browser_profile_id="prof_compat_01",
    )
    db_session.add(channel)

    # Competitor without project_id
    competitor = Competitor(
        competitor_id="comp_compat_01",
        niche_id="niche_compat",
        username="viral_reviewer",
        profile_url="https://tiktok.com/@viral_reviewer",
    )
    db_session.add(competitor)
    await db_session.flush()

    # CompetitorVideo without project_id
    comp_video = CompetitorVideo(
        video_id="vid_compat_01",
        competitor_id="comp_compat_01",
        video_url="https://tiktok.com/@viral_reviewer/video/1",
    )
    db_session.add(comp_video)

    # Product and VideoJob without project_id
    product = Product(
        product_id="prod_compat_01",
        niche_id="niche_compat",
        title="Wireless Earbuds",
        price=49.99,
        product_url="https://shop.tiktok.com/p/1",
    )
    db_session.add(product)
    await db_session.flush()

    video_job = VideoJob(
        job_id="job_compat_01",
        product_id="prod_compat_01",
        niche_id="niche_compat",
        channel_id="chan_compat_01",
    )
    db_session.add(video_job)
    await db_session.flush()

    # PublishLog without project_id
    pub_log = PublishLog(
        log_id="pub_compat_01",
        job_id="job_compat_01",
        channel_id="chan_compat_01",
    )
    db_session.add(pub_log)
    await db_session.commit()

    # Assert all project_id values are None and defaults are applied
    assert channel.project_id is None
    assert competitor.project_id is None
    assert competitor.platform == "tiktok"
    assert competitor.scrape_interval_hours == 4
    assert comp_video.project_id is None
    assert comp_video.platform == "tiktok"
    assert video_job.project_id is None
    assert pub_log.project_id is None


@pytest.mark.asyncio
async def test_project_foreign_key_ondelete_set_null(db_session: AsyncSession):
    """Verify deleting a Project sets project_id = NULL on dependent records without cascading delete."""
    project = Project(project_id="proj_parent_01", name="Parent Workspace")
    niche = Niche(niche_id="niche_setnull", name="SetNull Niche")
    db_session.add_all([project, niche])
    await db_session.flush()

    channel = Channel(
        channel_id="chan_sn_01",
        project_id="proj_parent_01",
        niche_id="niche_setnull",
        browser_profile_id="prof_sn_01",
    )
    competitor = Competitor(
        competitor_id="comp_sn_01",
        project_id="proj_parent_01",
        niche_id="niche_setnull",
        username="comp_user",
        profile_url="https://tiktok.com/@comp_user",
    )
    product = Product(
        product_id="prod_sn_01",
        niche_id="niche_setnull",
        title="Smart Watch",
        price=99.0,
        product_url="https://shop.tiktok.com/p/2",
    )
    db_session.add_all([channel, competitor, product])
    await db_session.flush()

    comp_video = CompetitorVideo(
        video_id="vid_sn_01",
        project_id="proj_parent_01",
        competitor_id="comp_sn_01",
        video_url="https://tiktok.com/@comp_user/video/2",
    )
    video_job = VideoJob(
        job_id="job_sn_01",
        project_id="proj_parent_01",
        product_id="prod_sn_01",
        niche_id="niche_setnull",
        channel_id="chan_sn_01",
    )
    db_session.add_all([comp_video, video_job])
    await db_session.flush()

    pub_log = PublishLog(
        log_id="pub_sn_01",
        project_id="proj_parent_01",
        job_id="job_sn_01",
        channel_id="chan_sn_01",
    )
    db_session.add(pub_log)
    await db_session.commit()

    # Delete parent project
    await db_session.delete(project)
    await db_session.commit()

    # Expire session cache to force reload from SQLite with foreign keys enforced
    db_session.expire_all()

    # Verify all records still exist but have project_id set to None
    chan_reloaded = (await db_session.execute(select(Channel).where(Channel.channel_id == "chan_sn_01"))).scalar_one()
    comp_reloaded = (await db_session.execute(select(Competitor).where(Competitor.competitor_id == "comp_sn_01"))).scalar_one()
    vid_reloaded = (await db_session.execute(select(CompetitorVideo).where(CompetitorVideo.video_id == "vid_sn_01"))).scalar_one()
    job_reloaded = (await db_session.execute(select(VideoJob).where(VideoJob.job_id == "job_sn_01"))).scalar_one()
    pub_reloaded = (await db_session.execute(select(PublishLog).where(PublishLog.log_id == "pub_sn_01"))).scalar_one()

    assert chan_reloaded.project_id is None
    assert comp_reloaded.project_id is None
    assert vid_reloaded.project_id is None
    assert job_reloaded.project_id is None
    assert pub_reloaded.project_id is None


@pytest.mark.asyncio
async def test_competitor_scrape_interval_check_constraint(db_session: AsyncSession):
    """Verify Competitor scrape_interval_hours check constraint (>= 2)."""
    niche = Niche(niche_id="niche_chk", name="Check Niche")
    db_session.add(niche)
    await db_session.flush()

    # Valid: scrape_interval_hours == 2 (boundary)
    valid_comp = Competitor(
        competitor_id="comp_valid_02",
        niche_id="niche_chk",
        username="user_2h",
        profile_url="https://tiktok.com/@user_2h",
        scrape_interval_hours=2,
    )
    db_session.add(valid_comp)
    await db_session.commit()
    assert valid_comp.scrape_interval_hours == 2

    # Invalid: scrape_interval_hours == 1 (< 2 violation)
    invalid_comp = Competitor(
        competitor_id="comp_invalid_01",
        niche_id="niche_chk",
        username="user_1h",
        profile_url="https://tiktok.com/@user_1h",
        scrape_interval_hours=1,
    )
    async with db_session.begin_nested():
        db_session.add(invalid_comp)
        with pytest.raises(IntegrityError):
            await db_session.flush()


@pytest.mark.asyncio
async def test_project_group_crud_and_cascade(db_session: AsyncSession):
    """Verify ProjectGroup CRUD, check constraint on privacy, and cascade deletion."""
    project = Project(project_id="proj_grp_01", name="Group Marketing Project")
    db_session.add(project)
    await db_session.flush()

    group = ProjectGroup(
        group_id="grp_fb_101",
        project_id="proj_grp_01",
        group_url="https://facebook.com/groups/affiliates_vn",
        group_name="Vietnamese Affiliate Community",
        privacy="public",
        approval_mode=False,
        is_active=True,
    )
    db_session.add(group)
    await db_session.commit()

    # Verify group fields
    stmt = select(ProjectGroup).where(ProjectGroup.group_id == "grp_fb_101")
    fetched = (await db_session.execute(stmt)).scalar_one()
    assert fetched.group_name == "Vietnamese Affiliate Community"
    assert fetched.approval_mode is False
    assert fetched.is_active is True
    assert fetched.created_at is not None

    # Test invalid privacy check constraint
    invalid_group = ProjectGroup(
        group_id="grp_fb_bad",
        project_id="proj_grp_01",
        group_url="https://facebook.com/groups/secret",
        group_name="Secret Group",
        privacy="secret",  # must be 'public' or 'private'
    )
    async with db_session.begin_nested():
        db_session.add(invalid_group)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    # Test CASCADE delete when Project is deleted
    await db_session.delete(project)
    await db_session.commit()

    db_session.expire_all()
    group_after_delete = (await db_session.execute(stmt)).scalar_one_or_none()
    assert group_after_delete is None


@pytest.mark.asyncio
async def test_group_comment_log_unique_constraint(db_session: AsyncSession):
    """Verify GroupCommentLog UniqueConstraint on (group_id, post_id)."""
    project = Project(project_id="proj_comm_01", name="Comment Marketing Project")
    db_session.add(project)
    await db_session.flush()

    group = ProjectGroup(
        group_id="grp_fb_202",
        project_id="proj_comm_01",
        group_url="https://facebook.com/groups/gadgets",
        group_name="Gadget Fanatics",
    )
    db_session.add(group)
    await db_session.flush()

    # First comment log succeeds
    log1 = GroupCommentLog(
        log_id="log_comm_01",
        group_id="grp_fb_202",
        project_id="proj_comm_01",
        post_id="post_777",
        post_content="Looking for recommended headphones",
        matched_keyword="headphones",
        comment_text="Check out these active noise cancelling earbuds!",
    )
    db_session.add(log1)
    await db_session.commit()

    # Duplicate comment log on same group_id and post_id must raise IntegrityError
    log2_duplicate = GroupCommentLog(
        log_id="log_comm_02",
        group_id="grp_fb_202",
        project_id="proj_comm_01",
        post_id="post_777",  # Duplicate (group_id, post_id)
        comment_text="Another comment attempt",
    )
    async with db_session.begin_nested():
        db_session.add(log2_duplicate)
        with pytest.raises(IntegrityError):
            await db_session.flush()


@pytest.mark.asyncio
async def test_publish_schedule_crud_and_constraints(db_session: AsyncSession):
    """Verify PublishSchedule CRUD, check constraints, and cascade delete on Channel deletion."""
    project = Project(project_id="proj_sched_01", name="Calendar Project")
    niche = Niche(niche_id="niche_sched", name="Calendar Niche")
    db_session.add_all([project, niche])
    await db_session.flush()

    channel = Channel(
        channel_id="chan_sched_01",
        niche_id="niche_sched",
        browser_profile_id="prof_sched_01",
    )
    db_session.add(channel)
    await db_session.flush()

    scheduled_time = datetime(2026, 12, 1, 12, 0, 0, tzinfo=timezone.utc)
    schedule = PublishSchedule(
        schedule_id="sched_item_01",
        project_id="proj_sched_01",
        channel_id="chan_sched_01",
        platform="tiktok",
        target_type="reel",
        title="Top Trending Gadgets Dec 2026",
        caption="Check these out! #tech #gadgets",
        scheduled_at=scheduled_time,
        status="scheduled",
    )
    db_session.add(schedule)
    await db_session.commit()

    # Query back and verify
    stmt = select(PublishSchedule).where(PublishSchedule.schedule_id == "sched_item_01")
    fetched = (await db_session.execute(stmt)).scalar_one()
    assert fetched.title == "Top Trending Gadgets Dec 2026"
    assert fetched.platform == "tiktok"
    assert fetched.target_type == "reel"
    assert fetched.status == "scheduled"
    assert fetched.scheduled_at == scheduled_time

    # Invalid status constraint
    bad_status_schedule = PublishSchedule(
        schedule_id="sched_item_bad_status",
        channel_id="chan_sched_01",
        title="Bad Status",
        scheduled_at=scheduled_time,
        status="completed_invalid",
    )
    async with db_session.begin_nested():
        db_session.add(bad_status_schedule)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    # Invalid platform constraint
    bad_platform_schedule = PublishSchedule(
        schedule_id="sched_item_bad_plat",
        channel_id="chan_sched_01",
        title="Bad Platform",
        scheduled_at=scheduled_time,
        platform="youtube",  # must be tiktok, facebook, or instagram
    )
    async with db_session.begin_nested():
        db_session.add(bad_platform_schedule)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    # Invalid target_type constraint
    bad_target_schedule = PublishSchedule(
        schedule_id="sched_item_bad_target",
        channel_id="chan_sched_01",
        title="Bad Target",
        scheduled_at=scheduled_time,
        target_type="story",  # must be reel, post, or group
    )
    async with db_session.begin_nested():
        db_session.add(bad_target_schedule)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    # Verify CASCADE delete when Channel is deleted
    await db_session.delete(channel)
    await db_session.commit()

    db_session.expire_all()
    schedule_after_delete = (await db_session.execute(stmt)).scalar_one_or_none()
    assert schedule_after_delete is None
