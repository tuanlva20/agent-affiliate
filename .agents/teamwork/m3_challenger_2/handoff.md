# Adversarial Stress Testing Handoff Report: Milestone 3 (HomeLifeScoutAgent & Prompt Templates)

**Agent ID**: `m3_challenger_2`  
**Milestone**: Milestone 3 (Specialist Scout Agents)  
**Roles**: critic, specialist  
**Working Directory**: `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m3_challenger_2/`  
**Date**: 2026-11-10T09:28:00Z  
**Verdict**: `REQUEST_CHANGES`  

---

## 1. Observation

### 1.1 Test Suite & Harness Execution Summary
- Existing Unit Tests: `pytest tests/test_specialist_scouts.py -v` -> **37 passed in 0.71s**
- Existing E2E Tests: `pytest tests/e2e/ -v` -> **61 passed in 1.41s**
- Dedicated Adversarial Harness: `python3 scripts/m3_homelife_adversarial_harness.py` -> **51 passed, 11 failed out of 62 test cases (82.3% pass rate)**

### 1.2 Verbatim Adversarial Failures
Command executed:
```bash
python3 scripts/m3_homelife_adversarial_harness.py
```

Breakdown by category:
- Category 1 (Exaggerated Claims Bypass): **11/20 passed (55.0% pass rate, 9 failed)**
- Category 2 (Pricing Boundaries): **9/11 passed (81.8% pass rate, 2 failed)**
- Category 3 (Score Threshold Boundaries): **3/3 passed (100.0% pass rate)**
- Category 4 (Hook & Viral Factor Validation): **14/14 passed (100.0% pass rate)**
- Category 5 (Corrupted Inputs & Concurrency): **14/14 passed (100.0% pass rate)**

Verbatim output for the 11 failed test cases:
```
FAILED: [1. Exaggerated Claims Bypass] bypass_synonym_shorthand_'ko'
   input: 'vĩnh viễn ko bám bẩn'
   expected: passed_filter=False, score=0.0, rejection_reason contains 'exaggerated'/'policy'
   actual: passed_filter=True, score=10.0, reason='None'

FAILED: [1. Exaggerated Claims Bypass] bypass_unaccented_'khong'
   input: 'vĩnh viễn khong bám bẩn'
   expected: passed_filter=False, score=0.0, rejection_reason contains 'exaggerated'/'policy'
   actual: passed_filter=True, score=10.0, reason='None'

FAILED: [1. Exaggerated Claims Bypass] bypass_underscore_separator
   input: 'thần_dược'
   expected: passed_filter=False, score=0.0, rejection_reason contains 'exaggerated'/'policy'
   actual: passed_filter=True, score=10.0, reason='None'

FAILED: [1. Exaggerated Claims Bypass] bypass_hyphen_separator
   input: 'thần-dược'
   expected: passed_filter=False, score=0.0, rejection_reason contains 'exaggerated'/'policy'
   actual: passed_filter=True, score=10.0, reason='None'

FAILED: [1. Exaggerated Claims Bypass] bypass_dot_separator
   input: 'thần.dược'
   expected: passed_filter=False, score=0.0, rejection_reason contains 'exaggerated'/'policy'
   actual: passed_filter=True, score=10.0, reason='None'

FAILED: [1. Exaggerated Claims Bypass] bypass_multi-space_separator
   input: 'trị   dứt   điểm   100%'
   expected: passed_filter=False, score=0.0, rejection_reason contains 'exaggerated'/'policy'
   actual: passed_filter=True, score=10.0, reason='None'

FAILED: [1. Exaggerated Claims Bypass] bypass_underscore_verb
   input: 'trị_dứt_điểm'
   expected: passed_filter=False, score=0.0, rejection_reason contains 'exaggerated'/'policy'
   actual: passed_filter=True, score=10.0, reason='None'

FAILED: [1. Exaggerated Claims Bypass] bypass_full_underscores
   input: 'vĩnh_viễn_không_bám_bẩn'
   expected: passed_filter=False, score=0.0, rejection_reason contains 'exaggerated'/'policy'
   actual: passed_filter=True, score=10.0, reason='None'

FAILED: [1. Exaggerated Claims Bypass] bypass_spaced_percent_lifetime
   input: '100 % không bao giờ hỏng'
   expected: passed_filter=False, score=0.0, rejection_reason contains 'exaggerated'/'policy'
   actual: passed_filter=True, score=10.0, reason='None'

FAILED: [2. Pricing Boundaries] nan_price
   input: price=nan
   expected: passed_filter=False, score=0.0, rejection_reason='Invalid product input'
   actual: passed_filter=True, score=9.7, reason='None'

FAILED: [2. Pricing Boundaries] pos_inf_price
   input: price=inf
   expected: passed_filter=False, score=0.0, rejection_reason='Invalid product input'
   actual: passed_filter=True, score=9.7, reason='None'
```

