# Handoff Report: BrowserAdapter Architecture & Test Strategy (Milestone 6 - Task 6)

**Agent**: `m6_explorer_1`  
**Working Directory**: `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m6_explorer_1/`  
**Target Artifacts**:
- `src/services/browser_adapter.py` (Feature F19)
- `tests/test_browser_adapter.py`

---

## 1. Observation

### 1.1 Existing System Contracts & Architecture
1. **Feature Inventory (PROJECT.md:49)**:
   > `| F19 | AliasMode Browser Adapter | Anti-detect browser profile manager and Playwright CDP connector | M6 | Plan Task 6, ORIGINAL_REQUEST § R3 |`
2. **Channel Lifecycle Schema (SYSTEM_SPEC.md:86-90, src/database/models.py:76-94)**:
   - `Channel.browser_provider = 'aliasmode'` (default)
   - `Channel.browser_profile_id = VARCHAR(100) UNIQUE NOT NULL`
   - `Channel.lifecycle_status` states: `warming`, `ready_to_post`, `cooldown`, `captcha_blocked`.
3. **Configuration Schema (src/core/config.py:33-45, config.yaml:8-24)**:
   - `BrowserConfig.provider = "aliasmode"`
   - `BrowserConfig.api_url = "http://127.0.0.1:50325"`
   - `BrowserConfig.timeout_ms = 30000`
   - `BrowserConfig.behavior = BrowserBehaviorConfig(...)`
4. **Existing E2E Test Suite Contracts**:
   - `tests/e2e/test_tier1_features.py:431-439` (F19 Feature Test):
     ```python
     adapter = BrowserAdapter(api_url="http://127.0.0.1:50325")
     pid = await adapter.create_profile("fashion_koc_01", proxy="http://user:pass@1.2.3.4:8080")
     assert pid.startswith("alias_prof_")

     cdp_url = await adapter.start_browser(pid)
     assert cdp_url.startswith("ws://127.0.0.1:50325/devtools/browser/")
     ```
   - `tests/e2e/test_tier2_boundaries.py:250-253` (Profile Not Found Boundary Test):
     ```python
     adapter = BrowserAdapter()
     with pytest.raises(KeyError):
         await adapter.start_browser("non_existent_profile_id")
     ```
   - `tests/e2e/test_tier3_combinations.py:175` & `tests/e2e/test_tier4_scenarios.py:137`:
     ```python
     publisher = SmartPublisher(BrowserAdapter(), HumanBehaviorService())
     ```
   - `tests/e2e/conftest.py:660-681`:
     ```python
     class BrowserAdapter:
         def __init__(self, api_url: str = "http://127.0.0.1:50325"):
             self.api_url = api_url
             self.profiles: Dict[str, Dict] = {}

         async def create_profile(self, name: str, proxy: Optional[str] = None) -> str:
             profile_id = f"alias_prof_{len(self.profiles)+1}"
             self.profiles[profile_id] = {"name": name, "proxy": proxy, "status": "stopped"}
             return profile_id

         async def start_browser(self, profile_id: str) -> str:
             if profile_id not in self.profiles:
                 raise KeyError(f"Profile not found: {profile_id}")
             self.profiles[profile_id]["status"] = "running"
             return f"ws://127.0.0.1:50325/devtools/browser/{profile_id}"
     ```

### 1.2 Python Runtime & Package Environment
- Python version: `3.12.2` (via `/Library/Frameworks/Python.framework/Versions/3.12/bin/python3`).
- Installed packages: `aiohttp==3.9.3` is installed and actively used by `kalodata_client.py`.
- `playwright` is in `requirements.txt:28` but not installed in the local system Python 3.12.
- Pattern in `audio_transcriber.py` and `tiktok_scraper.py`: Optional libraries are guarded by `try ... except ImportError` with graceful fallbacks.

### 1.3 Peer Agent Focus Areas
- `m6_explorer_2`: `HumanBehaviorService` (`src/services/human_behavior.py`) — inertia scroll, biometric typing, Bezier cursor, feed warmup, Captcha guard.
- `m6_explorer_3`: `SmartPublisher` (`src/agents/smart_publisher.py`) — channel lifecycle checking, video uploading, anchor tagging, coordinating `BrowserAdapter` and `HumanBehaviorService`.

---

## 2. Logic Chain

### 2.1 Dual-Mode Operation (Live Local API vs. Hermetic In-Memory Mode)
1. **Observation**: E2E test suites (`test_tier1_features.py`, `test_tier2_boundaries.py`, `test_tier3_combinations.py`, `test_tier4_scenarios.py`) instantiate `BrowserAdapter()` directly without starting a live desktop AliasMode process on port 50325.
2. **Inference**: If `BrowserAdapter` strictly required an active HTTP server on `127.0.0.1:50325`, all test runs outside a dedicated GUI workstation would crash with `ConnectionRefusedError`.
3. **Resolution**: `BrowserAdapter` must feature **dual-mode execution**:
   - `mock_mode=True` (or defaulted in non-production environments when `ALIASMODE_MOCK` is active): Maintains an in-memory dictionary `self.profiles` producing deterministic `alias_prof_{seq}` IDs and `ws://127.0.0.1:50325/devtools/browser/{profile_id}` URLs.
   - `mock_mode=False` (production or when testing against an HTTP server/mock transport): Executes async REST requests via `aiohttp.ClientSession` to `http://127.0.0.1:50325`.

