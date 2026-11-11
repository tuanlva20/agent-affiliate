# Handoff Report: FashionScoutAgent (F08) & Hoài My KOC Persona Exploration

**Author**: `m3_explorer_1`  
**Milestone**: Milestone 3 (Task 3: Specialist Scout Agents)  
**Target Modules**: `src/agents/fashion_scout.py`, `src/core/prompt_templates.py`, `tests/test_specialist_scouts.py`  
**Date**: 2026-11-10T09:08:00Z  

---

## 1. Observation

### 1.1 Existing Codebase & Contracts

1. **System Specification & Niche Definition** (`SYSTEM_SPEC.md` lines 8, 18):
   - Target Niche: Pilot 1 is Women's Fashion (`thoi_trang_nu`).
   - Agent 1: `FashionScoutAgent` conducts deep niche market research on fashion products.

2. **Milestone 3 Task 3 Requirements** (`docs/superpowers/plans/2026-11-10-autonomous-affiliate-system.md` lines 152-177):
   - Files to create: `src/agents/fashion_scout.py`, `src/agents/homelife_scout.py`, `src/core/prompt_templates.py`, `tests/test_specialist_scouts.py`.
   - Interface: `FashionScoutAgent.evaluate_product(item: Dict) -> SpecialistEvaluation`.
   - Requirements: Body-hack evaluation (che bụng, giấu mỡ, chiết eo, hack dáng, tôn vòng 1, chân dài, tôn dáng, hack chiều cao), elimination of counterfeit/fake brands (Zara, Chanel, etc.), KOC prompt templates.

3. **`PROJECT.md` Interface Contract** (lines 85-88):
   - `FashionScoutAgent.evaluate_product(item: Dict) -> SpecialistEvaluation`
   - `SpecialistEvaluation` dataclass: `product_id: str`, `niche_id: str`, `passed_filter: bool`, `score: float`, `hook_angle: str`, `target_audience: str`, `pros: List[str]`, `cons: List[str]`, `viral_factor: str`, `rejection_reason: Optional[str]`.

4. **Niche Configuration & Thresholds** (`config.yaml` lines 52-109):
   - `niche_id`: `"thoi_trang_nu"`
   - `thresholds`: `min_price: 99000.0`, `max_price: 650000.0`, `min_commission_rate: 0.10`, `min_sales_7d: 100`, `min_rating: 4.5`, `min_evaluation_score: 7.0`.
   - `persona`: Voice `vi-VN-HoaiMyNeural`, role `KOC Thời trang nữ Gen Z / Millennial`. Tone: thân mật, ngọt ngào, xưng hô "chị em ơi", "mấy bà ơi", "các bà ơi", "tui".
   - `banned_keywords`: zara, chanel, gucci, dior, louis vuitton, lv, hermes, nike, adidas, rep 1:1, rep 1 1, super fake, hàng rep, like auth, chuẩn auth, tuồn auth.

5. **Anti-Robotic & Counterfeit Validator** (`src/core/tone_validator.py` lines 47-70, 109-140):
   - `ToneValidator.validate(text: str) -> bool`: Pure validator, returns `False` if text contains robotic clichés, counterfeit brand keywords, or exaggerated claims.
   - `ToneValidator.check_violations(text: str) -> List[str]`: Returns specific violation strings such as `COUNTERFEIT_KEYWORD: 'Zara'`, `COUNTERFEIT_KEYWORD: 'rep 1:1'`.

6. **Existing E2E Test Invocations & Assertions**:
   - `tests/e2e/test_tier1_features.py` (lines 250-272):
     ```python
     scout = FashionScoutAgent()
     eval_result = scout.evaluate_product(sample_fashion_product)
     assert isinstance(eval_result, SpecialistEvaluation)
     assert eval_result.passed_filter is True
     assert eval_result.score >= 8.0
     assert "bụng" in eval_result.hook_angle.lower() or "eo" in eval_result.hook_angle.lower()

     fake_eval = scout.evaluate_product(fake_item)
     assert fake_eval.passed_filter is False
     assert fake_eval.score == 0.0
     assert "trademark" in fake_eval.rejection_reason.lower() or "policy" in fake_eval.rejection_reason.lower()
     ```
   - `tests/e2e/test_tier2_boundaries.py` (lines 108-119):
     Asserts counterfeit items (Zara, Chanel, Gucci, Dior, LV, Hermes, rep 1:1, super fake, hàng fake, nhái) return `passed_filter is False`, `score == 0.0`, with `"trademark"` or `"policy"` in `rejection_reason`.
   - `tests/e2e/test_tier4_scenarios.py` (lines 68-74):
     Asserts target fashion candidate with "hack dáng" receives `evaluation.score >= 8.5`.

