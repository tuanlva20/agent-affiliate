"""AMAS v1.4.0 — Anti-Robotic, Policy & Brand Tone Validator.

Kiểm tra và ngăn chặn:
1. Mùi bot, văn phong máy móc rập khuôn AI (Robotic Clichés).
2. Từ khóa nhãn hiệu vi phạm sở hữu trí tuệ / hàng nhái (Counterfeit Brands).
3. Cam kết y tế / quảng cáo quá đà vi phạm chính sách TikTok Shop (Exaggerated Claims).
4. Xác minh sự hiện diện của các dấu hiệu KOC tự nhiên (KOC Markers).
"""

from __future__ import annotations

import re
import unicodedata
from typing import List, Tuple


class ToneValidator:
    """Bộ kiểm tra tuân thủ giọng điệu KOC và chính sách TikTok Shop."""

    # Nhóm 1: Mẫu câu máy móc / Mùi bot AI (Banned Robotic Clichés)
    ROBOTIC_PATTERNS: List[Tuple[str, str]] = [
        (r"\b(dạ\s+)?(em\s+)?(xin\s+|kính\s+)?chào\s+(mừng\s+)?quý\s+khách\b", "chào quý khách"),
        (r"\bchào\s+mừng\s+(bạn|quý\s+vị|mọi\s+người)\s+đến\s+với\b", "chào mừng bạn đến với"),
        (r"\bkính chào quý khách\b", "kính chào quý khách"),
        (r"\bkính thưa quý vị\b", "kính thưa quý vị"),
        (r"\b(sau|dưới)\s+đây\s+là\s+(danh\s+sách|một\s+số\s+gợi\s+ý|gợi\s+ý)\b", "sau/dưới đây là danh sách/gợi ý"),
        (r"\brất hân hạnh được phục vụ\b", "rất hân hạnh được phục vụ"),
        (r"\btôi là\s+(một\s+)?trợ lý\s+(ảo|ai|thông minh|ngôn ngữ)\b", "tôi là trợ lý ảo/AI"),
        (r"\btôi là (ai|chatgpt|mô hình ngôn ngữ)\b", "tôi là AI/mô hình ngôn ngữ"),
        (r"\btôi là một mô hình ngôn ngữ\b", "tôi là một mô hình ngôn ngữ"),
        (r"\b(như|là)\s+một\s+(trợ lý|mô hình)\s+(ảo|ai|ngôn ngữ)\b", "như một trợ lý/mô hình AI"),
        (r"\bhy vọng\s+(thông tin\s+này\s+)?hữu ích\s+(cho\s+bạn|với\s+bạn)?\b", "hy vọng thông tin hữu ích"),
        (r"\bsản phẩm này rất tốt và tiện ích\b", "sản phẩm này rất tốt và tiện ích"),
        (r"\bsản phẩm (này )?rất tuyệt vời\b", "sản phẩm rất tuyệt vời"),
        (r"\bđáp ứng mọi nhu cầu( của bạn)?\b", "đáp ứng mọi nhu cầu"),
        (r"\bsự lựa chọn hoàn hảo\b", "sự lựa chọn hoàn hảo"),
        (r"\bgiải pháp hoàn hảo\b", "giải pháp hoàn hảo"),
        (r"\bđừng bỏ lỡ cơ hội này\b", "đừng bỏ lỡ cơ hội này"),
        (r"\bhãy nhanh tay sở hữu\b", "hãy nhanh tay sở hữu"),
        (r"\bsở hữu ngay hôm nay\b", "sở hữu ngay hôm nay"),
        (r"\bcảm ơn quý khách đã tin tưởng\b", "cảm ơn quý khách đã tin tưởng"),
        (r"\bchúc quý khách một ngày tốt lành\b", "chúc quý khách một ngày tốt lành"),
        (r"\bmọi thắc mắc xin vui lòng liên hệ\b", "mọi thắc mắc xin vui lòng liên hệ"),
        (r"\btrân trọng cảm ơn\b", "trân trọng cảm ơn"),
    ]

    # Nhóm 2: Từ khóa nhãn hiệu hàng nhái / vi phạm bản quyền (Counterfeit Keywords)
    COUNTERFEIT_PATTERNS: List[Tuple[str, str]] = [
        (r"(?:\b|^|\s)r[\.\s\-_]*e[\.\s\-_]*p[\.\s\-_]*(?:1[\.\s\-_]*[:\/\-\.][\.\s\-_]*1|1[\.\s\-_]*1)(?:\b|$|\s)", "rep 1:1"),
        (r"(?:\b|^|\s)s[\.\s\-_]*u[\.\s\-_]*p[\.\s\-_]*e[\.\s\-_]*r[\.\s\-_]*f[\.\s\-_]*a[\.\s\-_]*k[\.\s\-_]*e(?:\b|$|\s)", "super fake"),
        (r"\b(hàng|hang|áo|quần|giày|dép|túi|ví|đầm|bản)?\s*fake(\s*1(?:\s*[:\/\-\.]\s*1)?)?\b", "fake"),
        (r"\b(hàng|hang)\s*(fake|rep|f1)\b", "hàng fake/rep/f1"),
        (r"(?<!mon )(?<!món )(?<!thit )(?<!thịt )\b(nhai|nhái)\b", "nhái"),
        (r"\b(like|chuan|chuẩn|tuon|tuồn)[\.\s\-_]*auth\b", "like/chuẩn/tuồn auth"),
        (r"\b(hàng|hang)[\.\s\-_]*(tuồn|tuon)\b", "hàng tuồn"),
        (r"\bvnxk[\.\s\-_]*(chuẩn|chuan)[\.\s\-_]*auth\b", "vnxk chuẩn auth"),
        (r"\bcheck\s*code\s*auth\b", "check code auth"),
        (r"\bzara\b", "Zara"),
        (r"\bchanel\b", "Chanel"),
        (r"\bgucci\b", "Gucci"),
        (r"\bdior\b", "Dior"),
        (r"\blouis\s*vuitton\b", "Louis Vuitton"),
        (r"(?:\b|^|\s)lv(?:\b|$|\s)", "LV"),
        (r"\bherm[eè]s\b", "Hermes"),
        (r"\bprada\b", "Prada"),
        (r"\bbalenciaga\b", "Balenciaga"),
        (r"\brolex\b", "Rolex"),
        (r"\bnike\b", "Nike"),
        (r"\badidas\b", "Adidas"),
    ]

    # Nhóm 3: Cam kết y tế / quảng cáo quá đà (Exaggerated Claims)
    EXAGGERATED_PATTERNS: List[Tuple[str, str]] = [
        (r"\btrị[\s_\-\.]+dứt[\s_\-\.]+điểm([\s_\-\.]+100[\s_\-\.]*%)?\b", "trị dứt điểm 100%"),
        (r"\bchữa[\s_\-\.]+dứt[\s_\-\.]+điểm\b", "chữa dứt điểm"),
        (r"\bchữa[\s_\-\.]+khỏi\b", "chữa khỏi"),
        (r"\bcam[\s_\-\.]+kết[\s_\-\.]+chữa[\s_\-\.]+khỏi\b", "cam kết chữa khỏi"),
        (r"\b100[\s_\-\.]*%[\s_\-\.]+hết[\s_\-\.]+bệnh\b", "100% hết bệnh"),
        (r"\bhết[\s_\-\.]+bệnh\b", "hết bệnh"),
        (r"\bđặc[\s_\-\.]+trị([\s_\-\.]+(dứt[\s_\-\.]+điểm|tận[\s_\-\.]+gốc))?\b", "đặc trị"),
        (r"\bcam[\s_\-\.]+kết[\s_\-\.]+khỏi([\s_\-\.]+bệnh)?([\s_\-\.]+100[\s_\-\.]*%)?\b", "cam kết khỏi bệnh 100%"),
        (r"\bkhỏi[\s_\-\.]+hẳn[\s_\-\.]+sau\b", "khỏi hẳn sau"),
        (r"\bthần[\s_\-\.]+dược\b", "thần dược"),
        (r"\bthuốc[\s_\-\.]+trị\b", "thuốc trị"),
        (r"\bvĩnh[\s_\-\.]+viễn[\s_\-\.]+(không|ko|khong)[\s_\-\.]+bám[\s_\-\.]+bẩn\b", "vĩnh viễn không bám bẩn"),
        (r"\bvĩnh[\s_\-\.]+viễn[\s_\-\.]+(không|ko|khong)[\s_\-\.]+hỏng\b", "vĩnh viễn không hỏng"),
        (r"\b100[\s_\-\.]*%[\s_\-\.]*(không|ko|khong)[\s_\-\.]+bao[\s_\-\.]+giờ[\s_\-\.]+hỏng\b", "100% không bao giờ hỏng"),
        (r"\bvĩnh[\s_\-\.]+viễn[\s_\-\.]+(không|ko|khong)[\s_\-\.]+(rỉ|gỉ)[\s_\-\.]+sét\b", "vĩnh viễn không rỉ sét"),
        (r"\bbảo[\s_\-\.]+hành[\s_\-\.]+trọn[\s_\-\.]+đời[\s_\-\.]+(không|ko|khong)[\s_\-\.]+hỏng\b", "bảo hành trọn đời không hỏng"),
        (r"\btốt[\s_\-\.]+nhất[\s_\-\.]+thị[\s_\-\.]+trường\b", "tốt nhất thị trường"),
        (r"\bsố[\s_\-\.]+1[\s_\-\.]+(thế[\s_\-\.]+giới|việt[\s_\-\.]+nam)\b", "số 1 thế giới/việt nam"),
        (r"\bduy[\s_\-\.]+nhất[\s_\-\.]+trên[\s_\-\.]+thị[\s_\-\.]+trường\b", "duy nhất trên thị trường"),
    ]

    # Nhóm 4: Dấu hiệu văn phong KOC tự nhiên (KOC Markers)
    KOC_MARKER_PATTERNS: List[str] = [
        r"\b(chị em ơi|mấy bà ơi|các bà ơi|bà nào|chị nào|mấy bác ơi|các bác ơi|bà con ơi|team chân ngắn|team bụng mỡ)\b",
        r"\b(nhàn hẳn|nhàn tênh|mê chữ ê kéo dài|chân ái|đỉnh chóp|hack dáng|che khuyết điểm|bụng dưới to|bắp tay to)\b",
        r"\b(giỏ hàng góc trái|góc trái màn hình|bấm ngay góc trái|giỏ hàng vàng|mã freeship|săn sale|săn voucher)\b",
    ]

    @classmethod
    def _normalize(cls, text: str) -> str:
        """Chuẩn hóa Unicode NFC và chữ thường."""
        if not text:
            return ""
        return unicodedata.normalize("NFC", text).lower()

    @classmethod
    def canonicalize_brand_text(cls, text: str) -> str:
        r"""Auxiliary brand de-obfuscation / canonicalization method for trademark checks.

        - Normalizes Unicode NFC and lowercases.
        - Strips accents from brand tokens (e.g. zàra -> zara, chánel -> chanel, gùcci -> gucci).
        - Separates glued rep/fake and numbers (e.g. rep1:1 -> rep 1:1, fake1:1 -> fake 1:1).
        - Removes inter-character punctuation [_\-.\/:] between single characters (e.g. z.a.r.a -> zara, c-h-a-n-e-l -> chanel, l.v -> lv).
        - Collapses spaced single letters into words (e.g. z a r a -> zara, c h a n e l -> chanel).
        - Substitutes common leetspeak characters in latin tokens: 4/@ -> a, 3 -> e, 1/! -> i, 0 -> o, 5/$ -> s.
        """
        if not text:
            return ""
        s = unicodedata.normalize("NFC", text).lower()

        # Strip latin accents / combining diacritical marks
        s_nfd = unicodedata.normalize("NFD", s)
        s_stripped = "".join(c for c in s_nfd if unicodedata.category(c) != "Mn")
        s = unicodedata.normalize("NFC", s_stripped)

        # Separate glued rep/fake from numbers before leetspeak: rep1:1 -> rep 1:1, fake1:1 -> fake 1:1
        s = re.sub(r"\b(rep|fake)(\d)", r"\1 \2", s, flags=re.IGNORECASE)

        # 1. Remove inter-character punctuation [_\-.\/:] between single characters:
        def collapse_punct(m: re.Match) -> str:
            t = m.group(0)
            if re.match(r"^1[:\/\-\.]1$", t):
                return t
            return re.sub(r"[._\-\/:]", "", t)

        s = re.sub(r"(?<![a-z0-9])(?:[a-z0-9][._\-\/:]){1,}[a-z0-9](?![a-z0-9])", collapse_punct, s)

        # 2. Collapse spaced single letters into words:
        def collapse_spaces(m: re.Match) -> str:
            return re.sub(r"\s+", "", m.group(0))

        s = re.sub(r"(?<![a-z0-9])[a-z0-9](?:\s+[a-z0-9])+(?![a-z0-9])", collapse_spaces, s)

        # 3. Leetspeak substitutions on latin tokens:
        words = s.split()
        new_words = []
        for w in words:
            if re.match(r"^1[:\/\-\.]1$", w) or w == "11":
                new_words.append(w)
                continue
            tw = w
            if any(c.isalpha() for c in tw):
                tw = tw.replace("4", "a").replace("@", "a")
                tw = tw.replace("3", "e")
                tw = tw.replace("1", "i")
                tw = re.sub(r"!(?=[a-z0-9])", "i", tw)
                tw = tw.replace("0", "o")
                tw = tw.replace("5", "s").replace("$", "s")
            new_words.append(tw)
        s = " ".join(new_words)

        return s

    @classmethod
    def check_violations(cls, text: str) -> List[str]:
        """Trả về danh sách chi tiết các vi phạm có trong văn bản."""
        if not text or not text.strip():
            return ["EMPTY_TEXT: 'Text cannot be empty or whitespace only'"]

        norm_text = cls._normalize(text)
        canon_brand = cls.canonicalize_brand_text(text)

        # Normalizations for exaggerated claims (slang & punctuation separators)
        norm_slang = re.sub(r"\bko\b", "không", norm_text)
        norm_slang = re.sub(r"\bkhong\b", "không", norm_slang)
        norm_spaces = re.sub(r"[_\-.]", " ", norm_slang)
        norm_spaces = re.sub(r"\s+", " ", norm_spaces)

        violations: List[str] = []

        # Kiểm tra Robotic Clichés
        for pattern, label in cls.ROBOTIC_PATTERNS:
            if re.search(pattern, norm_text, re.IGNORECASE):
                violations.append(f"ROBOTIC_CLICHE: '{label}'")

        # Kiểm tra Counterfeit Keywords (trên cả norm_text và canon_brand)
        for pattern, label in cls.COUNTERFEIT_PATTERNS:
            if re.search(pattern, norm_text, re.IGNORECASE) or (
                canon_brand and re.search(pattern, canon_brand, re.IGNORECASE)
            ):
                violations.append(f"COUNTERFEIT_KEYWORD: '{label}'")

        # Kiểm tra Exaggerated Claims (trên norm_text, norm_slang, và norm_spaces)
        for pattern, label in cls.EXAGGERATED_PATTERNS:
            if (
                re.search(pattern, norm_text, re.IGNORECASE)
                or re.search(pattern, norm_slang, re.IGNORECASE)
                or re.search(pattern, norm_spaces, re.IGNORECASE)
            ):
                violations.append(f"EXAGGERATED_CLAIM: '{label}'")

        return violations

    @classmethod
    def validate(cls, text: str) -> bool:
        """Trả về True nếu văn bản sạch, không chứa bất kỳ vi phạm nào."""
        if not text or not text.strip():
            return False
        return len(cls.check_violations(text)) == 0

    @classmethod
    def has_koc_markers(cls, text: str) -> bool:
        """Kiểm tra văn bản có chứa ít nhất 1 dấu hiệu KOC tự nhiên hay không."""
        if not text or not text.strip():
            return False
        norm_text = cls._normalize(text)
        for pattern in cls.KOC_MARKER_PATTERNS:
            if re.search(pattern, norm_text, re.IGNORECASE):
                return True
        return False
