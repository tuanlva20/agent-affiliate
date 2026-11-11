# Handoff Report — Specialist Scout Agents: Prompt Templates, Dataclass Schema & Test Suite

**Agent ID**: `m3_explorer_3`  
**Milestone**: Milestone 3 (Task 3: Specialist Scout Agents — Prompt Templates & Test Suite)  
**Timestamp**: 2026-11-10T09:10:00Z  
**Type**: Hard Handoff  

---

## 1. Observation

Direct code and configuration inspection revealed the following exact facts across the AMAS codebase:

### 1.1 Dataclass and Interface Contracts in Existing Test Suite
- In `tests/e2e/conftest.py` (lines 324–336), `SpecialistEvaluation` is prototyped with the following exact dataclass definition:
  ```python
  @dataclass
  class SpecialistEvaluation:
      product_id: str
      niche_id: str
      passed_filter: bool
      score: float
      hook_angle: str
      target_audience: str
      pros: List[str]
      cons: List[str]
      viral_factor: str
      rejection_reason: Optional[str] = None
  ```
- In `tests/e2e/test_tier1_features.py` (lines 250–273), test `test_f08_fashion_scout_agent` asserts:
  - `eval_result = scout.evaluate_product(sample_fashion_product)`
  - `isinstance(eval_result, SpecialistEvaluation)`
  - `eval_result.passed_filter is True`
  - `eval_result.score >= 8.0`
  - `"bụng" in eval_result.hook_angle.lower() or "eo" in eval_result.hook_angle.lower()`
  - On counterfeit input (`"Váy Chanel rep 1:1 siêu cấp"`):
    - `fake_eval.passed_filter is False`
    - `fake_eval.score == 0.0`
    - `"trademark" in fake_eval.rejection_reason.lower() or "policy" in fake_eval.rejection_reason.lower()`
- In `tests/e2e/test_tier1_features.py` (lines 277–298), test `test_f09_homelife_scout_agent` asserts:
  - `eval_result = scout.evaluate_product(sample_homelife_product)`
  - `isinstance(eval_result, SpecialistEvaluation)`
  - `eval_result.passed_filter is True`
  - `eval_result.score >= 8.5`
  - `"3s" in eval_result.hook_angle or "nhàn" in eval_result.hook_angle`
  - On exaggerated input (`"Chai xịt nano vĩnh viễn không bám bẩn"`):
    - `exag_eval.passed_filter is False`
    - `exag_eval.score == 0.0`
    - `"exaggerated" in exag_eval.rejection_reason.lower() or "policy" in exag_eval.rejection_reason.lower()`
- In `tests/e2e/test_tier2_boundaries.py` (lines 88–120 and 124–150):
  - Parametrized tests verify zero tolerance for counterfeit trademarks (`"Zara chuẩn auth"`, `"Chanel"`, `"Gucci"`, `"Dior"`, `"Louis Vuitton"`, `"Hermes"`, `"rep 1:1"`, `"super fake"`, `"nhái"`) with `passed_filter is False`, `score == 0.0`, `"trademark" in rejection_reason.lower() or "policy" in rejection_reason.lower()`.
  - Parametrized tests verify zero tolerance for exaggerated medical/cleaning claims (`"trị dứt điểm 100%"`, `"vĩnh viễn không bám bẩn"`, `"cam kết chữa khỏi"`, `"100% hết bệnh"`, `"chữa dứt điểm"`) with `passed_filter is False`, `score == 0.0`.

### 1.2 Tone and Policy Rules in `src/core/tone_validator.py`
- In `src/core/tone_validator.py` (lines 20–100):
  - `ROBOTIC_PATTERNS`: Catches AI clichés such as `"chào quý khách"`, `"kính chào quý khách"`, `"sau/dưới đây là danh sách"`, `"tôi là trợ lý ảo/AI"`, `"sản phẩm rất tuyệt vời"`, `"đáp ứng mọi nhu cầu"`, `"sự lựa chọn hoàn hảo"`, `"giải pháp hoàn hảo"`, `"đừng bỏ lỡ cơ hội này"`, `"hãy nhanh tay sở hữu"`, `"sở hữu ngay hôm nay"`.
  - `COUNTERFEIT_PATTERNS`: Catches `"rep 1:1"`, `"super fake"`, `"fake"`, `"nhái"`, `"like/chuẩn/tuồn auth"`, `"Zara"`, `"Chanel"`, `"Gucci"`, `"Dior"`, `"Louis Vuitton"`, `"LV"`, `"Hermes"`, `"Prada"`, `"Balenciaga"`, `"Rolex"`, `"Nike"`, `"Adidas"`.
  - `EXAGGERATED_PATTERNS`: Catches `"trị dứt điểm 100%"`, `"chữa dứt điểm"`, `"chữa khỏi"`, `"thần dược"`, `"vĩnh viễn không bám bẩn"`, `"vĩnh viễn không hỏng"`, `"100% không bao giờ hỏng"`, `"vĩnh viễn không rỉ sét"`, `"số 1 thế giới/việt nam"`.
  - `KOC_MARKER_PATTERNS`: Confirms presence of natural KOC expressions such as `"chị em ơi"`, `"mấy bà ơi"`, `"bà nào bụng dưới to"`, `"team chân ngắn"`, `"nhàn hẳn"`, `"nhàn tênh"`, `"mê chữ ê kéo dài"`, `"chân ái"`, `"đỉnh chóp"`, `"hack dáng"`, `"giỏ hàng góc trái"`, `"giỏ hàng vàng"`.
  - Methods: `ToneValidator.check_violations(text) -> List[str]`, `ToneValidator.validate(text) -> bool`, `ToneValidator.has_koc_markers(text) -> bool`.

