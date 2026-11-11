# Milestone 2 (Task 2) Data & Boundary Review Report

**Reviewer**: `m2_reviewer_2` (Roles: Reviewer, Adversarial Critic)  
**Target**: Milestone 2 (Task 2: Base Scout Infrastructure & Scraper Service)  
**Implementer**: `worker_m2_1`  
**Date**: 2026-11-10  
**Verdict**: **`REQUEST_CHANGES`**  
**Overall Risk Assessment**: **`HIGH`**

---

## 1. Observation

### 1.1 Test Suite Verification
All existing test suites pass cleanly:
1. **Milestone 2 Scraper and Scout Unit Tests**:
   - Command: `pytest tests/test_kalodata_client.py tests/test_tiktok_scraper.py tests/test_base_scout.py -v`
   - Result: `25 passed in 0.87s`
2. **Milestone 1 Core Regression Tests**:
   - Command: `pytest tests/test_config.py tests/test_database.py tests/test_database_stress.py -v`
   - Result: `24 passed in 1.48s`
3. **E2E 4-Tier Test Suite**:
   - Command: `pytest tests/e2e/ -v`
   - Result: `61 passed in 1.48s`
4. **Milestone 1 Empirical Stress Harness**:
   - Command: `python3 scripts/m1_stress_harness.py`
   - Result: `59/59 passed (100.0%)`
5. **Full Project Test Suite**:
   - Command: `pytest tests/ -v`
   - Result: `110 passed in 2.97s`

### 1.2 Integrity & Cheating Inspection
- Inspected `src/services/kalodata_client.py`, `src/services/tiktok_scraper.py`, `src/agents/base_scout.py`.
- No evidence of hardcoded test result lookups, dummy facades, or fabricated test attestations.
- `KalodataClient` implements genuine asynchronous HTTP query submission and result polling via `aiohttp`.
- `TikTokScraper` implements genuine `yt-dlp` metadata extraction in a worker thread (`asyncio.to_thread`), yellow cart anchor parsing, and caption regex fallback.
- `BaseScoutAgent` implements dual-schema threshold resolution, quantitative filtering, batch ingestion, and database ORM mapping.
- Offline simulation modes (`mock_mode` and `expired_token` checks) are cleanly separated and explicitly documented for unit testing without live network or external token credentials.

### 1.3 Boundary & Adversarial Stress Observations
Through empirical adversarial execution, the following boundary vulnerabilities were uncovered:

1. **`NaN` Boundary Bypass in `BaseScoutAgent.filter_product`**:
   - Location: `src/agents/base_scout.py`, lines 213–247.
   - Observation: When `price` or `commission_rate` is `float('nan')`, comparison operators (`<=`, `<`, `>`, `>=`) all evaluate to `False`.
   - Command:
     ```bash
     python3 -c "from src.agents.base_scout import BaseScoutAgent; print(BaseScoutAgent().filter_product({'product_id': 'nan_01', 'title': 'Váy NaN', 'price': float('nan'), 'commission_rate': 0.15}))"
     ```
   - Result: `filter_product with NaN price: True` (Accepted!).
   - Command:
     ```bash
     python3 -c "from src.agents.base_scout import BaseScoutAgent; print(BaseScoutAgent().filter_product({'product_id': 'nan_02', 'title': 'Váy NaN Comm', 'price': 150000.0, 'commission_rate': float('nan')}))"
     ```
   - Result: `filter_product with NaN comm: True` (Accepted!).

2. **Greedy Extraction of Non-Shopping Anchors in `TikTokScraper._extract_anchor_from_info`**:
   - Location: `src/services/tiktok_scraper.py`, lines 268–289.
   - Observation: Any anchor present in the `anchors` array (e.g. location/POI type 28, CapCut template, music anchor) is accepted as a shopping product if it appears before a yellow cart anchor.
   - Command:
     ```bash
     python3 -c "from src.services.tiktok_scraper import TikTokScraper; print(TikTokScraper()._extract_anchor_from_info({'anchors': [{'type': 28, 'id': 'poi_12345', 'keyword': 'Hồ Gươm', 'extra': ''}]}))"
     ```
   - Result: `('poi_12345', 'Hồ Gươm')` extracted as TikTok Shop anchor product.

3. **Loss of `product_id` and `title` when `anchor["extra"]` is a parsed `dict`**:
   - Location: `src/services/tiktok_scraper.py`, line 273.
   - Observation: `if extra_str and isinstance(extra_str, str):` only parses strings. If `extra` is already a dictionary, it evaluates to `False`, skips reading `extra`, and returns `(anchor_id, None)`.
   - Command:
     ```bash
     python3 -c "from src.services.tiktok_scraper import TikTokScraper; print(TikTokScraper()._extract_anchor_from_info({'anchors': [{'id': 'anc_1', 'extra': {'product_id': 'p_456', 'title': 'Shirt'}}]}))"
     ```
   - Result: `('anc_1', None)` instead of `('p_456', 'Shirt')`.

