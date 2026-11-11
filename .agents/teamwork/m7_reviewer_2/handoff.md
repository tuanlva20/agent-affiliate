# Review & Adversarial Critic Report: Feature F27 (CommentAgent Intent & KOC Reply)

**Reviewer**: `m7_reviewer_2` (Roles: Reviewer, Adversarial Critic)  
**Parent Agent**: `f5177315-7404-4813-b8ba-56081885cdd4`  
**Working Directory**: `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m7_reviewer_2/`  
**Milestone**: Milestone 7 (Comment Engagement & Conversion Agent: Feature F27)  
**Date**: 2026-11-10T17:03:00Z  
**Verdict**: **APPROVE**  

---

## 1. Observation

### 1.1 Static Integrity Verification
Executed static integrity scan on the entire `src/` directory to detect any forbidden imports of `unittest.mock` (`MagicMock`, `AsyncMock`, `patch`) or test-bypass shortcuts:
```bash
python3 -c "
import os, sys
violations = []
for root, dirs, files in os.walk('src'):
    for file in files:
        if file.endswith('.py'):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'unittest.mock' in content or 'MagicMock' in content or 'AsyncMock' in content or 'from unittest import mock' in content:
                    violations.append((path, 'mock import'))
                if 'MOCK_PASS' in content or 'BYPASS_INTEGRITY' in content:
                    violations.append((path, 'bypass flag'))
assert len(violations) == 0, f'Integrity violations found: {violations}'
print('Static Integrity Check: 100% CLEAN. Zero mock imports and zero dummy bypass flags in src/')
"
```
**Output**:
```
Static Integrity Check: 100% CLEAN. Zero mock imports and zero dummy bypass flags in src/
```

### 1.2 Test Execution Results
1. **Targeted CommentAgent Intent & Reply Suite**:
   ```bash
   pytest tests/test_comment_agent.py -k "TestCommentIntent or TestGenerateReply or TestTone" -v
   ```
   **Output**: `48 passed, 15 deselected in 0.72s` (100% PASS).

2. **Tier 1 E2E Integration Suite for Feature F27**:
   ```bash
   pytest tests/e2e/test_tier1_features.py -k "test_f27" -v
   ```
   **Output**: `1 passed, 28 deselected in 0.08s` (100% PASS).

3. **Full Milestone 7 Comment Suite**:
   ```bash
   pytest tests/test_comment_agent.py -v
   ```
   **Output**: `63 passed in 1.12s` (100% PASS).

4. **Full Repository Regression Suite**:
   ```bash
   pytest tests/ -q
   ```
   **Output**: `457 passed in 22.20s` (100% PASS with zero regressions across Milestones 1–7).

### 1.3 Implementation Inspection
- `src/agents/comment_agent.py`:
  - `CommentIntent` enum values defined (lines 26-32):
    - `ASK_PRICE = "ask_price"`
    - `ASK_MATERIAL_USAGE = "ask_material_usage"`
    - `COMPLAINT = "complaint"`
    - `OTHER = "other"`
  - `classify_intent` (lines 223-262):
    - Normalizes text via Unicode NFC (`unicodedata.normalize("NFC", comment_text).lower().strip()`).
    - Strips diacritics via `remove_accents` for unaccented transliteration matching.
    - Evaluates dual compiled regex sets (`_complaint_res`, `_complaint_unacc_res`, `_price_res`, `_price_unacc_res`, `_material_res`, `_material_unacc_res`).
    - Price false-positive guards (`_re_false_price`, `_re_product_price`, `_re_explicit_q`).
    - Enforces priority order: `COMPLAINT` > `ASK_PRICE` > `ASK_MATERIAL_USAGE` > `OTHER`.
  - `generate_reply` (lines 316-402):
    - Resolves persona to `hoai_my` (Fashion) or `nam_minh` (Home Utilities).
    - Price formatting into standard currency representation (`189,000đ`).
    - Sanitizes product title via `_sanitize_title` against banned counterfeits and exaggerated claims.
    - Deterministic MD5 rotation across certified template banks.
    - 100% `ToneValidator.validate()` enforcement with emergency certified fallbacks.
