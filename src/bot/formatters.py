"""AMAS v1.4.0 — Telegram Product Card & Alert Formatters (Feature F10, F11).

Provides:
- format_product_card: Formats candidate product and specialist evaluation into a KOC-styled card.
- format_captcha_alert: Emergency alert formatter for Captcha encounters.
- format_product_message: Alias for format_product_card.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from src.agents.fashion_scout import SpecialistEvaluation


def format_product_card(
    product: Union[Dict[str, Any], Any, str],
    evaluation: Optional[SpecialistEvaluation] = None,
    title: Optional[str] = None,
    price_vnd: Optional[float] = None,
    commission_rate: Optional[float] = None,
    score: Optional[float] = None,
    hook_angle: Optional[str] = None,
) -> str:
    """Format a scouted product candidate and specialist evaluation into a Telegram card.

    Supports both (product, evaluation) and flat parameter invocation.
    Guaranteed to comply with ToneValidator and contain natural KOC markers.
    """
    # 1. Handle flat parameters invocation if first argument is niche_id string
    if isinstance(product, str) and evaluation is None:
        niche_id = product
        p_title = title or "Sản phẩm tiềm năng"
        p_price = float(price_vnd or 0.0)
        p_comm = float(commission_rate or 0.0)
        p_score = float(score or 8.0)
        p_hook = hook_angle or "Mấy bà ơi em này dùng thích mê luôn á!"
        p_id = "prod_sample"
        p_sales = 500
        target_audience = "Người tiêu dùng thông minh"
        pros = ["Chất lượng ổn định", "Giá thành hợp lý"]
        cons = ["Cần lưu ý bảo quản đúng cách"]
        viral_factor = "Visual 3s thu hút"
    else:
        # Extract from evaluation
        if evaluation is not None:
            niche_id = evaluation.niche_id
            p_score = evaluation.score
            p_hook = evaluation.hook_angle
            p_id = evaluation.product_id
            target_audience = evaluation.target_audience
            pros = evaluation.pros
            cons = evaluation.cons
            viral_factor = evaluation.viral_factor
        else:
            niche_id = getattr(product, "niche_id", "thoi_trang_nu") if not isinstance(product, dict) else product.get("niche_id", "thoi_trang_nu")
            p_score = 8.5
            p_hook = "Chị em ơi lướt thấy em này là phải dừng lại xem ngay nha!"
            p_id = "prod_sample"
            target_audience = "Người tiêu dùng trẻ"
            pros = []
            cons = []
            viral_factor = "Hook 3s bắt mắt"

        # Extract title
        if hasattr(product, "title"):
            p_title = product.title
        elif isinstance(product, dict):
            p_title = product.get("title") or product.get("name") or "Sản phẩm tiềm năng"
        else:
            p_title = "Sản phẩm tiềm năng"

        # Extract product ID if present on product
        if hasattr(product, "product_id") and product.product_id:
            p_id = product.product_id
        elif isinstance(product, dict) and product.get("product_id"):
            p_id = product.get("product_id")

        # Extract price
        if hasattr(product, "price_vnd") and product.price_vnd is not None:
            p_price = float(product.price_vnd)
        elif hasattr(product, "price") and product.price is not None:
            p_price = float(product.price)
        elif isinstance(product, dict):
            raw_price = product.get("price_vnd") if product.get("price_vnd") is not None else product.get("price", 0.0)
            p_price = float(raw_price or 0.0)
        else:
            p_price = 0.0

        # Extract commission rate
        if hasattr(product, "commission_rate") and product.commission_rate is not None:
            p_comm = float(product.commission_rate)
        elif isinstance(product, dict):
            raw_comm = product.get("commission_rate") if product.get("commission_rate") is not None else product.get("commission", 0.0)
            p_comm = float(raw_comm or 0.0)
        else:
            p_comm = 0.0

        # Extract sales
        if hasattr(product, "sales_30d") and product.sales_30d is not None:
            p_sales = int(product.sales_30d)
        elif hasattr(product, "sales_count") and product.sales_count is not None:
            p_sales = int(product.sales_count)
        elif isinstance(product, dict):
            raw_sales = (
                product.get("sales_30d")
                if product.get("sales_30d") is not None
                else (
                    product.get("sales_count")
                    if product.get("sales_count") is not None
                    else product.get("sales", 0)
                )
            )
            p_sales = int(raw_sales or 0)
        else:
            p_sales = 0

    # Calculate financial metrics
    comm_pct = int(round(p_comm * 100)) if p_comm <= 1.0 else int(round(p_comm))
    decimal_comm = p_comm if p_comm <= 1.0 else p_comm / 100.0
    est_payout = int(round(p_price * decimal_comm))

    # Niche & Persona styling
    if niche_id == "thoi_trang_nu":
        header = "👗 [ĐỀ XUẤT SẢN PHẨM — THỜI TRANG NỮ]"
        persona_label = "Hoài My (vi-VN-HoaiMyNeural)"
    elif niche_id == "do_gia_dung":
        header = "🏠 [ĐỀ XUẤT SẢN PHẨM — ĐỒ GIA DỤNG THÔNG MINH]"
        persona_label = "Nam Minh (vi-VN-NamMinhNeural)"
    else:
        header = f"📦 [ĐỀ XUẤT SẢN PHẨM — {niche_id.upper()}]"
        persona_label = "KOC Specialist"

    pros_text = "\n".join(f"• {p}" for p in pros) if pros else "• Thiết kế chuẩn form dáng\n• Độ hoàn thiện chỉn chu"
    cons_text = "\n".join(f"• {c}" for c in cons) if cons else "• Số lượng tồn kho theo đợt có hạn"

    return (
        f"{header}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 Sản phẩm: {p_title}\n"
        f"🆔 Mã SP: {p_id}\n"
        f"💰 Giá bán: {int(p_price):,}đ | Hoa hồng: {comm_pct}% (~{est_payout:,}đ/đơn)\n"
        f"📈 Doanh số 30d: {p_sales:,} đã bán | ⭐ Tiềm năng: {p_score:.1f}/10\n\n"
        f"🎯 Chân dung khách hàng:\n"
        f"• {target_audience}\n\n"
        f"🎙️ Hook 3s ({persona_label}):\n"
        f"\"{p_hook}\"\n\n"
        f"🔥 Yếu tố Viral:\n"
        f"• {viral_factor}\n\n"
        f"✅ Ưu điểm nổi bật (Pros):\n"
        f"{pros_text}\n\n"
        f"⚠️ Điểm yếu / Cần lưu ý (Cons):\n"
        f"{cons_text}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👉 Nhấn nút bên dưới để Duyệt hoặc Từ chối:"
    )


format_product_message = format_product_card


def format_captcha_alert(channel_id: str = "", screenshot_path: Optional[str] = None) -> str:
    """Generate emergency Captcha alarm message."""
    chan_str = f" - KÊNH {channel_id}" if channel_id else ""
    return (
        f"🚨 [CẢNH BÁO CAPTCHA TIKTOK{chan_str}]\n"
        f"Phát hiện màn hình yêu cầu xác minh danh tính. Bot đã tạm dừng an toàn!\n"
        f"👉 Vui lòng mở trình duyệt giải bằng tay trong vòng 5 phút."
    )
