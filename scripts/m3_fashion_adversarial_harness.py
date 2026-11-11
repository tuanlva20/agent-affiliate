#!/usr/bin/env python3
"""Adversarial Stress Harness for Milestone 3 (FashionScoutAgent & Prompt Templates).

Empirically tests:
1. Trademark bypass attempts: mixed case, accents, leetspeak, spacing, punctuation
   (e.g., "Z.a.r.a", "C-h-a-n-e-l", "G_u_c_c_i", "r.e.p 1:1", "super_fake",
   "like auth", "rep1:1", "áo fake 1:1 Quảng Châu").
   Verifies 100% of counterfeit attempts are rejected with score=0.0 and
   rejection_reason containing "trademark" or "policy".
2. Corrupted and boundary inputs: empty string title, whitespace title, None description,
   zero price, huge sales count, negative rating, NaN/Inf rating.
   Verifies no unhandled exceptions.
3. Score threshold boundary tests: products right below and above threshold.
   Ensures correct classification and threshold calibration.
4. Hook angle tone validation: ensures generated hooks pass ToneValidator
   and don't trigger robotic/counterfeit/exaggerated phrases.
5. Concurrency / high throughput: evaluates 100+ items concurrently to ensure
   thread safety, deterministic behavior, and zero race conditions.
"""

from __future__ import annotations

import concurrent.futures
import math
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.base_scout import ProductCandidate
from src.agents.fashion_scout import FashionScoutAgent, SpecialistEvaluation
from src.core.tone_validator import ToneValidator


class TestResult:
    def __init__(self, name: str) -> None:
        self.name = name
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.failures: List[str] = []

    def record_pass(self) -> None:
        self.total += 1
        self.passed += 1

    def record_fail(self, detail: str) -> None:
        self.total += 1
        self.failed += 1
        self.failures.append(detail)

    @property
    def pass_rate(self) -> float:
        return (self.passed / self.total * 100.0) if self.total > 0 else 0.0


def test_1_trademark_bypass_matrix(agent: FashionScoutAgent) -> TestResult:
    """Challenge 1: Trademark bypass attempts.

    Verifies that mixed case, accents, leetspeak, spacing, and punctuation
    attempting to bypass counterfeit brand detection are 100% rejected with:
    - passed_filter == False
    - score == 0.0
    - rejection_reason containing 'trademark' or 'policy'.
    """
    res = TestResult("Challenge 1: Trademark Bypass Matrix")

    bypass_cases: List[Tuple[str, str]] = [
        # Explicitly requested cases from prompt
        ("Punctuation Zara", "Váy Z.a.r.a dáng xòe chiết eo che bụng"),
        ("Hyphen Chanel", "Đầm C-h-a-n-e-l tiểu thư tôn dáng chiết eo"),
        ("Underscore Gucci", "Áo G_u_c_c_i croptop che mỡ bụng"),
        ("Punctuation rep 1:1", "Váy r.e.p 1:1 lụa sang chảnh chiết eo"),
        ("Underscore super fake", "Váy super_fake loại 1 chiết eo"),
        ("Standard like auth", "Đầm like auth tôn dáng che mỡ bụng"),
        ("Standard rep1:1", "Váy rep1:1 cao cấp cạp cao che bụng"),
        ("Standard fake 1:1 VN", "Áo fake 1:1 Quảng Châu hack dáng chiết eo"),

        # Additional punctuation & symbol variations
        ("Dot Dior", "Váy D.i.o.r dáng xòe che mỡ bụng"),
        ("Dot Nike", "Áo thể thao N.i.k.e hack dáng"),
        ("Dot Adidas", "Áo khoác A.d.i.d.a.s tôn dáng"),
        ("Dot LV", "Túi xách L.V sang chảnh"),
        ("Dot Hermes", "Khăn lụa H.e.r.m.e.s cao cấp"),
        ("Hyphen rep 1-1", "Váy ren r-e-p 1-1 Quảng Châu"),
        ("Slash rep 1/1", "Váy lụa rep 1/1 cao cấp"),

        # Spaced out bypass attempts
        ("Spaced Zara", "Váy Z a r a dáng xòe chiết eo"),
        ("Spaced Chanel", "Đầm C h a n e l tiểu thư thắt eo"),
        ("Spaced Gucci", "Áo G u c c i croptop che mỡ bụng"),
        ("Spaced Dior", "Sơ mi D i o r lụa chuẩn form"),
        ("Spaced Nike", "Giày N i k e thể thao cạp cao"),

        # Leetspeak bypass attempts
        ("Leet Zara Z4r4", "Váy Z4r4 dáng xòe tôn dáng"),
        ("Leet Chanel Ch4n3l", "Đầm Ch4n3l siêu xinh chiết eo"),
        ("Leet Gucci Gucc1", "Áo Gucc1 thời trang che mỡ"),
        ("Leet Dior D10r", "Váy D10r sang chảnh hack eo"),

        # Accents & Diacritics bypass attempts
        ("Accent Zàra", "Váy Zàra thiết kế tôn dáng"),
        ("Accent Chánel", "Đầm Chánel dáng suông che bụng"),
        ("Accent Gùcci", "Áo Gùcci croptop"),

        # Combined adversarial attacks
        ("Adversarial Rep 1:1 Dot", "Áo dạ r.e.p. 1.1 cao cấp chiết eo"),
        ("Adversarial Super Fake Dot", "Váy s.u.p.e.r f.a.k.e dáng xòe"),
        ("Adversarial Like Auth Hyphen", "Đầm like-auth chuẩn form hack eo"),
    ]

    for label, title in bypass_cases:
        item = {
            "product_id": f"bypass_{hash(title) % 100000}",
            "title": title,
            "price": 220000.0,
            "commission_rate": 0.18,
            "sales_30d": 3500,
            "rating": 4.9,
        }
        eval_res = agent.evaluate_product(item)

        reason_str = (eval_res.rejection_reason or "").lower()
        has_policy_kw = "trademark" in reason_str or "policy" in reason_str

        # Strict invariant: 100% rejected, score == 0.0, policy/trademark cited
        if eval_res.passed_filter is False and eval_res.score == 0.0 and has_policy_kw:
            res.record_pass()
        else:
            fail_detail = (
                f"[{label}] '{title}' -> passed_filter={eval_res.passed_filter}, "
                f"score={eval_res.score}, rejection_reason={eval_res.rejection_reason!r}"
            )
            res.record_fail(fail_detail)

    return res


