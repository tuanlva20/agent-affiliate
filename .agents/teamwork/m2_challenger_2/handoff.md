# Milestone 2 Adversarial Stress Testing Handoff Report

**Agent**: `m2_challenger_2` (Empirical Challenger)  
**Parent**: `f5177315-7404-4813-b8ba-56081885cdd4`  
**Target Components**: `src/services/tiktok_scraper.py` and `src/agents/base_scout.py`  
**Test Harness**: `scripts/m2_stress_harness.py`  
**Verdict**: **`REQUEST_CHANGES`**  
**Overall Risk Assessment**: **HIGH**

---

## 1. Observation

Empirical testing was executed across 47 adversarial scenarios using `python3 scripts/m2_stress_harness.py`. 36 test cases passed, and 11 failed due to reproducible bugs and security/boundary gaps.

### 1.1 Finding A: BaseScoutAgent Accepts NaN Price and NaN Commission (Numerical Boundary Evasion)
- **File**: `src/agents/base_scout.py`, lines 213–247
- **Code**:
  ```python
  # 2. Extract and validate price
  price_val = raw_item.get("price") if raw_item.get("price") is not None else raw_item.get("price_vnd")
  try:
      if price_val is None:
          return False
      price = float(price_val)
  except (ValueError, TypeError):
      return False

  if price <= 0.0:
      return False

  # 3. Extract and validate commission rate
  comm_val = raw_item.get("commission_rate") if raw_item.get("commission_rate") is not None else raw_item.get("commission")
  try:
      if comm_val is None:
          return False
      comm = float(comm_val)
  except (ValueError, TypeError):
      return False

  if comm <= 0.0 or comm > 1.0:
      return False
  ...
  if price < min_price or price > max_price:
      return False
  if comm < min_comm:
      return False

  return True
  ```
- **Observed Behavior**:
  When `price_val` is `float('nan')` or string `'nan'`:
  - `price = float('nan')` succeeds without exception.
  - In IEEE 754 standard arithmetic, all comparisons against `NaN` evaluate to `False`:
    - `nan <= 0.0` is `False`
    - `nan < min_price` is `False`
    - `nan > max_price` is `False`
  - Consequently, `filter_product` returns `True` for products with NaN prices!
  - Likewise for commission:
    - `nan <= 0.0 or nan > 1.0` is `False`
    - `nan < min_comm` is `False`
  - Consequently, `filter_product` returns `True` for products with NaN commission!
- **Harness Output**:
  ```
  [FAIL] NaN price float('nan') - Expected False (NaN price MUST be rejected), got True
  [FAIL] NaN price string 'nan' - Expected False (NaN string price MUST be rejected), got True
  [FAIL] Commission rate = NaN - Expected False (NaN commission MUST be rejected), got True
  [FAIL] Mixed batch filters invalid types and accepts only genuine valid candidates - Expected exactly 1 candidate ['p_good'], got ['p_good', 'p_nan_price']
  ```
- **Downstream Consequence**:
  `discover_candidates` ingests the NaN items, generates `ProductCandidate(price_vnd=nan, commission_rate=nan)`, and constructs ORM `Product(price=nan, commission_rate=nan)`. When serialized to JSON or stored in PostgreSQL, NaN values cause database insert failures or corrupt downstream revenue calculations (`price * sales`).

---

### 1.2 Finding B: TikTokScraper Unhandled `AttributeError` on `itemInfo: None`
- **File**: `src/services/tiktok_scraper.py`, lines 261–266
- **Code**:
  ```python
  def _extract_anchor_from_info(self, info: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
      anchors = info.get("anchors") or []
      if not anchors:
          raw_struct = info.get("raw_data") or info.get("itemInfo", {}).get("itemStruct", {})
          if isinstance(raw_struct, dict):
              anchors = raw_struct.get("anchors") or []
  ```
- **Observed Behavior**:
  When yt-dlp or raw JSON payloads contain `{"itemInfo": null}` (a standard JSON pattern when itemInfo is absent):
  - `info.get("itemInfo", {})` evaluates to `None` because `"itemInfo"` is a key in the dictionary. The default `{}` is NOT returned.
  - Next, `None.get("itemStruct", {})` raises an unhandled exception:
    `AttributeError: 'NoneType' object has no attribute 'get'`.
  - When `itemInfo` is a non-dict string (e.g. `{"itemInfo": "corrupted"}`):
    `AttributeError: 'str' object has no attribute 'get'`.
