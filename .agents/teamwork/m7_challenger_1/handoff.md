# Milestone 7 Adversarial Challenge Report (CommentScanner & CommentAgent)

**Agent**: `m7_challenger_1` (Role: Scanner & Intent Adversarial Challenger)  
**Parent Agent**: `f5177315-7404-4813-b8ba-56081885cdd4`  
**Working Directory**: `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m7_challenger_1/`  
**Target Components**: `src/services/comment_scanner.py`, `src/agents/comment_agent.py`  
**Harness Script**: `scripts/m7_adversarial_scanner_intent_harness.py`  
**Date**: 2026-11-10T17:05:00Z  
**Verdict**: **REQUEST_CHANGES**

---

## 1. Observation

### 1.1 Test Harness Execution & Verbatim Output
The standalone adversarial stress test harness was executed via:
```bash
python3 scripts/m7_adversarial_scanner_intent_harness.py
```
Exit code: `1` (Failed)

Verbatim terminal output summary:
```
======================================================================
AMAS Milestone 7 Adversarial Stress Harness (CommentScanner & CommentAgent)
Timestamp: 2026-11-10T17:02:49.001675+00:00
======================================================================

======================================================================
SUITE 1: CommentScanner Robustness, Boundaries, and Database Sync
======================================================================
  [PASS] Scanner-ExtremeInput :: Invalid Video ID (empty string) -> Correctly raised InvalidVideoIdError
  [PASS] Scanner-ExtremeInput :: Invalid Video ID (whitespace only) -> Correctly raised InvalidVideoIdError
  [PASS] Scanner-ExtremeInput :: Invalid Video ID (newline and tab) -> Correctly raised InvalidVideoIdError
  [PASS] Scanner-ExtremeInput :: Invalid Video ID (None type) -> Correctly raised InvalidVideoIdError
  [PASS] Scanner-ExtremeInput :: Invalid Video ID (integer type) -> Correctly raised InvalidVideoIdError
  [PASS] Scanner-ExtremeInput :: Invalid Video ID (float type) -> Correctly raised InvalidVideoIdError
  [PASS] Scanner-ExtremeInput :: Invalid Video ID (list type) -> Correctly raised InvalidVideoIdError
  [PASS] Scanner-ExtremeInput :: Invalid Video ID (dict type) -> Correctly raised InvalidVideoIdError
  [PASS] Scanner-ExtremeInput :: Unicode Emoji Video ID -> Returned 5 mock comments for emoji ID
  [PASS] Scanner-ExtremeInput :: Huge Video ID (5000 chars) -> Returned 3 comments without memory or processing failure
  [PASS] Scanner-ExtremeInput :: Full TikTok URL with Query Params -> Successfully extracted clean video ID and generated comments
  [PASS] Scanner-LimitBoundaries :: limit = 0 -> Requested limit=0, received len=0 (expected 0)
  [PASS] Scanner-LimitBoundaries :: limit = -1 -> Requested limit=-1, received len=0 (expected 0)
  [PASS] Scanner-LimitBoundaries :: limit = -100 -> Requested limit=-100, received len=0 (expected 0)
  [PASS] Scanner-LimitBoundaries :: limit = 1000 (stress) -> Requested limit=1000, received len=1000 (expected 1000)
  [PASS] Scanner-DB-Torture :: Malformed comments batch ingestion -> Ingested 5 valid records from 9 malformed entries (0 crashes)
  [PASS] Scanner-DB-Torture :: Intra-batch duplicate comment IDs -> Handled 20 duplicate entries with 4 unique keys without IntegrityError
  [PASS] Scanner-Concurrency :: 25 Concurrent scan_comments tasks -> Executed 25 scans (500 mock comments total) in 0.001s
  [PASS] Scanner-Concurrency :: 25 Concurrent sync_comments_to_db tasks -> Committed 500 records concurrently across 25 sessions in 0.191s

======================================================================
SUITE 2: CommentAgent.classify_intent Adversarial Stress & Homographs
======================================================================
  [FAIL] Intent-SlangTeenCode :: 'bnhiu z sop' -> Result: other (Expected: ask_price) — Teen code for 'bao nhiêu vậy shop' (Error: Misclassified as other)
  [PASS] Intent-SlangTeenCode :: 'mấy xèng' -> Result: ask_price (Expected: ask_price) — Slang for 'mấy tiền'
  [FAIL] Intent-SlangTeenCode :: 'rổ rá' -> Result: other (Expected: ask_price) — Colloquial idiom for price inquiry ('rổ rá thế nào') (Error: Misclassified as other)
  [PASS] Intent-SlangTeenCode :: 'vải gì dợ' -> Result: ask_material_usage (Expected: ask_material_usage) — Southern slang 'dợ' = 'vậy'
  [PASS] Intent-SlangTeenCode :: 'm7 50kg vừa hơm' -> Result: ask_material_usage (Expected: ask_material_usage) — Teen code 'hơm' = 'không'
  [PASS] Intent-SlangTeenCode :: 'đắt wa ko giống video' -> Result: complaint (Expected: complaint) — Teen code 'wa' = 'quá', 'ko' = 'không'
  [PASS] Intent-SlangTeenCode :: 'shop lừa à' -> Result: complaint (Expected: complaint) — Scam complaint
  [FAIL] Intent-SlangTeenCode :: 'bn z shop' -> Result: other (Expected: ask_price) — Teen code abbreviation 'bn' = 'bao nhiêu' (Error: Misclassified as other)
  [FAIL] Intent-SlangTeenCode :: 'bnhieu vậy' -> Result: other (Expected: ask_price) — Teen code 'bnhieu' = 'bao nhiêu' (Error: Misclassified as other)
  [PASS] Intent-SlangTeenCode :: 'inbox giá em này' -> Result: ask_price (Expected: ask_price) — Direct price inquiry via inbox
  [PASS] Intent-Homographs :: 'bung 75 mac vua k' -> Result: ask_material_usage (Expected: ask_material_usage) — Unaccented 'bung' = waist 75cm
  [PASS] Intent-Homographs :: 'bụng to mặc vừa không' -> Result: ask_material_usage (Expected: ask_material_usage) — Accented waist query
  [PASS] Intent-Homographs :: 'bung chỉ rồi shop' -> Result: complaint (Expected: complaint) — Accented defect 'bung chỉ'
  [PASS] Intent-Homographs :: 'ao bi bung chi' -> Result: complaint (Expected: complaint) — Unaccented defect 'bung chi'
  [PASS] Intent-Homographs :: 'giao lau qua' -> Result: complaint (Expected: complaint) — Unaccented delivery delay 'giao lâu'
  [PASS] Intent-Homographs :: 'ship lau qua sop' -> Result: complaint (Expected: complaint) — Unaccented shipping delay 'ship lâu'
  [PASS] Intent-Homographs :: 'cay lau nha dung sao' -> Result: ask_material_usage (Expected: ask_material_usage) — Unaccented home utility 'cây lau nhà'
  [PASS] Intent-Homographs :: 'cay lau nha thong minh nay dung the nao' -> Result: ask_material_usage (Expected: ask_material_usage) — Smart mop usage inquiry
  [PASS] Intent-Homographs :: 'vai lua nay mac mat ko' -> Result: ask_material_usage (Expected: ask_material_usage) — Unaccented silk fabric 'vải lụa'
  [PASS] Intent-Homographs :: 'vai lua mac mua he vua k' -> Result: ask_material_usage (Expected: ask_material_usage) — Silk fabric summer fit
  [PASS] Intent-Homographs :: 'shop lua dao a' -> Result: complaint (Expected: complaint) — Unaccented scam complaint 'lừa đảo'
  [PASS] Intent-Homographs :: 'lua dao tien khach' -> Result: complaint (Expected: complaint) — Scamming money complaint
  [PASS] Intent-Homographs :: 'chat co gian hong shop' -> Result: ask_material_usage (Expected: ask_material_usage) — Southern question 'hong' = 'không'
  [PASS] Intent-Homographs :: 'váy này hỏng rồi' -> Result: complaint (Expected: complaint) — Accented broken item 'hỏng rồi'
  [PASS] Intent-Homographs :: 'ao bi hong khoa' -> Result: complaint (Expected: complaint) — Unaccented broken zipper 'bi hong'
  [PASS] Intent-Homographs :: 'hang hong roi' -> Result: complaint (Expected: complaint) — Unaccented broken item 'hang hong'
  [PASS] Intent-MultiPriority :: 'áo rách rồi, giá thì đắt mà ship lâu quá' -> Result: complaint (Expected: complaint) — Triple signal: defect + price + delay
  [PASS] Intent-MultiPriority :: 'vay bao nhieu ma ship lau the shop' -> Result: complaint (Expected: complaint) — Dual signal: price question + delivery delay
  [PASS] Intent-MultiPriority :: 'size M mac vua ko shop oi sao giao hang cham the' -> Result: complaint (Expected: complaint) — Dual signal: size query + slow shipping
  [FAIL] Intent-MultiPriority :: 'vải xấu quá mà giá đắt' -> Result: ask_material_usage (Expected: complaint) — Dual signal: bad fabric + price complaint (Error: Safety violation! Did not prioritize COMPLAINT, returned ask_material_usage)
  [FAIL] Intent-MultiPriority :: 'chất vải xấu mà giá đắt thế' -> Result: ask_material_usage (Expected: complaint) — Dual signal: bad fabric + high price (Error: Safety violation! Did not prioritize COMPLAINT, returned ask_material_usage)
  [FAIL] Intent-MultiPriority :: 'chất xấu như giẻ lau' -> Result: ask_material_usage (Expected: complaint) — Defect signal: extremely bad fabric (Error: Safety violation! Did not prioritize COMPLAINT, returned ask_material_usage)
  [FAIL] Intent-MultiPriority :: 'vải đểu thế mà bán 200k' -> Result: ask_material_usage (Expected: complaint) — Dual signal: counterfeit/fake fabric + price (Error: Safety violation! Did not prioritize COMPLAINT, returned ask_material_usage)
  [FAIL] Intent-MultiPriority :: 'hàng xấu vải mỏng tang' -> Result: ask_material_usage (Expected: complaint) — Dual signal: bad quality + transparent fabric (Error: Safety violation! Did not prioritize COMPLAINT, returned ask_material_usage)
  [PASS] Intent-MultiPriority :: 'đắt wa ko giống video' -> Result: complaint (Expected: complaint) — Dual signal: expensive + misleading video
  [PASS] Intent-FalsePositiveGuards :: 'đánh giá 5 sao' -> Result: other (Expected: other) — Review rating (not asking price)
  [PASS] Intent-FalsePositiveGuards :: 'giá như biết sớm' -> Result: other (Expected: other) — Idiom 'giá như' = 'wish that'
  [PASS] Intent-FalsePositiveGuards :: 'cái giá treo quần áo này' -> Result: other (Expected: other) — Utility item noun 'giá treo' without price question
  [PASS] Intent-FalsePositiveGuards :: 'cai gia de do nay bao tien' -> Result: ask_price (Expected: ask_price) — Utility noun WITH explicit price question 'bao tien'
  [PASS] Intent-FalsePositiveGuards :: 'gia nhu e biet shop som hon' -> Result: other (Expected: other) — Idiom 'giá như em biết shop sớm hơn'
  [PASS] Intent-FalsePositiveGuards :: 'danh gia 5 sao cho shop nhe' -> Result: other (Expected: other) — Review rating 'đánh giá 5 sao'
  [PASS] Intent-FalsePositiveGuards :: 'vay dep gia re qua shop oi' -> Result: other (Expected: other) — Compliment 'giá rẻ' (not asking price)

======================================================================
SUITE 3: Crash Resilience, Malformed Types & Tone Compliance
======================================================================
  [PASS] Resilience-ClassifyIntent :: Input (None type) -> Handled safely without crash, returned other
  [PASS] Resilience-ClassifyIntent :: Input (Empty string) -> Handled safely without crash, returned other
  [PASS] Resilience-ClassifyIntent :: Input (Whitespace string) -> Handled safely without crash, returned other
  [PASS] Resilience-ClassifyIntent :: Input (Newline/Tab string) -> Handled safely without crash, returned other
  [PASS] Resilience-ClassifyIntent :: Input (Integer type) -> Handled safely without crash, returned other
  [PASS] Resilience-ClassifyIntent :: Input (Float type) -> Handled safely without crash, returned other
  [PASS] Resilience-ClassifyIntent :: Input (List type) -> Handled safely without crash, returned other
  [PASS] Resilience-ClassifyIntent :: Input (Dict type) -> Handled safely without crash, returned other
  [PASS] Resilience-ClassifyIntent :: Input (Boolean True) -> Handled safely without crash, returned other
  [PASS] Resilience-ClassifyIntent :: Input (Boolean False) -> Handled safely without crash, returned other
  [PASS] Resilience-ClassifyIntent :: Input (20,000 Unicode Emojis) -> Handled safely without crash, returned other
  [PASS] Resilience-ClassifyIntent :: Input (50,000 ASCII chars) -> Handled safely without crash, returned other
  [PASS] Resilience-ClassifyIntent :: Input (Control/Binary bytes decoded) -> Handled safely without crash, returned other
  [PASS] Resilience-GenerateReply :: Zero Crashes on Malformed Metas/Personas -> Executed 168 matrix combinations with 0 crashes
  [PASS] Resilience-ToneValidator :: 100% ToneValidator Compliance Guarantee -> 0 tone violations across 168 reply generations
  [PASS] Resilience-TitleSanitization :: Banned Brand & Policy Leak Prevention -> All counterfeit brands and policy violations sanitized from replies

======================================================================
FINAL ADVERSARIAL STRESS TEST SUMMARY
======================================================================
Total Tests Run: 77
Passed:          68 (88.3%)
Failed:          9 (11.7%)

FAILURE BREAKDOWN:
- [Intent-SlangTeenCode] 'bnhiu z sop': Result: other (Expected: ask_price) — Teen code for 'bao nhiêu vậy shop' | Error: Misclassified as other
- [Intent-SlangTeenCode] 'rổ rá': Result: other (Expected: ask_price) — Colloquial idiom for price inquiry ('rổ rá thế nào') | Error: Misclassified as other
- [Intent-SlangTeenCode] 'bn z shop': Result: other (Expected: ask_price) — Teen code abbreviation 'bn' = 'bao nhiêu' | Error: Misclassified as other
- [Intent-SlangTeenCode] 'bnhieu vậy': Result: other (Expected: ask_price) — Teen code 'bnhieu' = 'bao nhiêu' | Error: Misclassified as other
- [Intent-MultiPriority] 'vải xấu quá mà giá đắt': Result: ask_material_usage (Expected: complaint) — Dual signal: bad fabric + price complaint | Error: Safety violation! Did not prioritize COMPLAINT, returned ask_material_usage
- [Intent-MultiPriority] 'chất vải xấu mà giá đắt thế': Result: ask_material_usage (Expected: complaint) — Dual signal: bad fabric + high price | Error: Safety violation! Did not prioritize COMPLAINT, returned ask_material_usage
- [Intent-MultiPriority] 'chất xấu như giẻ lau': Result: ask_material_usage (Expected: complaint) — Defect signal: extremely bad fabric | Error: Safety violation! Did not prioritize COMPLAINT, returned ask_material_usage
- [Intent-MultiPriority] 'vải đểu thế mà bán 200k': Result: ask_material_usage (Expected: complaint) — Dual signal: counterfeit/fake fabric + price | Error: Safety violation! Did not prioritize COMPLAINT, returned ask_material_usage
- [Intent-MultiPriority] 'hàng xấu vải mỏng tang': Result: ask_material_usage (Expected: complaint) — Dual signal: bad quality + transparent fabric | Error: Safety violation! Did not prioritize COMPLAINT, returned ask_material_usage

VERDICT: REQUEST_CHANGES
```