### 1.3 Niche Configuration in `config.yaml` and `src/core/config.py`
- In `config.yaml` (lines 52–155):
  - `thoi_trang_nu`:
    - `voice_name: "vi-VN-HoaiMyNeural"`
    - Persona role: `"KOC Thời trang nữ Gen Z / Millennial"`
    - Tone: `"Thân mật, hào hứng, xưng chị em/các bà/tui, am hiểu chất vải và form dáng tôn dáng, cởi mở chân thật"`
    - Thresholds: `min_price: 99000.0`, `max_price: 650000.0`, `min_commission_rate: 0.10`, `min_evaluation_score: 7.0`
    - Sample greetings: `"Chị em ơi"`, `"Mấy bà ơi"`, `"Bà nào bụng dưới to bơi hết vào đây nha"`, `"Team chân ngắn đâu rồi bơi vào nhận đồ đẹp nè"`
    - Sample hooks: `"Mặc cái này lên eo thon gọn hẳn 5 phân không cần nịt bụng"`, `"Váy hack dáng đỉnh nhất tui từng thử trong năm nay"`
    - Sample CTAs: `"Bấm ngay góc trái nhận mã freeship nha"`, `"Link tui để ở giỏ hàng góc trái nè"`, `"Săn ngay mã giảm giá ở giỏ hàng vàng nha mấy bà"`
  - `do_gia_dung`:
    - `voice_name: "vi-VN-NamMinhNeural"`
    - Persona role: `"KOC Đồ gia dụng thông minh / Yêu bếp nghiện nhà"`
    - Tone: `"Thực tế, gần gũi, xưng các bác/mấy bà/tui, chú trọng giải phóng sức lao động, nhấn mạnh Before/After 3s"`
    - Thresholds: `min_price: 49000.0`, `max_price: 1200000.0`, `min_commission_rate: 0.12`, `min_evaluation_score: 7.0`
    - Sample greetings: `"Các bác ơi"`, `"Bà nào ngại dọn nhà bơi vào đây"`, `"Chân ái cho hội lười dọn dẹp đây rồi"`, `"Từ ngày tậu em này việc nhà nhàn hẳn"`
    - Sample hooks: `"Bỏ ngay mấy cái giẻ lau cũ đi, dùng cái này nhàn tênh"`, `"3 giây sạch bóng kin kít không tốn một giọt mồ hôi"`
    - Sample CTAs: `"Chị em bấm vào giỏ hàng góc trái nhận ưu đãi nha"`, `"Đang có mã giảm 20k ở giỏ hàng vàng kìa các bác"`

### 1.4 Database Model in `src/database/models.py`
- In `src/database/models.py` (line 176–178):
  `evaluation_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONType, nullable=True)`
  Persisting evaluations requires a clean dictionary output (`to_dict()`) compatible with JSONB.

---

## 2. Logic Chain

1. **Contract Alignment**:
   - Because `tests/e2e/conftest.py` and all Tier 1, 2, 3 tests construct and inspect `SpecialistEvaluation` with 10 exact fields, the production definition must preserve these exact field names, types, and ordering:
     `product_id: str`, `niche_id: str`, `passed_filter: bool`, `score: float`, `hook_angle: str`, `target_audience: str`, `pros: List[str]`, `cons: List[str]`, `viral_factor: str`, `rejection_reason: Optional[str] = None`.
   - In addition, adding `to_dict()` and `from_dict()` methods enables clean integration with `Product.evaluation_data` in PostgreSQL (Observation 1.4) and downstream serialization for Telegram Bot cards (Task 4) and Redis queues.

2. **Scoring Calibration & Filter Rules**:
   - For valid fashion body-hack products: Scoring must assign score `>= 8.0` (as asserted in Observation 1.1 `test_f08_fashion_scout_agent`) when matching keywords like `"bụng"`, `"eo"`, `"hack dáng"`, `"che khuyết điểm"`, `"giấu mỡ"`. The hook generator must produce a natural spoken hook containing `"bụng"` or `"eo"`.
   - For valid homelife labor-saving products: Scoring must assign score `>= 8.5` (as asserted in Observation 1.1 `test_f09_homelife_scout_agent`) when matching keywords like `"tự vắt"`, `"thông minh"`, `"nhàn"`, `"đa năng"`. The hook generator must produce a hook containing `"3s"` or `"nhàn"`.
   - For counterfeit fashion products: Rejection must trigger immediately via `ToneValidator.check_violations` (Observation 1.2), returning `passed_filter = False`, `score = 0.0`, and `rejection_reason` containing `"trademark"` or `"policy"`.
   - For exaggerated homelife products: Rejection must trigger immediately via `ToneValidator.check_violations`, returning `passed_filter = False`, `score = 0.0`, and `rejection_reason` containing `"exaggerated"` or `"policy"`.
   - For mediocre products without body-hack or labor-saving merits: Scoring yields `< 7.0` (below `min_evaluation_score = 7.0` in Observation 1.3), resulting in `passed_filter = False`.
   - For corrupted/empty inputs: Agents must return `passed_filter = False`, `score = 0.0` with clear rejection reason without raising uncaught exceptions.

