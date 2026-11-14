"""Unit tests for AMAS-15: Quick Cookie Import and Channel Auto-Verification."""

from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.main import app
from src.database.models import Base, Channel, Niche
from src.database.session import get_async_engine, get_session_factory
from src.services.browser_adapter import (
    BrowserAdapter,
    BrowserAdapterError,
    parse_cookies_input,
)

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = get_async_engine(TEST_DB_URL, force_new=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with get_session_factory(TEST_DB_URL)() as session:
        session.add(Niche(niche_id="niche_cookie_01", name="Fashion"))
        session.add(
            Channel(
                channel_id="chan_cookie_01",
                niche_id="niche_cookie_01",
                platform="facebook",
                browser_profile_id="alias_prof_cookie_01",
                lifecycle_status="warming",
                platform_metadata={},
            )
        )
        session.add(
            Channel(
                channel_id="chan_cookie_02",
                niche_id="niche_cookie_01",
                platform="tiktok",
                browser_profile_id="alias_prof_cookie_02",
                lifecycle_status="captcha_blocked",
                platform_metadata={},
            )
        )
        await session.commit()
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ---------------------------------------------------------------------------
# Cookie Parsing Unit Tests
# ---------------------------------------------------------------------------

def test_parse_json_array_cookies():
    raw = '[{"name": "c_user", "value": "100012345", "domain": ".facebook.com"}, {"name": "xs", "value": "sec_token"}]'
    cookies = parse_cookies_input(raw, default_domain=".facebook.com")
    assert len(cookies) == 2
    assert cookies[0]["name"] == "c_user"
    assert cookies[0]["value"] == "100012345"
    assert cookies[1]["name"] == "xs"
    assert cookies[1]["domain"] == ".facebook.com"


def test_parse_netscape_cookies():
    raw = (
        "# Netscape HTTP Cookie File\n"
        "# http://curl.haxx.se/rfc/cookie_spec.html\n"
        ".facebook.com\tTRUE\t/\tTRUE\t1735689600\tc_user\t1000888999\n"
        ".facebook.com\tTRUE\t/\tTRUE\t1735689600\txs\t28%3Aabc%3A2\n"
    )
    cookies = parse_cookies_input(raw, default_domain=".facebook.com")
    assert len(cookies) == 2
    assert cookies[0]["name"] == "c_user"
    assert cookies[0]["value"] == "1000888999"
    assert cookies[1]["name"] == "xs"


def test_parse_raw_header_cookies():
    raw = "c_user=1000999888; xs=30%3Afbtoken%3A1; datr=secret_datr_123;"
    cookies = parse_cookies_input(raw, default_domain=".facebook.com")
    assert len(cookies) == 3
    names = [c["name"] for c in cookies]
    assert "c_user" in names
    assert "xs" in names
    assert "datr" in names


def test_parse_invalid_or_empty_cookies_raises_error():
    with pytest.raises(BrowserAdapterError):
        parse_cookies_input("")

    with pytest.raises(BrowserAdapterError):
        parse_cookies_input("    ")

    with pytest.raises(BrowserAdapterError):
        parse_cookies_input("invalid_no_equal_sign_string")


# ---------------------------------------------------------------------------
# BrowserAdapter Service Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_browser_adapter_import_cookies_mock_mode():
    adapter = BrowserAdapter(mock_mode=True)
    raw = "sessionid=tiktok_session_abc123; sid_guard=guard_xyz"
    res = await adapter.import_cookies_to_profile(
        profile_id="alias_prof_test_99",
        raw_cookie=raw,
        platform="tiktok",
    )
    assert res["success"] is True
    assert res["cookie_count"] == 2
    assert res["authenticated"] is True
    assert adapter.profiles["alias_prof_test_99"]["cookies"][0]["name"] == "sessionid"


# ---------------------------------------------------------------------------
# API Endpoint Integration Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_import_cookies_success(db_session):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "cookies": "c_user=1000555666; xs=28%3Avalid%3A1;",
            "format": "auto",
        }
        resp = await ac.post("/api/channels/chan_cookie_01/import-cookies", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["channel_id"] == "chan_cookie_01"
        assert data["lifecycle_status"] == "ready_to_post"
        assert data["cookie_count"] == 2
        assert data["authenticated"] is True

        # Verify second channel captcha_blocked -> ready_to_post
        payload_tiktok = {
            "cookies": '[{"name": "sessionid", "value": "tk_sess_999"}]',
        }
        resp_tt = await ac.post("/api/channels/chan_cookie_02/import-cookies", json=payload_tiktok)
        assert resp_tt.status_code == 200
        assert resp_tt.json()["lifecycle_status"] == "ready_to_post"


@pytest.mark.asyncio
async def test_api_import_cookies_not_found(db_session):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/api/channels/non_existent_channel/import-cookies", json={"cookies": "a=b"})
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_import_cookies_invalid_format(db_session):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/api/channels/chan_cookie_01/import-cookies", json={"cookies": "bad_cookie_no_equals"})
        assert resp.status_code == 400