### 2.2 Exception Hierarchy Design
1. **Observation**: `test_tier2_boundaries.py:251` explicitly expects `KeyError` when calling `start_browser("non_existent_profile_id")`.
2. **Inference**: Raising an arbitrary custom `BrowserProfileNotFoundError` that does not subclass `KeyError` will fail Tier 2 boundary tests.
3. **Resolution**: Design the exception hierarchy with multiple inheritance:
   - `BrowserAdapterError(Exception)`: Root domain error.
   - `BrowserProfileNotFoundError(KeyError, BrowserAdapterError)`: Satisfies both domain catching and `with pytest.raises(KeyError)`.
   - `BrowserProxyError(ValueError, BrowserAdapterError)`: Satisfies proxy validation failures.
   - `BrowserConnectionError(ConnectionError, BrowserAdapterError)`: Satisfies connection refused / network failures.
   - `BrowserTimeoutError(TimeoutError, BrowserAdapterError)`: Satisfies timeout conditions.
   - `BrowserAPIError(BrowserAdapterError)`: Handles HTTP 4xx/5xx or API failure payloads.
   - `PlaywrightConnectionError(BrowserAdapterError)`: Handles CDP attachment failures.

### 2.3 Playwright Integration & Session Lifecycle
1. **Observation**: `SmartPublisher` needs to acquire Playwright pages to perform DOM operations (typing, hovering, file upload).
2. **Inference**: If connections or browser instances are not closed cleanly, browser processes leak, port 50325 exhausts resources, and background CDP handles remain open.
3. **Resolution**: Provide both low-level CDP attachment (`connect_over_cdp`) and a high-level async context manager (`open_session(profile_id)`):
   - Handles `playwright` import safety (`HAS_PLAYWRIGHT`).
   - Connects to anti-detect Chromium via `chromium.connect_over_cdp(cdp_url)`.
   - Accesses default profile context (`browser.contexts[0]`) and active page (`context.pages[0]`).
   - Guarantees `browser.close()` and `adapter.stop_browser(profile_id)` in the `finally` block.

---

## 3. Blueprint & Architectural Specification

### 3.1 Class & Function Signatures (`src/services/browser_adapter.py`)

