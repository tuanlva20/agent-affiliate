#!/usr/bin/env python3
"""Empirical Adversarial Stress Harness for Milestone 6 (BrowserAdapter & SmartPublisher).

AMAS v1.4.0 — Target Features:
- F19: AliasMode Browser Adapter (Anti-detect browser profile & CDP connector)
- F24: Emergency Captcha Guard (Immediate abort & Telegram alert)
- F25: Smart Publisher Agent (Channel lifecycle guard & automated video publishing)

Adversarial Stress Dimensions:
1. BrowserAdapter Proxy Torture:
   - Invalid schemes: ftp://, ssh://, socks4://, ws://, file://, etc. -> MUST raise BrowserProxyError (subclass of ValueError)
   - Invalid ports: port 0, port 65536, port 70000, port -1, non-numeric port -> MUST raise BrowserProxyError
   - Missing host: http://:8080, http://user:pass@, http://user:pass@:8080, socks5:// -> MUST raise BrowserProxyError
   - Valid edge schemes: user with special chars (p@ss!word), standard socks5, https, None/empty string tolerance
2. Missing Profile Boundary:
   - Mock mode: start_browser, stop_browser, delete_profile with non-existent profile ID -> MUST raise BrowserProfileNotFoundError (KeyError)
   - Live REST API mode: 404 response or {success: false, error: 'not found'} -> MUST raise BrowserProfileNotFoundError (KeyError)
3. SmartPublisher Lifecycle State Machine Torture:
   - Fuzz all lifecycle statuses: 'warming', 'captcha_blocked', 'cooldown', 'unknown_status', None, ''
   - Verify 'warming' is rejected 100% of the time with error containing 'warming stage'
   - Verify 'captcha_blocked' is rejected 100% of the time with error containing 'blocked by Captcha' or 'captcha blocked'
   - Verify 'cooldown' is rejected 100% of the time with error containing 'cooldown stage'
   - Dict vs ORM Channel model equivalence across all statuses
4. Concurrency & Race Conditions:
   - 20 concurrent publish_video requests on the same channel: verify status transitions remain consistent
   - Sequential/staggered guard: subsequent calls blocked once cooldown is reached
   - Mid-flight Captcha detection: verify channel transitions to 'captcha_blocked', db_session commits change, and error returned
   - Browser start failure: verify publisher catches error gracefully and leaves channel in valid state
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.agents.smart_publisher import PublishResult, SmartPublisher
from src.database.models import Base, Channel, Niche, Product, VideoJob
from src.services.browser_adapter import (
    BrowserAdapter,
    BrowserAdapterError,
    BrowserAPIError,
    BrowserConnectionError,
    BrowserProfileNotFoundError,
    BrowserProxyError,
    BrowserTimeoutError,
    ProxyConfig,
    parse_and_validate_proxy,
)

logging.basicConfig(level=logging.ERROR)


# ---------------------------------------------------------------------------
# Test Suite Reporter Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class TestResult:
    name: str
    passed: bool
    details: str = ""
    error: Optional[str] = None


@dataclass
class SuiteReport:
    name: str
    results: List[TestResult] = field(default_factory=list)

    def add(self, name: str, passed: bool, details: str = "", error: Optional[str] = None) -> None:
        self.results.append(TestResult(name=name, passed=passed, details=details, error=error))

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def pass_rate(self) -> float:
        return (self.passed / self.total * 100.0) if self.total > 0 else 0.0

    @property
    def failures(self) -> List[str]:
        return [f"[{r.name}] {r.details} - Error: {r.error}" for r in self.results if not r.passed]


# ---------------------------------------------------------------------------
# Suite 1: BrowserAdapter Proxy Torture
# ---------------------------------------------------------------------------

async def test_suite_1_proxy_torture() -> SuiteReport:
    suite = SuiteReport("Suite 1: BrowserAdapter Proxy Torture")

    # 1.1 Invalid Schemes
    invalid_schemes = [
        "ftp://proxy.corp.local:8080",
        "ssh://1.2.3.4:22",
        "socks4://1.2.3.4:1080",
        "ws://127.0.0.1:8080",
        "file:///etc/proxy",
        "gopher://10.0.0.1:70",
        "telnet://192.168.1.1:23",
        "unknown://proxy:8080",
    ]
    for p in invalid_schemes:
        try:
            parse_and_validate_proxy(p)
            suite.add(f"InvalidScheme_{p}", False, f"Expected BrowserProxyError for scheme in '{p}', but parsed successfully.")
        except BrowserProxyError as exc:
            is_val_err = isinstance(exc, ValueError)
            is_adapt_err = isinstance(exc, BrowserAdapterError)
            if is_val_err and is_adapt_err:
                suite.add(f"InvalidScheme_{p}", True, f"Correctly raised BrowserProxyError (isinstance ValueError & BrowserAdapterError): {exc}")
            else:
                suite.add(f"InvalidScheme_{p}", False, f"BrowserProxyError does not inherit from ValueError or BrowserAdapterError: is_val={is_val_err}, is_adapt={is_adapt_err}")
        except Exception as exc:
            suite.add(f"InvalidScheme_{p}", False, f"Unexpected exception type {type(exc).__name__}: {exc}")

    # 1.2 Invalid Ports
    invalid_ports = [
        ("http://1.2.3.4:0", "port 0"),
        ("http://1.2.3.4:65536", "port 65536 (out of 16-bit range)"),
        ("http://1.2.3.4:70000", "port 70000"),
        ("http://1.2.3.4:-1", "port -1 (negative)"),
        ("http://1.2.3.4:abc", "port non-numeric string"),
        ("http://1.2.3.4:80a80", "port alphanumeric"),
        ("socks5://10.0.0.1:999999", "port 999999"),
    ]
    for p, label in invalid_ports:
        try:
            parse_and_validate_proxy(p)
            suite.add(f"InvalidPort_{label}", False, f"Expected BrowserProxyError for {label} in '{p}', but parsed successfully.")
        except BrowserProxyError as exc:
            is_val_err = isinstance(exc, ValueError)
            suite.add(f"InvalidPort_{label}", is_val_err, f"Correctly caught BrowserProxyError: {exc}")
        except Exception as exc:
            suite.add(f"InvalidPort_{label}", False, f"Unexpected exception type {type(exc).__name__}: {exc}")

    # 1.3 Missing Host
    missing_hosts = [
        "http://:8080",
        "http://user:pass@",
        "http://user:pass@:8080",
        "socks5://",
        "http:///",
        "https://@:8080",
    ]
    for p in missing_hosts:
        try:
            parse_and_validate_proxy(p)
            suite.add(f"MissingHost_{p}", False, f"Expected BrowserProxyError for missing host in '{p}', but parsed successfully.")
        except BrowserProxyError as exc:
            is_val_err = isinstance(exc, ValueError)
            suite.add(f"MissingHost_{p}", is_val_err, f"Correctly caught BrowserProxyError for missing host: {exc}")
        except Exception as exc:
            suite.add(f"MissingHost_{p}", False, f"Unexpected exception type {type(exc).__name__}: {exc}")

    # 1.4 Valid Edge Schemes
    valid_proxies = [
        ("http://user:p@ss!word@1.2.3.4:8080", "http", "1.2.3.4", 8080, "user", "p@ss!word"),
        ("socks5://127.0.0.1:1080", "socks5", "127.0.0.1", 1080, None, None),
        ("https://proxy.example.com:443", "https", "proxy.example.com", 443, None, None),
        ("socks5h://admin:pass123@192.168.1.100:9050", "socks5h", "192.168.1.100", 9050, "admin", "pass123"),
    ]
    for raw_url, exp_scheme, exp_host, exp_port, exp_user, exp_pass in valid_proxies:
        try:
            cfg = parse_and_validate_proxy(raw_url)
            if cfg is None:
                suite.add(f"ValidEdge_{raw_url}", False, "Expected ProxyConfig object, got None")
                continue

            matches = (
                cfg.scheme == exp_scheme
                and cfg.host == exp_host
                and cfg.port == exp_port
                and cfg.username == exp_user
                and cfg.password == exp_pass
            )
            if matches:
                suite.add(f"ValidEdge_{raw_url}", True, f"Parsed {raw_url} correctly into {cfg}")
            else:
                suite.add(f"ValidEdge_{raw_url}", False, f"Mismatch in parsed ProxyConfig: {cfg}")
        except Exception as exc:
            suite.add(f"ValidEdge_{raw_url}", False, f"Valid proxy threw unexpected exception: {exc}")

    # 1.5 Null and Empty tolerance
    for empty_val in [None, "", "   ", "\t\n"]:
        try:
            res = parse_and_validate_proxy(empty_val)
            suite.add(f"EmptyProxyTolerance_{repr(empty_val)}", res is None, f"Empty proxy returned {res}")
        except Exception as exc:
            suite.add(f"EmptyProxyTolerance_{repr(empty_val)}", False, f"Unexpected exception for empty input: {exc}")

    return suite


# ---------------------------------------------------------------------------
# Suite 2: Missing Profile Boundary Tests
# ---------------------------------------------------------------------------

async def test_suite_2_missing_profile_boundary() -> SuiteReport:
    suite = SuiteReport("Suite 2: Missing Profile Boundary")

    # 2.1 Mock Mode Missing Profile Boundaries
    adapter_mock = BrowserAdapter(mock_mode=True)

    # start_browser non-existent profile
    try:
        await adapter_mock.start_browser("non_existent_profile")
        suite.add("Mock_StartMissingProfile", False, "Expected BrowserProfileNotFoundError, but call succeeded")
    except BrowserProfileNotFoundError as exc:
        is_key_err = isinstance(exc, KeyError)
        suite.add("Mock_StartMissingProfile", is_key_err, f"Correctly raised BrowserProfileNotFoundError (KeyError={is_key_err})")
    except Exception as exc:
        suite.add("Mock_StartMissingProfile", False, f"Unexpected exception type: {type(exc).__name__}: {exc}")

    # stop_browser non-existent profile
    try:
        await adapter_mock.stop_browser("non_existent_profile")
        suite.add("Mock_StopMissingProfile", False, "Expected KeyError, but call succeeded")
    except KeyError as exc:
        suite.add("Mock_StopMissingProfile", True, f"Correctly raised KeyError: {exc}")
    except Exception as exc:
        suite.add("Mock_StopMissingProfile", False, f"Unexpected exception type: {type(exc).__name__}: {exc}")

    # delete_profile non-existent profile
    try:
        await adapter_mock.delete_profile("non_existent_profile")
        suite.add("Mock_DeleteMissingProfile", False, "Expected KeyError, but call succeeded")
    except KeyError as exc:
        suite.add("Mock_DeleteMissingProfile", True, f"Correctly raised KeyError: {exc}")
    except Exception as exc:
        suite.add("Mock_DeleteMissingProfile", False, f"Unexpected exception type: {type(exc).__name__}: {exc}")

    # start_browser with empty profile string
    try:
        await adapter_mock.start_browser("")
        suite.add("Mock_StartEmptyProfile", False, "Expected KeyError, but call succeeded")
    except KeyError as exc:
        suite.add("Mock_StartEmptyProfile", True, f"Correctly rejected empty profile with KeyError: {exc}")
    except Exception as exc:
        suite.add("Mock_StartEmptyProfile", False, f"Unexpected exception type: {type(exc).__name__}: {exc}")

    # 2.2 Live REST API Mode (404 HTTP Response)
    mock_resp_404 = AsyncMock()
    mock_resp_404.status = 404
    mock_resp_404.text = AsyncMock(return_value="Profile not found in AliasMode database")
    cm_404 = MagicMock()
    cm_404.__aenter__ = AsyncMock(return_value=mock_resp_404)
    cm_404.__aexit__ = AsyncMock(return_value=None)
    mock_session_404 = MagicMock()
    mock_session_404.post.return_value = cm_404
    mock_session_404.closed = False

    adapter_live_404 = BrowserAdapter(mock_mode=False, session=mock_session_404)

    try:
        await adapter_live_404.start_browser("live_missing_prof_01")
        suite.add("Live404_StartMissingProfile", False, "Expected BrowserProfileNotFoundError on 404, but call succeeded")
    except BrowserProfileNotFoundError as exc:
        is_key_err = isinstance(exc, KeyError)
        suite.add("Live404_StartMissingProfile", is_key_err, f"Correctly raised BrowserProfileNotFoundError (KeyError={is_key_err}) on 404")
    except Exception as exc:
        suite.add("Live404_StartMissingProfile", False, f"Unexpected exception: {type(exc).__name__}: {exc}")

    try:
        await adapter_live_404.stop_browser("live_missing_prof_01")
        suite.add("Live404_StopMissingProfile", False, "Expected KeyError on 404, but call succeeded")
    except KeyError as exc:
        suite.add("Live404_StopMissingProfile", True, f"Correctly raised KeyError on 404: {exc}")
    except Exception as exc:
        suite.add("Live404_StopMissingProfile", False, f"Unexpected exception: {type(exc).__name__}: {exc}")

    # 2.3 Live REST API Mode (200 OK with success=False payload)
    mock_resp_err = AsyncMock()
    mock_resp_err.status = 200
    mock_resp_err.json = AsyncMock(return_value={"success": False, "error": "Profile alias_prof_404 not found"})
    cm_err = MagicMock()
    cm_err.__aenter__ = AsyncMock(return_value=mock_resp_err)
    cm_err.__aexit__ = AsyncMock(return_value=None)
    mock_session_err = MagicMock()
    mock_session_err.post.return_value = cm_err
    mock_session_err.closed = False

    adapter_live_err = BrowserAdapter(mock_mode=False, session=mock_session_err)

    try:
        await adapter_live_err.start_browser("alias_prof_404")
        suite.add("LivePayloadErr_StartMissingProfile", False, "Expected BrowserProfileNotFoundError, but call succeeded")
    except BrowserProfileNotFoundError as exc:
        is_key_err = isinstance(exc, KeyError)
        suite.add("LivePayloadErr_StartMissingProfile", is_key_err, f"Correctly parsed payload error and raised BrowserProfileNotFoundError (KeyError={is_key_err})")
    except Exception as exc:
        suite.add("LivePayloadErr_StartMissingProfile", False, f"Unexpected exception: {type(exc).__name__}: {exc}")

    return suite


# ---------------------------------------------------------------------------
# Suite 3: SmartPublisher Lifecycle State Machine Torture
# ---------------------------------------------------------------------------

async def test_suite_3_lifecycle_state_machine_torture() -> SuiteReport:
    suite = SuiteReport("Suite 3: SmartPublisher Lifecycle State Machine Torture")

    mock_browser = MagicMock()
    mock_browser.start_browser = AsyncMock()
    mock_human = MagicMock()
    mock_human.warmup_feed_session = AsyncMock()

    publisher = SmartPublisher(browser_adapter=mock_browser, human_behavior=mock_human)

    # 3.1 100% Rejection of 'warming' stage
    for iteration in range(5):
        ch_dict = {"channel_id": f"ch_warm_{iteration}", "lifecycle_status": "warming"}
        res = await publisher.publish_video(f"job_w_{iteration}", ch_dict, "/tmp/vid.mp4", "Caption", {})
        is_rejected = (res.success is False and res.channel_status == "warming" and "warming stage" in (res.error or ""))
        suite.add(
            f"WarmingRejected_Iteration_{iteration}",
            is_rejected,
            f"Warming rejection verified (success={res.success}, error={res.error})",
        )
    mock_browser.start_browser.assert_not_called()

    # 3.2 100% Rejection of 'captcha_blocked' stage
    for iteration in range(5):
        ch_dict = {"channel_id": f"ch_cap_{iteration}", "lifecycle_status": "captcha_blocked"}
        res = await publisher.publish_video(f"job_c_{iteration}", ch_dict, "/tmp/vid.mp4", "Caption", {})
        err_lower = (res.error or "").lower()
        has_captcha_mention = "blocked by captcha" in err_lower or "captcha blocked" in err_lower
        is_rejected = (res.success is False and res.channel_status == "captcha_blocked" and has_captcha_mention)
        suite.add(
            f"CaptchaBlockedRejected_Iteration_{iteration}",
            is_rejected,
            f"Captcha blocked rejection verified (success={res.success}, error={res.error})",
        )
    mock_browser.start_browser.assert_not_called()

    # 3.3 100% Rejection of 'cooldown' stage
    for iteration in range(5):
        ch_dict = {"channel_id": f"ch_cool_{iteration}", "lifecycle_status": "cooldown"}
        res = await publisher.publish_video(f"job_cool_{iteration}", ch_dict, "/tmp/vid.mp4", "Caption", {})
        is_rejected = (res.success is False and res.channel_status == "cooldown" and "cooldown stage" in (res.error or ""))
        suite.add(
            f"CooldownRejected_Iteration_{iteration}",
            is_rejected,
            f"Cooldown rejection verified (success={res.success}, error={res.error})",
        )
    mock_browser.start_browser.assert_not_called()

    # 3.4 Fuzzing non-standard statuses: unknown_status, None, empty string ""
    fuzz_statuses = ["unknown_status", None, "", "pending_verification", "banned_permanent", 12345]
    for status_val in fuzz_statuses:
        ch_dict = {"channel_id": "ch_fuzz", "lifecycle_status": status_val}
        res = await publisher.publish_video("job_fuzz", ch_dict, "/tmp/vid.mp4", "Caption", {})
        is_rejected = (
            res.success is False
            and res.channel_status == status_val
            and "invalid channel lifecycle status" in (res.error or "")
        )
        suite.add(
            f"FuzzStatus_Dict_{repr(status_val)}",
            is_rejected,
            f"Rejected fuzz status {repr(status_val)} with error: {res.error}",
        )

    # 3.5 Dict vs ORM Channel Model Equivalence
    # Test valid statuses as well as raw/bypassed statuses to ensure absolute parity
    statuses_to_compare = ["warming", "captcha_blocked", "cooldown", "unknown_status", None, ""]
    for st in statuses_to_compare:
        ch_dict = {"channel_id": f"ch_equiv_{st}", "lifecycle_status": st}

        if st in Channel.VALID_LIFECYCLE_STATUSES:
            ch_orm = Channel(
                channel_id=f"ch_equiv_{st}",
                niche_id="thoi_trang_nu",
                browser_profile_id=f"prof_equiv_{st}",
                lifecycle_status=st,
            )
        else:
            ch_orm = Channel(
                channel_id=f"ch_equiv_{st}",
                niche_id="thoi_trang_nu",
                browser_profile_id=f"prof_equiv_{st}",
                lifecycle_status="warming",
            )
            # Inject bypassed raw value
            ch_orm.__dict__["lifecycle_status"] = st

        res_dict = await publisher.publish_video(f"job_eq_{st}", ch_dict, "/tmp/vid.mp4", "Caption", {})
        res_orm = await publisher.publish_video(f"job_eq_{st}", ch_orm, "/tmp/vid.mp4", "Caption", {})

        equiv = (
            res_dict.success == res_orm.success
            and res_dict.channel_status == res_orm.channel_status
            and res_dict.error == res_orm.error
            and res_dict.video_id == res_orm.video_id
            and res_dict.published_url == res_orm.published_url
        )
        suite.add(
            f"Equivalence_Status_{repr(st)}",
            equiv,
            f"Dict vs ORM identical outcomes: success={res_dict.success}, status={res_dict.channel_status}, error={res_dict.error}",
        )

    # 3.6 None Channel Parameter Handling
    res_no_channel = await publisher.publish_video("job_null_ch", None, "/tmp/vid.mp4", "Caption", {})
    suite.add(
        "NullChannelHandling",
        res_no_channel.success is False and "channel parameter is required" in (res_no_channel.error or ""),
        f"Correctly handled None channel: {res_no_channel.error}",
    )

    return suite


# ---------------------------------------------------------------------------
# Suite 4: Concurrency & Race Conditions Tests
# ---------------------------------------------------------------------------

async def test_suite_4_concurrency_and_race_conditions() -> SuiteReport:
    suite = SuiteReport("Suite 4: Concurrency & Race Conditions")

    # 4.1 20 Concurrent publish_video requests on the same channel
    mock_browser = MagicMock()
    mock_browser.start_browser = AsyncMock(return_value="ws://127.0.0.1:50325/devtools/browser/prof_concurrent")

    mock_human = MagicMock()
    # Introduce small async yield to stress potential race conditions
    async def delayed_warmup(*args: Any, **kwargs: Any) -> bool:
        await asyncio.sleep(0.005)
        return True

    async def delayed_type(*args: Any, **kwargs: Any) -> None:
        await asyncio.sleep(0.005)

    mock_human.warmup_feed_session = delayed_warmup
    mock_human.detect_and_handle_captcha = AsyncMock(return_value=False)
    mock_human.human_type = delayed_type

    mock_page = MagicMock()
    async def delayed_goto(*args: Any, **kwargs: Any) -> None:
        await asyncio.sleep(0.005)

    mock_page.goto = delayed_goto
    mock_page.click = AsyncMock()
    mock_page.set_input_files = AsyncMock()

    publisher = SmartPublisher(browser_adapter=mock_browser, human_behavior=mock_human)
    channel = Channel(
        channel_id="ch_concurrent_20",
        niche_id="thoi_trang_nu",
        browser_profile_id="prof_conc_20",
        lifecycle_status="ready_to_post",
    )

    tasks = [
        publisher.publish_video(
            f"job_concurrent_{i}",
            channel,
            "/tmp/vid.mp4",
            f"Caption {i}",
            {},
            page=mock_page,
            warmup_duration=1,
        )
        for i in range(20)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Verify no unhandled exceptions crashed any of the 20 workers
    no_exceptions = all(not isinstance(r, Exception) for r in results)
    suite.add("Concurrent20_NoExceptions", no_exceptions, f"20 concurrent requests completed without throwing unhandled exceptions.")

    # Verify final channel lifecycle status transitioned cleanly to cooldown
    suite.add(
        "Concurrent20_FinalStatusCooldown",
        channel.lifecycle_status == "cooldown",
        f"Channel status successfully reached 'cooldown' (actual={channel.lifecycle_status})",
    )

    # Verify last_posted_at timestamp was populated with a valid datetime
    has_valid_timestamp = isinstance(channel.last_posted_at, datetime)
    suite.add(
        "Concurrent20_LastPostedAtSet",
        has_valid_timestamp,
        f"Channel last_posted_at set to {channel.last_posted_at}",
    )

    # 4.2 Sequential Guard: subsequent publish attempts MUST be rejected with 'cooldown'
    subsequent_res = await publisher.publish_video(
        "job_post_cooldown",
        channel,
        "/tmp/vid.mp4",
        "Subsequent caption",
        {},
        page=mock_page,
    )
    suite.add(
        "SubsequentPublishBlockedByCooldown",
        subsequent_res.success is False
        and subsequent_res.channel_status == "cooldown"
        and "cooldown stage" in (subsequent_res.error or ""),
        f"Subsequent attempt correctly blocked: {subsequent_res.error}",
    )

    # 4.3 Mid-flight Captcha Detection with Database Commit
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as db_session:
        niche = Niche(niche_id="niche_mid_cap", name="Niche Mid Captcha")
        db_session.add(niche)
        db_channel = Channel(
            channel_id="ch_mid_captcha",
            niche_id="niche_mid_cap",
            browser_profile_id="prof_mid_cap",
            lifecycle_status="ready_to_post",
        )
        db_session.add(db_channel)
        await db_session.commit()

        # Configure human behavior to simulate mid-flight Captcha trip
        mock_human_captcha = MagicMock()
        mock_human_captcha.warmup_feed_session = AsyncMock(return_value=True)
        mock_human_captcha.detect_and_handle_captcha = AsyncMock(return_value=True)

        publisher_captcha = SmartPublisher(browser_adapter=mock_browser, human_behavior=mock_human_captcha)

        cap_res = await publisher_captcha.publish_video(
            "job_mid_cap",
            db_channel,
            "/tmp/vid.mp4",
            "Test Captcha Caption",
            {},
            db_session=db_session,
        )

        suite.add(
            "MidFlightCaptcha_ResultFailure",
            cap_res.success is False and cap_res.channel_status == "captcha_blocked" and "Captcha" in (cap_res.error or ""),
            f"PublishResult returned error: {cap_res.error}",
        )

        suite.add(
            "MidFlightCaptcha_InMemoryStateUpdated",
            db_channel.lifecycle_status == "captcha_blocked",
            f"In-memory Channel lifecycle_status is {db_channel.lifecycle_status}",
        )

        # Query directly from DB to verify transaction commit
        stmt = select(Channel).where(Channel.channel_id == "ch_mid_captcha")
        fresh_ch = (await db_session.execute(stmt)).scalar_one()
        suite.add(
            "MidFlightCaptcha_DBTransactionCommitted",
            fresh_ch.lifecycle_status == "captcha_blocked",
            f"Committed DB Channel lifecycle_status is {fresh_ch.lifecycle_status}",
        )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

    # 4.4 Simulate Browser Start Failure Graceful Handling
    failing_browser = MagicMock()
    failing_browser.start_browser = AsyncMock(
        side_effect=BrowserConnectionError("Cannot connect to AliasMode Local API at http://127.0.0.1:50325")
    )
    publisher_failing_browser = SmartPublisher(browser_adapter=failing_browser, human_behavior=mock_human)

    channel_ready = Channel(
        channel_id="ch_browser_fail",
        niche_id="thoi_trang_nu",
        browser_profile_id="prof_browser_fail",
        lifecycle_status="ready_to_post",
    )

    fail_res = await publisher_failing_browser.publish_video(
        "job_browser_fail",
        channel_ready,
        "/tmp/vid.mp4",
        "Test Caption",
        {},
    )

    suite.add(
        "BrowserStartFailure_ResultHandled",
        fail_res.success is False
        and "Browser start failure" in (fail_res.error or "")
        and fail_res.channel_status == "ready_to_post",
        f"Handled start failure gracefully: {fail_res.error}",
    )

    suite.add(
        "BrowserStartFailure_ChannelStatePreserved",
        channel_ready.lifecycle_status == "ready_to_post",
        f"Channel status preserved as ready_to_post (actual={channel_ready.lifecycle_status})",
    )

    return suite


# ---------------------------------------------------------------------------
# Runner & Aggregator
# ---------------------------------------------------------------------------

async def run_all_adversarial_tests() -> Tuple[int, int, List[SuiteReport]]:
    print("=" * 80)
    print("M6 ADVERSARIAL STRESS TEST HARNESS — BrowserAdapter & SmartPublisher")
    print("AMAS v1.4.0 — Features F19, F24, F25")
    print("=" * 80)

    start_time = time.perf_counter()
    suites: List[SuiteReport] = []

    # 1. Proxy Torture
    s1 = await test_suite_1_proxy_torture()
    suites.append(s1)

    # 2. Missing Profile Boundary
    s2 = await test_suite_2_missing_profile_boundary()
    suites.append(s2)

    # 3. Lifecycle State Machine Torture
    s3 = await test_suite_3_lifecycle_state_machine_torture()
    suites.append(s3)

    # 4. Concurrency & Race Conditions
    s4 = await test_suite_4_concurrency_and_race_conditions()
    suites.append(s4)

    elapsed = time.perf_counter() - start_time
    total_passed = sum(s.passed for s in suites)
    total_failed = sum(s.failed for s in suites)
    grand_total = total_passed + total_failed

    for s in suites:
        status_str = "PASS" if s.failed == 0 else f"FAIL ({s.failed} issues)"
        print(f"\n▶ {s.name}: {status_str}")
        print(f"  Assertions: {s.total} | Passed: {s.passed} | Failed: {s.failed} | Pass Rate: {s.pass_rate:.1f}%")
        if s.failures:
            print("  Failures Encountered:")
            for f in s.failures[:5]:
                print(f"    ❌ {f}")
            if len(s.failures) > 5:
                print(f"    ... and {len(s.failures) - 5} more issues.")

    print("\n" + "=" * 80)
    overall_rate = (total_passed / grand_total * 100.0) if grand_total > 0 else 0.0
    print(
        f"SUMMARY: {total_passed}/{grand_total} assertions passed ({overall_rate:.1f}%). "
        f"Total Failures: {total_failed} in {elapsed*1000:.1f}ms"
    )
    print("=" * 80)

    return total_passed, total_failed, suites


if __name__ == "__main__":
    passed, failed, suite_list = asyncio.run(run_all_adversarial_tests())
    sys.exit(0 if failed == 0 else 1)
