# Milestone 7 (Comment Engagement & Conversion Agent: Features F26 & F27) Handoff Report

**Agent**: `worker_m7_2` (Roles: implementer, qa, specialist)  
**Parent Agent**: `f5177315-7404-4813-b8ba-56081885cdd4`  
**Working Directory**: `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/worker_m7_2/`  
**Milestone**: Milestone 7 (F26 CommentScanner & F27 CommentAgent)  
**Date**: 2026-11-10T16:56:00Z  

---

## 1. Observation

### 1.1 Inherited State from Predecessor `worker_m7_1`
- `worker_m7_1` had drafted `tests/test_comment_agent.py`, `src/services/comment_scanner.py`, `src/agents/comment_agent.py`, and `src/core/prompt_templates.py` before crashing due to a network interruption.
- Initial test execution (`pytest tests/test_comment_agent.py -v`) revealed 4 failing tests out of 63:
  1. `TestCommentScanner.test_sync_comments_to_db_idempotency` failed with `TypeError: 'tier1_target' is an invalid keyword argument for Niche`.
  2. `TestCommentScanner.test_sync_comments_to_db_intra_batch_dups` failed with `TypeError: 'tier1_target' is an invalid keyword argument for Niche`.
  3. `TestCommentIntentClassification.test_partition_cases["chất co giãn hong shop"]` failed because unaccented `hong` collided with `hỏng` in the unaccented complaint regex, falsely returning `CommentIntent.COMPLAINT` instead of `CommentIntent.ASK_MATERIAL_USAGE`.
  4. `TestDatabaseIntegration.test_video_comment_lifecycle_in_database` failed with `IntegrityError: NOT NULL constraint failed: products.product_url` and subsequently `NOT NULL constraint failed: video_jobs.niche_id`.
- Re-exports in `src/services/__init__.py` (for `CommentScanner` and custom exceptions) and `src/agents/__init__.py` (for `CommentAgent` and `CommentIntent`) were missing.

### 1.2 Verification Commands & Verbatim Outputs

#### A. Static Integrity Verification (0 occurrences of `unittest.mock` and zero dummy bypass flags in `src/`)
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

if violations:
    print('Integrity violations found:', violations)
    sys.exit(1)
else:
    print('Static Integrity Check: 100% CLEAN. Zero mock imports and zero dummy bypass flags in src/')
"
```
Output:
```
Static Integrity Check: 100% CLEAN. Zero mock imports and zero dummy bypass flags in src/
```

#### B. Milestone 7 Unit Test Suite (`pytest tests/test_comment_agent.py -v`)
```
============================= test session starts ==============================
platform darwin -- Python 3.12.2, pytest-9.2.0, pluggy-1.7.0 -- /Library/Frameworks/Python.framework/Versions/3.12/bin/python3
cachedir: .pytest_cache
rootdir: /Users/tuanlva/Folder/workSpace/affiliate
configfile: pytest.ini
plugins: asyncio-1.4.1.post1
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
collecting ... collected 63 items

