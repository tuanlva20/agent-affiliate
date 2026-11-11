"""AMAS v1.4.0 — Milestone 3 HomeLifeScoutAgent Adversarial Stress Test Harness.

Executes empirical challenge tests against HomeLifeScoutAgent (Feature F09) and related prompt templates:
1. Exaggerated claims bypass attempts: spacing, punctuation, synonyms, capitalization.
2. Pricing sweet spot boundary tests: 0 VND, 1 VND, 99.999 VND, 100.000 VND, 300.000 VND, 300.001 VND, 10.000.000 VND, negative, NaN/Inf.
3. Score threshold boundary tests: products right below and above the 8.5 threshold.
4. Hook angle and viral factor validation: "3s"/"nhàn" in hook angle, "3s"/"vắt khô" in viral factor, ToneValidator compliance.
5. Corrupted inputs and concurrency: robustness on nulls, malformed dicts, and 120+ concurrent evaluations.
"""

from __future__ import annotations

import concurrent.futures
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agents.homelife_scout import HomeLifeScoutAgent
from src.core.prompt_templates import (
    HOMELIFE_PERSONA,
    HOMELIFE_SYSTEM_PROMPT,
    HOMELIFE_SCRIPT_TEMPLATE,
    build_homelife_evaluation_prompt,
)
from src.core.tone_validator import ToneValidator


@dataclass
class TestResult:
    category: str
    case_name: str
    input_data: Any
    expected: str
    actual: str
    passed: bool
    details: str = ""


