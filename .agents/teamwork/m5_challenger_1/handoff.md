# Handoff Report: Milestone 5 Empirical Adversarial Stress Testing

**Agent**: `m5_challenger_1`  
**Role**: `critic`, `specialist` (Empirical Challenger)  
**Date**: 2026-11-10T11:56:00Z  
**Verdict**: **REQUEST_CHANGES** (Grand Total: 691/737 assertions passed, 46 failures)

---

## 1. Observation

### Command Executed & High-Level Metrics
- Command: `python3 scripts/m5_adversarial_script_harness.py`
- Results:
  - Grand Total Assertions: 737
  - Total Passed: 691 (93.8%)
  - Total Failed: 46 (6.2%)
  - Suite 1 (Adversarial Title Injections & Leakage): 144 tests | 106 passed | 38 failed | 73.6% pass rate
  - Suite 2 (KOC Marker Guarantee & Contract Integrity): 464 tests | 464 passed | 0 failed | 100.0% pass rate
  - Suite 3 (Extreme & Corrupt Metadata Inputs): 84 tests | 84 passed | 0 failed | 100.0% pass rate
  - Suite 4 (Persona & Voice Mapping Integrity): 45 tests | 37 passed | 8 failed | 82.2% pass rate

---

### Failure 1: Direct Voiceover Leakage & Silent ToneValidator Evasion
- **Location**: `src/services/script_generator.py:184-215` (`_sanitize_title`) and `src/core/tone_validator.py:49-70, 110-165, 188-194`.
- **Observed Behavior**:
  For products with title containing `t.u.ồ.n a.u.t.h` or `t.u.o.n a.u.t.h`, the script generator failed to sanitize the title, and `ToneValidator.validate(full_voiceover)` returned `True`.
- **Verbatim Output**:
  ```text
  Title: 'Mẫu t.u.ồ.n a.u.t.h chính hãng cao cấp'
  Voiceover: Chị em ơi, ai bảo eo to không mặc đẹp được? Nhìn ngay chiếc Mẫu t.u.ồ.n a.u.t.h chính hãng cao cấp này! Form may chiết eo cao giấu nhẹm mỡ thừa chỉ trong tích tắc...
  ToneValidator.validate: True
  ToneValidator.check_violations: []
  ```
  ```text
  Title: 'Chiếc t.u.o.n a.u.t.h chính hãng cao cấp'
  Voiceover: Chị em ơi, mặc chiếc Chiếc t.u.o.n a.u.t.h chính hãng cao cấp này lên là eo thon gọn hẳn 5 phân không cần nịt bụng luôn!...
  ToneValidator.validate: True
  ToneValidator.check_violations: []
  ```
- **Code Quote (`src/services/script_generator.py:203`)**:
  ```python
  r"\btuồn\s*auth\b",
  ```
- **Code Quote (`src/core/tone_validator.py:54, 125-127`)**:
  ```python
  (r"\b(like|chuẩn|tuồn)[\.\s\-_]*auth\b", "like/chuẩn/tuồn auth"),
  ```
  ```python
  # Strip latin accents / combining diacritical marks
  s_nfd = unicodedata.normalize("NFD", s)
  s_stripped = "".join(c for c in s_nfd if unicodedata.category(c) != "Mn")
  s = unicodedata.normalize("NFC", s_stripped)
  ```
  Because `canonicalize_brand_text` strips the combining mark `Mn` from `t.u.ồ.n`, it becomes `tuon auth`. But `COUNTERFEIT_PATTERNS` regex specifies `tuồn` (with `ồ`), so `re.search` fails on `canon_brand`! On `norm_text`, the dots between `t.u.ồ.n` prevent `\btuồn` from matching.
  Hence, `t.u.ồ.n a.u.t.h` completely evades detection and leaks into voiceover.

---