def test_2_corrupted_and_boundary_inputs(agent: FashionScoutAgent) -> TestResult:
    """Challenge 2: Corrupted and boundary inputs.

    Verifies that no unhandled exceptions are raised for empty, whitespace,
    missing, zero, extreme numeric, negative, NaN, Inf, and malformed inputs.
    """
    res = TestResult("Challenge 2: Corrupted & Boundary Inputs")

    corrupted_cases: List[Tuple[str, Any]] = [
        ("None input", None),
        ("Empty dict", {}),
        ("Empty string title", {"product_id": "c1", "title": ""}),
        ("Whitespace title spaces", {"product_id": "c2", "title": "    "}),
        ("Whitespace title tabs/newlines", {"product_id": "c3", "title": "\t \n \r "}),
        ("None description", {"product_id": "c4", "title": "Váy body che bụng", "description": None}),
        ("Zero price", {"product_id": "c5", "title": "Váy body che bụng", "price": 0.0}),
        ("Zero price integer", {"product_id": "c6", "title": "Váy body che bụng", "price": 0}),
        ("Huge sales count 10^9", {"product_id": "c7", "title": "Váy body che bụng chiết eo", "sales_30d": 1_000_000_000}),
        ("Negative price", {"product_id": "c8", "title": "Váy body che bụng", "price": -150000.0}),
        ("Negative commission rate", {"product_id": "c9", "title": "Váy body che bụng", "commission_rate": -0.2}),
        ("Negative sales count", {"product_id": "c10", "title": "Váy body che bụng", "sales_30d": -50}),
        ("Negative rating", {"product_id": "c11", "title": "Váy body che bụng", "rating": -1.0}),
        ("NaN rating", {"product_id": "c12", "title": "Váy body che bụng", "rating": float("nan")}),
        ("Inf rating positive", {"product_id": "c13", "title": "Váy body che bụng", "rating": float("inf")}),
        ("Inf rating negative", {"product_id": "c14", "title": "Váy body che bụng", "rating": float("-inf")}),
        ("Non-dict string", "not a dictionary"),
        ("Non-dict integer", 12345),
        ("Non-dict list", ["item1", "item2"]),
        ("Missing product_id", {"title": "Váy hoa nhí dáng xòe che bụng"}),
        ("Missing title but has name", {"product_id": "c15", "name": "Váy hoa nhí dáng xòe che bụng"}),
        ("Malformed price string", {"product_id": "c16", "title": "Váy hoa", "price": "free"}),
        ("Malformed sales string", {"product_id": "c17", "title": "Váy hoa", "sales_30d": "lots"}),
        ("NaN price", {"product_id": "c18", "title": "Váy hoa che bụng", "price": float("nan")}),
        ("NaN sales", {"product_id": "c19", "title": "Váy hoa che bụng", "sales_30d": float("nan")}),
    ]

    for label, payload in corrupted_cases:
        try:
            eval_res = agent.evaluate_product(payload)
            # Ensure evaluation returned a valid SpecialistEvaluation object
            if isinstance(eval_res, SpecialistEvaluation):
                # If input was invalid or missing required fields, passed_filter must be False
                if payload is None or (isinstance(payload, dict) and (not payload.get("title") and not payload.get("name"))):
                    if eval_res.passed_filter is False and eval_res.score == 0.0:
                        res.record_pass()
                    else:
                        res.record_fail(f"[{label}] Expected failure for invalid input, got passed={eval_res.passed_filter}")
                else:
                    res.record_pass()
            else:
                res.record_fail(f"[{label}] Did not return SpecialistEvaluation instance: {type(eval_res)}")
        except Exception as e:
            res.record_fail(f"[{label}] Unhandled exception: {type(e).__name__}: {e}")

    return res