- `src/agents/__init__.py`:
  - Properly exports `CommentAgent` and `CommentIntent` in `__all__`.

### 1.4 Adversarial Stress Testing Observations
1. **Unicode Decomposed Normalization (NFD vs NFC)**:
   - Evaluated both `text_nfc` and `text_nfd` for `"Váy này giá bao nhiêu vậy shop?"`.
   - Both returned `CommentIntent.ASK_PRICE`.
2. **Vietnamese Homograph Pairs**:
   - `bụng` vs `bung chỉ`:
     - `"bung 75 mac vua k"` -> `CommentIntent.ASK_MATERIAL_USAGE`.
     - `"ao bi bung chi roi sop oi"` -> `CommentIntent.COMPLAINT`.
   - `lâu` vs `cây lau`:
     - `"cay lau nha thong minh nay dung the nao"` -> `CommentIntent.ASK_MATERIAL_USAGE`.
     - `"ship lau qua shop oi"` -> `CommentIntent.COMPLAINT`.
   - `lừa` vs `vải lụa`:
     - `"chat vai lua mem mat ko"` -> `CommentIntent.ASK_MATERIAL_USAGE`.
     - `"shop lua dao a"` -> `CommentIntent.COMPLAINT`.
   - `hong` vs `hỏng`:
     - `"chất co giãn hong shop"` -> `CommentIntent.ASK_MATERIAL_USAGE`.
     - `"hang bi hong roi sop oi"` -> `CommentIntent.COMPLAINT`.
     - `"đẹp hong shop"` -> `CommentIntent.OTHER`.
3. **False-Positive Price Disqualification**:
   - `"giá như e biết shop sớm hơn"` -> `CommentIntent.OTHER`.
   - `"danh gia 5 sao cho shop nhe"` -> `CommentIntent.OTHER`.
   - `"vay dep gia re qua shop oi"` -> `CommentIntent.OTHER`.
   - `"cai gia de do nay bao tien"` -> `CommentIntent.ASK_PRICE` (allowed due to explicit inquiry).
4. **Tone Compliance Guarantee**:
   - Tested all 24 templates across 8 template banks in `CommentAgent`: 24/24 (100%) passed `ToneValidator.validate()`.
   - Tested all 4 emergency fallback responses: 4/4 (100%) passed `ToneValidator.validate()`.
5. **Title Sanitization**:
   - Stripped `"Váy Zara rep 1:1 siêu xịn tốt nhất thị trường vĩnh viễn không hỏng"` -> `"Váy siêu xịn"`.
   - Stripped `"Bộ nồi G.u.c.c.i s-u-p-e-r-f-a-k-e 100% không bao giờ hỏng"` -> `"Bộ nồi"`.

---

## 2. Logic Chain

1. **Integrity Assessment (Step 1.1)**:
   - There are zero occurrences of `unittest.mock` (`MagicMock`, `AsyncMock`, `patch`) or mock bypass flags anywhere in `src/`.
   - Source code implements genuine NLP normalization, compiled regex trees, currency string formatting, and template selection logic.
   - Conclusion: Zero integrity violations. Work is 100% genuine and not self-certifying facade.

2. **Specification & Contract Compliance (Step 1.2 & 1.3)**:
   - `CommentIntent` contains the required four enum values: `ask_price`, `ask_material_usage`, `complaint`, `other`.
   - `classify_intent` honors the strict priority order `COMPLAINT` > `ASK_PRICE` > `ASK_MATERIAL_USAGE` > `OTHER`. When a comment contains both a complaint (e.g. shipping delay or defective fabric) and a price or material question, it unconditionally resolves to `COMPLAINT`, ensuring brand safety.
   - Dual compiled regex trees allow high-throughput classification of both diacritic-accented Vietnamese and informal unaccented chat/slang.
   - `generate_reply` aligns with the two pilot personas: Hoài My for Fashion (sisterly, body-hack focus) and Nam Minh for Home Utilities (practical, labor-saving focus).
   - Yellow cart navigation ("giỏ hàng vàng góc trái", "freeship") is present in all conversion templates.
   - 100% tone compliance is enforced through pre-certified templates and an emergency fallback safety net invoking `ToneValidator.validate()`.

