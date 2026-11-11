"""AMAS v1.4.0 — Milestone 1 Empirical Stress Test Harness & Adversarial Generator.

Focus areas:
1. Anti-Robotic ToneValidator: Adversarial variations of robotic cliches
2. Anti-Counterfeit ToneValidator: Counterfeit brand mentions with tricky punctuation / casing
3. False-Positive Resistance: Legitimate Vietnamese words containing substrings like 'lv', 'rep'
4. Central Config Loader: Malformed YAML, missing fields, invalid types, None-value env overrides
"""

from __future__ import annotations

import os
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple
import yaml
from pydantic import ValidationError

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.config import AppConfig, load_config
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


class EmpiricalStressHarness:
    def __init__(self) -> None:
        self.results: List[TestResult] = []

    def record(self, category: str, case_name: str, input_data: Any, expected: str, actual: str, passed: bool, details: str = "") -> None:
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
    # 1. COUNTERFEIT BRAND EVASION & DETECTION
    # -------------------------------------------------------------------------
    def test_counterfeits(self) -> None:
        category = "Counterfeit Detection"

        # Baseline expected to be blocked
        blocked_baseline = [
            ("rep 1:1 standard", "Váy hoa rep 1:1 cực xịn", False),
            ("REP 1:1 uppercase", "Váy hoa REP 1:1 cực xịn", False),
            ("rep 1-1 dash", "Áo thun rep 1-1 bao nét", False),
            ("rep 1/1 slash", "Đầm nữ rep 1/1", False),
            ("rep 1 1 space", "Túi xách rep 1 1 sang chảnh", False),
            ("like auth", "Váy Zara like auth chuẩn nét", False),
            ("LIKE AUTH uppercase", "Giày LIKE AUTH cao cấp", False),
            ("super fake", "Đồng hồ super fake loại 1", False),
            ("SUPER FAKE uppercase", "Túi SUPER FAKE da bò", False),
            ("hang fake", "Quần bò hang fake xuất xịn", False),
            ("hàng f1", "Áo khoác hàng f1 cao cấp", False),
            ("LV uppercase boundary", "Túi LV cao cấp", False),
            ("LV in quotes", 'Túi "LV" xách tay', False),
            ("LV with comma", "Túi LV, mẫu mới nhất", False),
            ("LV with exclamation", "Túi LV! Siêu hot", False),
        ]

        for name, text, expected_valid in blocked_baseline:
            is_valid = ToneValidator.validate(text)
            violations = ToneValidator.check_violations(text)
            passed = (is_valid == expected_valid)
            self.record(
                category,
                name,
                text,
                f"Valid={expected_valid}",
                f"Valid={is_valid} (Violations: {violations})",
                passed,
            )

        # Adversarial evasion variations (counterfeits that SHOULD be blocked, but might evade)
        adversarial_counterfeits = [
            ("rep 1.1 with dot", "Túi xách rep 1.1 bao đẹp", False),
            ("rep-1:1 with hyphen prefix", "Đầm thiết kế rep-1:1 xịn", False),
            ("like-auth with hyphen", "Giày like-auth cực xịn", False),
            ("super-fake with hyphen", "Đầm body super-fake loại 1", False),
            ("super_fake with underscore", "Ví nữ super_fake bao nét", False),
            ("fake 1:1 standalone", "Áo phông fake 1:1 cao cấp", False),
            ("fake 1 without hàng", "Giày fake 1 siêu cấp", False),
            ("áo fake without hàng", "Áo fake loại 1 chất xịn", False),
            ("giày fake without hàng", "Giày fake cực êm chân", False),
        ]

        for name, text, expected_valid in adversarial_counterfeits:
            is_valid = ToneValidator.validate(text)
            violations = ToneValidator.check_violations(text)
            passed = (is_valid == expected_valid)
            self.record(
                category,
                f"[Adversarial] {name}",
                text,
                f"Valid={expected_valid} (Must Block)",
                f"Valid={is_valid} (Violations: {violations})",
                passed,
                details="EVASION DETECTED" if is_valid is True else "BLOCKED",
            )

    # -------------------------------------------------------------------------
    # 2. ROBOTIC CLICHÉS EVASION & DETECTION
    # -------------------------------------------------------------------------
    def test_robotic_cliches(self) -> None:
        category = "Robotic Clichés"

        # Baseline expected to be blocked
        blocked_baseline = [
            ("xin chào quý khách", "Xin chào quý khách, shop em có khuyến mãi", False),
            ("chào mừng quý khách", "Chào mừng quý khách đến với kênh", False),
            ("kính chào quý khách", "Kính chào quý khách ghé thăm gian hàng", False),
            ("tôi là trợ lý ảo", "Tôi là trợ lý ảo hỗ trợ đặt hàng", False),
            ("tôi là ai", "Tôi là AI tư vấn sản phẩm", False),
            ("tôi là một mô hình ngôn ngữ", "Tôi là một mô hình ngôn ngữ được tạo bởi OpenAI", False),
            ("sản phẩm này rất tốt và tiện ích", "Sản phẩm này rất tốt và tiện ích cho mọi nhà", False),
            ("sự lựa chọn hoàn hảo", "Đây chính là sự lựa chọn hoàn hảo", False),
            ("giải pháp hoàn hảo", "Giải pháp hoàn hảo cho căn bếp", False),
            ("hãy nhanh tay sở hữu", "Hãy nhanh tay sở hữu ngay em váy này", False),
            ("sở hữu ngay hôm nay", "Sở hữu ngay hôm nay để nhận ưu đãi", False),
            ("cảm ơn quý khách đã tin tưởng", "Cảm ơn quý khách đã tin tưởng ủng hộ", False),
            ("chúc quý khách một ngày tốt lành", "Chúc quý khách một ngày tốt lành nha", False),
        ]

        for name, text, expected_valid in blocked_baseline:
            is_valid = ToneValidator.validate(text)
            violations = ToneValidator.check_violations(text)
            passed = (is_valid == expected_valid)
            self.record(
                category,
                name,
                text,
                f"Valid={expected_valid}",
                f"Valid={is_valid} (Violations: {violations})",
                passed,
            )

        # Adversarial polite greetings & AI variations that SHOULD ideally be caught
        adversarial_robotic = [
            ("chào quý khách (without xin)", "Chào quý khách, hôm nay shop sale lớn ạ", False),
            ("dạ em chào quý khách ạ", "Dạ em chào quý khách ạ, có gì cần tư vấn không ạ?", False),
            ("chào mừng bạn đến với shop", "Chào mừng bạn đến với shop của chúng tôi", False),
            ("tôi là một trợ lý ảo", "Tôi là một trợ lý ảo của cửa hàng", False),
            ("như một mô hình AI", "Như một mô hình AI, tôi xin giới thiệu bộ sưu tập mới", False),
            ("hy vọng thông tin này hữu ích", "Hy vọng thông tin này hữu ích cho bạn nhé", False),
            ("dưới đây là danh sách gợi ý", "Dưới đây là một số gợi ý dành riêng cho bạn", False),
        ]

        for name, text, expected_valid in adversarial_robotic:
            is_valid = ToneValidator.validate(text)
            violations = ToneValidator.check_violations(text)
            passed = (is_valid == expected_valid)
            self.record(
                category,
                f"[Adversarial] {name}",
                text,
                f"Valid={expected_valid} (Robotic Cliché)",
                f"Valid={is_valid} (Violations: {violations})",
                passed,
                details="ROBOTIC LEAK / EVASION" if is_valid is True else "BLOCKED",
            )

    # -------------------------------------------------------------------------
    # 3. FALSE POSITIVE TRAPS (LEGITIMATE VIETNAMESE WORDS)
    # -------------------------------------------------------------------------
    def test_false_positive_traps(self) -> None:
        category = "False Positive Resistance"

        valid_vietnamese_cases = [
            ("lực lượng (contains 'l' and 'v' related sounds)", "Lực lượng lao động trẻ trung năng động"),
            ("lưu trữ (contains 'l' and 'v' letters)", "Hộp đựng thực phẩm giúp lưu trữ đồ ăn tươi ngon"),
            ("ly nước (contains 'ly')", "Ly nước thủy tinh chịu nhiệt siêu xinh"),
            ("quản lý (contains 'lý')", "Quản lý việc nhà nhàn tênh với máy hút bụi mini"),
            ("rep tin nhắn (legitimate social phrase)", "Shop ơi rep tin nhắn em check size với ạ"),
            ("rep inbox (legitimate social phrase)", "Chị ơi nhớ rep inbox em đặt hàng nha"),
            ("rep cmt (legitimate social phrase)", "Đang bận rep cmt cho các bà đây"),
            ("vải crepe (fashion fabric contains 'rep')", "Chân váy chữ A chất vải crepe cao cấp tôn dáng"),
            ("món nhái chiên giòn (culinary term contains 'nhái')", "Nồi chiên không dầu làm món nhái chiên giòn rụm"),
        ]

        for name, text in valid_vietnamese_cases:
            is_valid = ToneValidator.validate(text)
            violations = ToneValidator.check_violations(text)
            # Legitimate Vietnamese text MUST have 0 violations and Valid=True
            passed = (is_valid is True and len(violations) == 0)
            self.record(
                category,
                name,
                text,
                "Valid=True, Violations=[]",
                f"Valid={is_valid}, Violations={violations}",
                passed,
                details="FALSE POSITIVE DETECTED" if not passed else "ZERO FALSE POSITIVE",
            )

    # -------------------------------------------------------------------------
    # 4. CONFIG LOADER STRESS & PYDANTIC VALIDATION
    # -------------------------------------------------------------------------
    def test_config_loader(self) -> None:
        category = "Config Resilience"

        # Case 4.1: Missing file raises FileNotFoundError
        try:
            load_config("non_existent_config_file_xyz.yaml")
            self.record(category, "missing_file", "non_existent_path", "Raises FileNotFoundError", "Did not raise", False)
        except FileNotFoundError:
            self.record(category, "missing_file", "non_existent_path", "Raises FileNotFoundError", "FileNotFoundError", True)
        except Exception as e:
            self.record(category, "missing_file", "non_existent_path", "Raises FileNotFoundError", type(e).__name__, False)

        # Case 4.2: Corrupted YAML syntax raises yaml.YAMLError
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
            f.write("corrupted: [syntax: unclosed brace\n  invalid yaml")
            corrupt_path = f.name
        try:
            load_config(corrupt_path)
            self.record(category, "corrupted_yaml_syntax", "bad syntax", "Raises yaml.YAMLError", "Did not raise", False)
        except yaml.YAMLError as e:
            self.record(category, "corrupted_yaml_syntax", "bad syntax", "Raises yaml.YAMLError", f"yaml.{type(e).__name__}", True)
        except Exception as e:
            self.record(category, "corrupted_yaml_syntax", "bad syntax", "Raises yaml.YAMLError", type(e).__name__, False)

        # Case 4.3: Missing required fields in NicheConfig raises pydantic.ValidationError
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
            f.write("""
niches:
  - name: "Thời trang"
    # missing niche_id and persona
""")
            missing_fields_path = f.name
        try:
            load_config(missing_fields_path)
            self.record(category, "missing_required_fields", "missing niche_id & persona", "Raises ValidationError", "Did not raise", False)
        except ValidationError as e:
            self.record(category, "missing_required_fields", "missing niche_id & persona", "Raises ValidationError", f"ValidationError (errors: {e.error_count()})", True)
        except Exception as e:
            self.record(category, "missing_required_fields", "missing niche_id & persona", "Raises ValidationError", type(e).__name__, False)

        # Case 4.4: Invalid types and out-of-bounds numbers raise ValidationError
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
            f.write("""
browser:
  behavior:
    typo_rate: 2.5 # max is 0.5
    typing_min_delay_ms: "invalid_string"
database:
  pool_size: -10 # min is 1
""")
            invalid_types_path = f.name
        try:
            load_config(invalid_types_path)
            self.record(category, "invalid_data_types_and_bounds", "typo_rate=2.5, pool_size=-10", "Raises ValidationError", "Did not raise", False)
        except ValidationError as e:
            self.record(category, "invalid_data_types_and_bounds", "typo_rate=2.5, pool_size=-10", "Raises ValidationError", f"ValidationError (errors: {e.error_count()})", True)
        except Exception as e:
            self.record(category, "invalid_data_types_and_bounds", "typo_rate=2.5, pool_size=-10", "Raises ValidationError", type(e).__name__, False)

        # Case 4.5: Non-dict root (e.g. list at top level) raises ValidationError
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
            f.write("- item1\n- item2\n")
            list_path = f.name
        try:
            load_config(list_path)
            self.record(category, "non_dict_yaml_root", "list at root", "Raises ValidationError", "Did not raise", False)
        except ValidationError:
            self.record(category, "non_dict_yaml_root", "list at root", "Raises ValidationError", "ValidationError", True)
        except Exception as e:
            self.record(category, "non_dict_yaml_root", "list at root", "Raises ValidationError", type(e).__name__, False)

        # Case 4.6: None-value section in YAML when env var is set (CRASH TEST)
        os.environ["POSTGRES_URL"] = "postgresql+asyncpg://test:pass@localhost/db"
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
            f.write("""
app_name: "TEST_APP"
database: # parsed as None
telegram: # parsed as None
""")
            none_section_path = f.name
        try:
            load_config(none_section_path)
            self.record(category, "none_section_with_env_override", "database: None + POSTGRES_URL set", "AppConfig loaded successfully", "Success", True)
        except TypeError as e:
            self.record(category, "none_section_with_env_override", "database: None + POSTGRES_URL set", "AppConfig loaded successfully", f"TypeError: {e}", False, details="BUG: setdefault on None key")
        except Exception as e:
            self.record(category, "none_section_with_env_override", "database: None + POSTGRES_URL set", "AppConfig loaded successfully", type(e).__name__, False)

    # -------------------------------------------------------------------------
    # RUNNER & SUMMARY
    # -------------------------------------------------------------------------
    def run_all(self) -> Dict[str, Any]:
        self.test_counterfeits()
        self.test_robotic_cliches()
        self.test_false_positive_traps()
        self.test_config_loader()

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

    def print_report(self) -> None:
        summary = self.run_all()
        print("=" * 80)
        print("AMAS v1.4.0 — MILESTONE 1 EMPIRICAL ADVERSARIAL STRESS TEST REPORT")
        print("=" * 80)
        print(f"Total Test Cases: {summary['total']}")
        print(f"Passed:           {summary['passed']}")
        print(f"Failed / Gaps:    {summary['failed']}")
        print("-" * 80)
        print("BREAKDOWN BY CATEGORY:")
        for cat, stats in summary["by_category"].items():
            rate = (stats["passed"] / stats["total"]) * 100 if stats["total"] > 0 else 0
            print(f"  - {cat:<28}: {stats['passed']:>2}/{stats['total']:<2} passed ({rate:>5.1f}%)")
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


if __name__ == "__main__":
    harness = EmpiricalStressHarness()
    harness.print_report()
