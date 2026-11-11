"""Unit tests for Natural KOC Script Generator Service (Feature F15)."""

import pytest
from unittest.mock import MagicMock
from src.core.tone_validator import ToneValidator
from src.services.script_generator import KOCScriptResult, ScriptGenerator


@pytest.fixture
def sample_fashion_meta():
    return {
        "product_id": "fash_101",
        "niche_id": "thoi_trang_nu",
        "title": "Váy hoa nhí dáng xòe chiết eo hack dáng tôn da",
        "price": 189000.0,
        "commission_rate": 0.15,
        "rating": 4.85,
        "sales_count": 1250,
    }


@pytest.fixture
def sample_homelife_meta():
    return {
        "product_id": "home_202",
        "niche_id": "do_gia_dung",
        "title": "Cây lau nhà tự vắt xoay 360 độ thông minh",
        "price": 149000.0,
        "commission_rate": 0.18,
        "rating": 4.90,
        "sales_count": 3400,
    }


class TestScriptGeneratorContract:
    """Verifies interface contract with Tier 1 and VideoStudioAgent."""

    def test_contract_keys_and_indexing(self, sample_fashion_meta):
        gen = ScriptGenerator()
        script = gen.generate_script(sample_fashion_meta, {"tone": "koc"})

        # Required contract keys
        assert "hook_3s" in script
        assert "body" in script
        assert "cta_yellow_cart" in script
        assert "caption" in script
        assert "full_voiceover" in script

        # Dict subscripting
        assert isinstance(script["hook_3s"], str)
        assert isinstance(script["body"], str)
        assert isinstance(script["cta_yellow_cart"], str)
        assert isinstance(script["caption"], str)
        assert isinstance(script["full_voiceover"], str)

        # Content non-empty
        assert len(script["hook_3s"].strip()) > 0
        assert len(script["body"].strip()) > 0
        assert len(script["cta_yellow_cart"].strip()) > 0
        assert len(script["full_voiceover"].strip()) > 0

    def test_tone_validator_zero_robotic_cliches(self, sample_fashion_meta):
        gen = ScriptGenerator()
        script = gen.generate_script(sample_fashion_meta, {"tone": "koc"})
        assert ToneValidator.validate(script["full_voiceover"]) is True

    def test_tone_validator_has_koc_markers(self, sample_fashion_meta):
        gen = ScriptGenerator()
        script = gen.generate_script(sample_fashion_meta, {"tone": "koc"})
        assert ToneValidator.has_koc_markers(script["full_voiceover"]) is True


class TestPersonaResolution:
    """Verifies persona assignment for Fashion (Hoài My) and HomeLife (Nam Minh)."""

    def test_fashion_persona_hoai_my(self, sample_fashion_meta):
        gen = ScriptGenerator()
        script = gen.generate_script(sample_fashion_meta, "hoai_my")
        assert script["persona"] == "hoai_my"
        assert script["voice_id"] == "vi-VN-HoaiMyNeural"

        # Check KOC tone & body-hack keywords
        full_text = script["full_voiceover"].lower()
        assert any(w in full_text for w in ["chị em", "mấy bà", "tui", "bà nào"])
        assert any(w in full_text for w in ["eo", "bụng", "dáng", "hack dáng", "che khuyết điểm"])

    def test_homelife_persona_nam_minh(self, sample_homelife_meta):
        gen = ScriptGenerator()
        script = gen.generate_script(sample_homelife_meta, "nam_minh")
        assert script["persona"] == "nam_minh"
        assert script["voice_id"] == "vi-VN-NamMinhNeural"

        # Check labor-saving keywords
        full_text = script["full_voiceover"].lower()
        assert any(w in full_text for w in ["các bác", "tui", "bà nào", "mấy bà"])
        assert any(w in full_text for w in ["3s", "3 giây", "nhàn", "nhàn tênh", "nhàn hẳn", "tiện"])

    def test_auto_infer_persona_by_niche_id(self, sample_fashion_meta, sample_homelife_meta):
        gen = ScriptGenerator()
        script_f = gen.generate_script(sample_fashion_meta, persona=None)
        assert script_f["persona"] == "hoai_my"
        assert script_f["voice_id"] == "vi-VN-HoaiMyNeural"

        script_h = gen.generate_script(sample_homelife_meta, persona=None)
        assert script_h["persona"] == "nam_minh"
        assert script_h["voice_id"] == "vi-VN-NamMinhNeural"

    def test_auto_infer_persona_by_title_keywords(self):
        gen = ScriptGenerator()
        # No niche_id provided
        prod_fashion = {"title": "Chân váy chữ A cạp cao giấu bụng"}
        script_f = gen.generate_script(prod_fashion, persona={})
        assert script_f["persona"] == "hoai_my"

        prod_home = {"title": "Bộ dao thớt đa năng kháng khuẩn thông minh"}
        script_h = gen.generate_script(prod_home, persona={})
        assert script_h["persona"] == "nam_minh"