---

## 2. Logic Chain

### 2.1 Robustness of `CommentScanner` (Suite 1: 19/19 Passed, 100%)
- `CommentScanner` safely handles all tested extreme inputs: empty string, whitespace, null types, integers, floats, dicts, lists (raising `InvalidVideoIdError`), emojis, and 5000-char strings.
- Limit boundaries `limit=0`, `limit=-1`, `limit=-100` correctly return `[]`.
- Stress limit `limit=1000` returns 1000 mock comments with unique keys.
- In `sync_comments_to_db` (`src/services/comment_scanner.py:364-440`), malformed records (missing keys, `NaN`/`Inf`/overflow timestamps) are gracefully parsed by `parse_timestamp` to UTC `datetime.now(timezone.utc)`.
- Intra-batch duplicate comments (20 duplicate items with 4 distinct keys) are properly deduplicated in memory via `existing_map` before the SQLite session flush, preventing primary key violations.
- Concurrency test (25 concurrent scans and 25 concurrent database sync transactions) finished in <0.2s with 0 lock errors or data corruption.
- **Scanner assessment**: Clean and solid.

### 2.2 Defect 1: Slang & Teen Code Price Inquiries Misclassified as `OTHER` (4 Failures)
- **Observations**:
  - `'bnhiu z sop'` -> `CommentIntent.OTHER` (Expected: `CommentIntent.ASK_PRICE`)
  - `'rổ rá'` -> `CommentIntent.OTHER` (Expected: `CommentIntent.ASK_PRICE`)
  - `'bn z shop'` -> `CommentIntent.OTHER` (Expected: `CommentIntent.ASK_PRICE`)
  - `'bnhieu vậy'` -> `CommentIntent.OTHER` (Expected: `CommentIntent.ASK_PRICE`)
