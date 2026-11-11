"""Empirical Adversarial Stress Harness for KalodataClient (Milestone 2 Task 2).

Tests:
1. Token boundary evasions (None, empty, whitespace, expired, invalid types, corrupted files)
2. Malformed API payloads, missing product fields, corrupted JSON, unexpected types
3. Polling timeout resilience, rapid concurrent queries, error classification
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import aiohttp
from src.services.kalodata_client import (
    KalodataAPIError,
    KalodataAuthError,
    KalodataClient,
    KalodataError,
    KalodataNetworkError,
    KalodataTimeoutError,
)


@dataclass
class AdversarialCaseResult:
    category: str
    name: str
    passed: bool
    exception_type: Optional[str]
    details: str


class KalodataAdversarialTester:
    def __init__(self) -> None:
        self.results: List[AdversarialCaseResult] = []

    def record(self, category: str, name: str, passed: bool, exc_type: Optional[str], details: str) -> None:
        self.results.append(AdversarialCaseResult(category, name, passed, exc_type, details))

    # -------------------------------------------------------------------------
    # 1. Token Boundary Evasions
    # -------------------------------------------------------------------------
    async def test_token_boundaries(self) -> None:
        cat = "Token Boundary Evasions"

        # 1.1 None token with clean env and missing file
        try:
            with patch.dict(os.environ, {}, clear=True), \
                 patch.object(KalodataClient, "TOKEN_FILE_PATH", Path("/tmp/nonexistent_kalo_token")):
                client = KalodataClient(token=None)
                try:
                    await client.get_top_products("test")
                    self.record(cat, "Token=None missing env & file", False, None, "Expected KalodataAuthError, got success")
                except KalodataAuthError as e:
                    valid_msg = "~/.kalopilot/token" in str(e)
                    self.record(cat, "Token=None missing env & file", valid_msg, type(e).__name__, str(e))
                except Exception as e:
                    self.record(cat, "Token=None missing env & file", False, type(e).__name__, f"Unexpected error: {e}")
        except Exception as e:
            self.record(cat, "Token=None setup", False, type(e).__name__, str(e))

        # 1.2 Empty string token
        try:
            client = KalodataClient(token="")
            try:
                await client.get_top_products("test")
                self.record(cat, "Token='' (empty string)", False, None, "Expected KalodataAuthError, got success")
            except KalodataAuthError as e:
                self.record(cat, "Token='' (empty string)", "~/.kalopilot/token" in str(e), type(e).__name__, str(e))
            except Exception as e:
                self.record(cat, "Token='' (empty string)", False, type(e).__name__, f"Unexpected error: {e}")
        except Exception as e:
            self.record(cat, "Token='' init", False, type(e).__name__, str(e))

        # 1.3 Whitespace-only tokens
        for ws in ["   ", "\t\t", "\n\r\n", " \t \n "]:
            try:
                client = KalodataClient(token=ws)
                try:
                    await client.get_top_products("test")
                    self.record(cat, f"Token=whitespace ({repr(ws)})", False, None, "Expected KalodataAuthError, got success")
                except KalodataAuthError as e:
                    self.record(cat, f"Token=whitespace ({repr(ws)})", "~/.kalopilot/token" in str(e), type(e).__name__, str(e))
                except Exception as e:
                    self.record(cat, f"Token=whitespace ({repr(ws)})", False, type(e).__name__, f"Unexpected error: {e}")
            except Exception as e:
                self.record(cat, f"Token=whitespace init ({repr(ws)})", False, type(e).__name__, str(e))

        # 1.4 expired_token marker and variants
        for exp in ["expired_token", "  expired_token  ", "expired_token\n"]:
            try:
                client = KalodataClient(token=exp)
                try:
                    await client.get_top_products("test")
                    self.record(cat, f"Token=expired ({repr(exp)})", False, None, "Expected KalodataAuthError, got success")
                except KalodataAuthError as e:
                    self.record(cat, f"Token=expired ({repr(exp)})", "~/.kalopilot/token" in str(e), type(e).__name__, str(e))
                except Exception as e:
                    self.record(cat, f"Token=expired ({repr(exp)})", False, type(e).__name__, f"Unexpected error: {e}")
            except Exception as e:
                self.record(cat, f"Token=expired init ({repr(exp)})", False, type(e).__name__, str(e))

        # 1.5 Non-string token types
        for val in [12345, False, ["some_token"], {"key": "val"}]:
            try:
                client = KalodataClient(token=val)  # type: ignore
                # Should either resolve safely to string or raise KalodataAuthError when used
                try:
                    # Mock submit_query to see if _ensure_authenticated passes or crashes
                    mock_resp = AsyncMock()
                    mock_resp.status = 200
                    mock_resp.json = AsyncMock(return_value={"success": True, "data": {"task_id": "t1"}})
                    mock_resp.__aenter__.return_value = mock_resp
                    mock_session = MagicMock()
                    mock_session.post.return_value = mock_resp
                    mock_session.closed = False
                    client._custom_session = mock_session

                    tid = await client.submit_query("query")
                    self.record(cat, f"Token non-string type ({type(val).__name__})", True, None, f"Coerced to {client.token}")
                except KalodataError as e:
                    self.record(cat, f"Token non-string type ({type(val).__name__})", True, type(e).__name__, str(e))
                except Exception as e:
                    self.record(cat, f"Token non-string type ({type(val).__name__})", False, type(e).__name__, f"Unhandled crash: {e}")
            except Exception as e:
                self.record(cat, f"Token non-string type init ({type(val).__name__})", False, type(e).__name__, f"Crash on init: {e}")

        # 1.6 Corrupted ~/.kalopilot/token file (Non-UTF8 binary content)
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(b"\x80\xff\xfe\x00\xab\xcd")
            binary_file_path = Path(tf.name)

        try:
            with patch.dict(os.environ, {}, clear=True), \
                 patch.object(KalodataClient, "TOKEN_FILE_PATH", binary_file_path):
                # Check whether init handles non-UTF8 without unhandled UnicodeDecodeError
                try:
                    client = KalodataClient(token=None)
                    self.record(cat, "Token file corrupted binary (non-UTF8)", True, None, f"Handled gracefully, token={client.token}")
                except UnicodeDecodeError as e:
                    self.record(cat, "Token file corrupted binary (non-UTF8)", False, type(e).__name__, f"Unhandled UnicodeDecodeError: {e}")
                except Exception as e:
                    self.record(cat, "Token file corrupted binary (non-UTF8)", False, type(e).__name__, f"Crash: {e}")
        finally:
            if binary_file_path.exists():
                binary_file_path.unlink()

        # 1.7 Token file unreadable / permission denied
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(b"valid_file_token")
            unreadable_path = Path(tf.name)
        try:
            os.chmod(unreadable_path, 0000)
            with patch.dict(os.environ, {}, clear=True), \
                 patch.object(KalodataClient, "TOKEN_FILE_PATH", unreadable_path):
                try:
                    client = KalodataClient(token=None)
                    self.record(cat, "Token file unreadable (0000 chmod)", True, None, f"Handled gracefully, token={client.token}")
                except Exception as e:
                    self.record(cat, "Token file unreadable (0000 chmod)", False, type(e).__name__, f"Crash: {e}")
        finally:
            os.chmod(unreadable_path, 0o600)
            if unreadable_path.exists():
                unreadable_path.unlink()

        # 1.8 Server Auth Rejections (401 and code=401)
        for status_code, payload in [
            (401, {"message": "Unauthorized"}),
            (200, {"success": False, "code": 401, "message": "Signature expired"}),
            (200, {"success": False, "code": 1004, "message": "The user token is expired"}),
            (200, {"success": False, "code": 1005, "message": "TOKEN invalid format"}),
        ]:
            client = KalodataClient(token="test_tok")
            mock_resp = AsyncMock()
            mock_resp.status = status_code
            mock_resp.json = AsyncMock(return_value=payload)
            mock_resp.__aenter__.return_value = mock_resp
            mock_session = MagicMock()
            mock_session.post.return_value = mock_resp
            mock_session.closed = False
            client._custom_session = mock_session

            try:
                await client.submit_query("query")
                self.record(cat, f"Auth rejection ({status_code}, {payload.get('code')})", False, None, "Expected KalodataAuthError")
            except KalodataAuthError as e:
                self.record(cat, f"Auth rejection ({status_code}, {payload.get('code')})", "~/.kalopilot/token" in str(e), type(e).__name__, str(e))
            except Exception as e:
                self.record(cat, f"Auth rejection ({status_code}, {payload.get('code')})", False, type(e).__name__, f"Unexpected error: {e}")

    # -------------------------------------------------------------------------
    # 2. Malformed API Payloads & Corrupted JSON
    # -------------------------------------------------------------------------
    async def test_malformed_payloads(self) -> None:
        cat = "Malformed Payloads & Corrupted JSON"

        # 2.1 Submit response is invalid/corrupted JSON (e.g. HTML 502)
        client = KalodataClient(token="valid_token")
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(side_effect=aiohttp.ContentTypeError(MagicMock(), MagicMock()))
        mock_resp.text = AsyncMock(return_value="<html>502 Bad Gateway</html>")
        mock_resp.__aenter__.return_value = mock_resp
        mock_session = MagicMock()
        mock_session.post.return_value = mock_resp
        mock_session.closed = False
        client._custom_session = mock_session

        try:
            await client.submit_query("query")
            self.record(cat, "Submit HTML 502 non-JSON", False, None, "Expected KalodataAPIError")
        except KalodataAPIError as e:
            self.record(cat, "Submit HTML 502 non-JSON", True, type(e).__name__, str(e))
        except Exception as e:
            self.record(cat, "Submit HTML 502 non-JSON", False, type(e).__name__, f"Unhandled error: {e}")

        # 2.2 Poll response is invalid/corrupted JSON (e.g. HTML 502 or JSONDecodeError)
        client = KalodataClient(token="valid_token", max_polls=2, poll_interval=0.001)
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(side_effect=json.JSONDecodeError("Expecting value", "foo", 0))
        mock_resp.text = AsyncMock(return_value="<html>502 Bad Gateway</html>")
        mock_resp.__aenter__.return_value = mock_resp
        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp
        mock_session.closed = False
        client._custom_session = mock_session

        try:
            await client.poll_task("task_123")
            self.record(cat, "Poll corrupted JSON / 502 HTML", False, None, "Expected KalodataError")
        except KalodataError as e:
            self.record(cat, "Poll corrupted JSON / 502 HTML", True, type(e).__name__, str(e))
        except Exception as e:
            self.record(cat, "Poll corrupted JSON / 502 HTML", False, type(e).__name__, f"Unhandled error: {e}")

        # 2.3 Submit response top-level is list or string or None
        for bad_top in [
            ["an", "array"],
            "string response",
            12345,
            None,
        ]:
            client = KalodataClient(token="valid_token")
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=bad_top)
            mock_resp.text = AsyncMock(return_value=str(bad_top))
            mock_resp.__aenter__.return_value = mock_resp
            mock_session = MagicMock()
            mock_session.post.return_value = mock_resp
            mock_session.closed = False
            client._custom_session = mock_session

            try:
                await client.submit_query("query")
                self.record(cat, f"Submit bad top-level ({type(bad_top).__name__})", False, None, "Expected KalodataAPIError")
            except KalodataAPIError as e:
                self.record(cat, f"Submit bad top-level ({type(bad_top).__name__})", True, type(e).__name__, str(e))
            except Exception as e:
                self.record(cat, f"Submit bad top-level ({type(bad_top).__name__})", False, type(e).__name__, f"Unhandled error: {e}")

        # 2.4 Poll response top-level is list or string or None
        for bad_top in [
            ["an", "array"],
            "string response",
            None,
        ]:
            client = KalodataClient(token="valid_token", max_polls=2, poll_interval=0.001)
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=bad_top)
            mock_resp.text = AsyncMock(return_value=str(bad_top))
            mock_resp.__aenter__.return_value = mock_resp
            mock_session = MagicMock()
            mock_session.get.return_value = mock_resp
            mock_session.closed = False
            client._custom_session = mock_session

            try:
                await client.poll_task("task_123")
                self.record(cat, f"Poll bad top-level ({type(bad_top).__name__})", False, None, "Expected KalodataAPIError")
            except KalodataAPIError as e:
                self.record(cat, f"Poll bad top-level ({type(bad_top).__name__})", True, type(e).__name__, str(e))
            except Exception as e:
                self.record(cat, f"Poll bad top-level ({type(bad_top).__name__})", False, type(e).__name__, f"Unhandled error: {e}")

        # 2.5 Submit response with data=None or data='string'
        for bad_data in [None, "not_a_dict", [1, 2, 3]]:
            client = KalodataClient(token="valid_token")
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value={"success": True, "data": bad_data})
            mock_resp.__aenter__.return_value = mock_resp
            mock_session = MagicMock()
            mock_session.post.return_value = mock_resp
            mock_session.closed = False
            client._custom_session = mock_session

            try:
                await client.submit_query("query")
                self.record(cat, f"Submit data={type(bad_data).__name__}", False, None, "Expected KalodataAPIError")
            except KalodataAPIError as e:
                self.record(cat, f"Submit data={type(bad_data).__name__}", True, type(e).__name__, str(e))
            except Exception as e:
                self.record(cat, f"Submit data={type(bad_data).__name__}", False, type(e).__name__, f"Unhandled error: {e}")

        # 2.6 Poll response with data=None or data='string'
        for bad_data in [None, "running_string", 42]:
            client = KalodataClient(token="valid_token", max_polls=2, poll_interval=0.001)
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value={"success": True, "data": bad_data})
            mock_resp.__aenter__.return_value = mock_resp
            mock_session = MagicMock()
            mock_session.get.return_value = mock_resp
            mock_session.closed = False
            client._custom_session = mock_session

            try:
                await client.poll_task("task_123")
                self.record(cat, f"Poll data={type(bad_data).__name__}", False, None, "Expected KalodataAPIError")
            except KalodataAPIError as e:
                self.record(cat, f"Poll data={type(bad_data).__name__}", True, type(e).__name__, str(e))
            except Exception as e:
                self.record(cat, f"Poll data={type(bad_data).__name__}", False, type(e).__name__, f"Unhandled error: {e}")

        # 2.7 Poll response with status='error' and error=None or error='string'
        for bad_err in ["String error message", None, 500, ["err1", "err2"]]:
            client = KalodataClient(token="valid_token", max_polls=2, poll_interval=0.001)
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value={"success": True, "data": {"status": "error", "error": bad_err}})
            mock_resp.__aenter__.return_value = mock_resp
            mock_session = MagicMock()
            mock_session.get.return_value = mock_resp
            mock_session.closed = False
            client._custom_session = mock_session

            try:
                await client.poll_task("task_123")
                self.record(cat, f"Poll error field={type(bad_err).__name__}", False, None, "Expected KalodataAPIError")
            except KalodataAPIError as e:
                self.record(cat, f"Poll error field={type(bad_err).__name__}", True, type(e).__name__, str(e))
            except Exception as e:
                self.record(cat, f"Poll error field={type(bad_err).__name__}", False, type(e).__name__, f"Unhandled error: {e}")

        # 2.8 Rejection with message=None
        for endpoint, is_post in [("submit", True), ("poll", False)]:
            client = KalodataClient(token="valid_token", max_polls=2, poll_interval=0.001)
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value={"success": False, "code": 500, "message": None})
            mock_resp.__aenter__.return_value = mock_resp
            mock_session = MagicMock()
            if is_post:
                mock_session.post.return_value = mock_resp
            else:
                mock_session.get.return_value = mock_resp
            mock_session.closed = False
            client._custom_session = mock_session

            try:
                if is_post:
                    await client.submit_query("query")
                else:
                    await client.poll_task("task_123")
                self.record(cat, f"{endpoint} message=None rejection", False, None, "Expected KalodataAPIError")
            except KalodataAPIError as e:
                self.record(cat, f"{endpoint} message=None rejection", True, type(e).__name__, str(e))
            except Exception as e:
                self.record(cat, f"{endpoint} message=None rejection", False, type(e).__name__, f"Unhandled error: {e}")

    # -------------------------------------------------------------------------
    # 3. Product Parsing & Numeric Type Boundary Attacks
    # -------------------------------------------------------------------------
    async def test_product_parsing_boundaries(self) -> None:
        cat = "Product Schema & Boundary Coercion"
        client = KalodataClient(token="valid_token")

        # 3.1 Non-dict result_data
        try:
            prods = client._parse_products(None, "niche", 10)  # type: ignore
            self.record(cat, "Parse products with result_data=None", isinstance(prods, list), None, f"Returned {prods}")
        except Exception as e:
            self.record(cat, "Parse products with result_data=None", False, type(e).__name__, f"Crash: {e}")

        # 3.2 Corrupted product list items (None, ints, strings, empty dicts)
        dirty_items = [
            None,
            "not a dict",
            12345,
            [],
            {},  # empty dict -> should fill defaults
            {"product_id": "p_valid", "title": "Valid Prod", "price": 100000.0, "commission_rate": 0.20},
        ]
        try:
            res = client._parse_products({"products": dirty_items}, "thoi_trang_nu", 10)
            # Should filter non-dicts and produce 2 items (one from {}, one from p_valid)
            valid = len(res) == 2 and res[1]["product_id"] == "p_valid"
            self.record(cat, "Parse dirty list with non-dicts", valid, None, f"Parsed {len(res)} items")
        except Exception as e:
            self.record(cat, "Parse dirty list with non-dicts", False, type(e).__name__, f"Crash: {e}")

        # 3.3 Numeric Edge Cases (NaN, Inf, negative, scientific notation)
        edge_product = {
            "product_id": "p_edge",
            "title": "Edge Product",
            "price": float("nan"),
            "commission_rate": float("nan"),
            "sales_30d": float("nan"),
            "revenue_30d": float("nan"),
        }
        try:
            res = client._parse_products({"products": [edge_product]}, "thoi_trang_nu", 10)
            self.record(cat, "Product with NaN numerics", True, None, f"Parsed item: {res[0] if res else None}")
        except Exception as e:
            self.record(cat, "Product with NaN numerics", False, type(e).__name__, f"Crash on NaN: {e}")

        edge_inf_product = {
            "product_id": "p_edge_inf",
            "title": "Infinity Product",
            "price": float("inf"),
            "commission_rate": float("inf"),
            "sales_30d": float("inf"),
            "revenue_30d": float("inf"),
        }
        try:
            res = client._parse_products({"products": [edge_inf_product]}, "thoi_trang_nu", 10)
            self.record(cat, "Product with Inf numerics", True, None, f"Parsed item: {res[0] if res else None}")
        except Exception as e:
            self.record(cat, "Product with Inf numerics", False, type(e).__name__, f"Crash on Inf: {e}")

        # 3.4 String numerics variations
        string_variations = [
            {"sales_30d": "10k", "commission_rate": "25%"},
            {"sales_30d": "1.5k", "commission_rate": "15.5%"},
            {"sales_30d": "1,000,000", "price": "199.000đ"},
            {"sales_30d": "N/A", "price": "free", "commission_rate": "unknown"},
        ]
        try:
            res = client._parse_products({"products": string_variations}, "thoi_trang_nu", 10)
            self.record(cat, "String numeric representations (10k, 25%, 199.000đ, N/A)", len(res) == 4, None, f"Coerced: {[r['sales_30d'] for r in res]}")
        except Exception as e:
            self.record(cat, "String numeric representations", False, type(e).__name__, f"Crash: {e}")

        # 3.5 Malformed markdown embedded JSON
        malformed_markdowns = [
            "```json\n[ {'product_id': 'bad_quotes'} ]\n```",  # single quotes
            "```json\n[ {\"product_id\": 1, unclosed ...\n```",
            "No json code block here at all",
        ]
        for idx, md in enumerate(malformed_markdowns):
            try:
                res = client._parse_products({"report": md}, "thoi_trang_nu", 10)
                self.record(cat, f"Malformed markdown JSON #{idx+1}", isinstance(res, list), None, f"Returned {len(res)} items")
            except Exception as e:
                self.record(cat, f"Malformed markdown JSON #{idx+1}", False, type(e).__name__, f"Crash: {e}")

    # -------------------------------------------------------------------------
    # 4. Polling Timeout, Network Errors, and Concurrency
    # -------------------------------------------------------------------------
    async def test_resilience_and_concurrency(self) -> None:
        cat = "Resilience & Concurrency"

        # 4.1 Polling loop maximum attempts exceeded raises KalodataTimeoutError
        client = KalodataClient(token="valid_token", poll_interval=0.001, max_polls=5)
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={"success": True, "data": {"status": "running"}})
        mock_resp.__aenter__.return_value = mock_resp
        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp
        mock_session.closed = False
        client._custom_session = mock_session

        try:
            await client.poll_task("task_never_finishes")
            self.record(cat, "Polling max_polls exceeded", False, None, "Expected KalodataTimeoutError")
        except KalodataTimeoutError as e:
            self.record(cat, "Polling max_polls exceeded", True, type(e).__name__, str(e))
        except Exception as e:
            self.record(cat, "Polling max_polls exceeded", False, type(e).__name__, f"Unexpected error: {e}")

        # 4.2 Network exception during submit and poll
        for method, is_post in [("submit", True), ("poll", False)]:
            client = KalodataClient(token="valid_token", poll_interval=0.001, max_polls=2)
            mock_session = MagicMock()
            if is_post:
                mock_session.post.side_effect = aiohttp.ClientConnectorError(MagicMock(), OSError("Connection refused"))
            else:
                mock_session.get.side_effect = asyncio.TimeoutError("Socket read timeout")
            mock_session.closed = False
            client._custom_session = mock_session

            try:
                if is_post:
                    await client.submit_query("query")
                else:
                    await client.poll_task("task_123")
                self.record(cat, f"Network transport error during {method}", False, None, "Expected KalodataNetworkError")
            except KalodataNetworkError as e:
                self.record(cat, f"Network transport error during {method}", True, type(e).__name__, str(e))
            except Exception as e:
                self.record(cat, f"Network transport error during {method}", False, type(e).__name__, f"Unexpected error: {e}")

        # 4.3 Rapid concurrent queries on shared client instance
        client = KalodataClient(token="valid_token", poll_interval=0.001, max_polls=5)
        mock_submit_resp = AsyncMock()
        mock_submit_resp.status = 200
        mock_submit_resp.json = AsyncMock(return_value={"success": True, "data": {"task_id": "concurrent_task"}})
        mock_submit_resp.__aenter__.return_value = mock_submit_resp

        mock_poll_resp = AsyncMock()
        mock_poll_resp.status = 200
        mock_poll_resp.json = AsyncMock(return_value={
            "success": True,
            "data": {
                "status": "completed",
                "products": [{"product_id": "p1", "price": 100000.0, "commission_rate": 0.1}],
            },
        })
        mock_poll_resp.__aenter__.return_value = mock_poll_resp

        mock_session = MagicMock()
        mock_session.post.return_value = mock_submit_resp
        mock_session.get.return_value = mock_poll_resp
        mock_session.closed = False
        client._custom_session = mock_session

        try:
            # 50 concurrent requests
            tasks = [client.get_top_products(f"niche_{i}", limit=1) for i in range(50)]
            results = await asyncio.gather(*tasks)
            self.record(cat, "50 concurrent queries on shared client", len(results) == 50, None, f"Completed {len(results)} queries")
        except Exception as e:
            self.record(cat, "50 concurrent queries on shared client", False, type(e).__name__, f"Crash during concurrency: {e}")

        # 4.4 Repeated context manager lifecycle
        try:
            for _ in range(10):
                async with KalodataClient(token="valid_token") as c:
                    assert c.token == "valid_token"
            self.record(cat, "Repeated context manager open/close cycle", True, None, "Clean open/close across 10 iterations")
        except Exception as e:
            self.record(cat, "Repeated context manager open/close cycle", False, type(e).__name__, f"Crash: {e}")


async def main() -> int:
    tester = KalodataAdversarialTester()
    print("=====================================================================")
    print("AMAS v1.4.0 — KalodataClient Empirical Adversarial Stress Harness")
    print("=====================================================================")

    await tester.test_token_boundaries()
    await tester.test_malformed_payloads()
    await tester.test_product_parsing_boundaries()
    await tester.test_resilience_and_concurrency()

    passed_count = sum(1 for r in tester.results if r.passed)
    failed_count = sum(1 for r in tester.results if not r.passed)
    total_count = len(tester.results)

    print(f"\nTotal Test Cases: {total_count}")
    print(f"Passed: {passed_count}")
    print(f"Failed / Gaps: {failed_count}")
    print(f"Success Rate: {(passed_count / total_count) * 100:.1f}%\n")

    current_cat = ""
    for r in tester.results:
        if r.category != current_cat:
            current_cat = r.category
            print(f"\n--- {current_cat} ---")
        status = "PASS" if r.passed else "FAIL"
        print(f"[{status}] {r.name}")
        if not r.passed or r.exception_type:
            print(f"       Details: {r.details} (exc: {r.exception_type})")

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
