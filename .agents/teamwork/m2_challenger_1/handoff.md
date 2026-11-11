# Milestone 2 Adversarial Challenge Report — `KalodataClient`

**Component**: `src/services/kalodata_client.py`  
**Challenger**: `m2_challenger_1`  
**Date**: 2026-11-10  
**Verdict**: **REQUEST_CHANGES**  
**Overall Risk Assessment**: **HIGH**

---

## 1. Observation

### 1.1 Baseline Test Runs
- Existing unit test suite in `tests/test_kalodata_client.py`:
  - Command: `pytest tests/test_kalodata_client.py -v`
  - Result: 9 passed in 0.16s.
  - Note: Tests only covered golden paths and basic known error paths (401 status and running timeouts). None probed schema corruption or boundary edge cases.

### 1.2 Adversarial Stress Test Suite Execution
Created two empirical test harnesses:
- `scripts/m2_kalodata_stress_harness.py`: Standalone stress runner executing 53 test scenarios across 4 dimensions.
- `tests/test_kalodata_client_adversarial.py`: Formal pytest adversarial suite with 19 test cases.

Execution of `python3 scripts/m2_kalodata_stress_harness.py`:
- Command: `python3 scripts/m2_kalodata_stress_harness.py`
- Output:
  ```
  Total Test Cases: 53
  Passed: 29
  Failed / Gaps: 24
  Success Rate: 54.7%
  ```

Execution of `pytest tests/test_kalodata_client_adversarial.py -v`:
- Command: `pytest tests/test_kalodata_client_adversarial.py -v`
- Output: `17 failed, 2 passed in 0.54s`

### 1.3 Exact Code Observations and Verbatim Failure Errors

#### Observation O1: Corrupted Token File Crashes `KalodataClient.__init__` with `UnicodeDecodeError`
- **File**: `src/services/kalodata_client.py:102-107`
- **Code**:
  ```python
  token_file = cls.TOKEN_FILE_PATH
  if token_file.exists() and token_file.is_file():
      try:
          content = token_file.read_text(encoding="utf-8").strip()
          if content:
              return content
      except OSError:
          pass
  ```
- **Verbatim Error**: `UnicodeDecodeError: 'utf-8' codec can't decode byte 0x80 in position 0: invalid start byte`
- **Test Case**: `test_adversarial_token_file_corrupted_binary`

#### Observation O2: Corrupted JSON / HTML Gateway Errors in `poll_task` Crash with Raw `JSONDecodeError`
- **File**: `src/services/kalodata_client.py:186-194`
- **Code**:
  ```python
  for _ in range(1, self.max_polls + 1):
      try:
          async with session.get(url, params=params, headers=self._get_headers()) as resp:
              if resp.status == 401:
                  raise KalodataAuthError(...)
              data = await resp.json()
      except (aiohttp.ClientError, asyncio.TimeoutError) as err:
          if isinstance(err, KalodataError):
              raise
          raise KalodataNetworkError(...)
  ```
- **Verbatim Error**: `json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)`
- **Test Case**: `test_adversarial_poll_corrupted_json`

#### Observation O3: Top-Level Non-Dict Payloads Crash with Unhandled `AttributeError`
- **File**: `src/services/kalodata_client.py:161` (submit_query) and `199` (poll_task)
- **Code**:
  ```python
  if not data.get("success", False):
  ```
- **Verbatim Error**: `AttributeError: 'list' object has no attribute 'get'` (also reproduced on `str`, `int`, and `NoneType`)
- **Test Case**: `test_adversarial_submit_and_poll_non_dict_top_level`

#### Observation O4: Payload `data` Key is `None` or Non-Dict (`data: null`) Crashes with `AttributeError`
- **File**: `src/services/kalodata_client.py:170` (submit_query) and `208-209` (poll_task)
- **Code**:
  `submit_query`: `tid = data.get("data", {}).get("task_id")`  
  `poll_task`: `task_data = data.get("data", {})`, `status = task_data.get("status", "running")`
- **Verbatim Error**: `AttributeError: 'NoneType' object has no attribute 'get'` (when payload contains `{"success": True, "data": None}`) and `AttributeError: 'str' object has no attribute 'get'` (when `data` is string or int).
- **Test Case**: `test_adversarial_data_field_non_dict`

#### Observation O5: Task Error Response with String `error` Field Crashes with `AttributeError`
- **File**: `src/services/kalodata_client.py:214`
- **Code**:
  ```python
  elif status == "error":
      err_msg = task_data.get("error", {}).get("message", "Unknown Kalodata task error")
      raise KalodataAPIError(f"Kalodata task failed: {err_msg}", data=task_data)
  ```