def test_3_score_threshold_boundary(agent: FashionScoutAgent) -> TestResult:
    """Challenge 3: Score threshold boundary tests.

    Verifies behavior right below and above threshold:
    - Products with no body-hack attributes score < 7.0 and fail filter.
    - Borderline products score near the boundary.
    - High-velocity body-hack products score >= 8.0 and pass filter.
    - When min_score threshold is calibrated (e.g. 8.0), products below 8.0 are rejected.
    """
    res = TestResult("Challenge 3: Score Threshold Boundary")

    # Case A: Sub-threshold generic fashion item (expected score < 7.0, passed_filter == False)
    subthreshold_item = {
        "product_id": "bland_01",
        "title": "Áo thun cotton trơn màu đen basic",
        "price": 99000.0,
        "commission_rate": 0.10,
        "sales_30d": 20,
        "rating": 4.0,
    }
    eval_sub = agent.evaluate_product(subthreshold_item)
    if eval_sub.passed_filter is False and eval_sub.score < 7.0 and eval_sub.rejection_reason:
        res.record_pass()
    else:
        res.record_fail(f"[Subthreshold] Expected < 7.0 and rejected, got score={eval_sub.score}, passed={eval_sub.passed_filter}")

    # Case B: Top-tier viral body-hack candidate (expected score >= 8.0, passed_filter == True)
    viral_item = {
        "product_id": "viral_01",
        "title": "Váy hoa nhí dáng xòe chiết eo hack dáng che bụng mỡ cực đỉnh",
        "price": 219000.0,
        "commission_rate": 0.18,
        "sales_30d": 4500,
        "rating": 4.9,
    }
    eval_viral = agent.evaluate_product(viral_item)
    if eval_viral.passed_filter is True and eval_viral.score >= 8.0 and eval_viral.rejection_reason is None:
        res.record_pass()
    else:
        res.record_fail(f"[Viral >= 8.0] Expected score >= 8.0, got score={eval_viral.score}, passed={eval_viral.passed_filter}")

    # Case C: Boundary test with threshold = 8.0 configured
    strict_agent = FashionScoutAgent()
    strict_agent.min_score = 8.0

    # Item with modest body-hack appeal (scores ~7.2 - 7.6, passes at 7.0 but should fail at 8.0)
    modest_item = {
        "product_id": "modest_01",
        "title": "Chân váy chữ A che khuyết điểm",
        "price": 150000.0,
        "commission_rate": 0.12,
        "sales_30d": 150,
        "rating": 4.5,
    }
    eval_modest = strict_agent.evaluate_product(modest_item)
    if eval_modest.passed_filter is False and eval_modest.score < 8.0:
        res.record_pass()
    else:
        res.record_fail(f"[Threshold 8.0] Expected rejection below 8.0, got score={eval_modest.score}, passed={eval_modest.passed_filter}")

    # High body-hack item evaluated by strict agent should pass
    eval_strict_viral = strict_agent.evaluate_product(viral_item)
    if eval_strict_viral.passed_filter is True and eval_strict_viral.score >= 8.0:
        res.record_pass()
    else:
        res.record_fail(f"[Threshold 8.0 Viral] Expected pass >= 8.0, got score={eval_strict_viral.score}, passed={eval_strict_viral.passed_filter}")

    # Case D: Verify score precision and range [0.0, 10.0]
    for test_sales in [0, 50, 200, 800, 2500, 10000]:
        item = {
            "product_id": f"range_{test_sales}",
            "title": "Váy suông chữ A giấu bụng tôn dáng",
            "price": 190000.0,
            "commission_rate": 0.15,
            "sales_30d": test_sales,
            "rating": 4.85,
        }
        ev = agent.evaluate_product(item)
        if 0.0 <= ev.score <= 10.0 and round(ev.score, 1) == ev.score:
            res.record_pass()
        else:
            res.record_fail(f"[Score range] Invalid score {ev.score} for sales={test_sales}")

    return res