### Failure 2: Emergency Fallback Persona Cross-Contamination
- **Location**: `src/services/script_generator.py:304-312`.
- **Observed Behavior**:
  When a HomeLife (`do_gia_dung`, `nam_minh`, `vi-VN-NamMinhNeural`) product title contains a policy-violating phrase (`vĩnh viễn không bám bẩn`, `chữa khỏi hoàn toàn`, `kính chào quý khách`, `sản phẩm hoàn hảo đáp ứng mọi nhu cầu`, `hãy nhanh tay sở hữu`), `_generate_from_templates` places the phrase into `result.hook_3s` and `result.full_voiceover`.
  `ToneValidator.validate(result.full_voiceover)` detects the violation and returns `False`.
  Line 307 triggers the emergency fallback:
  ```python
  if not ToneValidator.validate(result.full_voiceover):
      # Double sanitize if an edge case occurred
      logger.error("Template failed ToneValidator unexpectedly; applying emergency fallback")
      result.hook_3s = "Chị em ơi, nhìn ngay em này hack dáng cực đỉnh!"
      result.body = "Chất vải mát, form may giấu nhẹm mỡ thừa tôn dáng cực kỳ."
      result.cta_yellow_cart = "Chị em bấm ngay vào giỏ hàng góc trái màn hình nhận mã freeship nha!"
      result.full_voiceover = f"{result.hook_3s} {result.body} {result.cta_yellow_cart}"
  ```
- **Verbatim Output**:
  ```text
  Product: 'Chảo vĩnh viễn không bám bẩn'
  niche_id: 'do_gia_dung'
  persona: 'nam_minh'
  voice_id: 'vi-VN-NamMinhNeural'
  Voiceover: Chị em ơi, nhìn ngay em này hack dáng cực đỉnh! Chất vải mát, form may giấu nhẹm mỡ thừa tôn dáng cực kỳ. Chị em bấm ngay vào giỏ hàng góc trái màn hình nhận mã freeship nha!
  ```
- **Consequence**:
  Nam Minh (`vi-VN-NamMinhNeural`) speaks female fashion clothing lines ("Chị em ơi", "hack dáng", "giấu nhẹm mỡ thừa") for a frying pan / mop! All male KOC markers (`các bác`, `3s`, `nhàn`) are stripped.

---

### Failure 3: Prohibited Phrases Leaking into Captions
- **Location**: `src/services/script_generator.py:231, 236, 304-312`.
- **Observed Behavior**:
  34 captions leaked prohibited phrases across 17 adversarial titles.
  `caption` is generated in `_generate_from_templates` using `clean_title`.
  Because `_sanitize_title` fails to strip `N.i.k.e`, `A.d.i.d.a.s`, `r.e.p 1:1`, `s.u.p.e.r f.a.k.e`, `l.i.k.e a.u.t.h`, `vĩnh viễn không bám bẩn`, `chữa khỏi hoàn toàn`, `thần dược gia đình`, `kính chào quý khách`, `sản phẩm hoàn hảo đáp ứng mọi nhu cầu`, `hãy nhanh tay sở hữu`, these terms remain in `clean_title`.
  Furthermore, the emergency fallback in lines 304-312 **never** updates or cleans `result.caption`.
- **Verbatim Output**:
  ```text
  ❌ [trademark] Prohibited token 'N.i.k.e' leaked into caption: 'Mẫu N.i.k.e chính hãng cao cấp tôn dáng cực đỉnh #fashion #xuhuong #thoitrang #koc'
  ❌ [counterfeit] Prohibited token 'r.e.p 1:1' leaked into caption: 'Mẫu r.e.p 1:1 chính hãng cao cấp hack dáng che khuyết điểm cho chị em #outfit #thoitrangnu #xuhuong'
  ❌ [exaggerated] Prohibited token 'vĩnh viễn không bám bẩn' leaked into caption: 'Mẫu vĩnh viễn không bám bẩn chính hãng cao cấp chân ái cho hội lười dọn dẹp #meovat #giadungtienich #xuhuong'
  ❌ [robotic] Prohibited token 'kính chào quý khách' leaked into caption: 'Mẫu kính chào quý khách chính hãng cao cấp giải phóng việc nhà nhàn tênh 3s #dogiadung #giadungthongminh #xuhuong #koc'
  ```

---

## 2. Logic Chain

1. **Premise**: Directive 1 mandates:
   "Verify that generated scripts NEVER leak these into `full_voiceover` and that `ToneValidator.validate(full_voiceover)` ALWAYS returns `True`."
   Directive 4 mandates:
   "Verify that homelife products (`do_gia_dung`) always select `vi-VN-NamMinhNeural` and male KOC markers (`các bác`, `tui`, `3s`/`nhàn`)."