tests/test_comment_agent.py::TestCommentScanner::test_scan_comments_f26_contract PASSED [  1%]
tests/test_comment_agent.py::TestCommentScanner::test_scan_comments_limit_partitions PASSED [  3%]
tests/test_comment_agent.py::TestCommentScanner::test_scan_comments_url_extraction PASSED [  4%]
tests/test_comment_agent.py::TestCommentScanner::test_scan_comments_invalid_ids PASSED [  6%]
tests/test_comment_agent.py::TestCommentScanner::test_scan_comments_mock_deterministic PASSED [  7%]
tests/test_comment_agent.py::TestCommentScanner::test_scan_comments_live_api_success PASSED [  9%]
tests/test_comment_agent.py::TestCommentScanner::test_scan_comments_live_rate_limit PASSED [ 11%]
tests/test_comment_agent.py::TestCommentScanner::test_scan_comments_live_rate_limit_fallback PASSED [ 12%]
tests/test_comment_agent.py::TestCommentScanner::test_scan_comments_timeout PASSED [ 14%]
tests/test_comment_agent.py::TestCommentScanner::test_sync_comments_to_db_idempotency PASSED [ 15%]
tests/test_comment_agent.py::TestCommentScanner::test_sync_comments_to_db_intra_batch_dups PASSED [ 17%]
tests/test_comment_agent.py::TestCommentScanner::test_sync_comments_to_db_invalid_channel PASSED [ 19%]
tests/test_comment_agent.py::TestCommentIntentClassification::test_tier1_contract_comments PASSED [ 20%]
tests/test_comment_agent.py::TestCommentIntentClassification::test_partition_cases[Váy này bao tiền thế?-ask_price] PASSED [ 22%]
tests/test_comment_agent.py::TestCommentIntentClassification::test_partition_cases[nhiu xien vay shop-ask_price] PASSED [ 23%]
tests/test_comment_agent.py::TestCommentIntentClassification::test_partition_cases[gia bn sop-ask_price] PASSED [ 25%]
tests/test_comment_agent.py::TestCommentIntentClassification::test_partition_cases[inbox gia giup minh-ask_price] PASSED [ 26%]
tests/test_comment_agent.py::TestCommentIntentClassification::test_partition_cases[ro gia the nao shop-ask_price] PASSED [ 28%]
tests/test_comment_agent.py::TestCommentIntentClassification::test_partition_cases[bao nhieu a-ask_price] PASSED [ 30%]
tests/test_comment_agent.py::TestCommentIntentClassification::test_partition_cases[cai gia de do nay bao tien-ask_price] PASSED [ 31%]
tests/test_comment_agent.py::TestCommentIntentClassification::test_partition_cases[mấy củ vậy-ask_price] PASSED [ 33%]
tests/test_comment_agent.py::TestCommentIntentClassification::test_partition_cases[mấy đồng shop ơi-ask_price] PASSED [ 34%]
tests/test_comment_agent.py::TestCommentIntentClassification::test_partition_cases[m7 60kg mặc sz gì-ask_material_usage] PASSED [ 36%]
tests/test_comment_agent.py::TestCommentIntentClassification::test_partition_cases[55 cân vừa k shop-ask_material_usage] PASSED [ 38%]
tests/test_comment_agent.py::TestCommentIntentClassification::test_partition_cases[bung 75 mac vua k-ask_material_usage] PASSED [ 39%]
tests/test_comment_agent.py::TestCommentIntentClassification::test_partition_cases[chat vai dui hay cotton vay-ask_material_usage] PASSED [ 41%]
tests/test_comment_agent.py::TestCommentIntentClassification::test_partition_cases[cay lau nha thong minh nay dung the nao-ask_material_usage] PASSED [ 42%]
tests/test_comment_agent.py::TestCommentIntentClassification::test_partition_cases[cai gia treo nay lap kieu gi-ask_material_usage] PASSED [ 44%]
tests/test_comment_agent.py::TestCommentIntentClassification::test_partition_cases[váy này mặc vừa khum shop-ask_material_usage] PASSED [ 46%]
tests/test_comment_agent.py::TestCommentIntentClassification::test_partition_cases[chất co giãn hong shop-ask_material_usage] PASSED [ 47%]
tests/test_comment_agent.py::TestCommentIntentClassification::test_partition_cases[cao 1m58 nang 48kg mac size nao-ask_material_usage] PASSED [ 49%]
tests/test_comment_agent.py::TestCommentIntentClassification::test_partition_cases[chan vay dai den dau the-ask_material_usage] PASSED [ 50%]
tests/test_comment_agent.py::TestCommentIntentClassification::test_partition_cases[hang loi rach roi doi tra the nao-complaint] PASSED [ 52%]
tests/test_comment_agent.py::TestCommentIntentClassification::test_partition_cases[shop lua dao a-complaint] PASSED [ 53%]
tests/test_comment_agent.py::TestCommentIntentClassification::test_partition_cases[dat 2 tuan ma chua nhan duoc hang-complaint] PASSED [ 55%]
tests/test_comment_agent.py::TestCommentIntentClassification::test_partition_cases[giao sai mau roi shop oi-complaint] PASSED [ 57%]
tests/test_comment_agent.py::TestCommentIntentClassification::test_partition_cases[vai xau khong giong hinh-complaint] PASSED [ 58%]
tests/test_comment_agent.py::TestCommentIntentClassification::test_partition_cases[ship lau qua shop oi-complaint] PASSED [ 60%]
tests/test_comment_agent.py::TestCommentIntentClassification::test_partition_cases[hang ko giong video-complaint] PASSED [ 61%]
tests/test_comment_agent.py::TestCommentIntentClassification::test_partition_cases[gia nhu e biet shop som hon-other] PASSED [ 63%]
tests/test_comment_agent.py::TestCommentIntentClassification::test_partition_cases[danh gia 5 sao cho shop nhe-other] PASSED [ 65%]
tests/test_comment_agent.py::TestCommentIntentClassification::test_partition_cases[vay dep gia re qua shop oi-other] PASSED [ 66%]
tests/test_comment_agent.py::TestCommentIntentClassification::test_partition_cases[chấm-other] PASSED [ 68%]
tests/test_comment_agent.py::TestCommentIntentClassification::test_partition_cases[haha cute qua-other] PASSED [ 69%]
tests/test_comment_agent.py::TestCommentIntentClassification::test_partition_cases[-other] PASSED [ 71%]
tests/test_comment_agent.py::TestCommentIntentClassification::test_partition_cases[   -other] PASSED [ 73%]
tests/test_comment_agent.py::TestCommentIntentClassification::test_partition_cases[...-other] PASSED [ 74%]
tests/test_comment_agent.py::TestCommentIntentClassification::test_partition_cases[🥰🥰🥰-other] PASSED [ 76%]
tests/test_comment_agent.py::TestCommentIntentClassification::test_complaint_trumps_price PASSED [ 77%]
tests/test_comment_agent.py::TestCommentIntentClassification::test_complaint_trumps_material PASSED [ 79%]
tests/test_comment_agent.py::TestGenerateReplyFashion::test_fashion_ask_price_reply PASSED [ 80%]
tests/test_comment_agent.py::TestGenerateReplyFashion::test_fashion_ask_material_reply PASSED [ 82%]
tests/test_comment_agent.py::TestGenerateReplyFashion::test_fashion_complaint_reply PASSED [ 84%]
tests/test_comment_agent.py::TestGenerateReplyFashion::test_fashion_other_reply PASSED [ 85%]
tests/test_comment_agent.py::TestGenerateReplyHomeLife::test_homelife_ask_price_reply PASSED [ 87%]
tests/test_comment_agent.py::TestGenerateReplyHomeLife::test_homelife_ask_material_reply PASSED [ 88%]
tests/test_comment_agent.py::TestGenerateReplyHomeLife::test_homelife_complaint_reply PASSED [ 90%]
tests/test_comment_agent.py::TestGenerateReplyHomeLife::test_homelife_other_reply PASSED [ 92%]
tests/test_comment_agent.py::TestToneValidatorGuarantee::test_100_percent_matrix_tone_compliance PASSED [ 93%]
tests/test_comment_agent.py::TestToneValidatorGuarantee::test_dirty_product_title_sanitization_in_reply PASSED [ 95%]
tests/test_comment_agent.py::TestDatabaseIntegration::test_video_comment_lifecycle_in_database PASSED [ 96%]
tests/test_comment_agent.py::TestLLMIntegrationAndFallback::test_generate_reply_with_mock_llm_success PASSED [ 98%]
tests/test_comment_agent.py::TestLLMIntegrationAndFallback::test_generate_reply_llm_robotic_fallback_to_template PASSED [100%]

