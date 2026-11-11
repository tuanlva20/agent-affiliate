"""AMAS v1.4.0 — BrowserAdapter Service (Feature F19).

Manages AliasMode Anti-Detect profiles and Playwright CDP browser sessions.
Interacts with AliasMode Local API (default http://127.0.0.1:50325) or runs in
high-fidelity mock/offline mode when live API is unavailable.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import os
import urllib.parse
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple, Union

import aiohttp

# Optional Playwright dependency handling
try:
    from playwright.async_api import (  # type: ignore
        Browser,
        BrowserContext,
        Page,
        Playwright,
        async_playwright,
    )
    HAS_PLAYWRIGHT = True
except ImportError:
    Browser = None  # type: ignore
    BrowserContext = None  # type: ignore
    Page = None  # type: ignore
    Playwright = None  # type: ignore
    async_playwright = None  # type: ignore
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
        scheme = (parsed.scheme or "").lower()
        if scheme not in ("http", "https", "socks5", "socks5h"):
            raise BrowserProxyError(
                f"Unsupported proxy scheme '{scheme}'. Supported schemes: http, https, socks5."
            )

        if not parsed.hostname:
            raise BrowserProxyError(f"Proxy URL '{clean_url}' is missing hostname.")

        port = parsed.port
        if port is None:
            raise BrowserProxyError(f"Proxy URL '{clean_url}' is missing port number.")

        if not (1 <= port <= 65535):
            raise BrowserProxyError(
                f"Proxy port {port} out of valid range (1-65535)."
            )

        return ProxyConfig(
            raw_url=clean_url,
            scheme=scheme,
            host=parsed.hostname,
            port=port,
            username=parsed.username,
            password=parsed.password,
        )
    except BrowserProxyError:
        raise
    except Exception as e:
        raise BrowserProxyError(f"Malformed proxy URL '{clean_url}': {e}") from e


# ---------------------------------------------------------------------------
# In-Memory Stubs for Offline & Mock Automation (Feature F19)
# ---------------------------------------------------------------------------

class StubMouse:
    """In-memory stub for Playwright Mouse emulation without external mocks."""

    def __init__(self) -> None:
        self.x: float = 0.0
        self.y: float = 0.0
        self.is_down: bool = False
        self.scroll_history: List[Tuple[float, float]] = []

    async def move(self, x: float, y: float, **kwargs: Any) -> None:
        self.x = float(x)
        self.y = float(y)

    async def down(self, button: str = "left", **kwargs: Any) -> None:
        self.is_down = True

    async def up(self, button: str = "left", **kwargs: Any) -> None:
        self.is_down = False

    async def click(self, x: float, y: float, **kwargs: Any) -> None:
        await self.move(x, y)
        await self.down()
        await self.up()

    async def wheel(self, delta_x: float, delta_y: float) -> None:
        self.scroll_history.append((float(delta_x), float(delta_y)))


class StubKeyboard:
    """In-memory stub for Playwright Keyboard emulation without external mocks."""

    def __init__(self) -> None:
        self.typed_chars: List[str] = []
        self.pressed_keys: List[str] = []

    async def type(self, text: str, delay: float = 0, **kwargs: Any) -> None:
        self.typed_chars.extend(list(text))

    async def press(self, key: str, delay: float = 0, **kwargs: Any) -> None:
        self.pressed_keys.append(str(key))
        self.typed_chars.append(str(key))

    async def down(self, key: str) -> None:
        pass

    async def up(self, key: str) -> None:
        pass


class StubPage:
    """In-memory stub for Playwright Page supporting full automation lifecycle."""

    def __init__(
        self,
        url: str = "about:blank",
        context: Optional[StubBrowserContext] = None,
    ) -> None:
        self.url: str = url
        self.context: Optional[StubBrowserContext] = context
        self.is_closed: bool = False
        self.mouse: StubMouse = StubMouse()
        self.keyboard: StubKeyboard = StubKeyboard()
        self.input_files: Dict[str, Any] = {}
        self.clicked_selectors: List[str] = []
        self.hovered_selectors: List[str] = []
        self.viewport_size: Dict[str, int] = {"width": 1280, "height": 800}

    async def goto(self, url: str, **kwargs: Any) -> Any:
        self.url = str(url)
        return None

    async def close(self) -> None:
        self.is_closed = True

    async def click(self, selector: str, **kwargs: Any) -> None:
        self.clicked_selectors.append(selector)

    async def hover(self, selector: str, **kwargs: Any) -> None:
        self.hovered_selectors.append(selector)

    async def is_visible(self, selector: str, **kwargs: Any) -> bool:
        return False

    async def screenshot(self, path: Optional[str] = None, **kwargs: Any) -> bytes:
        dummy_png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05"
            b"\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        if path:
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(path, "wb") as f:
                f.write(dummy_png)
        return dummy_png

    async def set_input_files(self, selector: str, files: Any, **kwargs: Any) -> None:
        self.input_files[selector] = files

    async def wait_for_timeout(self, timeout: float) -> None:
        await asyncio.sleep(min(float(timeout) / 1000.0, 0.01))

    async def evaluate(self, expression: str, arg: Any = None) -> Any:
        return None

    async def content(self) -> str:
        return "<html><body></body></html>"

    async def title(self) -> str:
        return "TikTok"

    async def set_viewport_size(self, viewport_size: Dict[str, int]) -> None:
        self.viewport_size = viewport_size


class StubBrowserContext:
    """In-memory stub for Playwright BrowserContext."""

    def __init__(
        self,
        pages: Optional[List[StubPage]] = None,
        browser: Optional[StubBrowser] = None,
    ) -> None:
        self.browser: Optional[StubBrowser] = browser
        self.pages: List[StubPage] = pages if pages is not None else []
        if not self.pages:
            self.pages.append(StubPage(context=self))
        else:
            for p in self.pages:
                p.context = self

    async def new_page(self) -> StubPage:
        page = StubPage(context=self)
        self.pages.append(page)
        return page

    async def close(self) -> None:
        for p in list(self.pages):
            await p.close()


class StubBrowser:
    """In-memory stub for Playwright Browser."""

    def __init__(self, contexts: Optional[List[StubBrowserContext]] = None) -> None:
        self.contexts: List[StubBrowserContext] = contexts if contexts is not None else []
        if not self.contexts:
            self.contexts.append(StubBrowserContext(browser=self))
        else:
            for ctx in self.contexts:
                ctx.browser = self

    async def new_context(self, **kwargs: Any) -> StubBrowserContext:
        ctx = StubBrowserContext(browser=self)
        self.contexts.append(ctx)
        return ctx

    async def close(self) -> None:
        for ctx in list(self.contexts):
            await ctx.close()


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

        if mock_mode is not None:
            self.mock_mode = mock_mode
        elif os.getenv("ALIASMODE_MOCK") is not None:
            self.mock_mode = os.getenv("ALIASMODE_MOCK", "").lower() in ("1", "true", "yes")
        elif os.getenv("ENVIRONMENT") == "production":
            self.mock_mode = False
        else:
            self.mock_mode = True

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
                return str(profile_id)

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
                return str(cdp_url)

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

        if self.mock_mode and playwright_instance is None:
            stub_page = StubPage()
            stub_context = StubBrowserContext(pages=[stub_page])
            stub_browser = StubBrowser(contexts=[stub_context])
            return stub_browser, stub_context, stub_page

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
                    if inspect.isawaitable(res):
                        await res
            except Exception as e:
                logger.warning(f"Error closing browser: {e}")
            try:
                await self.stop_browser(profile_id)
            except Exception as e:
                logger.warning(f"Error stopping profile: {e}")
