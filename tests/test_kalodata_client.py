"""AMAS v1.4.0 — Kalodata Client Unit Test Suite (Feature F05).

Verifies async submit/poll protocol, token precedence and expiration checks,
schema normalization, and network/API error handling.
"""

from __future__ import annotations

import asyncio
import json
import os
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


@pytest.fixture
def mock_pilot_submit_response():
    return {
        "success": True,
        "data": {
            "task_id": "kalo_task_test_12345",
            "status": "submitted",
        },
    }


@pytest.fixture
def mock_pilot_result_completed():
    return {
        "success": True,
        "data": {
            "task_id": "kalo_task_test_12345",
            "status": "completed",
            "message_id": "msg_999",
            "products": [
                {
                    "product_id": "prod_kalo_001",
                    "title": "Váy hoa nhí dáng xòe mùa hè",
                    "price": 199000.0,
                    "commission_rate": 0.15,
                    "sales_30d": 1500,
                    "revenue_30d": 298500000.0,
                    "product_url": "https://shop.tiktok.com/view/product/prod_kalo_001",
                },
                {
                    "product_id": "prod_kalo_002",
                    "title": "Set áo blazer công sở cao cấp",
                    "price": 350000.0,
                    "commission_rate": "18%",
                    "sales_30d": "2.5k",
                    "revenue_30d": 875000000.0,
                    "product_url": "https://shop.tiktok.com/view/product/prod_kalo_002",
                },
            ],
            "text": "Phân tích xu hướng thời trang nữ",
            "credits_consumed": 10,
        },
    }


# ---------------------------------------------------------------------------
# 1. Token Resolution and Precedence Tests
# ---------------------------------------------------------------------------

def test_kalodata_client_token_resolution(tmp_path: Path):
    # 1. Explicit token argument has highest priority
    client_explicit = KalodataClient(token="explicit_token_123")
    assert client_explicit.token == "explicit_token_123"

    # 2. Environment variable KALOPILOT_TOKEN takes priority when no explicit token
    with patch.dict(os.environ, {"KALOPILOT_TOKEN": "env_token_456"}):
        client_env = KalodataClient()
        assert client_env.token == "env_token_456"

    # 3. ~/.kalopilot/token file is read when no arg and no env var
    fake_token_file = tmp_path / "fake_token"
    fake_token_file.write_text("file_token_789\n", encoding="utf-8")
    with patch.dict(os.environ, {}, clear=True), \
         patch.object(KalodataClient, "TOKEN_FILE_PATH", fake_token_file):
        client_file = KalodataClient()
        assert client_file.token == "file_token_789"


@pytest.mark.asyncio
async def test_kalodata_client_missing_or_expired_token():
    # Empty token raises PermissionError with ~/.kalopilot/token mentioned
    with patch.dict(os.environ, {}, clear=True), \
         patch.object(KalodataClient, "TOKEN_FILE_PATH", Path("/nonexistent/token")):
        client_empty = KalodataClient(token=None)
        with pytest.raises(PermissionError) as exc_info:
            await client_empty.get_top_products("thoi_trang_nu")
        assert "~/.kalopilot/token" in str(exc_info.value)
        assert isinstance(exc_info.value, KalodataAuthError)

    # "expired_token" marker raises PermissionError
    client_expired = KalodataClient(token="expired_token")
    with pytest.raises(PermissionError) as exc_info:
        await client_expired.get_top_products("thoi_trang_nu")
    assert "~/.kalopilot/token" in str(exc_info.value)
    assert isinstance(exc_info.value, KalodataAuthError)

    # Whitespace only token raises PermissionError
    client_ws = KalodataClient(token="   ")
    with pytest.raises(PermissionError) as exc_info:
        await client_ws.get_top_products("thoi_trang_nu")
    assert "~/.kalopilot/token" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 2. Schema Normalization & Return Contract Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_kalodata_client_get_top_products_schema(mock_pilot_submit_response, mock_pilot_result_completed):
    client = KalodataClient(token="valid_test_token", poll_interval=0.001)

    with patch.object(client, "submit_query", AsyncMock(return_value="kalo_task_test_12345")), \
         patch.object(client, "poll_task", AsyncMock(return_value=mock_pilot_result_completed["data"])):
        products = await client.get_top_products(category_id="thoi_trang_nu", limit=5)

    assert isinstance(products, list)
    assert len(products) == 2

    for item in products:
        assert "product_id" in item
        assert "title" in item
        assert "price" in item
        assert "commission_rate" in item
        assert "sales_30d" in item
        assert "revenue_30d" in item
        assert "product_url" in item
        assert "category_id" in item

        assert isinstance(item["product_id"], str) and len(item["product_id"]) > 0
        assert isinstance(item["title"], str) and len(item["title"]) > 0
        assert isinstance(item["price"], float) and item["price"] > 0.0
        assert isinstance(item["commission_rate"], float) and 0.0 < item["commission_rate"] <= 1.0
        assert isinstance(item["sales_30d"], int) and item["sales_30d"] >= 0
        assert isinstance(item["revenue_30d"], float) and item["revenue_30d"] >= 0.0
        assert item["category_id"] == "thoi_trang_nu"

    # Verify type conversions ("18%" -> 0.18, "2.5k" -> 2500)
    assert products[1]["commission_rate"] == 0.18
    assert products[1]["sales_30d"] == 2500


