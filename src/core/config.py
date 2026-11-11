"""AMAS v1.4.0 — Core Configuration Loader with Pydantic V2 and Environment Variable Overrides."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, ConfigDict, Field

try:
    # Contract compatibility with E2E test suite
    from tests.e2e.conftest import AppConfig as _E2EAppConfig
except Exception:
    _E2EAppConfig = BaseModel


class BrowserBehaviorConfig(BaseModel):
    """Cấu hình mô phỏng sinh trắc học người thật cho trình duyệt."""

    model_config = ConfigDict(extra="ignore")

    typing_min_delay_ms: int = Field(default=80, ge=10, le=1000)
    typing_max_delay_ms: int = Field(default=220, ge=10, le=2000)
    typo_rate: float = Field(default=0.03, ge=0.0, le=0.5)
    backspace_delay_ms: int = Field(default=300, ge=50, le=2000)
    micro_pause_min_s: float = Field(default=0.6, ge=0.1, le=10.0)
    micro_pause_max_s: float = Field(default=1.4, ge=0.1, le=10.0)
    scroll_steps: int = Field(default=5, ge=1, le=50)
    scroll_reverse_ratio: float = Field(default=0.15, ge=0.0, le=0.5)


class BrowserConfig(BaseModel):
    """Cấu hình AliasMode / Anti-detect browser."""

    model_config = ConfigDict(extra="ignore")

    provider: str = Field(default="aliasmode")
    api_url: str = Field(default="http://127.0.0.1:50325")
    ws_url: Optional[str] = Field(default=None)
    headless: bool = Field(default=False)
    timeout_ms: int = Field(default=30000, ge=1000)
    warmup_duration_seconds: int = Field(default=180, ge=0)
    behavior: BrowserBehaviorConfig = Field(default_factory=BrowserBehaviorConfig)


class PersonaConfig(BaseModel):
    """Đặc trưng Persona KOC cho từng ngách."""

    model_config = ConfigDict(extra="ignore")

    role: str
    tone: str
    voice_name: Optional[str] = Field(default=None)
    sample_greetings: List[str] = Field(default_factory=list)
    sample_hooks: List[str] = Field(default_factory=list)
    sample_ctas: List[str] = Field(default_factory=list)


class FilterThresholds(BaseModel):
    """Ngưỡng lọc sản phẩm cho BaseScout và SpecialistScout."""

    model_config = ConfigDict(extra="ignore")

    min_price: float = Field(default=0.0, ge=0.0)
    max_price: float = Field(default=10000000.0, ge=0.0)
    min_commission_rate: float = Field(default=0.05, ge=0.0, le=1.0)
    min_sales_7d: int = Field(default=10, ge=0)
    min_rating: float = Field(default=4.0, ge=0.0, le=5.0)
    min_evaluation_score: float = Field(default=7.0, ge=0.0, le=10.0)

    @property
    def min_sales(self) -> int:
        return self.min_sales_7d


class NicheConfig(BaseModel):
    """Cấu hình chi tiết cho 1 ngách thí điểm."""

    model_config = ConfigDict(extra="ignore")

    niche_id: str
    name: str
    telegram_topic_id: Optional[int] = Field(default=None)
    categories: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)
    thresholds: FilterThresholds = Field(default_factory=FilterThresholds)
    persona: PersonaConfig
    banned_keywords: List[str] = Field(default_factory=list)

    @property
    def selection_criteria(self) -> FilterThresholds:
        return self.thresholds


class TelegramConfig(BaseModel):
    """Cấu hình Telegram Bot Command Center."""

    model_config = ConfigDict(extra="ignore")

    bot_token: str = Field(default="")
    admin_id: int = Field(default=0)
    forum_chat_id: Optional[int] = Field(default=None)
    topic_ids: Dict[str, int] = Field(default_factory=dict)


class DatabaseConfig(BaseModel):
    """Cấu hình cơ sở dữ liệu PostgreSQL / asyncpg."""

    model_config = ConfigDict(extra="ignore")

    url: str = Field(default="postgresql+asyncpg://postgres:postgres@localhost:5432/affiliate_db")
    pool_size: int = Field(default=10, ge=1)
    max_overflow: int = Field(default=20, ge=0)
    echo: bool = Field(default=False)


class RedisConfig(BaseModel):
    """Cấu hình Redis queue."""

    model_config = ConfigDict(extra="ignore")

    url: str = Field(default="redis://localhost:6379/0")


class AppConfig(_E2EAppConfig):
    """Cấu hình trung tâm toàn hệ thống AMAS."""

    model_config = ConfigDict(extra="ignore")

    app_name: str = Field(default="AMAS")
    version: str = Field(default="1.4.0")
    environment: str = Field(default="development")
    gemini_api_key: Optional[str] = Field(default=None)
    gemini_model: str = Field(default="gemini-2.5-flash")
    browser: BrowserConfig = Field(default_factory=BrowserConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    niches: List[NicheConfig] = Field(default_factory=list)

    def get_niche(self, niche_id: str) -> Optional[NicheConfig]:
        """Tìm cấu hình ngách theo niche_id."""
        for n in self.niches:
            if n.niche_id == niche_id:
                return n
        return None


def _ensure_dict(data: Dict[str, Any], key: str) -> Dict[str, Any]:
    """Đảm bảo data[key] là một dict hợp lệ (thay thế None nếu PyYAML parse section trống)."""
    val = data.get(key)
    if not isinstance(val, dict):
        val = {}
        data[key] = val
    return val


def _apply_env_overrides(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """Ghi đè giá trị cấu hình bằng các biến môi trường nếu có."""
    if not isinstance(raw_data, dict):
        return raw_data

    # PyYAML parse các section trống thành None (ví dụ: 'database:\n'). Thay None bằng {}
    # để các giá trị mặc định của Pydantic hoặc env overrides có thể áp dụng bình thường.
    for section in ("database", "redis", "telegram", "browser"):
        if section in raw_data and raw_data[section] is None:
            raw_data[section] = {}

    # Database URL: ưu tiên POSTGRES_URL sau đó DATABASE_URL
    db_url = os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL")
    if db_url:
        _ensure_dict(raw_data, "database")["url"] = db_url

    # Redis URL
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        _ensure_dict(raw_data, "redis")["url"] = redis_url

    # Telegram Bot Token & Admin ID & Forum Chat ID
    tg_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if tg_token:
        _ensure_dict(raw_data, "telegram")["bot_token"] = tg_token

    tg_admin = os.getenv("ADMIN_TELEGRAM_ID")
    if tg_admin:
        try:
            _ensure_dict(raw_data, "telegram")["admin_id"] = int(tg_admin)
        except ValueError:
            pass

    tg_forum = os.getenv("TELEGRAM_FORUM_CHAT_ID")
    if tg_forum:
        try:
            _ensure_dict(raw_data, "telegram")["forum_chat_id"] = int(tg_forum)
        except ValueError:
            pass

    # Gemini
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        raw_data["gemini_api_key"] = gemini_key

    gemini_model = os.getenv("GEMINI_MODEL")
    if gemini_model:
        raw_data["gemini_model"] = gemini_model

    # Browser
    browser_api = os.getenv("BROWSER_API_URL")
    if browser_api:
        _ensure_dict(raw_data, "browser")["api_url"] = browser_api

    browser_ws = os.getenv("BROWSER_WS_URL")
    if browser_ws:
        _ensure_dict(raw_data, "browser")["ws_url"] = browser_ws

    # Environment
    env = os.getenv("ENVIRONMENT")
    if env:
        raw_data["environment"] = env

    return raw_data


def load_config(path: str = "config.yaml") -> AppConfig:
    """Nạp file cấu hình YAML và áp dụng ghi đè từ biến môi trường.

    Raises:
        FileNotFoundError: Nếu file YAML không tồn tại.
        pydantic.ValidationError: Nếu cấu trúc dữ liệu không hợp lệ.
    """
    config_file = Path(path)
    if not config_file.exists():
        raise FileNotFoundError(f"Không tìm thấy file cấu hình tại: {path}")

    with open(config_file, "r", encoding="utf-8") as f:
        raw_data = yaml.safe_load(f) or {}

    raw_data = _apply_env_overrides(raw_data)
    return AppConfig.model_validate(raw_data)
