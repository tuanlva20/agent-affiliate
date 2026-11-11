"""AMAS v1.4.0 — Specialist Scout Agents & Prompt Templates Unit Test Suite (Feature F08 & F09).

Tests:
1. test_fashion_scout_valid_body_hack: Valid body-hack fashion item passes filter (score >= 8.0, hook with 'bụng'/'eo').
2. test_fashion_scout_rejects_counterfeit_trademarks: Counterfeit brand items rejected (score == 0.0, passed_filter == False, rejection_reason contains 'trademark'/'policy').
3. test_fashion_scout_subthreshold_rejection: Low-scoring items without fashion appeal score < 7.0 and fail filter.
4. test_homelife_scout_valid_labor_saving: Valid home utility item passes filter (score >= 8.5, hook with '3s'/'nhàn').
5. test_homelife_scout_rejects_exaggerated_claims: Exaggerated claims rejected (score == 0.0, passed_filter == False, rejection_reason contains 'exaggerated'/'policy').
6. test_homelife_scout_subthreshold_rejection: Mediocre items without visual contrast score < 7.0 and fail filter.
7. test_corrupted_inputs_handling: None/empty/corrupted dictionary inputs handled gracefully without crashing.
8. test_prompt_templates_contracts: Personas (Hoài My, Nam Minh), system prompts, and script guidelines exist and contain required keys.
9. ProductCandidate compatibility & SpecialistEvaluation dataclass serialization.
10. Anti-robotic tone validation on generated hooks.
"""

from __future__ import annotations

from typing import Any, Dict
import pytest

from src.agents.base_scout import ProductCandidate
from src.agents.fashion_scout import FashionScoutAgent, SpecialistEvaluation
from src.agents.homelife_scout import HomeLifeScoutAgent
from src.core.prompt_templates import (
    HOAI_MY_PERSONA,
    NAM_MINH_PERSONA,
    HOOK_3S_GUIDELINES,
    FASHION_KOC_SYSTEM_PROMPT,
    HOMELIFE_SYSTEM_PROMPT,
    build_fashion_evaluation_prompt,
    build_homelife_evaluation_prompt,
)
from src.core.tone_validator import ToneValidator


# ==============================================================================
# 1. SpecialistEvaluation Dataclass Tests
# ==============================================================================

def test_specialist_evaluation_dataclass_contract():
    """Validates SpecialistEvaluation dataclass fields, defaults, and round-trip serialization."""
    eval_item = SpecialistEvaluation(
        product_id="prod_01",
        niche_id="thoi_trang_nu",
        passed_filter=True,
        score=8.5,
        hook_angle="Bà nào bụng to bơi vào đây",
        target_audience="Nữ 18-30",
        pros=["Tôn dáng", "Vải đẹp"],
        cons=["Hơi dài"],
        viral_factor="Before/After 3s giấu mỡ bụng",
    )
    assert eval_item.product_id == "prod_01"
    assert eval_item.niche_id == "thoi_trang_nu"
    assert eval_item.passed_filter is True
    assert eval_item.score == 8.5
    assert eval_item.rejection_reason is None

    # Test dictionary serialization round-trip
    d = eval_item.to_dict()
    assert d["product_id"] == "prod_01"
    assert d["score"] == 8.5
    assert d["rejection_reason"] is None

    reconstructed = SpecialistEvaluation.from_dict(d)
    assert reconstructed.product_id == eval_item.product_id
    assert reconstructed.score == eval_item.score
    assert reconstructed.pros == eval_item.pros
    assert reconstructed.rejection_reason is None


# ==============================================================================
# 2. Fashion Scout: Valid Body-Hack Item (F08 Requirement)
# ==============================================================================

