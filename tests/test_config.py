"""Unit tests for Central Configuration Loader and ToneValidator."""

import os
from pathlib import Path
import pytest
from pydantic import ValidationError

from src.core.config import AppConfig, load_config
from src.core.tone_validator import ToneValidator


# ==============================================================================
# 1. CONFIGURATION LOADER TESTS
# ==============================================================================

def test_load_config_niches_and_browser():
    """Kiểm tra đọc file config.yaml gốc của dự án."""
    config = load_config("config.yaml")

    # Kiểm tra cấu hình browser
    assert config.browser.provider == "aliasmode"
    assert config.browser.api_url == "http://127.0.0.1:50325"
    assert config.browser.headless is False
    assert config.browser.behavior.typing_min_delay_ms == 80
    assert config.browser.behavior.typing_max_delay_ms == 220
    assert config.browser.behavior.typo_rate == 0.03
    assert config.browser.behavior.micro_pause_min_s == 0.6
    assert config.browser.behavior.micro_pause_max_s == 1.4

    # Kiểm tra 2 ngách thí điểm
    assert len(config.niches) == 2
    niche_ids = [n.niche_id for n in config.niches]
    assert "thoi_trang_nu" in niche_ids
    assert "do_gia_dung" in niche_ids

    # Kiểm tra chi tiết ngách Thời trang nữ
    fashion = config.get_niche("thoi_trang_nu")
    assert fashion is not None
    assert fashion.telegram_topic_id == 2
    assert fashion.thresholds.min_price == 99000.0
    assert fashion.thresholds.min_commission_rate == 0.10
    assert len(fashion.persona.sample_greetings) > 0
    assert len(fashion.banned_keywords) > 0

    # Kiểm tra chi tiết ngách Đồ gia dụng
    homelife = config.get_niche("do_gia_dung")
    assert homelife is not None
    assert homelife.telegram_topic_id == 4
    assert homelife.thresholds.min_price == 49000.0
    assert homelife.thresholds.min_commission_rate == 0.12


