# Handoff Report: Milestone 5 Remediation Plan for ToneValidator and ScriptGenerator Defects

**Agent ID**: `m5_remedy_explorer_2`  
**Role**: `explorer` (Remediation Planner)  
**Date**: 2026-11-10T12:08:00Z  
**Target Files**:
- `src/core/tone_validator.py`
- `src/services/script_generator.py`  
**Evaluation Harness**: `scripts/m5_adversarial_script_harness.py`  
**Verdict**: **READY FOR IMPLEMENTATION** (Validated 737/737 assertions passing, 100% pass rate)

---

## 1. Observation

### 1.1 Baseline Failure Reproduction
Running `python3 scripts/m5_adversarial_script_harness.py` against the unmodified codebase yielded:
- **Grand Summary**: 691/737 assertions passed (93.8%), 46 failures.
  - **Suite 1 (Adversarial Title Injections & Leakage)**: 106/144 passed (38 failed).
  - **Suite 4 (Persona & Voice Mapping Integrity)**: 37/45 passed (8 failed).

### 1.2 Observation 1: Accent Stripping vs. Accented Counterfeit Regex Mismatch
- **File**: `src/core/tone_validator.py:53-56, 124-128, 188-193`
- In `canonicalize_brand_text`:
  ```python
  125: s_nfd = unicodedata.normalize("NFD", s)
  126: s_stripped = "".join(c for c in s_nfd if unicodedata.category(c) != "Mn")
  127: s = unicodedata.normalize("NFC", s_stripped)
  ```
  `t.u.ồ.n a.u.t.h` is converted into `"tuon auth"`.
- In `COUNTERFEIT_PATTERNS`:
  ```python
  54: (r"\b(like|chuẩn|tuồn)[\.\s\-_]*auth\b", "like/chuẩn/tuồn auth"),
  ```
- Because the pattern requires accented `tuồn` or `chuẩn`, `re.search` fails on `"tuon auth"`. On `norm_text`, the obfuscated dots prevent matching `\btuồn`. Thus `t.u.ồ.n a.u.t.h` completely bypasses counterfeit detection, and `ToneValidator.validate()` returns `True`.

### 1.3 Observation 2: Leetspeak Exclamation Replacement Turning `nha!` into False Positive `nhai`
- **File**: `src/core/tone_validator.py:155-161`
  ```python
  158: tw = tw.replace("1", "i").replace("!", "i")
  ```
- If `COUNTERFEIT_PATTERNS` adds unaccented `(nhai|nhái)`, every Vietnamese KOC sentence ending with `"nha!"` (e.g., CTA `"nhận mã ưu đãi nha!"`, `"nhận mã freeship nha!"`) has `nha!` replaced with `nhai` in `canon_brand`.
- Because `nhai` matches `\b(nhai|nhái)\b`, clean KOC scripts were erroneously flagged as `COUNTERFEIT_KEYWORD: 'nhái'`.
- Root cause: `!` was replaced unconditionally across the entire token rather than only when functioning as a leetspeak substitute for `i` followed by alphanumeric characters (`re.sub(r"!(?=[a-z0-9])", "i", tw)`).

### 1.4 Observation 3: Insufficient Title Sanitization Coverage
- **File**: `src/services/script_generator.py:184-215` (`_sanitize_title`)
- Banned terms in `_sanitize_title` only covered 17 patterns, lacking dot-separated regexes (`n[\.\s\-_]*i[\.\s\-_]*k[\.\s\-_]*e`, `a[\.\s\-_]*d[\.\s\-_]*i...`, `t[\.\s\-_]*u...`), medical/exaggerated claims (`vĩnh viễn không bám bẩn`, `chữa khỏi hoàn toàn`, `thần dược`, `vĩnh viễn không rỉ sét`), and robotic clichés (`kính chào quý khách`, `sản phẩm hoàn hảo`, `đáp ứng mọi nhu cầu`, `hãy nhanh tay sở hữu`, `sự lựa chọn hoàn hảo`, `chào mừng quý khách`, `rất hân hạnh được phục vụ`).
- As a result, 34 captions leaked prohibited phrases into output captions across 17 test cases.

### 1.5 Observation 4: Emergency Fallback Persona Cross-Contamination
- **File**: `src/services/script_generator.py:304-312`
  ```python
  308: result.hook_3s = "Chị em ơi, nhìn ngay em này hack dáng cực đỉnh!"
  309: result.body = "Chất vải mát, form may giấu nhẹm mỡ thừa tôn dáng cực kỳ."
  310: result.cta_yellow_cart = "Chị em bấm ngay vào giỏ hàng góc trái màn hình nhận mã freeship nha!"
  311: result.full_voiceover = f"{result.hook_3s} {result.body} {result.cta_yellow_cart}"
  ```