- **Harness Output**:
  ```
  [FAIL] itemInfo: None does not crash with AttributeError - CRASH: 'NoneType' object has no attribute 'get'
  [FAIL] itemInfo: string does not crash - CRASH: 'str' object has no attribute 'get'
  ```
- **Downstream Consequence**:
  Instead of gracefully concluding that the video has no anchor product (`has_anchor_product = False`), the scraper fails the entire metadata extraction, raising `TikTokScraperError: Scraper failed for ...: 'NoneType' object has no attribute 'get'`.

---

### 1.3 Finding C: TikTokScraper URL Validation Substring Evasion & Spoofing
- **File**: `src/services/tiktok_scraper.py`, lines 214–228
- **Code**:
  ```python
  def _validate_video_url(self, url: Any) -> str:
      if not url or not isinstance(url, str) or not url.strip():
          raise InvalidTikTokURLError("Invalid TikTok URL: URL cannot be empty")
      url_clean = url.strip()
      if "tiktok.com" not in url_clean:
          raise InvalidTikTokURLError(f"Invalid TikTok URL: {url_clean}")
      return url_clean
  ```
- **Observed Behavior**:
  Validation relies exclusively on `"tiktok.com" in url_clean`. It accepts any URL or URI scheme containing the literal string `"tiktok.com"` anywhere in the domain suffix, query string, or protocol:
  - `javascript:alert('tiktok.com')` -> **ACCEPTED**
  - `file:///etc/passwd#tiktok.com` -> **ACCEPTED**
  - `https://tiktok.com.attacker.com/video/7123456789` -> **ACCEPTED**
  - `https://not-tiktok.com/video/7123456789` -> **ACCEPTED**
  - `https://youtube.com/watch?v=123&ref=tiktok.com` -> **ACCEPTED**
- **Harness Output**:
  ```
  [FAIL] Youtube video with tiktok in query - Security/Validation flaw: Invalid URL 'https://youtube.com/watch?v=123&ref=tiktok.com' was accepted as valid!
  [FAIL] Attacker domain suffix (.attacker.com) - Security/Validation flaw: Invalid URL 'https://tiktok.com.attacker.com/video/7123456789' was accepted as valid!
  [FAIL] Attacker domain prefix (not-tiktok.com) - Security/Validation flaw: Invalid URL 'https://not-tiktok.com/video/7123456789' was accepted as valid!
  [FAIL] Javascript pseudo-protocol injection - Security/Validation flaw: Invalid URL 'javascript:alert('tiktok.com')' was accepted as valid!
  [FAIL] File URI scheme - Security/Validation flaw: Invalid URL 'file:///etc/passwd#tiktok.com' was accepted as valid!
  ```
- **Downstream Consequence**:
  In a production environment where yt-dlp or scraper processes execute external network requests, unvalidated schemes (`file://`, `javascript:`) can lead to SSRF, local file inclusion, or unhandled crashes when yt-dlp attempts to extract media from non-TikTok platforms.

---

## 2. Logic Chain

1. **Premise 1 (Numerical Integrity)**: An affiliate scout agent must reject corrupted numeric inputs. If `price` or `commission_rate` is `NaN`, it represents an undefined value.
2. **Observation 1.1**: `BaseScoutAgent.filter_product` relies on `<` and `>` comparisons. In IEEE 754, `nan < x`, `nan > x`, and `nan <= x` are all `False`.
3. **Deduction 1**: Products with `price=nan` or `commission_rate=nan` silently pass `filter_product` and are saved to the database. This violates the R1/Task 2 requirement that `BaseScoutAgent` filter invalid prices and commissions.
4. **Premise 2 (Robust Parsing)**: Web scraping payloads from yt-dlp and TikTok frequently include `null` for omitted fields. Optional keys must be safely navigated.
5. **Observation 1.2**: `info.get("itemInfo", {}).get(...)` assumes that if `"itemInfo"` is present, it is a non-empty dictionary. When `"itemInfo"` is `null`, `info.get("itemInfo", {})` returns `None`, crashing on `.get(...)` with `AttributeError`.
6. **Deduction 2**: Real-world TikTok video scrapes with null itemInfo crash metadata extraction rather than returning clean metadata without an anchor.
7. **Premise 3 (URL Sanitation)**: A service that downloads media must ensure that target URLs belong to the intended domain and use safe HTTP/HTTPS schemes.
8. **Observation 1.3**: `_validate_video_url` checks substring presence only, passing arbitrary protocols and spoofed domains.
9. **Deduction 3**: The scraper allows malicious or mismatched URLs to reach the extraction backend.

