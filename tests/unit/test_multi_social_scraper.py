"""Unit tests for AMAS-14 MultiSocialScraper: canonical IDs, UPSERT dedup, velocity scoring."""

from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Base, Competitor, CompetitorScrapeLog, CompetitorVideo, Niche
from src.database.session import get_async_engine, get_session_factory
from src.services import multi_social_scraper as mss
from src.services.multi_social_scraper import (
    calculate_velocity_score,
    extract_canonical_id,
    ingest_competitor_video,
)

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = get_async_engine(TEST_DB_URL, force_new=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with get_session_factory(TEST_DB_URL)() as session:
        session.add(Niche(niche_id="n1", name="Fashion"))
        session.add(Competitor(competitor_id="c1", niche_id="n1", username="rival",
                               profile_url="https://www.tiktok.com/@rival"))
        await session.commit()
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.parametrize("url,expected", [
    ("https://www.tiktok.com/@rival/video/7431289412345678901?is_from_webapp=1&utm_source=x",
     ("tiktok", "7431289412345678901")),
    ("https://www.instagram.com/reel/C_xyz123/?igsh=abc123", ("instagram", "C_xyz123")),
    ("https://www.instagram.com/p/Bq-9_Az/", ("instagram", "Bq-9_Az")),
    ("https://www.facebook.com/reel/102938475610?mibextid=xyz", ("facebook", "102938475610")),
    ("https://www.facebook.com/shop/videos/556677889900/", ("facebook", "556677889900")),
    ("https://www.facebook.com/watch/?v=998877665544&ref=share", ("facebook", "998877665544")),
])
def test_extract_canonical_id(url, expected):
    assert extract_canonical_id(url) == expected


def test_short_links_ignore_tracking_params():
    a = extract_canonical_id("https://vt.tiktok.com/ZSabc123/?utm_source=copy")
    b = extract_canonical_id("https://vt.tiktok.com/ZSabc123/")
    assert a == b and a[0] == "tiktok"


def test_unsupported_url_rejected():
    with pytest.raises(ValueError):
        extract_canonical_id("https://youtube.com/watch?v=1")


def test_velocity_score_ranks_viral_above_flop():
    viral = calculate_velocity_score(850000, 45000, 1200, 24)
    flop = calculate_velocity_score(500, 5, 0, 48)
    assert viral >= mss.VIRAL_THRESHOLD > flop
    assert 0 <= flop and viral <= 10


@pytest.mark.asyncio
async def test_force_ingest_three_times_creates_single_row(db_session, monkeypatch):
    views = iter([1000, 2000, 3000])

    async def fake_meta(platform, url):
        v = next(views)
        return {"views": v, "likes": v // 10, "comments": 1, "caption": f"v{v}", "hours_since_posted": 24}

    monkeypatch.setattr(mss, "fetch_metadata", fake_meta)
    url = "https://www.tiktok.com/@rival/video/7431289412345678901"
    results = [
        await ingest_competitor_video(db_session, url + f"?utm_source={i}", "c1", force=True)
        for i in range(3)
    ]

    assert [r["is_duplicate_updated"] for r in results] == [False, True, True]
    count = await db_session.scalar(select(func.count()).select_from(CompetitorVideo))
    assert count == 1
    row = await db_session.get(CompetitorVideo, "7431289412345678901")
    assert (row.views_count, row.likes_count, row.caption) == (3000, 300, "v3000")


@pytest.mark.asyncio
async def test_scheduled_run_skips_low_score(db_session, monkeypatch):
    async def flop_meta(platform, url):
        return {"views": 500, "likes": 5, "comments": 0, "caption": "flop", "hours_since_posted": 48}

    monkeypatch.setattr(mss, "fetch_metadata", flop_meta)
    url = "https://www.instagram.com/reel/C_flop1/"

    res = await ingest_competitor_video(db_session, url, "c1", force=False)
    assert res["skipped_low_score"] and not res["stored"]
    assert await db_session.get(CompetitorVideo, "C_flop1") is None
    log = (await db_session.execute(select(CompetitorScrapeLog))).scalars().one()
    assert log.status == "skipped_low_score"

    forced = await ingest_competitor_video(db_session, url, "c1", force=True)
    assert forced["stored"]
    row = await db_session.get(CompetitorVideo, "C_flop1")
    assert row.platform == "instagram"


@pytest.mark.asyncio
async def test_mock_metadata_paths_store_viral_posts(db_session):
    for url in ("https://www.tiktok.com/@rival/video/111",
                "https://www.facebook.com/reel/222",
                "https://www.instagram.com/reel/C333/"):
        res = await ingest_competitor_video(db_session, url, "c1", project_id=None, force=False)
        assert res["stored"], res


@pytest.mark.asyncio
async def test_cached_file_skips_download(tmp_path, monkeypatch):
    monkeypatch.setattr(mss, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(mss, "MOCK_MODE", False)
    (tmp_path / "tiktok_123.mp4").write_bytes(b"x")
    path, downloaded = await mss.ensure_cached_video("tiktok", "123", "https://www.tiktok.com/@a/video/123")
    assert path.exists() and downloaded is False