2. **Step 1**: In `ToneValidator`, canonicalization strips accents (`s_nfd -> Mn stripped`), but `COUNTERFEIT_PATTERNS` contains accented tokens `tuồn`, `chuẩn`, `nhái`. Thus, obfuscated variants like `t.u.ồ.n a.u.t.h` become unaccented `tuon auth`, failing both the unaccented canon check and the dotted norm check.
3. **Step 2**: In `ScriptGenerator._sanitize_title`, `banned_terms` only matches un-dotted `\bnike\b`, `\badidas\b`, `\brep\s*1[\:\/\.]1\b`, `\blike\s*auth\b`, `\btuồn\s*auth\b`, and lacks patterns for `vĩnh viễn không bám bẩn`, `chữa khỏi`, or any robotic clichés (`kính chào quý khách`, `sản phẩm hoàn hảo`, `hãy nhanh tay sở hữu`).
4. **Step 3**: Because `_sanitize_title` fails to strip these tokens, `_generate_from_templates` places them into `caption` and `hook_3s`.
5. **Step 4**: When `ToneValidator.validate(result.full_voiceover)` detects the violation, the fallback overwrites the script with a single hardcoded female fashion string (`Chị em ơi, nhìn ngay em này hack dáng...`) regardless of whether the product is HomeLife or Fashion.
6. **Step 5**: Because the fallback does not touch `result.caption`, the prohibited terms permanently leak into published captions.
7. **Conclusion**: Both Directive 1 (leakage prevention & validator robustness) and Directive 4 (persona & voice mapping integrity under stress) are breached.

---

## 3. Caveats

- **No Caveats**: All 4 directives were tested directly and empirically against live code.
- Test suites 2 and 3 passed 100% (contract key structure, diverse title KOC markers, corrupt inputs/NaN/huge strings do not crash).
- The defects are concentrated in:
  1. `src/core/tone_validator.py` (`canonicalize_brand_text` accent stripping vs. accented regex patterns).
  2. `src/services/script_generator.py` (`_sanitize_title` pattern coverage, caption cleaning, and persona-aware emergency fallback).

---

## 4. Conclusion & Required Changes

**Verdict**: **REQUEST_CHANGES**

### Remediation Guidance for Worker / Implementer:
1. **Fix `src/core/tone_validator.py`**:
   - In `COUNTERFEIT_PATTERNS`, add unaccented variants to patterns tested against `canon_brand` (e.g. `(r"\b(like|chuan|chuẩn|tuon|tuồn)[\.\s\-_]*auth\b", "like/chuẩn/tuồn auth")` and `(r"(?<!mon )(?<!món )(?<!thit )(?<!thịt )\b(nhai|nhái)\b", "nhái")`).
   - Ensure `canon_brand` also detects `tuon auth` and dotted variants.
2. **Fix `src/services/script_generator.py`**:
   - Enhance `_sanitize_title`:
     - Clean obfuscated dots from all brand names (`n.?i.?k.?e`, `a.?d.?i.?d.?a.?s`, `r.?e.?p`, `s.?u.?p.?e.?r.?f.?a.?k.?e`, `l.?i.?k.?e.?a.?u.?t.?h`, `t.?u.?ồ.?n.?a.?u.?t.?h`, `t.?u.?o.?n.?a.?u.?t.?h`).
     - Strip exaggerated claims: `vĩnh viễn không bám bẩn`, `chữa khỏi (hoàn toàn)?`, `thần dược`, `vĩnh viễn không rỉ sét`.
     - Strip robotic clichés: `kính chào quý khách`, `sản phẩm hoàn hảo`, `đáp ứng mọi nhu cầu`, `hãy nhanh tay sở hữu`, `sự lựa chọn hoàn hảo`, `chào mừng quý khách`, `rất hân hạnh được phục vụ`.
   - Update Emergency Fallback (lines 304-312):
     - Make it persona-aware: If `persona == "nam_minh"`, use HomeLife fallback (e.g. `"Các bác ơi, nhìn ngay em này việc nhà nhàn hẳn, 3s là nhà sạch bóng!"`, `"Cơ chế thông minh lau sạch kin kít không tốn một giọt mồ hôi."`, `"Các bác bấm ngay vào giỏ hàng góc trái màn hình nhận mã ưu đãi nha!"`).
     - Reset `result.caption` to a clean fallback caption (e.g. `f"{clean_title or 'Sản phẩm hot'} ..."` or clean default).

---

## 5. Verification Method

To independently reproduce all failures:
```bash
python3 scripts/m5_adversarial_script_harness.py
```
Expected output upon failure:
```text
GRAND SUMMARY: 691/737 assertions passed (93.8%)
Total Failures: 46
FINAL VERDICT: REQUEST_CHANGES
```

Invalidation condition:
The verdict can be upgraded to **APPROVE** when `python3 scripts/m5_adversarial_script_harness.py` exits with code 0 and reports `737/737 assertions passed (100.0%)` with `Total Failures: 0`.
