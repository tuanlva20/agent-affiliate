#!/usr/bin/env python3
"""AMAS v1.4.0 — Milestone 5 Empirical Adversarial Stress Harness.

Target: Script Generator Service (F15) & ToneValidator Compliance.
Author: m5_challenger_1 (Empirical Challenger)

Directives Evaluated:
1. Adversarial Title Injections:
   - Obfuscated trademark names: Z.a.r.a, C.h.a.n.e.l, G.u.c.c.i, N.i.k.e, r.e.p 1:1,
     s.u.p.e.r f.a.k.e, l.i.k.e a.u.t.h, t.u.ồ.n a.u.t.h, etc.
   - Exaggerated & medical claims: trị dứt điểm 100%, vĩnh viễn không bám bẩn,
     chữa khỏi hoàn toàn, 100% không bao giờ hỏng.
   - Robotic clichés in title: sản phẩm hoàn hảo đáp ứng mọi nhu cầu,
     kính chào quý khách, hãy nhanh tay sở hữu.
   - Verifies that generated voiceover NEVER leaks these and ToneValidator.validate ALWAYS returns True.
   - Verifies that captions do not leak prohibited policy violations.
2. KOC Marker Guarantee:
   - 50+ diverse and unusual product titles across both niches.
   - ToneValidator.has_koc_markers(full_voiceover) is ALWAYS True.
   - All 5 contract keys exist and are non-empty strings.
3. Extreme / Corrupt Metadata Inputs:
   - None, empty dict, missing keys, non-string types, negative/NaN/Inf prices,
     massive 10,000-character strings, null bytes, corrupt persona arguments.
   - Ensures generate_script handles all gracefully without crashing.
4. Persona & Voice Mapping Integrity:
   - Fashion products -> vi-VN-HoaiMyNeural + female KOC markers (chị em, mấy bà, tui).
   - HomeLife products -> vi-VN-NamMinhNeural + male KOC markers (các bác, tui, 3s/nhàn).
   - Prevents persona cross-contamination under emergency fallback.
"""

from __future__ import annotations

import math
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.tone_validator import ToneValidator
from src.services.script_generator import KOCScriptResult, ScriptGenerator


class TestResult:
    """Tracks test assertions and failures for a suite."""

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


# ==============================================================================
# SUITE 1: ADVERSARIAL TITLE INJECTIONS & LEAKAGE
# ==============================================================================