---

## 3. Caveats

1. **Mock Mode vs. Live Network**: Live yt-dlp scraping against real TikTok servers was not tested due to missing live network credentials and isolation constraints in the test harness. Mock mode and synthetic payloads were used to stress-test the internal parser methods.
2. **Specialist Scout Scope**: Fashion and Home Life domain-specific filters (e.g. counterfeit brand names, aesthetic hooks) were not tested here as they belong to Milestone 2 Task 3 (`FashionScoutAgent` and `HomeLifeScoutAgent`).

---

## 4. Conclusion & Required Changes

The current Milestone 2 Task 2 implementation fails adversarial stress testing in 3 distinct areas:
1. `BaseScoutAgent` does not reject `NaN` prices or commissions.
2. `TikTokScraper` crashes on null/non-dict `itemInfo`.
3. `TikTokScraper` fails to validate URL schemes and hostnames.

**Verdict**: **`REQUEST_CHANGES`**

### Actionable Remediation Guidance for Worker:

1. **In `src/agents/base_scout.py`**:
   - Add `import math`
   - In `filter_product`:
     ```python
     if math.isnan(price) or not math.isfinite(price):
         return False
     ...
     if math.isnan(comm) or not math.isfinite(comm):
         return False
     ```
   - In `ProductCandidate.from_raw_dict`:
     Ensure `float(...)` values are finite, or fallback to `0.0`.

2. **In `src/services/tiktok_scraper.py`**:
   - In `_extract_anchor_from_info`:
     Safely traverse `itemInfo`:
     ```python
     raw_struct = info.get("raw_data")
     if not isinstance(raw_struct, dict):
         item_info = info.get("itemInfo")
         if isinstance(item_info, dict):
             raw_struct = item_info.get("itemStruct")
         else:
             raw_struct = {}
     if not isinstance(raw_struct, dict):
         raw_struct = {}
     ```
   - In `_validate_video_url` and `_validate_channel_url`:
     Use `urllib.parse.urlparse` to enforce `scheme in ("http", "https")` and ensure hostname ends with `tiktok.com` (e.g. `parsed.netloc == "tiktok.com" or parsed.netloc.endswith(".tiktok.com")`).

---

## 5. Verification Method

To independently reproduce all 11 failures:

```bash
# Run the adversarial stress suite
python3 scripts/m2_stress_harness.py
```
Expected output before fix:
```
EMPIRICAL M2 ADVERSARIAL STRESS TEST SUMMARY
Total Test Cases: 47
Passed:           36
Failed / Gaps:    11
```

To verify resolution after worker fixes:
```bash
# 1. Run the empirical stress harness (must reach 47/47 passed, exit code 0)
python3 scripts/m2_stress_harness.py

# 2. Verify all existing unit tests remain green
pytest tests/test_kalodata_client.py tests/test_tiktok_scraper.py tests/test_base_scout.py -v

# 3. Verify entire project test suite
pytest tests/ -v
```

### Invalidation Conditions
- Any run of `scripts/m2_stress_harness.py` that exits with non-zero code or reports failed test cases.
- Any condition where `agent.filter_product({'product_id': '1', 'title': 'T', 'price': float('nan'), 'commission_rate': 0.15})` returns `True`.
- Any condition where `scraper._extract_anchor_from_info({'itemInfo': None})` raises `AttributeError`.
- Any condition where `scraper.download_video_metadata("javascript:alert('tiktok.com')")` does not raise `InvalidTikTokURLError` or `ValueError`.
