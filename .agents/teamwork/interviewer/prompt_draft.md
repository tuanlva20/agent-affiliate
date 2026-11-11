Thực thi toàn diện kế hoạch triển khai hệ thống tự động hóa TikTok Affiliate đa Agent (AMAS v1.4.0) cho hai ngách thí điểm: Thời trang nữ và Đồ gia dụng thông minh, tuân thủ TDD và checklist từng task trong file plan.

Working directory: /Users/tuanlva/Folder/workSpace/affiliate
Integrity mode: development

Tài liệu tham chiếu:
- Plan file: `/Users/tuanlva/Folder/workSpace/affiliate/docs/superpowers/plans/2026-11-10-autonomous-affiliate-system.md`
- System Spec: `/Users/tuanlva/Folder/workSpace/affiliate/SYSTEM_SPEC.md`

## Requirements

### R1. Base Scout & Specialist Scout Agents cho 2 ngách thí điểm
Triển khai dịch vụ trinh sát sản phẩm và xu hướng (Kalodata client & TikTok scraper) cùng 2 Agent chuyên gia: `FashionScoutAgent` (Thời trang nữ) và `HomeLifeScoutAgent` (Đồ gia dụng thông minh) để tìm kiếm sản phẩm tiềm năng, đánh giá tiêu chí chuyên ngành và lọc bỏ vi phạm chính sách/hàng nhái.

### R2. Video Remix Studio & Kịch bản KOC Tự Nhiên
Xây dựng pipeline sản xuất và remix video tự động gồm: bóc tách âm thanh (Whisper), lồng tiếng tiếng Việt tự nhiên (`edge-tts`), xử lý video lách quét bản quyền (`FFmpeg`), và sinh kịch bản tối ưu chuyển đổi theo công thức Hook 3s với văn phong KOC tự nhiên đời thường, cấm tuyệt đối giọng văn máy móc hoặc mùi bot.

### R3. Smart Publisher & Human Behavioral Biometrics Engine
Triển khai Agent xuất bản kết nối AliasMode (qua Local API / CDP) với engine mô phỏng sinh trắc học người thật (`human_behavior.py`): cuộn trang quán tính có gia tốc, gõ phím biến thiên 80–220ms với micro-pauses 0.6–1.4s và tỷ lệ typo 3% có sửa lại bằng Backspace, quy trình warm-up lướt feed 3–5 phút trước khi đăng, và cơ chế dừng ngay lập tức kèm còi báo động khẩn cấp về Telegram khi gặp Captcha.

### R4. Quản lý Cơ sở Dữ liệu & Trạng thái Vòng đời Kênh
Thiết lập PostgreSQL (SQLAlchemy 2.0 Async + asyncpg + JSONB) và Redis Queue kết nối theo cấu hình `.env`. Triển khai các models và quản lý trạng thái vòng đời kênh TikTok: `warming`, `ready_to_post`, `cooldown`, `captcha_blocked`.

### R5. Telegram Bot Command Center & Phê Duyệt 1 Chạm
Xây dựng giao diện điều phối Telegram Bot (`aiogram` 3.x) hỗ trợ phân luồng Topics (`#thoi-trang-nu`, `#do-gia-dung`, `#dashboard-tong`), phím inline duyệt 1 chạm (Human-in-the-Loop), và các lệnh điều khiển kiểm thử (`/test_scout`, `/test_video`, `/test_reply`, `/create_channel`, `/warmup`).

### R6. Comment Engagement & Conversion Agent
Xây dựng Agent tự động quét và phân loại ý định bình luận của người xem, sinh câu trả lời tư vấn chuẩn Persona KOC để kích thích chốt đơn và điều hướng người mua vào giỏ hàng vàng.

### R7. Hermes Orchestrator & E2E Integration
Tích hợp toàn bộ các Agent qua State Graph điều phối (Hermes Orchestrator) và file thực thi `main.py` CLI runner để chạy kiểm thử luồng E2E dry-run.

### R8. Quy trình TDD & Kiểm thử Toàn diện
Thực thi lần lượt theo đúng checklist 8 tasks trong file plan, tuân thủ nghiêm ngặt chu trình TDD (viết test -> chạy test FAIL -> cài đặt mã nguồn -> chạy test PASS -> commit). Tạo đầy đủ mock fixtures và dữ liệu mẫu đại diện cho 2 ngách để đảm bảo toàn bộ test suite chạy thành công 100%.

