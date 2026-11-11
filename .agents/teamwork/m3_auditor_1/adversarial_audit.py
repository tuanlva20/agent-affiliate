"""Adversarial stress test runner for Milestone 3 (Specialist Scout Agents).

Author: m3_auditor_1 (Forensic Auditor)
"""

import sys
import json
import unicodedata
from pathlib import Path
sys.path.insert(0, "/Users/tuanlva/Folder/workSpace/affiliate")

from src.agents.fashion_scout import FashionScoutAgent, SpecialistEvaluation
from src.agents.homelife_scout import HomeLifeScoutAgent
from src.agents.base_scout import ProductCandidate
from src.core.tone_validator import ToneValidator
from src.core.prompt_templates import (
    HOAI_MY_PERSONA,
    NAM_MINH_PERSONA,
    HOOK_3S_GUIDELINES,
    FASHION_KOC_SYSTEM_PROMPT,
    HOMELIFE_SYSTEM_PROMPT,
    SPECIALIST_EVALUATION_JSON_SCHEMA,
    build_fashion_evaluation_prompt,
    build_homelife_evaluation_prompt,
)

passed = 0
failed = 0
report = []

def record(test_name: str, success: bool, msg: str = ""):
    global passed, failed
    if success:
        passed += 1
        report.append(f"✅ [PASS] {test_name}: {msg}")
    else:
        failed += 1
        report.append(f"❌ [FAIL] {test_name}: {msg}")

print("================================================================================")
print("AMAS v1.4.0 — M3 FORENSIC ADVERSARIAL STRESS TEST")
print("================================================================================")

f_scout = FashionScoutAgent()
h_scout = HomeLifeScoutAgent()

# ------------------------------------------------------------------------------
# 1. Monotonicity of scoring with keywords
# ------------------------------------------------------------------------------
base_item = {
    "product_id": "mono_01",
    "title": "Váy nữ basic",
    "price": 199000.0,
    "commission_rate": 0.15,
    "sales_30d": 1000,
}
score_0 = f_scout.evaluate_product(base_item).score

item_1 = dict(base_item, title="Váy nữ chiết eo basic")
score_1 = f_scout.evaluate_product(item_1).score

item_2 = dict(base_item, title="Váy nữ chiết eo giấu mỡ bụng hack dáng")
score_2 = f_scout.evaluate_product(item_2).score

item_3 = dict(base_item, title="Váy nữ chiết eo giấu mỡ bụng hack dáng kéo dài chân tôn vòng 1 dáng xòe che bắp tay")
score_3 = f_scout.evaluate_product(item_3).score

is_monotonic = (score_0 < score_1 <= score_2 <= score_3) and (score_3 <= 10.0)
record("Fashion scoring monotonicity", is_monotonic, f"{score_0} < {score_1} <= {score_2} <= {score_3} <= 10.0")

# ------------------------------------------------------------------------------
# 2. HomeLife scoring monotonicity
# ------------------------------------------------------------------------------
h_base = {
    "product_id": "h_mono_01",
    "title": "Dụng cụ nhà bếp tiện ích",
    "price": 199000.0,
    "commission_rate": 0.15,
    "sales_30d": 1000,
}
h_score_0 = h_scout.evaluate_product(h_base).score

h_item_1 = dict(h_base, title="Cây lau nhà tự vắt tiện ích")
h_score_1 = h_scout.evaluate_product(h_item_1).score

h_item_2 = dict(h_base, title="Cây lau nhà tự vắt xoay 360 độ 3s sạch bóng đa năng")
h_score_2 = h_scout.evaluate_product(h_item_2).score

h_monotonic = (h_score_0 < h_score_1 <= h_score_2) and (h_score_2 <= 10.0)
record("HomeLife scoring monotonicity", h_monotonic, f"{h_score_0} < {h_score_1} <= {h_score_2} <= 10.0")