- **Code Inspection** (`src/agents/comment_agent.py:168-179`):
  ```python
  raw_prices = [
      r"\b(giá|gia)\s*(bao nhiêu|nhiêu|bao tiền|mấy tiền|mấy đồng|thế nào|sao|ntn|bn|bnh|bnhieu|bnhiu|nhiu)\b", # (1)
      ...
      r"\brổ\s+giá\b", # (2)
      ...
      r"\b(giá|nhiêu|nhiu|bn|bnhieu)\s*(\?|\!|\.|\s)*$", # (3)
      r"^\s*(giá|nhiêu|nhiu|bao nhiêu|bao tiền|bn|bnh|bnhieu)\s*(\?|\!|\.|\s)*$", # (4)
      r"\b(nhiêu|nhiu)\s+(ạ|thế|vậy|shop|sop|v|z|hả)\b", # (5)
  ]
  ```
  1. Pattern (5) only includes `(nhiêu|nhiu)`. It completely omits teen code abbreviations `(bnhiu|bnhieu|bn|bao nhiêu)`.
  2. Because word boundaries are applied (`\b(nhiêu|nhiu)\b`), `bnhiu` fails to match because `b` precedes `nhiu`.
  3. Pattern (1) requires the keyword prefix `giá` or `gia`. Teenagers rarely write `"giá bnhiu z sop"`; they write `"bnhiu z sop"`.
  4. Patterns (3) and (4) require end-of-string `$`. In `'bnhiu z sop'` and `'bn z shop'`, the words `z sop` / `z shop` follow the price term, so the regex fails to match.
  5. Pattern (2) checks `r"\brổ\s+giá\b"`, but Vietnamese colloquial slang specifically uses `"rổ rá"` (literally basket, idiom for price, e.g. "cho em xin rổ rá em này").