4. **Default 189,000 VND / 15% Commission Substitution for Missing Fields in `KalodataClient._parse_products`**:
   - Location: `src/services/kalodata_client.py`, lines 258–265.
   - Observation: `_coerce_float(item.get("price"), default=189000.0)` and `_coerce_float(item.get("commission_rate"), default=0.15)` automatically fabricate valid fashion thresholds when data is missing or None.
   - Command:
     ```bash
     python3 -c "from src.services.kalodata_client import KalodataClient; print(KalodataClient(token='test')._parse_products({'items': [{}]}, 'thoi_trang_nu', 1))"
     ```
   - Result: Generates a complete product candidate with `price: 189000.0` and `commission_rate: 0.15` out of an empty dictionary `{}`.

5. **Whitespace-Only Product ID and Title Acceptance in `BaseScoutAgent.filter_product`**:
   - Location: `src/agents/base_scout.py`, line 209.
   - Observation: `if not pid or not title:` does not strip whitespace. `"   "` is truthy in Python.
   - Command:
     ```bash
     python3 -c "from src.agents.base_scout import BaseScoutAgent; print(BaseScoutAgent().filter_product({'product_id': '   ', 'title': '   ', 'price': 150000.0, 'commission_rate': 0.15}))"
     ```
   - Result: `filter_product with whitespace pid/title: True`.

6. **String Float Representation Crash in `ProductCandidate.from_raw_dict`**:
   - Location: `src/agents/base_scout.py`, line 120.
   - Observation: `sales = int(sales_raw)` crashes when `sales_raw` is `"1500.0"`.
   - Command:
     ```bash
     python3 -c "from src.agents.base_scout import ProductCandidate; ProductCandidate.from_raw_dict({'product_id': 'p1', 'title': 'Test', 'price': 100000, 'commission_rate': 0.1, 'sales_30d': '1500.0'}, 'thoi_trang_nu')"
     ```
   - Result: `ValueError: invalid literal for int() with base 10: '1500.0'`.

---

## 2. Logic Chain

1. **Test Verification vs. Edge Case Reality (Observation 1.1 -> Observation 1.3)**:
   - While the unit tests and E2E suites pass 100% on standard happy-path inputs and basic mocks, they fail to exercise hostile inputs (`NaN`, non-shopping anchors, whitespace strings, dict extra).
   - Passing tests do not certify robustness when boundary assertions omit non-numeric IEEE 754 floats (`NaN`) or non-string extra payloads.

2. **Impact of `NaN` Prices on Downstream Pipeline (Observation 1.3.1)**:
   - In Python, `float('nan') < x`, `float('nan') > x`, `float('nan') == x`, and `float('nan') <= x` all evaluate to `False`.
   - In `BaseScoutAgent.filter_product`:
     ```python
     if price <= 0.0: return False  # False when price is NaN
     if price < min_price or price > max_price: return False  # False when price is NaN
     if comm <= 0.0 or comm > 1.0: return False  # False when comm is NaN
     if comm < min_comm: return False  # False when comm is NaN
     return True  # Bypassed!
     ```
   - An item with `NaN` price or commission passes the filter and is converted into a `ProductCandidate` and SQLAlchemy `Product` ORM entity.
   - Downstream, calculating affiliate metrics or revenue (`NaN * sales = NaN`) causes financial metric corruption, DB persistence errors, and Telegram formatting exceptions.

3. **Impact of Greedily Accepting Any Anchor in Scraper (Observation 1.3.2)**:
   - TikTok videos frequently contain multiple anchor types: Location/Point of Interest (type 28), CapCut templates (type 1005/1006), Sound/Music anchors, and Yellow Cart E-commerce shopping anchors (type 1004).
   - `TikTokScraper._extract_anchor_from_info` falls back to `prod_id = prod_id or (anchor_id if anchor_id else None)` across any anchor type.
   - A video tagged with a location (e.g. "Hồ Gươm") before the shopping anchor will report "Hồ Gươm" as an affiliate product with URL `https://shop.tiktok.com/view/product/poi_12345`.
   - Downstream specialist agents and video remix studios will attempt to generate affiliate campaigns for a geographic location tag.

4. **Impact of Fabricated Default Values in `KalodataClient` (Observation 1.3.4)**:
   - In `_coerce_float`, using `default=189000.0` and `default=0.15` masks malformed API items.
   - If Kalodata API returns an item where the price was omitted or failed to parse, the client invisibly assigns 189k VND and 15% commission.
   - This prevents `BaseScoutAgent` from rejecting bad data, creating ghost candidates with synthetic prices.

---

## 3. Findings

### [Critical] Finding 1: `BaseScoutAgent.filter_product` allows `NaN` and `Inf` to bypass boundary checks
- **Where**: `src/agents/base_scout.py`, lines 213–247
- **Why**: IEEE 754 `NaN` evaluates to `False` in all inequality checks. Products with `NaN` price or `NaN` commission rate return `True` in `filter_product` and become active candidates.
- **Suggestion**:
  ```python
  import math
  if math.isnan(price) or math.isinf(price) or price <= 0.0:
      return False
  if math.isnan(comm) or math.isinf(comm) or comm <= 0.0 or comm > 1.0:
      return False
  ```

