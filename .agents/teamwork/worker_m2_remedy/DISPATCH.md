## 2026-11-10T08:39:25Z
You are worker_m2_remedy, assigned to remediate the empirical adversarial defects and boundary vulnerabilities identified during Milestone 2 Gate verification.

Your working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/worker_m2_remedy/
Maintain progress.md in your working directory.
Original request file: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/ORIGINAL_REQUEST.md
Project plan: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/PROJECT.md

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Detailed Failure Reports to Read First:
1. /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m2_reviewer_2/handoff.md
2. /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m2_challenger_1/handoff.md
3. /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m2_challenger_2/handoff.md

## Write Ownership:
You have exclusive write ownership of:
- `src/agents/base_scout.py`
- `src/services/tiktok_scraper.py`
- `src/services/kalodata_client.py`
- `tests/test_kalodata_client.py`
- `tests/test_tiktok_scraper.py`
- `tests/test_base_scout.py`
- Your working directory: `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/worker_m2_remedy/`

## Concrete Tasks to Implement:

### 1. In `src/agents/base_scout.py`:
- Guard against IEEE 754 `NaN` and `Inf` in price and commission rate (`math.isnan`, `math.isinf`):
  Reject any item where `price` or `comm` is NaN, Inf, <= 0.0, or `comm > 1.0`.
- Strip and reject empty/whitespace-only `product_id` and `title`.

### 2. In `src/services/tiktok_scraper.py`:
- Use `urllib.parse.urlparse` for URL validation:
  Must have `scheme in ('http', 'https')` and `netloc.endswith("tiktok.com")` (e.g. `tiktok.com`, `www.tiktok.com`, `vm.tiktok.com`, `m.tiktok.com`).
  Reject domain spoofing (e.g. `tiktok.com.attacker.com`, `not-tiktok.com`), `javascript:`, `file:`, empty strings with `ValueError` (or subclass `InvalidTikTokURLError`).
- In `_extract_anchor_from_info`:
  - Guard `itemInfo`: if `itemInfo` is None or not a dict, do not crash with `AttributeError`.
  - Filter anchors: ONLY extract shopping anchors (e.g. `anchor.get("type") in (1004, ...)` or verify shopping keywords), ignore POI / location (type 28), CapCut templates, Wikipedia links.
  - When `anchor.get("extra")` is already a parsed dictionary (`isinstance(extra, dict)`), use it directly instead of calling `json.loads(extra)`.

### 3. In `src/services/kalodata_client.py`:
- Fix all 8 crash bugs identified by `m2_challenger_1`:
  1. `UnicodeDecodeError` in `_resolve_token`: read file with `try/except (UnicodeDecodeError, OSError)`.
  2. Wrap response JSON decoding in `poll_task` with `try/except (json.JSONDecodeError, aiohttp.ContentTypeError)` and raise `KalodataNetworkError` or `KalodataError`.
  3. Ensure top-level payloads and nested `data` are dicts before accessing `.get()`: check `isinstance(payload, dict)` and `isinstance(data, dict)`.
  4. Handle `error` field gracefully whether it is a dict, string, or None.
  5. Guard `message: None`: `(msg or "").lower()`.
  6. In `_parse_products`: check `isinstance(result_data, dict)` before indexing.
  7. Do NOT inject fallback 189k price and 15% commission for missing/empty fields; reject or skip incomplete items unless mock test fallback is specifically configured.
  8. In `_coerce_int`: guard against `float('nan')` and `float('inf')`.

## Verification Protocol:
You MUST run and verify 100% PASS for:
1. `python3 scripts/m2_stress_harness.py` -> All 47 test cases must PASS!
2. `python3 scripts/m2_kalodata_stress_harness.py` -> All 53 test cases must PASS!
3. `pytest tests/test_kalodata_client_adversarial.py -v` -> All adversarial tests must PASS!
4. `pytest tests/test_kalodata_client.py tests/test_tiktok_scraper.py tests/test_base_scout.py -v` -> All 25+ unit tests must PASS!
5. `pytest tests/e2e/ -v` -> All 61 E2E tests must PASS!
6. `pytest tests/ -v` -> 100% PASS across full suite!

## 2026-11-10T08:49:48Z
**Context**: Milestone 2 Remediation
**Content**: Status check: 10 minutes elapsed since dispatch. Please report your current status on fixing BaseScoutAgent, TikTokScraper, and KalodataClient, and test harness execution.
**Action**: Update progress.md and report status.