- **Business Impact**: Missing teen code price inquiries prevents the conversion bot from delivering the product discount and yellow cart voucher CTA, leaking potential revenue on TikTok Shop.

### 2.3 Defect 2: Critical Brand Safety Failure — Complaints Misclassified as `ASK_MATERIAL_USAGE` (5 Failures)
- **Observations**:
  - `'vải xấu quá mà giá đắt'` -> `CommentIntent.ASK_MATERIAL_USAGE` (Expected: `CommentIntent.COMPLAINT`)
  - `'chất vải xấu mà giá đắt thế'` -> `CommentIntent.ASK_MATERIAL_USAGE` (Expected: `CommentIntent.COMPLAINT`)
  - `'chất xấu như giẻ lau'` -> `CommentIntent.ASK_MATERIAL_USAGE` (Expected: `CommentIntent.COMPLAINT`)
  - `'vải đểu thế mà bán 200k'` -> `CommentIntent.ASK_MATERIAL_USAGE` (Expected: `CommentIntent.COMPLAINT`)
  - `'hàng xấu vải mỏng tang'` -> `CommentIntent.ASK_MATERIAL_USAGE` (Expected: `CommentIntent.COMPLAINT`)
- **Code Inspection** (`src/agents/comment_agent.py:136-165, 186-208`):
  1. In `_complaint_res`, the patterns detect broken parts (`rách`, `hỏng`, `lỗi`, `bung chỉ`), delivery delays (`ship lâu`, `giao chậm`), and scams (`lừa đảo`, `treo đầu dê`).
  2. However, poor quality/defect vocabulary is extremely narrow: only `chất lượng (kém|tệ)` and `hàng đểu|hàng dỏm`.
  3. Crucial Vietnamese defect terms are completely missing:
     - `xấu`, `quá xấu`, `vải xấu`, `chất xấu`, `hàng xấu`
     - `vải đểu`, `đồ đểu`, `vải dỏm`, `đồ dỏm`
     - `mỏng dính`, `mỏng tang`, `như giẻ lau`, `như giẻ rách`
  4. Because the comment fails to match any complaint regex, it bypasses the `COMPLAINT` stage in `classify_intent` (lines 236-239).
  5. It then reaches `ASK_MATERIAL_USAGE` (lines 257-259), where `r"\b(chất|chất liệu|chất vải|vải)\b"` triggers a match on the word `vải` or `chất`.
  6. The comment is tagged as `ASK_MATERIAL_USAGE`.