### 1.3 Inspection of Code Vulnerabilities
1. **`src/core/tone_validator.py` Lines 73-92 & 102-132**:
   - `EXAGGERATED_PATTERNS` relies on rigid single-space delimiters (e.g. `\bvĩnh viễn không bám bẩn\b`, `\bthần dược\b`, `\b100% không bao giờ hỏng\b`).
   - `_normalize()` only calls `unicodedata.normalize("NFC", text).lower()`. It does not normalize punctuation separators (`_`, `-`, `.`), does not collapse consecutive spaces (`\s+`), does not normalize common slang/abbreviations (`ko`, `khong` -> `không`), and does not permit variable whitespace before `%`.
   - As a consequence, malicious or careless sellers evading keyword filters with `thần_dược`, `vĩnh viễn ko bám bẩn`, or `trị   dứt   điểm` completely bypass `ToneValidator.check_violations()` and `ToneValidator.validate()`.

2. **`src/agents/homelife_scout.py` Lines 114-133**:
   - Numeric type check:
     ```python
     price = float(raw_dict.get("price") or raw_dict.get("price_vnd") or 0.0)
     comm_rate = float(raw_dict.get("commission_rate") or raw_dict.get("commission") or 0.0)
     sales_30d = int(raw_dict.get("sales_30d") or raw_dict.get("sales_7d") or raw_dict.get("sales_count") or raw_dict.get("sales") or 0)
     if price < 0 or comm_rate < 0 or sales_30d < 0:
         raise ValueError("Negative values not permitted")
     ```
   - For `price = float('nan')`: `nan < 0` is `False`.
   - For `price = float('inf')`: `inf < 0` is `False`.
   - Neither raises `ValueError`, allowing non-finite floats to bypass input validation and receive a passing score of 9.7 with `passed_filter=True`.

---

## 2. Logic Chain

1. **Policy Enforcement Invariant**:
   - Specification Requirement R1 & Feature F09 demand zero-tolerance filtering against exaggerated claims (medical claims, unverified permanent cleaning promises).
   - In `HomeLifeScoutAgent.evaluate_product`, filtering relies on `ToneValidator.check_violations(title)`.
   - When titles contain bypass variants explicitly specified in the testing instructions (`"vĩnh viễn ko bám bẩn"`, `"thần_dược"`, `"100 % không bao giờ hỏng"`, `"trị_dứt_điểm"`), `ToneValidator.check_violations` returns empty `[]`.
   - Because the product title has valid labor-saving keywords (`"tự vắt"`, `"3s"`), the agent awards a score of 10.0 and sets `passed_filter = True`.
   - Direct consequence: Unverified medical/permanent claim items are approved and sent downstream to the Telegram channel and Video Studio pipeline, creating an immediate account ban risk on TikTok Shop.