def test_fashion_scout_valid_body_hack():
    """Validates valid body-hack fashion item passes with score >= 8.0 and hook angle containing 'bụng' or 'eo'."""
    scout = FashionScoutAgent()
    valid_product = {
        "product_id": "fash_dress_001",
        "niche_id": "thoi_trang_nu",
        "title": "Váy hoa nhí dáng xòe chiết eo hack dáng đỉnh cao",
        "price": 189000.0,
        "commission_rate": 0.15,
        "sales_30d": 3500,
        "revenue_30d": 661500000.0,
        "rating": 4.85,
    }

    eval_res = scout.evaluate_product(valid_product)
    assert isinstance(eval_res, SpecialistEvaluation)
    assert eval_res.passed_filter is True
    assert eval_res.score >= 8.0
    hook_lower = eval_res.hook_angle.lower()
    assert "bụng" in hook_lower or "eo" in hook_lower
    assert eval_res.rejection_reason is None
    assert len(eval_res.pros) > 0
    assert len(eval_res.cons) > 0
    assert len(eval_res.viral_factor) > 0


@pytest.mark.parametrize(
    "title",
    [
        "Đầm suông chữ A giấu mỡ bụng tôn dáng cực đỉnh",
        "Quần ống rộng cạp cao chiết eo hack chiều cao cho nấm lùn",
        "Chân váy chữ A cạp cao che khuyết điểm bụng dưới to",
    ],
)
def test_fashion_scout_body_hack_variations_parametrized(title: str):
    """Verifies various body-hack items consistently achieve >= 8.0 score and targeted hook angles."""
    scout = FashionScoutAgent()
    item = {
        "product_id": "fash_var_01",
        "title": title,
        "price": 210000.0,
        "commission_rate": 0.18,
        "sales_30d": 2000,
    }
    result = scout.evaluate_product(item)
    assert result.passed_filter is True
    assert result.score >= 8.0
    assert "bụng" in result.hook_angle.lower() or "eo" in result.hook_angle.lower()


# ==============================================================================
# 3. Fashion Scout: Rejection of Counterfeit Trademarks (F08 Requirement)
# ==============================================================================

@pytest.mark.parametrize(
    "suspicious_title,brand",
    [
        ("Váy Zara tiểu thư dáng xòe chuẩn auth", "Zara"),
        ("Đầm Chanel rep 1:1 siêu cấp", "Chanel"),
        ("Áo Gucci thêu hoa chuẩn auth", "Gucci"),
        ("Sơ mi Dior nữ cao cấp", "Dior"),
        ("Túi xách LV like auth", "LV"),
        ("Khăn lụa Hermes sang chảnh", "Hermes"),
        ("Giày Nike thể thao rep 1:1", "Nike"),
        ("Áo khoác Adidas super fake", "Adidas"),
        ("Váy dạ tweed rep 1:1 Quảng Châu", "rep 1:1"),
        ("Đầm suông thiết kế super fake loại 1", "super fake"),
    ],
)
def test_fashion_scout_rejects_counterfeit_trademarks(suspicious_title: str, brand: str):
    """Validates counterfeit brand items are rejected with score == 0.0, passed_filter == False, and rejection_reason containing 'trademark' or 'policy'."""
    scout = FashionScoutAgent()
    fake_item = {
        "product_id": f"fake_{brand.lower().replace(' ', '_')}",
        "title": suspicious_title,
        "price": 220000.0,
        "commission_rate": 0.18,
        "sales_30d": 1500,
    }
    eval_res = scout.evaluate_product(fake_item)
    assert eval_res.passed_filter is False
    assert eval_res.score == 0.0
    assert eval_res.rejection_reason is not None
    reason_lower = eval_res.rejection_reason.lower()
    assert "trademark" in reason_lower or "policy" in reason_lower
    assert eval_res.hook_angle == ""
    assert len(eval_res.pros) == 0


# ==============================================================================
# 4. Fashion Scout: Subthreshold Rejection (F08 Requirement)
# ==============================================================================

def test_fashion_scout_subthreshold_rejection():
    """Validates low-scoring items without fashion appeal score < 7.0 and passed_filter == False."""
    scout = FashionScoutAgent()
    bland_item = {
        "product_id": "fash_bland_01",
        "title": "Áo phông cotton trơn màu xám cổ tròn basic",
        "price": 120000.0,
        "commission_rate": 0.10,
        "sales_30d": 30,
        "rating": 4.1,
    }
    eval_res = scout.evaluate_product(bland_item)
    assert eval_res.passed_filter is False
    assert eval_res.score < 7.0
    assert eval_res.rejection_reason is not None
    assert "threshold" in eval_res.rejection_reason.lower() or "score" in eval_res.rejection_reason.lower()


