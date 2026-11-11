"""AMAS v1.4.0 — Empirical Challenger Adversarial Stress Suite.

Designed by m1_challenger_reverify to stress-test:
1. ToneValidator boundary evasions, diacritics, whitespace variations, and false-positive traps.
2. Concurrent transaction safety with interleaved rollbacks and commits.
3. Nested JSON array/object mutation persistence.
4. Channel lifecycle state validation under invalid ORM mutations.
5. Config loader edge cases with missing or malformed inputs.
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import yaml
from pathlib import Path
from typing import List, Tuple

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.tone_validator import ToneValidator
from src.core.config import AppConfig, load_config
from src.database.models import Base, Niche, Channel, Product, VideoJob
from src.database.session import get_async_engine, get_db


class AdversarialRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.failures: List[str] = []

    def check(self, name: str, condition: bool, details: str = ""):
        if condition:
            self.passed += 1
            print(f"  [PASS] {name}")
        else:
            self.failed += 1
            msg = f"  [FAIL] {name} - {details}"
            self.failures.append(msg)
            print(msg)


async def run_tone_validator_challenges(runner: AdversarialRunner):
    print("\n=== CHALLENGE SUITE 1: ToneValidator Adversarial Attack Matrix ===")
    
    # 1. Punctuation and spacing evasion attacks on counterfeit keywords
    counterfeit_attacks = [
        ("rep   1:1 multi-space", "Váy hoa rep   1:1 đẹp", False),
        ("rep\t1:1 tab separated", "Đầm rep\t1:1 siêu xinh", False),
        ("rep\n1:1 newline separated", "Set rep\n1:1 cao cấp", False),
        ("rep 1 / 1 spaced slash", "Áo khoác rep 1 / 1", False),
        ("rep 1 . 1 spaced dot", "Áo thun rep 1 . 1", False),
        ("rep1:1 no space", "Túi xách rep1:1 chuẩn", False),
        ("super   fake multi-space", "Túi super   fake chất da xịn", False),
        ("super_fake underscore", "Ví super_fake chuẩn nét", False),
        ("like_auth underscore", "Giày like_auth sang chảnh", False),
        ("like - auth dash space", "Giày like - auth sang chảnh", False),
        ("chuẩn auth with dash", "Hàng chuẩn-auth cực xịn", False),
        ("tuồn auth with underscore", "Hàng tuồn_auth bao đẹp", False),
        ("HÀNG NHÁI uppercase", "Áo này là HÀNG NHÁI giá rẻ", False),
        ("áo fake standalone", "Áo fake form rộng unisex", False),
        ("quần fake standalone", "Quần fake ống suông", False),
        ("giày fake standalone", "Giày fake nhẹ êm chân", False),
        ("dép fake standalone", "Dép fake quai ngang", False),
        ("túi fake standalone", "Túi fake mini xinh xắn", False),
        ("ví fake standalone", "Ví fake cầm tay nam", False),
        ("đầm fake standalone", "Đầm fake dự tiệc", False),
        ("hàng fake standalone", "Hàng fake loại 1", False),
        ("hàng rep standalone", "Hàng rep giá sinh viên", False),
        ("hàng f1 standalone", "Hàng f1 chuẩn dáng", False),
        ("LV in parentheses", "Túi (LV) thời thượng", False),
        ("LV in square brackets", "Túi [LV] siêu hot", False),
        ("LV at sentence end with dot", "Chiếc túi này gắn logo LV.", False),
        ("LV surrounded by commas", "Túi thời trang, LV, mẫu 2026", False),
        ("Hermès with accent grave", "Khăn lụa Hermès sang xịn", False),
        ("GUCCI all caps", "Túi GUCCI da bò cao cấp", False),
        ("DiOr mixed case", "Nước hoa DiOr thơm lâu", False),
        ("Rolex watch", "Đồng hồ Rolex mạ vàng", False),
    ]

    for name, text, expected in counterfeit_attacks:
        valid = ToneValidator.validate(text)
        runner.check(name, valid == expected, f"Expected {expected}, got {valid}. Violations: {ToneValidator.check_violations(text)}")

    # 2. Robotic Clichés variations
    robotic_attacks = [
        ("Dạ em chào quý khách", "Dạ em chào quý khách đã ghé gian hàng ạ", False),
        ("Em xin kính chào quý khách", "Em xin kính chào quý khách", False),
        ("Chào mừng quý vị đến với", "Chào mừng quý vị đến với buổi livestream", False),
        ("Chào mừng mọi người đến với", "Chào mừng mọi người đến với kênh của em", False),
        ("Dưới đây là một số gợi ý", "Dưới đây là một số gợi ý phối đồ cực xinh", False),
        ("Sau đây là danh sách", "Sau đây là danh sách 5 món đồ không thể thiếu", False),
        ("Tôi là một trợ lý ảo", "Tôi là một trợ lý ảo của thương hiệu", False),
        ("Tôi là trợ lý thông minh", "Tôi là trợ lý thông minh hỗ trợ giải đáp", False),
        ("Như một mô hình ngôn ngữ", "Như một mô hình ngôn ngữ lớn, tôi khuyên bạn...", False),
        ("Hy vọng thông tin này hữu ích", "Hy vọng thông tin này hữu ích với bạn nhé", False),
        ("Hy vọng hữu ích cho bạn", "Hy vọng hữu ích cho bạn trong việc lựa chọn", False),
        ("Sản phẩm rất tuyệt vời", "Sản phẩm rất tuyệt vời và đáng đồng tiền", False),
        ("Sự lựa chọn hoàn hảo", "Đây là sự lựa chọn hoàn hảo cho mùa đông", False),
        ("Giải pháp hoàn hảo", "Giải pháp hoàn hảo giúp nhà tắm luôn sạch", False),
        ("Hãy nhanh tay sở hữu", "Hãy nhanh tay sở hữu trước khi hết hàng", False),
        ("Sở hữu ngay hôm nay", "Sở hữu ngay hôm nay để nhận voucher giảm giá", False),
        ("Cảm ơn quý khách đã tin tưởng", "Cảm ơn quý khách đã tin tưởng dịch vụ bên em", False),
        ("Chúc quý khách một ngày tốt lành", "Chúc quý khách một ngày tốt lành nha mọi người", False),
    ]

    for name, text, expected in robotic_attacks:
        valid = ToneValidator.validate(text)
        runner.check(name, valid == expected, f"Expected {expected}, got {valid}. Violations: {ToneValidator.check_violations(text)}")

    # 3. False-Positive Immunity Checks (Vietnamese natural text MUST PASS)
    immunity_checks = [
        ("Món nhái chiên giòn rụm", "Hôm nay mẹ làm món nhái chiên giòn rụm ăn mê luôn", True),
        ("Thịt nhái bổ dưỡng", "Cháo nấu với thịt nhái thơm ngon bổ dưỡng cho bé", True),
        ("Vải crepe cao cấp", "Váy thiết kế may bằng chất vải crepe mềm mịn mát rượi", True),
        ("Rep tin nhắn em nha", "Chị ơi nhớ rep tin nhắn em check size đầm nha", True),
        ("Rep inbox shop ơi", "Shop rep inbox em gửi địa chỉ nhận hàng liền nhé", True),
        ("Rep cmt của em với", "Mấy bà rep cmt của em để em tư vấn màu phù hợp nha", True),
        ("Kênh channel youtube", "Video này được cắt từ kênh channel ẩm thực dân dã", True),
        ("Lực lượng công nhân", "Lực lượng lao động tay nghề cao tại nhà máy dệt", True),
        ("Lưu ý bảo quản", "Lưu ý khi giặt không nên dùng chất tẩy mạnh", True),
        ("Ly nước giữ nhiệt", "Ly nước giữ nhiệt inox 304 giữ ấm suốt 12 tiếng", True),
        ("Quản lý chi tiêu", "Chiếc ví nhỏ giúp quản lý chi tiêu cá nhân hiệu quả", True),
        ("Review chân thật", "Review chân thật không quảng cáo cho chị em", True),
    ]

    for name, text, expected in immunity_checks:
        valid = ToneValidator.validate(text)
        violations = ToneValidator.check_violations(text)
        runner.check(name, valid == expected, f"False positive triggered! Violations: {violations}")

    # 4. Exaggerated claims checks
    exaggerated_attacks = [
        ("trị dứt điểm 100%", "Kem bôi cam kết trị dứt điểm 100% tàn nhang", False),
        ("vĩnh viễn không rỉ sét", "Kệ để bát vĩnh viễn không rỉ sét trọn đời", False),
        ("thần dược trị nám", "Serum được mệnh danh thần dược tái sinh làn da", False),
        ("thuốc trị dứt điểm", "Thuốc trị xương khớp công hiệu ngay lần đầu", False),
        ("100% không bao giờ hỏng", "Chảo gang 100% không bao giờ hỏng qua năm tháng", False),
    ]

    for name, text, expected in exaggerated_attacks:
        valid = ToneValidator.validate(text)
        runner.check(name, valid == expected, f"Expected {expected}, got {valid}")

    # 5. KOC Markers check
    koc_positive = [
        ("KOC marker: mấy bà ơi + hack dáng", "Mấy bà ơi chân váy này hack dáng đỉnh chóp luôn á"),
        ("KOC marker: giỏ hàng góc trái", "Bấm ngay góc trái màn hình để săn voucher nha chị em ơi"),
        ("KOC marker: nhàn tênh", "Dùng cây lau nhà này xong thấy việc nhà nhàn tênh"),
    ]
    for name, text in koc_positive:
        has_koc = ToneValidator.has_koc_markers(text)
        runner.check(name, has_koc is True, f"KOC marker not detected in: {text}")


async def run_database_concurrency_and_acid_challenges(runner: AdversarialRunner):
    print("\n=== CHALLENGE SUITE 2: Database ACID & Concurrency Under Adversarial Conditions ===")
    
    engine = get_async_engine(force_new=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Seed initial niche
    async with get_db() as db:
        db.add(Niche(niche_id="niche_adv_test", name="Adversarial Test Niche"))

    # Challenge 2.1: Interleaved commits and rollbacks across 20 coroutines
    # Half of the coroutines succeed, half intentionally abort with an exception.
    async def committing_worker(idx: int):
        async with get_db() as db:
            prod = Product(
                product_id=f"prod_commit_{idx:02d}",
                niche_id="niche_adv_test",
                title=f"Valid Committed Product {idx}",
                price=50.0 + idx,
                product_url=f"http://test.com/commit/{idx}",
                status="approved",
            )
            db.add(prod)

    async def aborting_worker(idx: int):
        try:
            async with get_db() as db:
                prod = Product(
                    product_id=f"prod_abort_{idx:02d}",
                    niche_id="niche_adv_test",
                    title=f"Aborting Product {idx}",
                    price=999.0,
                    product_url=f"http://test.com/abort/{idx}",
                    status="rejected",
                )
                db.add(prod)
                await db.flush()
                # Intentionally raise to force rollback
                raise RuntimeError(f"Simulated crash in worker {idx}")
        except RuntimeError:
            pass

    tasks = []
    for i in range(10):
        tasks.append(committing_worker(i))
        tasks.append(aborting_worker(i))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    exceptions = [r for r in results if isinstance(r, Exception)]
    runner.check("Interleaved 20 coroutines executed with zero unhandled exceptions", len(exceptions) == 0, f"Exceptions: {exceptions}")

    # Verify that exactly the 10 committing products exist, and ZERO aborting products exist
    async with get_db() as db:
        for i in range(10):
            p_comm = await db.get(Product, f"prod_commit_{i:02d}")
            p_abort = await db.get(Product, f"prod_abort_{i:02d}")
            runner.check(f"Committed worker {i} persisted cleanly", p_comm is not None, "Product missing")
            runner.check(f"Aborting worker {i} was properly rolled back", p_abort is None, "Aborted product was leaked into DB!")

    # Challenge 2.2: In-place JSON Top-Level Mutation (tracked by MutableDict)
    async with get_db() as db:
        prod = Product(
            product_id="prod_json_mut_top",
            niche_id="niche_adv_test",
            title="JSON Mutation Target",
            price=120.0,
            product_url="http://test.com/json_mut",
            evaluation_data={
                "score": 7.5,
                "passed_filter": False,
                "metrics": {"ctr": 0.05, "conversion": 0.02},
                "tags": ["initial", "unprocessed"],
            },
        )
        db.add(prod)

    # In-place top-level modifications tracked by MutableDict
    async with get_db() as db:
        p = await db.get(Product, "prod_json_mut_top")
        assert p is not None
        p.evaluation_data["score"] = 9.5
        p.evaluation_data["passed_filter"] = True
        p.evaluation_data["status_note"] = "approved_by_critic"

    # Clean reload and assert persistence of in-place modifications
    async with get_db() as db:
        reloaded = await db.get(Product, "prod_json_mut_top")
        assert reloaded is not None
        runner.check("In-place top-level score mutation persisted", reloaded.evaluation_data["score"] == 9.5)
        runner.check("In-place top-level boolean mutation persisted", reloaded.evaluation_data["passed_filter"] is True)
        runner.check("In-place new key assignment persisted", reloaded.evaluation_data.get("status_note") == "approved_by_critic")

    # Challenge 2.3: Channel Lifecycle Invalid State Rejection
    async with get_db() as db:
        valid_chan = Channel(
            channel_id="chan_valid_01",
            niche_id="niche_adv_test",
            browser_profile_id="prof_valid_01",
            lifecycle_status="ready_to_post",
        )
        db.add(valid_chan)

    async with get_db() as db:
        saved_chan = await db.get(Channel, "chan_valid_01")
        assert saved_chan is not None
        # Attempt to set unauthorized lifecycle status via ORM attribute assignment
        caught = False
        try:
            saved_chan.lifecycle_status = "unauthorized_status"
        except ValueError:
            caught = True
        runner.check("Channel model rejects invalid lifecycle status via @validates", caught is True)


def run_config_edge_cases(runner: AdversarialRunner):
    print("\n=== CHALLENGE SUITE 3: Config Loader Edge Cases & Crash Resilience ===")
    
    # Challenge 3.1: Config with extra unexpected fields
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        f.write("""
app_name: "AMAS_CUSTOM"
unknown_future_field_1: 12345
unknown_future_field_2:
  nested_surprise: "hello"