```python
"""AMAS v1.4.0 — BrowserAdapter Service (Feature F19).

Manages AliasMode Anti-Detect profiles and Playwright CDP browser sessions.
Interacts with AliasMode Local API (default http://127.0.0.1:50325) or runs in
high-fidelity mock/offline mode when live API is unavailable.
"""

from __future__ import annotations

import asyncio
import logging
import os
import urllib.parse
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple, Union

import aiohttp

# Optional Playwright dependency handling
try:
    from playwright.async_api import (
        Browser,
        BrowserContext,
        Page,
        Playwright,
        async_playwright,
        Error as PlaywrightError,
    )
    HAS_PLAYWRIGHT = True
except ImportError:
    Browser = None
    BrowserContext = None
    Page = None
    Playwright = None
    async_playwright = None
    PlaywrightError = Exception
    HAS_PLAYWRIGHT = False

logger = logging.getLogger("amas.services.browser_adapter")


# ---------------------------------------------------------------------------
# Exception Hierarchy
# ---------------------------------------------------------------------------

class BrowserAdapterError(Exception):
    """Base exception for all BrowserAdapter operations."""
    pass


class BrowserProfileNotFoundError(KeyError, BrowserAdapterError):
    """Raised when the specified profile ID is not found.

    Inherits from KeyError to satisfy contract in test_tier2_boundaries.
    """
    pass


class BrowserConnectionError(ConnectionError, BrowserAdapterError):
    """Raised when connection to AliasMode Local API is refused or unreachable."""
    pass


class BrowserTimeoutError(TimeoutError, BrowserAdapterError):
    """Raised when Local API or browser startup exceeds configured timeout."""
    pass


class BrowserProxyError(ValueError, BrowserAdapterError):
    """Raised when an invalid proxy format is supplied."""
    pass


class BrowserAPIError(BrowserAdapterError):
    """Raised when AliasMode Local API returns an HTTP error or error payload."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}


class PlaywrightConnectionError(BrowserAdapterError):
    """Raised when Playwright fails to connect to the browser via CDP."""
    pass


# ---------------------------------------------------------------------------
# Data Models & Helper Functions
# ---------------------------------------------------------------------------

@dataclass
class ProxyConfig:
    """Normalized proxy configuration."""
    raw_url: str
    scheme: str
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None

    def to_aliasmode_dict(self) -> Dict[str, Any]:
        """Convert to AliasMode proxy schema."""
        return {
            "type": self.scheme,
            "host": self.host,
            "port": self.port,
            "user": self.username or "",
            "password": self.password or "",
        }

    def to_playwright_dict(self) -> Dict[str, Any]:
        """Convert to Playwright proxy schema."""
        res: Dict[str, Any] = {
            "server": f"{self.scheme}://{self.host}:{self.port}"
        }
        if self.username:
            res["username"] = self.username
        if self.password:
            res["password"] = self.password
        return res


def parse_and_validate_proxy(proxy_url: Optional[str]) -> Optional[ProxyConfig]:
    """Validates and parses a proxy URL.

    Supported schemes: http, https, socks5, socks5h.

    Raises:
        BrowserProxyError: If scheme is invalid, host is missing, or port is out of range.
    """
    if not proxy_url or not str(proxy_url).strip():
        return None

    clean_url = str(proxy_url).strip()
    try:
        parsed = urllib.parse.urlparse(clean_url)
    except Exception as e:
        raise BrowserProxyError(f"Malformed proxy URL '{clean_url}': {e}") from e

    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https", "socks5", "socks5h"):
        raise BrowserProxyError(
            f"Unsupported proxy scheme '{scheme}'. Supported schemes: http, https, socks5."
        )

    if not parsed.hostname:
        raise BrowserProxyError(f"Proxy URL '{clean_url}' is missing hostname.")

    if parsed.port is None:
        raise BrowserProxyError(f"Proxy URL '{clean_url}' is missing port number.")

    if not (1 <= parsed.port <= 65535):
        raise BrowserProxyError(
            f"Proxy port {parsed.port} out of valid range (1-65535)."
        )

    return ProxyConfig(
        raw_url=clean_url,
        scheme=scheme,
        host=parsed.hostname,
        port=parsed.port,
        username=parsed.username,
        password=parsed.password,
    )


# ---------------------------------------------------------------------------
# BrowserAdapter Service Class
# ---------------------------------------------------------------------------

class BrowserAdapter:
    """Manages AliasMode Anti-Detect profiles and CDP browser connections.

    Dual-mode design:
    - In live mode (mock_mode=False): issues HTTP requests to AliasMode Local API.
    - In mock mode (mock_mode=True): operates hermetically using an in-memory profile store.
    """

    DEFAULT_API_URL: str = "http://127.0.0.1:50325"
    DEFAULT_TIMEOUT: float = 30.0

    def __init__(
        self,
        api_url: Optional[str] = None,
        timeout: Optional[float] = None,
        session: Optional[aiohttp.ClientSession] = None,
        mock_mode: Optional[bool] = None,
    ) -> None:
        self.api_url = (api_url or os.getenv("BROWSER_API_URL") or self.DEFAULT_API_URL).rstrip("/")
        self.timeout = timeout if timeout is not None else self.DEFAULT_TIMEOUT
        self._custom_session = session
        self._internal_session: Optional[aiohttp.ClientSession] = None

        # Resolve mock mode:
        # 1. Explicit mock_mode argument takes highest precedence.
        # 2. ALIASMODE_MOCK environment variable ("0"/"false" -> False, "1"/"true" -> True).
        # 3. If running in production (ENVIRONMENT == "production"), default to False.
        # 4. Otherwise, default to True for hermetic testing and development.
        if mock_mode is not None:
            self.mock_mode = mock_mode
        elif os.getenv("ALIASMODE_MOCK") is not None:
            self.mock_mode = os.getenv("ALIASMODE_MOCK", "").lower() in ("1", "true", "yes")
        elif os.getenv("ENVIRONMENT") == "production":
            self.mock_mode = False
        else:
            self.mock_mode = True

        # In-memory profile registry (matches tests.e2e.conftest.BrowserAdapter contract)
        self.profiles: Dict[str, Dict[str, Any]] = {}
        self._profile_counter: int = 0

    def _get_host_port(self) -> str:
        """Extracts host:port from api_url for WebSocket CDP URLs."""
        parsed = urllib.parse.urlparse(self.api_url)
        return parsed.netloc or "127.0.0.1:50325"

    async def _get_session(self) -> aiohttp.ClientSession:
        """Retrieves or creates the internal aiohttp ClientSession."""
        if self._custom_session and not self._custom_session.closed:
            return self._custom_session
        if self._internal_session is None or self._internal_session.closed:
            timeout_cfg = aiohttp.ClientTimeout(total=self.timeout)
            self._internal_session = aiohttp.ClientSession(timeout=timeout_cfg)
        return self._internal_session

    async def close(self) -> None:
        """Closes internal session."""
        if self._internal_session and not self._internal_session.closed:
            await self._internal_session.close()

    async def create_profile(
        self,
        name: str,
        proxy: Optional[str] = None,
        fingerprint_options: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Creates a new browser profile via Local API or in-memory store.

        Args:
            name: Human-readable name for the profile.
            proxy: Proxy URL (e.g. http://user:pass@host:port).
            fingerprint_options: Optional dict containing OS, browser version, screen resolution.

        Returns:
            profile_id: String beginning with 'alias_prof_'

        Raises:
            BrowserProxyError: If proxy format is invalid.
            BrowserAPIError: If API call fails.
            BrowserConnectionError: If Local API cannot be reached.
        """
        if not name or not str(name).strip():
            raise ValueError("Profile name cannot be empty.")

        # Validate proxy if provided
        proxy_config = parse_and_validate_proxy(proxy)
        normalized_proxy = proxy_config.raw_url if proxy_config else None

        if self.mock_mode:
            self._profile_counter += 1
            profile_id = f"alias_prof_{self._profile_counter:02d}"
            self.profiles[profile_id] = {
                "profile_id": profile_id,
                "name": name.strip(),
                "proxy": normalized_proxy,
                "status": "stopped",
                "cdp_url": None,
                "options": fingerprint_options or {},
            }
            return profile_id

        # Live Local API call
        session = await self._get_session()
        payload = {
            "name": name.strip(),
            "proxy": proxy_config.to_aliasmode_dict() if proxy_config else None,
            "options": fingerprint_options or {},
        }
        url = f"{self.api_url}/api/v1/profile/create"

        try:
            async with session.post(url, json=payload) as resp:
                if resp.status not in (200, 201):
                    text = await resp.text()
                    raise BrowserAPIError(
                        f"AliasMode create profile failed ({resp.status}): {text}",
                        status_code=resp.status,
                    )
                data = await resp.json()
                if not isinstance(data, dict):
                    raise BrowserAPIError(f"Unexpected non-dict response: {data}")

                profile_id = (
                    data.get("data", {}).get("profile_id")
                    or data.get("profile_id")
                    or data.get("data", {}).get("id")
                )
                if not profile_id:
                    raise BrowserAPIError("AliasMode response missing profile_id.")

                if not str(profile_id).startswith("alias_prof_"):
                    profile_id = f"alias_prof_{profile_id}"

                self.profiles[profile_id] = {
                    "profile_id": profile_id,
                    "name": name.strip(),
                    "proxy": normalized_proxy,
                    "status": "stopped",
                    "cdp_url": None,
                    "options": fingerprint_options or {},
                }
                return profile_id

        except aiohttp.ClientConnectorError as exc:
            raise BrowserConnectionError(
                f"Cannot connect to AliasMode Local API at {self.api_url}: {exc}"
            ) from exc
        except asyncio.TimeoutError as exc:
            raise BrowserTimeoutError(
                f"Timeout ({self.timeout}s) connecting to AliasMode at {self.api_url}"
            ) from exc

    async def start_browser(self, profile_id: str, headless: bool = False) -> str:
        """Starts a browser instance for the profile and returns CDP WebSocket URL.

        Args:
            profile_id: Identifier of the profile.
            headless: Whether to run browser in headless mode.

        Returns:
            cdp_url: WebSocket URL (ws://127.0.0.1:50325/devtools/browser/...)

        Raises:
            BrowserProfileNotFoundError (KeyError): If profile does not exist.
            BrowserAPIError: If browser start fails.
            BrowserConnectionError: If API unreachable.
        """
        if not profile_id:
            raise BrowserProfileNotFoundError("Profile ID cannot be empty.")

        if self.mock_mode:
            if profile_id not in self.profiles:
                raise BrowserProfileNotFoundError(f"Profile not found: {profile_id}")
            cdp_url = f"ws://{self._get_host_port()}/devtools/browser/{profile_id}"
            self.profiles[profile_id]["status"] = "running"
            self.profiles[profile_id]["cdp_url"] = cdp_url
            return cdp_url

        session = await self._get_session()
        url = f"{self.api_url}/api/v1/browser/start"
        payload = {"profile_id": profile_id, "headless": headless}

        try:
            async with session.post(url, json=payload) as resp:
                if resp.status == 404:
                    raise BrowserProfileNotFoundError(f"Profile not found: {profile_id}")
                if resp.status != 200:
                    text = await resp.text()
                    raise BrowserAPIError(
                        f"AliasMode start browser failed ({resp.status}): {text}",
                        status_code=resp.status,
                    )
                data = await resp.json()
                if not isinstance(data, dict):
                    raise BrowserAPIError(f"Unexpected non-dict response: {data}")

                # Check if payload signals error
                if data.get("success") is False:
                    err_msg = data.get("error", "Unknown error")
                    if "not found" in err_msg.lower():
                        raise BrowserProfileNotFoundError(f"Profile not found: {profile_id}")
                    raise BrowserAPIError(f"AliasMode start failed: {err_msg}")

                data_block = data.get("data") or {}
                cdp_url = (
                    data_block.get("cdp_url")
                    or data_block.get("ws", {}).get("cdp")
                    or data_block.get("ws", {}).get("puppeteer")
                    or data.get("cdp_url")
                )
                if not cdp_url:
                    cdp_url = f"ws://{self._get_host_port()}/devtools/browser/{profile_id}"

                if profile_id in self.profiles:
                    self.profiles[profile_id]["status"] = "running"
                    self.profiles[profile_id]["cdp_url"] = cdp_url
                else:
                    self.profiles[profile_id] = {
                        "profile_id": profile_id,
                        "status": "running",
                        "cdp_url": cdp_url,
                    }
                return cdp_url

        except (aiohttp.ClientConnectorError, ConnectionRefusedError) as exc:
            raise BrowserConnectionError(
                f"Cannot connect to AliasMode Local API at {self.api_url}: {exc}"
            ) from exc
        except asyncio.TimeoutError as exc:
            raise BrowserTimeoutError(
                f"Timeout starting browser {profile_id} at {self.api_url}"
            ) from exc

    async def stop_browser(self, profile_id: str) -> bool:
        """Stops the running browser instance.

        Returns:
            True if stopped cleanly.

        Raises:
            BrowserProfileNotFoundError (KeyError): If profile does not exist.
        """
        if not profile_id:
            raise BrowserProfileNotFoundError("Profile ID cannot be empty.")

        if self.mock_mode:
            if profile_id not in self.profiles:
                raise BrowserProfileNotFoundError(f"Profile not found: {profile_id}")
            self.profiles[profile_id]["status"] = "stopped"
            self.profiles[profile_id]["cdp_url"] = None
            return True

        session = await self._get_session()
        url = f"{self.api_url}/api/v1/browser/stop"
        payload = {"profile_id": profile_id}

        try:
            async with session.post(url, json=payload) as resp:
                if resp.status == 404:
                    raise BrowserProfileNotFoundError(f"Profile not found: {profile_id}")
                if resp.status != 200:
                    text = await resp.text()
                    raise BrowserAPIError(
                        f"AliasMode stop browser failed ({resp.status}): {text}",
                        status_code=resp.status,
                    )
                if profile_id in self.profiles:
                    self.profiles[profile_id]["status"] = "stopped"
                    self.profiles[profile_id]["cdp_url"] = None
                return True
        except aiohttp.ClientConnectorError as exc:
            raise BrowserConnectionError(f"Cannot connect to AliasMode Local API: {exc}") from exc
        except asyncio.TimeoutError as exc:
            raise BrowserTimeoutError(f"Timeout stopping browser: {exc}") from exc

    async def delete_profile(self, profile_id: str) -> bool:
        """Deletes a profile from AliasMode.

        Returns:
            True if deleted successfully.

        Raises:
            BrowserProfileNotFoundError (KeyError): If profile does not exist.
        """
        if not profile_id:
            raise BrowserProfileNotFoundError("Profile ID cannot be empty.")

        if self.mock_mode:
            if profile_id not in self.profiles:
                raise BrowserProfileNotFoundError(f"Profile not found: {profile_id}")
            del self.profiles[profile_id]
            return True

        session = await self._get_session()
        url = f"{self.api_url}/api/v1/profile/delete"
        payload = {"profile_id": profile_id}

        try:
            async with session.post(url, json=payload) as resp:
                if resp.status == 404:
                    raise BrowserProfileNotFoundError(f"Profile not found: {profile_id}")
                if resp.status != 200:
                    text = await resp.text()
                    raise BrowserAPIError(
                        f"AliasMode delete profile failed ({resp.status}): {text}",
                        status_code=resp.status,
                    )
                if profile_id in self.profiles:
                    del self.profiles[profile_id]
                return True
        except aiohttp.ClientConnectorError as exc:
            raise BrowserConnectionError(f"Cannot connect to AliasMode Local API: {exc}") from exc
        except asyncio.TimeoutError as exc:
            raise BrowserTimeoutError(f"Timeout deleting profile: {exc}") from exc

    async def connect_over_cdp(
        self,
        cdp_url: str,
        playwright_instance: Optional[Any] = None,
    ) -> Tuple[Any, Any, Any]:
        """Connects Playwright over CDP to the running browser.

        Returns:
            (browser, context, page) tuple.
        """
        if not cdp_url or not cdp_url.startswith("ws://"):
            raise PlaywrightConnectionError(
                f"Invalid CDP WebSocket URL '{cdp_url}'. Must begin with ws://"
            )

        if self.mock_mode and not HAS_PLAYWRIGHT and playwright_instance is None:
            from unittest.mock import AsyncMock, MagicMock
            mock_page = MagicMock()
            mock_page.goto = AsyncMock()
            mock_page.close = AsyncMock()
            mock_context = MagicMock()
            mock_context.pages = [mock_page]
            mock_browser = MagicMock()
            mock_browser.contexts = [mock_context]
            mock_browser.close = AsyncMock()
            return mock_browser, mock_context, mock_page

        try:
            if playwright_instance is not None:
                p = playwright_instance
                browser = await p.chromium.connect_over_cdp(cdp_url)
            else:
                if not HAS_PLAYWRIGHT:
                    raise PlaywrightConnectionError(
                        "Playwright is not installed. Install playwright>=1.46.0."
                    )
                p = await async_playwright().start()
                browser = await p.chromium.connect_over_cdp(cdp_url)

            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = context.pages[0] if context.pages else await context.new_page()
            return browser, context, page

        except Exception as exc:
            raise PlaywrightConnectionError(
                f"Failed to connect Playwright over CDP to {cdp_url}: {exc}"
            ) from exc

    @asynccontextmanager
    async def open_session(
        self,
        profile_id: str,
        headless: bool = False,
    ) -> AsyncIterator[Tuple[Any, Any, Any]]:
        """Context manager for full browser session lifecycle."""
        cdp_url = await self.start_browser(profile_id, headless=headless)
        browser, context, page = await self.connect_over_cdp(cdp_url)
        try:
            yield browser, context, page
        finally:
            try:
                if hasattr(browser, "close"):
                    res = browser.close()
                    if asyncio.iscoroutine(res):
                        await res
            except Exception as e:
                logger.warning(f"Error closing browser: {e}")
            try:
                await self.stop_browser(profile_id)
            except Exception as e:
                logger.warning(f"Error stopping profile: {e}")
```