class TestHookAndCTARules:
    """Verifies 3-stage formula: Hook 3s, Core Body, Yellow Cart CTA."""

    def test_hook_3s_fashion_body_hack(self, sample_fashion_meta):
        gen = ScriptGenerator()
        script = gen.generate_script(sample_fashion_meta, "hoai_my")
        hook = script["hook_3s"].lower()
        assert any(w in hook for w in ["eo", "bụng", "dáng", "hack dáng", "chân ngắn", "khuyết điểm"])
        assert any(w in hook for w in ["chị em", "mấy bà", "team"])

    def test_hook_3s_homelife_labor_saving(self, sample_homelife_meta):
        gen = ScriptGenerator()
        script = gen.generate_script(sample_homelife_meta, "nam_minh")
        hook = script["hook_3s"].lower()
        assert any(w in hook for w in ["3s", "3 giây", "nhàn", "nhàn tênh", "nhàn hẳn"])

    def test_cta_yellow_cart_navigation(self, sample_fashion_meta, sample_homelife_meta):
        gen = ScriptGenerator()
        for meta, pers in [(sample_fashion_meta, "hoai_my"), (sample_homelife_meta, "nam_minh")]:
            script = gen.generate_script(meta, pers)
            cta = script["cta_yellow_cart"].lower()
            assert any(
                phrase in cta
                for phrase in [
                    "giỏ hàng góc trái",
                    "góc trái màn hình",
                    "giỏ hàng vàng",
                    "mã freeship",
                    "săn voucher",
                    "bấm ngay góc trái",
                ]
            )

    def test_caption_contains_hashtags(self, sample_fashion_meta, sample_homelife_meta):
        gen = ScriptGenerator()
        script_f = gen.generate_script(sample_fashion_meta, "hoai_my")
        assert "#" in script_f["caption"]
        assert "fashion" in script_f["caption"] or "thoitrang" in script_f["caption"]

        script_h = gen.generate_script(sample_homelife_meta, "nam_minh")
        assert "#" in script_h["caption"]
        assert "giadung" in script_h["caption"] or "dogiadung" in script_h["caption"]


class TestSanitizationAndResilience:
    """Verifies counterfeit removal, exaggerated claims cleansing, and edge cases."""

    def test_dirty_counterfeit_title_sanitization(self):
        gen = ScriptGenerator()
        dirty_meta = {
            "product_id": "fash_fake",
            "niche_id": "thoi_trang_nu",
            "title": "Váy Zara thiết kế rep 1:1 super fake hàng like auth",
            "price": 250000.0,
        }
        script = gen.generate_script(dirty_meta, "hoai_my")
        assert ToneValidator.validate(script["full_voiceover"]) is True
        for banned in ["zara", "rep 1:1", "super fake", "like auth"]:
            assert banned not in script["full_voiceover"].lower()

    def test_exaggerated_claims_sanitization(self):
        gen = ScriptGenerator()
        dirty_meta = {
            "product_id": "home_exag",
            "niche_id": "do_gia_dung",
            "title": "Chổi lau nhà trị dứt điểm 100% vĩnh viễn không bao giờ hỏng",
            "price": 199000.0,
        }
        script = gen.generate_script(dirty_meta, "nam_minh")
        assert ToneValidator.validate(script["full_voiceover"]) is True
        for banned in ["trị dứt điểm 100%", "vĩnh viễn không bao giờ hỏng"]:
            assert banned not in script["full_voiceover"].lower()

    def test_empty_or_none_product_meta(self):
        gen = ScriptGenerator()
        script_none = gen.generate_script(None, persona="hoai_my")
        assert ToneValidator.validate(script_none["full_voiceover"]) is True
        assert ToneValidator.has_koc_markers(script_none["full_voiceover"]) is True

        script_empty = gen.generate_script({}, persona="nam_minh")
        assert ToneValidator.validate(script_empty["full_voiceover"]) is True
        assert ToneValidator.has_koc_markers(script_empty["full_voiceover"]) is True

    def test_template_rotation_diversity(self):
        gen = ScriptGenerator()
        titles = [
            "Đầm xòe cổ trang trí nơ",
            "Quần suông ống rộng cạp cao",
            "Áo sơ mi lụa hàn quốc",
            "Set bộ mặc nhà thun tăm",
            "Váy đuôi cá thắt eo",
        ]
        results = [
            gen.generate_script({"title": t, "niche_id": "thoi_trang_nu"}, "hoai_my")["hook_3s"]
            for t in titles
        ]
        # At least 2 distinct hooks across 5 products
        assert len(set(results)) >= 2

    def test_duration_estimation_bounds(self, sample_fashion_meta):
        gen = ScriptGenerator()
        script = gen.generate_script(sample_fashion_meta, "hoai_my")
        dur = script["estimated_duration_sec"]
        assert 15.0 <= dur <= 60.0

    def test_mock_llm_integration_and_fallback(self, sample_fashion_meta):
        # 1. When LLM succeeds with valid JSON
        mock_llm = MagicMock()
        mock_llm.generate.return_value = (
            '{"hook_3s": "Chị em ơi, nhìn ngay em này hack dáng đỉnh chóp!", '
            '"body": "Chất mát, form tôn dáng giấu mỡ cực xinh.", '
            '"cta_yellow_cart": "Bấm ngay giỏ hàng góc trái săn voucher nha!", '
            '"caption": "Váy xinh #fashion #xuhuong"}'
        )
        gen = ScriptGenerator(llm_client=mock_llm)
        script = gen.generate_script(sample_fashion_meta, "hoai_my")
        assert script["generation_mode"] == "llm"
        assert ToneValidator.validate(script["full_voiceover"]) is True

        # 2. When LLM returns robotic cliché -> fallback to clean template
        mock_llm.generate.return_value = (
            '{"hook_3s": "Kính chào quý khách!", '
            '"body": "Đây là giải pháp hoàn hảo đáp ứng mọi nhu cầu.", '
            '"cta_yellow_cart": "Hãy nhanh tay sở hữu ngay hôm nay!", '
            '"caption": "Sản phẩm tốt"}'
        )
        script_fallback = gen.generate_script(sample_fashion_meta, "hoai_my")
        # ToneValidator must still be True due to automatic fallback gate!
        assert ToneValidator.validate(script_fallback["full_voiceover"]) is True
        assert "kính chào quý khách" not in script_fallback["full_voiceover"].lower()