============================== 63 passed in 1.11s ==============================
```

#### C. Full Repository Regression Suite (`pytest tests/ -v`)
```
============================= 457 passed in 21.47s =============================
```

---

## 2. Logic Chain

### 2.1 Feature F26: `CommentScanner` Implementation (`src/services/comment_scanner.py`)
- **Dual-Mode Operation**:
  - `mock_mode=True` (default when `COMMENT_SCANNER_MOCK` != `false`): Generates deterministic, high-fidelity mock comments with keys: `comment_id`, `text`, `user`, `author_name`, `author_id`, `timestamp`, `like_count`, `reply_count`.
  - `mock_mode=False`: Hits the live TikTok Web comment endpoint `https://www.tiktok.com/api/comment/list/` with timeout safeguards (`asyncio.timeout(self.timeout)`), exponential backoff rate limit retry on HTTP 429 / status_code 10101, and raises `CommentRateLimitError`, `CommentScannerTimeoutError`, or `VideoNotFoundError`.
  - Optional `fallback_to_mock=True` provides resilient fallback to mock comments when live API fails.
- **Idempotent DB Synchronization (`sync_comments_to_db`)**:
  - Filters and queries existing records by `comment_id.in_(...)`.
  - Existing records are preserved (retaining `reply_status`, `reply_text`, and `intent`).
  - New records are instantiated as `VideoComment` ORM objects with `reply_status='pending'`, mapped accurately to `author_id`, `author_name`, `comment_text`, and parsed UTC timestamp.
  - Dedupes intra-batch comments in memory (`existing_map`) before flushing to prevent primary key collision.
- **Complete Exception Hierarchy**:
  - `CommentScannerError(Exception)`
  - `InvalidVideoIdError(ValueError, CommentScannerError)`
  - `CommentScannerTimeoutError(TimeoutError, CommentScannerError)`
  - `CommentRateLimitError(CommentScannerError)`
  - `VideoNotFoundError(CommentScannerError)`

### 2.2 Feature F27: `CommentAgent` & `CommentIntent` (`src/agents/comment_agent.py`)
- **`CommentIntent` Enum**:
  - `ASK_PRICE = "ask_price"`
  - `ASK_MATERIAL_USAGE = "ask_material_usage"`
  - `COMPLAINT = "complaint"`
  - `OTHER = "other"`
