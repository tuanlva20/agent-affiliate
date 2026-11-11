"""AMAS v1.4.0 — Natural KOC Script Generator Service (Feature F15).

Generates authentic Vietnamese KOC video scripts complying with ToneValidator,
featuring 3-stage formulas: 3s Hook, Problem/Solution Body with honest caveats,
and Yellow Cart CTA navigation.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Union

from src.core.tone_validator import ToneValidator

logger = logging.getLogger("amas.services.script_generator")


@dataclass
class KOCScriptResult:
    """Structured KOC video script result adhering to F15 contract."""

    hook_3s: str
    body: str
    cta_yellow_cart: str
    caption: str
    full_voiceover: str
    persona: str = "hoai_my"
    voice_id: str = "vi-VN-HoaiMyNeural"
    estimated_duration_sec: float = 35.0
    generation_mode: str = "offline_template"

    def __getitem__(self, item: str) -> Any:
        """Enables dictionary-style indexing for backwards-compatibility with contracts."""
        return getattr(self, item)

    def __contains__(self, item: str) -> bool:
        """Enables 'in script' checks for contracts."""
        return hasattr(self, item)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to standard Python dictionary."""
        return {
            "hook_3s": self.hook_3s,
            "body": self.body,
            "cta_yellow_cart": self.cta_yellow_cart,
            "caption": self.caption,
            "full_voiceover": self.full_voiceover,
            "persona": self.persona,
            "voice_id": self.voice_id,
            "estimated_duration_sec": self.estimated_duration_sec,
            "generation_mode": self.generation_mode,
        }


