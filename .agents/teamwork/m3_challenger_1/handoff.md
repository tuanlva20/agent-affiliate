# Adversarial Stress Testing Handoff Report: Milestone 3 (FashionScoutAgent)

**Agent ID**: `m3_challenger_1`  
**Milestone**: Milestone 3 (Specialist Scout Agents & Prompt Templates)  
**Assigned Roles**: critic, specialist  
**Working Directory**: `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m3_challenger_1/`  
**Date**: 2026-11-10T09:28:00Z  
**Handoff Type**: Hard Handoff  
**VERDICT**: **REQUEST_CHANGES**

---

## 1. Observation

### 1.1 Test Suite & Harness Execution Summary

Three test suites were executed independently in the environment:
1. `pytest tests/test_specialist_scouts.py -v` (Unit suite by worker_m3_1):
   - Result: `37 passed in 0.59s` (100% pass)
2. `pytest tests/e2e/ -v` (End-to-end integration suite):
   - Result: `61 passed in 1.40s` (100% pass)
3. `python3 scripts/m3_fashion_adversarial_harness.py` (Dedicated adversarial challenge harness):
   - Result: **FAILED** with exit code 1.
   - Summary: `69/93 assertions passed (74.2%)`. **24 critical failures** in Challenge 1 (Trademark Bypass).

### 1.2 Verbatim Command Outputs

#### Command 1: `python3 scripts/m3_fashion_adversarial_harness.py`
```
================================================================================
AMAS v1.4.0 — Milestone 3 FashionScoutAgent Adversarial Challenge Harness
================================================================================

▶ Challenge 1: Trademark Bypass Matrix: FAIL (24 issues)
  Tests: 30 | Passed: 6 | Failed: 24 | Pass Rate: 20.0%
  Top Failure Details (first 5):
    ❌ [Punctuation Zara] 'Váy Z.a.r.a dáng xòe chiết eo che bụng' -> passed_filter=True, score=9.6, rejection_reason=None
    ❌ [Hyphen Chanel] 'Đầm C-h-a-n-e-l tiểu thư tôn dáng chiết eo' -> passed_filter=True, score=9.0, rejection_reason=None
    ❌ [Underscore Gucci] 'Áo G_u_c_c_i croptop che mỡ bụng' -> passed_filter=True, score=8.2, rejection_reason=None
    ❌ [Punctuation rep 1:1] 'Váy r.e.p 1:1 lụa sang chảnh chiết eo' -> passed_filter=True, score=8.2, rejection_reason=None
    ❌ [Dot Dior] 'Váy D.i.o.r dáng xòe che mỡ bụng' -> passed_filter=True, score=8.7, rejection_reason=None
    ... and 19 more failures.

▶ Challenge 2: Corrupted & Boundary Inputs: PASS
  Tests: 25 | Passed: 25 | Failed: 0 | Pass Rate: 100.0%

▶ Challenge 3: Score Threshold Boundary: PASS
  Tests: 10 | Passed: 10 | Failed: 0 | Pass Rate: 100.0%

▶ Challenge 4: Hook Angle Tone Validation: PASS
  Tests: 26 | Passed: 26 | Failed: 0 | Pass Rate: 100.0%
      [Throughput] Evaluated 160 items in 34.6ms (4626.0 items/sec)

▶ Challenge 5: Concurrency & High Throughput: PASS
  Tests: 2 | Passed: 2 | Failed: 0 | Pass Rate: 100.0%

================================================================================
SUMMARY: 69/93 assertions passed (74.2%). Total Failures: 24
================================================================================
```

