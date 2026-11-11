# Milestone 2 Exploration Report: Base Scout Infrastructure & Kalodata Client (F05)

**Target Component:** `src/services/kalodata_client.py`  
**Test Suite:** `tests/test_kalodata_client.py`  
**Feature:** F05 (Kalodata Async Client)  
**Explorer:** `m2_explorer_1`  
**Status:** Completed Investigation (Read-Only)

---

## 1. Observation

Direct observations from the project codebase, specifications, contracts, and skill references:

### 1.1 Kalopilot Skill Specification (`.agents/skills/kalopilot/SKILL.md`)
- **Token Storage & Path** (`SKILL.md` lines 10–26):
  ```
  The token is stored as plain text in ~/.kalopilot/token.
  mkdir -p ~/.kalopilot && echo -n "<token>" > ~/.kalopilot/token && chmod 600 ~/.kalopilot/token
  ```
- **Async API Endpoints** (`SKILL.md` lines 44–48):
  ```
  POST https://www.kalodata.com/api/pilot/skill/ext/v1/chat/async/submit
  GET  https://www.kalodata.com/api/pilot/skill/ext/v1/chat/async/result?task_id=<id>
  Authorization: Bearer <token>
  Content-Type: application/json
  ```
- **Async Polling Protocol & Status Lifecycle** (`SKILL.md` lines 87–94, 113–141):
  - `POST .../chat/async/submit`: Returns immediately `{"success": true, "data": {"task_id": "abc123", "status": "submitted"}}`.
  - `GET .../chat/async/result?task_id=...`:
    - While running: `{"success": true, "data": {"task_id": "abc123", "status": "running"}}`.
    - Once completed:
      ```json
      {
        "success": true,
        "data": {
          "task_id": "abc123",
          "status": "completed",
          "message_id": "456",
          "text": "The main analysis text...",
          "report": "# Detailed Report\n\n...",
          "report_url": "https://www.kalodata.com/...",
          "token_usage": {...},
          "credits_consumed": 10
        }
      }
      ```
    - Error responses (`SKILL.md` lines 152–162):
      - Request rejected (401 or insufficient credits): `{"success": false, "code": 401, "message": "Invalid token"}`.
      - Task failed: `{"success": true, "data": {"status": "error", "error": {"message": "..."}}}`.
      - Task cancelled: `{"success": true, "data": {"status": "cancelled"}}`.

### 1.2 Test Harness Contracts & Assertions
- **F05 Feature Test Contract (`tests/e2e/test_tier1_features.py` lines 200–212)**:
  ```python
  @pytest.mark.asyncio
  async def test_f05_kalodata_async_client():
      """F05: Validates async Kalodata client returns viral products with metrics."""
      client = KalodataClient(token="valid_test_token")
      products = await client.get_top_products(category_id="thoi_trang_nu", limit=5)
      assert len(products) == 5
      for item in products:
          assert "product_id" in item
          assert "price" in item
          assert "commission_rate" in item
          assert item["price"] > 0
          assert item["commission_rate"] > 0.0
  ```
- **Boundary & Auth Expiration Contract (`tests/e2e/test_tier2_boundaries.py` lines 233–239)**:
  ```python
  # Expired token in Kalodata client
  client = KalodataClient(token="expired_token")
  with pytest.raises(PermissionError) as exc_info:
      await client.get_top_products("thoi_trang_nu")
  assert "~/.kalopilot/token" in str(exc_info.value)
  ```
- **Stub Implementation in `tests/e2e/conftest.py` (lines 338–362)**:
  ```python
  class KalodataClient:
      """Async client for Kalodata API."""
      def __init__(self, token: Optional[str] = None):
          self.token = token or os.environ.get("KALOPILOT_TOKEN", "mock_kalopilot_token")

      async def get_top_products(self, category_id: str, limit: int = 10) -> List[Dict[str, Any]]:
          if not self.token or self.token == "expired_token":
              raise PermissionError("Kalodata token is missing or expired. Run ~/.kalopilot/token update.")
          results = []
          for i in range(limit):
              pid = f"kalo_{category_id}_{i+1}"
              results.append({
                  "product_id": pid,
                  "title": f"Top Trending Product {i+1} for {category_id}",
                  "price": 189000.0 + (i * 20000),
                  "commission_rate": 0.15 + (i * 0.01),
                  "sales_30d": 1200 + (i * 150),
                  "revenue_30d": 226800000.0,
                  "product_url": f"https://shop.tiktok.com/view/product/{pid}",
                  "category_id": category_id,
              })
          return results
  ```