def test_1_adversarial_title_injections(gen: ScriptGenerator) -> TestResult:
    """Tests resilience against obfuscated trademarks, exaggerated claims, and robotic clichés."""
    result = TestResult("Suite 1: Adversarial Title Injections & Leakage")

    adversarial_cases: List[Dict[str, Any]] = [
        # Trademarks & Counterfeit Obfuscations
        {"phrase": "Z.a.r.a", "clean": "zara", "niche": "thoi_trang_nu", "category": "trademark"},
        {"phrase": "C.h.a.n.e.l", "clean": "chanel", "niche": "thoi_trang_nu", "category": "trademark"},
        {"phrase": "G.u.c.c.i", "clean": "gucci", "niche": "thoi_trang_nu", "category": "trademark"},
        {"phrase": "N.i.k.e", "clean": "nike", "niche": "thoi_trang_nu", "category": "trademark"},
        {"phrase": "r.e.p 1:1", "clean": "rep 1:1", "niche": "thoi_trang_nu", "category": "counterfeit"},
        {"phrase": "s.u.p.e.r f.a.k.e", "clean": "super fake", "niche": "thoi_trang_nu", "category": "counterfeit"},
        {"phrase": "l.i.k.e a.u.t.h", "clean": "like auth", "niche": "thoi_trang_nu", "category": "counterfeit"},
        {"phrase": "t.u.ồ.n a.u.t.h", "clean": "tuồn auth", "niche": "thoi_trang_nu", "category": "counterfeit"},
        {"phrase": "t.u.o.n a.u.t.h", "clean": "tuon auth", "niche": "thoi_trang_nu", "category": "counterfeit"},
        {"phrase": "A.d.i.d.a.s", "clean": "adidas", "niche": "thoi_trang_nu", "category": "trademark"},
        {"phrase": "D.i.o.r", "clean": "dior", "niche": "thoi_trang_nu", "category": "trademark"},
        {"phrase": "L.V", "clean": "lv", "niche": "thoi_trang_nu", "category": "trademark"},

        # Exaggerated & Medical Claims
        {"phrase": "trị dứt điểm 100%", "clean": "trị dứt điểm", "niche": "do_gia_dung", "category": "exaggerated"},
        {"phrase": "vĩnh viễn không bám bẩn", "clean": "không bám bẩn", "niche": "do_gia_dung", "category": "exaggerated"},
        {"phrase": "chữa khỏi hoàn toàn", "clean": "chữa khỏi", "niche": "do_gia_dung", "category": "medical"},
        {"phrase": "100% không bao giờ hỏng", "clean": "không bao giờ hỏng", "niche": "do_gia_dung", "category": "exaggerated"},
        {"phrase": "thần dược gia đình", "clean": "thần dược", "niche": "do_gia_dung", "category": "medical"},
        {"phrase": "vĩnh viễn không rỉ sét", "clean": "không rỉ sét", "niche": "do_gia_dung", "category": "exaggerated"},

        # Robotic Clichés
        {"phrase": "sản phẩm hoàn hảo đáp ứng mọi nhu cầu", "clean": "đáp ứng mọi nhu cầu", "niche": "do_gia_dung", "category": "robotic"},
        {"phrase": "kính chào quý khách", "clean": "kính chào quý khách", "niche": "do_gia_dung", "category": "robotic"},
        {"phrase": "hãy nhanh tay sở hữu", "clean": "hãy nhanh tay sở hữu", "niche": "do_gia_dung", "category": "robotic"},
        {"phrase": "sự lựa chọn hoàn hảo", "clean": "sự lựa chọn hoàn hảo", "niche": "thoi_trang_nu", "category": "robotic"},
        {"phrase": "chào mừng quý khách đến với", "clean": "chào mừng quý khách", "niche": "thoi_trang_nu", "category": "robotic"},
        {"phrase": "rất hân hạnh được phục vụ", "clean": "rất hân hạnh được phục vụ", "niche": "do_gia_dung", "category": "robotic"},
    ]

    prefixes = ["Mẫu", "Chiếc", "Bộ", "Cây", "Hộp", "Áo", "Quần"]

    for item in adversarial_cases:
        phrase = item["phrase"]
        clean_target = item["clean"]
        niche = item["niche"]
        cat = item["category"]

        # Test across multiple title variations to ensure we test template slotting
        for prefix in prefixes[:2]:
            title = f"{prefix} {phrase} chính hãng cao cấp"
            meta = {"product_id": f"adv_{phrase[:4]}", "title": title, "niche_id": niche}
            script = gen.generate_script(meta)

            vo = script["full_voiceover"]
            vo_lower = vo.lower()

            # 1. Verify ToneValidator.validate(full_voiceover) ALWAYS returns True
            is_valid = ToneValidator.validate(vo)
            if is_valid:
                result.record_pass()
            else:
                violations = ToneValidator.check_violations(vo)
                result.record_fail(
                    f"[{cat}] ToneValidator failed for '{title}': {violations} | Voiceover: {vo[:100]}"
                )

            # 2. Verify that generated voiceover NEVER leaks the raw prohibited phrase or un-dotted form
            phrase_sub = re.escape(phrase)
            un_dotted = phrase.replace(".", "").lower()
            leaked_raw = bool(re.search(phrase_sub, vo, re.IGNORECASE))
            leaked_clean = clean_target.lower() in vo_lower or un_dotted in vo_lower

            if not leaked_raw and not (leaked_clean and un_dotted in ["nike", "adidas", "zara", "chanel", "gucci", "tuon auth", "tuồn auth"]):
                result.record_pass()
            else:
                result.record_fail(
                    f"[{cat}] Prohibited token '{phrase}' leaked into voiceover! Title: '{title}' | Voiceover: {vo[:100]}"
                )

            # 3. Verify caption does NOT contain the raw prohibited phrase
            caption = script.get("caption", "")
            if phrase.lower() not in caption.lower():
                result.record_pass()
            else:
                result.record_fail(
                    f"[{cat}] Prohibited token '{phrase}' leaked into caption: '{caption}'"
                )

    return result