- **Verbatim Error**: `AttributeError: 'str' object has no attribute 'get'` (when `error` is `"Quota exceeded"`) or `AttributeError: 'NoneType' object has no attribute 'get'` (when `error: null`).
- **Test Case**: `test_adversarial_error_field_non_dict`

#### Observation O6: API Rejection with Null `message` (`message: null`) Crashes on `msg.lower()`
- **File**: `src/services/kalodata_client.py:163-164` (submit_query) and `201-202` (poll_task)
- **Code**:
  ```python
  msg = data.get("message", "Unknown submission rejection")
  if code == 401 or "token" in msg.lower():
  ```
- **Verbatim Error**: `AttributeError: 'NoneType' object has no attribute 'lower'`
- **Test Case**: `test_adversarial_null_message_rejection`

#### Observation O7: `_parse_products` Crashes on `result_data = None` or Non-Dict
- **File**: `src/services/kalodata_client.py:235-236`
- **Code**:
  ```python
  def _parse_products(self, result_data: Dict[str, Any], category_id: str, limit: int) -> List[Dict[str, Any]]:
      raw_items: List[Dict[str, Any]] = []
      if isinstance(result_data.get("products"), list):
  ```
- **Verbatim Error**: `AttributeError: 'NoneType' object has no attribute 'get'`
- **Test Case**: `test_adversarial_parse_products_result_data_none`

#### Observation O8: `_coerce_int` Crashes on Float `NaN` and `Inf`
- **File**: `src/services/kalodata_client.py:297-298`
- **Code**:
  ```python
  if isinstance(val, float):
      return int(val)
  ```
- **Verbatim Error**: `ValueError: cannot convert float NaN to integer` and `OverflowError: cannot convert float infinity to integer`
- **Test Case**: `test_adversarial_parse_products_nan_and_inf_handling`

---

## 2. Logic Chain

1. **Token File Handling (From Observation O1)**:
   - In Python, `UnicodeDecodeError` inherits from `ValueError`, NOT `OSError`.
   - The developer wrapped `token_file.read_text()` in `try ... except OSError: pass`, assuming all file reading errors are `OSError`.
   - When a token file contains binary or non-UTF-8 bytes, `UnicodeDecodeError` is raised and escapes uncaught, crashing the entire client initialization before any requests can be made.

2. **Polling Loop Exception Classification (From Observation O2)**:
   - In `submit_query`, the developer guarded JSON deserialization:
     `try: data = await resp.json() except Exception as exc: raise KalodataAPIError(...) from exc`.
   - In `poll_task`, this guard was completely omitted: `data = await resp.json()`.
   - `resp.json()` invokes `json.loads`, which raises `json.JSONDecodeError` on malformed JSON or HTML 502/503 responses. `json.JSONDecodeError` inherits from `ValueError`, not `aiohttp.ClientError`.
   - Consequently, `poll_task` crashes with an unhandled `JSONDecodeError` instead of gracefully classifying it into `KalodataAPIError` or `KalodataNetworkError`.

3. **Dict Access Assumption on Untrusted External Data (From Observations O3, O4, O5, O6, O7)**:
   - Python's `dict.get(key, default)` returns `None` if `key` exists and its value is explicitly `None`.
   - Throughout `submit_query`, `poll_task`, and `_parse_products`:
     - `data.get("success")` assumes `data` is a `dict`. If the server returns a list `["error"]` or string, it raises `AttributeError`.
     - `data.get("data", {}).get(...)` assumes `data["data"]` is a `dict`. When `data["data"]` is `None` (e.g., `{"success": True, "data": None}`), `data.get("data", {})` evaluates to `None`, causing `None.get(...)` to crash with `AttributeError`.
     - `task_data.get("error", {}).get("message")` crashes with `AttributeError` if `error` is a string or `None`.
     - `data.get("message", "default")` returns `None` if `"message": null`, causing `msg.lower()` to crash with `AttributeError`.
     - `_parse_products` lacks entry validation for `isinstance(result_data, dict)`.

4. **Numeric Coercion Safety (From Observation O8)**:
   - In Python, `int(float('nan'))` raises `ValueError` and `int(float('inf'))` raises `OverflowError`.
   - `_coerce_int` unconditionally converts `float` to `int(val)` without checking for `math.isnan(val)` or `math.isinf(val)`.
   - In analytics APIs, missing or infinite metrics occasionally produce `NaN` or `Inf`. This causes `_parse_products` to crash with an unhandled exception.