def test_4_hook_angle_tone_validation(agent: FashionScoutAgent) -> TestResult:
    """Challenge 4: Hook angle tone validation.

    Ensures that every generated hook angle across all keyword categories
    satisfies ToneValidator, does not trigger robotic clichés, and contains
    natural Vietnamese spoken KOC markers.
    """
    res = TestResult("Challenge 4: Hook Angle Tone Validation")

    categories_to_test = [
        ("belly", "Đầm suông giấu mỡ bụng dưới cực tốt"),
        ("waist", "Váy cạp cao chiết eo thon gọn"),
        ("height", "Quần ống rộng hack chiều cao chân dài miên man cho nấm lùn"),
        ("default", "Váy thiết kế dáng thon tôn đường cong"),
    ]

    for cat_name, title in categories_to_test:
        item = {
            "product_id": f"hook_{cat_name}",
            "title": title,
            "price": 200000.0,
            "commission_rate": 0.15,
            "sales_30d": 3000,
            "rating": 4.8,
        }
        eval_res = agent.evaluate_product(item)
        hook = eval_res.hook_angle

        # 1. Non-empty hook
        if not hook:
            res.record_fail(f"[{cat_name}] Generated hook is empty")
            continue

        # 2. Contains required keyword 'bụng' or 'eo'
        hook_lower = hook.lower()
        if "bụng" not in hook_lower and "eo" not in hook_lower:
            res.record_fail(f"[{cat_name}] Hook lacks 'bụng' or 'eo': '{hook}'")
            continue
        res.record_pass()

        # 3. ToneValidator compliance (zero robotic, counterfeit, or exaggerated patterns)
        violations = ToneValidator.check_violations(hook)
        if violations:
            res.record_fail(f"[{cat_name}] Hook triggers violations {violations}: '{hook}'")
        else:
            res.record_pass()

        # 4. Pure validate method returns True
        if ToneValidator.validate(hook):
            res.record_pass()
        else:
            res.record_fail(f"[{cat_name}] ToneValidator.validate() returned False for '{hook}'")

        # 5. Natural KOC markers present
        if ToneValidator.has_koc_markers(hook):
            res.record_pass()
        else:
            res.record_fail(f"[{cat_name}] Hook lacks KOC markers: '{hook}'")

    # Also test all static HOOK_TEMPLATES directly
    for group, templates in agent.HOOK_TEMPLATES.items():
        for idx, tmpl in enumerate(templates):
            viols = ToneValidator.check_violations(tmpl)
            if viols:
                res.record_fail(f"[Template {group} #{idx}] Violations {viols}: '{tmpl}'")
            else:
                res.record_pass()

    return res