# ==============================================================================
# SUITE 2: KOC MARKER GUARANTEE & CONTRACT INTEGRITY (50+ TITLES)
# ==============================================================================

def test_2_koc_marker_and_contract_guarantee(gen: ScriptGenerator) -> TestResult:
    """Verifies that across 50+ diverse and unusual titles, KOC markers and all contract keys exist."""
    result = TestResult("Suite 2: KOC Marker Guarantee & Contract Integrity")

    diverse_titles: List[Tuple[str, str]] = [
        # Fashion products
        ("Quần ống loe cạp cao gen bụng thon eo", "thoi_trang_nu"),
        ("Áo croptop cổ vuông ôm body quyến rũ", "thoi_trang_nu"),
        ("Chân váy xếp ly dáng dài công sở thanh lịch", "thoi_trang_nu"),
        ("Set blazer dạ tweed sang chảnh tiểu thư", "thoi_trang_nu"),
        ("Đầm suông đuôi cá họa tiết hoa nhí vintage", "thoi_trang_nu"),
        ("Áo len tăm cổ lọ mềm mịn giữ nhiệt", "thoi_trang_nu"),
        ("Quần jean baggy rách gối cá tính năng động", "thoi_trang_nu"),
        ("Váy yếm kaki phong cách ulzzang Hàn Quốc", "thoi_trang_nu"),
        ("Áo phông oversize cotton 100% thấm hút", "thoi_trang_nu"),
        ("Áo sơ mi lụa hàn phối nơ cổ điệu đà", "thoi_trang_nu"),
        ("Đầm body ôm sát khoét lưng gợi cảm tôn dáng", "thoi_trang_nu"),
        ("Chân váy chữ A kaki túi hộp trẻ trung", "thoi_trang_nu"),
        ("Quần culottes lụa ống rộng bay tà mát mẻ", "thoi_trang_nu"),
        ("Set đồ ngủ pijama lụa satin cao cấp", "thoi_trang_nu"),
        ("Áo khoác gió 2 lớp chống nước cản gió", "thoi_trang_nu"),
        ("Váy công chúa dự tiệc đính ngọc lấp lánh", "thoi_trang_nu"),
        ("Áo polo cộc tay form rộng unisex", "thoi_trang_nu"),
        ("Quần đùi thun thể thao tập gym yoga", "thoi_trang_nu"),
        ("Bộ mặc nhà tay lửng thun cotton mềm mát", "thoi_trang_nu"),
        ("Chân váy jean xẻ tà hack chân dài miên man", "thoi_trang_nu"),
        ("Đầm maxi hoa đi biển bồng bềnh sống ảo", "thoi_trang_nu"),
        ("Áo gile len dáng rộng phối sơ mi học sinh", "thoi_trang_nu"),
        ("Quần tây baggy cạp cao che bụng dưới", "thoi_trang_nu"),
        ("Váy đuôi tôm dự tiệc quyến rũ sang trọng", "thoi_trang_nu"),
        ("Áo thun ba lỗ nữ ôm sát basic", "thoi_trang_nu"),

        # HomeLife products
        ("Chổi lau nhà thông minh tự vắt 360 độ", "do_gia_dung"),
        ("Nồi chiên không dầu 8 lít đa năng cảm ứng", "do_gia_dung"),
        ("Máy hút bụi cầm tay không dây sạc pin công suất lớn", "do_gia_dung"),
        ("Kệ để đồ nhà tắm dán tường inox 304 không gỉ", "do_gia_dung"),
        ("Bộ dao làm bếp 6 món thép rèn nguyên khối", "do_gia_dung"),
        ("Hộp đựng cơm giữ nhiệt 3 tầng inox văn phòng", "do_gia_dung"),
        ("Máy xay sinh tố mini cầm tay sạc pin usb tiện lợi", "do_gia_dung"),
        ("Dụng cụ gọt hoa quả thông minh xoay tự động", "do_gia_dung"),
        ("Thớt kháng khuẩn inox 2 mặt chống mốc", "do_gia_dung"),
        ("Thảm chùi chân siêu thấm hút chống trượt nhà tắm", "do_gia_dung"),
        ("Giá treo quần áo gấp gọn thông minh gắn tường", "do_gia_dung"),
        ("Đèn ngủ cảm ứng chuyển động tự động bật tắt", "do_gia_dung"),
        ("Cây gạt nước sàn nhà silicone sạch bóng", "do_gia_dung"),
        ("Máy ép chậm mini ép kiệt bã giữ trọn vitamin", "do_gia_dung"),
        ("Bình giữ nhiệt 1 lít inox 316 hiển thị nhiệt độ", "do_gia_dung"),
        ("Hộp chia ngăn tủ quần áo đựng đồ lót gọn gàng", "do_gia_dung"),
        ("Khay hứng nước rửa chén có vòi thoát thông minh", "do_gia_dung"),
        ("Bộ nhả kem đánh răng tự động khử khuẩn tia UV", "do_gia_dung"),
        ("Máy làm sữa hạt đa năng 1.5L không cần lọc", "do_gia_dung"),
        ("Cân điện tử thông minh đo 14 chỉ số mỡ cơ thể", "do_gia_dung"),
        ("Nồi lẩu nướng 2 ngăn đa năng tiện lợi gia đình", "do_gia_dung"),
        ("Máy xịt rửa xe cao áp sạc pin mini không dây", "do_gia_dung"),
        ("Hộp đựng gia vị 4 ngăn nắp gập kèm muỗng", "do_gia_dung"),
        ("Kệ để giày dép 5 tầng khung thép chịu lực", "do_gia_dung"),
        ("Máy sấy tóc ion âm bảo vệ tóc không xơ rối", "do_gia_dung"),

        # Unusual / Boundary titles (symbols, emojis, numbers, mixed)
        ("🔥 Siêu phẩm hot trend 2026! Đồ gia dụng cực xịn ✨", "do_gia_dung"),
        (">>> [FLASH SALE 50%] <<< Váy xinh công sở sang xịn mịn", "thoi_trang_nu"),
        ("Sản phẩm mã #12345-ABC 2026 New Version", "thoi_trang_nu"),
        ("Combo 3 trong 1 siêu tiết kiệm cho mẹ bỉm", "do_gia_dung"),
        ("Thiết bị 4.0 gia dụng tự động thế hệ mới", "do_gia_dung"),
        ("Tiếng Việt có dấu đầy đủ: Ắ, Ằ, Ẳ, Ẵ, Ặ, Ế, Ề, Ể, Ỗ", "thoi_trang_nu"),
        ("Váy babydoll bồng bềnh 👗 outfit dễ thương", "thoi_trang_nu"),
        ("Dụng cụ bếp 🍳🥘🧹 đa năng tiện ích", "do_gia_dung"),
    ]

    required_keys = ["hook_3s", "body", "cta_yellow_cart", "caption", "full_voiceover"]

    for title, niche in diverse_titles:
        meta = {"title": title, "niche_id": niche, "price": 199000.0}
        script = gen.generate_script(meta)
        d = script.to_dict()

        # 1. Verify all 5 contract keys exist and are non-empty strings
        for k in required_keys:
            if k in d and isinstance(d[k], str) and len(d[k].strip()) > 0:
                result.record_pass()
            else:
                result.record_fail(f"Title '{title[:30]}': Key '{k}' missing, non-string, or empty!")

        # 2. Verify ToneValidator.has_koc_markers(full_voiceover) ALWAYS returns True
        vo = script.get("full_voiceover", "")
        if ToneValidator.has_koc_markers(vo):
            result.record_pass()
        else:
            result.record_fail(f"Title '{title[:30]}': ToneValidator.has_koc_markers is False! VO: {vo[:80]}")

        # 3. Verify ToneValidator.validate(full_voiceover) is True
        if ToneValidator.validate(vo):
            result.record_pass()
        else:
            result.record_fail(
                f"Title '{title[:30]}': ToneValidator.validate is False! Violations: {ToneValidator.check_violations(vo)}"
            )

        # 4. Verify reasonable duration bounds (15s - 60s)
        dur = script.estimated_duration_sec
        if 15.0 <= dur <= 60.0:
            result.record_pass()
        else:
            result.record_fail(f"Title '{title[:30]}': estimated_duration_sec={dur} out of bounds (15-60)!")

    return result


