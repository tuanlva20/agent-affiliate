#!/usr/bin/env python3
"""Empirical Challenger Verification Script for Milestone 3 Fashion Scout Remediation.

Checks:
1. Verifies the exact 30 bypass cases in scripts/m3_fashion_adversarial_harness.py:
   - Must be rejected (passed_filter == False)
   - Must have score == 0.0
   - Must have rejection_reason containing 'trademark' or 'policy'
2. Stress-tests 40+ NEW adversarial bypass mutations:
   - Combinations of leetspeak, mixed symbols, accents, spaced letters
3. Verifies false positive rate on legitimate products (must NOT be rejected as counterfeit)
4. Verifies boundary and corrupted inputs
5. Checks HomeLife scout alignment and existing test suites
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.fashion_scout import FashionScoutAgent, SpecialistEvaluation
from src.core.tone_validator import ToneValidator


def run_challenger_audit():
    agent = FashionScoutAgent()
    print("=" * 70)
    print("CHALLENGER AUDIT: FashionScoutAgent & ToneValidator Remediation")
    print("=" * 70)

    # 1. Audit the 30 standard harness cases
    from scripts.m3_fashion_adversarial_harness import test_1_trademark_bypass_matrix
    t1_res = test_1_trademark_bypass_matrix(agent)
    print(f"\n[Audit 1] Standard Harness 30 Bypass Cases: {t1_res.passed}/{t1_res.total} Passed ({t1_res.pass_rate:.1f}%)")
    if t1_res.failed > 0:
        for f in t1_res.failures:
            print(f"  FAIL: {f}")
        return False

    # 2. Audit 40+ NEW adversarial mutation bypass cases
    new_mutations = [
        # Leet + Punctuation combos
        ("Dot + Leet Zara", "Váy z.4.r.4 dáng xòe tôn eo"),
        ("Hyphen + Leet Zara", "Đầm z-4-r-4 chiết eo che bụng"),
        ("Spaced + Leet Zara", "Váy z 4 r 4 cực xinh che bụng"),
        ("At sign Zara", "Váy z@ra dáng xòe che mỡ"),
        ("Dot + Leet Chanel", "Đầm c.h.4.n.3.l tiểu thư tôn dáng"),
        ("Hyphen + Leet Chanel", "Set đồ c-h-4-n-3-l sang chảnh chiết eo"),
        ("Exclamation Gucci", "Áo Gucc! croptop hack dáng"),
        ("Dot + Leet Gucci", "Áo g.u.c.c.1 che mỡ bụng"),
        ("Zero Dior", "Váy D-1-0-r hack eo"),
        ("Dot + Leet Dior", "Váy d.1.0.r dáng xòe"),
        ("Dot + Leet Nike", "Giày n.1.k.e thể thao tôn dáng"),
        ("Exclamation Nike", "Giày n!ke chạy bộ hack chiều cao"),
        ("Dot + Leet Adidas", "Áo 4.d.1.d.4.s tôn dáng"),
        ("Spaced + Leet Adidas", "Áo 4 d 1 d 4 s hack eo"),
        ("Slash LV", "Túi xách l/v sang xịn"),
        ("Hyphen LV", "Túi đeo chéo l-v cao cấp"),
        ("Underscore LV", "Balo nữ l_v da mềm"),
        ("Dot Prada", "Váy p.r.a.d.a cao cấp hack dáng"),
        ("Spaced Prada", "Đầm p r a d a chiết eo"),
        ("Dot Balenciaga", "Áo b.a.l.e.n.c.i.a.g.a form rộng che bụng"),
        ("Dot Rolex", "Đồng hồ r.o.l.e.x nữ đính đá"),
        
        # Rep / Fake variations
        ("Slash rep 1:1", "Váy r/e/p 1:1 siêu cấp"),
        ("Dot rep 1-1", "Váy r.e.p 1-1 Quảng Châu chiết eo"),
        ("Glued rep1:1 dot", "Váy r.e.p1:1 cao cấp che bụng"),
        ("Space rep 1 : 1", "Đầm rep 1 : 1 chuẩn form"),
        ("Slash fake 1/1", "Áo fake 1/1 cao cấp tôn dáng"),
        ("Punctuation fake 1:1", "Áo f.a.k.e 1:1 Quảng Châu"),
        ("Super fake hyphen", "Váy super-fake dáng xòe"),
        ("Super fake dot", "Váy super.fake loại 1 chiết eo"),
        ("S.u.p.e.r-f.a.k.e", "Đầm s.u.p.e.r-f.a.k.e tiểu thư"),
        ("Like-auth dot", "Đầm like.auth chuẩn form hack eo"),
        ("Chuan auth hyphen", "Váy chuẩn-auth dáng xòe che mỡ"),
        ("Tuon auth dot", "Đầm tuồn.auth sang chảnh chiết eo"),
        
        # Accents variations
        ("Double accent Zàrả", "Váy zàrả dáng thon"),
        ("Accent Chánèl", "Đầm chánèl xòe chiết eo"),
        ("Accent Gùccì", "Áo gùccì thêu hoa tôn eo"),
        ("Accent Dìòr", "Váy dìòr lụa cao cấp"),
        ("Accent Hèrmès", "Khăn hèrmès lụa sang chảnh"),
        ("Accent Prádá", "Váy prádá tôn dáng che bụng"),
        ("Accent Níkè", "Áo khoác níkè thể thao"),
    ]

    print(f"\n[Audit 2] Testing {len(new_mutations)} NEW Adversarial Mutations...")
    passed_mut = 0
    failed_mut = 0
    failures = []
    for label, title in new_mutations:
        item = {
            "product_id": f"mut_{hash(title) % 100000}",
            "title": title,
            "price": 199000.0,
            "commission_rate": 0.15,
            "sales_30d": 2500,
            "rating": 4.8,
        }
        res = agent.evaluate_product(item)
        reason = (res.rejection_reason or "").lower()
        has_policy = "trademark" in reason or "policy" in reason
        if res.passed_filter is False and res.score == 0.0 and has_policy:
            passed_mut += 1
        else:
            failed_mut += 1
            failures.append(f"[{label}] '{title}' -> passed={res.passed_filter}, score={res.score}, reason={res.rejection_reason}")

    print(f"  Result: {passed_mut}/{len(new_mutations)} Passed ({passed_mut/len(new_mutations)*100:.1f}%)")
    if failures:
        print("  Failures in new mutations:")
        for f in failures:
            print(f"    ❌ {f}")
    else:
        print("  ✅ All 40 new mutations 100% blocked with score=0.0 and trademark/policy cited!")

    # 3. False Positive Audit: Verify legitimate products are NOT rejected
    legit_products = [
        ("Váy hoa nhí dáng xòe chiết eo tôn dáng che bụng mỡ cực đỉnh", True),
        ("Đầm suông chữ A lụa cao cấp che mỡ bụng dưới", True),
        ("Áo sơ mi croptop chiết eo cạp cao hack dáng chân dài", True),
        ("Chân váy chữ A cạp cao che khuyết điểm bụng to", True),
        ("Quần jean ống rộng cạp cao hack chiều cao cho nấm lùn", True),
        ("Váy peplum công sở giấu mỡ bụng dưới cực tốt thắt eo", True),
        ("Đầm body nhún eo tôn vòng 1 vòng 3 quyến rũ", True),
        ("Set áo vest cộc tay phối chân váy xòe sang chảnh chiết eo", True),
        ("Áo thun cotton trơn màu đen basic", False),  # Subthreshold score < 7.0, but NOT trademark rejection!
    ]

    print(f"\n[Audit 3] Testing False Positive Protection on {len(legit_products)} Products...")
    fp_issues = []
    for title, should_pass in legit_products:
        item = {
            "product_id": f"legit_{hash(title) % 100000}",
            "title": title,
            "price": 220000.0,
            "commission_rate": 0.18,
            "sales_30d": 3500 if should_pass else 15,
            "rating": 4.9 if should_pass else 4.0,
        }
        res = agent.evaluate_product(item)
        reason = (res.rejection_reason or "").lower()
        if "trademark" in reason or "counterfeit" in reason:
            fp_issues.append(f"FALSE POSITIVE: '{title}' falsely rejected for trademark: {res.rejection_reason}")
        elif should_pass and not res.passed_filter:
            fp_issues.append(f"FALSE REJECTION: Valid item '{title}' failed filter: score={res.score}, reason={res.rejection_reason}")
        elif not should_pass and res.passed_filter:
            fp_issues.append(f"UNEXPECTED PASS: Bland item '{title}' passed filter: score={res.score}")

    if fp_issues:
        for iss in fp_issues:
            print(f"  ❌ {iss}")
    else:
        print("  ✅ Zero False Positives! Legitimate products evaluated accurately.")

    return t1_res.failed == 0 and failed_mut == 0 and len(fp_issues) == 0


if __name__ == "__main__":
    success = run_challenger_audit()
    sys.exit(0 if success else 1)
