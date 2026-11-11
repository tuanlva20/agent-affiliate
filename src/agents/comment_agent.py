"""AMAS v1.4.0 — Comment Engagement & Conversion Agent (Feature F26 & F27).

Responsible for:
1. High-precision Vietnamese NLP intent classification (CommentIntent).
2. Natural KOC conversion reply generation passing ToneValidator and directing to yellow cart.
"""

from __future__ import annotations

from enum import Enum
import hashlib
import logging
import re
from typing import Any, Dict, List, Optional, Union
import unicodedata

from src.core.tone_validator import ToneValidator

logger = logging.getLogger("amas.agents.comment_agent")


# ==============================================================================
# CommentIntent Enum
# ==============================================================================

class CommentIntent(str, Enum):
    """Categorization of incoming viewer comments for automated KOC conversion."""

    ASK_PRICE = "ask_price"
    ASK_MATERIAL_USAGE = "ask_material_usage"
    COMPLAINT = "complaint"
    OTHER = "other"


# ==============================================================================
# Unicode Normalization Helper
# ==============================================================================

def remove_accents(text: str) -> str:
    """Normalize and strip combining diacritical marks from Vietnamese text."""
    if not text:
        return ""
    text = text.replace("đ", "d").replace("Đ", "D")
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if unicodedata.category(c) != "Mn")


# ==============================================================================
# CommentAgent
# ==============================================================================