# ==============================================================================
# 5. HomeLife Scout: Valid Labor-Saving Utility (F09 Requirement)
# ==============================================================================

def test_homelife_scout_valid_labor_saving():
    """Validates valid home utility item passes with score >= 8.5 and hook angle containing '3s' or 'nhàn'."""
    scout = HomeLifeScoutAgent()
    valid_product = {
        "product_id": "home_mop_001",
        "niche_id": "do_gia_dung",
        "title": "Cây lau nhà tự vắt xoay 360 độ đa năng thông minh",
        "price": 149000.0,
        "commission_rate": 0.18,
        "sales_30d": 5200,
        "revenue_30d": 774800000.0,
        "rating": 4.8,
    }

    eval_res = scout.evaluate_product(valid_product)
    assert isinstance(eval_res, SpecialistEvaluation)
    assert eval_res.passed_filter is True
    assert eval_res.score >= 8.5
    hook_lower = eval_res.hook_angle.lower()
    assert "3s" in hook_lower or "nhàn" in hook_lower
    assert eval_res.rejection_reason is None
    assert len(eval_res.pros) > 0
    assert len(eval_res.cons) > 0
    viral_lower = eval_res.viral_factor.lower()
    assert "3s" in viral_lower or "vắt khô" in viral_lower


@pytest.mark.parametrize(
    "title",
    [
        "Máy hút bụi mini cầm tay không dây nhàn tênh việc nhà",
        "Cây gạt nước tự vắt 3s sạch bóng kính đa năng",
        "Nồi chiên không dầu đa năng tự động giải phóng sức lao động",
    ],
)
def test_homelife_scout_labor_saving_variations_parametrized(title: str):
    """Verifies utility products achieve >= 8.5 and hooks containing '3s' or 'nhàn'."""
    scout = HomeLifeScoutAgent()
    item = {
        "product_id": "home_var_01",
        "title": title,
        "price": 280000.0,
        "commission_rate": 0.15,
        "sales_30d": 4000,
    }
    result = scout.evaluate_product(item)
    assert result.passed_filter is True
    assert result.score >= 8.5
    assert "3s" in result.hook_angle.lower() or "nhàn" in result.hook_angle.lower()


# ==============================================================================
# 6. HomeLife Scout: Rejection of Exaggerated Claims (F09 Requirement)
# ==============================================================================

@pytest.mark.parametrize(
    "exaggerated_title",
    [
        "Serum bôi trị dứt điểm 100% mụn thâm",
        "Chai xịt phủ nano vĩnh viễn không bám bẩn",
        "Dung dịch thần dược đánh bay rỉ sét trọn đời",
        "Nước lau sàn cam kết chữa khỏi nấm mốc",
        "Thuốc xịt côn trùng trị dứt điểm 100% vĩnh viễn không quay lại",
        "Chảo chống dính vĩnh viễn không hỏng 100%",
    ],
)
def test_homelife_scout_rejects_exaggerated_claims(exaggerated_title: str):
    """Validates exaggerated claims are rejected with score == 0.0, passed_filter == False, and rejection_reason containing 'exaggerated' or 'policy'."""
    scout = HomeLifeScoutAgent()
    exag_item = {
        "product_id": "home_fake_01",
        "title": exaggerated_title,
        "price": 120000.0,
        "commission_rate": 0.15,
    }
    result = scout.evaluate_product(exag_item)
    assert result.passed_filter is False
    assert result.score == 0.0
    assert result.rejection_reason is not None
    reason_lower = result.rejection_reason.lower()
    assert "exaggerated" in reason_lower or "policy" in reason_lower
    assert result.hook_angle == ""
    assert len(result.pros) == 0


# ==============================================================================
# 7. HomeLife Scout: Subthreshold Rejection (F09 Requirement)
# ==============================================================================