#### Detailed Breakdown of All 24 Trademark Bypass Failures (Challenge 1)
```
 1. [Punctuation Zara] 'Váy Z.a.r.a dáng xòe chiết eo che bụng' -> passed_filter=True, score=9.6, rejection_reason=None
 2. [Hyphen Chanel] 'Đầm C-h-a-n-e-l tiểu thư tôn dáng chiết eo' -> passed_filter=True, score=9.0, rejection_reason=None
 3. [Underscore Gucci] 'Áo G_u_c_c_i croptop che mỡ bụng' -> passed_filter=True, score=8.2, rejection_reason=None
 4. [Punctuation rep 1:1] 'Váy r.e.p 1:1 lụa sang chảnh chiết eo' -> passed_filter=True, score=8.2, rejection_reason=None
 5. [Dot Dior] 'Váy D.i.o.r dáng xòe che mỡ bụng' -> passed_filter=True, score=8.7, rejection_reason=None
 6. [Dot Nike] 'Áo thể thao N.i.k.e hack dáng' -> passed_filter=True, score=8.1, rejection_reason=None
 7. [Dot Adidas] 'Áo khoác A.d.i.d.a.s tôn dáng' -> passed_filter=True, score=8.1, rejection_reason=None
 8. [Dot LV] 'Túi xách L.V sang chảnh' -> passed_filter=False, score=6.6, rejection_reason='Product score 6.6 below minimum threshold (7.0)'
 9. [Dot Hermes] 'Khăn lụa H.e.r.m.e.s cao cấp' -> passed_filter=False, score=6.6, rejection_reason='Product score 6.6 below minimum threshold (7.0)'
10. [Hyphen rep 1-1] 'Váy ren r-e-p 1-1 Quảng Châu' -> passed_filter=False, score=6.6, rejection_reason='Product score 6.6 below minimum threshold (7.0)'
11. [Spaced Zara] 'Váy Z a r a dáng xòe chiết eo' -> passed_filter=True, score=8.7, rejection_reason=None
12. [Spaced Chanel] 'Đầm C h a n e l tiểu thư thắt eo' -> passed_filter=True, score=8.2, rejection_reason=None
13. [Spaced Gucci] 'Áo G u c c i croptop che mỡ bụng' -> passed_filter=True, score=8.2, rejection_reason=None
14. [Spaced Dior] 'Sơ mi D i o r lụa chuẩn form' -> passed_filter=True, score=8.1, rejection_reason=None
15. [Spaced Nike] 'Giày N i k e thể thao cạp cao' -> passed_filter=True, score=8.2, rejection_reason=None
16. [Leet Zara Z4r4] 'Váy Z4r4 dáng xòe tôn dáng' -> passed_filter=True, score=8.6, rejection_reason=None
17. [Leet Chanel Ch4n3l] 'Đầm Ch4n3l siêu xinh chiết eo' -> passed_filter=True, score=8.2, rejection_reason=None
18. [Leet Gucci Gucc1] 'Áo Gucc1 thời trang che mỡ' -> passed_filter=False, score=6.6, rejection_reason='Product score 6.6 below minimum threshold (7.0)'
19. [Leet Dior D10r] 'Váy D10r sang chảnh hack eo' -> passed_filter=False, score=6.6, rejection_reason='Product score 6.6 below minimum threshold (7.0)'
20. [Accent Zàra] 'Váy Zàra thiết kế tôn dáng' -> passed_filter=True, score=8.1, rejection_reason=None
21. [Accent Chánel] 'Đầm Chánel dáng suông che bụng' -> passed_filter=True, score=8.2, rejection_reason=None
22. [Accent Gùcci] 'Áo Gùcci croptop' -> passed_filter=False, score=6.6, rejection_reason='Product score 6.6 below minimum threshold (7.0)'
23. [Adversarial Rep 1:1 Dot] 'Áo dạ r.e.p. 1.1 cao cấp chiết eo' -> passed_filter=True, score=8.2, rejection_reason=None
24. [Adversarial Super Fake Dot] 'Váy s.u.p.e.r f.a.k.e dáng xòe' -> passed_filter=True, score=7.8, rejection_reason=None
```

### 1.3 Inspection of Implementation Files

1. `src/core/tone_validator.py` (lines 48-70):
   ```python
   COUNTERFEIT_PATTERNS: List[Tuple[str, str]] = [
       (r"(?:\b|^|\s)rep[\s\-_]*(1[\s\-_]*[:\/\-\.][\s\-_]*1|1[\s\-_]*1)(?:\b|$|\s)", "rep 1:1"),
       (r"\bsuper[\s\-_]*fake\b", "super fake"),
       (r"\b(hàng|hang|áo|quần|giày|dép|túi|ví|đầm|bản)?\s*fake(\s*1(?:\s*[:\/\-\.]\s*1)?)?\b", "fake"),
       (r"\b(hàng|hang)\s*(fake|rep|f1)\b", "hàng fake/rep/f1"),
       (r"(?<!món )(?<!thịt )\bnhái\b", "nhái"),
       (r"\b(like|chuẩn|tuồn)[\s\-_]*auth\b", "like/chuẩn/tuồn auth"),
       (r"\bhàng\s*tuồn\b", "hàng tuồn"),
       (r"\bvnxk\s*chuẩn\s*auth\b", "vnxk chuẩn auth"),
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
   ```