- **Downstream Behavior in `generate_reply`**:
  - When classified as `ASK_MATERIAL_USAGE`, `CommentAgent.generate_reply()` selects from `FASHION_ASK_MATERIAL_TEMPLATES`:
    *"Dạ chất vải đũi may 2 lớp cực mát, form che bụng đỉnh chóp luôn chị ạ. Chị chọn size theo bảng trong giỏ hàng vàng nha!"*
  - **Severe Brand Hazard**: Sending a cheerful promotional reply praising the fabric and urging purchase from the yellow cart to an angry customer complaining that "chất vải xấu mà giá đắt thế" makes the channel look tone-deaf, scammy, and automated.
  - This directly violates the brand safety guarantee: *"Strict Priority: COMPLAINT strictly trumps both ASK_PRICE and ASK_MATERIAL_USAGE (critical brand safety guard against promoting products to angry customers)."*

### 2.4 Homograph Protection & False-Positive Guards (23/23 Passed, 100%)
- Homograph pairs (`bụng` vs `bung chỉ`, `lâu` vs `lau nhà`, `lụa` vs `lừa đảo`, `hong` vs `hỏng`) successfully resolved without cross-contamination.
- False positive guards (`đánh giá 5 sao`, `giá như biết sớm`, `cái giá treo`) correctly prevented false triggers of `ASK_PRICE`.
- Crash resilience on malformed inputs and 100% ToneValidator compliance passed.