niches:
  - niche_id: "test_niche"
    name: "Test Niche"
    persona:
      role: "Expert"
      tone: "Casual"
    thresholds:
      min_price: 10000
""")
        temp_path = f.name

    try:
        cfg = load_config(temp_path)
        runner.check("Config loads cleanly ignoring unknown extra fields", cfg.app_name == "AMAS_CUSTOM")
        runner.check("Niche thresholds mapped correctly", cfg.niches[0].thresholds.min_price == 10000.0)
    finally:
        os.unlink(temp_path)

    # Challenge 3.2: Empty sections with environment variables
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        f.write("""
database:
redis:
telegram:
niches:
  - niche_id: "niche_empty_sec"
    name: "Empty Sec"
    persona:
      role: "Reviewer"
      tone: "Natural"
""")
        temp_path = f.name

    try:
        os.environ["POSTGRES_URL"] = "postgresql+asyncpg://override_user:pass@remote:5432/live_db"
        os.environ["REDIS_URL"] = "redis://cache.redis.local:6379/2"
        os.environ["ADMIN_TELEGRAM_ID"] = "99887766"
        cfg = load_config(temp_path)
        runner.check("POSTGRES_URL env override populated into empty database section", cfg.database.url == "postgresql+asyncpg://override_user:pass@remote:5432/live_db")
        runner.check("REDIS_URL env override populated into empty redis section", cfg.redis.url == "redis://cache.redis.local:6379/2")
        runner.check("ADMIN_TELEGRAM_ID env override converted to integer", cfg.telegram.admin_id == 99887766)
    finally:
        os.environ.pop("POSTGRES_URL", None)
        os.environ.pop("REDIS_URL", None)
        os.environ.pop("ADMIN_TELEGRAM_ID", None)
        os.unlink(temp_path)


async def main():
    runner = AdversarialRunner()
    await run_tone_validator_challenges(runner)
    await run_database_concurrency_and_acid_challenges(runner)
    run_config_edge_cases(runner)

    print("\n" + "=" * 60)
    print(f"ADVERSARIAL CHALLENGER SUITE SUMMARY:")
    print(f"Total Challenges Run: {runner.passed + runner.failed}")
    print(f"Passed:               {runner.passed}")
    print(f"Failed:               {runner.failed}")
    print("=" * 60)

    if runner.failed > 0:
        print("\nFAILURES IDENTIFIED:")
        for f in runner.failures:
            print(f)
        sys.exit(1)
    else:
        print("\nALL ADVERSARIAL CHALLENGES EMPIRICALLY CONFIRMED PASSING!")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