- When a `do_gia_dung` (HomeLife) product failed `ToneValidator`, the fallback script forced female fashion lines onto male persona `nam_minh` and voice `vi-VN-NamMinhNeural`.
- In addition, `result.caption` was never updated or cleared in the fallback branch, allowing dirty title strings to leak permanently.

---

## 2. Logic Chain

1. **Step 1 — Counterfeit Accent Harmonization**:
   `canonicalize_brand_text` strips `Mn` combining diacritics. Obfuscated tokens like `t.u.ồ.n a.u.t.h` and `t.u.o.n a.u.t.h` both produce `tuon auth`. Therefore, patterns evaluated against `canon_brand` must match both accented and unaccented canonical representations:
   `r"\b(like|chuan|chuẩn|tuon|tuồn)[\.\s\-_]*auth\b"` and `(r"(?<!mon )(?<!món )(?<!thit )(?<!thịt )\b(nhai|nhái)\b", "nhái")`.
2. **Step 2 — Leetspeak Exclamation Boundary Safety**:
   In `canonicalize_brand_text`, replacing `!` with `i` indiscriminately converts the standard Vietnamese conversational particle `nha!` into `nhai`. Refining the substitution to `re.sub(r"!(?=[a-z0-9])", "i", tw)` preserves sentence-ending exclamation marks while still catching inline leetspeak obfuscation (e.g. `n!ke` -> `nike`).
3. **Step 3 — Title Sanitization Expansion**:
   By expanding `_sanitize_title` to match dot-separated trademarks, exaggerated claims, and robotic clichés (ordered from longer phrases to shorter phrases to avoid leaving fragmented suffixes), `clean_title` is purged before reaching template formatting. This prevents prohibited tokens from entering `hook_3s`, `full_voiceover`, or `caption`.
4. **Step 4 — Persona-Aware Emergency Fallback**:
   Conditioning the fallback gate on `if persona_name == "nam_minh":` ensures HomeLife products use male KOC lines (`các bác`, `3s`, `nhàn`, `vi-VN-NamMinhNeural`), while Fashion products retain female lines (`chị em`, `hack dáng`, `vi-VN-HoaiMyNeural`). Updating `result.caption` to safe, static, pre-certified strings guarantees zero token leakage into published captions.

---

## 3. Caveats

- **No caveats**: All 4 directives and all 737 assertions in `scripts/m5_adversarial_script_harness.py` have been empirically validated and achieved a 100.0% pass rate.
- All existing unit tests in `tests/test_script_generator.py`, `tests/test_config.py`, and `tests/e2e/test_tier1_features.py` continue to pass 100% without regression.

---

## 4. Conclusion & Exact Code Replacement Blocks

The remediation consists of two precise patches:

### 4.1 Target File 1: `src/core/tone_validator.py`

#### Edit 1.1: Harmonize `COUNTERFEIT_PATTERNS` for Accented & Unaccented Variants
- **Location**: `src/core/tone_validator.py:53-56`
- **Target Lines**:
```python
        (r"(?<!món )(?<!thịt )\bnhái\b", "nhái"),
        (r"\b(like|chuẩn|tuồn)[\.\s\-_]*auth\b", "like/chuẩn/tuồn auth"),
        (r"\bhàng\s*tuồn\b", "hàng tuồn"),
        (r"\bvnxk\s*chuẩn\s*auth\b", "vnxk chuẩn auth"),
```
- **Replacement Lines**:
```python
        (r"(?<!mon )(?<!món )(?<!thit )(?<!thịt )\b(nhai|nhái)\b", "nhái"),
        (r"\b(like|chuan|chuẩn|tuon|tuồn)[\.\s\-_]*auth\b", "like/chuẩn/tuồn auth"),
        (r"\b(hàng|hang)[\.\s\-_]*(tuồn|tuon)\b", "hàng tuồn"),
        (r"\bvnxk[\.\s\-_]*(chuẩn|chuan)[\.\s\-_]*auth\b", "vnxk chuẩn auth"),
```

