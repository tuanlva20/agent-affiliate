#!/usr/bin/env python3
"""Empirical Adversarial Stress Harness for Milestone 7 (CommentScanner & CommentAgent).

AMAS v1.4.0 — Target Components:
- src/services/comment_scanner.py (Feature F26: CommentScanner & DB sync)
- src/agents/comment_agent.py (Feature F27: CommentAgent & CommentIntent classification)

Adversarial Stress Dimensions:
1. CommentScanner Robustness & Limit Boundary:
   - Extreme inputs: empty strings, whitespace, unicode emojis, huge strings (10k+ chars), non-string inputs.
   - Limit boundary testing: limit=0, limit=-1, limit=-100, limit=1000.
   - Malformed DB sync payload: missing keys, None values, NaN/overflow timestamps, huge comments.
   - High concurrency: 25 concurrent scans, 25 concurrent database syncs.
   - Intra-batch duplicate comment insertions: verify deduplication and clean SQLite flush.
2. CommentAgent.classify_intent Adversarial Stress:
   - Slang & teen code: 'bnhiu z sop', 'mấy xèng', 'rổ rá', 'vải gì dợ', 'm7 50kg vừa hơm', 'đắt wa ko giống video', 'shop lừa à'.
   - Homograph traps: 'bụng' vs 'bung chỉ', 'lâu' vs 'lau nhà', 'lụa' vs 'lừa đảo', 'hong' vs 'hỏng'.
   - Multi-intent priority: ensure comments with mixed signals (e.g. 'áo rách rồi, giá thì đắt mà ship lâu quá') are ALWAYS classified as COMPLAINT.
   - False-positive guards: ensure 'đánh giá 5 sao', 'giá như biết sớm', 'cái giá treo quần áo này' do NOT falsely trigger ASK_PRICE.
3. Crash & Exception Resilience Guarantee:
   - 0 unhandled exceptions or crashes across all extreme, non-string, and malformed inputs.
   - 100% ToneValidator compliance on all generated replies.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import logging
import math
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.agents.comment_agent import CommentAgent, CommentIntent
from src.core.tone_validator import ToneValidator
from src.database.models import Base, Channel, Niche, VideoComment
from src.services.comment_scanner import (
    CommentRateLimitError,
    CommentScanner,
    CommentScannerError,
    CommentScannerTimeoutError,
    InvalidVideoIdError,
    VideoNotFoundError,
    extract_video_id,
    parse_timestamp,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("m7_adversarial_harness")


# ==============================================================================
# Test Result Tracking
# ==============================================================================

@dataclass
class TestResult:
    category: str
    name: str
    passed: bool
    details: str
    error: Optional[str] = None


@dataclass
class SuiteSummary:
    total: int = 0
    passed: int = 0
    failed: int = 0
    results: List[TestResult] = field(default_factory=list)

    def record(self, category: str, name: str, passed: bool, details: str, error: Optional[str] = None) -> None:
        self.total += 1
        if passed:
            self.passed += 1
            print(f"  [PASS] {category} :: {name} -> {details}")
        else:
            self.failed += 1
            print(f"  [FAIL] {category} :: {name} -> {details} (Error: {error})")
        self.results.append(TestResult(category, name, passed, details, error))


# ==============================================================================
# Suite 1: CommentScanner Robustness & Limit Boundary Testing
# ==============================================================================

async def run_suite_1_scanner(summary: SuiteSummary) -> None:
    print("\n" + "=" * 70)
    print("SUITE 1: CommentScanner Robustness, Boundaries, and Database Sync")
    print("=" * 70)

    scanner = CommentScanner(mock_mode=True)

    # 1.1 Extreme video ID inputs
    invalid_ids = [
        ("", "empty string"),
        ("   ", "whitespace only"),
        ("\t\r\n", "newline and tab"),
        (None, "None type"),
        (123456789, "integer type"),
        (99.99, "float type"),
        (["tt_vid_1"], "list type"),
        ({"video_id": "tt_123"}, "dict type"),
    ]

    for val, label in invalid_ids:
        try:
            await scanner.scan_comments(val)  # type: ignore
            summary.record(
                "Scanner-ExtremeInput",
                f"Invalid Video ID ({label})",
                False,
                f"Expected InvalidVideoIdError for {val!r}, but returned normally",
            )
        except InvalidVideoIdError:
            summary.record(
                "Scanner-ExtremeInput",
                f"Invalid Video ID ({label})",
                True,
                "Correctly raised InvalidVideoIdError",
            )
        except Exception as e:
            summary.record(
                "Scanner-ExtremeInput",
                f"Invalid Video ID ({label})",
                False,
                f"Raised unexpected exception {type(e).__name__}: {e}",
                str(e),
            )

    # 1.2 Extreme but valid inputs (emojis, huge strings, URLs)
    try:
        emoji_res = await scanner.scan_comments("🎉🔥🚀_tt_video", limit=5)
        summary.record(
            "Scanner-ExtremeInput",
            "Unicode Emoji Video ID",
            len(emoji_res) == 5 and all("c_🎉🔥🚀_tt_video_" in c["comment_id"] for c in emoji_res),
            f"Returned {len(emoji_res)} mock comments for emoji ID",
        )
    except Exception as e:
        summary.record("Scanner-ExtremeInput", "Unicode Emoji Video ID", False, "Crashed on emoji ID", str(e))

    try:
        huge_id = "vid_" + ("a" * 5000)
        huge_res = await scanner.scan_comments(huge_id, limit=3)
        summary.record(
            "Scanner-ExtremeInput",
            "Huge Video ID (5000 chars)",
            len(huge_res) == 3,
            f"Returned {len(huge_res)} comments without memory or processing failure",
        )
    except Exception as e:
        summary.record("Scanner-ExtremeInput", "Huge Video ID", False, "Crashed on huge ID", str(e))

    try:
        url_id = "https://www.tiktok.com/@creator_vn/video/7391827461928374612?is_from_webapp=1&sender_device=pc"
        url_res = await scanner.scan_comments(url_id, limit=4)
        summary.record(
            "Scanner-ExtremeInput",
            "Full TikTok URL with Query Params",
            len(url_res) == 4 and "7391827461928374612" in url_res[0]["comment_id"],
            "Successfully extracted clean video ID and generated comments",
        )
    except Exception as e:
        summary.record("Scanner-ExtremeInput", "Full TikTok URL with Query Params", False, "Crashed on URL parsing", str(e))

    # 1.3 Limit boundary testing
    boundary_cases = [
        (0, 0, "limit = 0"),
        (-1, 0, "limit = -1"),
        (-100, 0, "limit = -100"),
        (1000, 1000, "limit = 1000 (stress)"),
    ]

    for limit_val, exp_len, label in boundary_cases:
        try:
            res = await scanner.scan_comments("test_vid_boundaries", limit=limit_val)
            summary.record(
                "Scanner-LimitBoundaries",
                label,
                len(res) == exp_len,
                f"Requested limit={limit_val}, received len={len(res)} (expected {exp_len})",
            )
        except Exception as e:
            summary.record("Scanner-LimitBoundaries", label, False, f"Crashed on limit={limit_val}", str(e))

    # 1.4 Database Ingestion Torture & Concurrency
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    # Seed channel and niche
    async with session_factory() as session:
        niche = Niche(niche_id="niche_adv", name="Adversarial Testing")
        chan = Channel(
            channel_id="chan_adv_01",
            niche_id="niche_adv",
            browser_profile_id="prof_adv_01",
        )
        session.add_all([niche, chan])
        await session.commit()

    # 1.4.1 Malformed comment batch ingestion
    async with session_factory() as session:
        malformed_comments = [
            {},  # empty dict
            {"comment_id": None},  # None comment_id
            {"comment_id": ""},  # empty string comment_id
            {"comment_id": "   "},  # whitespace comment_id
            {"comment_id": "c_ok_1", "text": None, "user": None, "author_id": None, "timestamp": None},
            {"comment_id": "c_ok_2", "text": "🔥" * 10000, "timestamp": "invalid_date_format"},
            {"comment_id": "c_ok_3", "timestamp": 10**20},  # overflow epoch
            {"comment_id": "c_ok_4", "timestamp": float("nan")},  # NaN epoch
            {"comment_id": "c_ok_5", "timestamp": float("inf")},  # Inf epoch
        ]

        try:
            synced = await scanner.sync_comments_to_db("v_adv", "chan_adv_01", malformed_comments, session)
            await session.commit()
            summary.record(
                "Scanner-DB-Torture",
                "Malformed comments batch ingestion",
                len(synced) == 5,
                f"Ingested {len(synced)} valid records from 9 malformed entries (0 crashes)",
            )
        except Exception as e:
            summary.record("Scanner-DB-Torture", "Malformed comments batch ingestion", False, "Crashed on malformed batch", str(e))

    # 1.4.2 Intra-batch duplicate comment insertions
    async with session_factory() as session:
        # Create 20 comments with only 4 distinct comment IDs (each repeated 5 times)
        dup_batch = [
            {"comment_id": f"c_dup_{i % 4}", "text": f"Duplicate comment text {i}", "user": f"user_{i}"}
            for i in range(20)
        ]
        try:
            synced_dups = await scanner.sync_comments_to_db("v_dup", "chan_adv_01", dup_batch, session)
            await session.commit()
            unique_cids = {c.comment_id for c in synced_dups}
            summary.record(
                "Scanner-DB-Torture",
                "Intra-batch duplicate comment IDs",
                len(synced_dups) == 20 and len(unique_cids) == 4,
                f"Handled 20 duplicate entries with 4 unique keys without IntegrityError",
            )
        except Exception as e:
            summary.record("Scanner-DB-Torture", "Intra-batch duplicate comment IDs", False, "Failed intra-batch deduplication", str(e))

    # 1.4.3 High Concurrency Stress: 25 concurrent scans & 25 concurrent DB syncs
    try:
        async def do_scan(idx: int) -> List[Dict[str, Any]]:
            return await scanner.scan_comments(f"v_concurrent_{idx}", limit=20)

        t0 = time.perf_counter()
        scan_tasks = [do_scan(i) for i in range(25)]
        concurrent_scans = await asyncio.gather(*scan_tasks)
        scan_time = time.perf_counter() - t0

        all_scans_valid = len(concurrent_scans) == 25 and all(len(c) == 20 for c in concurrent_scans)
        summary.record(
            "Scanner-Concurrency",
            "25 Concurrent scan_comments tasks",
            all_scans_valid,
            f"Executed 25 scans (500 mock comments total) in {scan_time:.3f}s",
        )

        async def do_sync(idx: int, c_list: List[Dict[str, Any]]) -> int:
            async with session_factory() as sess:
                res = await scanner.sync_comments_to_db(f"v_concurrent_{idx}", "chan_adv_01", c_list, sess)
                await sess.commit()
                return len(res)

        t1 = time.perf_counter()
        sync_tasks = [do_sync(i, concurrent_scans[i]) for i in range(25)]
        concurrent_syncs = await asyncio.gather(*sync_tasks)
        sync_time = time.perf_counter() - t1

        all_syncs_valid = len(concurrent_syncs) == 25 and all(c == 20 for c in concurrent_syncs)
        summary.record(
            "Scanner-Concurrency",
            "25 Concurrent sync_comments_to_db tasks",
            all_syncs_valid,
            f"Committed 500 records concurrently across 25 sessions in {sync_time:.3f}s",
        )
    except Exception as e:
        summary.record("Scanner-Concurrency", "25 Concurrent operations", False, "Concurrency stress failed", str(e))

    await engine.dispose()


# ==============================================================================
# Suite 2: CommentAgent.classify_intent Adversarial Stress
# ==============================================================================

def run_suite_2_intent(summary: SuiteSummary) -> None:
    print("\n" + "=" * 70)
    print("SUITE 2: CommentAgent.classify_intent Adversarial Stress & Homographs")
    print("=" * 70)

    agent = CommentAgent()

    # 2.1 Slang & Teen Code Cases
    slang_matrix = [
        ("bnhiu z sop", CommentIntent.ASK_PRICE, "Teen code for 'bao nhiêu vậy shop'"),
        ("mấy xèng", CommentIntent.ASK_PRICE, "Slang for 'mấy tiền'"),
        ("rổ rá", CommentIntent.ASK_PRICE, "Colloquial idiom for price inquiry ('rổ rá thế nào')"),
        ("vải gì dợ", CommentIntent.ASK_MATERIAL_USAGE, "Southern slang 'dợ' = 'vậy'"),
        ("m7 50kg vừa hơm", CommentIntent.ASK_MATERIAL_USAGE, "Teen code 'hơm' = 'không'"),
        ("đắt wa ko giống video", CommentIntent.COMPLAINT, "Teen code 'wa' = 'quá', 'ko' = 'không'"),
        ("shop lừa à", CommentIntent.COMPLAINT, "Scam complaint"),
        ("bn z shop", CommentIntent.ASK_PRICE, "Teen code abbreviation 'bn' = 'bao nhiêu'"),
        ("bnhieu vậy", CommentIntent.ASK_PRICE, "Teen code 'bnhieu' = 'bao nhiêu'"),
        ("inbox giá em này", CommentIntent.ASK_PRICE, "Direct price inquiry via inbox"),
    ]

    for comment, expected, desc in slang_matrix:
        actual = agent.classify_intent(comment)
        passed = (actual == expected)
        summary.record(
            "Intent-SlangTeenCode",
            f"'{comment}'",
            passed,
            f"Result: {actual.value} (Expected: {expected.value}) — {desc}",
            None if passed else f"Misclassified as {actual.value}",
        )

    # 2.2 Homograph Traps
    homograph_matrix = [
        # bụng vs bung chỉ
        ("bung 75 mac vua k", CommentIntent.ASK_MATERIAL_USAGE, "Unaccented 'bung' = waist 75cm"),
        ("bụng to mặc vừa không", CommentIntent.ASK_MATERIAL_USAGE, "Accented waist query"),
        ("bung chỉ rồi shop", CommentIntent.COMPLAINT, "Accented defect 'bung chỉ'"),
        ("ao bi bung chi", CommentIntent.COMPLAINT, "Unaccented defect 'bung chi'"),

        # lâu vs lau nhà
        ("giao lau qua", CommentIntent.COMPLAINT, "Unaccented delivery delay 'giao lâu'"),
        ("ship lau qua sop", CommentIntent.COMPLAINT, "Unaccented shipping delay 'ship lâu'"),
        ("cay lau nha dung sao", CommentIntent.ASK_MATERIAL_USAGE, "Unaccented home utility 'cây lau nhà'"),
        ("cay lau nha thong minh nay dung the nao", CommentIntent.ASK_MATERIAL_USAGE, "Smart mop usage inquiry"),

        # lụa vs lừa đảo
        ("vai lua nay mac mat ko", CommentIntent.ASK_MATERIAL_USAGE, "Unaccented silk fabric 'vải lụa'"),
        ("vai lua mac mua he vua k", CommentIntent.ASK_MATERIAL_USAGE, "Silk fabric summer fit"),
        ("shop lua dao a", CommentIntent.COMPLAINT, "Unaccented scam complaint 'lừa đảo'"),
        ("lua dao tien khach", CommentIntent.COMPLAINT, "Scamming money complaint"),

        # hong vs hỏng
        ("chat co gian hong shop", CommentIntent.ASK_MATERIAL_USAGE, "Southern question 'hong' = 'không'"),
        ("váy này hỏng rồi", CommentIntent.COMPLAINT, "Accented broken item 'hỏng rồi'"),
        ("ao bi hong khoa", CommentIntent.COMPLAINT, "Unaccented broken zipper 'bi hong'"),
        ("hang hong roi", CommentIntent.COMPLAINT, "Unaccented broken item 'hang hong'"),
    ]

    for comment, expected, desc in homograph_matrix:
        actual = agent.classify_intent(comment)
        passed = (actual == expected)
        summary.record(
            "Intent-Homographs",
            f"'{comment}'",
            passed,
            f"Result: {actual.value} (Expected: {expected.value}) — {desc}",
            None if passed else f"Homograph collision detected! Returned {actual.value}",
        )

    # 2.3 Multi-Intent Priority & Defect Brand Safety
    # When multiple signals exist, COMPLAINT must strictly override ASK_PRICE and ASK_MATERIAL_USAGE
    priority_matrix = [
        ("áo rách rồi, giá thì đắt mà ship lâu quá", CommentIntent.COMPLAINT, "Triple signal: defect + price + delay"),
        ("vay bao nhieu ma ship lau the shop", CommentIntent.COMPLAINT, "Dual signal: price question + delivery delay"),
        ("size M mac vua ko shop oi sao giao hang cham the", CommentIntent.COMPLAINT, "Dual signal: size query + slow shipping"),
        ("vải xấu quá mà giá đắt", CommentIntent.COMPLAINT, "Dual signal: bad fabric + price complaint"),
        ("chất vải xấu mà giá đắt thế", CommentIntent.COMPLAINT, "Dual signal: bad fabric + high price"),
        ("chất xấu như giẻ lau", CommentIntent.COMPLAINT, "Defect signal: extremely bad fabric"),
        ("vải đểu thế mà bán 200k", CommentIntent.COMPLAINT, "Dual signal: counterfeit/fake fabric + price"),
        ("hàng xấu vải mỏng tang", CommentIntent.COMPLAINT, "Dual signal: bad quality + transparent fabric"),
        ("đắt wa ko giống video", CommentIntent.COMPLAINT, "Dual signal: expensive + misleading video"),
    ]

    for comment, expected, desc in priority_matrix:
        actual = agent.classify_intent(comment)
        passed = (actual == expected)
        summary.record(
            "Intent-MultiPriority",
            f"'{comment}'",
            passed,
            f"Result: {actual.value} (Expected: {expected.value}) — {desc}",
            None if passed else f"Safety violation! Did not prioritize COMPLAINT, returned {actual.value}",
        )

    # 2.4 False-Positive Guards for Price
    fp_matrix = [
        ("đánh giá 5 sao", CommentIntent.OTHER, "Review rating (not asking price)"),
        ("giá như biết sớm", CommentIntent.OTHER, "Idiom 'giá như' = 'wish that'"),
        ("cái giá treo quần áo này", CommentIntent.OTHER, "Utility item noun 'giá treo' without price question"),
        ("cai gia de do nay bao tien", CommentIntent.ASK_PRICE, "Utility noun WITH explicit price question 'bao tien'"),
        ("gia nhu e biet shop som hon", CommentIntent.OTHER, "Idiom 'giá như em biết shop sớm hơn'"),
        ("danh gia 5 sao cho shop nhe", CommentIntent.OTHER, "Review rating 'đánh giá 5 sao'"),
        ("vay dep gia re qua shop oi", CommentIntent.OTHER, "Compliment 'giá rẻ' (not asking price)"),
    ]

    for comment, expected, desc in fp_matrix:
        actual = agent.classify_intent(comment)
        passed = (actual == expected)
        summary.record(
            "Intent-FalsePositiveGuards",
            f"'{comment}'",
            passed,
            f"Result: {actual.value} (Expected: {expected.value}) — {desc}",
            None if passed else f"False positive triggered! Returned {actual.value}",
        )


# ==============================================================================
# Suite 3: Crash Resilience, Extreme Types & Tone Compliance
# ==============================================================================

def run_suite_3_resilience(summary: SuiteSummary) -> None:
    print("\n" + "=" * 70)
    print("SUITE 3: Crash Resilience, Malformed Types & Tone Compliance")
    print("=" * 70)

    agent = CommentAgent()

    # 3.1 Non-string & Malformed inputs to classify_intent
    extreme_inputs = [
        (None, "None type"),
        ("", "Empty string"),
        ("   ", "Whitespace string"),
        ("\t\r\n", "Newline/Tab string"),
        (12345, "Integer type"),
        (45.67, "Float type"),
        ([], "List type"),
        ({}, "Dict type"),
        (True, "Boolean True"),
        (False, "Boolean False"),
        ("🔥" * 20000, "20,000 Unicode Emojis"),
        ("a" * 50000, "50,000 ASCII chars"),
        ("\x00\x01\x02\xff\xfe", "Control/Binary bytes decoded"),
    ]

    for item, label in extreme_inputs:
        try:
            res = agent.classify_intent(item)  # type: ignore
            summary.record(
                "Resilience-ClassifyIntent",
                f"Input ({label})",
                res == CommentIntent.OTHER,
                f"Handled safely without crash, returned {res.value}",
            )
        except Exception as e:
            summary.record("Resilience-ClassifyIntent", f"Input ({label})", False, "Crashed", str(e))

    # 3.2 Extreme inputs to generate_reply
    metas = [
        (None, "None meta"),
        ({}, "Empty meta"),
        ({"title": None, "price": None}, "None values in meta"),
        ({"title": 12345, "price": "invalid_price_string"}, "Corrupt types in meta"),
        ({"title": "x" * 5000, "price": -999999}, "Huge title & negative price"),
        (
            {"title": "Váy Zara rep 1:1 siêu xịn tốt nhất thị trường vĩnh viễn không hỏng", "price": 199000},
            "Trademark & Superlative dirty title",
        ),
    ]

    personas = [None, "", "hoai_my", "nam_minh", 123, {"niche_id": "do_gia_dung"}, {"name": "unknown"}]

    crash_count = 0
    tone_violations = []
    brand_leak_count = 0

    for m, m_lbl in metas:
        for p in personas:
            for text in ["giá bao nhiêu", "chất vải gì", "giao chậm quá", "đẹp quá"]:
                try:
                    reply = agent.generate_reply(text, m, p)  # type: ignore
                    if not isinstance(reply, str) or not reply:
                        crash_count += 1
                        continue

                    # Check ToneValidator compliance
                    if not ToneValidator.validate(reply):
                        tone_violations.append((reply, m_lbl, str(p)))

                    # Check banned brand leaks
                    reply_lower = reply.lower()
                    if any(b in reply_lower for b in ["zara", "chanel", "rep 1:1", "tốt nhất thị trường"]):
                        brand_leak_count += 1
                except Exception:
                    crash_count += 1

    summary.record(
        "Resilience-GenerateReply",
        "Zero Crashes on Malformed Metas/Personas",
        crash_count == 0,
        f"Executed {len(metas) * len(personas) * 4} matrix combinations with 0 crashes",
        f"{crash_count} crashes occurred" if crash_count else None,
    )

    summary.record(
        "Resilience-ToneValidator",
        "100% ToneValidator Compliance Guarantee",
        len(tone_violations) == 0,
        f"0 tone violations across {len(metas) * len(personas) * 4} reply generations",
        f"{len(tone_violations)} replies failed ToneValidator" if tone_violations else None,
    )

    summary.record(
        "Resilience-TitleSanitization",
        "Banned Brand & Policy Leak Prevention",
        brand_leak_count == 0,
        "All counterfeit brands and policy violations sanitized from replies",
        f"{brand_leak_count} brand leaks detected" if brand_leak_count else None,
    )


# ==============================================================================
# Main Runner & Verdict Evaluation
# ==============================================================================

async def main() -> int:
    print("=" * 70)
    print("AMAS Milestone 7 Adversarial Stress Harness (CommentScanner & CommentAgent)")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)

    summary = SuiteSummary()

    # Run all suites
    await run_suite_1_scanner(summary)
    run_suite_2_intent(summary)
    run_suite_3_resilience(summary)

    # Final tally
    print("\n" + "=" * 70)
    print("FINAL ADVERSARIAL STRESS TEST SUMMARY")
    print("=" * 70)
    print(f"Total Tests Run: {summary.total}")
    print(f"Passed:          {summary.passed} ({summary.passed / summary.total * 100:.1f}%)")
    print(f"Failed:          {summary.failed} ({summary.failed / summary.total * 100:.1f}%)")

    if summary.failed > 0:
        print("\nFAILURE BREAKDOWN:")
        for r in summary.results:
            if not r.passed:
                print(f"- [{r.category}] {r.name}: {r.details} | Error: {r.error}")

        print("\nVERDICT: REQUEST_CHANGES")
        return 1
    else:
        print("\nVERDICT: APPROVE")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