def test_homelife_scout_subthreshold_rejection():
    """Validates mediocre items without visual contrast score < 7.0 and passed_filter == False."""
    scout = HomeLifeScoutAgent()
    mediocre_item = {
        "product_id": "home_low_01",
        "title": "Móc treo quần áo nhựa thông thường basic",
        "price": 25000.0,
        "commission_rate": 0.10,
        "sales_30d": 15,
        "rating": 4.1,
    }
    result = scout.evaluate_product(mediocre_item)
    assert result.passed_filter is False
    assert result.score < 7.0
    assert result.rejection_reason is not None
    assert "threshold" in result.rejection_reason.lower() or "score" in result.rejection_reason.lower()


# ==============================================================================
# 8. Corrupted & Edge Inputs Handling
# ==============================================================================

@pytest.mark.parametrize(
    "corrupted_input",
    [
        None,
        {},
        {"product_id": ""},
        {"title": ""},
        {"product_id": "   ", "title": "   "},
        {"product_id": "p1", "title": "Váy hoa", "price": "invalid"},
        {"product_id": "p1", "title": "Cây lau", "commission_rate": -0.5},
    ],
)
def test_corrupted_inputs_handling(corrupted_input: Any):
    """Validates None/empty/corrupted dictionary inputs do not crash and return valid SpecialistEvaluation instances with passed_filter == False."""
    f_scout = FashionScoutAgent()
    h_scout = HomeLifeScoutAgent()

    f_res = f_scout.evaluate_product(corrupted_input)
    assert isinstance(f_res, SpecialistEvaluation)
    assert f_res.passed_filter is False
    assert f_res.score == 0.0
    assert f_res.rejection_reason is not None

    h_res = h_scout.evaluate_product(corrupted_input)
    assert isinstance(h_res, SpecialistEvaluation)
    assert h_res.passed_filter is False
    assert h_res.score == 0.0
    assert h_res.rejection_reason is not None


# ==============================================================================
# 9. Prompt Templates Contracts
# ==============================================================================

def test_prompt_templates_contracts():
    """Validates personas (Hoài My, Nam Minh), system prompts, and script guidelines exist and contain required keys."""
    # Hoài My persona contract
    assert HOAI_MY_PERSONA["name"] == "Hoài My"
    assert HOAI_MY_PERSONA["voice_name"] == "vi-VN-HoaiMyNeural"
    assert "role" in HOAI_MY_PERSONA
    assert "tone" in HOAI_MY_PERSONA
    assert len(HOAI_MY_PERSONA["signature_greetings"]) > 0
    assert len(HOAI_MY_PERSONA["signature_hooks"]) > 0

    # Nam Minh persona contract
    assert NAM_MINH_PERSONA["name"] == "Nam Minh"
    assert NAM_MINH_PERSONA["voice_name"] == "vi-VN-NamMinhNeural"
    assert "role" in NAM_MINH_PERSONA
    assert "tone" in NAM_MINH_PERSONA
    assert len(NAM_MINH_PERSONA["signature_greetings"]) > 0
    assert len(NAM_MINH_PERSONA["signature_hooks"]) > 0

    # Hook 3s rules contract
    assert "rule_of_3_seconds" in HOOK_3S_GUIDELINES
    assert "fashion_hook_rules" in HOOK_3S_GUIDELINES
    assert "homelife_hook_rules" in HOOK_3S_GUIDELINES
    assert "anti_robotic_guardrails" in HOOK_3S_GUIDELINES

    # System prompts contract
    assert "vi-VN-HoaiMyNeural" in FASHION_KOC_SYSTEM_PROMPT
    assert "vi-VN-NamMinhNeural" in HOMELIFE_SYSTEM_PROMPT
    assert "Chào quý khách" not in FASHION_KOC_SYSTEM_PROMPT
    assert "Chào quý khách" not in HOMELIFE_SYSTEM_PROMPT

    # Prompt builder functions
    sample_item = {
        "product_id": "test_01",
        "title": "Váy chiết eo tôn dáng",
        "price": 189000.0,
        "commission_rate": 0.15,
        "sales_30d": 1200,
    }
    f_prompt = build_fashion_evaluation_prompt(sample_item)
    assert "Váy chiết eo tôn dáng" in f_prompt
    assert "189,000" in f_prompt

    h_prompt = build_homelife_evaluation_prompt(sample_item)
    assert "Váy chiết eo tôn dáng" in h_prompt


