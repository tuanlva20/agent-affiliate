"""AMAS v1.4.0 — Home Utilities Specialist Scout Agent (Feature F09).

Evaluates home appliances & utility products for viral TikTok potential based on:
1. Zero tolerance for exaggerated medical or cleaning claims via ToneValidator.
2. Labor-saving utility score (giải phóng sức lao động, nhàn việc nhà, rảnh tay).
3. Visual Before/After 3s contrast hook potential.
4. Realistic KOC Nam Minh persona hook, audience, pros/cons, and viral factor generation.
"""

from __future__ import annotations

import logging
import math
import unicodedata
from typing import Any, Dict, List, Optional, Union

from src.agents.fashion_scout import SpecialistEvaluation
from src.core.config import AppConfig, load_config
from src.core.tone_validator import ToneValidator

logger = logging.getLogger(__name__)


class HomeLifeScoutAgent:
    """Home utilities specialist evaluator (Feature F09)."""

    NICHE_ID: str = "do_gia_dung"
    MIN_EVALUATION_SCORE: float = 7.0

    # Keywords for Labor-Saving Utility (Dimension 1)
    LABOR_SAVING_TIER1: List[str] = [
        "tự vắt", "tự động", "không chạm tay", "rảnh tay", "thông minh",
        "công nghệ mới", "thế hệ mới", "robot", "hút bụi tự động", "giải phóng sức lao động",
    ]
    LABOR_SAVING_TIER2: List[str] = [
        "xoay 360", "360 độ", "đa năng", "tiện lợi", "tiện ích", "nhàn",
        "gấp gọn", "nhẹ nhàng", "tiết kiệm thời gian", "rút gọn", "chống mỏi lưng",
        "không dây", "cầm tay",
    ]

    # Keywords for Visual Before/After 3s Contrast (Dimension 2)
    VISUAL_CONTRAST_KEYWORDS: List[str] = [
        "lau nhà", "hút bụi", "tẩy sạch", "tẩy cặn", "sạch bóng", "sạch bong",
        "đánh bay", "vắt khô", "lau kính", "hô biến", "3s", "3 giây", "tức thì",
        "nhanh chóng", "kin kít", "sáng bóng",
    ]

    def __init__(self, config: Optional[AppConfig] = None) -> None:
        self.config = config
        self.banned_keywords: List[str] = []
        if self.config is None:
            try:
                self.config = load_config()
            except Exception:
                self.config = None

        if self.config:
            niche_cfg = self.config.get_niche(self.NICHE_ID)
            if niche_cfg:
                self.MIN_EVALUATION_SCORE = getattr(
                    niche_cfg.thresholds, "min_evaluation_score", 7.0
                )
                self.banned_keywords = getattr(niche_cfg, "banned_keywords", []) or []

    def evaluate_product(self, item: Union[Dict[str, Any], Any]) -> SpecialistEvaluation:
        """Evaluate a home utilities product candidate."""
        # 1. Normalize input
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
            raw_dict = item.to_dict()
        elif isinstance(item, dict):
            raw_dict = item
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

        pid = str(raw_dict.get("product_id") or raw_dict.get("id") or "").strip()
        title = str(raw_dict.get("title") or raw_dict.get("name") or "").strip()

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
            raw_price = raw_dict.get("price") if raw_dict.get("price") is not None else raw_dict.get("price_vnd")
            price = float(raw_price if raw_price is not None else 0.0)
            raw_comm = raw_dict.get("commission_rate") if raw_dict.get("commission_rate") is not None else raw_dict.get("commission")
            comm_rate = float(raw_comm if raw_comm is not None else 0.0)
            raw_sales = (
                raw_dict.get("sales_30d")
                if raw_dict.get("sales_30d") is not None
                else (
                    raw_dict.get("sales_7d")
                    if raw_dict.get("sales_7d") is not None
                    else (
                        raw_dict.get("sales_count")
                        if raw_dict.get("sales_count") is not None
                        else raw_dict.get("sales")
                    )
                )
            )
            sales_30d = int(float(raw_sales if raw_sales is not None else 0))
            if (
                math.isnan(price)
                or math.isinf(price)
                or math.isnan(comm_rate)
                or math.isinf(comm_rate)
                or price < 0
                or comm_rate < 0
                or sales_30d < 0
            ):
                raise ValueError("Invalid numeric value: negative, NaN, or Inf not permitted")
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

        # 2. Check policy violations (ToneValidator & banned patterns)
        violations = ToneValidator.check_violations(title)
        norm_title = unicodedata.normalize("NFC", title).lower()
        canon_title = ToneValidator.canonicalize_brand_text(title)
        config_banned = [
            k for k in getattr(self, "banned_keywords", [])
            if k.lower() in norm_title or (canon_title and k.lower() in canon_title)
        ]

        if not ToneValidator.validate(title) or violations or config_banned:
            is_counterfeit = any("COUNTERFEIT_KEYWORD" in v for v in violations)
            if is_counterfeit:
                rejection_reason = "Violates trademark policy: detected counterfeit brand or unauthorized trademark"
            else:
                rejection_reason = "Violates exaggerated policy: contains exaggerated claims or unverified medical/cleaning promises"

            return SpecialistEvaluation(
                product_id=pid,
                niche_id=self.NICHE_ID,
                passed_filter=False,
                score=0.0,
                hook_angle="",
                target_audience="",
                pros=[],
                cons=["Contains exaggerated claims or policy violations"],
                viral_factor="",
                rejection_reason=rejection_reason,
            )

        # 3. Calculate quantitative score
        score = self._calculate_score(raw_dict, title)

        # 4. Check against minimum evaluation score threshold
        if score < self.MIN_EVALUATION_SCORE:
            return SpecialistEvaluation(
                product_id=pid,
                niche_id=self.NICHE_ID,
                passed_filter=False,
                score=score,
                hook_angle="",
                target_audience="",
                pros=[],
                cons=["Low viral contrast", "Limited labor-saving utility"],
                viral_factor="",
                rejection_reason=f"Product score {score:.1f} below minimum threshold ({self.MIN_EVALUATION_SCORE}): lacks strong labor-saving utility or visual contrast",
            )

        # 5. Generate Nam Minh KOC attributes for passing products
        hook_angle, viral_factor, target_audience, pros, cons = self._generate_koc_attributes(title, raw_dict)

        return SpecialistEvaluation(
            product_id=pid,
            niche_id=self.NICHE_ID,
            passed_filter=True,
            score=score,
            hook_angle=hook_angle,
            target_audience=target_audience,
            pros=pros,
            cons=cons,
            viral_factor=viral_factor,
            rejection_reason=None,
        )

    def _calculate_score(self, item: Dict[str, Any], title: str) -> float:
        """Calculate score from 0.0 to 10.0 based on labor saving and visual contrast."""
        title_lower = title.lower()

        # Dimension 1: Labor-Saving Utility (Max +2.0)
        tier1_matches = sum(1 for kw in self.LABOR_SAVING_TIER1 if kw in title_lower)
        tier2_matches = sum(1 for kw in self.LABOR_SAVING_TIER2 if kw in title_lower)
        labor_bonus = min(2.0, (tier1_matches * 1.2) + (tier2_matches * 0.6))

        # Dimension 2: Visual Before/After 3s Contrast (Max +1.2)
        visual_matches = sum(1 for kw in self.VISUAL_CONTRAST_KEYWORDS if kw in title_lower)
        if visual_matches >= 2:
            visual_bonus = 1.2
        elif visual_matches == 1:
            visual_bonus = 0.6
        else:
            visual_bonus = 0.0

        # Dimension 3: Market Velocity (Max +0.5)
        sales_30d = int(item.get("sales_30d") or item.get("sales_7d") or item.get("sales_count") or item.get("sales") or 0)
        if sales_30d >= 5000:
            velocity_bonus = 0.5
        elif sales_30d >= 1000:
            velocity_bonus = 0.3
        elif sales_30d >= 200:
            velocity_bonus = 0.1
        else:
            velocity_bonus = 0.0

        # Dimension 4: Price Sweet Spot (Max +0.3)
        price = float(item.get("price") or item.get("price_vnd") or 0.0)
        if 99000.0 <= price <= 350000.0:
            price_bonus = 0.3
        elif 49000.0 <= price < 99000.0 or 350000.0 < price <= 800000.0:
            price_bonus = 0.1
        else:
            price_bonus = 0.0

        # Dimension 5: Rating adjustment
        rating = 0.0
        try:
            rating = float(item.get("rating") or (item.get("raw_data", {}).get("rating") if isinstance(item.get("raw_data"), dict) else 0.0) or 0.0)
        except (ValueError, TypeError):
            rating = 0.0
        if rating >= 4.8:
            rating_bonus = 0.2
        elif 0.0 < rating < 4.2:
            rating_bonus = -0.5
        else:
            rating_bonus = 0.0

        # Base score calibration:
        # If product has no labor-saving utility and no visual contrast, cap below threshold (< 7.0)
        if labor_bonus == 0.0 and visual_bonus == 0.0:
            score = 5.8 + velocity_bonus + price_bonus + rating_bonus
        else:
            score = 6.0 + labor_bonus + visual_bonus + velocity_bonus + price_bonus + rating_bonus

        return min(10.0, max(0.0, round(score, 1)))

    def _generate_koc_attributes(
        self, title: str, item: Dict[str, Any]
    ) -> tuple[str, str, str, List[str], List[str]]:
        """Generate hook angle, viral factor, target audience, pros, and cons."""
        title_lower = title.lower()

        # Category detection
        is_cleaner = any(k in title_lower for k in ["lau", "vắt", "vệ sinh", "chổi", "cọ", "xịt", "tẩy", "rửa"])
        is_kitchen = any(k in title_lower for k in ["bếp", "nồi", "chảo", "dao", "kéo", "gọt", "cắt", "chiên", "nướng"])

        if is_cleaner:
            hook_angle = "Từ ngày tậu em này việc nhà nhàn hẳn, đúng 3s là nhà sạch bóng kin kít các bác ơi!"
            viral_factor = "Visual Before/After 3s vắt khô kiệt nước không cần chạm tay"
            target_audience = "Người nội trợ, gia đình trẻ bận rộn, người ngại dọn dẹp nhà cửa"
            pros = [
                "Tiết kiệm 80% thời gian dọn dẹp nhà cửa",
                "Xoay 360 độ luồn lách mọi ngóc ngách dễ dàng",
                "Vắt khô kiệt nước không cần chạm tay bẩn",
            ]
            cons = [
                "Cần thay thế bông lau định kỳ sau 3-6 tháng sử dụng",
            ]
        elif is_kitchen:
            hook_angle = "Bác nào ngại việc bếp núc bơi vào đây, có em này nấu nướng dọn dẹp nhàn tênh chỉ mất 3s!"
            viral_factor = "Visual Before/After 3s sơ chế và làm sạch siêu tốc, vắt khô sạch sẽ"
            target_audience = "Người thích nấu nướng, hội yêu bếp nghiện nhà, mẹ bỉm bận rộn"
            pros = [
                "Tiết kiệm 70% thời gian chuẩn bị và nấu nướng",
                "Chất liệu cao cấp an toàn thực phẩm, dễ tháo rửa",
                "Thiết kế thông minh đa năng, tối ưu không gian bếp",
            ]
            cons = [
                "Cần vệ sinh kỹ các khớp nối nhỏ sau khi sử dụng",
            ]
        else:
            hook_angle = "Từ ngày tậu em này việc nhà nhàn hẳn, đúng 3s là thấy cuộc đời thảnh thơi các bác ạ!"
            viral_factor = "Visual Before/After 3s vắt khô làm sạch thấy ngay hiệu quả"
            target_audience = "Gia đình trẻ, người bận rộn, sinh viên, người ở chung cư"
            pros = [
                "Giải phóng sức lao động tức thì, tối ưu cuộc sống",
                "Thiết kế gọn nhẹ, tiện ích thông minh tiện dụng",
                "Giá thành hợp lý, độ hoàn thiện chắc chắn",
            ]
            cons = [
                "Cần đọc kỹ hướng dẫn để lắp ráp đúng khớp",
            ]

        return hook_angle, viral_factor, target_audience, pros, cons