---

## 3. Caveats

- **Mock vs Live TikTok API**: Test harness verified hermetic mock and local logic. Live network requests to `https://www.tiktok.com/api/comment/list/` were not run against live endpoints to avoid external IP bans and maintain hermetic test isolation.
- **LLM-Free Deterministic Verification**: Verification was conducted using deterministic regex rules and template fallback paths to guarantee 100% reproducible empirical evidence.

---

## 4. Conclusion

- Feature F26 (`CommentScanner`) is **ROBUST** and ready for production: 100% boundary compliance, 0 crashes on extreme inputs, clean concurrency, and reliable intra-batch deduplication.
- Feature F27 (`CommentAgent.classify_intent`) has **TWO CRITICAL DEFECTS**:
  1. **Teen Code & Slang Conversion Leakage**: Fails to detect `bnhiu z sop`, `rổ rá`, `bn z shop`, `bnhieu vậy`, classifying them as `OTHER` and missing yellow cart conversion opportunities.
  2. **Brand Safety Defect (Mixed Signal & Quality Complaints)**: Comments complaining of bad fabric/quality (`vải xấu quá mà giá đắt`, `chất xấu như giẻ lau`, `vải đểu thế mà bán 200k`, `hàng xấu vải mỏng tang`) falsely trigger `ASK_MATERIAL_USAGE`, prompting cheerful sales pitches to disgruntled buyers.