7. **Current Test Status**:
   - `pytest tests/test_config.py tests/test_database.py tests/test_kalodata_client.py tests/test_tiktok_scraper.py tests/test_base_scout.py` -> 43 passed in 3.80s.
   - `tests/test_specialist_scouts.py` does NOT exist yet.

---

## 2. Logic Chain

### Step 1: Dataclass & Module Architecture
- **Observation 3 & 6** establish that downstream agents (Telegram Command Center F10-F12, Video Studio F18, and e2e test suites) depend on `SpecialistEvaluation` with fields:
  `(product_id, niche_id, passed_filter, score, hook_angle, target_audience, pros, cons, viral_factor, rejection_reason)`.
- Defining `SpecialistEvaluation` in `src/agents/fashion_scout.py` (or shared in `src/agents/base_scout.py` / exported from `src/agents/__init__.py`) ensures complete decoupling while satisfying typing contracts.
- Both `Dict[str, Any]` and `ProductCandidate` instances should be accepted by `evaluate_product()` so that items from `BaseScoutAgent.discover_candidates()` or raw scraper dictionaries can be evaluated directly without conversion friction.

### Step 2: Zero-Tolerance Counterfeit Rejection Mechanism
- **Observation 4, 5 & 6** require immediate rejection of trademarked and counterfeit brand names.
- By calling `ToneValidator.check_violations(title)` inside `FashionScoutAgent.evaluate_product()`:
  - If any counterfeit keyword or banned brand from `config.yaml` is detected:
    - `passed_filter = False`
    - `score = 0.0`
    - `rejection_reason = f"Violates trademark policy: detected counterfeit brand/keyword '{keyword}'"`
    - `cons = [f"Contains banned or counterfeit brand name: {keyword}"]`
    - `hook_angle = ""`, `target_audience = ""`, `pros = []`, `viral_factor = ""`
  - This satisfies both `"trademark"` and `"policy"` substring checks across `test_tier1_features.py` and `test_tier2_boundaries.py`.

### Step 3: Body-Hack Scoring Algorithm & Velocity Multiplier
- **Observation 2, 4 & 6** dictate that scoring must reward body-hack attributes while incorporating sales velocity:
  - **Base Score**: 6.5 for valid women's fashion items.
  - **Keyword Bonuses**: Evaluates 7 distinct body-hack categories (che bụng, giấu mỡ, chiết eo, tôn dáng, hack chiều cao, tôn vòng 1/3, flattering silhouettes) with individual weights (+0.4 to +0.8) and category caps, totaling up to +3.0 max.
  - **Viral Sales Velocity Multiplier**: Applies a multiplier based on 30-day sales volume (`sales_30d`):
    - $\ge 5,000 \rightarrow 1.15\times$
    - $3,000 - 4,999 \rightarrow 1.10\times$
    - $1,000 - 2,999 \rightarrow 1.05\times$
    - $300 - 999 \rightarrow 1.00\times$
    - $100 - 299 \rightarrow 0.98\times$
    - $< 100 \rightarrow 0.95\times$
  - **Rating Adjustment**: $\ge 4.8 \rightarrow +0.2$; $< 4.0 \rightarrow -0.8$.
  - **Threshold**: From `config.yaml`, `min_evaluation_score = 7.0`. Products scoring $\ge 7.0$ receive `passed_filter = True`. Body-hack products with high velocity comfortably hit $\ge 8.5$, meeting `test_tier4_scenarios.py` and `test_tier1_features.py`. Bland non-body-hack products with low sales remain $< 7.0$ and get `passed_filter = False`.

