"""Unit tests for BrowserAdapter service (Milestone 6, Task 6, Feature F19)."""

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
    assert adapter.mock_mode is True  # Defaults to True in test/dev environment


def test_browser_adapter_init_custom(monkeypatch):
    monkeypatch.setenv("BROWSER_API_URL", "http://custom-host:50325/")
    adapter = BrowserAdapter(timeout=15.0, mock_mode=False)
    assert adapter.api_url == "http://custom-host:50325"
    assert adapter.timeout == 15.0
    assert adapter.mock_mode is False


def test_browser_adapter_env_mock_mode(monkeypatch):
    monkeypatch.setenv("ALIASMODE_MOCK", "false")
    adapter = BrowserAdapter()
    assert adapter.mock_mode is False

    monkeypatch.setenv("ALIASMODE_MOCK", "true")
    adapter2 = BrowserAdapter()
    assert adapter2.mock_mode is True


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
    assert cfg.to_aliasmode_dict()["type"] == "http"
    assert cfg.to_aliasmode_dict()["port"] == 8080
    assert cfg.to_playwright_dict()["server"] == "http://1.2.3.4:8080"

    socks_cfg = parse_and_validate_proxy("socks5://10.0.0.1:1080")
    assert socks_cfg is not None
    assert socks_cfg.scheme == "socks5"
    assert socks_cfg.port == 1080
    assert socks_cfg.username is None

    assert parse_and_validate_proxy(None) is None
    assert parse_and_validate_proxy("") is None
    assert parse_and_validate_proxy("   ") is None


@pytest.mark.parametrize(
    "invalid_proxy",
    [
        "ftp://1.2.3.4:8080",
        "http://:8080",
        "http://1.2.3.4",
        "http://1.2.3.4:0",
        "http://1.2.3.4:70000",
        "http://1.2.3.4:invalid",
        "not_a_valid_url",
    ],
)
def test_proxy_validation_invalid(invalid_proxy):
    with pytest.raises(BrowserProxyError) as exc_info:
        parse_and_validate_proxy(invalid_proxy)
    # Must also be catchable as ValueError and BrowserAdapterError
    assert isinstance(exc_info.value, ValueError)
    assert isinstance(exc_info.value, BrowserAdapterError)


# ---------------------------------------------------------------------------
# 3. In-Memory Mock Mode Lifecycle Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mock_mode_full_lifecycle():
    adapter = BrowserAdapter(mock_mode=True)

    # 1. Create Profile
    pid = await adapter.create_profile("fashion_koc_01", proxy="http://user:pass@1.2.3.4:8080")
    assert pid.startswith("alias_prof_")
    assert pid in adapter.profiles
    assert adapter.profiles[pid]["name"] == "fashion_koc_01"
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

    # Must raise BrowserProfileNotFoundError, which is a KeyError subclass
    with pytest.raises(KeyError) as exc_info:
        await adapter.start_browser("alias_prof_non_existent")
    assert isinstance(exc_info.value, BrowserProfileNotFoundError)
    assert isinstance(exc_info.value, BrowserAdapterError)

    with pytest.raises(KeyError):
        await adapter.stop_browser("alias_prof_non_existent")

    with pytest.raises(KeyError):
        await adapter.delete_profile("alias_prof_non_existent")


@pytest.mark.asyncio
async def test_create_profile_empty_name_error():
    adapter = BrowserAdapter(mock_mode=True)
    with pytest.raises(ValueError):
        await adapter.create_profile("")


# ---------------------------------------------------------------------------
# 4. Live REST API Client Tests (Mocking HTTP responses)
# ---------------------------------------------------------------------------

def make_mock_session(status=200, json_data=None, text_data="", side_effect=None):
    mock_resp = AsyncMock()
    mock_resp.status = status
    if json_data is not None:
        mock_resp.json = AsyncMock(return_value=json_data)
    if text_data:
        mock_resp.text = AsyncMock(return_value=text_data)

    cm = MagicMock()
    if side_effect:
        cm.__aenter__ = AsyncMock(side_effect=side_effect)
    else:
        cm.__aenter__ = AsyncMock(return_value=mock_resp)
    cm.__aexit__ = AsyncMock(return_value=None)

    mock_session = MagicMock()
    mock_session.post.return_value = cm
    mock_session.closed = False
    mock_session.close = AsyncMock()
    return mock_session


