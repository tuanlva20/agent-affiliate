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
from typing import Any, Dict, List, Optional, Union

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
        if not isinstance(data, dict):
            data = {}
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


class FashionScoutAgent:
    """Agent 1 (Fashion Specialist): Body-hack evaluator and policy validator."""

    NICHE_ID: str = "thoi_trang_nu"

    # Category 1: Che bụng & Giấu mỡ
    BELLY_KEYWORDS: List[str] = [
        "che bụng", "giấu mỡ", "giấu bụng", "bụng to", "bụng dưới",
        "bụng mỡ", "eo bánh mì", "mỡ bụng",
    ]
    # Category 2: Chiết eo & Vòng eo thon
    WAIST_KEYWORDS: List[str] = [
        "chiết eo", "eo thon", "thắt eo", "siết eo", "ôm eo",
        "cạp cao", "lưng cao", "thon gọn",
    ]
    # Category 3: Tôn dáng & Hack dáng
    BODY_HACK_KEYWORDS: List[str] = [
        "hack dáng", "tôn dáng", "che khuyết điểm", "chuẩn form",
        "tôn đường cong", "dáng thon", "hack form",
    ]
    # Category 4: Hack chiều cao & Kéo dài chân
    HEIGHT_KEYWORDS: List[str] = [
        "hack chiều cao", "chân dài", "kéo dài chân", "dài miên man",
        "nấm lùn", "team chân ngắn", "hack chân",
    ]
    # Category 5: Tôn vòng 1 & Vòng 3
    CURVE_KEYWORDS: List[str] = [
        "tôn vòng 1", "nâng ngực", "tôn vòng 3", "nở hậu", "tôn ngực",
    ]
    # Category 6: Dáng váy tôn khuyết điểm (A-line, flare, peplum)
    SILHOUETTE_KEYWORDS: List[str] = [
        "dáng xòe", "chữ a", "suông a", "peplum", "babydoll", "xếp ly", "đuôi cá",
    ]
    # Category 7: Bắp tay / Bắp chân
    LIMB_KEYWORDS: List[str] = [
        "bắp tay to", "tay bồng", "tay phồng", "che bắp tay", "bắp chân to",
    ]

    # Predefined KOC Hooks (guaranteed to contain 'bụng' or 'eo' and pass ToneValidator)
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
            "Bà nào muốn chiết eo tôn dáng giấu mỡ bụng thì bơi hết vào đây!",
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
        self.min_score: float = 7.0
        self.banned_keywords: List[str] = []
        if self.config:
            niche_cfg = self.config.get_niche(self.NICHE_ID)
            if niche_cfg:
                self.min_score = getattr(niche_cfg.thresholds, "min_evaluation_score", 7.0)
                self.banned_keywords = getattr(niche_cfg, "banned_keywords", [])

    def _calculate_sales_multiplier(self, sales: int) -> float:
        """Calculate score multiplier based on 30-day sales velocity."""
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
        """Evaluate a women's fashion candidate against body-hack criteria and policies."""
        # 1. Normalization & input validation
        if item is None:
            return SpecialistEvaluation(
                product_id="unknown",
                niche_id=self.NICHE_ID,
                passed_filter=False,
                score=0.0,
                hook_angle="",
                target_audience="",
                pros=[],
                cons=["Invalid input: None"],
                viral_factor="",
                rejection_reason="Invalid product input: None",
            )

        if hasattr(item, "to_dict") and callable(getattr(item, "to_dict")):
            raw = item.to_dict()
        elif isinstance(item, dict):
            raw = item
        else:
            return SpecialistEvaluation(
                product_id="invalid",
                niche_id=self.NICHE_ID,
                passed_filter=False,
                score=0.0,
                hook_angle="",
                target_audience="",
                pros=[],
                cons=["Input must be a dictionary or ProductCandidate"],
                viral_factor="",
                rejection_reason="Invalid product input: not a dictionary",
            )

        pid = str(raw.get("product_id") or raw.get("id") or "").strip()
        title = str(raw.get("title") or raw.get("name") or "").strip()

        if not pid or not title:
            return SpecialistEvaluation(
                product_id=pid or "unknown",
                niche_id=self.NICHE_ID,
                passed_filter=False,
                score=0.0,
                hook_angle="",
                target_audience="",
                pros=[],
                cons=["Missing product_id or title"],
                viral_factor="",
                rejection_reason="Invalid product input: missing product_id or title",
            )

        # Validate numeric types
        try:
            raw_price = raw.get("price") if raw.get("price") is not None else raw.get("price_vnd")
            price = float(raw_price if raw_price is not None else 0.0)
            raw_comm = raw.get("commission_rate") if raw.get("commission_rate") is not None else raw.get("commission")
            comm_rate = float(raw_comm if raw_comm is not None else 0.0)
            raw_sales = (
                raw.get("sales_30d")
                if raw.get("sales_30d") is not None
                else (
                    raw.get("sales_7d")
                    if raw.get("sales_7d") is not None
                    else (
                        raw.get("sales_count")
                        if raw.get("sales_count") is not None
                        else raw.get("sales")
                    )
                )
            )
            sales = int(float(raw_sales if raw_sales is not None else 0))
            raw_rating = raw.get("rating")
            if raw_rating is None and isinstance(raw.get("raw_data"), dict):
                raw_rating = raw.get("raw_data", {}).get("rating")
            rating = float(raw_rating if raw_rating is not None else 0.0)

            if (
                math.isnan(price)
                or math.isinf(price)
                or math.isnan(comm_rate)
                or math.isinf(comm_rate)
                or price < 0
                or comm_rate < 0
                or sales < 0
            ):
                raise ValueError("Invalid numeric value: negative, NaN, or Inf not permitted")
            if math.isnan(rating) or math.isinf(rating) or rating < 0:
                rating = 0.0
        except (ValueError, TypeError):
            return SpecialistEvaluation(
                product_id=pid,
                niche_id=self.NICHE_ID,
                passed_filter=False,
                score=0.0,
                hook_angle="",
                target_audience="",
                pros=[],
                cons=["Invalid numeric values in product data"],
                viral_factor="",
                rejection_reason="Invalid product input: numeric parsing error",
            )

        # 2. Trademark / Counterfeit Policy Check via ToneValidator & Config Banned Keywords
        violations = ToneValidator.check_violations(title)
        counterfeit_violations = [v for v in violations if "COUNTERFEIT_KEYWORD" in v]

        norm_title = unicodedata.normalize("NFC", title).lower()
        canon_title = ToneValidator.canonicalize_brand_text(title)
        config_banned = [
            k for k in self.banned_keywords
            if k.lower() in norm_title or (canon_title and k.lower() in canon_title)
        ]

        if counterfeit_violations or config_banned:
            rejection_detail = ", ".join(counterfeit_violations + [f"BANNED: '{b}'" for b in config_banned])
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

        # Also check general ToneValidator compliance
        if not ToneValidator.validate(title):
            return SpecialistEvaluation(
                product_id=pid,
                niche_id=self.NICHE_ID,
                passed_filter=False,
                score=0.0,
                hook_angle="",
                target_audience="",
                pros=[],
                cons=["Product title violates tone or policy guidelines"],
                viral_factor="",
                rejection_reason=f"Policy violation: product violates tone or content policy ({'; '.join(violations)})",
            )

        # 3. Body-Hack Keyword Scoring
        base_score = 6.5
        bonus = 0.0

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

        # If item has no body-hack features, score should be low (< 7.0)
        multiplier = self._calculate_sales_multiplier(sales)
        rating_adj = 0.2 if rating >= 4.8 else (-0.8 if 0.0 < rating < 4.0 else 0.0)

        if bonus > 0.0:
            raw_score = (base_score + bonus) * multiplier + rating_adj
        else:
            # Bland item with no body-hack attributes
            raw_score = 5.8 * multiplier + rating_adj

        final_score = min(10.0, max(0.0, round(raw_score, 1)))

        # 4. Threshold Decision
        passed = final_score >= self.min_score
        rejection_reason = None
        if not passed:
            rejection_reason = f"Product score {final_score:.1f} below minimum threshold ({self.min_score})"
            return SpecialistEvaluation(
                product_id=pid,
                niche_id=self.NICHE_ID,
                passed_filter=False,
                score=final_score,
                hook_angle="",
                target_audience="",
                pros=[],
                cons=["Lacks strong body-hack appeal", "Mediocre sales velocity"],
                viral_factor="",
                rejection_reason=rejection_reason,
            )

        # 5. Hook Angle Selection (guaranteed to contain 'bụng' or 'eo')
        if matches_belly:
            hook_angle = self.HOOK_TEMPLATES["belly"][0]
        elif matches_waist:
            hook_angle = self.HOOK_TEMPLATES["waist"][0]
        elif matches_height:
            hook_angle = self.HOOK_TEMPLATES["height"][0]
        else:
            hook_angle = self.HOOK_TEMPLATES["default"][0]

        # 6. Metadata Context for Telegram Card
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
            passed_filter=True,
            score=final_score,
            hook_angle=hook_angle,
            target_audience=target_audience,
            pros=pros,
            cons=cons,
            viral_factor=viral_factor,
            rejection_reason=None,
        )