# ==============================================================================
# 10. ProductCandidate Object Compatibility
# ==============================================================================

def test_product_candidate_object_compatibility():
    """Validates that scouts accept ProductCandidate instances directly."""
    f_scout = FashionScoutAgent()
    h_scout = HomeLifeScoutAgent()

    f_cand = ProductCandidate(
        product_id="prod_cand_01",
        niche_id="thoi_trang_nu",
        title="Chân váy chữ A cạp cao che bụng tôn dáng",
        price_vnd=199000.0,
        commission_rate=0.15,
        sales_30d=2200,
        raw_data={"rating": 4.8},
    )
    f_eval = f_scout.evaluate_product(f_cand)
    assert f_eval.passed_filter is True
    assert f_eval.score >= 8.0
    assert "bụng" in f_eval.hook_angle.lower() or "eo" in f_eval.hook_angle.lower()

    h_cand = ProductCandidate(
        product_id="prod_cand_02",
        niche_id="do_gia_dung",
        title="Cây lau nhà tự vắt xoay 360 độ thế hệ mới",
        price_vnd=169000.0,
        commission_rate=0.18,
        sales_30d=3500,
        raw_data={"rating": 4.8},
    )
    h_eval = h_scout.evaluate_product(h_cand)
    assert h_eval.passed_filter is True
    assert h_eval.score >= 8.5
    assert "3s" in h_eval.hook_angle.lower() or "nhàn" in h_eval.hook_angle.lower()


# ==============================================================================
# 11. Anti-Robotic Tone Guard in Generated Hook Angles
# ==============================================================================

def test_generated_hook_angles_satisfy_tone_validator():
    """Ensures that generated hook angles pass ToneValidator and contain natural KOC markers."""
    f_scout = FashionScoutAgent()
    h_scout = HomeLifeScoutAgent()

    f_eval = f_scout.evaluate_product({
        "product_id": "f1",
        "title": "Váy hoa nhí dáng xòe chiết eo hack dáng",
        "price": 189000.0,
        "commission_rate": 0.15,
        "sales_30d": 2000,
    })
    h_eval = h_scout.evaluate_product({
        "product_id": "h1",
        "title": "Cây lau nhà tự vắt xoay 360 độ đa năng thông minh",
        "price": 149000.0,
        "commission_rate": 0.18,
        "sales_30d": 2500,
    })

    assert ToneValidator.validate(f_eval.hook_angle) is True
    assert ToneValidator.validate(h_eval.hook_angle) is True

    # Natural spoken KOC markers
    assert ToneValidator.has_koc_markers(f_eval.hook_angle) is True
    assert ToneValidator.has_koc_markers(h_eval.hook_angle) is True


# ==============================================================================
# 12. Obfuscated Trademark Rejection (Remediation Test Suite)
# ==============================================================================

@pytest.mark.parametrize(
    "obfuscated_title",
    [
        "Váy Z.a.r.a dáng xòe chiết eo che bụng",
        "Đầm C-h-a-n-e-l tiểu thư tôn dáng chiết eo",
        "Áo G_u_c_c_i croptop che mỡ bụng",
        "Váy r.e.p 1:1 lụa sang chảnh chiết eo",
        "Váy super_fake loại 1 chiết eo",
        "Váy Z a r a dáng xòe chiết eo",
        "Váy Z4r4 dáng xòe tôn dáng",
        "Đầm Ch4n3l siêu xinh chiết eo",
        "Áo Gucc1 thời trang che mỡ",
        "Váy D10r sang chảnh hack eo",
        "Váy Zàra thiết kế tôn dáng",
        "Đầm Chánel dáng suông che bụng",
        "Áo Gùcci croptop",
        "Áo dạ r.e.p. 1.1 cao cấp chiết eo",
        "Váy s.u.p.e.r f.a.k.e dáng xòe",
        "Đầm like-auth chuẩn form hack eo",
        "Túi xách L.V sang chảnh",
        "Khăn lụa H.e.r.m.e.s cao cấp",
    ],
)
def test_fashion_scout_rejects_obfuscated_trademarks_parametrized(obfuscated_title: str):
    """Verifies that obfuscated, punctuated, spaced, accented, and leetspeak brand variants are 100% rejected."""
    scout = FashionScoutAgent()
    item = {
        "product_id": f"obf_{hash(obfuscated_title) % 10000}",
        "title": obfuscated_title,
        "price": 250000.0,
        "commission_rate": 0.18,
        "sales_30d": 3000,
        "rating": 4.9,
    }
    result = scout.evaluate_product(item)
    assert result.passed_filter is False
    assert result.score == 0.0
    assert result.rejection_reason is not None
    reason_lower = result.rejection_reason.lower()
    assert "trademark" in reason_lower or "policy" in reason_lower


