"""AMAS v1.4.0 — Base Scout Agent & ProductCandidate Unit Test Suite (Feature F07).

Tests quantitative filtering (price, commission rate, boundaries), niche discrimination,
dataclass serialization, database model generation, and autonomous Kalodata integration.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.agents.base_scout import BaseScoutAgent, ProductCandidate
from src.core.config import FilterThresholds, NicheConfig, PersonaConfig
from src.database.models import Product


# ---------------------------------------------------------------------------
# 1. ProductCandidate Dataclass Tests
# ---------------------------------------------------------------------------

def test_product_candidate_dataclass_methods():
    raw_sample = {
        "product_id": "prod_dress_101",
        "title": "Váy hoa nhí dáng xòe chiết eo hack dáng",
        "price": 189000.0,
        "commission_rate": 0.15,
        "sales_30d": 1500,
        "revenue_30d": 283500000.0,
        "product_url": "https://shop.tiktok.com/view/product/prod_dress_101",
        "image_url": "https://p16.tiktokcdn.com/img101.jpg",
        "rating": 4.85,
    }

    candidate = ProductCandidate.from_raw_dict(raw_sample, niche_id="thoi_trang_nu")
    assert candidate.product_id == "prod_dress_101"
    assert candidate.niche_id == "thoi_trang_nu"
    assert candidate.price_vnd == 189000.0
    assert candidate.commission_rate == 0.15
    assert candidate.sales_30d == 1500
    assert candidate.image_url == "https://p16.tiktokcdn.com/img101.jpg"

    # Test to_dict
    d = candidate.to_dict()
    assert d["product_id"] == "prod_dress_101"
    assert d["price_vnd"] == 189000.0
    assert d["commission_rate"] == 0.15

    # Test to_db_product
    db_product = candidate.to_db_product(status="pending")
    assert isinstance(db_product, Product)
    assert db_product.product_id == "prod_dress_101"
    assert db_product.niche_id == "thoi_trang_nu"
    assert db_product.price == 189000.0
    assert db_product.commission_rate == 0.15
    assert db_product.rating == 4.85
    assert db_product.status == "pending"
    assert db_product.evaluation_data["revenue_30d"] == 283500000.0


# ---------------------------------------------------------------------------
# 2. Base Scout Filtering Tests (Women's Fashion & Home Life)
# ---------------------------------------------------------------------------

def test_base_scout_filtering_fashion_valid():
    agent = BaseScoutAgent()
    niche_cfg = NicheConfig(
        niche_id="thoi_trang_nu",
        name="Thời Trang Nữ",
        telegram_topic_id=101,
        persona=PersonaConfig(role="koc", tone="friendly"),
        thresholds=FilterThresholds(
            min_price=99000.0,
            max_price=650000.0,
            min_commission_rate=0.10,
        ),
    )

    valid_item = {
        "product_id": "fashion_01",
        "title": "Chân váy chữ A dáng dài",
        "price": 199000.0,
        "commission_rate": 0.15,
    }
    assert agent.filter_product(valid_item, niche_cfg) is True


def test_base_scout_filtering_price_boundaries():
    agent = BaseScoutAgent()
    niche_cfg = NicheConfig(
        niche_id="thoi_trang_nu",
        name="Thời Trang Nữ",
        telegram_topic_id=101,
        persona=PersonaConfig(role="koc", tone="friendly"),
        thresholds=FilterThresholds(
            min_price=99000.0,
            max_price=650000.0,
            min_commission_rate=0.10,
        ),
    )

    # Below minimum price (70k < 99k)
    too_cheap = {"product_id": "p1", "title": "Tất vớ nữ", "price": 70000.0, "commission_rate": 0.15}
    assert agent.filter_product(too_cheap, niche_cfg) is False

    # Above maximum price (700k > 650k)
    too_expensive = {"product_id": "p2", "title": "Áo khoác dạ xịn", "price": 700000.0, "commission_rate": 0.15}
    assert agent.filter_product(too_expensive, niche_cfg) is False

    # Exact boundary price values
    exact_min = {"product_id": "p3", "title": "Áo croptop basic", "price": 99000.0, "commission_rate": 0.10}
    assert agent.filter_product(exact_min, niche_cfg) is True

    exact_max = {"product_id": "p4", "title": "Đầm dạ hội cao cấp", "price": 650000.0, "commission_rate": 0.10}
    assert agent.filter_product(exact_max, niche_cfg) is True

    # Zero and negative price
    zero_price = {"product_id": "p5", "title": "Miễn phí", "price": 0.0, "commission_rate": 0.15}
    assert agent.filter_product(zero_price, niche_cfg) is False

    neg_price = {"product_id": "p6", "title": "Giá âm", "price": -50000.0, "commission_rate": 0.15}
    assert agent.filter_product(neg_price, niche_cfg) is False

    # Extreme high price
    extreme_price = {"product_id": "p7", "title": "Siêu đắt", "price": 99999999999.0, "commission_rate": 0.15}
    assert agent.filter_product(extreme_price, niche_cfg) is False


def test_base_scout_filtering_commission_boundaries():
    agent = BaseScoutAgent()
    niche_cfg = NicheConfig(
        niche_id="thoi_trang_nu",
        name="Thời Trang Nữ",
        telegram_topic_id=101,
        persona=PersonaConfig(role="koc", tone="friendly"),
        thresholds=FilterThresholds(
            min_price=99000.0,
            max_price=650000.0,
            min_commission_rate=0.10,
        ),
    )

    # Below minimum commission (5% < 10%)
    low_comm = {"product_id": "c1", "title": "Đầm suông", "price": 200000.0, "commission_rate": 0.05}
    assert agent.filter_product(low_comm, niche_cfg) is False

    # Zero commission
    zero_comm = {"product_id": "c2", "title": "Đầm suông", "price": 200000.0, "commission_rate": 0.0}
    assert agent.filter_product(zero_comm, niche_cfg) is False

    # Excessive commission outlier (> 100%, e.g. 150%)
    excessive_comm = {"product_id": "c3", "title": "Đầm suông", "price": 200000.0, "commission_rate": 1.50}
    assert agent.filter_product(excessive_comm, niche_cfg) is False


def test_base_scout_niche_discrimination():
    agent = BaseScoutAgent()
    # 60,000 VND and 13% commission:
    # Passes Home Utilities (min 49k, min 12%)
    # Fails Women's Fashion (min 99k, min 10%)
    item = {"product_id": "util_01", "title": "Dụng cụ gọt củ quả", "price": 60000.0, "commission_rate": 0.13}

    home_cfg = NicheConfig(
        niche_id="do_gia_dung",
        name="Đồ Gia Dụng",
        telegram_topic_id=102,
        persona=PersonaConfig(role="koc", tone="friendly"),
        thresholds=FilterThresholds(min_price=49000.0, max_price=1200000.0, min_commission_rate=0.12),
    )
    fashion_cfg = NicheConfig(
        niche_id="thoi_trang_nu",
        name="Thời Trang Nữ",
        telegram_topic_id=101,
        persona=PersonaConfig(role="koc", tone="friendly"),
        thresholds=FilterThresholds(min_price=99000.0, max_price=650000.0, min_commission_rate=0.10),
    )

    assert agent.filter_product(item, home_cfg) is True
    assert agent.filter_product(item, fashion_cfg) is False


def test_base_scout_invalid_or_missing_keys():
    agent = BaseScoutAgent()
    assert agent.filter_product("not a dict") is False  # type: ignore
    assert agent.filter_product({}) is False
    assert agent.filter_product({"product_id": "p1"}) is False
    assert agent.filter_product({"title": "Test product"}) is False
    assert agent.filter_product({"product_id": "p1", "title": "T", "price": "invalid", "commission_rate": 0.15}) is False
    assert agent.filter_product({"product_id": "p1", "title": "T", "price": 100000.0, "commission_rate": "invalid"}) is False


def test_base_scout_nan_inf_and_whitespace():
    agent = BaseScoutAgent()
    # NaN and Inf price/commission
    assert agent.filter_product({"product_id": "p1", "title": "T", "price": float("nan"), "commission_rate": 0.15}) is False
    assert agent.filter_product({"product_id": "p1", "title": "T", "price": "nan", "commission_rate": 0.15}) is False
    assert agent.filter_product({"product_id": "p1", "title": "T", "price": 100000.0, "commission_rate": float("nan")}) is False
    assert agent.filter_product({"product_id": "p1", "title": "T", "price": float("inf"), "commission_rate": 0.15}) is False
    assert agent.filter_product({"product_id": "p1", "title": "T", "price": 100000.0, "commission_rate": float("inf")}) is False

    # Whitespace only product_id or title
    assert agent.filter_product({"product_id": "   ", "title": "T", "price": 100000.0, "commission_rate": 0.15}) is False
    assert agent.filter_product({"product_id": "p1", "title": "   ", "price": 100000.0, "commission_rate": 0.15}) is False
    assert agent.filter_product({"product_id": "\t\n", "title": " \r ", "price": 100000.0, "commission_rate": 0.15}) is False

    # ProductCandidate string float sales coercion
    cand = ProductCandidate.from_raw_dict(
        {"product_id": "p1", "title": "T", "price": 100000.0, "commission_rate": 0.15, "sales_30d": "1500.0"},
        "thoi_trang_nu",
    )
    assert cand.sales_30d == 1500


# ---------------------------------------------------------------------------
# 3. Batch Discovery & Autonomous Mode Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_base_scout_discover_candidates_batch():
    agent = BaseScoutAgent()
    raw_items = [
        {"product_id": "p1", "title": "Váy hợp lệ", "price": 150000.0, "commission_rate": 0.15},
        {"product_id": "p2", "title": "Váy quá rẻ", "price": 50000.0, "commission_rate": 0.15},
        {"product_id": "p3", "title": "Váy hoa xịn", "price": 250000.0, "commission_rate": 0.12},
    ]

    candidates = await agent.discover_candidates(niche_id="thoi_trang_nu", raw_items=raw_items)
    assert len(candidates) == 2
    assert candidates[0].product_id == "p1"
    assert candidates[1].product_id == "p3"
    assert candidates[0].niche_id == "thoi_trang_nu"


@pytest.mark.asyncio
async def test_base_scout_discover_candidates_autonomous():
    mock_kalo = AsyncMock()
    mock_kalo.get_top_products = AsyncMock(return_value=[
        {
            "product_id": "kalo_auto_01",
            "title": "Nồi chiên không dầu thông minh",
            "price": 650000.0,
            "commission_rate": 0.15,
            "sales_30d": 2000,
            "revenue_30d": 1300000000.0,
            "product_url": "https://shop.tiktok.com/view/product/kalo_auto_01",
        }
    ])

    agent = BaseScoutAgent(kalodata_client=mock_kalo)
    candidates = await agent.discover_candidates(niche_id="do_gia_dung")

    assert len(candidates) == 1
    assert candidates[0].product_id == "kalo_auto_01"
    assert candidates[0].price_vnd == 650000.0
    mock_kalo.get_top_products.assert_called()