class CommentAgent:
    """Agent 5: Natural KOC comment conversion and intent classification."""

    # --------------------------------------------------------------------------
    # Certified Template Banks: Fashion (Hoài My - vi-VN-HoaiMyNeural)
    # --------------------------------------------------------------------------
    FASHION_ASK_PRICE_TEMPLATES: List[str] = [
        "Chị em ơi, em {title} này đang có giá ưu đãi chỉ {price_str} thôi nè. Chị bấm ngay góc trái nhận mã freeship nha!",
        "Mấy bà ơi, chiếc {title} hack dáng này đang sale sốc chỉ {price_str} thôi nè. Bấm vào giỏ hàng vàng góc trái nhận voucher freeship nha chị em!",
        "Dạ chị yêu ơi, em {title} này giá gốc hơn hai trăm mà nay săn sale chỉ còn {price_str} thôi ạ. Chị ghé ngay giỏ hàng vàng góc trái rinh về nha!",
    ]

    FASHION_ASK_MATERIAL_TEMPLATES: List[str] = [
        "Dạ chất vải đũi may 2 lớp cực mát, form che bụng đỉnh chóp luôn chị ạ. Chị chọn size theo bảng trong giỏ hàng vàng nha!",
        "Chị em ơi, em này chất co giãn nhẹ thấm hút mồ hôi, mặc lên hack eo tôn dáng lắm nha. Chị xem bảng size chi tiết ở giỏ hàng góc trái nè!",
        "Mấy bà yên tâm nha, chất vải đứng form dày dặn giấu bụng mỡ cực đỉnh. Chị yêu bấm vào giỏ hàng vàng góc trái xem bảng thông số chuẩn nha!",
    ]

    FASHION_COMPLAINT_TEMPLATES: List[str] = [
        "Dạ chị yêu thông cảm giúp shop đợt này đơn nhiều, chị nhắn tin trực tiếp để shop hỗ trợ kiểm tra đơn ngay nha!",
        "Chị em ơi cho shop xin lỗi về sự bất tiện này nha, chị yêu nhắn tin trực tiếp để bên em ưu tiên hỗ trợ xử lý ngay cho mình nha!",
        "Dạ chị yêu ơi shop rất xin lỗi vì trải nghiệm chưa trọn vẹn ạ, chị nhắn tin qua hộp thư để em hỗ trợ giải quyết liền cho mình nha!",
    ]

    FASHION_OTHER_TEMPLATES: List[str] = [
        "Cảm ơn chị đã quan tâm nè, chị ghé giỏ hàng vàng để xem chi tiết nhé!",
        "Mấy bà ghé giỏ hàng góc trái xem thêm nhiều mẫu xinh và nhận mã freeship nha, yêu chị em nhiều!",
        "Dạ cảm ơn chị yêu nhiều nha, chị bấm vào giỏ hàng vàng góc trái săn deal hời cùng em nhé!",
    ]

    # --------------------------------------------------------------------------
    # Certified Template Banks: Home Utilities (Nam Minh - vi-VN-NamMinhNeural)
    # --------------------------------------------------------------------------
    HOMELIFE_ASK_PRICE_TEMPLATES: List[str] = [
        "Các bác ơi, em {title} này giá đang cực hời chỉ {price_str} thôi. Bác bấm vào giỏ hàng vàng góc trái màn hình nhận mã freeship nha!",
        "Bác ơi, em {title} giúp việc nhà nhàn hẳn này đang sale chỉ còn {price_str} thôi. Bác ghé giỏ hàng vàng góc trái rinh ngay kẻo hết mã giảm giá nha!",
        "Dạ các bác ơi, em {title} tiện ích này chỉ có {price_str} thôi ạ. Bác bấm vào giỏ hàng góc trái nhận ưu đãi freeship nha!",
    ]

    HOMELIFE_ASK_MATERIAL_TEMPLATES: List[str] = [
        "Các bác ơi, em này nhựa ABS cao cấp siêu bền, lau dọn 3s là sạch bóng nhàn tênh. Bác bấm vào giỏ hàng vàng góc trái xem video hướng dẫn và nhận ưu đãi nha!",
        "Bác ơi, chất liệu inox chống rỉ cực chắc chắn, dùng bao nhàn và tiện luôn. Bác ghé giỏ hàng vàng góc trái xem chi tiết thông số và bảo hành nha!",
        "Dạ em này dễ dùng lắm các bác, lắp ráp 30 giây là xong, dọn dẹp nhàn hẳn luôn. Bác bấm vào giỏ hàng góc trái nhận mã freeship nha!",
    ]

    HOMELIFE_COMPLAINT_TEMPLATES: List[str] = [
        "Nam Minh xin lỗi bác vì sự bất tiện này ạ, bác nhắn tin trực tiếp cho shop để bên em kiểm tra và hỗ trợ giải quyết cho bác ngay nhé!",
        "Dạ các bác thông cảm giúp shop nha, bác nhắn tin riêng qua hộp thư để em ưu tiên hỗ trợ xử lý đơn cho bác ngay và luôn ạ!",
        "Các bác ơi Nam Minh thành thật xin lỗi vì sơ suất này ạ, bác nhắn tin ngay cho shop để bên em đổi mới hoặc xử lý thỏa đáng cho bác nhé!",
    ]

    HOMELIFE_OTHER_TEMPLATES: List[str] = [
        "Cảm ơn các bác đã ủng hộ nha, bác bấm vào giỏ hàng vàng góc trái xem thêm mẹo hay và nhận ưu đãi nhé!",
        "Bác ghé giỏ hàng góc trái săn voucher ưu đãi nha, chúc bác và gia đình luôn vui vẻ và việc nhà nhàn tênh!",
        "Dạ cảm ơn bác nhiều nha, bác vào giỏ hàng vàng góc trái tham khảo thêm nhiều món đồ tiện ích nhé!",
    ]

    # --------------------------------------------------------------------------
    # Title Sanitization Filters
    # --------------------------------------------------------------------------
    BANNED_TITLE_PATTERNS: List[str] = [
        r"\bz[\.\s\-_]*a[\.\s\-_]*r[\.\s\-_]*a\b",
        r"\bc[\.\s\-_]*h[\.\s\-_]*a[\.\s\-_]*n[\.\s\-_]*e[\.\s\-_]*l\b",
        r"\bg[\.\s\-_]*u[\.\s\-_]*c[\.\s\-_]*c[\.\s\-_]*i\b",
        r"\bd[\.\s\-_]*i[\.\s\-_]*o[\.\s\-_]*r\b",
        r"\bl[\.\s\-_]*v\b",
        r"\blouis[\.\s\-_]*vuitton\b",
        r"\br[\.\s\-_]*e[\.\s\-_]*p([\.\s\-_]*(1[\:\/\.\-_]1|11))?\b",
        r"\bs[\.\s\-_]*u[\.\s\-_]*p[\.\s\-_]*e[\.\s\-_]*r[\.\s\-_]*f[\.\s\-_]*a[\.\s\-_]*k[\.\s\-_]*e\b",
        r"\bf[\.\s\-_]*a[\.\s\-_]*k[\.\s\-_]*e[\.\s\-_]*(1[\:\/\.\-_]1|1)?\b",
        r"\bl[\.\s\-_]*i[\.\s\-_]*k[\.\s\-_]*e[\.\s\-_]*a[\.\s\-_]*u[\.\s\-_]*t[\.\s\-_]*h\b",
        r"\bt[\.\s\-_]*u[\.\s\-_]*[oồ][\.\s\-_]*n[\.\s\-_]*a[\.\s\-_]*u[\.\s\-_]*t[\.\s\-_]*h\b",
        r"\btốt[\s_\-\.]+nhất[\s_\-\.]+thị[\s_\-\.]+trường\b",
        r"\bsố[\s_\-\.]+1[\s_\-\.]+(thế[\s_\-\.]+giới|việt[\s_\-\.]+nam)\b",
        r"\bvĩnh[\s_\-\.]+viễn[\s_\-\.]+(không|ko|khong)[\s_\-\.]+hỏng\b",
        r"\b100[\s_\-\.]*%[\s_\-\.]*(không|ko|khong)[\s_\-\.]+bao[\s_\-\.]+giờ[\s_\-\.]+hỏng\b",
    ]

    def __init__(self, llm_client: Any = None) -> None:
        self.llm_client = llm_client
        self._init_intent_patterns()

    def _init_intent_patterns(self) -> None:
        """Precompile regex patterns for performance, homograph safety, and thread safety."""
        # 1. Complaint Patterns (Highest priority)
        raw_complaints = [
            r"\b(giao|ship)\s*(chậm|lâu|trễ|muộn)\b|\b(lâu|chậm)\s*(quá|qua|wa|ghê|thế|kinh)\b",
            r"\b(đợi|chờ)\s*(lâu|mãi)\b|\b(chưa|mãi chưa|sao chưa)\s*(nhận|thấy|giao|tới)\b",
            r"\bchưa\s*nhận\s*(được|dc)\b|\bhủy\s*(đơn|hàng)\b",
            r"\b(lỗi|hỏng|rách|bục chỉ|bung chỉ|bị bung|xước|trầy|vỡ|móp)\b",
            r"\b(chất lượng\s*(kém|tệ)|quá tệ|tệ quá|tệ thật|dở tệ|quá dở|hàng đểu|hàng dỏm|làm ăn chán)\b",
            r"\b(vải|chất|chất vải|hàng|đồ|áo|váy)\s*(xấu|quá xấu|xấu quá|đểu|dỏm|tệ|kém|mỏng tang|mỏng dính)\b",
            r"\b(quá xấu|xấu quá|xấu tệ|xấu thật|như giẻ lau|như giẻ rách|giẻ rách|mỏng tang|mỏng dính)\b",
            r"\b(giá|gia)\s*(quá\s+)?(đắt|chát)\b|\b(đắt|mắc)\s*(quá|qua|wa|thế|kinh|ghê|vãi)\b",
            r"\b(sai|nhầm)\s*(mẫu|màu|size|sz|hàng)\b|\b(giao|gửi)\s*(sai|thiếu|nhầm)\b",
            r"\b(không|ko|k)\s*giống\s*(hình|ảnh|mẫu|video|clip|quảng cáo)\b|\bkhác\s*(hình|ảnh|mẫu)\b",
            r"\b(lừa đảo|lừa tiền|scam|bịp|gian dối|treo đầu dê)\b|\b(shop|sop)\s+lừa\b",
            r"\b(thất vọng|bực mình|ức chế)\b|\b(chặn|block)\s*(tin nhắn|ib|inbox|khách)\b",
            r"\b(đừng|né|tẩy chay)\s*(mua|ra|shop)\b|\b(mất|phí)\s*tiền\s*oan\b",
            r"\b(đổi trả|hoàn tiền|trả hàng|đổi hàng)\b",
        ]
        self._complaint_res = [re.compile(p, re.IGNORECASE) for p in raw_complaints]
        unacc_complaints = []
        for p in raw_complaints:
            unacc_p = remove_accents(p)
            # Homograph guard: in unaccented text, bare 'hong' (from 'hỏng') collides with Southern
            # question particle 'hong' / 'hông' (e.g. 'chất co giãn hong shop', 'đẹp hong').
            # Require defect context for unaccented 'hong'.
            unacc_p = unacc_p.replace(
                r"\b(loi|hong|",
                r"\b(loi|bi hong|hang hong|hong roi|hong hoc|do hong|",
            )
            # Homograph guard: unaccented dat/mac vs wear (mặc -> mac) and order (đặt -> dat).
            unacc_p = unacc_p.replace(
                r"\b(dat|mac)\s*",
                r"\bgia\s*(dat|mac)\s*",
            )
            unacc_complaints.append(unacc_p)
        self._complaint_unacc_res = [
            re.compile(p, re.IGNORECASE) for p in unacc_complaints
        ]

        # 2. Price Patterns
        raw_prices = [
            r"\b(giá|gia)\s*(bao nhiêu|nhiêu|bao tiền|mấy tiền|mấy đồng|thế nào|sao|ntn|bn|bnh|bnhieu|bnhiu|nhiu)\b",
            r"\b(bao nhiêu|bao tiền|hết bao tiền|mấy tiền|mấy đồng)\b",
            r"\b(bao|mấy|hết bao)\s*(tiền|xiền|xèng|củ|lít|k|đồng)\b",
            r"\b(nhiêu xiền|mấy xiền|nhiu xien|may xien)\b",
            r"\b(cho\s+)?(e|em|mình|tui|bác)?\s*(xin|hỏi)\s+giá\b",
            r"\b(inbox|ib|check ib)\s+giá\b",
            r"\brổ\s+(giá|rá)\b",
            r"\bbán\s+(sao|giá sao|thế nào|bao nhiêu|nhiêu)\b",
            r"\b(giá|nhiêu|nhiu|bn|bnh|bnhieu|bnhiu)\s*(\?|\!|\.|\s)*$",
            r"^\s*(giá|nhiêu|nhiu|bao nhiêu|bao tiền|bn|bnh|bnhieu|bnhiu)\s*(\?|\!|\.|\s)*$",
            r"\b(nhiêu|nhiu|bnhiu|bnhieu|bao nhiêu)\s+(ạ|thế|vậy|shop|sop|v|z|hả)\b",
            r"\bbn\s+(thế|vậy|v|z|shop|sop|hả)\b",
        ]
        self._price_res = [re.compile(p, re.IGNORECASE) for p in raw_prices]
        self._price_unacc_res = [
            re.compile(remove_accents(p), re.IGNORECASE) for p in raw_prices
        ]

        # 3. Material & Usage Patterns
        raw_materials = [
            r"\b(size|sz|kích thước|kích cỡ|bảng size)\b",
            r"\b(mặc|mang)\s+(size|sz|vừa|được|dc|đẹp|rộng|chật)\b",
            r"\bvừa\s*(không|ko|k|khum|hong|hơm)\s*(shop|sop|ạ)?\b",
            r"\b(bụng|eo|vòng 1|vòng 2|vòng 3|v1|v2|v3|bắp tay|mông|đùi|ngực|vai)\b",
            r"\b\d+\s*(kg|kí|ký|cân)\b|\b(1m\d{2}|m\d{2})\b|\b(cao|nặng)\s+\d+\b|\b\d+\s*cm\b",
            r"\b(form|phom|dáng)\b|\b(chiết eo|tôn dáng|hack dáng|che bụng|giấu bụng|giấu mỡ)\b",
            r"\b(dài|ngắn)\s*(bao nhiêu|tới đâu|đến đâu|không|k|ko|khum)?\b",
            r"\b(chất|chất liệu|chất vải|vải)\b",
            r"\b(đũi|cotton|voan|lụa|len|thun|kaki|jean)\b",
            r"\b(co giãn|co dãn|đàn hồi|xù lông|nhăn|lộ nội y|2 lớp|lót trong)\b",
            r"\b(giặt máy|giặt tay|giặt)\b",
            r"\b(cách dùng|dùng sao|dùng thế nào|sử dụng|hướng dẫn)\b",
            r"\b(lắp|lắp ráp|lắp đặt|cách lắp)\b",
            r"\b(dùng pin|pin sạc|sạc điện|cắm điện|công suất|dung tích)\b",
            r"\b(chống dính|chịu lực|chịu nhiệt|bền không|dễ dùng|dễ lau)\b",
            r"\b(lau được|hút được|rửa được|vệ sinh|cách vệ sinh)\b",
        ]
        self._material_res = [re.compile(p, re.IGNORECASE) for p in raw_materials]
        self._material_unacc_res = [
            re.compile(remove_accents(p), re.IGNORECASE) for p in raw_materials
        ]

        # False-Positive Disqualification Guards for Price
        self._re_false_price = re.compile(
            r"\b(giá như|đánh giá|giá rẻ|giá tốt|giá hợp lý|đáng tiền|đáng đồng tiền|giá cả phải chăng)\b",
            re.IGNORECASE,
        )
        self._re_product_price = re.compile(
            r"\b(giá treo|giá đỡ|giá sách|giá để đồ|giá úp bát)\b",
            re.IGNORECASE,
        )
        self._re_explicit_q = re.compile(
            r"\b(bao nhiêu|bao tiền|mấy tiền|mấy đồng|nhiêu|nhiu|bn|bnh|bnhieu|bnhiu)\b",
            re.IGNORECASE,
        )

    def classify_intent(self, comment_text: str) -> CommentIntent:
        """Classify comment text into one of four CommentIntent categories.

        Evaluates comments with robust Vietnamese normalization, unaccented fallback,
        homograph collision protection, and strict precedence ordering:
        COMPLAINT > ASK_PRICE > ASK_MATERIAL_USAGE > OTHER.
        """
        if not comment_text or not isinstance(comment_text, str) or not comment_text.strip():
            return CommentIntent.OTHER

        raw_lower = unicodedata.normalize("NFC", comment_text).lower().strip()
        unacc = remove_accents(raw_lower)

        # 1. Check COMPLAINT first (Highest priority to protect customer experience)
        for r, ru in zip(self._complaint_res, self._complaint_unacc_res):
            if r.search(raw_lower) or ru.search(unacc):
                return CommentIntent.COMPLAINT

        # 2. Check Price Disqualification Guards
        price_disqualified = False
        if self._re_false_price.search(raw_lower) or self._re_false_price.search(unacc):
            if not (self._re_explicit_q.search(raw_lower) or self._re_explicit_q.search(unacc)):
                price_disqualified = True
        elif self._re_product_price.search(raw_lower) or self._re_product_price.search(unacc):
            if not (self._re_explicit_q.search(raw_lower) or self._re_explicit_q.search(unacc)):
                price_disqualified = True

        # 3. Check ASK_PRICE
        if not price_disqualified:
            for r, ru in zip(self._price_res, self._price_unacc_res):
                if r.search(raw_lower) or ru.search(unacc):
                    return CommentIntent.ASK_PRICE

        # 4. Check ASK_MATERIAL_USAGE
        for r, ru in zip(self._material_res, self._material_unacc_res):
            if r.search(raw_lower) or ru.search(unacc):
                return CommentIntent.ASK_MATERIAL_USAGE

        # 5. Default Fallthrough
        return CommentIntent.OTHER

    def _sanitize_title(self, title: str) -> str:
        """Strips trademark counterfeits and policy-violating buzzwords."""
        if not title:
            return "em này"
        cleaned = title
        for pattern in self.BANNED_TITLE_PATTERNS:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned if cleaned else "em này"

    def _resolve_persona(
        self,
        persona: Optional[Union[Dict[str, Any], str]],
        product_meta: Dict[str, Any],
    ) -> str:
        """Resolves persona to 'nam_minh' or 'hoai_my'."""
        p_name = ""
        if isinstance(persona, str):
            p_name = persona.lower().strip()
        elif isinstance(persona, dict):
            p_name = str(
                persona.get("name")
                or persona.get("niche_id")
                or persona.get("tone")
                or ""
            ).lower()

        niche_id = str(product_meta.get("niche_id") or "").lower()
        title = str(product_meta.get("title") or "").lower()

        if "nam_minh" in p_name or "gia_dung" in p_name or niche_id == "do_gia_dung":
            return "nam_minh"

        homelife_keywords = ["lau nhà", "nồi", "bếp", "gia dụng", "chổi", "hút bụi", "thông minh"]
        if any(k in title for k in homelife_keywords):
            return "nam_minh"

        return "hoai_my"

    def _format_price(self, product_meta: Dict[str, Any]) -> str:
        """Formats price into Vietnamese currency representation."""
        raw_price = (
            product_meta.get("price")
            or product_meta.get("price_vnd")
            or 189000
        )
        try:
            val = int(raw_price)
            return f"{val:,}đ"
        except (ValueError, TypeError):
            return "189,000đ"

    def generate_reply(
        self,
        comment_text: str,
        product_meta: Optional[Dict[str, Any]] = None,
        persona: Optional[Union[Dict[str, Any], str]] = None,
    ) -> str:
        """Generates authentic KOC reply directing viewers to the yellow cart."""
        meta = product_meta or {}
        intent = self.classify_intent(comment_text)
        persona_name = self._resolve_persona(persona, meta)

        title = self._sanitize_title(str(meta.get("title") or "em này"))
        price_str = self._format_price(meta)

        # 1. Attempt LLM generation if client is available
        if self.llm_client is not None:
            try:
                prompt = (
                    f"Bạn là KOC {'Nam Minh (đồ gia dụng)' if persona_name == 'nam_minh' else 'Hoài My (thời trang nữ)'}.\n"
                    f"Hãy trả lời bình luận sau của khách hàng trên TikTok:\n"
                    f"Bình luận: '{comment_text}'\n"
                    f"Sản phẩm: '{title}', Giá: '{price_str}', Ý định: '{intent.value}'.\n"
                    f"Quy tắc: 1-2 câu thân mật, không dùng từ ngữ bot AI rập khuôn, điều hướng giỏ hàng vàng góc trái."
                )
                raw_llm_reply = self.llm_client.generate(prompt)
                if isinstance(raw_llm_reply, str):
                    candidate_reply = raw_llm_reply.strip().strip('"').strip("'")
                    if ToneValidator.validate(candidate_reply):
                        return candidate_reply
            except Exception as e:
                logger.warning("LLM comment generation failed: %s; falling back to templates", e)

        # 2. Pre-certified Template Rotation
        seed = int(hashlib.md5((comment_text + title).encode("utf-8")).hexdigest(), 16)

        if persona_name == "nam_minh":
            if intent == CommentIntent.ASK_PRICE:
                bank = self.HOMELIFE_ASK_PRICE_TEMPLATES
            elif intent == CommentIntent.ASK_MATERIAL_USAGE:
                bank = self.HOMELIFE_ASK_MATERIAL_TEMPLATES
            elif intent == CommentIntent.COMPLAINT:
                bank = self.HOMELIFE_COMPLAINT_TEMPLATES
            else:
                bank = self.HOMELIFE_OTHER_TEMPLATES
        else:
            if intent == CommentIntent.ASK_PRICE:
                bank = self.FASHION_ASK_PRICE_TEMPLATES
            elif intent == CommentIntent.ASK_MATERIAL_USAGE:
                bank = self.FASHION_ASK_MATERIAL_TEMPLATES
            elif intent == CommentIntent.COMPLAINT:
                bank = self.FASHION_COMPLAINT_TEMPLATES
            else:
                bank = self.FASHION_OTHER_TEMPLATES

        chosen_template = bank[seed % len(bank)]
        reply = chosen_template.format(title=title, price_str=price_str)

        # 3. Final Tone Guarantee & Fallback Safety Guard
        if not ToneValidator.validate(reply):
            logger.error(
                "Generated reply failed ToneValidator: '%s'. Triggering emergency fallback.",
                reply,
            )
            if persona_name == "nam_minh":
                if intent == CommentIntent.COMPLAINT:
                    reply = (
                        "Nam Minh xin lỗi bác vì sự bất tiện này ạ, bác nhắn tin trực tiếp cho shop "
                        "để bên em kiểm tra và hỗ trợ giải quyết cho bác ngay nhé!"
                    )
                else:
                    reply = (
                        "Các bác ơi, em này đang sale cực hời ở giỏ hàng vàng góc trái màn hình, "
                        "bác bấm vào nhận mã freeship nha!"
                    )
            else:
                if intent == CommentIntent.COMPLAINT:
                    reply = (
                        "Dạ chị yêu thông cảm giúp shop đợt này đơn nhiều, chị nhắn tin trực tiếp "
                        "để shop hỗ trợ kiểm tra đơn ngay nha!"
                    )
                else:
                    reply = (
                        "Chị em ơi, em này đang có giá ưu đãi ở giỏ hàng vàng góc trái nè, "
                        "chị bấm vào nhận mã freeship nha!"
                    )

        return reply