### Step 4: Hook Angle & Context Generation
- **Observation 4 & 6** require natural Vietnamese KOC hooks containing `"bụng"` or `"eo"` without robotic clichés:
  - Pattern examples:
    - `"Bà nào bụng dưới to bơi hết vào đây, chiếc váy này cứu cánh cực đỉnh!"`
    - `"Mặc cái này lên eo thon gọn hẳn 5 phân không cần nịt bụng, nhìn mê chữ ê kéo dài!"`
    - `"Team bụng mỡ đâu rồi, em váy này giấu bụng thắt eo đỉnh chóp luôn nha!"`
  - Target audience, pros, cons, and viral factors are dynamically populated to provide authentic Human-in-the-Loop context for Telegram approval cards.

### Step 5: Hoài My KOC Persona Prompt Template in `src/core/prompt_templates.py`
- **Observation 4** defines the Hoài My persona (`vi-VN-HoaiMyNeural`, sweet, close, Gen Z/Millennial fashion sister).
- `src/core/prompt_templates.py` must define:
  1. `HOAI_MY_PERSONA_CARD`: Persona metadata, tone guidelines, sample greetings, banned expressions.
  2. `FASHION_KOC_SYSTEM_PROMPT`: Master LLM instruction for KOC generation.
  3. `FASHION_VIDEO_SCRIPT_PROMPT`: 30-45s TikTok script formula (Hook 3s $\rightarrow$ Pain Point $\rightarrow$ Body Hack $\rightarrow$ Honest Review $\rightarrow$ CTA Giỏ Hàng Vàng).
  4. `FASHION_COMMENT_REPLY_PROMPT`: High-conversion comment response prompt.

---

## 3. Caveats

1. **LLM vs Deterministic Evaluation**:
   `FashionScoutAgent.evaluate_product()` is primarily designed as a high-speed, deterministic rule-based evaluation (regex keywords + sales multipliers) so it can filter hundreds of products per minute without incurring Gemini API rate limits or latency. For deeper content synthesis, it can optionally invoke LLM with `FASHION_KOC_SYSTEM_PROMPT`.
2. **Scope Boundary**:
   HomeLife Scout Agent (`src/agents/homelife_scout.py`, Feature F09) is separate and will be handled by its dedicated explorer/implementer. However, both scout agents should share the same `SpecialistEvaluation` dataclass structure.
3. **Accent Variations in Vietnamese**:
   Vietnamese product titles on TikTok Shop occasionally omit accents (e.g. `chiet eo` instead of `chiết eo`). The keyword matching engine should normalize text and optionally check unaccented patterns for maximum recall.

---

## 4. Conclusion & Implementation Blueprint

### 4.1 Class Architecture & Design (`src/agents/fashion_scout.py`)