2. `src/agents/fashion_scout.py` (lines 251-271):
   ```python
   # 2. Trademark / Counterfeit Policy Check via ToneValidator & Config Banned Keywords
   violations = ToneValidator.check_violations(title)
   counterfeit_violations = [v for v in violations if "COUNTERFEIT_KEYWORD" in v]

   norm_title = unicodedata.normalize("NFC", title).lower()
   config_banned = [k for k in self.banned_keywords if k.lower() in norm_title]

   if counterfeit_violations or config_banned:
       ...
   ```
3. `config.yaml` (lines 92-108):
   Banned keywords are static strings: `"zara"`, `"chanel"`, `"gucci"`, `"dior"`, `"louis vuitton"`, `"lv"`, `"hermes"`, `"nike"`, `"adidas"`, `"rep 1:1"`, `"rep 1 1"`, `"super fake"`, `"hàng rep"`, `"like auth"`, `"chuẩn auth"`, `"tuồn auth"`.

---

## 2. Logic Chain

1. **Vulnerability Root Cause**:
   - `ToneValidator.COUNTERFEIT_PATTERNS` uses strict word boundary regexes (`\bzara\b`, `\bchanel\b`, `\bgucci\b`, etc.) operating on raw unicode text.
   - When an affiliate seller or scraped title obfuscates the brand name using punctuation (e.g. `Z.a.r.a`, `C-h-a-n-e-l`, `G_u_c_c_i`, `D.i.o.r`), spaces (e.g. `Z a r a`, `C h a n e l`), leetspeak (e.g. `Z4r4`, `Ch4n3l`), or accents (e.g. `Zàra`, `Chánel`), the pattern `\bzara\b` fails to match because '.' is not a word character in regex, spaces break token continuity, and substituted glyphs change the character codes.
   - Furthermore, `config.yaml` banned keywords check `k.lower() in norm_title` which only matches contiguous substrings and therefore also misses `z.a.r.a`, `z a r a`, etc.

2. **Impact & Blast Radius (Critical)**:
   - When a counterfeit title bypasses `ToneValidator.check_violations()` and `config_banned`, execution falls through to body-hack keyword scoring (lines 288-319).
   - If the counterfeit listing contains appealing fashion terms (e.g., `"chiết eo"`, `"che bụng"`, `"tôn dáng"`, `"dáng xòe"`), it is awarded maximum category bonuses and sales multipliers.
   - As observed empirically:
     - `'Váy Z.a.r.a dáng xòe chiết eo che bụng'` **passed with score 9.6**!
     - `'Đầm C-h-a-n-e-l tiểu thư tôn dáng chiết eo'` **passed with score 9.0**!
     - `'Áo G_u_c_c_i croptop che mỡ bụng'` **passed with score 8.2**!
     - `'Váy r.e.p 1:1 lụa sang chảnh chiết eo'` **passed with score 8.2**!
     - `'Váy s.u.p.e.r f.a.k.e dáng xòe'` **passed with score 7.8**!
   - These counterfeit listings are marked as `passed_filter = True` and scored above 8.0, meaning they will be surfaced to the Telegram Command Center as high-priority viral recommendations, approved for automated video remixing, and published to TikTok Shop channels.
   - This directly leads to copyright infringement strikes, merchant affiliate suspensions, and permanent account bans under TikTok Shop Intellectual Property policy.

3. **Inconsistency on Rejected Items**:
   - For cases where the product lacked enough body-hack keywords to pass the 7.0 threshold (e.g. `'Túi xách L.V sang chảnh'`, score 6.6), the rejection reason was `"Product score 6.6 below minimum threshold (7.0)"` instead of flagging the counterfeit brand with `score = 0.0` and citing `"trademark policy"`. If such an item had high sales velocity, it would have passed.