2. **Numeric Boundary Invariant**:
   - Product feeds from web scrapers or corrupted API responses can contain `NaN` or `Inf` floats.
   - The validation check `if price < 0` fails to guard against `math.isnan(price)` and `math.isinf(price)`.
   - Direct consequence: Malformed candidates with non-finite pricing are marked as approved with score 9.7, polluting database models and downstream video script prompts (`{price_vnd} VNĐ` rendering as `nan VNĐ` or `inf VNĐ`).

3. **Robust Areas Verified**:
   - Score boundaries around 8.5 correctly categorize products: product with minimal utility scores 8.4 (< 8.5), high-velocity utility product scores 8.6 (>= 8.5), and basic item scores 5.8 (< 7.0, rejected with threshold reason).
   - Generated hook angles and viral factors across cleaner, kitchen, and general categories strictly contain `"3s"` or `"nhàn"`, and `"3s"` or `"vắt khô"`.
   - ToneValidator validates all generated hook angles and confirms presence of natural KOC markers.
   - Corrupted inputs (`None`, `{}`, missing fields, string inputs, negative numbers) and concurrent execution of 120 parallel evaluations over 16 threads run safely with 100% success rate without memory corruption or race conditions.

---

## 3. Caveats

- **Scope of Review**: Adversarial testing focused on `HomeLifeScoutAgent` (F09), `ToneValidator`, and related prompt templates as dispatched. `FashionScoutAgent` was spot-checked for architectural symmetry.
- **Read-Only Constraint**: In strict adherence to the role constraints of `critic`, no production code was modified by this agent. All findings are empirically captured in `scripts/m3_homelife_adversarial_harness.py`.

---

## 4. Conclusion & Required Changes

### Explicit Verdict: `REQUEST_CHANGES`

Milestone 3 cannot be approved in its current state because it fails 11 empirical adversarial test cases, directly violating zero-tolerance policy enforcement and numeric validation contracts.

### Actionable Remediation Plan for Implementer:

1. **Enhance `src/core/tone_validator.py`**:
   - In `_normalize(cls, text: str) -> str`:
     - Normalize slang: replace `\bko\b` and `\bkhong\b` with `không`.
     - Replace punctuation separators `[_\-.]` with whitespace.
     - Collapse multiple consecutive whitespace characters `re.sub(r"\s+", " ", text)`.
   - Update `EXAGGERATED_PATTERNS` regexes:
     - `r"\btrị\s+dứt\s+điểm(\s*100\s*%)?\b"`
     - `r"\bvĩnh\s+viễn\s+(không|ko|khong)\s+bám\s+bẩn\b"`
     - `r"\bthần[\s_\-\.]+dược\b"`
     - `r"\b100\s*%\s*(không|ko|khong)\s+bao\s+giờ\s+hỏng\b"`
     - `r"\bvĩnh\s+viễn\s+(không|ko|khong)\s+hỏng\b"`
     - `r"\bvĩnh\s+viễn\s+(không|ko|khong)\s+(rỉ|gỉ)\s+sét\b"`

2. **Harden Numeric Validation in `src/agents/homelife_scout.py` (and `fashion_scout.py`)**:
   - In `evaluate_product`:
     ```python
     if (
         math.isnan(price) or math.isinf(price)
         or math.isnan(comm_rate) or math.isinf(comm_rate)
         or price < 0 or comm_rate < 0 or sales_30d < 0
     ):
         raise ValueError("Invalid numeric value: negative, NaN, or Inf not permitted")
     ```

---

## 5. Verification Method

To independently reproduce the empirical findings:

1. **Execute Adversarial Test Harness**:
   ```bash
   python3 scripts/m3_homelife_adversarial_harness.py
   ```
   *Current Result*: Exits with code 1, reporting 11 failed test cases (9 exaggerated claim leaks + 2 NaN/Inf pricing leaks).
   *Target Result after remediation*: Exits with code 0, 62/62 passed (100.0%).

2. **Verify Existing Suites**:
   ```bash
   pytest tests/test_specialist_scouts.py -v
   pytest tests/e2e/ -v
   ```
   *Expected Result*: 100% pass (ensures fixes do not cause regressions).