3. **Prompt Templates & KOC Personas Architecture**:
   - The central prompt module `src/core/prompt_templates.py` must encapsulate both KOC personas (Hoài My: `vi-VN-HoaiMyNeural` and Nam Minh: `vi-VN-NamMinhNeural`), the 3s Hook formulas, anti-robotic guardrails, system prompts for LLM Evaluators with structured JSON output schema matching `SpecialistEvaluation`, and prompt builders for script generation (Task 5) and comment engagement (Task 7).

4. **Unit Test Suite Coverage**:
   - To achieve 100% test pass rate and high test robustness, `tests/test_specialist_scouts.py` must define a dedicated unit test suite with 12 distinct test cases covering all 6 mandatory scenarios + dataclass serialization, parametrized boundary matrices, and tone compliance.

---

## 3. Caveats

1. **Dual Evaluation Capability (Rule-based Fallback vs. Gemini LLM)**:
   - When `GEMINI_API_KEY` is not provided (e.g. offline testing or local development), `FashionScoutAgent` and `HomeLifeScoutAgent` must evaluate deterministically via their rule-based scoring engines. When `GEMINI_API_KEY` is present, they can optionally invoke Gemini LLM with the structured JSON prompts.
   - The unit tests in `tests/test_specialist_scouts.py` MUST test deterministic evaluation without requiring external network access or paid API keys.
2. **Read-only Investigation**:
   - In accordance with explorer constraints, no source files outside `.agents/teamwork/m3_explorer_3/` were modified. The proposed codes in Section 4 are complete and directly applicable by the implementation worker.

---

## 4. Conclusion & Proposed Implementation Artifacts

The investigation confirms that Task 3 requires three core artifacts:
1. `src/core/prompt_templates.py`: The single source of truth for KOC Personas (Hoài My & Nam Minh), 3s Hook guidelines, Anti-Robotic rules, and LLM Structured Evaluation Prompts.
2. `SpecialistEvaluation` Dataclass in `src/agents/fashion_scout.py` (and re-exported by `src/agents/homelife_scout.py` and `src/agents/__init__.py`).
3. `tests/test_specialist_scouts.py`: Unit test suite verifying all 6 dispatch requirements + edge cases.

Below are the complete, production-ready code proposals:

### 4.1 Proposed `src/core/prompt_templates.py`