4. **Areas of Robustness**:
   - Challenge 2 (Corrupted & Boundary Inputs) passed 100% (25/25): NaN, Inf, None, zero price, huge sales (10^9), and non-dict inputs were handled cleanly without uncaught exceptions.
   - Challenge 3 (Score Threshold Boundary) passed 100% (10/10): Products right below and above thresholds were evaluated accurately.
   - Challenge 4 (Hook Angle Tone Validation) passed 100% (26/26): All generated hooks strictly passed ToneValidator and contained spoken KOC markers.
   - Challenge 5 (Concurrency & High Throughput) passed 100% (2/2): Evaluated 160 items concurrently across 16 threads in 34.6ms (~4,626 items/s) with 100% deterministic outputs and zero race conditions.

---

## 3. Caveats

- **LLM Synthesis**: This evaluation tested the deterministic Python rule engine of `FashionScoutAgent`. If an external LLM is called via `build_fashion_evaluation_prompt`, the LLM prompt in `prompt_templates.py` contains explicit guidelines to reject counterfeit brands; however, production high-throughput scraping relies on the local `FashionScoutAgent.evaluate_product()` method.
- **Vietnamese Diacritics on Common Words**: Canonicalization for brand checking must be careful not to strip diacritics from normal Vietnamese words when checking non-brand criteria (e.g. don't corrupt `áo`, `váy`, `bụng`). The brand normalizer should run on an auxiliary normalized view of the title specifically for counterfeit detection.

---

## 4. Conclusion

### Final Verdict: **REQUEST_CHANGES**

Milestone 3 implementation cannot be approved in its current state because it fails the explicit requirement to reject 100% of counterfeit brand bypass attempts (achieved only 20% on Challenge 1).

### Actionable Remediation Required:

1. **Obfuscation-Resistant Brand Canonicalizer in `ToneValidator`**:
   Implement a title canonicalizer before evaluating `COUNTERFEIT_PATTERNS`:
   - Strip all punctuation, dots, hyphens, underscores: `re.sub(r"[^\w\s]", "", title)`
   - Collapse single-character spaced tokens into words (e.g., `"z a r a"` -> `"zara"`, `"c h a n e l"` -> `"chanel"`).
   - Substitute common leetspeak characters: `4/@ -> a`, `3 -> e`, `1/! -> i`, `0 -> o`, `5/$ -> s`.
   - Strip Latin accents on brand tokens: `à, á -> a`, `è, é -> e`, etc.
   - Broaden the `rep 1:1` and `super fake` regex patterns to tolerate internal punctuation/dots: e.g., `r[\.\s\-_]*e[\.\s\-_]*p[\.\s\-_]*(1[\.\s\-_]*[:\/\-\.][\.\s\-_]*1|1[\.\s\-_]*1)`.

2. **Enforce Zero Tolerance in `FashionScoutAgent`**:
   Ensure `FashionScoutAgent.evaluate_product` uses the canonicalized counterfeit check so that any obfuscated brand immediately triggers `passed_filter = False`, `score = 0.0`, and `rejection_reason` containing `"trademark"` or `"policy"`.

---

## 5. Verification Method

To independently reproduce the failures and verify fixes:

1. **Execute Dedicated Adversarial Harness**:
   ```bash
   python3 scripts/m3_fashion_adversarial_harness.py
   ```
   - Current result: `FAIL (24 issues in Challenge 1, exit code 1)`.
   - Target passing condition: `93/93 passed (100.0%, exit code 0)`.

2. **Verify Existing Suites Remain 100% Green**:
   ```bash
   pytest tests/test_specialist_scouts.py -v
   pytest tests/e2e/ -v
   ```

3. **Invalidation Conditions for Any Proposed Fix**:
   - Any title containing `"Z.a.r.a"`, `"C-h-a-n-e-l"`, `"G_u_c_c_i"`, `"r.e.p 1:1"`, `"super_fake"`, `"Z a r a"`, `"Z4r4"`, or `"Zàra"` passing filter (`passed_filter == True`) or scoring $> 0.0$.
   - Any failure or regression in existing 37 unit tests or 61 e2e tests.