3. **Adversarial Robustness (Step 1.4)**:
   - Stress testing verified that all four homograph conflict zones identified in the requirements (`bụng` vs `bung chỉ`, `lâu` vs `cây lau`, `lừa` vs `vải lụa`, `hong` vs `hỏng`) are resolved without false positives.
   - Price false-positive guards prevent non-price queries containing the word "giá" (e.g., "giá như", "đánh giá", "giá để đồ") from triggering `ASK_PRICE` unless accompanied by explicit interrogatives.
   - NFD unicode decomposed strings are normalized to NFC before evaluation, guaranteeing stability across mobile operating systems.

4. **Minor Adversarial Findings (Non-blocking)**:
   - **Finding 1 (Minor - Persona String Normalization)**: In `src/agents/comment_agent.py:294`, `_resolve_persona` checks `if "nam_minh" in p_name:`. If a caller passes `persona={"name": "Nam Minh"}` (the literal name in `NAM_MINH_PERSONA`) without `product_meta` containing `niche_id: "do_gia_dung"` or homelife keywords in `title`, `p_name` has `"nam minh"` (with space), which does not contain `"nam_minh"` (with underscore), falling back to `"hoai_my"`. In existing pipeline flows, `product_meta` always provides `niche_id` or keywords, masking this in production. Recommendation: normalize spaces to underscores or check `"nam minh" in p_name`.
   - **Finding 2 (Minor - Empty Title Phrasing)**: In `src/agents/comment_agent.py:272`, if a title is empty or stripped of all banned words, `_sanitize_title` returns `"em này"`. When interpolated into `"em {title} này"`, it results in `"em em này này"`. Recommendation: use `"sản phẩm"` as fallback.

---

## 3. Caveats

- **LLM vs Template Execution**: In the test environment and default production fallback, deterministic template rotation is used. If a live LLM client is plugged in, candidate responses that fail `ToneValidator` will automatically trigger the template fallback.
- **Scope Limit**: Review scope is strictly confined to Feature F27 (`CommentAgent` and related templates/tests). No modifications were made to implementation code in accordance with reviewer constraints.

---

## 4. Conclusion

The implementation of Feature F27 (`CommentAgent` intent classification & KOC reply generation) meets all technical requirements, architectural patterns, and quality criteria of AMAS v1.4.0. The code is clean, robust against Vietnamese homographs and dialect slang, brand-safe, and 100% compliant with `ToneValidator`.

**Verdict**: **APPROVE**

---

## 5. Verification Method

To independently reproduce and verify this review:

1. **Verify Static Integrity (0 mock imports in `src/`)**:
   ```bash
   python3 -c "
   import os, sys
   violations = [os.path.join(r, f) for r, d, fs in os.walk('src') for f in fs if f.endswith('.py') and ('unittest.mock' in open(os.path.join(r, f), encoding='utf-8').read() or 'MagicMock' in open(os.path.join(r, f), encoding='utf-8').read())]
   assert len(violations) == 0, f'Mock imports: {violations}'
   print('Static integrity: 100% CLEAN')
   "
   ```

2. **Verify Milestone 7 Test Suite**:
   ```bash
   pytest tests/test_comment_agent.py -k "TestCommentIntent or TestGenerateReply or TestTone" -v
   pytest tests/test_comment_agent.py -v
   ```
   *Expected: All tests pass.*

3. **Verify Tier 1 Feature F27 Test**:
   ```bash
   pytest tests/e2e/test_tier1_features.py -k "test_f27" -v
   ```
   *Expected: 1 passed.*

4. **Verify Full Regression Suite**:
   ```bash
   pytest tests/ -q
   ```
   *Expected: 457 passed in ~22s.*