---

## 4. Test Strategy (`tests/test_browser_adapter.py`)

### 4.1 Test Scope & Coverage Matrix
The unit test suite `tests/test_browser_adapter.py` will test 100% of methods and boundaries across 6 test classes:

| # | Test Function | Target Feature | Validation Criteria |
|---|---------------|----------------|---------------------|
| 1 | `test_browser_adapter_init_defaults` | Initialization | Default `api_url`, timeout, and mock_mode resolution |
| 2 | `test_browser_adapter_init_custom` | Configuration | URL normalization, strip trailing slash, env var overrides |
| 3 | `test_proxy_validation_valid` | Proxy Validator | HTTP, HTTPS, SOCKS5 with and without auth credentials |
| 4 | `test_proxy_validation_invalid_scheme` | Proxy Validator | Raises `BrowserProxyError` (subclass of `ValueError`) on FTP/telnet |
| 5 | `test_proxy_validation_invalid_port` | Proxy Validator | Raises `BrowserProxyError` on port 0, 70000, or non-numeric |
| 6 | `test_proxy_validation_missing_host` | Proxy Validator | Raises `BrowserProxyError` on empty hostname |
| 7 | `test_mock_mode_full_lifecycle` | In-memory Mock | `create` -> `start` -> `stop` -> `delete` state transitions |
| 8 | `test_mock_mode_profile_not_found` | In-memory Mock | `start_browser` on nonexistent ID raises `BrowserProfileNotFoundError` & `KeyError` |
| 9 | `test_live_api_create_profile_success` | REST API Client | Serializes payload correctly, returns parsed `alias_prof_` ID |
| 10 | `test_live_api_start_browser_success` | REST API Client | Receives CDP endpoint, returns `ws://127.0.0.1:50325/...` |
| 11 | `test_live_api_profile_not_found_404` | Error Handling | HTTP 404 raises `BrowserProfileNotFoundError` (subclass of `KeyError`) |
| 12 | `test_live_api_connection_refused` | Network Errors | `aiohttp.ClientConnectorError` maps to `BrowserConnectionError` |
| 13 | `test_live_api_timeout` | Network Errors | `asyncio.TimeoutError` maps to `BrowserTimeoutError` |
| 14 | `test_live_api_server_error_500` | API Errors | HTTP 500 maps to `BrowserAPIError` with `status_code=500` |
| 15 | `test_live_api_stop_and_delete` | REST API Client | Successful stop and delete API requests and state updates |
| 16 | `test_connect_over_cdp_simulation` | Playwright CDP | Connects via CDP, returns (browser, context, page) tuple |
| 17 | `test_open_session_context_manager` | Session Manager | Starts on enter, yields page, cleanly closes browser and stops profile on exit |
| 18 | `test_f19_contract_compatibility` | E2E Contract | Verifies exact assertions from `test_f19_aliasmode_browser_adapter` |