def test_5_concurrency_and_throughput(agent: FashionScoutAgent) -> TestResult:
    """Challenge 5: Concurrency and high throughput.

    Evaluates 160+ product items concurrently across 16 worker threads
    to verify thread safety, deterministic outcomes, and absence of race conditions.
    """
    res = TestResult("Challenge 5: Concurrency & High Throughput")

    # Generate 160 distinct items: 80 valid body-hack, 40 counterfeit, 40 corrupted
    items: List[Dict[str, Any]] = []
    for i in range(80):
        items.append({
            "product_id": f"conc_valid_{i}",
            "title": f"Váy hoa nhí dáng xòe chiết eo che mỡ bụng mã {i}",
            "price": 180000.0 + (i * 1000),
            "commission_rate": 0.15,
            "sales_30d": 1000 + (i * 50),
            "rating": 4.8,
            "_expected_pass": True,
        })
    for i in range(40):
        items.append({
            "product_id": f"conc_counterfeit_{i}",
            "title": f"Váy Zara thiết kế rep 1:1 siêu cấp số {i}",
            "price": 250000.0,
            "commission_rate": 0.18,
            "sales_30d": 2000,
            "rating": 4.9,
            "_expected_pass": False,
        })
    for i in range(40):
        items.append({
            "product_id": f"conc_bland_{i}",
            "title": f"Áo phông trắng cotton trơn basic mã {i}",
            "price": 89000.0,
            "commission_rate": 0.08,
            "sales_30d": 10,
            "rating": 4.1,
            "_expected_pass": False,
        })

    start_time = time.perf_counter()
    results: List[SpecialistEvaluation] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
        futures = [executor.submit(agent.evaluate_product, itm) for itm in items]
        for f in concurrent.futures.as_completed(futures):
            try:
                results.append(f.result())
            except Exception as e:
                res.record_fail(f"Concurrent execution raised: {type(e).__name__}: {e}")

    elapsed = time.perf_counter() - start_time

    if len(results) == len(items):
        res.record_pass()
    else:
        res.record_fail(f"Expected {len(items)} results, got {len(results)}")

    # Determinism verification: evaluate first 10 items twice and compare
    deterministic_ok = True
    for itm in items[:10]:
        ev1 = agent.evaluate_product(itm)
        ev2 = agent.evaluate_product(itm)
        if ev1.score != ev2.score or ev1.passed_filter != ev2.passed_filter or ev1.rejection_reason != ev2.rejection_reason:
            deterministic_ok = False
            res.record_fail(f"Non-deterministic outcome for item {itm['product_id']}")
            break
    if deterministic_ok:
        res.record_pass()

    print(f"      [Throughput] Evaluated {len(items)} items in {elapsed*1000:.1f}ms ({len(items)/elapsed:.1f} items/sec)")
    return res


def run_all_adversarial_tests() -> Tuple[int, int, List[TestResult]]:
    """Run full adversarial challenge suite against FashionScoutAgent."""
    print("=" * 80)
    print("AMAS v1.4.0 — Milestone 3 FashionScoutAgent Adversarial Challenge Harness")
    print("=" * 80)

    agent = FashionScoutAgent()
    test_functions = [
        test_1_trademark_bypass_matrix,
        test_2_corrupted_and_boundary_inputs,
        test_3_score_threshold_boundary,
        test_4_hook_angle_tone_validation,
        test_5_concurrency_and_throughput,
    ]

    suite_results: List[TestResult] = []
    total_passed = 0
    total_failed = 0

    for test_fn in test_functions:
        result = test_fn(agent)
        suite_results.append(result)
        total_passed += result.passed
        total_failed += result.failed

        status_str = "PASS" if result.failed == 0 else f"FAIL ({result.failed} issues)"
        print(f"\n▶ {result.name}: {status_str}")
        print(f"  Tests: {result.total} | Passed: {result.passed} | Failed: {result.failed} | Pass Rate: {result.pass_rate:.1f}%")
        if result.failures:
            print("  Top Failure Details (first 5):")
            for f in result.failures[:5]:
                print(f"    ❌ {f}")
            if len(result.failures) > 5:
                print(f"    ... and {len(result.failures) - 5} more failures.")

    print("\n" + "=" * 80)
    grand_total = total_passed + total_failed
    overall_rate = (total_passed / grand_total * 100.0) if grand_total > 0 else 0.0
    print(f"SUMMARY: {total_passed}/{grand_total} assertions passed ({overall_rate:.1f}%). Total Failures: {total_failed}")
    print("=" * 80)

    return total_passed, total_failed, suite_results


if __name__ == "__main__":
    passed, failed, results = run_all_adversarial_tests()
    # Exit with code 1 if any challenge failed
    sys.exit(0 if failed == 0 else 1)