@pytest.mark.asyncio
async def test_live_api_create_profile_success():
    mock_session = make_mock_session(status=200, json_data={"data": {"profile_id": "alias_prof_99"}})
    adapter = BrowserAdapter(mock_mode=False, session=mock_session)
    pid = await adapter.create_profile("live_koc_01")

    assert pid == "alias_prof_99"
    mock_session.post.assert_called_once()
    assert "/api/v1/profile/create" in mock_session.post.call_args[0][0]


@pytest.mark.asyncio
async def test_live_api_start_browser_success():
    mock_session = make_mock_session(
        status=200,
        json_data={"data": {"cdp_url": "ws://127.0.0.1:50325/devtools/browser/alias_prof_99"}},
    )
    adapter = BrowserAdapter(mock_mode=False, session=mock_session)
    cdp_url = await adapter.start_browser("alias_prof_99")

    assert cdp_url == "ws://127.0.0.1:50325/devtools/browser/alias_prof_99"
    mock_session.post.assert_called_once()
    assert "/api/v1/browser/start" in mock_session.post.call_args[0][0]


@pytest.mark.asyncio
async def test_live_api_profile_not_found_404():
    mock_session = make_mock_session(status=404, text_data="Profile not found")
    adapter = BrowserAdapter(mock_mode=False, session=mock_session)
    with pytest.raises(KeyError) as exc_info:
        await adapter.start_browser("alias_prof_unknown")
    assert isinstance(exc_info.value, BrowserProfileNotFoundError)


@pytest.mark.asyncio
async def test_live_api_server_error_500():
    mock_session = make_mock_session(status=500, text_data="Internal Server Error")
    adapter = BrowserAdapter(mock_mode=False, session=mock_session)
    with pytest.raises(BrowserAPIError) as exc_info:
        await adapter.start_browser("alias_prof_10")
    assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_live_api_connection_error():
    conn_err = aiohttp.ClientConnectorError(
        connection_key=MagicMock(), os_error=OSError(61, "Connection refused")
    )
    mock_session = make_mock_session(side_effect=conn_err)
    adapter = BrowserAdapter(mock_mode=False, session=mock_session)
    with pytest.raises(BrowserConnectionError):
        await adapter.create_profile("prof_err")


@pytest.mark.asyncio
async def test_live_api_timeout():
    mock_session = make_mock_session(side_effect=asyncio.TimeoutError())
    adapter = BrowserAdapter(mock_mode=False, session=mock_session)
    with pytest.raises(BrowserTimeoutError):
        await adapter.start_browser("alias_prof_timeout")


@pytest.mark.asyncio
async def test_live_api_stop_and_delete_success():
    mock_session = make_mock_session(status=200, json_data={"success": True})
    adapter = BrowserAdapter(mock_mode=False, session=mock_session)
    assert await adapter.stop_browser("alias_prof_1") is True
    assert await adapter.delete_profile("alias_prof_1") is True


# ---------------------------------------------------------------------------
# 5. CDP Attachment & Session Context Manager Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_connect_over_cdp_invalid_url():
    adapter = BrowserAdapter()
    with pytest.raises(PlaywrightConnectionError):
        await adapter.connect_over_cdp("http://not-ws-url")


@pytest.mark.asyncio
async def test_connect_over_cdp_mock_simulation():
    adapter = BrowserAdapter(mock_mode=True)
    browser, context, page = await adapter.connect_over_cdp("ws://127.0.0.1:50325/devtools/browser/alias_prof_01")
    assert browser is not None
    assert context is not None
    assert page is not None


