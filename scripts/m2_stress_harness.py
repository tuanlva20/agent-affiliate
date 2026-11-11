"""AMAS v1.4.0 — Empirical Challenger Adversarial Stress Suite for Milestone 2.

Empirically stress-tests:
1. TikTok URL variations, spoofed domains, protocols, shortlinks, trailing slashes.
2. Anchor product extraction edge cases (null itemInfo, corrupted JSON, missing titles/ids).
3. BaseScoutAgent numerical boundaries (NaN, float('inf'), negative, zero, 1.0, 1.0001, None).
"""

from __future__ import annotations

import asyncio
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple
from unittest.mock import patch

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.services.tiktok_scraper import (
    TikTokScraper,
    TikTokVideoMeta,
    TikTokScraperError,
    InvalidTikTokURLError,
)
from src.agents.base_scout import BaseScoutAgent, ProductCandidate
from src.core.config import NicheConfig, FilterThresholds, PersonaConfig


class StressRunner:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0
        self.failures: List[str] = []

    def check(self, name: str, condition: bool, details: str = "") -> None:
        if condition:
            self.passed += 1
            print(f"  [PASS] {name}")
        else:
            self.failed += 1
            msg = f"  [FAIL] {name} - {details}"
            self.failures.append(msg)
            print(msg)


# ===========================================================================
# 1. TikTok URL Variations & Validation Attacks
# ===========================================================================

async def run_tiktok_url_challenges(runner: StressRunner) -> None:
    print("\n=== CHALLENGE SUITE 1: TikTok URL Variations & Boundary Attacks ===")
    scraper = TikTokScraper(mock_mode=True)

    # 1.1 Valid variations that MUST succeed and extract clean ID
    valid_variations = [
        ("Trailing slash", "https://www.tiktok.com/@koc/video/7123456789/", "7123456789"),
        ("Multiple trailing slashes", "https://www.tiktok.com/@koc/video/7123456789///", "7123456789"),
        ("Webapp tracking param", "https://www.tiktok.com/@koc/video/7123456789?is_from_webapp=1", "7123456789"),
        ("Multi-query tracking params", "https://www.tiktok.com/@koc/video/7123456789?is_from_webapp=1&sender_device=pc&share_id=abc", "7123456789"),
        ("Shortlink vm.tiktok.com", "https://vm.tiktok.com/ZMhABCDEF/", "ZMhABCDEF"),
        ("Shortlink vt.tiktok.com", "https://vt.tiktok.com/ZS1234567/", "ZS1234567"),
        ("Bare domain tiktok.com", "https://tiktok.com/@koc/video/7123456789", "7123456789"),
        ("Http scheme", "http://www.tiktok.com/@koc/video/7123456789", "7123456789"),
    ]

    for name, url, expected_id in valid_variations:
        try:
            meta = await scraper.download_video_metadata(url)
            runner.check(
                name,
                meta.video_id == expected_id,
                f"Expected video_id '{expected_id}', got '{meta.video_id}'",
            )
        except Exception as exc:
            runner.check(name, False, f"Unexpected exception: {type(exc).__name__}: {exc}")

    # 1.2 Invalid / Malicious / Evasion URLs that MUST be rejected with InvalidTikTokURLError or ValueError
    invalid_attacks = [
        ("Empty string", ""),
        ("Whitespace only", "   \t\n  "),
        ("NoneType", None),
        ("Integer input", 99887766),
        ("Google domain", "https://google.com/search?q=tiktok"),
        ("Youtube video with tiktok in query", "https://youtube.com/watch?v=123&ref=tiktok.com"),
        ("Attacker domain suffix (.attacker.com)", "https://tiktok.com.attacker.com/video/7123456789"),
        ("Attacker domain prefix (not-tiktok.com)", "https://not-tiktok.com/video/7123456789"),
        ("Javascript pseudo-protocol injection", "javascript:alert('tiktok.com')"),
        ("File URI scheme", "file:///etc/passwd#tiktok.com"),
    ]

    for name, bad_url in invalid_attacks:
        rejected = False
        try:
            await scraper.download_video_metadata(bad_url)  # type: ignore
        except (InvalidTikTokURLError, ValueError):
            rejected = True
        except Exception as exc:
            # Other unhandled exceptions indicate a failure to validate cleanly
            runner.check(name, False, f"Unhandled crash instead of validation rejection: {type(exc).__name__}: {exc}")
            continue

        runner.check(name, rejected is True, f"Security/Validation flaw: Invalid URL '{bad_url}' was accepted as valid!")


# ===========================================================================
# 2. Anchor Product Extraction Edge Cases
# ===========================================================================