# ==============================================================================
# 13. Obfuscated Exaggerated Claims Rejection (Remediation Test Suite)
# ==============================================================================

@pytest.mark.parametrize(
    "exag_claim",
    [
        "vĩnh viễn ko bám bẩn",
        "vĩnh viễn khong bám bẩn",
        "thần_dược",
        "thần-dược",
        "thần.dược",
        "trị   dứt   điểm   100%",
        "trị_dứt_điểm",
        "vĩnh_viễn_không_bám_bẩn",
        "100 % không bao giờ hỏng",
        "bảo hành trọn đời không hỏng",
    ],
)
def test_homelife_scout_rejects_obfuscated_exaggerated_claims_parametrized(exag_claim: str):
    """Verifies that slang, punctuation-separated, and multi-spaced exaggerated claims are 100% rejected."""
    scout = HomeLifeScoutAgent()
    item = {
        "product_id": f"exag_{hash(exag_claim) % 10000}",
        "title": f"Cây lau nhà tự vắt thông minh 3s {exag_claim}",
        "price": 149000.0,
        "commission_rate": 0.18,
        "sales_30d": 5000,
        "rating": 4.9,
    }
    result = scout.evaluate_product(item)
    assert result.passed_filter is False
    assert result.score == 0.0
    assert result.rejection_reason is not None
    reason_lower = result.rejection_reason.lower()
    assert "exaggerated" in reason_lower or "policy" in reason_lower


# ==============================================================================
# 14. NaN and Inf Numeric Guards
# ==============================================================================

@pytest.mark.parametrize(
    "corrupt_price",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
        -50000.0,
    ],
)
def test_numeric_nan_inf_guards(corrupt_price: float):
    """Verifies that NaN, Inf, and negative prices in both scouts are safely rejected with score=0.0."""
    f_scout = FashionScoutAgent()
    h_scout = HomeLifeScoutAgent()

    item_f = {
        "product_id": "nan_f",
        "title": "Váy hoa nhí dáng xòe chiết eo che mỡ bụng",
        "price": corrupt_price,
        "commission_rate": 0.15,
        "sales_30d": 2000,
    }
    res_f = f_scout.evaluate_product(item_f)
    assert res_f.passed_filter is False
    assert res_f.score == 0.0
    assert "invalid" in (res_f.rejection_reason or "").lower()

    item_h = {
        "product_id": "nan_h",
        "title": "Cây lau nhà tự vắt xoay 360 độ đa năng thông minh 3s",
        "price": corrupt_price,
        "commission_rate": 0.18,
        "sales_30d": 3000,
    }
    res_h = h_scout.evaluate_product(item_h)
    assert res_h.passed_filter is False
    assert res_h.score == 0.0
    assert "invalid" in (res_h.rejection_reason or "").lower()


# ==============================================================================
# 15. SpecialistEvaluation from_dict Non-Dict Resilience
# ==============================================================================

@pytest.mark.parametrize(
    "non_dict_data",
    [
        None,
        "invalid_string",
        12345,
        [1, 2, 3],
    ],
)
def test_specialist_evaluation_from_dict_non_dict_input(non_dict_data: Any):
    """Verifies SpecialistEvaluation.from_dict handles non-dict payloads gracefully without raising AttributeError."""
    eval_obj = SpecialistEvaluation.from_dict(non_dict_data)
    assert isinstance(eval_obj, SpecialistEvaluation)
    assert eval_obj.passed_filter is False
    assert eval_obj.score == 0.0