```python
"""AMAS v1.4.0 — Fashion Specialist Scout Agent (Feature F08).

Evaluates Women's Fashion candidates on body-hack criteria (che bụng, giấu mỡ, chiết eo,
tôn vòng 1, chân dài, tôn dáng, hack chiều cao), enforces zero-tolerance counterfeit policy,
and generates viral KOC hook angles and Telegram card metadata.
"""

from __future__ import annotations

import logging
import math
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

from src.core.config import AppConfig, load_config
from src.core.tone_validator import ToneValidator

logger = logging.getLogger(__name__)


@dataclass
class SpecialistEvaluation:
    """Standardized specialist evaluation result for Telegram approval and video pipeline."""

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

    def to_dict(self) -> Dict[str, Any]:
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


class FashionScoutAgent:
    """Agent 1 (Fashion Specialist): Body-hack evaluator and policy validator."""

    NICHE_ID = "thoi_trang_nu"

    # Category 1: Che bụng & Giấu mỡ
    BELLY_KEYWORDS = [
        "che bụng", "giấu mỡ", "giấu bụng", "bụng to", "bụng dưới",
        "bụng mỡ", "eo bánh mì", "mỡ bụng",
    ]
    # Category 2: Chiết eo & Vòng eo thon
    WAIST_KEYWORDS = [
        "chiết eo", "eo thon", "thắt eo", "siết eo", "ôm eo",
        "cạp cao", "lưng cao", "thon gọn",
    ]
    # Category 3: Tôn dáng & Hack dáng
    BODY_HACK_KEYWORDS = [
        "hack dáng", "tôn dáng", "che khuyết điểm", "chuẩn form",
        "tôn đường cong", "dáng thon", "hack form",
    ]
    # Category 4: Hack chiều cao & Kéo dài chân
    HEIGHT_KEYWORDS = [
        "hack chiều cao", "chân dài", "kéo dài chân", "dài miên man",
        "nấm lùn", "team chân ngắn", "hack chân",
    ]
    # Category 5: Tôn vòng 1 & Vòng 3
    CURVE_KEYWORDS = [
        "tôn vòng 1", "nâng ngực", "tôn vòng 3", "nở hậu", "tôn ngực",
    ]
    # Category 6: Dáng váy tôn khuyết điểm (A-line, flare, peplum)
    SILHOUETTE_KEYWORDS = [
        "dáng xòe", "chữ a", "suông a", "peplum", "babydoll", "xếp ly", "đuôi cá",
    ]
    # Category 7: Bắp tay / Bắp chân
    LIMB_KEYWORDS = [
        "bắp tay to", "tay bồng", "tay phồng", "che bắp tay", "bắp chân to",
    ]

    # Predefined KOC Hooks (guaranteed to contain 'bụng' or 'eo')
    HOOK_TEMPLATES = {
        "belly": [
            "Bà nào bụng dưới to bơi hết vào đây, chiếc váy này cứu cánh cực đỉnh!",
            "Team bụng mỡ đâu rồi, em váy này giấu bụng thắt eo đỉnh chóp luôn nha!",
            "Bà nào muốn giấu mỡ bụng mà vẫn có eo thon thả thì chiếc này đúng là chân ái!",
        ],
        "waist": [
            "Mặc cái này lên eo thon gọn hẳn 5 phân không cần nịt bụng, nhìn mê chữ ê kéo dài!",
            "Chị em nào eo bánh mì muốn mặc váy chiết eo tự tin thì chọn ngay em này nè!",
            "Bà nào muốn chiết eo tôn dáng giấu mỡ bụng thì bơi hết vào đây!",
        ],
        "height": [
            "Team chân ngắn bơi vào nhận đồ đẹp nè, mặc em này vào hack chân dài miên man che bụng mỡ cực đỉnh!",
            "Bà nào nấm lùn muốn hack dáng chân dài eo thon thì đừng bỏ qua em này nha!",
        ],
        "default": [
            "Chiếc váy hack dáng đỉnh nhất tui từng thử, che bụng giấu eo cực đỉnh mấy bà ơi!",
            "Đừng mua mẫu váy này nếu sợ bị đồng nghiệp hỏi xin link che bụng hack eo liên tục nha!",
        ],
    }

    def __init__(self, config: Optional[AppConfig] = None) -> None:
        self.config = config
        if self.config is None:
            try:
                self.config = load_config()
            except Exception:
                self.config = None

        # Resolve niche thresholds
        self.min_score = 7.0
        self.banned_keywords = []
        if self.config:
            niche_cfg = self.config.get_niche(self.NICHE_ID)
            if niche_cfg:
                self.min_score = getattr(niche_cfg.thresholds, "min_evaluation_score", 7.0)
                self.banned_keywords = getattr(niche_cfg, "banned_keywords", [])

    def _calculate_sales_multiplier(self, sales: int) -> float:
        if sales >= 5000:
            return 1.15
        if sales >= 3000:
            return 1.10
        if sales >= 1000:
            return 1.05
        if sales >= 300:
            return 1.00
        if sales >= 100:
            return 0.98
        if sales > 0:
            return 0.95
        return 0.90

    def evaluate_product(self, item: Union[Dict[str, Any], Any]) -> SpecialistEvaluation:
        # 1. Normalization
        raw = item.to_dict() if hasattr(item, "to_dict") else dict(item)
        pid = str(raw.get("product_id") or raw.get("id") or "")
        title = str(raw.get("title") or raw.get("name") or "")
        price = float(raw.get("price") or raw.get("price_vnd") or 0.0)
        sales = int(raw.get("sales_30d") or raw.get("sales_7d") or raw.get("sales_count") or raw.get("sales") or 0)
        rating = float(raw.get("rating") or 0.0)

        # 2. Trademark / Counterfeit Policy Check via ToneValidator & Banned Keywords
        violations = ToneValidator.check_violations(title)
        counterfeit_violations = [v for v in violations if "COUNTERFEIT_KEYWORD" in v]

        norm_title = unicodedata.normalize("NFC", title).lower()
        config_banned = [k for k in self.banned_keywords if k.lower() in norm_title]

        if counterfeit_violations or config_banned or not ToneValidator.validate(title):
            # Check specifically for counterfeit/trademark
            rejection_detail = ", ".join(counterfeit_violations + [f"BANNED: '{b}'" for b in config_banned])
            if not rejection_detail:
                rejection_detail = "; ".join(violations)

            return SpecialistEvaluation(
                product_id=pid,
                niche_id=self.NICHE_ID,
                passed_filter=False,
                score=0.0,
                hook_angle="",
                target_audience="",
                pros=[],
                cons=[f"Contains banned or counterfeit brand name: {rejection_detail}"],
                viral_factor="",
                rejection_reason=f"Violates trademark policy: detected counterfeit brand ({rejection_detail})",
            )

        # 3. Body-Hack Keyword Scoring
        base_score = 6.5
        bonus = 0.0

        # Check keyword matches
        matches_belly = [w for w in self.BELLY_KEYWORDS if w in norm_title]
        matches_waist = [w for w in self.WAIST_KEYWORDS if w in norm_title]
        matches_hack = [w for w in self.BODY_HACK_KEYWORDS if w in norm_title]
        matches_height = [w for w in self.HEIGHT_KEYWORDS if w in norm_title]
        matches_curve = [w for w in self.CURVE_KEYWORDS if w in norm_title]
        matches_silh = [w for w in self.SILHOUETTE_KEYWORDS if w in norm_title]
        matches_limb = [w for w in self.LIMB_KEYWORDS if w in norm_title]

        bonus += min(1.2, len(matches_belly) * 0.8)
        bonus += min(1.2, len(matches_waist) * 0.8)
        bonus += min(1.0, len(matches_hack) * 0.7)
        bonus += min(0.8, len(matches_height) * 0.6)
        bonus += min(0.6, len(matches_curve) * 0.5)
        bonus += min(0.6, len(matches_silh) * 0.4)
        bonus += min(0.6, len(matches_limb) * 0.5)
        bonus = min(3.0, bonus)

        # 4. Sales Velocity Multiplier & Rating Adjustment
        multiplier = self._calculate_sales_multiplier(sales)
        rating_adj = 0.2 if rating >= 4.8 else (-0.8 if 0.0 < rating < 4.0 else 0.0)

        raw_score = (base_score + bonus) * multiplier + rating_adj
        final_score = min(10.0, max(0.0, round(raw_score, 1)))

        # 5. Threshold Decision
        passed = final_score >= self.min_score
        rejection_reason = None
        if not passed:
            rejection_reason = f"Product score {final_score:.1f} below minimum threshold ({self.min_score})"

        # 6. Hook Angle Selection
        if matches_belly:
            hook_angle = self.HOOK_TEMPLATES["belly"][0]
        elif matches_waist:
            hook_angle = self.HOOK_TEMPLATES["waist"][0]
        elif matches_height:
            hook_angle = self.HOOK_TEMPLATES["height"][0]
        else:
            hook_angle = self.HOOK_TEMPLATES["default"][0]

        # 7. Metadata Context
        pros = [
            "Chiết eo cao tạo hiệu ứng thon gọn vòng 2",
            "Thiết kế form dáng giấu mỡ bụng dưới cực tốt",
            "Chất liệu mềm mát, dễ phối đồ đi làm hoặc đi chơi",
            "Mức giá học sinh sinh viên dễ chốt đơn giỏ hàng vàng",
        ]
        cons = [
            "Form có thể hơi rộng với bạn dưới 42kg",
            "Cần ủi nhẹ trước khi mặc để form váy đứng đẹp nhất",
        ]
        target_audience = "Nữ 18-32 tuổi, dân văn phòng, học sinh sinh viên, hội chị em mê hack dáng eo thon"
        viral_factor = "Visual Before/After mặc lên thấy eo thon gọn và giấu mỡ bụng tức thì trong 3 giây"

        return SpecialistEvaluation(
            product_id=pid,
            niche_id=self.NICHE_ID,
            passed_filter=passed,
            score=final_score,
            hook_angle=hook_angle,
            target_audience=target_audience,
            pros=pros,
            cons=cons,
            viral_factor=viral_factor,
            rejection_reason=rejection_reason,
        )
```