# ==============================================================================
# SUITE 3: EXTREME & CORRUPT METADATA INPUT FUZZING
# ==============================================================================

def test_3_extreme_and_corrupt_inputs(gen: ScriptGenerator) -> TestResult:
    """Fuzzes generate_script with malformed, empty, negative, NaN, huge strings, and unexpected types."""
    result = TestResult("Suite 3: Extreme & Corrupt Metadata Inputs")

    corrupt_cases: List[Tuple[str, Any, Any]] = [
        ("None metadata", None, None),
        ("Empty dictionary", {}, None),
        ("Dict missing title", {"niche_id": "thoi_trang_nu"}, None),
        ("Dict missing niche_id", {"title": "Áo sơ mi lụa"}, None),
        ("Integer title", {"title": 987654321}, None),
        ("None title", {"title": None}, None),
        ("List title", {"title": ["Áo", "váy", "đẹp"]}, None),
        ("Dict title", {"title": {"nested": "value"}}, None),
        ("Float title", {"title": 3.14159265}, None),
        ("Negative price", {"title": "Váy đẹp", "price": -150000.0}, None),
        ("Zero price", {"title": "Váy đẹp", "price": 0.0}, None),
        ("NaN price", {"title": "Váy đẹp", "price": float("nan")}, None),
        ("Inf price", {"title": "Váy đẹp", "price": float("inf")}, None),
        ("-Inf price", {"title": "Váy đẹp", "price": float("-inf")}, None),
        ("Huge price", {"title": "Váy đẹp", "price": 10**18}, None),
        ("Negative sales", {"title": "Váy đẹp", "sales_count": -500}, None),
        ("Non-numeric commission", {"title": "Váy đẹp", "commission_rate": "invalid_rate"}, None),
        ("Massive title (10,000 characters)", {"title": "A" * 10000}, None),
        ("Whitespace only title", {"title": "    \t\n   "}, None),
        ("Null byte in title", {"title": "Váy\x00dạ\x00hội"}, None),
        ("Control chars in title", {"title": "Váy\r\n\t\b\f\v đẹp"}, None),
        ("None niche_id", {"title": "Váy đẹp", "niche_id": None}, None),
        ("Integer niche_id", {"title": "Váy đẹp", "niche_id": 12345}, None),
        ("Unknown niche_id", {"title": "Váy đẹp", "niche_id": "unsupported_xyz"}, None),
        # Corrupt persona parameter
        ("Integer persona param", {"title": "Váy đẹp"}, 9999),
        ("List persona param", {"title": "Váy đẹp"}, ["persona"]),
        ("Dict persona without name", {"title": "Váy đẹp"}, {"foo": "bar"}),
        ("Object persona param", {"title": "Váy đẹp"}, object()),
    ]

    for label, meta, persona_param in corrupt_cases:
        try:
            script = gen.generate_script(meta, persona=persona_param)
            result.record_pass()  # Handled without crash

            # Contract keys must still be non-empty strings
            d = script.to_dict()
            all_valid = all(
                k in d and isinstance(d[k], str) and len(d[k].strip()) > 0
                for k in ["hook_3s", "body", "cta_yellow_cart", "caption", "full_voiceover"]
            )
            if all_valid:
                result.record_pass()
            else:
                result.record_fail(f"{label}: One or more contract keys empty or non-string!")

            # Full voiceover must pass ToneValidator
            if ToneValidator.validate(script.full_voiceover):
                result.record_pass()
            else:
                result.record_fail(f"{label}: ToneValidator failed on corrupt input result!")

        except Exception as e:
            result.record_fail(f"{label}: Unhandled exception raised: {type(e).__name__}: {e}")

    return result