---

## 3. Caveats

- **Network Environment**: Stress testing was conducted with mock network layers (`unittest.mock.AsyncMock`) and isolated file structures to prevent external dependency on live Kalodata credits or internet flakiness.
- **Concurrent Load**: Tested up to 50 concurrent async queries on a single client instance. No race conditions in session lifecycle were observed under concurrent load (passed 50/50).
- **Scope Limit**: As an adversarial challenger, this agent does not modify `src/services/kalodata_client.py` directly, in strict compliance with the review-only constraint.

---

## 4. Conclusion & Required Changes

The implementation of `KalodataClient` in `src/services/kalodata_client.py` does NOT meet the required robustness standards. It contains **8 distinct unhandled crash bugs** when confronted with corrupted token files, malformed API responses, null fields, and boundary numeric values.

### Verdict: **REQUEST_CHANGES**

### Required Action Items for `worker_m2_1`:

1. **Fix Token Resolution (`src/services/kalodata_client.py:102-107`)**:
   Catch `(OSError, UnicodeDecodeError)` in `_resolve_token`.

2. **Wrap Polling JSON Parsing (`src/services/kalodata_client.py:193`)**:
   Wrap `data = await resp.json()` in `try ... except Exception as exc:` and raise `KalodataAPIError(f"Invalid JSON from Kalodata poll: {text[:200]}") from exc`.

3. **Validate Top-Level Response Type (`src/services/kalodata_client.py:161, 199`)**:
   In both `submit_query` and `poll_task`, verify `if not isinstance(data, dict): raise KalodataAPIError(f"Malformed response: expected dict, got {type(data).__name__}")`.

4. **Safely Extract `data` Field (`src/services/kalodata_client.py:170, 208-209`)**:
   In `submit_query`:
   ```python
   inner_data = data.get("data")
   if not isinstance(inner_data, dict):
       raise KalodataAPIError("Missing or invalid 'data' object in submit response", data=data)
   tid = inner_data.get("task_id")
   ```
   In `poll_task`:
   ```python
   task_data = data.get("data")
   if not isinstance(task_data, dict):
       raise KalodataAPIError(f"Malformed 'data' field in poll response: {type(task_data).__name__}", data=data)
   ```

5. **Safely Extract `error` Field (`src/services/kalodata_client.py:214-215`)**:
   ```python
   err_obj = task_data.get("error")
   if isinstance(err_obj, dict):
       err_msg = err_obj.get("message") or str(err_obj)
   elif err_obj is not None:
       err_msg = str(err_obj)
   else:
       err_msg = "Unknown Kalodata task error"
   ```

6. **Safely Extract `message` Field (`src/services/kalodata_client.py:163-164, 201-202`)**:
   ```python
   raw_msg = data.get("message")
   msg = str(raw_msg) if raw_msg is not None else ""
   ```

7. **Guard `_parse_products` Entry (`src/services/kalodata_client.py:234-236`)**:
   ```python
   if not isinstance(result_data, dict):
       return []
   ```

8. **Guard `_coerce_int` and `_coerce_float` against `NaN` and `Inf` (`src/services/kalodata_client.py:280-311`)**:
   ```python
   import math

   # in _coerce_float:
   if isinstance(val, (int, float)):
       if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
           return default
       return float(val)

   # in _coerce_int:
   if isinstance(val, float):
       if math.isnan(val) or math.isinf(val):
           return default
       return int(val)
   ```

---

## 5. Verification Method

To verify the fixes independently:

1. **Execute Standalone Adversarial Stress Harness**:
   ```bash
   python3 scripts/m2_kalodata_stress_harness.py
   ```
   Target: 53/53 Passed (100.0%), 0 Failed.

2. **Execute Pytest Adversarial Suite**:
   ```bash
   pytest tests/test_kalodata_client_adversarial.py -v
   ```
   Target: 19 passed in < 1.0s.

3. **Execute Full Project Test Suite**:
   ```bash
   pytest tests/ -v
   ```
   Target: All unit, boundary, and regression tests PASS 100%.

4. **Invalidation Conditions**:
   - Any unhandled `UnicodeDecodeError`, `JSONDecodeError`, `AttributeError`, `ValueError`, or `OverflowError` escaping `KalodataClient`.
   - Any failure where server rejection with `message: null` raises `AttributeError: 'NoneType' object has no attribute 'lower'`.
   - Any regression across existing 110 tests.