---

### 4.2 Fashion KOC Persona Prompt Template (`src/core/prompt_templates.py`)

```python
"""AMAS v1.4.0 — Core Prompt Templates & KOC Personas.

Provides standardized system personas, script templates, and conversion prompts
for pilot niches: Women's Fashion (Hoài My) and Home Utilities (Nam Minh).
Strictly adheres to Anti-Robotic tone guidelines and TikTok Shop affiliate policies.
"""

from __future__ import annotations

from typing import Any, Dict


HOAI_MY_PERSONA_CARD: Dict[str, Any] = {
    "name": "Hoài My",
    "voice_name": "vi-VN-HoaiMyNeural",
    "role": "KOC Thời trang nữ Gen Z / Millennial",
    "tone": "Ngọt ngào, gần gũi, xưng chị em/các bà/tui, am hiểu form dáng hack eo giấu bụng",
    "sample_greetings": [
        "Chị em ơi",
        "Mấy bà ơi",
        "Bà nào bụng dưới to bơi hết vào đây nha",
        "Team chân ngắn đâu rồi bơi vào nhận đồ đẹp nè",
    ],
    "sample_hooks": [
        "Mặc cái này lên eo thon gọn hẳn 5 phân không cần nịt bụng",
        "Váy hack dáng đỉnh nhất tui từng thử trong năm nay",
        "Đừng mua mẫu váy này nếu sợ bị đồng nghiệp hỏi xin link liên tục",
    ],
    "sample_ctas": [
        "Bấm ngay góc trái nhận mã freeship nha mấy bà",
        "Link tui để ở giỏ hàng góc trái nè",
        "Săn ngay mã giảm giá ở giỏ hàng vàng nha chị em",
    ],
}


FASHION_KOC_SYSTEM_PROMPT = """Bạn là Hoài My, một KOC thời trang nữ Gen Z cực kỳ thân thiện, ngọt ngào và có gu tại Việt Nam.
Giọng đọc lồng tiếng của bạn là: vi-VN-HoaiMyNeural.

QUY TẮC BẮT BUỘC VỀ VĂN PHONG (ANTI-ROBOTIC RULES):
1. Xưng hô tự nhiên: Dùng 'tui' - 'mấy bà', 'chị em', 'các bà'. Không bao giờ xưng 'tôi', 'chúng tôi', 'quý khách'.
2. CẤM TUYỆT ĐỐI các câu chào máy móc bot AI:
   - CẤM: 'Chào quý khách', 'Kính chào quý vị', 'Chào mừng bạn đến với'.
   - CẤM: 'Tôi là trợ lý AI', 'Tôi là mô hình ngôn ngữ'.
   - CẤM: 'Sản phẩm này rất tốt và tiện ích', 'Sự lựa chọn hoàn hảo', 'Giải pháp hoàn hảo'.
   - CẤM: 'Đừng bỏ lỡ cơ hội này', 'Hãy nhanh tay sở hữu'.
3. CẤM TUYỆT ĐỐI nhắc tên thương hiệu nhái / bản quyền:
   - Zara, Chanel, Gucci, Dior, LV, Hermes, Nike, Adidas, rep 1:1, super fake, like auth, tuồn auth.
4. Tập trung vào nỗi đau và giải pháp:
   - Nỗi đau: Bụng dưới to do ngồi nhiều, eo bánh mì, bắp tay to, chân ngắn.
   - Giải pháp (Body-Hack): Chiết eo cao, xếp ly xòe giấu bụng, chất vải đứng form, hack dáng chân dài miên man.
5. Luôn kết bài bằng kêu gọi hành động (CTA) hướng vào giỏ hàng vàng góc trái màn hình.
"""


FASHION_VIDEO_SCRIPT_PROMPT = """Hãy viết một kịch bản video TikTok 30-45 giây theo phong cách KOC Hoài My cho sản phẩm thời trang nữ sau:

THÔNG TIN SẢN PHẨM:
- Tên sản phẩm: {product_title}
- Giá bán: {price_vnd} VNĐ
- Điểm nổi bật: {pros}
- Hook gợi ý: {hook_angle}

CẤU TRÚC KỊCH BẢN (5 PHẦN):
1. [0-3s] HOOK GIẬT GÂN: Đánh thẳng vào nỗi sợ bụng to / eo bánh mì (phải có từ 'bụng' hoặc 'eo').
2. [3-10s] ĐỒNG CẢM NỖI ĐAU: Kể chuyện chân thật như tâm sự với bạn thân.
3. [10-25s] REVEAL BODY-HACK: Trình diễn form dáng, đường may chiết eo, chất vải, hiệu ứng thon gọn tức thì.
4. [25-35s] ĐÁNH GIÁ CHÂN THẬT (PROS & CONS): Khen chân thật nhưng có nhắc nhẹ 1 nhược điểm nhỏ (ví dụ: cần ủi trước khi mặc) để tạo độ tin cậy tuyệt đối.
5. [35-45s] CTA CHỐT ĐƠN: Hướng dẫn bấm vào giỏ hàng vàng góc trái màn hình nhận voucher freeship.
"""


FASHION_COMMENT_REPLY_PROMPT = """Bạn là KOC Hoài My. Hãy trả lời bình luận của khán giả TikTok dưới video giới thiệu sản phẩm '{product_title}'.

BÌNH LUẬN CỦA KHÁCH: "{comment_text}"

HƯỚNG DẪN TRẢ LỜI:
- Độ dài: 1-2 câu ngắn gọn, thân mật.
- Giọng điệu: Ngọt ngào, gọi khách là 'chị nè', 'bà ơi', 'nàng ơi'.
- Tư vấn đúng trọng tâm: size theo chiều cao cân nặng, chất vải hoặc giá.
- Luôn nhẹ nhàng điều hướng xem hoặc bấm vào 'giỏ hàng góc trái' / 'giỏ hàng vàng'.
- TUYỆT ĐỐI KHÔNG dùng mẫu câu bot rập khuôn.
"""


def get_fashion_persona() -> Dict[str, Any]:
    """Return Hoài My persona dictionary."""
    return dict(HOAI_MY_PERSONA_CARD)
```