# ------------------------------------------------------------------------------
# 3. Extreme values clamping
# ------------------------------------------------------------------------------
extreme_high = {
    "product_id": "ext_high",
    "title": "Váy chữ a giấu mỡ bụng chiết eo hack dáng tôn vòng 1 tôn vòng 3 che bắp tay hack chiều cao chân dài dáng xòe",
    "price": 999999999.0,
    "commission_rate": 0.99,
    "sales_30d": 9999999,
    "rating": 5.0,
}
f_res_high = f_scout.evaluate_product(extreme_high)
record("Fashion score clamping upper bound", 0.0 <= f_res_high.score <= 10.0, f"Score: {f_res_high.score}")

extreme_low = {
    "product_id": "ext_low",
    "title": "Vật thể lạ",
    "price": 0.0,
    "commission_rate": 0.0,
    "sales_30d": 0,
    "rating": 1.0,
}
f_res_low = f_scout.evaluate_product(extreme_low)
record("Fashion score clamping lower bound", 0.0 <= f_res_low.score <= 10.0, f"Score: {f_res_low.score}")

h_res_high = h_scout.evaluate_product(dict(extreme_high, title="Cây lau nhà tự vắt tự động robot xoay 360 độ 3s sạch bóng tẩy cặn đánh bay vắt khô"))
record("HomeLife score clamping upper bound", 0.0 <= h_res_high.score <= 10.0, f"Score: {h_res_high.score}")

# ------------------------------------------------------------------------------
# 4. Unicode Normalization (NFC vs NFD)
# ------------------------------------------------------------------------------
nfc_title = "Đầm suông chữ A giấu mỡ bụng tôn dáng cực đỉnh"
nfd_title = unicodedata.normalize("NFD", nfc_title)

res_nfc = f_scout.evaluate_product({"product_id": "nfc", "title": nfc_title, "price": 199000, "commission_rate": 0.15, "sales_30d": 2000})
res_nfd = f_scout.evaluate_product({"product_id": "nfd", "title": nfd_title, "price": 199000, "commission_rate": 0.15, "sales_30d": 2000})
record("Unicode normalization resilience (NFC vs NFD)", res_nfc.score == res_nfd.score and res_nfc.passed_filter == res_nfd.passed_filter, f"NFC: {res_nfc.score}, NFD: {res_nfd.score}")

# ------------------------------------------------------------------------------
# 5. Case-insensitivity on counterfeit & exaggerated keywords
# ------------------------------------------------------------------------------
case_titles = [
    ("zArA", "Váy zArA dáng xòe"),
    ("cHaNeL", "Đầm cHaNeL siêu cấp"),
    ("gUcCi", "Áo gUcCi thời trang"),
    ("ReP 1:1", "Áo thun ReP 1:1 chuẩn auth"),
    ("SuPeR fAkE", "Túi SuPeR fAkE cao cấp"),
]
all_cases_blocked = True
for brand, t in case_titles:
    res = f_scout.evaluate_product({"product_id": f"case_{brand}", "title": t, "price": 199000, "commission_rate": 0.15})
    if res.passed_filter or res.score != 0.0 or not res.rejection_reason or "trademark" not in res.rejection_reason.lower() and "policy" not in res.rejection_reason.lower():
        all_cases_blocked = False
        break
record("Case-insensitive counterfeit detection", all_cases_blocked, "All mixed-case counterfeit titles blocked with 0.0 score")

# ------------------------------------------------------------------------------
# 6. JSON serialization roundtrip integrity
# ------------------------------------------------------------------------------
eval_obj = f_scout.evaluate_product(item_2)
d = eval_obj.to_dict()
json_str = json.dumps(d) # must not raise
reloaded = json.loads(json_str)
reconstructed = SpecialistEvaluation.from_dict(reloaded)

roundtrip_ok = (
    reconstructed.product_id == eval_obj.product_id and
    reconstructed.score == eval_obj.score and
    reconstructed.passed_filter == eval_obj.passed_filter and
    reconstructed.hook_angle == eval_obj.hook_angle and
    reconstructed.pros == eval_obj.pros and
    reconstructed.cons == eval_obj.cons and
    reconstructed.viral_factor == eval_obj.viral_factor
)
record("SpecialistEvaluation JSON serialization roundtrip", roundtrip_ok, f"Keys preserved in JSONB: {list(d.keys())}")