```python
"""AMAS v1.4.0 — Core Prompt Templates & KOC Persona Engine.

Defines:
1. KOC Personas: Hoài My (Fashion - vi-VN-HoaiMyNeural) & Nam Minh (HomeLife - vi-VN-NamMinhNeural).
2. Hook 3s Formulas & Spoken Anti-Robotic Tone Guardrails.
3. Structured System & User Prompts for Gemini / LLM Specialist Product Evaluators.
4. Forward-compatible Script Generation and Comment Engagement templates.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

# ==============================================================================
# 1. KOC PERSONA DEFINITIONS & TONE GUIDELINES
# ==============================================================================

HOAI_MY_PERSONA: Dict[str, Any] = {
    "name": "Hoài My",
    "voice_name": "vi-VN-HoaiMyNeural",
    "role": "KOC Thời trang nữ Gen Z / Millennial (22-28 tuổi)",
    "tone": (
        "Thân mật, hào hứng, gần gũi, xưng chị em/các bà/tui. "
        "Am hiểu chất vải, form dáng tôn dáng, che khuyết điểm (eo bánh mì, bắp tay to, chân ngắn). "
        "Cởi mở, chân thật, nói chuyện tự nhiên như bạn bè tư vấn cho nhau, không quảng cáo sáo rỗng."
    ),
    "pronouns": {
        "self": ["tui", "em", "My"],
        "audience": ["chị em", "mấy bà", "các bà", "team chân ngắn", "team eo bánh mì", "mọi người"],
    },
    "signature_greetings": [
        "Chị em ơi",
        "Mấy bà ơi",
        "Bà nào bụng dưới to bơi hết vào đây nha",
        "Team chân ngắn đâu rồi bơi vào nhận đồ đẹp nè",
    ],
    "signature_hooks": [
        "Mặc cái này lên eo thon gọn hẳn 5 phân không cần nịt bụng",
        "Váy hack dáng đỉnh nhất tui từng thử trong năm nay",
        "Đừng mua mẫu váy này nếu sợ bị đồng nghiệp hỏi xin link liên tục",
        "Bà nào bụng dưới to bơi hết vào đây, chiếc váy này cứu cánh cực đỉnh!",
    ],
    "signature_ctas": [
        "Bấm ngay góc trái nhận mã freeship nha",
        "Link tui để ở giỏ hàng góc trái nè",
        "Săn ngay mã giảm giá ở giỏ hàng vàng nha mấy bà",
    ],
    "banned_elements": [
        "Từ ngữ máy móc (kính chào quý khách, sự lựa chọn hoàn hảo, giải pháp hoàn hảo...)",
        "Nhãn hiệu hàng nhái / vi phạm bản quyền (Zara, Chanel, Gucci, Dior, LV, Hermes, Nike, Adidas, rep 1:1, super fake...)",
    ],
}

NAM_MINH_PERSONA: Dict[str, Any] = {
    "name": "Nam Minh",
    "voice_name": "vi-VN-NamMinhNeural",
    "role": "KOC Đồ gia dụng thông minh / Yêu bếp nghiện nhà (25-32 tuổi)",
    "tone": (
        "Thực tế, mộc mạc, gần gũi, thẳng thắn, xưng các bác/mấy bà/tui. "
        "Chú trọng giải phóng sức lao động, tiết kiệm thời gian cho gia đình và mẹ bỉm. "
        "Nhấn mạnh Before/After 3s trực quan rõ rệt, khách quan đánh giá cả ưu lẫn nhược điểm."
    ),
    "pronouns": {
        "self": ["tui", "Minh"],
        "audience": ["các bác", "mấy bà", "mấy ông", "anh em", "mọi người"],
    },
    "signature_greetings": [
        "Các bác ơi",
        "Bà nào ngại dọn nhà bơi vào đây",
        "Chân ái cho hội lười dọn dẹp đây rồi",
        "Từ ngày tậu em này việc nhà nhàn hẳn",
    ],
    "signature_hooks": [
        "Bỏ ngay mấy cái giẻ lau cũ đi, dùng cái này nhàn tênh",
        "3 giây sạch bóng kin kít không tốn một giọt mồ hôi",
        "Cứ tưởng vô dụng mà đỉnh không tưởng các bác ạ",
        "Từ ngày tậu em này việc nhà nhàn hẳn, 3s là nhà sạch bóng!",
    ],
    "signature_ctas": [
        "Chị em bấm vào giỏ hàng góc trái nhận ưu đãi nha",
        "Đang có mã giảm 20k ở giỏ hàng vàng kìa các bác",
        "Link mua chính hãng ở góc trái màn hình nha",
    ],
    "banned_elements": [
        "Từ ngữ máy móc (kính chào quý khách, đáp ứng mọi nhu cầu...)",
        "Quảng cáo quá đà / cam kết y tế phi lý (trị dứt điểm 100%, vĩnh viễn không bám bẩn, vĩnh viễn không hỏng, thần dược...)",
    ],
}

# ==============================================================================
# 2. HOOK 3S GUIDELINES & ANTI-ROBOTIC GUARDRAILS
# ==============================================================================

HOOK_3S_GUIDELINES: Dict[str, Any] = {
    "rule_of_3_seconds": (
        "3 giây đầu tiên (10-15 từ đầu) quyết định hơn 70% tỷ lệ giữ chân người xem TikTok. "
        "Phải đập thẳng vào mắt hoặc tai nỗi đau cụ thể hoặc sự biến đổi trực quan, "
        "tuyệt đối không chào hỏi rườm rà hay giới thiệu bản thân."
    ),
    "fashion_hook_rules": [
        "BẮT BUỘC chứa ít nhất 1 từ khóa nhắm điểm đau hình thể: 'bụng', 'eo', 'hack dáng', 'che khuyết điểm', 'bụng dưới to', 'bắp tay'.",
        "Gợi mở visual Before/After: mặc vào lập tức thon gọn, giấu mỡ, tôn dáng.",
        "Xưng hô thân mật: 'Chị em ơi', 'Mấy bà ơi', 'Bà nào...', 'Team chân ngắn'.",
    ],
    "homelife_hook_rules": [
        "BẮT BUỘC chứa từ khóa tốc độ hoặc giải phóng sức lao động: '3s', '3 giây', 'nhàn', 'nhàn tênh', 'nhàn hẳn'.",
        "Gợi mở visual Before/After: vết bẩn cứng đầu biến mất trong tích tắc, lau dọn không tốn giọt mồ hôi.",
        "Xưng hô gần gũi: 'Các bác ơi', 'Bà nào ngại dọn nhà', 'Từ ngày tậu em này'.",
    ],
    "anti_robotic_guardrails": [
        "CẤM TUYỆT ĐỐI các mẫu câu chào đón khách hàng kiểu tổng đài: 'Chào quý khách', 'Kính chào quý vị', 'Chào mừng bạn đến với...'.",
        "CẤM TUYỆT ĐỐI các tính từ sáo rỗng vô thưởng vô phạt: 'sự lựa chọn hoàn hảo', 'giải pháp hoàn hảo', 'đáp ứng mọi nhu cầu', 'sản phẩm rất tuyệt vời'.",
        "CẤM TUYỆT ĐỐI các lời kêu gọi mua hàng rập khuôn: 'Hãy nhanh tay sở hữu ngay hôm nay', 'Đừng bỏ lỡ cơ hội này'.",
        "CẤM TUYỆT ĐỐI các xưng danh AI: 'Tôi là trợ lý AI', 'Như một mô hình ngôn ngữ'.",
    ],
}

# ==============================================================================
# 3. SPECIALIST SCOUT EVALUATOR PROMPTS (GEMINI / LLM)
# ==============================================================================

SPECIALIST_EVALUATION_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "product_id": {"type": "string"},
        "niche_id": {"type": "string", "enum": ["thoi_trang_nu", "do_gia_dung"]},
        "passed_filter": {"type": "boolean"},
        "score": {"type": "number", "minimum": 0.0, "maximum": 10.0},
        "hook_angle": {"type": "string"},
        "target_audience": {"type": "string"},
        "pros": {"type": "array", "items": {"type": "string"}},
        "cons": {"type": "array", "items": {"type": "string"}},
        "viral_factor": {"type": "string"},
        "rejection_reason": {"type": ["string", "null"]},
    },
    "required": [
        "product_id",
        "niche_id",
        "passed_filter",
        "score",
        "hook_angle",
        "target_audience",
        "pros",
        "cons",
        "viral_factor",
    ],
}

FASHION_EVALUATION_SYSTEM_PROMPT = """Bạn là Hoài My - KOC Trinh sát Thời trang nữ hàng đầu của hệ thống AMAS TikTok Shop Affiliate.
Nhiệm vụ của bạn là thẩm định sản phẩm thời trang nữ và trả về kết quả JSON có cấu trúc chính xác theo schema yêu cầu.

QUY TẮC THẨM ĐỊNH NGHIÊM NGẶT:
1. LOẠI TRỪ HÀNG NHÁI / VI PHẠM BẢN QUYỀN (Zero Tolerance):
   - Nếu tiêu đề hoặc mô tả chứa tên thương hiệu nhái/bản quyền (Zara, Chanel, Gucci, Dior, LV, Louis Vuitton, Hermes, Nike, Adidas, rep 1:1, super fake, fake, like auth, tuồn auth...):
     -> BẮT BUỘC trả về: passed_filter = false, score = 0.0, rejection_reason = "Violates trademark policy: <chi_tiet>", hook_angle = "".
2. TIÊU CHÍ HACK DÁNG & TÔN DÁNG (Trọng số chính):
   - Đánh giá khả năng giấu mỡ bụng dưới, chiết eo thon gọn, che bắp tay to, hack chiều cao cho học sinh, sinh viên, dân văn phòng.
   - Sản phẩm hack dáng xuất sắc đạt điểm score >= 8.0 (ví dụ 8.8).
3. TIÊU CHÍ HOOK 3S:
   - hook_angle BẮT BUỘC phải chứa từ khóa "bụng" hoặc "eo" (ví dụ: "Bà nào bụng dưới to bơi hết vào đây, chiếc váy này cứu cánh cực đỉnh!").
   - Giọng điệu tự nhiên, chị em tâm tình, KHÔNG mùi bot, KHÔNG chào hỏi máy móc.
4. NGƯỠNG ĐẠT CHUẨN:
   - Sản phẩm chất lượng kém hoặc không có tính năng hack dáng rõ rệt chỉ đạt score < 7.0 -> passed_filter = false.
   - Sản phẩm đạt điểm >= 7.0 (ưu tiên >= 8.0) -> passed_filter = true, rejection_reason = null.
5. ĐỊNH DẠNG ĐẦU RA:
   - BẮT BUỘC chỉ trả về duy nhất 1 JSON object hợp lệ, không bọc markdown ```json ```."""

HOMELIFE_EVALUATION_SYSTEM_PROMPT = """Bạn là Nam Minh - KOC Trinh sát Đồ gia dụng thông minh hàng đầu của hệ thống AMAS TikTok Shop Affiliate.
Nhiệm vụ của bạn là thẩm định sản phẩm đồ gia dụng tiện ích và trả về kết quả JSON có cấu trúc chính xác theo schema yêu cầu.

QUY TẮC THẨM ĐỊNH NGHIÊM NGẶT:
1. LOẠI TRỪ QUẢNG CÁO QUÁ ĐÀ / CAM KẾT Y TẾ (Zero Tolerance):
   - Nếu tiêu đề hoặc mô tả chứa cam kết phi lý (trị dứt điểm 100%, vĩnh viễn không bám bẩn, vĩnh viễn không hỏng, 100% không bao giờ hỏng, thần dược, chữa khỏi bệnh...):
     -> BẮT BUỘC trả về: passed_filter = false, score = 0.0, rejection_reason = "Violates policy: exaggerated claim '<chi_tiet>'", hook_angle = "".
2. TIÊU CHÍ GIẢI PHÓNG SỨC LAO ĐỘNG & BEFORE/AFTER 3S (Trọng số chính):
   - Đánh giá khả năng giúp việc nhà nhàn tênh, tiết kiệm thời gian, tự động/thông minh, Before/After trực quan ấn tượng (bẩn -> sạch bóng trong tích tắc).
   - Sản phẩm giải phóng sức lao động xuất sắc đạt điểm score >= 8.5 (ví dụ 9.0).
3. TIÊU CHÍ HOOK 3S:
   - hook_angle BẮT BUỘC phải chứa từ khóa "3s" hoặc "nhàn" (ví dụ: "Từ ngày tậu em này việc nhà nhàn hẳn, 3s là nhà sạch bóng!").
   - Giọng điệu chân thật, xưng "các bác", "tui", thực tế, KHÔNG mùi bot.
4. NGƯỠNG ĐẠT CHUẨN:
   - Sản phẩm bình thường, không có công năng nổi bật đạt score < 7.0 -> passed_filter = false.
   - Sản phẩm đạt điểm >= 7.0 (ưu tiên >= 8.5) -> passed_filter = true, rejection_reason = null.
5. ĐỊNH DẠNG ĐẦU RA:
   - BẮT BUỘC chỉ trả về duy nhất 1 JSON object hợp lệ, không bọc markdown ```json ```."""


def build_fashion_evaluation_prompt(item: Dict[str, Any]) -> str:
    """Xây dựng user prompt thẩm định sản phẩm thời trang cho LLM."""
    return f"""Hãy thẩm định sản phẩm thời trang nữ sau:
- ID: {item.get('product_id', '')}
- Tiêu đề: {item.get('title', '')}
- Giá bán: {item.get('price', item.get('price_vnd', 0)):,} VNĐ
- Tỷ lệ hoa hồng: {float(item.get('commission_rate', item.get('commission', 0))) * 100:.1f}%
- Doanh số 30 ngày: {item.get('sales_30d', item.get('sales', 0))} lượt bán
- Đánh giá shop: {item.get('rating', 'Chưa có')} sao

Hãy trả về JSON theo đúng định dạng SpecialistEvaluation."""


def build_homelife_evaluation_prompt(item: Dict[str, Any]) -> str:
    """Xây dựng user prompt thẩm định sản phẩm đồ gia dụng cho LLM."""
    return f"""Hãy thẩm định sản phẩm đồ gia dụng thông minh sau:
- ID: {item.get('product_id', '')}
- Tiêu đề: {item.get('title', '')}
- Giá bán: {item.get('price', item.get('price_vnd', 0)):,} VNĐ
- Tỷ lệ hoa hồng: {float(item.get('commission_rate', item.get('commission', 0))) * 100:.1f}%
- Doanh số 30 ngày: {item.get('sales_30d', item.get('sales', 0))} lượt bán
- Đánh giá shop: {item.get('rating', 'Chưa có')} sao

Hãy trả về JSON theo đúng định dạng SpecialistEvaluation."""
```

