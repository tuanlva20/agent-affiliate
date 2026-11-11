"""AMAS v1.4.0 — Kalodata Client Adversarial Stress & Robustness Tests.

Empirical verification of KalodataClient resilience against edge cases:
- Corrupted token files (non-UTF8 bytes)
- Corrupted and malformed API payloads (HTML 502, truncated JSON, non-dict top levels)
- Null and non-dict nested structures (data=None, error=str, message=None)
- Malformed numeric fields (NaN, Inf) in product parser
- Rapid concurrent queries and polling timeout resilience
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.kalodata_client import (
    KalodataAPIError,
    KalodataAuthError,
    KalodataClient,
    KalodataError,
    KalodataNetworkError,
    KalodataTimeoutError,
)


# ---------------------------------------------------------------------------
# 1. Token Boundary & Corrupted Token File Tests
# ---------------------------------------------------------------------------

def test_adversarial_token_file_corrupted_binary():
    """Token file containing non-UTF8 binary data should not crash with unhandled UnicodeDecodeError."""
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        tf.write(b"\x80\xff\xfe\x00\xab\xcd")
        corrupted_path = Path(tf.name)

    try:
        with patch.dict(os.environ, {}, clear=True), \
             patch.object(KalodataClient, "TOKEN_FILE_PATH", corrupted_path):
            # Client initialization should handle corrupted file gracefully
            client = KalodataClient(token=None)
            assert client.token is None
    finally:
        if corrupted_path.exists():
            corrupted_path.unlink()


# ---------------------------------------------------------------------------
# 2. Corrupted and Malformed API Payloads
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_adversarial_poll_corrupted_json():
    """Server returning HTML or corrupted JSON during poll_task must raise KalodataError, not raw JSONDecodeError."""
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

    with pytest.raises(KalodataError) as exc_info:
        await client.poll_task("task_test_123")
    assert isinstance(exc_info.value, (KalodataAPIError, KalodataNetworkError))


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_top", [
    ["an", "array", "of", "messages"],
    "Gateway timeout string",
    12345,
    None,
])
async def test_adversarial_submit_and_poll_non_dict_top_level(bad_top: Any):
    """Server returning non-dict top-level JSON must raise KalodataAPIError, not AttributeError."""
    client = KalodataClient(token="valid_token", max_polls=2, poll_interval=0.001)

    # Test submit_query with non-dict
    mock_submit_resp = AsyncMock()
    mock_submit_resp.status = 200
    mock_submit_resp.json = AsyncMock(return_value=bad_top)
    mock_submit_resp.text = AsyncMock(return_value=str(bad_top))
    mock_submit_resp.__aenter__.return_value = mock_submit_resp

    mock_session = MagicMock()
    mock_session.post.return_value = mock_submit_resp
    mock_session.closed = False
    client._custom_session = mock_session

    with pytest.raises(KalodataAPIError):
        await client.submit_query("test query")

    # Test poll_task with non-dict
    mock_poll_resp = AsyncMock()
    mock_poll_resp.status = 200
    mock_poll_resp.json = AsyncMock(return_value=bad_top)
    mock_poll_resp.text = AsyncMock(return_value=str(bad_top))
    mock_poll_resp.__aenter__.return_value = mock_poll_resp

    mock_session.get.return_value = mock_poll_resp
    with pytest.raises(KalodataAPIError):
        await client.poll_task("task_test_123")


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_data", [None, "string_data", [1, 2, 3], 42])
async def test_adversarial_data_field_non_dict(bad_data: Any):
    """Payloads where 'data' is null, string, or list must raise KalodataAPIError, not AttributeError."""
    client = KalodataClient(token="valid_token", max_polls=2, poll_interval=0.001)

    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value={"success": True, "data": bad_data})
    mock_resp.text = AsyncMock(return_value=str(bad_data))
    mock_resp.__aenter__.return_value = mock_resp

    mock_session = MagicMock()
    mock_session.post.return_value = mock_resp
    mock_session.get.return_value = mock_resp
    mock_session.closed = False
    client._custom_session = mock_session

    # Submit should fail gracefully
    with pytest.raises(KalodataAPIError):
        await client.submit_query("query")

    # Poll should fail gracefully
    with pytest.raises(KalodataAPIError):
        await client.poll_task("task_123")


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_err", ["Direct error message string", None, 500, ["err1", "err2"]])
async def test_adversarial_error_field_non_dict(bad_err: Any):
    """When status='error' and error is a string or null, must raise KalodataAPIError, not AttributeError."""
    client = KalodataClient(token="valid_token", max_polls=2, poll_interval=0.001)

    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value={
        "success": True,
        "data": {
            "status": "error",
            "error": bad_err,
        },
    })
    mock_resp.__aenter__.return_value = mock_resp

    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp
    mock_session.closed = False
    client._custom_session = mock_session

    with pytest.raises(KalodataAPIError) as exc_info:
        await client.poll_task("task_err")
    assert "Kalodata task failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_adversarial_null_message_rejection():
    """API returning success=False with message=None must raise KalodataAPIError, not AttributeError on msg.lower()."""
    client = KalodataClient(token="valid_token", max_polls=2, poll_interval=0.001)

    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value={"success": False, "code": 500, "message": None})
    mock_resp.__aenter__.return_value = mock_resp

    mock_session = MagicMock()
    mock_session.post.return_value = mock_resp
    mock_session.get.return_value = mock_resp
    mock_session.closed = False
    client._custom_session = mock_session

    with pytest.raises(KalodataAPIError):
        await client.submit_query("query")

    with pytest.raises(KalodataAPIError):
        await client.poll_task("task_123")


# ---------------------------------------------------------------------------
# 3. Product Parsing & Numeric Type Boundary Attacks
# ---------------------------------------------------------------------------

def test_adversarial_parse_products_result_data_none():
    """_parse_products with result_data=None or non-dict must return empty list without crashing."""
    client = KalodataClient(token="valid_token")
    res1 = client._parse_products(None, "thoi_trang_nu", 10)  # type: ignore
    assert isinstance(res1, list) and len(res1) == 0

    res2 = client._parse_products("not_a_dict", "thoi_trang_nu", 10)  # type: ignore
    assert isinstance(res2, list) and len(res2) == 0


def test_adversarial_parse_products_nan_and_inf_handling():
    """Products with NaN or Inf numerics must not crash with ValueError or OverflowError."""
    client = KalodataClient(token="valid_token")
    raw_payload = {
        "products": [
            {
                "product_id": "p_nan",
                "title": "NaN Product",
                "price": float("nan"),
                "commission_rate": float("nan"),
                "sales_30d": float("nan"),
            },
            {
                "product_id": "p_inf",
                "title": "Inf Product",
                "price": float("inf"),
                "commission_rate": float("inf"),
                "sales_30d": float("inf"),
            },
        ]
    }

    products = client._parse_products(raw_payload, "thoi_trang_nu", 10)
    assert len(products) == 2
    # Ensure sales_30d is a valid integer, not NaN or overflowed
    assert isinstance(products[0]["sales_30d"], int)
    assert isinstance(products[1]["sales_30d"], int)


# ---------------------------------------------------------------------------
# 4. Concurrency & Timeout Resilience
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_adversarial_rapid_concurrent_queries():
    """50 concurrent queries on a single client instance complete without race conditions."""
    client = KalodataClient(token="valid_token", poll_interval=0.001, max_polls=5)

    mock_submit_resp = AsyncMock()
    mock_submit_resp.status = 200
    mock_submit_resp.json = AsyncMock(return_value={"success": True, "data": {"task_id": "c_task"}})
    mock_submit_resp.__aenter__.return_value = mock_submit_resp

    mock_poll_resp = AsyncMock()
    mock_poll_resp.status = 200
    mock_poll_resp.json = AsyncMock(return_value={
        "success": True,
        "data": {
            "status": "completed",
            "products": [{"product_id": "p1", "price": 100000.0, "commission_rate": 0.15}],
        },
    })
    mock_poll_resp.__aenter__.return_value = mock_poll_resp

    mock_session = MagicMock()
    mock_session.post.return_value = mock_submit_resp
    mock_session.get.return_value = mock_poll_resp
    mock_session.closed = False
    client._custom_session = mock_session

    tasks = [client.get_top_products("test_niche", limit=1) for _ in range(50)]
    results = await asyncio.gather(*tasks)
    assert len(results) == 50
    for r in results:
        assert len(r) == 1
        assert r[0]["product_id"] == "p1"


@pytest.mark.asyncio
async def test_adversarial_polling_timeout_resilience():
    """Client raises KalodataTimeoutError when polling exhausts max_polls."""
    client = KalodataClient(token="valid_token", poll_interval=0.001, max_polls=3)

    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value={"success": True, "data": {"status": "running"}})
    mock_resp.__aenter__.return_value = mock_resp

    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp
    mock_session.closed = False
    client._custom_session = mock_session

    with pytest.raises(KalodataTimeoutError):
        await client.poll_task("task_stalled")