def run_anchor_extraction_challenges(runner: StressRunner) -> None:
    print("\n=== CHALLENGE SUITE 2: Anchor Product Extraction Edge Cases ===")
    scraper = TikTokScraper(mock_mode=False)

    # 2.1 Missing anchors list entirely
    info_no_anchors = {
        "id": "vid_no_anchors",
        "anchors": [],
        "description": "Video with absolutely no anchors",
    }
    pid, title = scraper._extract_anchor_from_info(info_no_anchors)
    runner.check("Empty anchors list returns (None, None)", pid is None and title is None)

    # 2.2 Null/None itemInfo key in payload (Testing AttributeError crash)
    info_null_iteminfo = {
        "id": "vid_null_iteminfo",
        "itemInfo": None,
        "description": "Payload with itemInfo: null",
    }
    try:
        pid, title = scraper._extract_anchor_from_info(info_null_iteminfo)
        runner.check("itemInfo: None does not crash with AttributeError", pid is None)
    except AttributeError as exc:
        runner.check("itemInfo: None does not crash with AttributeError", False, f"CRASH: {exc}")
    except Exception as exc:
        runner.check("itemInfo: None does not crash with AttributeError", False, f"Unexpected: {exc}")

    # 2.3 Non-dict itemInfo (list or string)
    info_string_iteminfo = {
        "id": "vid_str_iteminfo",
        "itemInfo": "corrupted_string",
        "description": "Payload with itemInfo string",
    }
    try:
        pid, title = scraper._extract_anchor_from_info(info_string_iteminfo)
        runner.check("itemInfo: string does not crash", pid is None)
    except Exception as exc:
        runner.check("itemInfo: string does not crash", False, f"CRASH: {exc}")

    # 2.4 Corrupted JSON in extra field
    info_corrupted_json = {
        "id": "vid_corrupted_extra",
        "anchors": [
            {
                "type": 1004,
                "id": "anchor_fallback_id",
                "keyword": "Fallback Keyword Title",
                "extra": "{this is not valid JSON : 123",
            }
        ],
    }
    pid, title = scraper._extract_anchor_from_info(info_corrupted_json)
    runner.check(
        "Corrupted JSON in extra falls back to anchor ID and keyword",
        pid == "anchor_fallback_id" and title == "Fallback Keyword Title",
        f"Got pid={pid}, title={title}",
    )

    # 2.5 Extra field is valid JSON but a primitive or list (not a dict)
    info_non_dict_extra = {
        "id": "vid_prim_extra",
        "anchors": [
            {
                "type": 1004,
                "id": "anchor_prim_id",
                "keyword": "Prim Title",
                "extra": "[1, 2, 3]",
            }
        ],
    }
    pid, title = scraper._extract_anchor_from_info(info_non_dict_extra)
    runner.check(
        "Non-dict JSON extra falls back to anchor id/keyword",
        pid == "anchor_prim_id" and title == "Prim Title",
        f"Got pid={pid}, title={title}",
    )

    # 2.6 Anchor missing title / empty keyword
    info_missing_title = {
        "id": "vid_missing_title",
        "anchors": [
            {
                "type": 1004,
                "id": "prod_no_title_123",
                "keyword": "",
                "extra": json.dumps({"product_id": "prod_no_title_123"}),
            }
        ],
    }
    pid, title = scraper._extract_anchor_from_info(info_missing_title)
    runner.check(
        "Missing title in anchor yields None for title",
        pid == "prod_no_title_123" and title is None,
        f"Got pid={pid}, title={title}",
    )

    # 2.7 Anchor in caption regex fallback
    info_caption_anchor = {
        "id": "vid_caption_link",
        "description": "Mua sản phẩm tại https://shop.tiktok.com/view/product/prod_cap_999 ngay nha",
    }
    pid, title = scraper._extract_anchor_from_info(info_caption_anchor)
    runner.check(
        "Caption regex fallback extracts product id",
        pid == "prod_cap_999" and title is None,
        f"Got pid={pid}, title={title}",
    )


# ===========================================================================
# 3. BaseScoutAgent Numerical Boundaries & Edge Cases
# ===========================================================================