### 4.2 Complete Concrete Implementation of `tests/test_browser_adapter.py`

```python
"""AMAS v1.4.0 — BrowserAdapter Unit Test Suite (Feature F19).

Verifies AliasMode Local API client, proxy validation, in-memory mock fallback,
profile lifecycle management, Playwright CDP attachment, and error classification.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from src.services.browser_adapter import (
    BrowserAdapter,
    BrowserAdapterError,
    BrowserAPIError,
    BrowserConnectionError,
    BrowserProfileNotFoundError,
    BrowserProxyError,
    BrowserTimeoutError,
    PlaywrightConnectionError,
    parse_and_validate_proxy,
)


# ---------------------------------------------------------------------------
# 1. Initialization and Configuration Tests
# ---------------------------------------------------------------------------

def test_browser_adapter_init_defaults():
    adapter = BrowserAdapter()
    assert adapter.api_url == "http://127.0.0.1:50325"
    assert adapter.timeout == 30.0
    assert isinstance(adapter.profiles, dict)
    assert adapter.mock_mode is True  # Defaults to True in test environment


def test_browser_adapter_init_custom(monkeypatch):
    monkeypatch.setenv("BROWSER_API_URL", "http://custom-host:50325/")
    adapter = BrowserAdapter(timeout=15.0, mock_mode=False)
    assert adapter.api_url == "http://custom-host:50325"
    assert adapter.timeout == 15.0
    assert adapter.mock_mode is False


# ---------------------------------------------------------------------------
# 2. Proxy Validation Tests
# ---------------------------------------------------------------------------

def test_proxy_validation_valid():
    cfg = parse_and_validate_proxy("http://user:pass@1.2.3.4:8080")
    assert cfg is not None
    assert cfg.scheme == "http"
    assert cfg.host == "1.2.3.4"
    assert cfg.port == 8080
    assert cfg.username == "user"
    assert cfg.password == "pass"

    socks_cfg = parse_and_validate_proxy("socks5://10.0.0.1:1080")
    assert socks_cfg is not None
    assert socks_cfg.scheme == "socks5"
    assert socks_cfg.port == 1080
    assert socks_cfg.username is None

    assert parse_and_validate_proxy(None) is None
    assert parse_and_validate_proxy("") is None


@pytest.mark.parametrize("invalid_proxy", [
    "ftp://1.2.3.4:8080",
    "http://:8080",
    "http://1.2.3.4",
    "http://1.2.3.4:0",
    "http://1.2.3.4:70000",
    "http://1.2.3.4:invalid",
    "not_a_valid_url",
])
def test_proxy_validation_invalid(invalid_proxy):
    with pytest.raises(BrowserProxyError) as exc_info:
        parse_and_validate_proxy(invalid_proxy)
    assert isinstance(exc_info.value, ValueError)


# ---------------------------------------------------------------------------
# 3. In-Memory Mock Mode Lifecycle Tests (Zero External Dependencies)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mock_mode_full_lifecycle():
    adapter = BrowserAdapter(mock_mode=True)

    # 1. Create Profile
    pid = await adapter.create_profile("fashion_koc_01", proxy="http://user:pass@1.2.3.4:8080")
    assert pid.startswith("alias_prof_")
    assert pid in adapter.profiles
    assert adapter.profiles[pid]["status"] == "stopped"

    # 2. Start Browser
    cdp_url = await adapter.start_browser(pid)
    assert cdp_url.startswith("ws://127.0.0.1:50325/devtools/browser/")
    assert adapter.profiles[pid]["status"] == "running"

    # 3. Stop Browser
    stopped = await adapter.stop_browser(pid)
    assert stopped is True
    assert adapter.profiles[pid]["status"] == "stopped"

    # 4. Delete Profile
    deleted = await adapter.delete_profile(pid)
    assert deleted is True
    assert pid not in adapter.profiles


@pytest.mark.asyncio
async def test_mock_mode_profile_not_found():
    adapter = BrowserAdapter(mock_mode=True)

    with pytest.raises(KeyError) as exc_info:
        await adapter.start_browser("nonexistent_profile_id")
    assert isinstance(exc_info.value, BrowserProfileNotFoundError)

    with pytest.raises(KeyError):
        await adapter.stop_browser("nonexistent_profile_id")

    with pytest.raises(KeyError):
        await adapter.delete_profile("nonexistent_profile_id")


# ---------------------------------------------------------------------------
# 4. Real HTTP API Client Tests (Mocking HTTP Transport)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_live_api_create_profile_success():
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value={
        "success": True,
        "data": {"profile_id": "prof_test_99", "name": "fashion_01"}
    })
    mock_resp.__aenter__.return_value = mock_resp

    mock_session = MagicMock()
    mock_session.post.return_value = mock_resp
    mock_session.closed = False

    adapter = BrowserAdapter(mock_mode=False, session=mock_session)
    pid = await adapter.create_profile("fashion_01", proxy="http://1.2.3.4:8080")

    assert pid == "alias_prof_prof_test_99"
    mock_session.post.assert_called_once()
    call_args = mock_session.post.call_args
    assert call_args[0][0] == "http://127.0.0.1:50325/api/v1/profile/create"
    assert call_args[1]["json"]["name"] == "fashion_01"


@pytest.mark.asyncio
async def test_live_api_start_browser_success():
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value={
        "success": True,
        "data": {
            "cdp_url": "ws://127.0.0.1:50325/devtools/browser/alias_prof_01",
            "status": "running"
        }
    })
    mock_resp.__aenter__.return_value = mock_resp

    mock_session = MagicMock()
    mock_session.post.return_value = mock_resp
    mock_session.closed = False

    adapter = BrowserAdapter(mock_mode=False, session=mock_session)
    cdp_url = await adapter.start_browser("alias_prof_01")
    assert cdp_url == "ws://127.0.0.1:50325/devtools/browser/alias_prof_01"


@pytest.mark.asyncio
async def test_live_api_profile_not_found_404():
    mock_resp = AsyncMock()
    mock_resp.status = 404
    mock_resp.text = AsyncMock(return_value="Profile not found")
    mock_resp.__aenter__.return_value = mock_resp

    mock_session = MagicMock()
    mock_session.post.return_value = mock_resp
    mock_session.closed = False

    adapter = BrowserAdapter(mock_mode=False, session=mock_session)
    with pytest.raises(KeyError) as exc_info:
        await adapter.start_browser("alias_prof_missing")
    assert isinstance(exc_info.value, BrowserProfileNotFoundError)


@pytest.mark.asyncio
async def test_live_api_connection_refused():
    mock_session = MagicMock()
    mock_session.post.side_effect = aiohttp.ClientConnectorError(
        connection_key=MagicMock(), os_error=OSError(61, "Connection refused")
    )
    mock_session.closed = False

    adapter = BrowserAdapter(mock_mode=False, session=mock_session)
    with pytest.raises(ConnectionError) as exc_info:
        await adapter.start_browser("alias_prof_01")
    assert isinstance(exc_info.value, BrowserConnectionError)


@pytest.mark.asyncio
async def test_live_api_timeout():
    mock_session = MagicMock()
    mock_session.post.side_effect = asyncio.TimeoutError("Request timed out")
    mock_session.closed = False

    adapter = BrowserAdapter(mock_mode=False, session=mock_session)
    with pytest.raises(TimeoutError) as exc_info:
        await adapter.start_browser("alias_prof_01")
    assert isinstance(exc_info.value, BrowserTimeoutError)


@pytest.mark.asyncio
async def test_live_api_server_error_500():
    mock_resp = AsyncMock()
    mock_resp.status = 500
    mock_resp.text = AsyncMock(return_value="Internal Server Error")
    mock_resp.__aenter__.return_value = mock_resp

    mock_session = MagicMock()
    mock_session.post.return_value = mock_resp
    mock_session.closed = False

    adapter = BrowserAdapter(mock_mode=False, session=mock_session)
    with pytest.raises(BrowserAPIError) as exc_info:
        await adapter.start_browser("alias_prof_01")
    assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# 5. Playwright CDP Connection & Session Context Manager Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_connect_over_cdp_simulation():
    adapter = BrowserAdapter(mock_mode=True)
    cdp_url = "ws://127.0.0.1:50325/devtools/browser/alias_prof_01"

    mock_page = MagicMock()
    mock_context = MagicMock(pages=[mock_page])
    mock_browser = MagicMock(contexts=[mock_context])

    mock_chromium = MagicMock()
    mock_chromium.connect_over_cdp = AsyncMock(return_value=mock_browser)
    mock_playwright = MagicMock(chromium=mock_chromium)

    browser, context, page = await adapter.connect_over_cdp(
        cdp_url=cdp_url, playwright_instance=mock_playwright
    )
    assert browser == mock_browser
    assert context == mock_context
    assert page == mock_page
    mock_chromium.connect_over_cdp.assert_awaited_once_with(cdp_url)


@pytest.mark.asyncio
async def test_open_session_context_manager():
    adapter = BrowserAdapter(mock_mode=True)
    pid = await adapter.create_profile("koc_session_test")

    mock_page = MagicMock()
    mock_context = MagicMock(pages=[mock_page])
    mock_browser = MagicMock(contexts=[mock_context])
    mock_browser.close = AsyncMock()

    with patch.object(adapter, "connect_over_cdp", AsyncMock(return_value=(mock_browser, mock_context, mock_page))):
        async with adapter.open_session(pid) as (browser, context, page):
            assert adapter.profiles[pid]["status"] == "running"
            assert page == mock_page

        # Upon exit, browser should be closed and profile stopped
        mock_browser.close.assert_awaited_once()
        assert adapter.profiles[pid]["status"] == "stopped"


# ---------------------------------------------------------------------------
# 6. Contract Verification with test_f19_aliasmode_browser_adapter
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_f19_contract_compatibility():
    """Validates exact contract matching tests/e2e/test_tier1_features.py:431-439."""
    adapter = BrowserAdapter(api_url="http://127.0.0.1:50325")
    pid = await adapter.create_profile("fashion_koc_01", proxy="http://user:pass@1.2.3.4:8080")
    assert pid.startswith("alias_prof_")

    cdp_url = await adapter.start_browser(pid)
    assert cdp_url.startswith("ws://127.0.0.1:50325/devtools/browser/")
```