# ==============================================================================
# SUITE 4: PERSONA & VOICE MAPPING INTEGRITY
# ==============================================================================

def test_4_persona_and_voice_mapping_integrity(gen: ScriptGenerator) -> TestResult:
    """Verifies persona assignment, voice IDs, and marker integrity for Fashion vs HomeLife."""
    result = TestResult("Suite 4: Persona & Voice Mapping Integrity")

    fashion_prods = [
        {"title": "Đầm xòe hoa nhí chiết eo", "niche_id": "thoi_trang_nu"},
        {"title": "Chân váy chữ A cạp cao", "niche_id": "thoi_trang_nu"},
        {"title": "Áo blazer tôn dáng giấu mỡ", "niche_id": "thoi_trang_nu"},
        {"title": "Quần tây ống đứng hack chân", "niche_id": "thoi_trang_nu"},
        {"title": "Set bộ đầm dạ hội sang chảnh", "niche_id": "thoi_trang_nu"},
    ]

    homelife_prods = [
        {"title": "Chổi lau nhà tự vắt thông minh", "niche_id": "do_gia_dung"},
        {"title": "Nồi chiên không dầu tiện ích", "niche_id": "do_gia_dung"},
        {"title": "Máy hút bụi cầm tay rảnh tay", "niche_id": "do_gia_dung"},
        {"title": "Kệ bếp đa năng giải phóng việc nhà", "niche_id": "do_gia_dung"},
        {"title": "Bộ dao thớt sạch bóng 3s", "niche_id": "do_gia_dung"},
    ]

    # 1. Fashion Persona Checks
    for meta in fashion_prods:
        script = gen.generate_script(meta)
        vo = script["full_voiceover"].lower()

        # Voice ID check
        if script["voice_id"] == "vi-VN-HoaiMyNeural":
            result.record_pass()
        else:
            result.record_fail(f"Fashion prod '{meta['title']}': Expected vi-VN-HoaiMyNeural, got {script['voice_id']}")

        # Persona name check
        if script["persona"] == "hoai_my":
            result.record_pass()
        else:
            result.record_fail(f"Fashion prod '{meta['title']}': Expected hoai_my, got {script['persona']}")

        # Female KOC markers presence
        female_markers = ["chị em", "mấy bà", "tui", "bà nào", "team chân ngắn"]
        has_female = any(m in vo for m in female_markers)
        if has_female:
            result.record_pass()
        else:
            result.record_fail(f"Fashion prod '{meta['title']}': Missing female KOC markers in: {vo[:80]}")

    # 2. HomeLife Persona Checks
    for meta in homelife_prods:
        script = gen.generate_script(meta)
        vo = script["full_voiceover"].lower()

        # Voice ID check
        if script["voice_id"] == "vi-VN-NamMinhNeural":
            result.record_pass()
        else:
            result.record_fail(f"HomeLife prod '{meta['title']}': Expected vi-VN-NamMinhNeural, got {script['voice_id']}")

        # Persona name check
        if script["persona"] == "nam_minh":
            result.record_pass()
        else:
            result.record_fail(f"HomeLife prod '{meta['title']}': Expected nam_minh, got {script['persona']}")

        # Male KOC markers presence
        male_markers = ["các bác", "tui", "3s", "3 giây", "nhàn", "nhàn tênh", "nhàn hẳn"]
        has_male = any(m in vo for m in male_markers)
        if has_male:
            result.record_pass()
        else:
            result.record_fail(f"HomeLife prod '{meta['title']}': Missing male KOC markers in: {vo[:80]}")

    # 3. Persona Cross-Contamination & Emergency Fallback Resilience Check
    # When a homelife product has an adversarial or dirty title, does it retain Nam Minh persona,
    # or does it get overwritten with Hoài My fashion clothing text?
    adversarial_homelife = [
        {"title": "Cây lau kính chào quý khách", "niche_id": "do_gia_dung"},
        {"title": "Chảo vĩnh viễn không bám bẩn", "niche_id": "do_gia_dung"},
        {"title": "Máy chữa khỏi hoàn toàn", "niche_id": "do_gia_dung"},
        {"title": "Kệ sản phẩm hoàn hảo đáp ứng mọi nhu cầu", "niche_id": "do_gia_dung"},
        {"title": "Bộ dao hãy nhanh tay sở hữu", "niche_id": "do_gia_dung"},
    ]

    for meta in adversarial_homelife:
        script = gen.generate_script(meta)
        vo = script["full_voiceover"].lower()

        # Must maintain vi-VN-NamMinhNeural
        if script["voice_id"] == "vi-VN-NamMinhNeural":
            result.record_pass()
        else:
            result.record_fail(f"Adversarial HomeLife '{meta['title']}': Voice ID switched to {script['voice_id']}")

        # Must NOT contain fashion clothing lines (hack dáng, mỡ thừa, giấu nhẹm mỡ) for a home appliance
        has_fashion_crossover = any(kw in vo for kw in ["hack dáng", "mỡ thừa", "chị em ơi, nhìn ngay em này hack dáng"])
        if not has_fashion_crossover:
            result.record_pass()
        else:
            result.record_fail(
                f"Adversarial HomeLife '{meta['title']}': Persona crossed over! Nam Minh speaking fashion lines: {vo[:90]}"
            )

        # Must retain male markers (các bác, nhàn, 3s)
        has_male_markers = any(kw in vo for kw in ["các bác", "nhàn", "3s", "3 giây"])
        if has_male_markers:
            result.record_pass()
        else:
            result.record_fail(
                f"Adversarial HomeLife '{meta['title']}': Lacks male KOC markers in fallback: {vo[:90]}"
            )

    return result