**Verdict**: **REQUEST_CHANGES**

### Required Action Items for Implementer (`worker_m7_2` / developer):
1. **Extend Slang & Teen Code Price Patterns in `src/agents/comment_agent.py`**:
   - In `raw_prices`, update the question pattern:
     ```python
     r"\b(nhiêu|nhiu|bnhiu|bnhieu|bn|bao nhiêu)\s+(ạ|thế|vậy|shop|sop|v|z|hả)\b"
     ```
   - In `raw_prices`, support `rổ rá`:
     ```python
     r"\brổ\s+(giá|rá)\b"
     ```
   - Support standalone prefix questions:
     ```python
     r"\b(bn|bnhiu|bnhieu)\b\s*(\?|\!|\.|\s)*$"
     ```
2. **Extend Complaint Patterns for Fabric & Quality Defects in `src/agents/comment_agent.py`**:
   - In `raw_complaints`, add fabric defect and poor quality patterns:
     ```python
     r"\b(xấu|quá xấu|tệ quá|dở quá|đểu|dỏm)\b",
     r"\b(vải|chất|hàng|áo|váy)\s*(xấu|đểu|dỏm|kém|tệ|mỏng tang|mỏng dính|nhăn nhúm)\b",
     r"\b(như giẻ|giẻ lau|giẻ rách)\b",
     r"\b(đắt|mắc)\s*(quá|qua|wa|thế)\b",
     ```
   - Ensure these complaint patterns run before `ASK_MATERIAL_USAGE` so that complaints about fabric quality are prioritized as `CommentIntent.COMPLAINT`.

---

## 5. Verification Method

To independently verify these findings:

1. **Execute the Standalone Adversarial Stress Harness**:
   ```bash
   python3 scripts/m7_adversarial_scanner_intent_harness.py
   ```
   *Expected Current Output: Exit code 1 with 9 test failures listed above.*

2. **Verify Remediation Invalidation Condition**:
   Once the implementer applies the regex updates, re-running:
   ```bash
   python3 scripts/m7_adversarial_scanner_intent_harness.py
   ```
   *Must exit with code 0 and report: `Passed: 77 (100.0%)`, `Failed: 0 (0.0%)`, `VERDICT: APPROVE`.*