class HomeLifeAdversarialHarness:
    def __init__(self) -> None:
        self.agent = HomeLifeScoutAgent()
        self.results: List[TestResult] = []

    def record(
        self,
        category: str,
        case_name: str,
        input_data: Any,
        expected: str,
        actual: str,
        passed: bool,
        details: str = "",
    ) -> None:
        self.results.append(
            TestResult(
                category=category,
                case_name=case_name,
                input_data=input_data,
                expected=expected,
                actual=actual,
                passed=passed,
                details=details,
            )
        )

    # -------------------------------------------------------------------------
    # 1. EXAGGERATED CLAIMS BYPASS ATTEMPTS
    # -------------------------------------------------------------------------
    def test_exaggerated_claims_bypass(self) -> None:
        category = "1. Exaggerated Claims Bypass"

        bypass_cases = [
            ("trị dứt điểm 100%", "standard phrase"),
            ("trị dứt điểm 100 %", "spaced percent"),
            ("chữa khỏi 100%", "standard cure claim"),
            ("TRỊ DỨT ĐIỂM 100%", "all uppercase"),
            ("vĩnh viễn không bám bẩn", "standard permanent claim"),
            ("vĩnh viễn ko bám bẩn", "synonym shorthand 'ko'"),
            ("vĩnh viễn khong bám bẩn", "unaccented 'khong'"),
            ("thần_dược", "underscore separator"),
            ("thần-dược", "hyphen separator"),
            ("thần.dược", "dot separator"),
            ("thần dược", "standard space"),
            ("trị   dứt   điểm   100%", "multi-space separator"),
            ("trị_dứt_điểm", "underscore verb"),
            ("vĩnh_viễn_không_bám_bẩn", "full underscores"),
            ("100% không bao giờ hỏng", "standard lifetime claim"),
            ("100 % không bao giờ hỏng", "spaced percent lifetime"),
            ("chữa khỏi", "base medical verb"),
            ("chữa khỏi bệnh", "compound medical claim"),
            ("cam kết khỏi bệnh 100%", "guaranteed cure 100%"),
            ("cam kết chữa khỏi", "guaranteed treatment"),
        ]

        for phrase, desc in bypass_cases:
            # Wrap in an otherwise highly-rated product candidate
            item = {
                "product_id": f"adv_exag_{hash(phrase) % 100000}",
                "title": f"Cây lau nhà tự vắt thông minh 3s {phrase}",
                "price": 149000.0,
                "commission_rate": 0.18,
                "sales_30d": 5000,
                "rating": 4.9,
            }

            res = self.agent.evaluate_product(item)
            reason = (res.rejection_reason or "").lower()
            is_rejected = (
                res.passed_filter is False
                and res.score == 0.0
                and ("exaggerated" in reason or "policy" in reason)
            )

            expected_str = "passed_filter=False, score=0.0, rejection_reason contains 'exaggerated'/'policy'"
            actual_str = f"passed_filter={res.passed_filter}, score={res.score}, reason='{res.rejection_reason}'"

            self.record(
                category=category,
                case_name=f"bypass_{desc.replace(' ', '_')}",
                input_data=phrase,
                expected=expected_str,
                actual=actual_str,
                passed=is_rejected,
                details=f"Policy check violation bypass: {'BLOCKED' if is_rejected else 'LEAKED'}",
            )

    # -------------------------------------------------------------------------
    # 2. PRICING SWEET SPOT BOUNDARY TESTS
    # -------------------------------------------------------------------------
    def test_pricing_boundaries(self) -> None:
        category = "2. Pricing Boundaries"

        price_cases = [
            (0.0, "zero_vnd", True, "price=0 valid non-negative, outside sweet spot"),
            (1.0, "one_vnd", True, "price=1 valid non-negative, outside sweet spot"),
            (99999.0, "sweet_spot_lower_boundary", True, "price=99,999 in sweet spot (99k-350k)"),
            (100000.0, "sweet_spot_nominal_low", True, "price=100,000 in sweet spot"),
            (300000.0, "sweet_spot_nominal_high", True, "price=300,000 in sweet spot"),
            (300001.0, "sweet_spot_upper_nominal", True, "price=300,001 in sweet spot"),
            (10000000.0, "ten_million_vnd", True, "price=10,000,000 extreme luxury, outside sweet spot"),
            (-100.0, "negative_price", False, "price=-100 must be rejected"),
            (float("nan"), "nan_price", False, "price=NaN must be rejected as invalid numeric"),
            (float("inf"), "pos_inf_price", False, "price=+Inf must be rejected as invalid numeric"),
            (float("-inf"), "neg_inf_price", False, "price=-Inf must be rejected as invalid numeric"),
        ]

        for price_val, name, should_survive_validation, desc in price_cases:
            item = {
                "product_id": f"price_test_{name}",
                "title": "Cây lau nhà tự vắt xoay 360 độ thông minh 3s",
                "price": price_val,
                "commission_rate": 0.15,
                "sales_30d": 3000,
                "rating": 4.8,
            }

            try:
                res = self.agent.evaluate_product(item)
                if should_survive_validation:
                    # Non-negative finite numbers should evaluate normally
                    passed = res.passed_filter is True and res.score >= 8.5
                    actual_str = f"passed_filter={res.passed_filter}, score={res.score}"
                    expected_str = "passed_filter=True, score>=8.5"
                else:
                    # Negative or NaN/Inf must be rejected with score=0.0
                    passed = (
                        res.passed_filter is False
                        and res.score == 0.0
                        and res.rejection_reason is not None
                    )
                    actual_str = f"passed_filter={res.passed_filter}, score={res.score}, reason='{res.rejection_reason}'"
                    expected_str = "passed_filter=False, score=0.0, rejection_reason='Invalid product input'"
            except Exception as e:
                passed = False
                actual_str = f"CRASH: {type(e).__name__}: {e}"
                expected_str = "Handled gracefully without exception"

            self.record(
                category=category,
                case_name=name,
                input_data=f"price={price_val}",
                expected=expected_str,
                actual=actual_str,
                passed=passed,
                details=desc,
            )

    # -------------------------------------------------------------------------
    # 3. SCORE THRESHOLD BOUNDARY TESTS (AROUND 8.5)
    # -------------------------------------------------------------------------
    def test_score_threshold_boundaries(self) -> None:
        category = "3. Score Threshold Boundaries"

        # Item engineered to score right below 8.5 (e.g., score = 8.4)
        # Base 6.0 + 1.2 (Tier 1 'tự vắt') + 0.6 (Visual 'lau nhà') + 0.1 (sales 200) + 0.3 (price 150k) + 0.2 (rating 4.85) = 8.4
        item_below_85 = {
            "product_id": "score_below_85",
            "title": "Cây lau nhà tự vắt",          # 1 tier 1 (tự vắt = 1.2), 1 visual (lau nhà = 0.6)
            "price": 150000.0,                      # price bonus +0.3
            "commission_rate": 0.15,
            "sales_30d": 200,                       # sales bonus +0.1
            "rating": 4.85,                         # rating bonus +0.2 -> sum: 6.0 + 1.2 + 0.6 + 0.1 + 0.3 + 0.2 = 8.4
        }

        res_below = self.agent.evaluate_product(item_below_85)
        # Verify calibrated score is exactly 8.4 (< 8.5)
        is_sub_85 = res_below.score < 8.5 and res_below.score >= 8.0
        self.record(
            category=category,
            case_name="product_score_right_below_8_5",
            input_data=item_below_85,
            expected="8.0 <= score < 8.5 (specifically 8.4)",
            actual=f"score={res_below.score}, passed_filter={res_below.passed_filter}",
            passed=is_sub_85,
            details=f"Expected score below 8.5 benchmark: score={res_below.score}",
        )

        # Item engineered to score right above 8.5 (e.g., score = 8.6)
        # Same item, but sales 1000 (+0.3 bonus instead of +0.1) -> 6.0 + 1.2 + 0.6 + 0.3 + 0.3 + 0.2 = 8.6
        item_above_85 = {
            "product_id": "score_above_85",
            "title": "Cây lau nhà tự vắt tiện ích",
            "price": 150000.0,
            "commission_rate": 0.15,
            "sales_30d": 1200,                      # sales bonus +0.3
            "rating": 4.85,                         # rating bonus +0.2
        }

        res_above = self.agent.evaluate_product(item_above_85)
        is_sup_85 = res_above.score >= 8.5 and res_above.passed_filter is True
        self.record(
            category=category,
            case_name="product_score_right_above_8_5",
            input_data=item_above_85,
            expected="score >= 8.5, passed_filter=True (specifically 8.6)",
            actual=f"score={res_above.score}, passed_filter={res_above.passed_filter}",
            passed=is_sup_85,
            details=f"Expected score above 8.5 benchmark: score={res_above.score}",
        )

        # Basic subthreshold item (< 7.0) with zero utility keywords
        item_subthreshold = {
            "product_id": "score_subthreshold",
            "title": "Móc nhựa treo quần áo trơn cơ bản",
            "price": 25000.0,
            "commission_rate": 0.10,
            "sales_30d": 10,
            "rating": 4.0,
        }

        res_sub = self.agent.evaluate_product(item_subthreshold)
        is_sub_rejected = res_sub.passed_filter is False and res_sub.score < 7.0 and "threshold" in (res_sub.rejection_reason or "").lower()
        self.record(
            category=category,
            case_name="product_score_subthreshold_rejected",
            input_data=item_subthreshold,
            expected="score < 7.0, passed_filter=False, rejection_reason contains 'threshold'",
            actual=f"score={res_sub.score}, passed_filter={res_sub.passed_filter}, reason='{res_sub.rejection_reason}'",
            passed=is_sub_rejected,
            details=f"Subthreshold rejection verified: score={res_sub.score}",
        )

    # -------------------------------------------------------------------------
    # 4. HOOK ANGLE AND VIRAL FACTOR VALIDATION
    # -------------------------------------------------------------------------
    def test_hook_angle_and_viral_factor(self) -> None:
        category = "4. Hook & Viral Factor Validation"

        categories_to_test = [
            ("cleaner_mop", "Cây lau nhà tự vắt xoay 360 độ sạch bóng 3s"),
            ("kitchen_fryer", "Nồi chiên không dầu tự động thông minh đa năng"),
            ("general_utility", "Máy hút bụi cầm tay không dây nhàn việc nhà"),
        ]

        for cat_name, title in categories_to_test:
            item = {
                "product_id": f"hook_{cat_name}",
                "title": title,
                "price": 189000.0,
                "commission_rate": 0.15,
                "sales_30d": 2500,
                "rating": 4.8,
            }

            res = self.agent.evaluate_product(item)

            # Check 1: '3s' or 'nhàn' in hook angle
            hook_lower = res.hook_angle.lower()
            hook_has_required_kw = "3s" in hook_lower or "nhàn" in hook_lower
            self.record(
                category=category,
                case_name=f"{cat_name}_hook_contains_3s_or_nhan",
                input_data=res.hook_angle,
                expected="'3s' or 'nhàn' present in hook angle",
                actual=f"'{res.hook_angle}'",
                passed=hook_has_required_kw,
            )

            # Check 2: '3s' or 'vắt khô' in viral factor
            viral_lower = res.viral_factor.lower()
            viral_has_required_kw = "3s" in viral_lower or "vắt khô" in viral_lower
            self.record(
                category=category,
                case_name=f"{cat_name}_viral_contains_3s_or_vat_kho",
                input_data=res.viral_factor,
                expected="'3s' or 'vắt khô' present in viral factor",
                actual=f"'{res.viral_factor}'",
                passed=viral_has_required_kw,
            )

            # Check 3: Hook angle passes ToneValidator
            hook_passes_tone = ToneValidator.validate(res.hook_angle)
            self.record(
                category=category,
                case_name=f"{cat_name}_hook_satisfies_tone_validator",
                input_data=res.hook_angle,
                expected="ToneValidator.validate() == True",
                actual=f"{hook_passes_tone}",
                passed=hook_passes_tone,
            )

            # Check 4: Hook angle contains natural KOC markers
            hook_has_koc = ToneValidator.has_koc_markers(res.hook_angle)
            self.record(
                category=category,
                case_name=f"{cat_name}_hook_has_koc_markers",
                input_data=res.hook_angle,
                expected="ToneValidator.has_koc_markers() == True",
                actual=f"{hook_has_koc}",
                passed=hook_has_koc,
            )

        # Check 5: Prompt template contract compliance
        persona_ok = (
            HOMELIFE_PERSONA.get("name") == "Nam Minh"
            and HOMELIFE_PERSONA.get("voice_name") == "vi-VN-NamMinhNeural"
        )
        self.record(
            category=category,
            case_name="homelife_persona_contract",
            input_data="HOMELIFE_PERSONA",
            expected="name='Nam Minh', voice_name='vi-VN-NamMinhNeural'",
            actual=f"name='{HOMELIFE_PERSONA.get('name')}', voice='{HOMELIFE_PERSONA.get('voice_name')}'",
            passed=persona_ok,
        )

        template_prompt_sample = build_homelife_evaluation_prompt({
            "product_id": "test_01",
            "title": "Cây lau nhà tự vắt",
            "price": 149000.0,
            "commission_rate": 0.18,
            "sales_30d": 3000,
        })
        prompt_ok = "Cây lau nhà tự vắt" in template_prompt_sample and "149,000" in template_prompt_sample
        self.record(
            category=category,
            case_name="build_homelife_evaluation_prompt_contract",
            input_data="sample_product",
            expected="Formatted product metadata present in prompt",
            actual="Prompt built successfully",
            passed=prompt_ok,
        )

    # -------------------------------------------------------------------------
    # 5. CORRUPTED INPUTS AND CONCURRENCY
    # -------------------------------------------------------------------------
    def test_corrupted_inputs_and_concurrency(self) -> None:
        category = "5. Corrupted Inputs & Concurrency"

        corrupted_cases = [
            (None, "none_input"),
            ({}, "empty_dict"),
            ({"product_id": None}, "null_product_id"),
            ({"title": None}, "null_title"),
            ({"product_id": "", "title": ""}, "empty_strings"),
            ({"product_id": "   ", "title": "   "}, "whitespace_strings"),
            ("just_a_string", "string_instead_of_dict"),
            ([1, 2, 3], "list_instead_of_dict"),
            (12345, "integer_instead_of_dict"),
            (
                {"product_id": "c1", "title": "Cây lau", "price": "invalid_number"},
                "malformed_price_string",
            ),
            (
                {"product_id": "c2", "title": "Cây lau", "sales_30d": "not_an_int"},
                "malformed_sales_string",
            ),
            (
                {"product_id": "c3", "title": "Cây lau", "price": -50000},
                "negative_price_value",
            ),
            (
                {"product_id": "c4", "title": "Cây lau", "commission_rate": -0.2},
                "negative_commission_value",
            ),
        ]

        for data, name in corrupted_cases:
            try:
                res = self.agent.evaluate_product(data)
                is_safe = (
                    res.passed_filter is False
                    and res.score == 0.0
                    and res.rejection_reason is not None
                )
                actual_str = f"passed_filter={res.passed_filter}, score={res.score}, reason='{res.rejection_reason}'"
            except Exception as e:
                is_safe = False
                actual_str = f"CRASH: {type(e).__name__}: {e}"

            self.record(
                category=category,
                case_name=f"corrupted_{name}",
                input_data=str(data),
                expected="passed_filter=False, score=0.0, no exception raised",
                actual=actual_str,
                passed=is_safe,
            )

        # Concurrency stress test: 120 concurrent requests
        concurrent_count = 120
        items = [
            {
                "product_id": f"conc_{i}",
                "title": f"Cây lau nhà tự vắt {i} đa năng thông minh 3s",
                "price": 149000.0 + (i * 100),
                "commission_rate": 0.15,
                "sales_30d": 2000 + i,
                "rating": 4.8,
            }
            for i in range(concurrent_count)
        ]

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
                concurrent_results = list(executor.map(self.agent.evaluate_product, items))

            concurrency_passed = (
                len(concurrent_results) == concurrent_count
                and all(r.passed_filter is True for r in concurrent_results)
                and all(r.score >= 8.5 for r in concurrent_results)
            )
            actual_conc_str = f"{len(concurrent_results)} evaluations completed, all passed_filter=True, score>=8.5"
        except Exception as e:
            concurrency_passed = False
            actual_conc_str = f"CRASH: {type(e).__name__}: {e}"

        self.record(
            category=category,
            case_name=f"concurrency_{concurrent_count}_parallel_evaluations",
            input_data=f"{concurrent_count} items with 16 threads",
            expected=f"{concurrent_count} items evaluated safely with score >= 8.5",
            actual=actual_conc_str,
            passed=concurrency_passed,
            details="Thread-safety and parallel evaluation stress",
        )

    # -------------------------------------------------------------------------
    # RUNNER & SUMMARY
    # -------------------------------------------------------------------------
    def run_all(self) -> Dict[str, Any]:
        self.test_exaggerated_claims_bypass()
        self.test_pricing_boundaries()
        self.test_score_threshold_boundaries()
        self.test_hook_angle_and_viral_factor()
        self.test_corrupted_inputs_and_concurrency()

        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed

        by_cat: Dict[str, Dict[str, int]] = {}
        for r in self.results:
            cat_stats = by_cat.setdefault(r.category, {"total": 0, "passed": 0, "failed": 0})
            cat_stats["total"] += 1
            if r.passed:
                cat_stats["passed"] += 1
            else:
                cat_stats["failed"] += 1

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "by_category": by_cat,
        }

    def print_report(self) -> int:
        summary = self.run_all()
        print("=" * 80)
        print("AMAS v1.4.0 — MILESTONE 3 HOMELIFE SCOUT ADVERSARIAL STRESS TEST REPORT")
        print("=" * 80)
        print(f"Total Test Cases: {summary['total']}")
        print(f"Passed:           {summary['passed']}")
        print(f"Failed / Gaps:    {summary['failed']}")
        print("-" * 80)
        print("BREAKDOWN BY CATEGORY:")
        for cat, stats in summary["by_category"].items():
            rate = (stats["passed"] / stats["total"]) * 100 if stats["total"] > 0 else 0
            print(f"  - {cat:<35}: {stats['passed']:>2}/{stats['total']:<2} passed ({rate:>5.1f}%)")
        print("=" * 80)
        print("\nDETAILED TEST RESULTS:")
        for r in self.results:
            status = "PASS" if r.passed else "FAIL"
            marker = "✅" if r.passed else "❌"
            print(f"{marker} [{status}] [{r.category}] {r.case_name}")
            print(f"     Input:    {r.input_data!r}")
            print(f"     Expected: {r.expected}")
            print(f"     Actual:   {r.actual}")
            if r.details:
                print(f"     Details:  {r.details}")
            print()

        # Exit code: 1 if any test failed, 0 if 100% passed
        return 1 if summary["failed"] > 0 else 0


if __name__ == "__main__":
    harness = HomeLifeAdversarialHarness()
    exit_code = harness.print_report()
    sys.exit(exit_code)
