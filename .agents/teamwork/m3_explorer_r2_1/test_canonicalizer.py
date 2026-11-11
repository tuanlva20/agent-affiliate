#!/usr/bin/env python3
"""Experimental Brand & Counterfeit Canonicalizer Prototype.

Tests canonicalization on:
1. 30 Adversarial Challenge Cases from m3_fashion_adversarial_harness.py
2. 30+ Genuine Vietnamese Fashion Titles (False-positive safety check)
3. 20+ HomeLife / General Titles
"""

import re
import unicodedata
from typing import List, Tuple

# Banned foreign brand targets
BRAND_TOKENS = [
    "zara", "chanel", "gucci", "dior", "louis vuitton", "lv",
    "hermes", "prada", "balenciaga", "rolex", "nike", "adidas",
]

# Leetspeak translation table
LEET_MAP = str.maketrans({
    "4": "a",
    "@": "a",
    "3": "e",
    "1": "i",
    "!": "i",
    "0": "o",
    "5": "s",
    "$": "s",
})

def strip_accents(text: str) -> str:
    """Strip accents from latin characters (NFD decomposition)."""
    nfd = unicodedata.normalize("NFD", text)
    # Remove combining diacritical marks
    stripped = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    # Replace đ/Đ with d/D if needed, but for brands d is already d
    return stripped.replace("đ", "d").replace("Đ", "D")

def deobfuscate_brand_text(text: str) -> str:
    """Generate canonicalized text representation for brand & counterfeit detection.
    
    Steps:
    1. Lowercase and Unicode NFC normalization.
    2. Normalize inter-character punctuation / separators within tokens:
       e.g., 'z.a.r.a' -> 'zara', 'c-h-a-n-e-l' -> 'chanel', 'g_u_c_c_i' -> 'gucci',
             'l.v' -> 'lv', 'r.e.p' -> 'rep', 's.u.p.e.r' -> 'super', 'f.a.k.e' -> 'fake'.
    3. Collapse spaced single characters into words:
       e.g., 'z a r a' -> 'zara', 'c h a n e l' -> 'chanel'.
    4. Strip latin accents:
       e.g., 'zàra' -> 'zara', 'chánel' -> 'chanel', 'gùcci' -> 'gucci'.
    5. Normalize leetspeak substitutions (4->a, 3->e, 1->i, 0->o) on mixed or relevant tokens:
       e.g., 'z4r4' -> 'zara', 'ch4n3l' -> 'chanel', 'gucc1' -> 'gucci', 'd10r' -> 'dior'.
    """
    if not text:
        return ""
    
    # Base normalization
    s = unicodedata.normalize("NFC", text).lower()
    
    # 1. First normalize rep 1:1 / super fake variations before punctuation stripping
    # e.g., 'r.e.p. 1.1' or 'r-e-p 1-1' or 'r.e.p 1:1' -> normalize to 'rep 1:1'
    # 's.u.p.e.r f.a.k.e' -> 'super fake'
    s = re.sub(r'\br[\.\-_/\s]*e[\.\-_/\s]*p[\.\-_/\s]*[.:\-_/]?\s*(1[\.\-_/\s]*[:\/\-\.][\.\-_/\s]*1|1[\.\-_/\s]*1)\b', 'rep 1:1', s)
    s = re.sub(r'\bs[\.\-_/\s]*u[\.\-_/\s]*p[\.\-_/\s]*e[\.\-_/\s]*r[\s\-_]+f[\.\-_/\s]*a[\.\-_/\s]*k[\.\-_/\s]*e\b', 'super fake', s)
    
    # 2. Strip inter-character punctuation between single letters or letters forming words:
    # E.g. 'z.a.r.a' -> 'zara', 'c-h-a-n-e-l' -> 'chanel', 'g_u_c_c_i' -> 'gucci', 'l.v' -> 'lv'
    # Match pattern: letter followed by punctuation (dot, dash, underscore) and another letter
    # Repeat to collapse chains like z.a.r.a
    def unpunct(m):
        return m.group(1) + m.group(2)
    
    # Collapse punctuation between letters (e.g., 'z.a.r.a' -> 'zara')
    prev = None
    while prev != s:
        prev = s
        s = re.sub(r'([a-zA-Z\d\u00C0-\u024F\u1EA0-\u1EF9])[\.\-_/\*~\\|]([a-zA-Z\d\u00C0-\u024F\u1EA0-\u1EF9])', r'\1\2', s)

    # 3. Collapse spaced single letters:
    # E.g. 'z a r a' -> 'zara', 'c h a n e l' -> 'chanel', 'g u c c i' -> 'gucci'
    # Must be 2 or more single letters separated by space:
    def collapse_single_letters(match):
        # Remove whitespace inside the matched single-letter sequence
        return re.sub(r'\s+', '', match.group(0))

    # Match sequences of single alphanumeric/accented characters separated by spaces
    # Boundary: must not merge with regular multi-character words
    s = re.sub(r'(?:(?<=\s)|^)([a-zA-Z\u00C0-\u024F\u1EA0-\u1EF9])(?:\s+([a-zA-Z\u00C0-\u024F\u1EA0-\u1EF9]))+(?=\s|$)', collapse_single_letters, s)

    # 4. Strip latin accents across the string for brand matching
    s = strip_accents(s)

    # 5. Normalize leetspeak on tokens containing letters and digits
    # (Avoid corrupting standalone numbers like '100', '4 món', '3s')
    def de_leet_token(token: str) -> str:
        # If token has both letters and digits, or starts with digit followed by letters
        if any(c.isalpha() for c in token) and any(c.isdigit() for c in token):
            return token.translate(LEET_MAP)
        return token

    tokens = s.split()
    tokens = [de_leet_token(t) for t in tokens]
    return " ".join(tokens)