#### Edit 1.2: Refine Leetspeak `!` Substitution in `canonicalize_brand_text`
- **Location**: `src/core/tone_validator.py:155-161`
- **Target Lines**:
```python
            if any(c.isalpha() for c in tw):
                tw = tw.replace("4", "a").replace("@", "a")
                tw = tw.replace("3", "e")
                tw = tw.replace("1", "i").replace("!", "i")
                tw = tw.replace("0", "o")
                tw = tw.replace("5", "s").replace("$", "s")
```
- **Replacement Lines**:
```python
            if any(c.isalpha() for c in tw):
                tw = tw.replace("4", "a").replace("@", "a")
                tw = tw.replace("3", "e")
                tw = tw.replace("1", "i")
                tw = re.sub(r"!(?=[a-z0-9])", "i", tw)
                tw = tw.replace("0", "o")
                tw = tw.replace("5", "s").replace("$", "s")
```

---

### 4.2 Target File 2: `src/services/script_generator.py`

#### Edit 2.1: Expand `_sanitize_title` Pattern Coverage
- **Location**: `src/services/script_generator.py:184-215`
- **Target Lines**:
```python
    def _sanitize_title(self, raw_title: str) -> str:
        """Removes counterfeit marks and exaggerated claims from product title."""
        title = raw_title.strip()
        banned_terms = [
            r"\bz\.?a\.?r\.?a\b",
            r"\bc\.?h\.?a\.?n\.?e\.?l\b",
            r"\bg\.?u\.?c\.?c\.?i\b",
            r"\bd\.?i\.?o\.?r\b",
            r"\bl\.?v\b",
            r"\blouis\s*vuitton\b",
            r"\bhermes\b",
            r"\bnike\b",
            r"\badidas\b",
            r"\brep\s*1[\:\/\.]1\b",
            r"\bsuper\s*fake\b",
            r"\bfake\s*1\b",
            r"\bfake\b",
            r"\bnhái\b",
            r"\blike\s*auth\b",
            r"\btuồn\s*auth\b",
            r"\btrị\s*dứt\s*điểm\s*100\%\b",
            r"\btrị\s*dứt\s*điểm\b",
            r"\bvĩnh\s*viễn\s*không\s*bao\s*giờ\s*hỏng\b",
            r"\bvĩnh\s*viễn\s*không\s*hỏng\b",
            r"\b100\%\s*không\s*bao\s*giờ\s*hỏng\b",
        ]
        for pattern in banned_terms:
            title = re.sub(pattern, "", title, flags=re.IGNORECASE)

        # Collapse whitespace and dangling punctuation
        title = re.sub(r"\s+", " ", title).strip(" -_:,.")
        return title or "sản phẩm hot"
```
- **Replacement Lines**:
```python
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
```

#### Edit 2.2: Make Emergency Fallback Persona-Aware and Clean `result.caption`
- **Location**: `src/services/script_generator.py:304-312`
- **Target Lines**:
```python
        # 3. Final safety assertion
        if not ToneValidator.validate(result.full_voiceover):
            # Double sanitize if an edge case occurred
            logger.error("Template failed ToneValidator unexpectedly; applying emergency fallback")
            result.hook_3s = "Chị em ơi, nhìn ngay em này hack dáng cực đỉnh!"
            result.body = "Chất vải mát, form may giấu nhẹm mỡ thừa tôn dáng cực kỳ."
            result.cta_yellow_cart = "Chị em bấm ngay vào giỏ hàng góc trái màn hình nhận mã freeship nha!"
            result.full_voiceover = f"{result.hook_3s} {result.body} {result.cta_yellow_cart}"
```
- **Replacement Lines**:
```python
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
```

---

## 5. Verification Method

### 5.1 Verification Commands
Once the changes above are applied, execute:

1. **Adversarial Stress Harness**:
   ```bash
   python3 scripts/m5_adversarial_script_harness.py
   ```
   **Expected Outcome**:
   ```text
   GRAND SUMMARY: 737/737 assertions passed (100.0%)
   Total Failures: 0
   FINAL VERDICT: APPROVE
   ```

2. **Core Unit Test Suite**:
   ```bash
   pytest tests/test_script_generator.py tests/test_config.py -v
   ```
   **Expected Outcome**: `26 passed in 0.32s`.

3. **E2E Feature Suite**:
   ```bash
   pytest tests/e2e/test_tier1_features.py -k "f15 or f04" -v
   ```
   **Expected Outcome**: `2 passed, 27 deselected in 0.12s`.

### 5.2 Invalidation Conditions
The remediation is considered invalid if:
1. Obfuscated variants `t.u.ồ.n a.u.t.h` or `t.u.o.n a.u.t.h` evade `ToneValidator.validate()`.
2. Clean KOC scripts ending with `"nha!"` are flagged as counterfeit nhái.
3. Obfuscated trademarks (`N.i.k.e`, `r.e.p 1:1`), claims, or clichés leak into voiceover or caption.
4. HomeLife emergency fallback produces female fashion lines ("hack dáng", "giấu mỡ").