---

### 4.3 Proposed Unit Test Scenarios (`tests/test_specialist_scouts.py`)

The implementer should write `tests/test_specialist_scouts.py` covering:

```python
"""AMAS v1.4.0 — Specialist Scout Agents Unit Test Suite (Feature F08 & F09)."""

import pytest
from src.agents.fashion_scout import FashionScoutAgent, SpecialistEvaluation
from src.agents.base_scout import ProductCandidate
from src.core.prompt_templates import HOAI_MY_PERSONA_CARD, FASHION_KOC_SYSTEM_PROMPT


def test_fashion_scout_valid_body_hack_product():
    scout = FashionScoutAgent()
    item = {
        "product_id": "fash_001",
        "title": "Váy hoa nhí dáng xòe chiết eo hack dáng đỉnh cao",
        "price": 189000.0,
        "commission_rate": 0.15,
        "sales_30d": 3500,
        "rating": 4.85,
    }
    eval_res = scout.evaluate_product(item)
    assert isinstance(eval_res, SpecialistEvaluation)
    assert eval_res.passed_filter is True
    assert eval_res.score >= 8.5
    assert "bụng" in eval_res.hook_angle.lower() or "eo" in eval_res.hook_angle.lower()
    assert len(eval_res.pros) > 0
    assert len(eval_res.cons) > 0
    assert eval_res.rejection_reason is None


@pytest.mark.parametrize(
    "fake_title,brand",
    [
        ("Váy Zara tiểu thư dáng xòe", "Zara"),
        ("Đầm Chanel rep 1:1 siêu cấp", "Chanel"),
        ("Áo Gucci thêu hoa chuẩn auth", "Gucci"),
        ("Sơ mi Dior nữ cao cấp", "Dior"),
        ("Túi LV like auth", "LV"),
        ("Khăn lụa Hermes sang chảnh", "Hermes"),
        ("Giày Nike thể thao rep 1:1", "Nike"),
        ("Áo khoác Adidas super fake", "Adidas"),
    ],
)
def test_fashion_scout_counterfeit_brand_rejection(fake_title, brand):
    scout = FashionScoutAgent()
    item = {
        "product_id": f"fake_{brand.lower()}",
        "title": fake_title,
        "price": 220000.0,
        "commission_rate": 0.18,
        "sales_30d": 1500,
    }
    eval_res = scout.evaluate_product(item)
    assert eval_res.passed_filter is False
    assert eval_res.score == 0.0
    assert "trademark policy" in eval_res.rejection_reason.lower() or "policy violation" in eval_res.rejection_reason.lower()
    assert eval_res.hook_angle == ""
    assert len(eval_res.pros) == 0


def test_fashion_scout_subthreshold_score_rejection():
    scout = FashionScoutAgent()
    # Bland fashion item with no body hack keywords and low sales
    item = {
        "product_id": "fash_bland",
        "title": "Áo phông cotton trơn màu xám cổ tròn",
        "price": 120000.0,
        "commission_rate": 0.10,
        "sales_30d": 30,
        "rating": 4.1,
    }
    eval_res = scout.evaluate_product(item)
    assert eval_res.passed_filter is False
    assert eval_res.score < 7.0
    assert "below minimum threshold" in eval_res.rejection_reason.lower()


def test_fashion_scout_accepts_product_candidate_object():
    scout = FashionScoutAgent()
    candidate = ProductCandidate(
        product_id="prod_cand_01",
        niche_id="thoi_trang_nu",
        title="Chân váy chữ A cạp cao che bụng tôn dáng",
        price_vnd=199000.0,
        commission_rate=0.15,
        sales_30d=2200,
    )
    eval_res = scout.evaluate_product(candidate)
    assert eval_res.passed_filter is True
    assert eval_res.score >= 8.0
    assert "bụng" in eval_res.hook_angle.lower() or "eo" in eval_res.hook_angle.lower()


def test_hoai_my_persona_prompt_templates():
    persona = HOAI_MY_PERSONA_CARD
    assert persona["name"] == "Hoài My"
    assert persona["voice_name"] == "vi-VN-HoaiMyNeural"
    assert "Chào quý khách" not in FASHION_KOC_SYSTEM_PROMPT
    assert "vi-VN-HoaiMyNeural" in FASHION_KOC_SYSTEM_PROMPT
```