# Test harness cases
bypass_cases = [
    ("Punctuation Zara", "Váy Z.a.r.a dáng xòe chiết eo che bụng"),
    ("Hyphen Chanel", "Đầm C-h-a-n-e-l tiểu thư tôn dáng chiết eo"),
    ("Underscore Gucci", "Áo G_u_c_c_i croptop che mỡ bụng"),
    ("Punctuation rep 1:1", "Váy r.e.p 1:1 lụa sang chảnh chiết eo"),
    ("Underscore super fake", "Váy super_fake loại 1 chiết eo"),
    ("Standard like auth", "Đầm like auth tôn dáng che mỡ bụng"),
    ("Standard rep1:1", "Váy rep1:1 cao cấp cạp cao che bụng"),
    ("Standard fake 1:1 VN", "Áo fake 1:1 Quảng Châu hack dáng chiết eo"),
    ("Dot Dior", "Váy D.i.o.r dáng xòe che mỡ bụng"),
    ("Dot Nike", "Áo thể thao N.i.k.e hack dáng"),
    ("Dot Adidas", "Áo khoác A.d.i.d.a.s tôn dáng"),
    ("Dot LV", "Túi xách L.V sang chảnh"),
    ("Dot Hermes", "Khăn lụa H.e.r.m.e.s cao cấp"),
    ("Hyphen rep 1-1", "Váy ren r-e-p 1-1 Quảng Châu"),
    ("Slash rep 1/1", "Váy lụa rep 1/1 cao cấp"),
    ("Spaced Zara", "Váy Z a r a dáng xòe chiết eo"),
    ("Spaced Chanel", "Đầm C h a n e l tiểu thư thắt eo"),
    ("Spaced Gucci", "Áo G u c c i croptop che mỡ bụng"),
    ("Spaced Dior", "Sơ mi D i o r lụa chuẩn form"),
    ("Spaced Nike", "Giày N i k e thể thao cạp cao"),
    ("Leet Zara Z4r4", "Váy Z4r4 dáng xòe tôn dáng"),
    ("Leet Chanel Ch4n3l", "Đầm Ch4n3l siêu xinh chiết eo"),
    ("Leet Gucci Gucc1", "Áo Gucc1 thời trang che mỡ"),
    ("Leet Dior D10r", "Váy D10r sang chảnh hack eo"),
    ("Accent Zàra", "Váy Zàra thiết kế tôn dáng"),
    ("Accent Chánel", "Đầm Chánel dáng suông che bụng"),
    ("Accent Gùcci", "Áo Gùcci croptop"),
    ("Adversarial Rep 1:1 Dot", "Áo dạ r.e.p. 1.1 cao cấp chiết eo"),
    ("Adversarial Super Fake Dot", "Váy s.u.p.e.r f.a.k.e dáng xòe"),
    ("Adversarial Like Auth Hyphen", "Đầm like-auth chuẩn form hack eo"),
]

print("=== TESTING 30 HARNESS CASES ===")
for label, title in bypass_cases:
    deobf = deobfuscate_brand_text(title)
    print(f"{label:30} -> {deobf}")