@pytest.mark.asyncio
async def test_kalodata_client_limit_and_category():
    client = KalodataClient(token="valid_test_token", poll_interval=0.001)

    # 10 mock items returned in data
    mock_data = {
        "status": "completed",
        "products": [
            {
                "product_id": f"pid_{i}",
                "title": f"Product {i}",
                "price": 100000.0 + i * 10000,
                "commission_rate": 0.15,
                "sales_30d": 100 * i,
                "revenue_30d": 10000000.0,
                "product_url": f"https://shop.tiktok.com/view/product/pid_{i}",
            }
            for i in range(10)
        ],
    }

    with patch.object(client, "submit_query", AsyncMock(return_value="t1")), \
         patch.object(client, "poll_task", AsyncMock(return_value=mock_data)):
        products_limit_3 = await client.get_top_products(category_id="do_gia_dung", limit=3)
        assert len(products_limit_3) == 3
        assert products_limit_3[0]["category_id"] == "do_gia_dung"
        assert products_limit_3[2]["product_id"] == "pid_2"

        products_limit_7 = await client.get_top_products(category_id="do_gia_dung", limit=7)
        assert len(products_limit_7) == 7


# ---------------------------------------------------------------------------
# 3. Markdown / JSON Table Parsing Fallback Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_kalodata_client_markdown_json_parsing_fallback():
    client = KalodataClient(token="valid_test_token", poll_interval=0.001)

    markdown_report = """
# Báo cáo Top Sản phẩm Thịnh hành
Dưới đây là danh sách sản phẩm:
```json
[
  {
    "product_id": "fallback_01",
    "title": "Chảo chống dính vân đá đáy từ",
    "price": 289000,
    "commission_rate": 0.20,
    "sales_30d": 3200,
    "revenue_30d": 924800000,
    "product_url": "https://shop.tiktok.com/view/product/fallback_01"
  }
]
```
Chúc bạn kinh doanh thành công!
"""
    mock_data = {
        "status": "completed",
        "report": markdown_report,
    }

    with patch.object(client, "submit_query", AsyncMock(return_value="t_fallback")), \
         patch.object(client, "poll_task", AsyncMock(return_value=mock_data)):
        products = await client.get_top_products(category_id="do_gia_dung", limit=5)
        assert len(products) == 1
        assert products[0]["product_id"] == "fallback_01"
        assert products[0]["price"] == 289000.0
        assert products[0]["commission_rate"] == 0.20


# ---------------------------------------------------------------------------
# 4. Error Handling and Lifecycle Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_kalodata_client_401_submission_raises_auth_error():
    client = KalodataClient(token="invalid_key")

    mock_resp = AsyncMock()
    mock_resp.status = 401
    mock_resp.__aenter__.return_value = mock_resp

    mock_session = MagicMock()
    mock_session.post.return_value = mock_resp
    mock_session.closed = False

    client._custom_session = mock_session

    with pytest.raises(KalodataAuthError) as exc_info:
        await client.submit_query("Test query")
    assert "~/.kalopilot/token" in str(exc_info.value)


@pytest.mark.asyncio
async def test_kalodata_client_task_error_raises_api_error():
    client = KalodataClient(token="valid_token", poll_interval=0.001)

    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value={
        "success": True,
        "data": {
            "status": "error",
            "error": {"message": "Kalopilot AI quota exhausted"},
        },
    })
    mock_resp.__aenter__.return_value = mock_resp

    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp
    mock_session.closed = False
    client._custom_session = mock_session

    with pytest.raises(KalodataAPIError) as exc_info:
        await client.poll_task("task_failed_123")
    assert "Kalopilot AI quota exhausted" in str(exc_info.value)


@pytest.mark.asyncio
async def test_kalodata_client_task_timeout():
    client = KalodataClient(token="valid_token", poll_interval=0.001, max_polls=3)

    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value={
        "success": True,
        "data": {
            "status": "running",
        },
    })
    mock_resp.__aenter__.return_value = mock_resp

    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp
    mock_session.closed = False
    client._custom_session = mock_session

    with pytest.raises(KalodataTimeoutError):
        await client.poll_task("task_stalled_123")


@pytest.mark.asyncio
async def test_kalodata_client_context_manager_teardown():
    async with KalodataClient(token="test_token") as client:
        assert client.token == "test_token"
    # Should exit cleanly without errors