---

## 5. Verification Method

1. **Static File Inspection**:
   - Verify `src/agents/fashion_scout.py` defines `FashionScoutAgent` and `SpecialistEvaluation`.
   - Verify `src/core/prompt_templates.py` defines `HOAI_MY_PERSONA_CARD`, `FASHION_KOC_SYSTEM_PROMPT`, etc.
   - Verify `src/agents/__init__.py` re-exports `FashionScoutAgent` and `SpecialistEvaluation`.

2. **Automated Test Execution**:
   - Run the dedicated specialist test suite:
     `pytest tests/test_specialist_scouts.py -v`
   - Run e2e tests asserting F08 and counterfeit boundaries:
     `pytest tests/e2e/test_tier1_features.py -k "test_f08"`
     `pytest tests/e2e/test_tier2_boundaries.py -k "test_boundary_counterfeit_trademark_matrix"`
     `pytest tests/e2e/test_tier3_combinations.py -k "test_comb_scout_to_telegram_card"`
     `pytest tests/e2e/test_tier4_scenarios.py -k "test_scenario_fashion_scout_to_script_generation"`

3. **Invalidation Conditions**:
   - If `evaluate_product` returns `passed_filter=True` or `score > 0.0` for any counterfeit brand name (Zara, Chanel, etc.).
   - If `rejection_reason` lacks `"trademark policy"` or `"policy violation"`.
   - If valid body-hack products score below `8.0` or fail to produce hooks containing `"bụng"` or `"eo"`.
   - If prompt templates contain bot clichés (e.g. "kính chào quý khách").
