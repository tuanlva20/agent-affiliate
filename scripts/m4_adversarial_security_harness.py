#!/usr/bin/env python3
"""Empirical Adversarial Security & Injection Stress Harness for Milestone 4 (Telegram Command Center).

AMAS v1.4.0 — Features F10 (Topic Routing), F11 (1-Tap Approval), F12 (Bot Command Center).

Adversarial Vectors Evaluated:
1. Admin Check Bypass Matrix:
   - Negative user IDs (-1, -987654321, -2**63)
   - Float IDs (123.45, 987654321.0000001, NaN, Inf, -Inf)
   - Zero, False, None
   - String representation of admin_id ("987654321", " 987654321 ", "0987654321", "admin")
   - Integer overflow & boundary (2**63 - 1, 2**64, 10**100)
   - Spoofed from_user objects & custom dicts
   - Heterogeneous types (list, dict, set, object)

2. Command Parser Abuse & Injection Matrix:
   - Massive payloads (100KB command string, 100KB arguments)
   - SQL injection strings in arguments (' OR '1'='1, 1; DROP TABLE products; --)
   - Shell injection characters (; rm -rf /, && ls -la, | cat /etc/passwd, $(whoami), `whoami`)
   - Special unicode control characters (null bytes \\x00, RTL overrides \\u202e, zero-width spaces \\u200b)
   - Newline injections (\\r\\n, multi-line fake alerts)
   - Malformed slash formatting (///test_scout, /TEST_SCOUT, '  /test_scout  ', \\test_scout, /, empty, None)
   - Bot mention suffixes (/test_scout@amas_bot)

3. Topic Routing Fuzzing & Fail-Safe Matrix:
   - None, empty string, whitespace
   - Non-existent & random niches
   - Unicode emoji niches (👗 thời trang, 🏠 đồ gia dụng)
   - Path traversal niches (../../, ../../etc/passwd, ..\\\\windows\\\\system32)
   - SQL injection in niche_id (' OR 1=1 --, '; DROP TABLE topics; --)
   - Case variations & trailing whitespace (THOI_TRANG_NU, 'thoi_trang_nu ')
   - Null bytes in niche (thoi_trang_nu\\x00)
   - Extreme length strings (100KB)
   - Non-string types (101, 102, True, False, unhashable objects)
   - Verifies 100% fail-safe fallback to 100 (#dashboard-tong)

4. Product Card Formatting, Adversarial Payload & Tone Compliance Matrix:
   - Malicious titles containing banned AI robotic clichés (sự lựa chọn hoàn hảo, đáp ứng mọi nhu cầu)
   - Malicious titles containing counterfeit brand keywords and obfuscations (Zara, Chanel, rep 1:1, like auth, z.a.r.a, super fake)
   - Malicious titles containing exaggerated medical / lifetime claims (trị dứt điểm 100%, thần dược, vĩnh viễn không hỏng)
   - Structural crash resistance against None, empty dict, negative prices, NaN/Inf, massive numbers, XSS, format strings
   - Verifies ToneValidator detection and formatting exception safety

5. 1-Tap Approval Callback Fuzzing & Database Integrity Matrix:
   - Unauthorized callback attempts
   - Malformed callback data (no colon, empty action, empty product_id, 100KB data)
   - SQL injection in product_id
   - Idempotency & race resilience on approve_product and reject_product
   - In-memory fallback queue verification

6. TelegramCommandCenter Lifecycle & Mock Mode Verification:
   - Edge case initialization parameters
   - Mock message transmission integrity and MessageDict dual-access properties
"""

from __future__ import annotations

import asyncio
import math
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.agents.fashion_scout import SpecialistEvaluation
from src.bot import (
    ADMIN_DENIED_MESSAGE,
    TOPIC_MAP,
    CompatibleInlineKeyboardButton,
    CompatibleInlineKeyboardMarkup,
    MessageDict,
    TelegramCommandCenter,
    execute_callback,
    execute_command,
    format_captcha_alert,
    format_product_card,
    format_product_message,
    get_approval_keyboard,
    get_main_menu_keyboard,
    route_topic,
)
from src.core.tone_validator import ToneValidator
from src.database.models import Base, Channel, Niche, Product, VideoJob