# ==============================================================================
# HARNESS RUNNER & VERDICT
# ==============================================================================

def run_adversarial_harness() -> Tuple[int, int, List[TestResult], str]:
    """Runs all 4 test suites and issues an explicit verdict: APPROVE or REQUEST_CHANGES."""
    print("=" * 80)
    print("AMAS v1.4.0 — Milestone 5 Empirical Adversarial Stress Harness")
    print(f"Timestamp: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
    print("=" * 80)

    gen = ScriptGenerator()

    suites = [
        test_1_adversarial_title_injections,
        test_2_koc_marker_and_contract_guarantee,
        test_3_extreme_and_corrupt_inputs,
        test_4_persona_and_voice_mapping_integrity,
    ]

    results: List[TestResult] = []
    total_passed = 0
    total_failed = 0

    for suite_fn in suites:
        res = suite_fn(gen)
        results.append(res)
        total_passed += res.passed
        total_failed += res.failed

        status_str = "PASS" if res.failed == 0 else f"FAIL ({res.failed} issues)"
        print(f"\n▶ {res.name}: {status_str}")
        print(f"  Tests: {res.total} | Passed: {res.passed} | Failed: {res.failed} | Pass Rate: {res.pass_rate:.1f}%")
        if res.failures:
            print("  Top Failure Details (first 5):")
            for f in res.failures[:5]:
                print(f"    ❌ {f}")
            if len(res.failures) > 5:
                print(f"    ... and {len(res.failures) - 5} more failure details.")

    print("\n" + "=" * 80)
    grand_total = total_passed + total_failed
    overall_rate = (total_passed / grand_total * 100.0) if grand_total > 0 else 0.0
    print(f"GRAND SUMMARY: {total_passed}/{grand_total} assertions passed ({overall_rate:.1f}%)")
    print(f"Total Failures: {total_failed}")
    print("=" * 80)

    verdict = "APPROVE" if total_failed == 0 else "REQUEST_CHANGES"
    print(f"\nFINAL VERDICT: {verdict}\n")

    return total_passed, total_failed, results, verdict


if __name__ == "__main__":
    passed, failed, results, verdict = run_adversarial_harness()
    sys.exit(0 if failed == 0 else 1)
