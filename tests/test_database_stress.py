"""Empirical stress test suite for AMAS v1.4.0 database layer.

Adversarial stress testing covering:
1. High-concurrency async operations (50 parallel coroutines, data integrity, pool leaks, isolation)
2. JSON/JSONB boundary stress (deep nesting, large payload, unicode emoji, in-place mutation)
3. Cascade delete tests (ORM delete and bulk SQL statement delete)
4. Lifecycle state machine stress (valid transitions and invalid state rejection)
"""

import asyncio
import os
import pytest
from datetime import datetime, timezone
from typing import AsyncGenerator
from sqlalchemy import select, delete, func
from sqlalchemy.exc import IntegrityError, DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    Base,
    Niche,
    Channel,
    Competitor,
    Product,
    VideoJob,
    VideoComment,
    Metric,
)
from src.database.session import get_async_engine, get_session_factory, get_db

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def engine():
    return get_async_engine(TEST_DB_URL, force_new=True)


@pytest.fixture(scope="function")
async def init_stress_db(engine):
    """Initializes a fresh schema for each stress test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ==============================================================================
# DIMENSION 1: HIGH CONCURRENCY ASYNC OPERATIONS (50 PARALLEL COROUTINES)
# ==============================================================================


@pytest.mark.asyncio
async def test_concurrency_50_parallel_coroutines_data_integrity(init_stress_db):
    """Stress Test 1.1: 50 parallel coroutines writing and reading channels, products, and video jobs via get_db().

    Expectation: Clean isolation, zero connection pool leaks, zero locked errors,
    and 100% data integrity (50 channels, 50 products, 50 video jobs persisted).
    """
    # Seed parent niche
    async with get_db() as db:
        db.add(Niche(niche_id="niche_conc_50", name="Concurrency Test Niche"))

    async def worker_pipeline(idx: int):
        # Phase 1: Write channel and product in parallel
        async with get_db() as db:
            ch = Channel(
                channel_id=f"chan_conc_{idx:03d}",
                niche_id="niche_conc_50",
                browser_profile_id=f"prof_conc_{idx:03d}",
                lifecycle_status="warming",
                warmup_days_completed=idx % 7,
            )
            prod = Product(
                product_id=f"prod_conc_{idx:03d}",
                niche_id="niche_conc_50",
                title=f"Concurrent Product {idx}",
                price=99.0 + idx,
                product_url=f"https://shop.tiktok.com/item/{idx:03d}",
                status="pending",
            )
            db.add_all([ch, prod])

        # Phase 2: Read product and channel in parallel, create VideoJob
        async with get_db() as db:
            p = await db.get(Product, f"prod_conc_{idx:03d}")
            if p is None:
                raise ValueError(
                    f"Product prod_conc_{idx:03d} missing! Silent data loss detected."
                )

            job = VideoJob(
                job_id=f"job_conc_{idx:03d}",
                product_id=p.product_id,
                niche_id="niche_conc_50",
                channel_id=f"chan_conc_{idx:03d}",
                status="created",
            )
            db.add(job)

    # Launch 50 concurrent worker coroutines
    tasks = [worker_pipeline(i) for i in range(50)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    exceptions = [r for r in results if isinstance(r, Exception)]

    # Collect persisted rows
    async with get_db() as db:
        saved_channels = (await db.execute(select(Channel))).scalars().all()
        saved_products = (await db.execute(select(Product))).scalars().all()
        saved_jobs = (await db.execute(select(VideoJob))).scalars().all()

    # Assertions
    assert len(exceptions) == 0, f"50 coroutines had {len(exceptions)} failures: {exceptions[:3]}"
    assert len(saved_channels) == 50, f"Expected 50 channels, found {len(saved_channels)}"
    assert len(saved_products) == 50, f"Expected 50 products, found {len(saved_products)}"
    assert len(saved_jobs) == 50, f"Expected 50 video jobs, found {len(saved_jobs)}"


@pytest.mark.asyncio
async def test_concurrency_transaction_isolation_and_cross_pollution(init_stress_db):
    """Stress Test 1.2: Verify ACID isolation between concurrent transactions.

    A rolling-back worker must NOT roll back a concurrent committing worker's work,
    and a committing worker must NOT commit uncommitted changes of another worker.
    """
    async with get_db() as db:
        db.add(Niche(niche_id="niche_iso", name="Isolation Test Niche"))

    async def worker_dirty_rollback():
        try:
            async with get_db() as db:
                db.add(
                    Product(
                        product_id="prod_dirty_uncommitted",
                        niche_id="niche_iso",
                        title="Dirty Product",
                        price=1.0,
                        product_url="http://dirty.com",
                    )
                )
                await db.flush()
                await asyncio.sleep(0.04)
                raise RuntimeError("Worker intentional abort for rollback")
        except RuntimeError:
            pass

    async def worker_clean_commit():
        await asyncio.sleep(0.01)
        async with get_db() as db:
            db.add(
                Product(
                    product_id="prod_valid_committed",
                    niche_id="niche_iso",
                    title="Valid Product",
                    price=2.0,
                    product_url="http://valid.com",
                )
            )
            await db.flush()
            await asyncio.sleep(0.05)

    await asyncio.gather(worker_dirty_rollback(), worker_clean_commit())

    async with get_db() as db:
        dirty_prod = await db.get(Product, "prod_dirty_uncommitted")
        valid_prod = await db.get(Product, "prod_valid_committed")

    # The dirty uncommitted product must NOT have been committed
    assert (
        dirty_prod is None
    ), "Transaction isolation failure: Dirty uncommitted data was persisted by concurrent commit!"
    # The valid product MUST have been committed
    assert (
        valid_prod is not None
    ), "Transaction isolation failure: Valid worker's commit was rolled back by concurrent abort!"


# ==============================================================================
# DIMENSION 2: JSON/JSONB BOUNDARY STRESS
# ==============================================================================


@pytest.mark.asyncio
async def test_json_in_place_mutation_persistence(init_stress_db):
    """Stress Test 2.1: In-place JSON dictionary and list mutations.

    Modifying `product.evaluation_data['score'] = 9.9` or `evaluation_data['pros'].append(...)`
    in-place must be tracked and persisted by SQLAlchemy unit-of-work.
    """
    async with get_db() as db:
        db.add(Niche(niche_id="niche_json_mut", name="JSON Mutation Niche"))
        prod = Product(
            product_id="prod_json_mut_01",
            niche_id="niche_json_mut",
            title="Initial JSON Product",
            price=150.0,
            product_url="http://shop.com/1",
            evaluation_data={
                "score": 6.0,
                "passed_filter": False,
                "tags": ["initial_tag"],
            },
        )
        db.add(prod)

    # Session 2: Retrieve and perform IN-PLACE mutations on evaluation_data
    async with get_db() as db:
        p = await db.get(Product, "prod_json_mut_01")
        assert p is not None
        p.evaluation_data["score"] = 9.8
        p.evaluation_data["passed_filter"] = True
        p.evaluation_data["tags"].append("mutated_tag")
        # Note: We deliberately do NOT reassign `p.evaluation_data = dict(...)`

    # Session 3: Verify whether in-place mutation survived or was silently dropped
    async with get_db() as db:
        reloaded = await db.get(Product, "prod_json_mut_01")
        assert reloaded is not None
        assert reloaded.evaluation_data["score"] == 9.8, (
            f"In-place mutation dropped! Expected 9.8, got {reloaded.evaluation_data.get('score')}. "
            "JSONType lacks MutableDict.as_mutable() wrapper."
        )
        assert reloaded.evaluation_data["passed_filter"] is True
        assert "mutated_tag" in reloaded.evaluation_data["tags"]


@pytest.mark.asyncio
async def test_json_boundaries_deep_nesting_large_payload_and_unicode(init_stress_db):
    """Stress Test 2.2: Deep nesting (60 levels), 2MB payload, and complex Unicode/Emoji characters."""
    async with get_db() as db:
        db.add(Niche(niche_id="niche_json_bound", name="JSON Boundary Niche"))

    # 1. 60 levels deeply nested structure
    deep_dict = {"depth": 60, "marker": "deepest_leaf"}
    for level in range(59, -1, -1):
        deep_dict = {"level": level, "child": deep_dict}

    # 2. Large 2MB payload
    large_payload = {
        "blob": "X" * (2 * 1024 * 1024),
        "size_bytes": 2 * 1024 * 1024,
    }

    # 3. Unicode emoji, Asian characters, Vietnamese diacritics, and escaping
    unicode_payload = {
        "vietnamese_hook": "Áo croptop lụa dáng ôm tôn vòng 1 & eo thon cực phẩm 👗🇻🇳",
        "emojis": "🔥🚀👗💄📦🛒🎉✨⚡️💯",
        "escapes": 'Line 1\nLine 2\t"Tabbed"\\Escaped',
        "multi_lang": "日本語テスト / 韓文테스트 / Arabic العربية",
    }

    async with get_db() as db:
        p_deep = Product(
            product_id="prod_deep_json",
            niche_id="niche_json_bound",
            title="Deep JSON Product",
            price=10.0,
            product_url="http://deep.com",
            evaluation_data=deep_dict,
        )
        p_large = Product(
            product_id="prod_large_json",
            niche_id="niche_json_bound",
            title="Large JSON Product",
            price=20.0,
            product_url="http://large.com",
            evaluation_data=large_payload,
        )
        p_unicode = Product(
            product_id="prod_unicode_json",
            niche_id="niche_json_bound",
            title="Unicode JSON Product",
            price=30.0,
            product_url="http://unicode.com",
            evaluation_data=unicode_payload,
        )
        db.add_all([p_deep, p_large, p_unicode])

    # Clean session verification
    async with get_db() as db:
        res_deep = await db.get(Product, "prod_deep_json")
        curr = res_deep.evaluation_data
        for l in range(60):
            assert curr["level"] == l
            curr = curr["child"]
        assert curr["marker"] == "deepest_leaf"

        res_large = await db.get(Product, "prod_large_json")
        assert len(res_large.evaluation_data["blob"]) == 2 * 1024 * 1024

        res_uni = await db.get(Product, "prod_unicode_json")
        assert "👗🇻🇳" in res_uni.evaluation_data["vietnamese_hook"]
        assert res_uni.evaluation_data["emojis"] == "🔥🚀👗💄📦🛒🎉✨⚡️💯"
        assert "\t" in res_uni.evaluation_data["escapes"]


# ==============================================================================
# DIMENSION 3: CASCADE DELETE TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_cascade_delete_orm_niche_and_product(init_stress_db):
    """Stress Test 3.1: ORM-level cascade delete:

    - Deleting Niche cascades to Channels and Products.
    - Deleting Product cascades to VideoJobs.
    """
    async with get_db() as db:
        niche = Niche(niche_id="niche_casc_orm", name="Cascade Niche")
        chan = Channel(
            channel_id="chan_casc_orm_1",
            niche_id="niche_casc_orm",
            browser_profile_id="prof_casc_orm_1",
        )
        prod = Product(
            product_id="prod_casc_orm_1",
            niche_id="niche_casc_orm",
            title="Cascade Product",
            price=80.0,
            product_url="http://casc.com",
        )
        db.add_all([niche, chan, prod])
        await db.flush()

        job = VideoJob(
            job_id="job_casc_orm_1",
            product_id="prod_casc_orm_1",
            niche_id="niche_casc_orm",
            channel_id="chan_casc_orm_1",
        )
        db.add(job)

    # Step 1: Delete Product via ORM
    async with get_db() as db:
        p = await db.get(Product, "prod_casc_orm_1")
        await db.delete(p)

    # Verify Product and VideoJob are gone
    async with get_db() as db:
        assert await db.get(Product, "prod_casc_orm_1") is None
        assert await db.get(VideoJob, "job_casc_orm_1") is None

    # Step 2: Delete Niche via ORM
    async with get_db() as db:
        n = await db.get(Niche, "niche_casc_orm")
        await db.delete(n)

    # Verify Niche and Channel are gone
    async with get_db() as db:
        assert await db.get(Niche, "niche_casc_orm") is None
        assert await db.get(Channel, "chan_casc_orm_1") is None


@pytest.mark.asyncio
async def test_cascade_delete_database_level_bulk_sql(init_stress_db):
    """Stress Test 3.2: Database-level foreign key cascade on bulk/raw SQL DELETE.

    When raw DELETE FROM niches WHERE niche_id = ... is executed,
    foreign key ON DELETE CASCADE must cleanly delete dependent channels and products.
    """
    async with get_db() as db:
        db.add(Niche(niche_id="niche_bulk_sql", name="Bulk SQL Cascade Niche"))
        await db.flush()
        db.add(
            Channel(
                channel_id="chan_bulk_sql",
                niche_id="niche_bulk_sql",
                browser_profile_id="prof_bulk_sql",
            )
        )
        db.add(
            Product(
                product_id="prod_bulk_sql",
                niche_id="niche_bulk_sql",
                title="Bulk SQL Prod",
                price=50.0,
                product_url="http://bulk.com",
            )
        )

    # Bulk delete statement
    async with get_db() as db:
        await db.execute(delete(Niche).where(Niche.niche_id == "niche_bulk_sql"))

    # Verify dependent entities
    async with get_db() as db:
        n = await db.get(Niche, "niche_bulk_sql")
        ch = await db.get(Channel, "chan_bulk_sql")
        pr = await db.get(Product, "prod_bulk_sql")

        assert n is None, "Niche was not deleted by bulk statement"
        assert ch is None, (
            "Database-level CASCADE failed! Channel orphaned after Niche bulk delete. "
            "SQLite foreign_keys PRAGMA is not enabled on connection."
        )
        assert pr is None, (
            "Database-level CASCADE failed! Product orphaned after Niche bulk delete. "
            "SQLite foreign_keys PRAGMA is not enabled on connection."
        )


# ==============================================================================
# DIMENSION 4: LIFECYCLE STATE MACHINE STRESS
# ==============================================================================


@pytest.mark.asyncio
async def test_lifecycle_all_valid_states_progression(init_stress_db):
    """Stress Test 4.1: Verify all 4 Channel lifecycle states per spec:

    'warming', 'ready_to_post', 'cooldown', 'captcha_blocked'.
    """
    VALID_STATES = ["warming", "ready_to_post", "cooldown", "captcha_blocked"]

    async with get_db() as db:
        db.add(Niche(niche_id="niche_valid_lc", name="Valid LC Niche"))

    for state in VALID_STATES:
        chan_id = f"chan_state_{state}"
        async with get_db() as db:
            ch = Channel(
                channel_id=chan_id,
                niche_id="niche_valid_lc",
                browser_profile_id=f"prof_{state}",
                lifecycle_status=state,
            )
            db.add(ch)

        async with get_db() as db:
            saved = await db.get(Channel, chan_id)
            assert saved is not None
            assert saved.lifecycle_status == state


@pytest.mark.asyncio
async def test_lifecycle_invalid_state_rejection_guard(init_stress_db):
    """Stress Test 4.2: Verify rejection of invalid Channel lifecycle states.

    The model or database constraint must reject unauthorized lifecycle states:
    e.g. 'banned', 'active', 'random_string', '', None.
    """
    INVALID_STATES = ["banned", "active", "UNKNOWN_STATUS", ""]

    async with get_db() as db:
        db.add(Niche(niche_id="niche_inv_lc", name="Invalid LC Niche"))

    for inv in INVALID_STATES:
        with pytest.raises((ValueError, IntegrityError, DBAPIError)):
            async with get_db() as db:
                ch = Channel(
                    channel_id=f"chan_inv_{inv}",
                    niche_id="niche_inv_lc",
                    browser_profile_id=f"prof_inv_{inv}",
                    lifecycle_status=inv,
                )
                db.add(ch)
                await db.flush()