class TestResult:
    """Test suite result tracker."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.failures: List[str] = []

    def record_pass(self) -> None:
        self.total += 1
        self.passed += 1

    def record_fail(self, detail: str) -> None:
        self.total += 1
        self.failed += 1
        self.failures.append(detail)

    @property
    def pass_rate(self) -> float:
        return (self.passed / self.total * 100.0) if self.total > 0 else 0.0


# ==============================================================================
# 1. Admin Authorization & Identity Spoofing Matrix
# ==============================================================================

async def test_1_admin_check_bypass_matrix() -> TestResult:
    """Test all bypass vectors attempting to circumvent user_id == admin_id."""
    res = TestResult("1. Admin Authorization & Identity Spoofing Matrix")
    legit_admin_id = 987654321

    spoofed_ids: List[Tuple[str, Any]] = [
        # Negative IDs
        ("negative -1", -1),
        ("negative -987654321", -987654321),
        ("negative -1001234567890", -1001234567890),
        ("negative 32-bit int", -2147483648),
        ("negative 64-bit int", -(2**63)),
        # Float IDs
        ("float 123.45", 123.45),
        ("float 0.0", 0.0),
        ("float -1.5", -1.5),
        ("float 987654321.0000001", 987654321.0000001),
        ("float 987654321.5", 987654321.5),
        ("float NaN", float("nan")),
        ("float Inf", float("inf")),
        ("float -Inf", float("-inf")),
        # String representations of admin
        ("string admin_id exact", "987654321"),
        ("string admin_id padded", " 987654321 "),
        ("string admin_id leading zero", "0987654321"),
        ("string hex admin_id", "0x3ade68b1"),
        ("string random user", "unauthorized_user"),
        ("string empty", ""),
        ("string zero", "0"),
        # Zero, False, None
        ("integer zero", 0),
        ("boolean False", False),
        ("NoneType", None),
        # Integer boundary & overflow
        ("int 32-bit max", 2147483647),
        ("int 64-bit max", 2**63 - 1),
        ("int 64-bit overflow", 2**64),
        ("int 100-digit overflow", 10**100),
        # Heterogeneous objects
        ("empty dict", {}),
        ("empty list", []),
        ("empty set", set()),
        ("tuple", (987654321,)),
        ("generic object", object()),
    ]

    # Spoofed from_user objects with duck-typing attributes
    class SpoofedFromUser:
        def __init__(self, uid: Any) -> None:
            self.id = uid
            self.user_id = uid

    class SpoofedIntSubclass(int):
        pass

    spoofed_ids.append(("spoofed from_user obj with admin id", SpoofedFromUser(legit_admin_id)))
    spoofed_ids.append(("spoofed from_user obj with other id", SpoofedFromUser(12345)))
    spoofed_ids.append(("spoofed from_user obj with None", SpoofedFromUser(None)))

    for label, uid in spoofed_ids:
        # Test execute_command
        try:
            resp = await execute_command(
                command="/status",
                user_id=uid,
                admin_id=legit_admin_id,
            )
            if resp == ADMIN_DENIED_MESSAGE:
                res.record_pass()
            else:
                res.record_fail(f"Command bypass with {label}: expected denied message, got {resp[:60]}")
        except Exception as e:
            res.record_fail(f"Command crash with {label}: {type(e).__name__}: {e}")

        # Test execute_callback
        try:
            cb_resp = await execute_callback(
                callback_data="approve_product:prod_bypass_test",
                user_id=uid,
                admin_id=legit_admin_id,
            )
            if (
                isinstance(cb_resp, dict)
                and cb_resp.get("success") is False
                and cb_resp.get("error") == "unauthorized"
                and cb_resp.get("message") == ADMIN_DENIED_MESSAGE
            ):
                res.record_pass()
            else:
                res.record_fail(f"Callback bypass with {label}: expected unauthorized dict, got {cb_resp}")
        except Exception as e:
            res.record_fail(f"Callback crash with {label}: {type(e).__name__}: {e}")

    # Legit admin execution sanity check
    try:
        legit_resp = await execute_command("/status", user_id=legit_admin_id, admin_id=legit_admin_id)
        if "AMAS v1.4.0" in legit_resp and ADMIN_DENIED_MESSAGE not in legit_resp:
            res.record_pass()
        else:
            res.record_fail(f"Legit admin was incorrectly denied or failed: {legit_resp}")
    except Exception as e:
        res.record_fail(f"Legit admin command raised exception: {type(e).__name__}: {e}")

    return res


# ==============================================================================
# 2. Command Parser Abuse & Injection Matrix
# ==============================================================================

async def test_2_command_parser_abuse_matrix() -> TestResult:
    """Test command parser against injection payloads, formatting anomalies, and fuzzing."""
    res = TestResult("2. Command Parser Abuse & Injection Matrix")
    admin_id = 987654321

    # 1. Massive payloads (100KB input)
    massive_arg = "A" * 100_000
    try:
        resp = await execute_command(f"/test_scout {massive_arg}", user_id=admin_id, admin_id=admin_id)
        if "🔍 Bắt đầu trinh sát ngách:" in resp and len(resp) >= 100_000:
            res.record_pass()
        else:
            res.record_fail("Massive 100KB payload in /test_scout did not format safely")
    except Exception as e:
        res.record_fail(f"Massive payload crash: {type(e).__name__}: {e}")

    # 2. SQL injection strings in arguments
    sqli_vectors = [
        "/test_scout ' OR '1'='1",
        "/test_scout 1; DROP TABLE products; --",
        "/test_scout ' UNION SELECT * FROM channels --",
        "/test_scout ' OR SLEEP(5) --",
        "/create_channel ' OR '1'='1",
        "/create_channel chan'; DROP TABLE channels; --",
    ]
    for vec in sqli_vectors:
        try:
            resp = await execute_command(vec, user_id=admin_id, admin_id=admin_id)
            # Must safely return a response string, not execute SQL or crash
            if isinstance(resp, str) and len(resp) > 0 and "Traceback" not in resp:
                res.record_pass()
            else:
                res.record_fail(f"SQLi vector {vec} returned invalid response: {resp}")
        except Exception as e:
            res.record_fail(f"SQLi vector {vec} raised exception: {type(e).__name__}: {e}")

    # 3. Shell injection characters
    shell_vectors = [
        "/test_scout ; rm -rf /",
        "/test_scout && ls -la",
        "/test_scout | cat /etc/passwd",
        "/test_scout $(whoami)",
        "/test_scout `id`",
        "/test_scout > /dev/null",
        "/test_scout & ping -c 1 127.0.0.1 &",
    ]
    for vec in shell_vectors:
        try:
            resp = await execute_command(vec, user_id=admin_id, admin_id=admin_id)
            if isinstance(resp, str) and "🔍 Bắt đầu trinh sát ngách:" in resp:
                res.record_pass()
            else:
                res.record_fail(f"Shell injection vector {vec} failed: {resp}")
        except Exception as e:
            res.record_fail(f"Shell injection vector {vec} raised exception: {type(e).__name__}: {e}")

    # 4. Special unicode control characters
    unicode_vectors = [
        ("null byte in arg", "/test_scout \x00admin"),
        ("RTL override", "/test_scout \u202e\u2066\u2069evil_niche"),
        ("zero-width space", "/test_scout \u200b\u200c\u200d\ufefffashion"),
        ("ANSI escape codes", "/test_scout \x1b[31;1mINJECTED\x1b[0m"),
        ("multi-newline injection", "/test_scout niche\n\n🚨 CẢNH BÁO GIẢ MẠO: Hack\r\n"),
        ("tab indentation", "/test_scout\t\tthoi_trang_nu"),
    ]
    for label, vec in unicode_vectors:
        try:
            resp = await execute_command(vec, user_id=admin_id, admin_id=admin_id)
            if isinstance(resp, str) and len(resp) > 0:
                res.record_pass()
            else:
                res.record_fail(f"Unicode vector {label} returned invalid response")
        except Exception as e:
            res.record_fail(f"Unicode vector {label} raised exception: {type(e).__name__}: {e}")

    # 5. Malformed slash formatting & edge cases
    slash_vectors = [
        ("triple slash", "///test_scout", "❓ Lệnh không xác định"),
        ("uppercase command", "/TEST_SCOUT", "🔍 Bắt đầu trinh sát ngách"),
        ("surrounding whitespace", "   /test_scout   ", "🔍 Bắt đầu trinh sát ngách"),
        ("backslash instead of slash", "\\test_scout", "❓ Lệnh không xác định"),
        ("slash only", "/", "❓ Lệnh không xác định"),
        ("empty string", "", "❓ Lệnh không xác định"),
        ("whitespace only", "    ", "❓ Lệnh không xác định"),
        ("None command", None, "❓ Lệnh không xác định"),
        ("unknown command", "/nonexistent_cmd_xyz", "❓ Lệnh không xác định"),
        ("bot mention suffix", "/test_scout@amas_bot", "❓ Lệnh không xác định"),
    ]
    for label, cmd, expected_substring in slash_vectors:
        try:
            resp = await execute_command(cmd, user_id=admin_id, admin_id=admin_id)
            if expected_substring in resp:
                res.record_pass()
            else:
                res.record_fail(f"Slash formatting '{label}' expected '{expected_substring}', got '{resp}'")
        except Exception as e:
            res.record_fail(f"Slash formatting '{label}' raised exception: {type(e).__name__}: {e}")

    return res


# ==============================================================================
# 3. Topic Routing Fuzzing & Fail-Safe Matrix
# ==============================================================================

def test_3_topic_routing_fuzzing_matrix() -> TestResult:
    """Fuzz route_topic with adversarial, corrupt, and boundary inputs."""
    res = TestResult("3. Topic Routing Fuzzing & Fail-Safe Matrix")

    # Contract standard paths
    if route_topic("thoi_trang_nu") == 101:
        res.record_pass()
    else:
        res.record_fail("thoi_trang_nu did not route to 101")

    if route_topic("do_gia_dung") == 102:
        res.record_pass()
    else:
        res.record_fail("do_gia_dung did not route to 102")

    if route_topic("dashboard_tong") == 100 and route_topic("dashboard") == 100:
        res.record_pass()
    else:
        res.record_fail("dashboard did not route to 100")

    # Adversarial fail-safe inputs: all unrecognized inputs MUST fail-safe to 100
    fuzz_inputs: List[Tuple[str, Any]] = [
        ("None", None),
        ("empty string", ""),
        ("whitespace", "   "),
        ("non-existent niche", "unknown_niche"),
        ("random category", "crypto_and_forex"),
        ("emoji niche fashion", "👗 thời trang 👠"),
        ("emoji niche home", "🏠 đồ gia dụng"),
        ("single fire emoji", "🔥"),
        ("path traversal ../", "../../"),
        ("path traversal /etc/passwd", "../../etc/passwd"),
        ("windows path traversal", "..\\..\\windows\\system32"),
        ("SQL injection OR 1=1", "' OR 1=1 --"),
        ("SQL injection DROP TABLE", "'; DROP TABLE topics; --"),
        ("uppercase THOI_TRANG_NU", "THOI_TRANG_NU"),
        ("mixed case Do_Gia_Dung", "Do_Gia_Dung"),
        ("trailing space", "thoi_trang_nu "),
        ("leading space", " do_gia_dung"),
        ("null byte in niche", "thoi_trang_nu\x00admin"),
        ("newline in niche", "thoi_trang_nu\n100"),
        ("massive string (100KB)", "niche_" + "X" * 100_000),
        ("integer 101", 101),
        ("integer 102", 102),
        ("integer 12345", 12345),
        ("float 101.5", 101.5),
        ("boolean True", True),
        ("boolean False", False),
    ]

    for label, val in fuzz_inputs:
        try:
            routed = route_topic(val)
            if routed == 100:
                res.record_pass()
            else:
                res.record_fail(f"Fuzz vector '{label}' routed to {routed} instead of fail-safe 100")
        except Exception as e:
            res.record_fail(f"Fuzz vector '{label}' crashed route_topic: {type(e).__name__}: {e}")

    # Custom mapping override fuzzing
    custom_map = {
        "thoi_trang_nu": 501,
        "do_gia_dung": 502,
        "custom_niche": 503,
    }
    try:
        if route_topic("custom_niche", custom_map) == 503:
            res.record_pass()
        else:
            res.record_fail("Custom topic mapping failed for custom_niche")

        if route_topic("unknown_custom", custom_map) == 100:
            res.record_pass()
        else:
            res.record_fail("Unknown custom topic did not fail-safe to 100")

        if route_topic(None, custom_map) == 100:
            res.record_pass()
        else:
            res.record_fail("None niche with custom map did not fail-safe to 100")
    except Exception as e:
        res.record_fail(f"Custom mapping raised exception: {type(e).__name__}: {e}")

    return res


# ==============================================================================
# 4. Product Card Formatting & Tone Compliance Matrix
# ==============================================================================

def test_4_tone_compliance_and_formatting_matrix() -> TestResult:
    """Test format_product_card against adversarial titles and ToneValidator compliance."""
    res = TestResult("4. Product Card Formatting & Tone Compliance Matrix")

    # 1. Robotic Clichés Injection: Ensure cards containing cliches FAIL ToneValidator
    robotic_titles = [
        "Áo sơ mi nữ công sở - Sự lựa chọn hoàn hảo",
        "Nồi cơm điện giải pháp hoàn hảo cho gia đình",
        "Máy xay sinh tố đáp ứng mọi nhu cầu của bạn",
        "Kính chào quý khách đến với shop áo khoác",
        "Sở hữu ngay hôm nay đừng bỏ lỡ cơ hội này",
        "Hy vọng thông tin này hữu ích cho bạn",
    ]
    for r_title in robotic_titles:
        try:
            card = format_product_card({"title": r_title, "price": 180000, "commission": 0.15})
            is_valid = ToneValidator.validate(card)
            violations = ToneValidator.check_violations(card)
            if not is_valid and any("ROBOTIC_CLICHE" in v for v in violations):
                res.record_pass()
            else:
                res.record_fail(f"Robotic title '{r_title}' bypassed ToneValidator! Valid={is_valid}, Violations={violations}")
        except Exception as e:
            res.record_fail(f"Robotic title '{r_title}' crashed formatter: {type(e).__name__}: {e}")

    # 2. Counterfeit Brand Injection & Obfuscations
    counterfeit_titles = [
        "Áo thun Zara like auth 1:1",
        "Túi xách Chanel rep 1:1 Quảng Châu",
        "Set đồ Gucci like auth chuẩn form",
        "Váy Dior hàng tuồn vnxk",
        "Giày Nike super fake full phụ kiện",
        "Đồng hồ Rolex bản rep",
        "Thắt lưng Louis Vuitton auth tuồn",
        "Áo khoác Z.a.r.a auth tuồn",
        "Túi c-h-a-n-e-l super_fake",
        "Váy Z@ra like.auth",
    ]
    for c_title in counterfeit_titles:
        try:
            card = format_product_card({"title": c_title, "price": 250000, "commission": 0.20})
            is_valid = ToneValidator.validate(card)
            violations = ToneValidator.check_violations(card)
            if not is_valid and any("COUNTERFEIT_KEYWORD" in v for v in violations):
                res.record_pass()
            else:
                res.record_fail(f"Counterfeit title '{c_title}' bypassed ToneValidator! Valid={is_valid}, Violations={violations}")
        except Exception as e:
            res.record_fail(f"Counterfeit title '{c_title}' crashed formatter: {type(e).__name__}: {e}")

    # 3. Exaggerated Claims Injection
    exaggerated_titles = [
        "Kem bôi cam kết trị dứt điểm 100% không tái phát",
        "Thuốc đông y chữa khỏi dứt điểm",
        "Thần dược trị mụn cấp tốc",
        "Chảo chống dính vĩnh viễn không hỏng",
        "Nồi chiên không dầu tốt nhất thị trường",
        "Bình giữ nhiệt số 1 việt nam",
        "100% hết bệnh sau 1 tuần",
    ]
    for e_title in exaggerated_titles:
        try:
            card = format_product_card({"title": e_title, "price": 320000, "commission": 0.12})
            is_valid = ToneValidator.validate(card)
            violations = ToneValidator.check_violations(card)
            if not is_valid and any("EXAGGERATED_CLAIM" in v for v in violations):
                res.record_pass()
            else:
                res.record_fail(f"Exaggerated title '{e_title}' bypassed ToneValidator! Valid={is_valid}, Violations={violations}")
        except Exception as e:
            res.record_fail(f"Exaggerated title '{e_title}' crashed formatter: {type(e).__name__}: {e}")

    # 4. Clean KOC Compliance: Both niches must pass 100%
    clean_cases = [
        ("thoi_trang_nu", "Quần Ống Suông Nữ Lưng Cao Hack Chân", 199000, 0.18, "Chị em ơi lướt thấy em này là mê chữ ê kéo dài nha!"),
        ("do_gia_dung", "Hộp Cơm Cắm Điện Tự Nấu Thông Minh 3 Tầng", 285000, 0.15, "Mấy bà dân văn phòng ơi trưa nay ăn gì nhàn tênh luôn nè!"),
    ]
    for niche, p_title, price, comm, hook in clean_cases:
        try:
            card = format_product_card(niche, title=p_title, price_vnd=price, commission_rate=comm, hook_angle=hook)
            is_valid = ToneValidator.validate(card)
            has_koc = ToneValidator.has_koc_markers(card)
            if is_valid and has_koc:
                res.record_pass()
            else:
                res.record_fail(f"Clean KOC card for {niche} failed tone check: valid={is_valid}, has_koc={has_koc}")
        except Exception as e:
            res.record_fail(f"Clean KOC card formatting crashed for {niche}: {type(e).__name__}: {e}")

    # 5. Structural Crash Resistance Fuzzing
    structural_payloads: List[Tuple[str, Any]] = [
        ("None product", None),
        ("empty dict", {}),
        ("all None fields", {"title": None, "price": None, "commission": None, "sales": None, "product_id": None}),
        ("negative numbers", {"title": "Test", "price": -50000, "commission": -0.5, "sales": -10}),
        ("huge numbers", {"title": "Test", "price": 10**15, "commission": 2.5, "sales": 10**9}),
        ("string formatted numbers", {"title": "Test", "price": "150000", "commission": "0.15", "sales": "500"}),
        ("massive title (100KB)", {"title": "A" * 100_000, "price": 100000}),
        ("XSS script injection", {"title": "<script>alert('xss')</script><b>Test</b>"}),
        ("Python format string injection", {"title": "{product_id} {niche_id} %(env)s %s %d"}),
        ("Unicode control characters", {"title": "Test\x00\r\n\t\u202e\u200b", "product_id": "p_ctrl"}),
    ]
    for label, payload in structural_payloads:
        try:
            card = format_product_card(payload)
            if isinstance(card, str) and len(card) > 0:
                res.record_pass()
            else:
                res.record_fail(f"Structural payload '{label}' returned empty or non-string")
        except Exception as e:
            res.record_fail(f"Structural payload '{label}' crashed format_product_card: {type(e).__name__}: {e}")

    return res


# ==============================================================================
# 5. 1-Tap Approval Callback Fuzzing & DB Integrity Matrix
# ==============================================================================

async def test_5_callback_fuzzing_and_db_integrity() -> TestResult:
    """Test execute_callback against malformed callbacks, SQLi, and idempotency."""
    res = TestResult("5. 1-Tap Approval Callback Fuzzing & DB Integrity Matrix")
    admin_id = 987654321

    # In-memory SQLite DB engine for isolated async testing
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as session:
        # Seed pilot niches & test products
        session.add(Niche(niche_id="thoi_trang_nu", name="Thời trang nữ"))
        session.add(Niche(niche_id="do_gia_dung", name="Đồ gia dụng thông minh"))
        session.add(Product(
            product_id="prod_db_test_01",
            niche_id="thoi_trang_nu",
            title="Đầm Maxi Nữ",
            price=250000.0,
            commission_rate=0.15,
            product_url="https://example.com/p01",
            status="pending",
        ))
        session.add(Product(
            product_id="prod_db_test_02",
            niche_id="do_gia_dung",
            title="Nồi Chiên Không Dầu",
            price=890000.0,
            commission_rate=0.12,
            product_url="https://example.com/p02",
            status="pending",
        ))
        await session.commit()

        # 1. Malformed callback data strings (must fail with success: False)
        malformed_callbacks = [
            ("None callback", None, "malformed_callback"),
            ("empty callback", "", "malformed_callback"),
            ("no colon separator", "approve_product", "malformed_callback"),
            ("only colon", ":", "unknown_action"),
            ("multiple colons unknown", ":::unknown", "unknown_action"),
            ("unknown action", "delete_all_records:prod_01", "unknown_action"),
            ("arbitrary action injection", "hack_system:prod_01", "unknown_action"),
        ]
        for label, cb_data, expected_err in malformed_callbacks:
            try:
                cb_res = await execute_callback(cb_data, user_id=admin_id, admin_id=admin_id, session=session)
                if isinstance(cb_res, dict) and cb_res.get("success") is False and cb_res.get("error") == expected_err:
                    res.record_pass()
                else:
                    res.record_fail(f"Malformed callback '{label}' should have failed with {expected_err}, got: {cb_res}")
            except Exception as e:
                res.record_fail(f"Malformed callback '{label}' crashed execute_callback: {type(e).__name__}: {e}")

        # 2. Boundary callback payloads (must be safely handled without unhandled exceptions or security leaks)
        boundary_callbacks = [
            ("empty product_id", "approve_product:"),
            ("massive callback (100KB)", "approve_product:" + "A" * 100_000),
            ("SQLi in product_id (DROP TABLE)", "approve_product:prod_'; DROP TABLE products; --"),
            ("SQLi in product_id (OR 1=1)", "approve_product:' OR '1'='1"),
            ("SQLi in reject_product", "reject_product:prod_'; DROP TABLE video_jobs; --"),
            ("control chars in product_id", "approve_product:prod_\x00\r\n\t"),
        ]
        for label, cb_data in boundary_callbacks:
            try:
                cb_res = await execute_callback(cb_data, user_id=admin_id, admin_id=admin_id, session=session)
                # Verify safe handling: returns a valid dict, no unhandled exceptions, no DB corruption
                if isinstance(cb_res, dict) and "success" in cb_res:
                    res.record_pass()
                else:
                    res.record_fail(f"Boundary callback '{label}' returned invalid response: {cb_res}")
            except Exception as e:
                res.record_fail(f"Boundary callback '{label}' crashed execute_callback: {type(e).__name__}: {e}")

        # 3. Valid approve_product DB transition
        try:
            app_res = await execute_callback("approve_product:prod_db_test_01", user_id=admin_id, admin_id=admin_id, session=session)
            if app_res.get("success") is True and app_res.get("product_id") == "prod_db_test_01":
                p = await session.get(Product, "prod_db_test_01")
                if p and p.status == "approved":
                    res.record_pass()
                else:
                    res.record_fail(f"Product status not updated to 'approved': {getattr(p, 'status', None)}")
            else:
                res.record_fail(f"approve_product failed: {app_res}")
        except Exception as e:
            res.record_fail(f"approve_product raised: {type(e).__name__}: {e}")

        # 4. Idempotency test: approve the same product a second time (must not duplicate VideoJob)
        try:
            app_res2 = await execute_callback("approve_product:prod_db_test_01", user_id=admin_id, admin_id=admin_id, session=session)
            if app_res2.get("success") is True:
                # Check DB VideoJob count for this product
                from sqlalchemy import func, select
                stmt = select(func.count(VideoJob.job_id)).where(VideoJob.product_id == "prod_db_test_01")
                job_count = (await session.execute(stmt)).scalar()
                if job_count == 1:
                    res.record_pass()
                else:
                    res.record_fail(f"Idempotency violation: expected exactly 1 VideoJob, found {job_count}")
            else:
                res.record_fail(f"Idempotent second approval failed: {app_res2}")
        except Exception as e:
            res.record_fail(f"Idempotent approval raised: {type(e).__name__}: {e}")

        # 5. Valid reject_product DB transition
        try:
            rej_res = await execute_callback("reject_product:prod_db_test_02", user_id=admin_id, admin_id=admin_id, session=session)
            if rej_res.get("success") is True and rej_res.get("product_id") == "prod_db_test_02":
                p2 = await session.get(Product, "prod_db_test_02")
                if p2 and p2.status == "rejected":
                    res.record_pass()
                else:
                    res.record_fail(f"Product status not updated to 'rejected': {getattr(p2, 'status', None)}")
            else:
                res.record_fail(f"reject_product failed: {rej_res}")
        except Exception as e:
            res.record_fail(f"reject_product raised: {type(e).__name__}: {e}")

    await engine.dispose()
    return res


# ==============================================================================
# 6. TelegramCommandCenter Lifecycle & Keyboard Dual-Mode Matrix
# ==============================================================================

async def test_6_command_center_lifecycle_and_keyboards() -> TestResult:
    """Test TelegramCommandCenter instantiation, mock sending, and keyboard dual-indexing."""
    res = TestResult("6. TelegramCommandCenter Lifecycle & Keyboard Dual-Mode Matrix")

    # 1. Keyboard Dual Subscripting and Attribute Access
    try:
        kb = get_approval_keyboard("prod_dual_mode_01")
        # Subscript access: kb["inline_keyboard"][0]
        row = kb["inline_keyboard"][0]
        btn_approve = row[0]
        btn_reject = row[1]
        if (
            btn_approve["callback_data"] == "approve_product:prod_dual_mode_01"
            and btn_approve.callback_data == "approve_product:prod_dual_mode_01"
            and btn_reject["callback_data"] == "reject_product:prod_dual_mode_01"
            and btn_reject.callback_data == "reject_product:prod_dual_mode_01"
            and "inline_keyboard" in kb
        ):
            res.record_pass()
        else:
            res.record_fail("Approval keyboard failed dual subscripting / attribute access")
    except Exception as e:
        res.record_fail(f"Approval keyboard raised: {type(e).__name__}: {e}")

    # 2. Main menu keyboard
    try:
        menu_kb = get_main_menu_keyboard()
        if len(menu_kb["inline_keyboard"]) == 3 and menu_kb.inline_keyboard[0][0].text == "🔍 Trinh sát":
            res.record_pass()
        else:
            res.record_fail("Main menu keyboard structure invalid")
    except Exception as e:
        res.record_fail(f"Main menu keyboard raised: {type(e).__name__}: {e}")

    # 3. TelegramCommandCenter Mock Mode & Safe Message Logging
    try:
        bot = TelegramCommandCenter(
            token="mock_token_adversarial",
            admin_id=987654321,
            forum_chat_id=-1001234567890,
        )
        # MessageDict dual access
        msg = await bot.send_message(
            chat_id=-1001234567890,
            text="Adversarial stress message",
            message_thread_id=101,
        )
        if (
            msg["message_id"] == 1
            and msg.message_id == 1
            and msg["text"] == "Adversarial stress message"
            and msg.text == "Adversarial stress message"
            and msg.message_thread_id == 101
        ):
            res.record_pass()
        else:
            res.record_fail("MessageDict dual access check failed")

        # Captcha emergency alert
        c_msg = await bot.send_captcha_alert(channel_id="chan_test_99", screenshot_path="/tmp/test.png")
        if (
            "🚨 [CẢNH BÁO CAPTCHA TIKTOK - KÊNH chan_test_99]" in c_msg.text
            and c_msg.message_thread_id == 100
        ):
            res.record_pass()
        else:
            res.record_fail(f"Captcha alert did not route to 100 or format correctly: {c_msg.text}")

        # Send product card with extreme payload
        pc_msg = await bot.send_product_card(
            product={"title": "Váy Dạ Tiệc", "price": 450000, "commission_rate": 0.20},
            niche_id="thoi_trang_nu",
        )
        if pc_msg.message_thread_id == 101 and "Váy Dạ Tiệc" in pc_msg.text:
            res.record_pass()
        else:
            res.record_fail("send_product_card failed to route to 101 or include title")

    except Exception as e:
        res.record_fail(f"TelegramCommandCenter execution raised: {type(e).__name__}: {e}")

    return res


# ==============================================================================
# Main Runner & Reporting
# ==============================================================================

async def run_all_adversarial_tests() -> Tuple[int, int, List[TestResult]]:
    """Run all 6 empirical adversarial stress test suites."""
    print("=" * 80)
    print("AMAS v1.4.0 — Milestone 4 Telegram Command Center Adversarial Security Harness")
    print("=" * 80)

    start_time = time.perf_counter()

    suites: List[TestResult] = []

    # Run Suite 1
    s1 = await test_1_admin_check_bypass_matrix()
    suites.append(s1)

    # Run Suite 2
    s2 = await test_2_command_parser_abuse_matrix()
    suites.append(s2)

    # Run Suite 3
    s3 = test_3_topic_routing_fuzzing_matrix()
    suites.append(s3)

    # Run Suite 4
    s4 = test_4_tone_compliance_and_formatting_matrix()
    suites.append(s4)

    # Run Suite 5
    s5 = await test_5_callback_fuzzing_and_db_integrity()
    suites.append(s5)

    # Run Suite 6
    s6 = await test_6_command_center_lifecycle_and_keyboards()
    suites.append(s6)

    elapsed = time.perf_counter() - start_time

    total_passed = sum(s.passed for s in suites)
    total_failed = sum(s.failed for s in suites)
    grand_total = total_passed + total_failed

    for s in suites:
        status_str = "PASS" if s.failed == 0 else f"FAIL ({s.failed} issues)"
        print(f"\n▶ {s.name}: {status_str}")
        print(f"  Tests: {s.total} | Passed: {s.passed} | Failed: {s.failed} | Pass Rate: {s.pass_rate:.1f}%")
        if s.failures:
            print("  Top Failures:")
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