### [Critical] Finding 2: `TikTokScraper` extracts non-shopping anchors (Location, CapCut) as TikTok Shop products
- **Where**: `src/services/tiktok_scraper.py`, lines 268–289
- **Why**: The loop does not verify the anchor type or e-commerce payload. Non-shopping anchors like location (POI type 28) or CapCut templates are extracted as affiliate products.
- **Suggestion**:
  Only extract anchors where `anchor.get("type") in (1004, 1005)` or where `extra` explicitly contains shopping product keys (`product_id`, `promotion_id`).

### [Major] Finding 3: `TikTokScraper` drops product metadata when `anchor["extra"]` is a parsed dictionary
- **Where**: `src/services/tiktok_scraper.py`, line 273
- **Why**: `if extra_str and isinstance(extra_str, str):` ignores `extra` when it is already a dictionary, falling back to `anchor_id` and discarding the product title.
- **Suggestion**:
  ```python
  extra = extra_str if isinstance(extra_str, dict) else (json.loads(extra_str) if isinstance(extra_str, str) else {})
  ```

### [Major] Finding 4: `KalodataClient._parse_products` fabricates prices and commissions for empty/missing items
- **Where**: `src/services/kalodata_client.py`, lines 258–265
- **Why**: Defaults of `189000.0` and `0.15` invent valid fashion data for missing fields instead of returning `0.0` or skipping invalid items.
- **Suggestion**:
  Change default to `0.0`, or skip items where `price is None` or `commission_rate is None`.

### [Major] Finding 5: `BaseScoutAgent.filter_product` accepts whitespace-only `product_id` and `title`
- **Where**: `src/agents/base_scout.py`, lines 207–210
- **Why**: `"   "` is truthy in Python. Blank strings pass validation and pollute the database and UI.
- **Suggestion**:
  `if not str(pid).strip() or not str(title).strip(): return False`

### [Minor] Finding 6: `ProductCandidate.from_raw_dict` crashes on string float sales representations
- **Where**: `src/agents/base_scout.py`, line 120
- **Why**: `int("1500.0")` raises `ValueError`.
- **Suggestion**:
  `sales = int(float(sales_raw))`

### [Minor] Finding 7: Broad `tiktok.com` substring validation allows attacker domains
- **Where**: `src/services/tiktok_scraper.py`, lines 218, 226
- **Why**: `"tiktok.com" in url` allows `https://evil-tiktok.com` or `https://tiktok.com.phishing.com`.
- **Suggestion**:
  Use `urllib.parse.urlsplit` and verify the netloc ends with `tiktok.com`.

### [Minor] Finding 8: `KalodataClient.poll_task` lacks overall wall-clock deadline
- **Where**: `src/services/kalodata_client.py`, lines 186–223
- **Why**: Polling only checks `max_polls` iteration count; cumulative slow responses can block far beyond `self.timeout`.
- **Suggestion**:
  Track `start_time = time.monotonic()` and raise `KalodataTimeoutError` if `time.monotonic() - start_time > self.timeout`.

---

## 4. Caveats
- No live TikTok or Kalodata network traffic was tested; external APIs were validated via mock environments and synthetic response payloads.
- The default 189k / 15% values in `KalodataClient` appear to have originated from matching the Milestone 1 `conftest.py` mock template rather than intentional fraud.

---

## 5. Conclusion
While the codebase demonstrates solid structure, proper async separation, and 100% test pass rates on existing test suites, critical numerical boundary leaks (`NaN` bypass) and greedy anchor extraction (location tags mistaken for shop products) prevent approval.

**Verdict: `REQUEST_CHANGES`**  
The implementer (`worker_m2_1`) must address Findings 1 through 5 and add corresponding test coverage before Milestone 2 can proceed to Task 3.

---

## 6. Verification Method

To verify these findings independently:

```bash
# 1. Verify NaN price/commission bypass
python3 -c "
from src.agents.base_scout import BaseScoutAgent
agent = BaseScoutAgent()
assert agent.filter_product({'product_id': 'p1', 'title': 'T', 'price': float('nan'), 'commission_rate': 0.15}) is False, 'NaN price must be rejected!'
"

# 2. Verify non-shopping anchor leakage
python3 -c "
from src.services.tiktok_scraper import TikTokScraper
scraper = TikTokScraper()
pid, _ = scraper._extract_anchor_from_info({'anchors': [{'type': 28, 'id': 'poi_123', 'keyword': 'Location'}]})
assert pid is None, 'Non-shopping anchor must not be extracted as product!'
"

# 3. Verify whitespace title rejection
python3 -c "
from src.agents.base_scout import BaseScoutAgent
agent = BaseScoutAgent()
assert agent.filter_product({'product_id': '   ', 'title': '   ', 'price': 150000.0, 'commission_rate': 0.15}) is False, 'Whitespace title/pid must be rejected!'
"

# 4. Run existing test suites
pytest tests/test_kalodata_client.py tests/test_tiktok_scraper.py tests/test_base_scout.py -v
pytest tests/e2e/ -v
```