async def run_basescout_boundary_challenges(runner: StressRunner) -> None:
    print("\n=== CHALLENGE SUITE 3: BaseScoutAgent Numerical Boundaries & Robustness ===")
    agent = BaseScoutAgent()

    fashion_cfg = NicheConfig(
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

    # 3.1 Numerical boundary inputs
    boundary_cases = [
        # (name, item, expected_pass, reason)
        (
            "Valid standard item",
            {"product_id": "p_valid", "title": "Áo thun", "price": 200000.0, "commission_rate": 0.15},
            True,
            "Meets all thresholds",
        ),
        (
            "Negative price (-100)",
            {"product_id": "p_neg", "title": "Áo thun", "price": -100.0, "commission_rate": 0.15},
            False,
            "Negative price must be rejected",
        ),
        (
            "Zero price (0.0)",
            {"product_id": "p_zero", "title": "Áo thun", "price": 0.0, "commission_rate": 0.15},
            False,
            "Zero price must be rejected",
        ),
        (
            "Float overflow positive infinity (inf)",
            {"product_id": "p_inf", "title": "Áo thun", "price": float("inf"), "commission_rate": 0.15},
            False,
            "Infinity price must be rejected",
        ),
        (
            "Float overflow negative infinity (-inf)",
            {"product_id": "p_ninf", "title": "Áo thun", "price": float("-inf"), "commission_rate": 0.15},
            False,
            "-Infinity price must be rejected",
        ),
        (
            "NaN price float('nan')",
            {"product_id": "p_nan", "title": "Áo thun", "price": float("nan"), "commission_rate": 0.15},
            False,
            "NaN price MUST be rejected",
        ),
        (
            "NaN price string 'nan'",
            {"product_id": "p_nan_str", "title": "Áo thun", "price": "nan", "commission_rate": 0.15},
            False,
            "NaN string price MUST be rejected",
        ),
        (
            "Commission rate = 0.0",
            {"product_id": "p_c0", "title": "Áo thun", "price": 200000.0, "commission_rate": 0.0},
            False,
            "Zero commission must be rejected",
        ),
        (
            "Commission rate = -0.05",
            {"product_id": "p_cneg", "title": "Áo thun", "price": 200000.0, "commission_rate": -0.05},
            False,
            "Negative commission must be rejected",
        ),
        (
            "Commission rate = 1.0 (100% boundary)",
            {"product_id": "p_c1", "title": "Áo thun", "price": 200000.0, "commission_rate": 1.0},
            True,
            "100% commission is valid upper boundary",
        ),
        (
            "Commission rate = 1.0001 (>100%)",
            {"product_id": "p_c10001", "title": "Áo thun", "price": 200000.0, "commission_rate": 1.0001},
            False,
            ">100% commission must be rejected",
        ),
        (
            "Commission rate = NaN",
            {"product_id": "p_cnan", "title": "Áo thun", "price": 200000.0, "commission_rate": float("nan")},
            False,
            "NaN commission MUST be rejected",
        ),
        (
            "Commission rate = +inf",
            {"product_id": "p_cinf", "title": "Áo thun", "price": 200000.0, "commission_rate": float("inf")},
            False,
            "Infinity commission must be rejected",
        ),
        (
            "None price",
            {"product_id": "p_pnone", "title": "Áo thun", "price": None, "commission_rate": 0.15},
            False,
            "None price must be rejected",
        ),
        (
            "None commission",
            {"product_id": "p_cnone", "title": "Áo thun", "price": 200000.0, "commission_rate": None},
            False,
            "None commission must be rejected",
        ),
        (
            "None title",
            {"product_id": "p_tnone", "title": None, "price": 200000.0, "commission_rate": 0.15},
            False,
            "None title must be rejected",
        ),
        (
            "None product_id",
            {"product_id": None, "title": "Áo thun", "price": 200000.0, "commission_rate": 0.15},
            False,
            "None product_id must be rejected",
        ),
        (
            "Empty dictionary",
            {},
            False,
            "Empty dictionary must be rejected",
        ),
        (
            "Non-dict input (None)",
            None,
            False,
            "Non-dict input must be rejected",
        ),
        (
            "Non-dict input (list)",
            ["product_id", "title"],
            False,
            "List input must be rejected",
        ),
    ]

    for name, item, expected, reason in boundary_cases:
        res = agent.filter_product(item, fashion_cfg)  # type: ignore
        runner.check(
            name,
            res == expected,
            f"Expected {expected} ({reason}), got {res}",
        )

    # 3.2 Batch discover_candidates with empty list and invalid elements
    # Empty list
    cands_empty = await agent.discover_candidates("thoi_trang_nu", raw_items=[])
    runner.check("Empty raw_items list returns empty candidates", cands_empty == [])

    # List containing invalid items (None, string, empty dict, valid item, nan item)
    mixed_items = [
        None,
        "not_a_dict",
        {},
        {"product_id": "p_good", "title": "Áo len", "price": 199000.0, "commission_rate": 0.15},
        {"product_id": "p_nan_price", "title": "Áo lỗi", "price": float("nan"), "commission_rate": 0.15},
    ]
    cands_mixed = await agent.discover_candidates("thoi_trang_nu", raw_items=mixed_items)  # type: ignore
    # If NaN is properly rejected, exactly 1 candidate (p_good) should be discovered
    runner.check(
        "Mixed batch filters invalid types and accepts only genuine valid candidates",
        len(cands_mixed) == 1 and cands_mixed[0].product_id == "p_good",
        f"Expected exactly 1 candidate ['p_good'], got {[c.product_id for c in cands_mixed]}",
    )


# ===========================================================================
# Main Execution
# ===========================================================================

async def main() -> None:
    runner = StressRunner()
    await run_tiktok_url_challenges(runner)
    run_anchor_extraction_challenges(runner)
    await run_basescout_boundary_challenges(runner)

    print("\n" + "=" * 60)
    print("EMPIRICAL M2 ADVERSARIAL STRESS TEST SUMMARY")
    print(f"Total Test Cases: {runner.passed + runner.failed}")
    print(f"Passed:           {runner.passed}")
    print(f"Failed / Gaps:    {runner.failed}")
    print("=" * 60)

    if runner.failed > 0:
        print("\nFAILURE DETAILS / VULNERABILITIES DETECTED:")
        for idx, fail in enumerate(runner.failures, 1):
            print(f"{idx}. {fail}")
        sys.exit(1)
    else:
        print("\nALL M2 ADVERSARIAL STRESS CHALLENGES PASSED EMPIRICALLY!")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