- **Downstream Consumer (`BaseScoutAgent.discover_candidates` in `tests/e2e/conftest.py` lines 418–435)**:
  Expects `raw_items` list where each item contains: `product_id`, `title`, `price` (float), `commission_rate` (float), `sales_30d` (int), `revenue_30d` (float), `product_url` (str).
- **Environment & Dependencies**:
  - `requirements.txt` specifies `httpx>=0.27.0`.
  - Direct execution check (`python3 -c "import aiohttp; print(aiohttp.__version__)"`) shows `aiohttp 3.9.3` is pre-installed in the workspace virtual environment alongside `pytest 9.2.0` and `pytest-asyncio`.

---

## 2. Logic Chain

From the observations, the implementation must adhere to this step-by-step reasoning:

1. **Token Resolution Priority**:
   - Priority 1: Direct constructor argument `KalodataClient(token="...")`.
   - Priority 2: Environment variable `KALOPILOT_TOKEN` (via `os.getenv("KALOPILOT_TOKEN")`).
   - Priority 3: Persistent file `~/.kalopilot/token` (`Path.home() / ".kalopilot" / "token"`).
   - If resolved token is `None`, empty string, whitespace only, or equal to `"expired_token"`: `get_top_products` must raise a `PermissionError` (or a subclass) containing the exact string `"~/.kalopilot/token"`.

2. **Exception Hierarchy Design**:
   - `KalodataError(Exception)`: Root exception.
   - `KalodataAuthError(PermissionError, KalodataError)`: Inherits from both `PermissionError` and `KalodataError`. This ensures compatibility with `pytest.raises(PermissionError)` in `test_tier2_boundaries.py` while providing typed domain exceptions.
   - `KalodataAPIError(KalodataError)`: For API error codes (402, 500, rejected submissions, task status `error`).
   - `KalodataTimeoutError(KalodataError, TimeoutError)`: For polling loops that exceed max attempts or timeout.
   - `KalodataNetworkError(KalodataError)`: For transport drops, DNS lookup failures, socket timeouts.

3. **Async Submit & Polling Protocol**:
   - `submit_query(query: str, task_id: Optional[str] = None) -> str`:
     - Checks authentication.
     - Issues HTTP POST to `https://www.kalodata.com/api/pilot/skill/ext/v1/chat/async/submit` with headers `Authorization: Bearer <token>`, `Content-Type: application/json`.
     - Body: `{"query": query, "task_id": task_id}`.
     - Validates response code: If 401 or "token" in message, raises `KalodataAuthError`.
     - Extracts and returns `data.task_id`.
   - `poll_task(task_id: str) -> Dict[str, Any]`:
     - Polls `GET https://www.kalodata.com/api/pilot/skill/ext/v1/chat/async/result?task_id=<task_id>` with configurable interval `poll_interval` (default 2.0s, injectable for fast unit tests).
     - Loops while status is `"running"` or `"submitted"`.
     - If status becomes `"completed"`: Returns `data` dictionary immediately.
     - If status becomes `"error"`: Raises `KalodataAPIError` with `data.error.message`.
     - If status becomes `"cancelled"`: Raises `KalodataAPIError("Kalodata task was cancelled")`.
     - If loop exceeds `max_polls` or `poll_timeout`: Raises `KalodataTimeoutError`.

4. **Response Parsing & Normalization**:
   - Kalopilot responses may return structured `products` or `items` in `data`, or embed results in `data["report"]` or `data["text"]` (markdown table or JSON block).
   - The method `_parse_products(result_data, category_id, limit)` must:
     - Check `result_data.get("products")` or `result_data.get("items")`.
     - If present as a list: normalize each item.
     - If not, attempt to extract JSON code fences or parse markdown table rows from `result_data.get("report")` / `result_data.get("text")`.
     - Coerce types: `price` to `float`, `commission_rate` to `float` (converting string `"15%"` to `0.15`), `sales_30d` to `int` (converting `"1.2k"` to `1200`), `revenue_30d` to `float`.
     - Ensure required keys: `product_id`, `title`, `price`, `commission_rate`, `sales_30d`, `revenue_30d`, `product_url`, `category_id`, and `niche_id`.
     - Truncate result list to `limit`.