# ------------------------------------------------------------------------------
# 7. Prompt builder contract and schemas
# ------------------------------------------------------------------------------
f_prompt = build_fashion_evaluation_prompt(item_2)
h_prompt = build_homelife_evaluation_prompt(h_item_2)
schema_valid = (
    SPECIALIST_EVALUATION_JSON_SCHEMA["type"] == "object" and
    "properties" in SPECIALIST_EVALUATION_JSON_SCHEMA and
    "required" in SPECIALIST_EVALUATION_JSON_SCHEMA and
    len(SPECIALIST_EVALUATION_JSON_SCHEMA["required"]) >= 8
)
record("Specialist evaluation JSON schema validity", schema_valid, f"Required properties count: {len(SPECIALIST_EVALUATION_JSON_SCHEMA['required'])}")
record("Fashion prompt builder contract", "ID:" in f_prompt and "Tiêu đề:" in f_prompt and "VNĐ" in f_prompt, "Valid prompt output")
record("HomeLife prompt builder contract", "ID:" in h_prompt and "Tiêu đề:" in h_prompt and "VNĐ" in h_prompt, "Valid prompt output")

# ------------------------------------------------------------------------------
# 8. Hook angle persona & tone integrity
# ------------------------------------------------------------------------------
f_hook = eval_obj.hook_angle
h_hook = h_scout.evaluate_product(h_item_2).hook_angle

f_hook_has_kw = ("bụng" in f_hook.lower() or "eo" in f_hook.lower())
h_hook_has_kw = ("3s" in h_hook.lower() or "nhàn" in h_hook.lower())
f_hook_tone = ToneValidator.validate(f_hook) and ToneValidator.has_koc_markers(f_hook)
h_hook_tone = ToneValidator.validate(h_hook) and ToneValidator.has_koc_markers(h_hook)

record("Fashion hook keyword constraint ('bụng'/'eo')", f_hook_has_kw, f"Hook: {f_hook}")
record("HomeLife hook keyword constraint ('3s'/'nhàn')", h_hook_has_kw, f"Hook: {h_hook}")
record("Fashion hook tone validation & KOC markers", f_hook_tone, "Passes anti-robotic guard")
record("HomeLife hook tone validation & KOC markers", h_hook_tone, "Passes anti-robotic guard")

# ------------------------------------------------------------------------------
# 9. Large string payload resilience
# ------------------------------------------------------------------------------
huge_title = "Váy chiết eo giấu mỡ bụng " + ("rất đẹp " * 5000)
huge_item = {"product_id": "huge_01", "title": huge_title, "price": 199000, "commission_rate": 0.15, "sales_30d": 1500}
try:
    huge_res = f_scout.evaluate_product(huge_item)
    record("Large payload (50KB title) handling", huge_res.passed_filter is True, f"Score: {huge_res.score}")
except Exception as e:
    record("Large payload handling", False, f"Exception: {e}")

# ------------------------------------------------------------------------------
# 10. Strange numeric representations
# ------------------------------------------------------------------------------
str_num_item = {
    "product_id": "str_num",
    "title": "Cây lau nhà tự vắt xoay 360",
    "price": "149000.0",
    "commission_rate": "0.18",
    "sales_30d": "3500",
    "rating": "4.8",
}
try:
    h_str_res = h_scout.evaluate_product(str_num_item)
    record("String-encoded numeric fields handling", h_str_res.passed_filter is True and h_str_res.score >= 8.5, f"Score: {h_str_res.score}")
except Exception as e:
    record("String-encoded numeric fields handling", False, f"Exception: {e}")

print("--------------------------------------------------------------------------------")
for line in report:
    print(line)
print("--------------------------------------------------------------------------------")
print(f"TOTAL: {passed + failed} | PASSED: {passed} | FAILED: {failed}")
print("================================================================================")

if failed > 0:
    sys.exit(1)
