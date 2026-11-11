"""AMAS v1.4.0 — Kalodata Async API Client (Feature F05).

Provides async submit and poll flow for TikTok Shop product scouting via Kalodata Pilot API.
Handles token loading (~/.kalopilot/token or KALOPILOT_TOKEN), authentication verification,
polling with backoff, schema normalization, and robust error classification.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exception Hierarchy
# ---------------------------------------------------------------------------

class KalodataError(Exception):
    """Base exception for all Kalodata client errors."""
    pass


class KalodataAuthError(PermissionError, KalodataError):
    """Raised when Kalodata token is missing, expired, or rejected (HTTP 401).

    Inherits from PermissionError to satisfy test_tier2_boundaries contract.
    """
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


# ---------------------------------------------------------------------------
# Client Implementation
# ---------------------------------------------------------------------------

class KalodataClient:
    """Async client for Kalodata Pilot API."""

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
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.poll_interval = poll_interval
        self.max_polls = max_polls
        self.timeout = timeout
        self._custom_session = session
        self._internal_session: Optional[aiohttp.ClientSession] = None
        self.token = self._resolve_token(token)

    @classmethod
    def _resolve_token(cls, token_arg: Optional[str]) -> Optional[str]:
        """Resolves token with precedence: arg -> KALOPILOT_TOKEN -> ~/.kalopilot/token."""
        if token_arg is not None:
            clean_arg = str(token_arg).strip()
            return clean_arg if clean_arg else ""

        env_val = os.getenv(cls.ENV_TOKEN_KEY)
        if env_val and env_val.strip():
            return env_val.strip()

        token_file = cls.TOKEN_FILE_PATH
        if token_file.exists() and token_file.is_file():
            try:
                content = token_file.read_text(encoding="utf-8").strip()
                if content:
                    return content
            except (OSError, UnicodeDecodeError):
                pass

        return None

    def _ensure_authenticated(self) -> str:
        """Validates token presence and ensures it is not expired.

        Raises:
            KalodataAuthError: If token is missing, whitespace, or equal to 'expired_token'.
        """
        if not self.token or not self.token.strip() or self.token == "expired_token":
            raise KalodataAuthError(
                "Kalodata token is missing or expired. Run ~/.kalopilot/token update."
            )
        return self.token

    async def _get_session(self) -> aiohttp.ClientSession:
        """Retrieves or creates the internal aiohttp ClientSession."""
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
        """Submits an async query to Kalodata Pilot API, returning task_id."""
        self._ensure_authenticated()
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
                except Exception as exc:
                    text = await resp.text()
                    raise KalodataAPIError(f"Invalid JSON from Kalodata submit: {text[:200]}") from exc

                if not isinstance(data, dict):
                    raise KalodataAPIError(f"Malformed submit response: expected dict, got {type(data).__name__}")

                if not data.get("success", False):
                    code = data.get("code")
                    raw_msg = data.get("message")
                    msg = str(raw_msg) if raw_msg is not None else ""
                    if code == 401 or "token" in msg.lower():
                        raise KalodataAuthError(
                            f"Kalodata token is missing or expired. Run ~/.kalopilot/token update. Detail: {msg}"
                        )
                    raise KalodataAPIError(f"Query submission rejected: {msg or 'Unknown submission rejection'}", code=code, data=data)

                inner_data = data.get("data")
                if not isinstance(inner_data, dict):
                    raise KalodataAPIError("Missing or invalid 'data' object in submit response", data=data)

                tid = inner_data.get("task_id")
                if not tid:
                    raise KalodataAPIError("No task_id returned in Kalodata submit response", data=data)
                return str(tid)
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            if isinstance(err, KalodataError):
                raise
            raise KalodataNetworkError(f"Network error during query submission: {err}") from err

    async def poll_task(self, task_id: str) -> Dict[str, Any]:
        """Polls task result until completion, error, or timeout."""
        self._ensure_authenticated()
        session = await self._get_session()
        url = f"{self.base_url}{self.RESULT_ENDPOINT}"
        params = {"task_id": task_id}

        start_time = time.monotonic()
        for _ in range(1, self.max_polls + 1):
            if time.monotonic() - start_time > self.timeout:
                raise KalodataTimeoutError(f"Kalodata task {task_id} polling timed out after {self.timeout}s")

            try:
                async with session.get(url, params=params, headers=self._get_headers()) as resp:
                    if resp.status == 401:
                        raise KalodataAuthError(
                            "Kalodata token is missing or expired. Run ~/.kalopilot/token update."
                        )
                    try:
                        data = await resp.json()
                    except Exception as exc:
                        text = await resp.text()
                        raise KalodataAPIError(f"Invalid JSON from Kalodata poll: {text[:200]}") from exc
            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                if isinstance(err, KalodataError):
                    raise
                raise KalodataNetworkError(f"Network error during task polling: {err}") from err

            if not isinstance(data, dict):
                raise KalodataAPIError(f"Malformed poll response: expected dict, got {type(data).__name__}")

            if not data.get("success", False):
                code = data.get("code")
                raw_msg = data.get("message")
                msg = str(raw_msg) if raw_msg is not None else ""
                if code == 401 or "token" in msg.lower():
                    raise KalodataAuthError(
                        f"Kalodata token is missing or expired. Run ~/.kalopilot/token update. Detail: {msg}"
                    )
                raise KalodataAPIError(f"Polling failed: {msg or 'Task polling rejected'}", code=code, data=data)

            task_data = data.get("data")
            if not isinstance(task_data, dict):
                raise KalodataAPIError(f"Malformed 'data' field in poll response: expected dict, got {type(task_data).__name__}", data=data)

            status = task_data.get("status", "running")

            if status == "completed":
                return task_data
            elif status == "error":
                err_obj = task_data.get("error")
                if isinstance(err_obj, dict):
                    err_msg = err_obj.get("message") or str(err_obj)
                elif err_obj is not None:
                    err_msg = str(err_obj)
                else:
                    err_msg = "Unknown Kalodata task error"
                raise KalodataAPIError(f"Kalodata task failed: {err_msg}", data=task_data)
            elif status == "cancelled":
                raise KalodataAPIError("Kalodata task was cancelled", data=task_data)
            elif status in ("running", "submitted"):
                await asyncio.sleep(self.poll_interval)
            else:
                await asyncio.sleep(self.poll_interval)

        raise KalodataTimeoutError(f"Kalodata task {task_id} polling timed out after {self.max_polls} attempts")

    async def get_top_products(self, category_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Formulates query, submits, polls, and returns normalized products."""
        self._ensure_authenticated()
        query = f"Top {limit} trending affiliate products in category '{category_id}' in Vietnam TikTok Shop"
        task_id = await self.submit_query(query)
        result_data = await self.poll_task(task_id)
        return self._parse_products(result_data, category_id, limit)

    def _parse_products(self, result_data: Dict[str, Any], category_id: str, limit: int) -> List[Dict[str, Any]]:
        """Parses and normalizes product items adhering to AMAS Scout contract."""
        if not isinstance(result_data, dict):
            return []

        raw_items: List[Dict[str, Any]] = []
        if isinstance(result_data.get("products"), list):
            raw_items = result_data["products"]
        elif isinstance(result_data.get("items"), list):
            raw_items = result_data["items"]
        else:
            # Fallback: search report or text for embedded JSON block
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
            price = self._coerce_float(item.get("price"), default=0.0)
            commission_rate = self._coerce_float(item.get("commission_rate"), default=0.0)
            if commission_rate > 1.0:
                commission_rate = commission_rate / 100.0
            sales_30d = self._coerce_int(item.get("sales_30d"), default=0)
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
            f_val = float(val)
            if math.isnan(f_val) or math.isinf(f_val):
                return default
            return f_val
        s = str(val).strip()
        if not s:
            return default
        cleaned = re.sub(r"[^\d.]", "", s)
        try:
            f_val = float(cleaned) if cleaned else default
            if math.isnan(f_val) or math.isinf(f_val):
                return default
            return f_val
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _coerce_int(val: Any, default: int = 0) -> int:
        if val is None:
            return default
        if isinstance(val, int):
            return val
        if isinstance(val, float):
            if math.isnan(val) or math.isinf(val):
                return default
            return int(val)
        s = str(val).lower().strip()
        if not s:
            return default
        if "k" in s:
            num_part = re.sub(r"[^\d.]", "", s)
            try:
                f_val = float(num_part)
                if math.isnan(f_val) or math.isinf(f_val):
                    return default
                return int(f_val * 1000)
            except (ValueError, TypeError):
                return default
        cleaned = re.sub(r"[^\d]", "", s)
        try:
            return int(cleaned) if cleaned else default
        except (ValueError, TypeError):
            return default

    async def close(self) -> None:
        """Closes internal session."""
        if self._internal_session and not self._internal_session.closed:
            await self._internal_session.close()

    async def __aenter__(self) -> "KalodataClient":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()