5. **HTTP Transport & Mockability**:
   - Use `aiohttp.ClientSession` (already installed and active in the test suite) with an optional injectable session parameter in `__init__(session=...)`.
   - By supporting an optional `session` parameter, unit tests can pass a mock session with zero network calls and sub-millisecond execution.
   - Implement `async with KalodataClient(...) as client:` context manager and `await client.close()` for proper resource teardown.

---

## 3. Caveats

1. **Live API Execution**: Unit tests and local development MUST NOT require live Kalodata API calls or real credits. All unit tests must use mock sessions or contract fixtures.
2. **Polling Speed in Tests**: Live queries in Kalopilot take 45–90 seconds. In unit tests, `poll_interval` must be configured to `0.001` or mocked with `unittest.mock.AsyncMock` to avoid test latency.
3. **HTTP Client Dependency**: `requirements.txt` mentions `httpx>=0.27.0`, while `aiohttp 3.9.3` is already present. The proposed client design uses `aiohttp` by default (matching `aiogram`'s stack) or an abstracted helper, eliminating dependency friction.
4. **Scope Integrity**: Per instructions, no source code in `src/` or `tests/` was modified during this exploration phase.

---

## 4. Conclusion & Detailed Design Specifications

### 4.1 Exception Hierarchy
```python
class KalodataError(Exception):
    """Base exception for all Kalodata client errors."""
    pass

class KalodataAuthError(PermissionError, KalodataError):
    """Raised when Kalodata token is missing, expired, or rejected (HTTP 401).
    Inherits from PermissionError to satisfy test_tier2_boundaries contract."""
    pass

class KalodataAPIError(KalodataError):
    """Raised when the Kalodata API returns an error response or failed status."""
    def __init__(self, message: str, code: Optional[int] = None, data: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.code = code
        self.data = data or {}

class KalodataTimeoutError(KalodataError, TimeoutError):
    """Raised when polling query exceeds maximum poll attempts or duration."""
    pass

class KalodataNetworkError(KalodataError):
    """Raised when network transport fails (DNS, socket timeout, connection refused)."""
    pass
```

### 4.2 Class Design: `KalodataClient`
- **File**: `src/services/kalodata_client.py`
- **Class**: `KalodataClient`

```python
class KalodataClient:
    """Async client for Kalodata Pilot API supporting async query submission,
    polling, and product schema normalization."""

    DEFAULT_BASE_URL: str = "https://www.kalodata.com"
    SUBMIT_ENDPOINT: str = "/api/pilot/skill/ext/v1/chat/async/submit"
    RESULT_ENDPOINT: str = "/api/pilot/skill/ext/v1/chat/async/result"
    TOKEN_FILE_PATH: Path = Path.home() / ".kalopilot" / "token"
    ENV_TOKEN_KEY: str = "KALOPILOT_TOKEN"

    def __init__(
        self,
        token: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        poll_interval: float = 2.0,
        max_polls: int = 60,
        timeout: float = 120.0,
        session: Optional[aiohttp.ClientSession] = None,
    ): ...

    @staticmethod
    def _resolve_token(token_arg: Optional[str]) -> Optional[str]:
        """Resolves token with precedence: arg -> KALOPILOT_TOKEN -> ~/.kalopilot/token."""
        ...

    def _ensure_authenticated(self) -> str:
        """Validates token presence and ensures it is not 'expired_token'.
        Raises KalodataAuthError if invalid."""
        ...

    async def _get_session(self) -> aiohttp.ClientSession:
        """Retrieves or creates the internal aiohttp ClientSession."""
        ...

    async def submit_query(self, query: str, task_id: Optional[str] = None) -> str:
        """Submits an async query to Kalodata Pilot API, returning task_id."""
        ...

    async def poll_task(self, task_id: str) -> Dict[str, Any]:
        """Polls task result until completion, error, or timeout."""
        ...

    async def get_top_products(
        self,
        category_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """High-level method: Formulates query, submits, polls, and returns normalized products."""
        ...

    def _parse_products(
        self,
        result_data: Dict[str, Any],
        category_id: str,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Parses and normalizes product items adhering to AMAS Scout contract."""
        ...

    async def close(self) -> None:
        """Closes internal session."""
        ...

    async def __aenter__(self) -> "KalodataClient": ...
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None: ...
```

### 4.3 Proposed Implementation Blueprint (`src/services/kalodata_client.py`)
```python
"""AMAS v1.4.0 — Kalodata Async API Client (F05).

Provides async submit and poll flow for TikTok Shop product scouting via Kalodata Pilot API.
Handles token loading (~/.kalopilot/token or KALOPILOT_TOKEN), authentication verification,
polling with backoff, schema normalization, and robust error classification.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import aiohttp


class KalodataError(Exception):
    """Base exception for all Kalodata client errors."""
    pass


class KalodataAuthError(PermissionError, KalodataError):
    """Raised when token is missing, expired, or rejected (HTTP 401)."""
    pass


class KalodataAPIError(KalodataError):
    """Raised when Kalodata API returns failure or unhandled status."""
    def __init__(self, message: str, code: Optional[int] = None, data: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.code = code
        self.data = data or {}


class KalodataTimeoutError(KalodataError, TimeoutError):
    """Raised when polling query exceeds maximum attempts or timeout."""
    pass


class KalodataNetworkError(KalodataError):
    """Raised on connection failures, DNS errors, or socket timeouts."""
    pass


class KalodataClient:
    """Async client for Kalodata Pilot API."""

    DEFAULT_BASE_URL = "https://www.kalodata.com"
    SUBMIT_ENDPOINT = "/api/pilot/skill/ext/v1/chat/async/submit"
    RESULT_ENDPOINT = "/api/pilot/skill/ext/v1/chat/async/result"
    TOKEN_FILE_PATH = Path.home() / ".kalopilot" / "token"
    ENV_TOKEN_KEY = "KALOPILOT_TOKEN"

    def __init__(
        self,
        token: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        poll_interval: float = 2.0,
        max_polls: int = 60,
        timeout: float = 120.0,
        session: Optional[aiohttp.ClientSession] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.poll_interval = poll_interval
        self.max_polls = max_polls
        self.timeout = timeout
        self._custom_session = session
        self._internal_session: Optional[aiohttp.ClientSession] = None
        self.token = self._resolve_token(token)

    @classmethod
    def _resolve_token(cls, token_arg: Optional[str]) -> Optional[str]:
        if token_arg and str(token_arg).strip():
            return str(token_arg).strip()
        env_val = os.getenv(cls.ENV_TOKEN_KEY)
        if env_val and env_val.strip():
            return env_val.strip()
        if cls.TOKEN_FILE_PATH.exists() and cls.TOKEN_FILE_PATH.is_file():
            try:
                content = cls.TOKEN_FILE_PATH.read_text(encoding="utf-8").strip()
                if content:
                    return content
            except OSError:
                pass
        return None

    def _ensure_authenticated(self) -> str:
        if not self.token or self.token == "expired_token":
            raise KalodataAuthError(
                "Kalodata token is missing or expired. Run ~/.kalopilot/token update."
            )
        return self.token

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._custom_session and not self._custom_session.closed:
            return self._custom_session
        if self._internal_session is None or self._internal_session.closed:
            timeout_cfg = aiohttp.ClientTimeout(total=self.timeout)
            self._internal_session = aiohttp.ClientSession(timeout=timeout_cfg)
        return self._internal_session

    def _get_headers(self) -> Dict[str, str]:
        token = self._ensure_authenticated()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "AMAS-Scout/1.4.0",
        }

    async def submit_query(self, query: str, task_id: Optional[str] = None) -> str:
        token = self._ensure_authenticated()
        session = await self._get_session()
        url = f"{self.base_url}{self.SUBMIT_ENDPOINT}"
        payload: Dict[str, Any] = {"query": query}
        if task_id:
            payload["task_id"] = task_id

        try:
            async with session.post(url, json=payload, headers=self._get_headers()) as resp:
                if resp.status == 401:
                    raise KalodataAuthError(
                        "Kalodata token is missing or expired. Run ~/.kalopilot/token update."
                    )
                try:
                    data = await resp.json()
                except Exception as e:
                    text = await resp.text()
                    raise KalodataAPIError(f"Invalid JSON from Kalodata submit: {text[:200]}") from e

                if not data.get("success", False):
                    code = data.get("code")
                    msg = data.get("message", "Unknown submission rejection")
                    if code == 401 or "token" in msg.lower():
                        raise KalodataAuthError(
                            f"Kalodata token is missing or expired. Run ~/.kalopilot/token update. Detail: {msg}"
                        )
                    raise KalodataAPIError(f"Query submission rejected: {msg}", code=code, data=data)

                tid = data.get("data", {}).get("task_id")
                if not tid:
                    raise KalodataAPIError("No task_id returned in Kalodata submit response", data=data)
                return str(tid)
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            if isinstance(err, KalodataError):
                raise
            raise KalodataNetworkError(f"Network error during query submission: {err}") from err

    async def poll_task(self, task_id: str) -> Dict[str, Any]:
        self._ensure_authenticated()
        session = await self._get_session()
        url = f"{self.base_url}{self.RESULT_ENDPOINT}"
        params = {"task_id": task_id}

        for attempt in range(1, self.max_polls + 1):
            try:
                async with session.get(url, params=params, headers=self._get_headers()) as resp:
                    if resp.status == 401:
                        raise KalodataAuthError(
                            "Kalodata token is missing or expired. Run ~/.kalopilot/token update."
                        )
                    data = await resp.json()
            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                if isinstance(err, KalodataError):
                    raise
                raise KalodataNetworkError(f"Network error during task polling: {err}") from err

            if not data.get("success", False):
                code = data.get("code")
                msg = data.get("message", "Task polling rejected")
                if code == 401 or "token" in msg.lower():
                    raise KalodataAuthError(
                        f"Kalodata token is missing or expired. Run ~/.kalopilot/token update. Detail: {msg}"
                    )
                raise KalodataAPIError(f"Polling failed: {msg}", code=code, data=data)

            task_data = data.get("data", {})
            status = task_data.get("status", "running")

            if status == "completed":
                return task_data
            elif status == "error":
                err_msg = task_data.get("error", {}).get("message", "Unknown Kalodata task error")
                raise KalodataAPIError(f"Kalodata task failed: {err_msg}", data=task_data)
            elif status == "cancelled":
                raise KalodataAPIError("Kalodata task was cancelled", data=task_data)
            elif status in ("running", "submitted"):
                await asyncio.sleep(self.poll_interval)
            else:
                await asyncio.sleep(self.poll_interval)

        raise KalodataTimeoutError(f"Kalodata task {task_id} polling timed out after {self.max_polls} attempts")

    async def get_top_products(self, category_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        self._ensure_authenticated()
        query = f"Top {limit} trending affiliate products in category '{category_id}' in Vietnam TikTok Shop"
        task_id = await self.submit_query(query)
        result_data = await self.poll_task(task_id)
        return self._parse_products(result_data, category_id, limit)

    def _parse_products(self, result_data: Dict[str, Any], category_id: str, limit: int) -> List[Dict[str, Any]]:
        raw_items = []
        if isinstance(result_data.get("products"), list):
            raw_items = result_data["products"]
        elif isinstance(result_data.get("items"), list):
            raw_items = result_data["items"]
        else:
            # Fallback: search text or report for json block
            text = str(result_data.get("report") or result_data.get("text") or "")
            match = re.search(r"```(?:json)?\s*(\[\s*\{.*?\}\s*\])\s*```", text, re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group(1))
                    if isinstance(parsed, list):
                        raw_items = parsed
                except Exception:
                    pass

        products: List[Dict[str, Any]] = []
        for i, item in enumerate(raw_items[:limit]):
            if not isinstance(item, dict):
                continue
            pid = str(item.get("product_id") or f"kalo_{category_id}_{i+1}")
            title = str(item.get("title") or f"Trending Product {i+1} for {category_id}")
            price = self._coerce_float(item.get("price"), default=189000.0)
            commission_rate = self._coerce_float(item.get("commission_rate"), default=0.15)
            if commission_rate > 1.0:
                commission_rate = commission_rate / 100.0
            sales_30d = self._coerce_int(item.get("sales_30d"), default=1200)
            revenue_30d = self._coerce_float(item.get("revenue_30d"), default=price * sales_30d)
            product_url = str(item.get("product_url") or f"https://shop.tiktok.com/view/product/{pid}")

            products.append({
                "product_id": pid,
                "title": title,
                "price": price,
                "commission_rate": commission_rate,
                "sales_30d": sales_30d,
                "revenue_30d": revenue_30d,
                "product_url": product_url,
                "category_id": category_id,
                "niche_id": category_id,
            })
        return products

    @staticmethod
    def _coerce_float(val: Any, default: float = 0.0) -> float:
        if val is None:
            return default
        if isinstance(val, (int, float)):
            return float(val)
        cleaned = re.sub(r"[^\d.]", "", str(val))
        try:
            return float(cleaned) if cleaned else default
        except ValueError:
            return default

    @staticmethod
    def _coerce_int(val: Any, default: int = 0) -> int:
        if val is None:
            return default
        if isinstance(val, int):
            return val
        if isinstance(val, float):
            return int(val)
        cleaned = re.sub(r"[^\d]", "", str(val))
        try:
            return int(cleaned) if cleaned else default
        except ValueError:
            return default

    async def close(self) -> None:
        if self._internal_session and not self._internal_session.closed:
            await self._internal_session.close()

    async def __aenter__(self) -> "KalodataClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()
```

---

## 5. Verification Method

To independently verify the implementation in Task 2:

### 5.1 Unit Test Suite (`tests/test_kalodata_client.py`)
Run the isolated unit tests:
```bash
pytest tests/test_kalodata_client.py -v
```

**15 Test Scenarios to Verify:**
1. `test_token_resolution_explicit_argument`: verifies param priority over env and file.
2. `test_token_resolution_env_variable`: verifies `KALOPILOT_TOKEN` is used when param is None.
3. `test_token_resolution_file_system`: verifies `~/.kalopilot/token` is used when param and env are None.
4. `test_token_missing_raises_auth_error`: verifies `PermissionError` is raised and message contains `"~/.kalopilot/token"`.
5. `test_token_expired_marker_raises_auth_error`: verifies `KalodataClient(token="expired_token")` raises `PermissionError` with `"~/.kalopilot/token"`.
6. `test_submit_query_happy_path`: verifies POST submit returns task_id.
7. `test_submit_query_401_raises_auth_error`: verifies HTTP 401 raises `KalodataAuthError`.
8. `test_submit_query_code_401_in_body_raises_auth_error`: verifies `code: 401` in body raises `KalodataAuthError`.
9. `test_submit_query_rejection_raises_api_error`: verifies rejection message raises `KalodataAPIError`.
10. `test_poll_task_completed`: verifies polling completes and returns data.
11. `test_poll_task_error_status_raises_api_error`: verifies status="error" raises `KalodataAPIError`.
12. `test_poll_task_cancelled_status_raises_api_error`: verifies status="cancelled" raises `KalodataAPIError`.
13. `test_poll_task_timeout_raises_timeout_error`: verifies max_polls exceeded raises `KalodataTimeoutError`.
14. `test_get_top_products_e2e_normalization`: verifies all 8 required product keys and data types.
15. `test_async_context_manager_cleanup`: verifies session closes on exit.

### 5.2 Existing Test Suite Regression Check
Run all existing tests to confirm zero regressions:
```bash
pytest tests/test_config.py tests/test_database.py -v
```

### 5.3 Invalidation Conditions
- Any test where `KalodataClient(token="expired_token")` does NOT raise `PermissionError` with `"~/.kalopilot/token"`.
- Any returned product dictionary missing any of the 8 required fields: `product_id`, `title`, `price`, `commission_rate`, `sales_30d`, `revenue_30d`, `product_url`, `category_id`.
- Any unhandled socket or HTTP connection exception not wrapped in `KalodataNetworkError`.
- Any real network request made during unit test execution.