@pytest.mark.asyncio
async def test_open_session_context_manager():
    adapter = BrowserAdapter(mock_mode=True)
    pid = await adapter.create_profile("session_test")

    async with adapter.open_session(pid) as (browser, context, page):
        assert adapter.profiles[pid]["status"] == "running"
        assert page is not None

    # After exit, profile must be stopped
    assert adapter.profiles[pid]["status"] == "stopped"


@pytest.mark.asyncio
async def test_open_session_context_manager_handles_error():
    adapter = BrowserAdapter(mock_mode=True)
    pid = await adapter.create_profile("session_err_test")

    with pytest.raises(RuntimeError, match="Context error"):
        async with adapter.open_session(pid) as (browser, context, page):
            raise RuntimeError("Context error")

    # Browser must still be stopped on exception
    assert adapter.profiles[pid]["status"] == "stopped"


@pytest.mark.asyncio
async def test_close_adapter_session():
    adapter = BrowserAdapter()
    # Creates and closes internal session cleanly
    await adapter.close()


# ---------------------------------------------------------------------------
# 6. In-Memory Automation Stubs Verification (StubMouse, StubKeyboard, StubPage)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_in_memory_stubs_behavior(tmp_path):
    from src.services.browser_adapter import (
        StubBrowser,
        StubBrowserContext,
        StubKeyboard,
        StubMouse,
        StubPage,
    )

    mouse = StubMouse()
    await mouse.move(100.0, 200.0)
    assert mouse.x == 100.0 and mouse.y == 200.0
    await mouse.click(50.0, 60.0)
    assert mouse.x == 50.0 and mouse.y == 60.0
    assert mouse.is_down is False
    await mouse.wheel(0.0, 300.0)
    assert mouse.scroll_history == [(0.0, 300.0)]

    keyboard = StubKeyboard()
    await keyboard.type("hello")
    assert keyboard.typed_chars == ["h", "e", "l", "l", "o"]
    await keyboard.press("Enter")
    assert keyboard.pressed_keys == ["Enter"]
    await keyboard.down("Shift")
    await keyboard.up("Shift")

    page = StubPage()
    await page.goto("https://www.tiktok.com")
    assert page.url == "https://www.tiktok.com"
    await page.click("button.test")
    assert "button.test" in page.clicked_selectors
    await page.hover("div.hover")
    assert "div.hover" in page.hovered_selectors
    assert await page.is_visible("selector") is False
    assert await page.content() == "<html><body></body></html>"
    assert await page.title() == "TikTok"

    test_png = tmp_path / "screenshot.png"
    png_bytes = await page.screenshot(path=str(test_png))
    assert png_bytes.startswith(b"\x89PNG")
    assert test_png.exists()
    assert test_png.stat().st_size > 0

    await page.set_input_files("input[type='file']", "/path/to/vid.mp4")
    assert page.input_files["input[type='file']"] == "/path/to/vid.mp4"
    await page.wait_for_timeout(50)
    assert await page.evaluate("1 + 1") is None
    await page.set_viewport_size({"width": 1920, "height": 1080})
    assert page.viewport_size == {"width": 1920, "height": 1080}
    await page.close()
    assert page.is_closed is True

    # Test context and browser lifecycle
    browser = StubBrowser()
    assert len(browser.contexts) == 1
    ctx = browser.contexts[0]
    assert len(ctx.pages) == 1
    new_p = await ctx.new_page()
    assert len(ctx.pages) == 2
    new_ctx = await browser.new_context()
    assert len(browser.contexts) == 2
    await browser.close()
    assert all(p.is_closed for c in browser.contexts for p in c.pages)


def test_no_mock_imports_in_browser_adapter_source():
    import src.services.browser_adapter as ba

    with open(ba.__file__, "r", encoding="utf-8") as f:
        content = f.read()

    assert "unittest.mock" not in content, "Found forbidden unittest.mock in browser_adapter.py"
    assert "MagicMock" not in content, "Found forbidden MagicMock in browser_adapter.py"
    assert "AsyncMock" not in content, "Found forbidden AsyncMock in browser_adapter.py"