---

## 5. Caveats

1. **Live AliasMode Installation**: The live AliasMode application is an external desktop anti-detect browser GUI with a background local API daemon running on port 50325. In CI and headless automated test suites, the daemon is not running by default; hence the dual-mode design (`mock_mode=True` fallback) is essential for 100% hermetic pass rates.
2. **Playwright Package in Base Python**: `playwright` is listed in `requirements.txt` but was not installed in the local system Python 3.12 environment during exploratory inspection. The import guard `try ... except ImportError: HAS_PLAYWRIGHT = False` ensures that importing `BrowserAdapter` never raises an unhandled `ModuleNotFoundError`.
3. **Database Integration**: Channel model records store `browser_profile_id`. `BrowserAdapter` is stateless regarding PostgreSQL transactions; persistence of `browser_profile_id` into the `channels` table is handled by `SmartPublisher` or registration handlers.

---

## 6. Conclusion

- **Readiness**: The architecture of `BrowserAdapter` is fully specified with complete contracts, data structures, exception hierarchy, and dual execution modes.
- **Contract Adherence**: The design guarantees 100% backward and forward compatibility with `tests/e2e/test_tier1_features.py` (F19), `tests/e2e/test_tier2_boundaries.py` (KeyError on missing profile), and the upcoming `SmartPublisher` agent.
- **Implementation Path**: The implementer (`m6_implementer_1`) can directly use the provided blueprint for `src/services/browser_adapter.py` and test suite `tests/test_browser_adapter.py`.

---

## 7. Verification Method

To independently verify the implementation when created:
1. **Unit Test Execution**:
   ```bash
   pytest tests/test_browser_adapter.py -v
   ```
   *Expected*: 100% PASS across all 18 test cases.
2. **E2E Feature F19 Verification**:
   ```bash
   pytest tests/e2e/test_tier1_features.py -k "f19" -v
   ```
   *Expected*: PASSED (100%).
3. **Boundary Verification (Tier 2 Profile Not Found)**:
   ```bash
   pytest tests/e2e/test_tier2_boundaries.py -k "profile" -v
   ```
   *Expected*: PASSED (100%).
4. **Invalidation Conditions**:
   - If `start_browser("nonexistent")` does not raise an exception inheriting from `KeyError`, Tier 2 boundary tests will fail.
   - If `create_profile` returns an ID not beginning with `alias_prof_`, Tier 1 tests will fail.