---

### 4.2 Proposed `SpecialistEvaluation` Dataclass (in `src/agents/fashion_scout.py` & `homelife_scout.py`)

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SpecialistEvaluation:
    """Specialist Scout evaluation outcome and KOC briefing data transfer object."""

    product_id: str
    niche_id: str
    passed_filter: bool
    score: float
    hook_angle: str
    target_audience: str
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)
    viral_factor: str = ""
    rejection_reason: Optional[str] = None

    def __post_init__(self) -> None:
        self.product_id = str(self.product_id)
        self.niche_id = str(self.niche_id)
        self.passed_filter = bool(self.passed_filter)
        self.score = float(self.score)
        self.hook_angle = str(self.hook_angle)
        self.target_audience = str(self.target_audience)
        if not isinstance(self.pros, list):
            self.pros = list(self.pros) if self.pros is not None else []
        if not isinstance(self.cons, list):
            self.cons = list(self.cons) if self.cons is not None else []
        self.viral_factor = str(self.viral_factor)
        if self.rejection_reason is not None:
            self.rejection_reason = str(self.rejection_reason)

    def to_dict(self) -> Dict[str, Any]:
        """Convert evaluation result to a serializable dictionary for JSONB persistence."""
        return {
            "product_id": self.product_id,
            "niche_id": self.niche_id,
            "passed_filter": self.passed_filter,
            "score": self.score,
            "hook_angle": self.hook_angle,
            "target_audience": self.target_audience,
            "pros": self.pros,
            "cons": self.cons,
            "viral_factor": self.viral_factor,
            "rejection_reason": self.rejection_reason,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SpecialistEvaluation:
        """Safely deserialize an evaluation dictionary into a SpecialistEvaluation instance."""
        return cls(
            product_id=str(data.get("product_id", "")),
            niche_id=str(data.get("niche_id", "")),
            passed_filter=bool(data.get("passed_filter", False)),
            score=float(data.get("score", 0.0)),
            hook_angle=str(data.get("hook_angle", "")),
            target_audience=str(data.get("target_audience", "")),
            pros=list(data.get("pros", []) or []),
            cons=list(data.get("cons", []) or []),
            viral_factor=str(data.get("viral_factor", "")),
            rejection_reason=data.get("rejection_reason"),
        )
```

---

### 4.3 Proposed Unit Test Suite `tests/test_specialist_scouts.py`

```python
"""AMAS v1.4.0 — Specialist Scout Agents Unit Test Suite (Task 3).

Tests:
1. SpecialistEvaluation Dataclass integrity, defaults, and round-trip serialization.
2. FashionScoutAgent valid body-hack evaluations (score >= 8.0, hook with 'bụng'/'eo').
3. FashionScoutAgent counterfeit / trademark rejections (score = 0.0, rejection_reason contains 'trademark'/'policy').
4. HomeLifeScoutAgent valid labor-saving evaluations (score >= 8.5, hook with '3s'/'nhàn').
5. HomeLifeScoutAgent exaggerated claims rejections (score = 0.0, rejection_reason contains 'exaggerated'/'policy').
6. Low-scoring mediocre products handling (score < 7.0, passed_filter = False).
7. Corrupted, missing, and boundary product inputs handling.
8. Anti-robotic tone validation and KOC markers in generated hook angles.
9. Prompt templates module exports and persona consistency.
"""

from __future__ import annotations

from typing import Any, Dict
import pytest

from src.agents.fashion_scout import FashionScoutAgent, SpecialistEvaluation
from src.agents.homelife_scout import HomeLifeScoutAgent
from src.core.prompt_templates import (
    HOAI_MY_PERSONA,
    NAM_MINH_PERSONA,
    HOOK_3S_GUIDELINES,
    build_fashion_evaluation_prompt,
    build_homelife_evaluation_prompt,
)
from src.core.tone_validator import ToneValidator


# ==============================================================================
# 1. SpecialistEvaluation Dataclass Tests
# ==============================================================================

def test_specialist_evaluation_dataclass_fields_and_defaults():
    """Validates SpecialistEvaluation dataclass attributes and default values."""
    eval_item = SpecialistEvaluation(
        product_id="prod_01",
        niche_id="thoi_trang_nu",
        passed_filter=True,
        score=8.5,
        hook_angle="Bà nào bụng to bơi vào đây",
        target_audience="Nữ 18-30",
        pros=["Tôn dáng", "Vải đẹp"],
        cons=["Hơi dài"],
        viral_factor="Before/After 3s",
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
# 2. Fashion Scout: Valid Body-Hack Products
# ==============================================================================

def test_fashion_scout_valid_body_hack_product():
    """F08 requirement: Valid fashion body-hack product evaluation (score >= 8.0, hook with 'bụng' / 'eo')."""
    scout = FashionScoutAgent()
    valid_product = {
        "product_id": "fash_dress_001",
        "niche_id": "thoi_trang_nu",
        "title": "Váy hoa nhí dáng xòe chiết eo hack dáng đỉnh cao",
        "price": 189000.0,
        "commission_rate": 0.15,
        "sales_30d": 3500,
        "revenue_30d": 661500000.0,
    }

    eval_result = scout.evaluate_product(valid_product)
    assert isinstance(eval_result, SpecialistEvaluation)
    assert eval_result.passed_filter is True
    assert eval_result.score >= 8.0
    hook_lower = eval_result.hook_angle.lower()
    assert "bụng" in hook_lower or "eo" in hook_lower
    assert eval_result.rejection_reason is None
    assert len(eval_result.pros) > 0
    assert len(eval_result.viral_factor) > 0


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
# 3. Fashion Scout: Counterfeit / Trademark Rejections (Zero Tolerance)
# ==============================================================================

@pytest.mark.parametrize(
    "suspicious_title",
    [
        "Váy Chanel rep 1:1 siêu cấp",
        "Áo phông Zara chuẩn auth",
        "Túi xách Gucci super fake loại 1",
        "Đầm dạ hội Dior cao cấp",
        "Áo khoác LV tuồn auth xịn sò",
        "Khăn lụa Hermes nhái cao cấp",
        "Set đồ thể thao Adidas fake loại 1",
        "Giày thể thao Nike rep 1:1 y hình",
    ],
)
def test_fashion_scout_counterfeit_rejection_matrix(suspicious_title: str):
    """F08 requirement: Counterfeit fashion rejection (score = 0.0, passed_filter = False, rejection_reason contains 'trademark' or 'policy')."""
    scout = FashionScoutAgent()
    fake_item = {
        "product_id": "fash_fake_01",
        "title": suspicious_title,
        "price": 250000.0,
        "commission_rate": 0.20,
    }
    result = scout.evaluate_product(fake_item)
    assert result.passed_filter is False
    assert result.score == 0.0
    assert result.rejection_reason is not None
    reason_lower = result.rejection_reason.lower()
    assert "trademark" in reason_lower or "policy" in reason_lower
    assert result.hook_angle == ""


# ==============================================================================
# 4. HomeLife Scout: Valid Labor-Saving Utility Products
# ==============================================================================

def test_homelife_scout_valid_labor_saving_product():
    """F09 requirement: Valid homelife labor-saving product evaluation (score >= 8.5, hook with '3s' / 'nhàn')."""
    scout = HomeLifeScoutAgent()
    valid_product = {
        "product_id": "home_mop_001",
        "niche_id": "do_gia_dung",
        "title": "Cây lau nhà tự vắt xoay 360 độ đa năng thông minh",
        "price": 149000.0,
        "commission_rate": 0.18,
        "sales_30d": 5200,
        "revenue_30d": 774800000.0,
    }

    eval_result = scout.evaluate_product(valid_product)
    assert isinstance(eval_result, SpecialistEvaluation)
    assert eval_result.passed_filter is True
    assert eval_result.score >= 8.5
    hook_lower = eval_result.hook_angle.lower()
    assert "3s" in hook_lower or "nhàn" in hook_lower
    assert eval_result.rejection_reason is None
    assert len(eval_result.pros) > 0
    assert len(eval_result.viral_factor) > 0


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
# 5. HomeLife Scout: Exaggerated Claims Rejections (Zero Tolerance)
# ==============================================================================

@pytest.mark.parametrize(
    "exaggerated_title",
    [
        "Chai xịt nano vĩnh viễn không bám bẩn",
        "Dung dịch thần dược tẩy sạch dầu mỡ trọn đời",
        "Thuốc xịt côn trùng trị dứt điểm 100% không bao giờ quay lại",
        "Chảo chống dính vĩnh viễn không hỏng 100%",
        "Nước lau sàn cam kết chữa khỏi nấm mốc trọn đời",
    ],
)
def test_homelife_scout_exaggerated_claims_rejection(exaggerated_title: str):
    """F09 requirement: Exaggerated homelife claim rejection (score = 0.0, passed_filter = False, rejection_reason contains 'exaggerated' or 'policy')."""
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


# ==============================================================================
# 6. Mediocre Low-Scoring Products
# ==============================================================================

def test_fashion_scout_mediocre_product_subthreshold():
    """Validates that plain products without body-hack merits receive score < 7.0 and fail filter."""
    scout = FashionScoutAgent()
    mediocre_item = {
        "product_id": "fash_plain_01",
        "title": "Áo thun cotton trơn đơn giản basic",
        "price": 380000.0,
        "commission_rate": 0.10,
        "sales_30d": 5,
    }
    result = scout.evaluate_product(mediocre_item)
    assert result.passed_filter is False
    assert result.score < 7.0
    assert result.rejection_reason is not None


def test_homelife_scout_mediocre_product_subthreshold():
    """Validates that ordinary utility products without labor-saving hooks receive score < 7.0 and fail filter."""
    scout = HomeLifeScoutAgent()
    mediocre_item = {
        "product_id": "home_plain_01",
        "title": "Bát sứ trắng ăn cơm hoa văn thông thường",
        "price": 85000.0,
        "commission_rate": 0.10,
        "sales_30d": 10,
    }
    result = scout.evaluate_product(mediocre_item)
    assert result.passed_filter is False
    assert result.score < 7.0
    assert result.rejection_reason is not None


# ==============================================================================
# 7. Corrupted & Empty Product Inputs Handling
# ==============================================================================

@pytest.mark.parametrize(
    "corrupted_input",
    [
        {},
        {"product_id": ""},
        {"title": ""},
        {"product_id": "   ", "title": "   "},
        {"product_id": "p1", "title": "Váy hoa", "price": "invalid"},
        {"product_id": "p1", "title": "Cây lau", "commission_rate": -0.5},
    ],
)
def test_specialist_scouts_corrupted_empty_inputs(corrupted_input: Dict[str, Any]):
    """Verifies that scouts gracefully handle missing/corrupted inputs without raising exceptions."""
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
# 8. Tone & Robotic Cliché Guard in Generated Hook Angles
# ==============================================================================

def test_generated_hook_angles_satisfy_tone_validator():
    """Ensures that generated hook angles are free of robotic clichés and contain natural KOC markers."""
    f_scout = FashionScoutAgent()
    h_scout = HomeLifeScoutAgent()

    f_eval = f_scout.evaluate_product({
        "product_id": "f1",
        "title": "Váy hoa nhí dáng xòe chiết eo hack dáng",
        "price": 189000.0,
        "commission_rate": 0.15,
    })
    h_eval = h_scout.evaluate_product({
        "product_id": "h1",
        "title": "Cây lau nhà tự vắt xoay 360 độ đa năng thông minh",
        "price": 149000.0,
        "commission_rate": 0.18,
    })

    assert ToneValidator.validate(f_eval.hook_angle) is True
    assert ToneValidator.validate(h_eval.hook_angle) is True

    # Check for presence of natural spoken KOC markers
    assert ToneValidator.has_koc_markers(f_eval.hook_angle) is True
    assert ToneValidator.has_koc_markers(h_eval.hook_angle) is True


# ==============================================================================
# 9. Prompt Templates Module & Persona Verification
# ==============================================================================

def test_prompt_templates_module_integrity():
    """Validates KOC Persona metadata, voice configurations, and prompt builder functions."""
    assert HOAI_MY_PERSONA["voice_name"] == "vi-VN-HoaiMyNeural"
    assert "chị em" in HOAI_MY_PERSONA["tone"].lower() or "tôn dáng" in HOAI_MY_PERSONA["tone"].lower()

    assert NAM_MINH_PERSONA["voice_name"] == "vi-VN-NamMinhNeural"
    assert "lao động" in NAM_MINH_PERSONA["tone"].lower() or "thực tế" in NAM_MINH_PERSONA["tone"].lower()

    assert "rule_of_3_seconds" in HOOK_3S_GUIDELINES

    sample_item = {"product_id": "t1", "title": "Váy chiết eo", "price": 150000.0, "commission_rate": 0.15}
    f_prompt = build_fashion_evaluation_prompt(sample_item)
    assert "Váy chiết eo" in f_prompt
    assert "150,000" in f_prompt

    h_prompt = build_homelife_evaluation_prompt(sample_item)
    assert "Váy chiết eo" in h_prompt
```

---

## 5. Verification Method

Once the implementation worker writes `src/core/prompt_templates.py`, `src/agents/fashion_scout.py`, `src/agents/homelife_scout.py`, and `tests/test_specialist_scouts.py`, the changes can be independently verified using:

1. **Dedicated Unit Test Command**:
   ```bash
   pytest tests/test_specialist_scouts.py -v
   ```
   *Expected result*: 12/12 unit tests PASS (100%).

2. **Full Regression Test Command**:
   ```bash
   pytest tests/test_base_scout.py tests/test_specialist_scouts.py tests/e2e/test_tier1_features.py -v
   ```
   *Expected result*: All base scout, specialist scout, and Tier 1 feature tests PASS with zero regressions.

3. **Code Compliance & Quality Checks**:
   - `ToneValidator.validate()` returns `True` for all valid hooks.
   - Counterfeit brand violations return `score = 0.0` with `"trademark"` or `"policy"` in `rejection_reason`.
   - Exaggerated utility claims return `score = 0.0` with `"exaggerated"` or `"policy"` in `rejection_reason`.