class ScriptGenerator:
    """Service generating authentic Vietnamese KOC video scripts complying with ToneValidator."""

    # Rotating template banks for Fashion (Hoài My - vi-VN-HoaiMyNeural)
    FASHION_HOOKS: List[str] = [
        "Chị em ơi, ai bảo eo to không mặc đẹp được? Nhìn ngay chiếc {clean_title} này!",
        "Mấy bà ơi, bà nào bụng dưới to bơi hết vào đây, chiếc {clean_title} này cứu cánh cực đỉnh!",
        "Team chân ngắn đâu rồi bơi vào đây, chiếc {clean_title} này hack dáng đỉnh chóp luôn nha!",
        "Chị em ơi, mặc chiếc {clean_title} này lên là eo thon gọn hẳn 5 phân không cần nịt bụng luôn!",
    ]

    FASHION_BODIES: List[str] = [
        "Form may chiết eo cao giấu nhẹm mỡ thừa chỉ trong tích tắc, chất vải xịn sò mát rượi đứng form cực kỳ. Đi làm hay đi cà phê cuối tuần cũng tôn dáng hết nấc, mỗi tội chị em nhớ ủi nhẹ trước khi mặc là chuẩn đét luôn.",
        "Chất vải cực mát, form may tôn dáng, che trọn khuyết điểm bụng dưới chỉ sau 1 giây. Đường may tỉ mỉ, mặc lên nhẹ tênh mà giấu mỡ bắp tay đỉnh thực sự. Nhìn ở ngoài xinh xỉu hơn trên hình nhiều nha.",
        "Bà nào hay ngồi văn phòng sợ lộ bụng mỡ thì chiếc này đúng là chân ái. Xếp ly xòe nhẹ che sạch mỡ bụng dưới, tạo cảm giác chân dài miên man. Tui test cả ngày không hề nhăn nhúm hay bí bách gì cả.",
    ]

    FASHION_CTAS: List[str] = [
        "Chị em bấm ngay góc trái màn hình nhận mã freeship và rinh về nhé!",
        "Mấy bà bấm ngay giỏ hàng góc trái săn voucher giảm giá nha, số lượng có hạn đó!",
        "Link tui để sẵn ở giỏ hàng vàng góc trái màn hình nè, nhanh tay kẻo hết size nha chị em!",
    ]

    FASHION_CAPTIONS: List[str] = [
        "{clean_title} tôn dáng cực đỉnh #fashion #xuhuong #thoitrang #koc",
        "{clean_title} hack dáng che khuyết điểm cho chị em #outfit #thoitrangnu #xuhuong",
    ]

    # Rotating template banks for HomeLife (Nam Minh - vi-VN-NamMinhNeural)
    HOMELIFE_HOOKS: List[str] = [
        "Các bác ơi, từ ngày tậu em {clean_title} này việc nhà nhàn hẳn, 3s là nhà sạch bóng!",
        "Bỏ ngay mấy cái giẻ lau cũ đi các bác, dùng em {clean_title} này nhàn tênh!",
        "Các bác ơi, 3 giây sạch bóng kin kít không tốn một giọt mồ hôi, chân ái dọn nhà đây rồi!",
        "Bà nào ngại dọn nhà bơi vào đây, có em {clean_title} này việc nhà nhàn hẳn!",
    ]

    HOMELIFE_BODIES: List[str] = [
        "Cơ chế thông minh tự vắt ráo nước trong một nốt nhạc, lau sạch kin kít vết dầu mỡ cứng đầu mà không cần cúi còng cả lưng. Bác nào nhà có con nhỏ hay nuôi thú cưng thì rinh em này về giải phóng sức lao động cực kỳ nhàn luôn.",
        "Test thực tế cho các bác xem, chỉ cần đẩy nhẹ 3 giây là sàn nhà khô ráo sạch bong kin kít. Không tốn sức, không bẩn tay, khay chứa rác thông minh dễ vệ sinh cực kỳ, mỗi tội lúc mới dùng phải đọc kỹ hướng dẫn lắp một chút thôi.",
        "Từ ngày có em này tui tiết kiệm được nửa tiếng dọn dẹp mỗi ngày. Vết bẩn cứng đầu trên sàn bếp chà nhẹ là sạch bóng, thiết kế gọn gàng dựng góc nhà nhàn tênh.",
    ]

    HOMELIFE_CTAS: List[str] = [
        "Các bác bấm ngay vào giỏ hàng góc trái màn hình nhận mã ưu đãi nha!",
        "Đang có mã giảm giá ở giỏ hàng vàng kìa các bác ơi, bấm góc trái màn hình đặt ngay nhé!",
        "Link mua chính hãng tui ghim ở giỏ hàng góc trái màn hình rồi, các bác bấm vào xem nha!",
    ]

    HOMELIFE_CAPTIONS: List[str] = [
        "{clean_title} giải phóng việc nhà nhàn tênh 3s #dogiadung #giadungthongminh #xuhuong #koc",
        "{clean_title} chân ái cho hội lười dọn dẹp #meovat #giadungtienich #xuhuong",
    ]

    def __init__(self, config: Optional[Any] = None, llm_client: Optional[Any] = None) -> None:
        self.config = config
        self.llm_client = llm_client

    def _normalize_product_meta(self, item: Any) -> Dict[str, Any]:
        """Converts input product representation to standard dictionary."""
        if item is None:
            return {"title": "Sản phẩm xu hướng", "niche_id": "thoi_trang_nu", "price": 0.0}
        if hasattr(item, "to_dict") and callable(getattr(item, "to_dict")):
            return item.to_dict()
        if isinstance(item, dict):
            return dict(item)

        result: Dict[str, Any] = {}
        for attr in [
            "product_id",
            "title",
            "niche_id",
            "price",
            "commission_rate",
            "rating",
            "sales_count",
            "sales_30d",
        ]:
            if hasattr(item, attr):
                result[attr] = getattr(item, attr)
        return result

    def _resolve_persona(
        self,
        persona_param: Optional[Union[Dict[str, Any], str]],
        product_meta: Dict[str, Any],
    ) -> Tuple[str, str]:
        """Resolves persona name ('hoai_my' or 'nam_minh') and voice id."""
        p_name = ""
        if isinstance(persona_param, str):
            p_name = persona_param.lower().strip()
        elif isinstance(persona_param, dict):
            p_name = str(
                persona_param.get("name")
                or persona_param.get("persona")
                or persona_param.get("tone")
                or ""
            ).lower().strip()

        niche_id = str(product_meta.get("niche_id") or "").lower().strip()
        title = str(product_meta.get("title") or "").lower().strip()

        if p_name in ("nam_minh", "homelife", "do_gia_dung"):
            return "nam_minh", "vi-VN-NamMinhNeural"
        if p_name in ("hoai_my", "fashion", "thoi_trang_nu"):
            return "hoai_my", "vi-VN-HoaiMyNeural"

        # Check niche_id
        if niche_id == "do_gia_dung":
            return "nam_minh", "vi-VN-NamMinhNeural"
        if niche_id == "thoi_trang_nu":
            return "hoai_my", "vi-VN-HoaiMyNeural"

        # Heuristic keywords in product title
        home_keywords = [
            "lau nhà", "nồi", "bếp", "máy", "thông minh", "gia dụng",
            "chổi", "kệ", "dao", "rửa", "hút bụi", "thớt",
        ]
        if any(k in title for k in home_keywords):
            return "nam_minh", "vi-VN-NamMinhNeural"

        return "hoai_my", "vi-VN-HoaiMyNeural"

    BANNED_TITLE_PATTERNS: List[str] = [
        # Trademarks & counterfeits with optional dots/separators
        r"\bz[\.\s\-_]*a[\.\s\-_]*r[\.\s\-_]*a\b",
        r"\bc[\.\s\-_]*h[\.\s\-_]*a[\.\s\-_]*n[\.\s\-_]*e[\.\s\-_]*l\b",
        r"\bg[\.\s\-_]*u[\.\s\-_]*c[\.\s\-_]*c[\.\s\-_]*i\b",
        r"\bd[\.\s\-_]*i[\.\s\-_]*o[\.\s\-_]*r\b",
        r"\bl[\.\s\-_]*v\b",
        r"\blouis[\.\s\-_]*vuitton\b",
        r"\bherm[eè]s\b",
        r"\bn[\.\s\-_]*i[\.\s\-_]*k[\.\s\-_]*e\b",
        r"\ba[\.\s\-_]*d[\.\s\-_]*i[\.\s\-_]*d[\.\s\-_]*a[\.\s\-_]*s\b",
        r"\br[\.\s\-_]*e[\.\s\-_]*p([\.\s\-_]*(1[\:\/\.\-_]1|11))?\b",
        r"\bs[\.\s\-_]*u[\.\s\-_]*p[\.\s\-_]*e[\.\s\-_]*r[\.\s\-_]*f[\.\s\-_]*a[\.\s\-_]*k[\.\s\-_]*e\b",
        r"\bf[\.\s\-_]*a[\.\s\-_]*k[\.\s\-_]*e[\.\s\-_]*(1[\:\/\.\-_]1|1)?\b",
        r"(?<!mon )(?<!món )(?<!thit )(?<!thịt )\b(nhai|nhái)\b",
        r"\bl[\.\s\-_]*i[\.\s\-_]*k[\.\s\-_]*e[\.\s\-_]*a[\.\s\-_]*u[\.\s\-_]*t[\.\s\-_]*h\b",
        r"\bt[\.\s\-_]*u[\.\s\-_]*[oồ][\.\s\-_]*n[\.\s\-_]*a[\.\s\-_]*u[\.\s\-_]*t[\.\s\-_]*h\b",
        r"\b(hàng|hang)[\.\s\-_]*(tuồn|tuon)\b",
        r"\bvnxk[\.\s\-_]*(chuẩn|chuan)[\.\s\-_]*auth\b",

        # Exaggerated & medical claims
        r"\btrị[\.\s\-_]*dứt[\.\s\-_]*điểm([\.\s\-_]*100[\.\s\-_]*%)?",
        r"\bchữa[\.\s\-_]*khỏi([\.\s\-_]*hoàn[\.\s\-_]*toàn)?\b",
        r"\bchữa[\.\s\-_]*dứt[\.\s\-_]*điểm\b",
        r"\bcam[\.\s\-_]*kết[\.\s\-_]*chữa[\.\s\-_]*khỏi\b",
        r"\b100[\.\s\-_]*%[\.\s\-_]*(không|ko|khong)[\.\s\-_]*bao[\.\s\-_]*giờ[\.\s\-_]*hỏng\b",
        r"\bvĩnh[\.\s\-_]*viễn[\.\s\-_]*(không|ko|khong)[\.\s\-_]*bao[\.\s\-_]*giờ[\.\s\-_]*hỏng\b",
        r"\bvĩnh[\.\s\-_]*viễn[\.\s\-_]*(không|ko|khong)[\.\s\-_]*hỏng\b",
        r"\bvĩnh[\.\s\-_]*viễn[\.\s\-_]*(không|ko|khong)[\.\s\-_]*bám[\.\s\-_]*bẩn\b",
        r"\bvĩnh[\.\s\-_]*viễn[\.\s\-_]*(không|ko|khong)[\.\s\-_]*(rỉ|gỉ)[\.\s\-_]*sét\b",
        r"\bthần[\.\s\-_]*dược\b",
        r"\bđặc[\.\s\-_]*trị\b",

        # Robotic clichés (longer patterns ordered first)
        r"\bchào\s+mừng\s+(bạn|quý\s+vị|quý\s+khách|mọi\s+người)\s+đến\s+với\b",
        r"\b(dạ\s+)?(em\s+)?(xin\s+|kính\s+)?chào\s+(mừng\s+)?quý\s+khách\b",
        r"\bkính\s*chào\s*quý\s*khách\b",
        r"\bsản\s*phẩm\s*hoàn\s*hảo\b",
        r"\bđáp\s*ứng\s*mọi\s*nhu\s*cầu(\s*của\s*bạn)?\b",
        r"\bhãy\s*nhanh\s*tay\s*sở\s*hữu\b",
        r"\bsự\s*lựa\s*chọn\s*hoàn\s*hảo\b",
        r"\brất\s*hân\s*hạnh\s*được\s*phục\s*vụ\b",
    ]

    def _sanitize_title(self, raw_title: str) -> str:
        """Removes counterfeit marks, exaggerated claims, and robotic clichés from product title."""
        title = str(raw_title or "").strip()
        for pattern in self.BANNED_TITLE_PATTERNS:
            title = re.sub(pattern, "", title, flags=re.IGNORECASE)

        # Collapse whitespace and dangling punctuation
        title = re.sub(r"\s+", " ", title).strip(" -_:,.")
        return title or "sản phẩm hot"

    def _generate_from_templates(
        self,
        clean_title: str,
        persona: str,
        voice_id: str,
    ) -> KOCScriptResult:
        """Generates script using pre-certified offline templates guaranteed to satisfy ToneValidator."""
        # Use stable hash of title to deterministically select rotating templates
        hash_val = int(hashlib.md5(clean_title.encode("utf-8")).hexdigest(), 16)

        if persona == "nam_minh":
            hook = self.HOMELIFE_HOOKS[hash_val % len(self.HOMELIFE_HOOKS)].format(clean_title=clean_title)
            body = self.HOMELIFE_BODIES[hash_val % len(self.HOMELIFE_BODIES)]
            cta = self.HOMELIFE_CTAS[hash_val % len(self.HOMELIFE_CTAS)]
            caption = self.HOMELIFE_CAPTIONS[hash_val % len(self.HOMELIFE_CAPTIONS)].format(clean_title=clean_title)
        else:
            hook = self.FASHION_HOOKS[hash_val % len(self.FASHION_HOOKS)].format(clean_title=clean_title)
            body = self.FASHION_BODIES[hash_val % len(self.FASHION_BODIES)]
            cta = self.FASHION_CTAS[hash_val % len(self.FASHION_CTAS)]
            caption = self.FASHION_CAPTIONS[hash_val % len(self.FASHION_CAPTIONS)].format(clean_title=clean_title)

        full_voiceover = f"{hook} {body} {cta}"
        word_count = len(full_voiceover.split())
        est_duration = max(15.0, round(word_count / 3.0, 1))

        return KOCScriptResult(
            hook_3s=hook,
            body=body,
            cta_yellow_cart=cta,
            caption=caption,
            full_voiceover=full_voiceover,
            persona=persona,
            voice_id=voice_id,
            estimated_duration_sec=est_duration,
            generation_mode="offline_template",
        )

    def generate_script(
        self,
        product_meta: Any = None,
        persona: Optional[Union[Dict[str, Any], str]] = None,
    ) -> KOCScriptResult:
        """Generates a natural Vietnamese KOC video script adhering to ToneValidator."""
        meta = self._normalize_product_meta(product_meta)
        persona_name, voice_id = self._resolve_persona(persona, meta)

        raw_title = str(meta.get("title") or "Sản phẩm hot")
        clean_title = self._sanitize_title(raw_title)

        # 1. Attempt LLM generation if client is available
        if self.llm_client is not None:
            try:
                prompt = (
                    f"Generate KOC script for product '{clean_title}' under persona '{persona_name}'."
                )
                llm_output = self.llm_client.generate(prompt)
                data = json.loads(llm_output) if isinstance(llm_output, str) else llm_output
                hook = data.get("hook_3s", "")
                body = data.get("body", "")
                cta = data.get("cta_yellow_cart", "")
                caption = data.get("caption", f"{clean_title} #xuhuong")
                full_voiceover = f"{hook} {body} {cta}".strip()

                # Validate with ToneValidator
                if (
                    ToneValidator.validate(full_voiceover)
                    and ToneValidator.has_koc_markers(full_voiceover)
                ):
                    word_count = len(full_voiceover.split())
                    return KOCScriptResult(
                        hook_3s=hook,
                        body=body,
                        cta_yellow_cart=cta,
                        caption=caption,
                        full_voiceover=full_voiceover,
                        persona=persona_name,
                        voice_id=voice_id,
                        estimated_duration_sec=max(15.0, round(word_count / 3.0, 1)),
                        generation_mode="llm",
                    )
                logger.warning("LLM generated text failed ToneValidator; falling back to offline template")
            except Exception as e:
                logger.warning(f"LLM generation failed: {e}; falling back to offline template")

        # 2. Pre-certified offline template engine
        result = self._generate_from_templates(clean_title, persona_name, voice_id)

        # 3. Final safety assertion
        if not ToneValidator.validate(result.full_voiceover):
            # Double sanitize if an edge case occurred
            logger.error("Template failed ToneValidator unexpectedly; applying emergency fallback")
            if persona_name == "nam_minh":
                result.hook_3s = "Các bác ơi, từ ngày tậu em này việc nhà nhàn hẳn, 3s là nhà sạch bóng!"
                result.body = "Cơ chế thông minh lau sạch kin kít không tốn một giọt mồ hôi, giải phóng sức lao động cực kỳ nhàn luôn."
                result.cta_yellow_cart = "Các bác bấm ngay vào giỏ hàng góc trái màn hình nhận mã ưu đãi nha!"
                result.voice_id = "vi-VN-NamMinhNeural"
                result.caption = "Giải phóng việc nhà nhàn tênh 3s sạch bóng #dogiadung #giadungthongminh #xuhuong #koc"
            else:
                result.hook_3s = "Chị em ơi, nhìn ngay em này hack dáng cực đỉnh!"
                result.body = "Chất vải mát, form may giấu nhẹm mỡ thừa tôn dáng cực kỳ."
                result.cta_yellow_cart = "Chị em bấm ngay vào giỏ hàng góc trái màn hình nhận mã freeship nha!"
                result.voice_id = "vi-VN-HoaiMyNeural"
                result.caption = "Tôn dáng cực đỉnh hack dáng che khuyết điểm cho chị em #outfit #thoitrangnu #xuhuong"
            result.persona = persona_name
            result.full_voiceover = f"{result.hook_3s} {result.body} {result.cta_yellow_cart}"
            word_count = len(result.full_voiceover.split())
            result.estimated_duration_sec = max(15.0, round(word_count / 3.0, 1))

        return result