## Acceptance Criteria

### Task 1: Scaffolding, Cấu hình & Database Schema
- [ ] File `.env.example`, `config.yaml` và `scripts/get_telegram_ids.py` được tạo đầy đủ.
- [ ] Models SQLAlchemy 2.0 async (`Niche`, `Channel`, `Competitor`, `Product`, `VideoJob`, `VideoComment`, `Metric`) được định nghĩa đúng schema với JSONB.
- [ ] `ToneValidator` kiểm tra và chặn được các mẫu câu rập khuôn AI.
- [ ] `pytest tests/test_config.py tests/test_database.py` chạy PASS 100%.

### Task 2: Base Scout & Scraper Service
- [ ] `KalodataClient` và `TikTokScraper` trích xuất được sản phẩm và metadata video.
- [ ] `BaseScoutAgent` lọc sản phẩm theo ngưỡng giá và hoa hồng.
- [ ] `pytest tests/test_kalodata_client.py tests/test_tiktok_scraper.py` chạy PASS 100%.

### Task 3: Specialist Scout Agents (Fashion & HomeLife)
- [ ] `FashionScoutAgent` đánh giá tiêu chí thời trang và lọc bỏ từ khóa hàng nhái.
- [ ] `HomeLifeScoutAgent` đánh giá tiêu chí gia dụng và Before/After.
- [ ] `pytest tests/test_specialist_scouts.py` chạy PASS 100%.

### Task 4: Telegram Command Center & Phê duyệt 1 chạm
- [ ] Bot gửi card sản phẩm kèm inline keyboard duyệt/từ chối vào đúng topic tương ứng.
- [ ] Xử lý callback query cập nhật trạng thái job vào database/queue.
- [ ] Các lệnh `/test_scout`, `/test_video`, `/test_reply`, `/create_channel`, `/warmup` phản hồi đúng logic.
- [ ] `pytest tests/test_telegram_bot.py` chạy PASS 100%.

### Task 5: Video Remix & Content Engine
- [ ] `script_generator.py` sinh kịch bản chuẩn giọng KOC tự nhiên có Hook và CTA giỏ hàng.
- [ ] `tts_service.py` sinh file âm thanh tiếng Việt tự nhiên qua `edge-tts`.
- [ ] `video_processor.py` ghép audio, áp dụng biến đổi lách bản quyền qua FFmpeg.
- [ ] `pytest tests/test_script_generator.py tests/test_tts_service.py tests/test_video_processor.py` chạy PASS 100%.

### Task 6: Human Behavioral Biometrics Engine & Smart Publisher
- [ ] `BrowserAdapter` tạo và quản lý profile AliasMode qua Local API/CDP.
- [ ] `HumanBehaviorService` thực hiện cuộn chuột quán tính, gõ phím biến thiên 80-220ms kèm micro-pauses và sửa lỗi typo 3%.
- [ ] Kịch bản `warmup_feed_session` lướt feed ngẫu nhiên đúng thời gian quy định.
- [ ] `detect_and_handle_captcha` phát hiện Captcha, chụp màn hình và kích hoạt còi cảnh báo về Telegram, dừng thao tác của bot.
- [ ] `pytest tests/test_browser_adapter.py tests/test_human_behavior.py tests/test_smart_publisher.py` chạy PASS 100%.

### Task 7: Comment Engagement Agent
- [ ] Phân loại chính xác ý định bình luận (hỏi giá, hỏi chất liệu/cách dùng, khiếu nại).
- [ ] Sinh câu trả lời tự nhiên chuẩn Persona KOC kèm điều hướng giỏ hàng.
- [ ] `pytest tests/test_comment_agent.py` chạy PASS 100%.

### Task 8: Hermes Orchestrator & E2E Dry-run
- [ ] Luồng điều phối LangGraph kết nối các agent và trạng thái thành công.
- [ ] File `main.py` CLI runner khởi chạy đầy đủ dịch vụ bot và scheduler.
- [ ] File `README.md` hướng dẫn cấu hình `.env` và vận hành hệ thống.
- [ ] Toàn bộ test suite `pytest tests/ -v` đạt 100% PASS không lỗi.