- **High-Precision Vietnamese NLP Normalization & Priority Classification**:
  - Precompiles dual regexes (accented and unaccented) for maximum throughput and thread safety.
  - **Strict Priority**: `COMPLAINT` strictly trumps both `ASK_PRICE` and `ASK_MATERIAL_USAGE` (critical brand safety guard against promoting products to angry customers).
  - **Homograph Collision Protection**:
    - Guarded `bung` (from `bung chỉ` defect vs `bụng` waist sizing query).
    - Guarded `lau` (from `giao lâu` shipping delay vs `lau nhà` home cleaning appliance query).
    - Guarded `lua` (from `lừa đảo` scam vs `vải lụa` silk fabric).
    - Guarded `hong`: In unaccented text, bare `hong` is Southern question slang (`không`), colliding with `hỏng` (broken/defect). The unaccented complaint pattern requires defect context (`bi hong`, `hang hong`, `hong roi`, `hong hoc`, `do hong`), successfully classifying `"chất co giãn hong shop"` as `ASK_MATERIAL_USAGE`.
  - **Price False-Positive Guards**:
    - Disqualifies phrases like `"giá như"`, `"đánh giá"`, `"giá rẻ"`, `"giá tốt"` unless accompanied by an explicit price inquiry question word.
    - Disqualifies home utility nouns like `"giá treo"`, `"giá đỡ"`, `"giá để đồ"` unless an explicit price inquiry is detected.
- **Natural KOC Reply Generation & Yellow Cart Navigation**:
  - Persona resolution dynamically maps fashion items to Hoài My (`vi-VN-HoaiMyNeural`, sweet, peer tone, "chị em ơi", "mấy bà ơi", body-hack focus) and home utility items to Nam Minh (`vi-VN-NamMinhNeural`, rustic, practical, "các bác ơi", "nhàn hẳn" labor-saving focus).
  - Price formatting into standard Vietnamese currency strings (`189,000đ`).
  - Title sanitization (`_sanitize_title`) cleans counterfeit brands (`Zara`, `Chanel`, `Gucci`, `Dior`, `LV`, `rep 1:1`, `super fake`) and exaggerated claims (`tốt nhất thị trường`, `vĩnh viễn không hỏng`).
  - All templates direct viewers to the yellow cart ("giỏ hàng vàng góc trái", "freeship", "voucher").
  - 100% `ToneValidator.validate(reply)` compliance: If candidate reply or LLM output fails `ToneValidator`, an emergency tone-certified fallback is triggered.

### 2.3 Hermetic Testing & Cross-Suite Isolation
- In `tests/test_comment_agent.py`, a dedicated function-scoped `db_session` fixture was created with its own isolated in-memory engine and cleanup. This prevents premature session-scoped engine caching and invalidation of `src.database.session._engines` / `_session_factories`, allowing the entire 457-test suite across all modules to run concurrently with zero cross-contamination.

### 2.4 Re-Exports
- `src/services/__init__.py`: Re-exported `CommentScanner`, `CommentScannerError`, `InvalidVideoIdError`, `CommentScannerTimeoutError`, `CommentRateLimitError`, `VideoNotFoundError`.
- `src/agents/__init__.py`: Re-exported `CommentAgent`, `CommentIntent`.

---

## 3. Caveats

- **TikTok Web API Rate Limiting in Live Mode**: Live TikTok Web API requests depend on IP reputation and can return HTTP 429 if called at extreme frequency. `CommentScanner` includes configurable backoff delay and `fallback_to_mock=True` for resilient fallback in production.
- **Mock Mode by Default**: Offline mock mode is active by default (controllable via `COMMENT_SCANNER_MOCK=false`), ensuring 100% deterministic, hermetic CI/CD test execution without external network flakiness.

---

## 4. Conclusion

- Milestone 7 (Features F26 & F27) is fully implemented, verified, and complete.
- Static integrity is verified 100% clean: 0 imports of `unittest.mock` across `src/`, 0 bypass flags, full genuine implementation.
- All 63 tests in `tests/test_comment_agent.py` PASS (100%).
- Full regression suite of 457 tests across all 7 milestones PASS (100% with zero regressions).
- Strict write boundaries were respected with no out-of-scope edits and no git commands executed.

---

## 5. Verification Method

To independently verify this milestone implementation:

1. **Verify Static Integrity**:
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
                   if 'unittest.mock' in content or 'MagicMock' in content or 'AsyncMock' in content:
                       violations.append(path)
   assert len(violations) == 0, f'Mock imports found: {violations}'
   print('Static integrity: 100% CLEAN')
   "
   ```

2. **Run Milestone 7 Test Suite**:
   ```bash
   pytest tests/test_comment_agent.py -v
   ```
   *Expected: 63 passed.*

3. **Run Full Project Regression Suite**:
   ```bash
   pytest tests/ -v
   ```
   *Expected: 457 passed in ~22s.*
