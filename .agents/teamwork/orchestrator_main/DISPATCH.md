# Dispatch Messages

## 2026-11-10T07:04:25Z
From: 13bdcc25-55d9-4738-b447-de9f536073e9
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