def test_load_config_env_overrides(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Kiểm tra cơ chế ưu tiên ghi đè bằng biến môi trường."""
    sample_yaml = tmp_path / "custom_config.yaml"
    sample_yaml.write_text(
        """
app_name: "AMAS_CUSTOM"
browser:
  provider: "aliasmode"
  api_url: "http://127.0.0.1:50325"
niches:
  - niche_id: "thoi_trang_nu"
    name: "Thời trang nữ"
    persona:
      role: "KOC"
      tone: "Tự nhiên"
""",
        encoding="utf-8",
    )

    # Đặt các biến môi trường ghi đè
    monkeypatch.setenv("POSTGRES_URL", "postgresql+asyncpg://user:pass@remote:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://remote-redis:6379/1")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "mock_bot_token_123")
    monkeypatch.setenv("ADMIN_TELEGRAM_ID", "987654321")
    monkeypatch.setenv("TELEGRAM_FORUM_CHAT_ID", "-1009876543210")
    monkeypatch.setenv("GEMINI_API_KEY", "mock_gemini_key_456")
    monkeypatch.setenv("BROWSER_API_URL", "http://aliasmode-host:50325")
    monkeypatch.setenv("ENVIRONMENT", "staging")

    config = load_config(str(sample_yaml))

    assert config.database.url == "postgresql+asyncpg://user:pass@remote:5432/db"
    assert config.redis.url == "redis://remote-redis:6379/1"
    assert config.telegram.bot_token == "mock_bot_token_123"
    assert config.telegram.admin_id == 987654321
    assert config.telegram.forum_chat_id == -1009876543210
    assert config.gemini_api_key == "mock_gemini_key_456"
    assert config.browser.api_url == "http://aliasmode-host:50325"
    assert config.environment == "staging"


def test_load_config_missing_file():
    """Kiểm tra bắn lỗi FileNotFoundError khi đường dẫn file không tồn tại."""
    with pytest.raises(FileNotFoundError):
        load_config("non_existent_config.yaml")


def test_load_config_invalid_schema(tmp_path: Path):
    """Kiểm tra bắn lỗi ValidationError khi dữ liệu sai quy chuẩn Pydantic."""
    broken_yaml = tmp_path / "broken_config.yaml"
    broken_yaml.write_text(
        """
browser:
  behavior:
    typo_rate: 1.5 # Vượt quá le=0.5
niches:
  - niche_id: "thoi_trang_nu"
    # Thiếu trường name và persona bắt buộc
""",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        load_config(str(broken_yaml))


# ==============================================================================
# 2. TONE VALIDATOR TESTS
# ==============================================================================

def test_tone_validator_valid_natural_koc():
    """Văn bản KOC đời thường chuẩn giọng người thật phải vượt qua kiểm tra."""
    fashion_sample = (
        "Chị em ơi, bà nào bụng dưới to bơi hết vào đây nha! "
        "Em váy chữ A này hack dáng đỉnh chóp luôn, mặc lên nhìn thon hẳn 5 phân. "
        "Bấm ngay góc trái nhận mã freeship nha các bà!"
    )
    assert ToneValidator.validate(fashion_sample) is True
    assert ToneValidator.check_violations(fashion_sample) == []
    assert ToneValidator.has_koc_markers(fashion_sample) is True

    homelife_sample = (
        "Các bác ơi, từ ngày tậu em máy này việc nhà nhàn hẳn luôn á. "
        "3 giây sạch bóng kin kít không tốn sức. "
        "Link tui để ở giỏ hàng góc trái nè!"
    )
    assert ToneValidator.validate(homelife_sample) is True
    assert ToneValidator.check_violations(homelife_sample) == []
    assert ToneValidator.has_koc_markers(homelife_sample) is True


def test_tone_validator_blocks_robotic_cliches():
    """Ngăn chặn các mẫu câu bot máy móc."""
    robotic_samples = [
        "Xin chào quý khách, tôi là trợ lý AI.",
        "Sản phẩm này rất tốt và tiện ích, đáp ứng mọi nhu cầu của bạn.",
        "Sự lựa chọn hoàn hảo cho mọi gia đình. Hãy nhanh tay sở hữu!",
        "Cảm ơn quý khách đã tin tưởng, chúc quý khách một ngày tốt lành.",
    ]
    for sample in robotic_samples:
        assert ToneValidator.validate(sample) is False
        violations = ToneValidator.check_violations(sample)
        assert any("ROBOTIC_CLICHE" in v for v in violations)


def test_tone_validator_blocks_counterfeit_trademarks():
    """Ngăn chặn từ khóa nhái thương hiệu lớn và tiếng lóng hàng giả."""
    counterfeit_samples = [
        ("Váy Zara thiết kế tôn dáng", "Zara"),
        ("Túi Chanel rep 1:1 bao nét", "Chanel"),
        ("Giày Gucci super fake chuẩn auth", "Gucci"),
        ("Áo thun Dior hàng tuồn vnxk", "Dior"),
        ("Ví nữ LV hàng rep đẹp mê", "LV"),
        ("Giày Nike rep 1 1 siêu cấp", "Nike"),
    ]
    for text, brand in counterfeit_samples:
        assert ToneValidator.validate(text) is False
        violations = ToneValidator.check_violations(text)
        assert any("COUNTERFEIT_KEYWORD" in v for v in violations), f"Failed for {text}"


def test_tone_validator_blocks_exaggerated_claims():
    """Ngăn chặn cam kết y tế và quảng cáo quá đà."""
    exaggerated_samples = [
        "Cam kết trị dứt điểm 100% mụn thâm sau 7 ngày",
        "Chảo chống dính vĩnh viễn không bám bẩn, 100% không bao giờ hỏng",
        "Sản phẩm tốt nhất thị trường số 1 việt nam",
        "Thần dược chữa khỏi hoàn toàn chứng mất ngủ",
    ]
    for sample in exaggerated_samples:
        assert ToneValidator.validate(sample) is False
        violations = ToneValidator.check_violations(sample)
        assert any("EXAGGERATED_CLAIM" in v for v in violations)


def test_tone_validator_word_boundaries_no_false_positives():
    """Kiểm tra từ biên (Word Boundaries) để không bắt nhầm các từ tiếng Việt hợp lệ."""
    valid_vietnamese_texts = [
        "Lực lượng lao động trẻ trung",      # Không bắt nhầm 'lv'
        "Lưu ý khi giặt váy lụa",            # Không bắt nhầm 'lv'
        "Quản lý việc nhà nhàn tênh",        # Không bắt nhầm 'lv'
        "Uống một ly trà sữa mát lạnh",      # Không bắt nhầm 'lv'
        "Quần áo thời trang phong cách",    # Không bắt nhầm 'rep' hay 'f1'
    ]
    for text in valid_vietnamese_texts:
        violations = ToneValidator.check_violations(text)
        assert violations == [], f"False positive in: '{text}', violations: {violations}"
        assert ToneValidator.validate(text) is True
