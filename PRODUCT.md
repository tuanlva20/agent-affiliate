# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Next.js / React + Tailwind CSS (kết nối FastAPI Backend qua REST API & Server-Sent Events SSE).

## Users

Người làm TikTok Shop Affiliate, Solo Creator, và các đội ngũ vận hành nội dung đa kênh (TikTok Shop / Facebook Reels). Họ cần sản xuất video hàng ngày với số lượng lớn, theo dõi đối thủ, nuôi dàn tài khoản an toàn và trả lời bình luận để tối đa hóa tỷ lệ chuyển đổi ra đơn hàng.

## Product Purpose

Hệ thống AMAS (Autonomous Multi-Agent TikTok Affiliate System) Web UI cung cấp giao diện quản trị và studio tự động hóa khép kín:
1. **Motion Control Studio:** Tự động tạo video KOC affiliate từ video đối thủ và ảnh nhân vật/sản phẩm (bóc tách 4 khúc, Replicate Motion Control, và Hybrid Face Swap siêu tiết kiệm).
2. **Quản lý Tài khoản & Proxy:** Theo dõi vòng đời nuôi nick đa kênh (warming, ready, cooldown, captcha_blocked), kho proxy tập trung và cơ chế duyệt Captcha khẩn cấp.
3. **Trung tâm Dữ liệu & Lịch sử:** Tra cứu lịch sử đăng, snapshot doanh thu/đơn hàng, lịch sử comment & trả lời tự động của bot KOC, và kho video cào từ kênh đối thủ.

Thành công của sản phẩm là giúp một nhà sáng tạo hoặc đội ngũ nhỏ có thể vận hành hàng chục tài khoản affiliate tự động với chi phí sản xuất video thấp nhất và tỷ lệ chuyển đổi cao nhất.

## Positioning

Hệ thống affiliate duy nhất kết hợp giữa **Kiến trúc Motion Control chuẩn SaaS (như Kling AI)** và **Pipeline Hybrid Face Swap cục bộ siêu tiết kiệm (≤ 1.000đ/video)**, bảo toàn 100% độ chân thật của video thật, lách triệt để thuật toán quét AI của nền tảng, gắn liền với cơ chế an toàn nuôi tài khoản (Anti-detect browser & Human biometrics).

## Operating Context

- Môi trường trình duyệt web máy tính (Desktop/Laptop), màn hình từ 1280px trở lên phục vụ công việc quản trị, dựng video và kiểm soát dàn tài khoản.
- Tích hợp chặt chẽ với:
  - Backend: FastAPI, PostgreSQL (SQLAlchemy 2.0 async), Redis.
  - Video Engines: Replicate API (`kwaivgi/kling-v3-motion-control`), Local Face Swap (`InsightFace / CodeFormer / LivePortrait`), FFmpeg (`VideoProcessor`), `edge-tts` (`TTSService`).
  - Browser Automation: AliasMode Anti-Detect Browser API / Playwright qua proxy riêng biệt cho từng kênh.

## Capabilities and Constraints

- **Capabilities:**
  - Tải video TikTok đối thủ không watermark, bóc tách timeline 4 khúc (Hook 3s, Vấn đề, Demo, CTA).
  - Ghép ảnh nhân vật + sản phẩm (Virtual Try-on) trước khi truyền pose chuyển động.
  - Hoán đổi mặt siêu thực (Auto Color Matching, Poisson Blending, CodeFormer, LivePortrait lip-sync tiếng Việt).
  - Quản lý kênh đa nền tảng (TikTok, Facebook), quản lý kho proxy (test live/dead).
  - Stream trạng thái render và thông số nuôi nick theo thời gian thực (SSE).
- **Constraints:**
  - Chi phí sản xuất video mục tiêu: ≤ 1.000 VNĐ / video (khi dùng luồng Hybrid Local Swap) và pay-per-use qua Replicate API khi cần Motion Control toàn thân.
  - An toàn tài khoản là ưu tiên tối thượng: Chặn đăng khi kênh đang ở trạng thái `warming`, `cooldown`, hoặc `captcha_blocked`.

## Brand Commitments

- Tên hệ thống: **AMAS v1.4.0** (Autonomous Multi-Agent TikTok Affiliate System).
- Tông giọng & Phong cách: Chuyên nghiệp, trực quan, đậm chất công cụ năng suất (productivity tool) cho creator/marketer, tập trung vào số liệu thực chiến (view, đơn hàng, trạng thái tài khoản) và tiến độ render.

## Evidence on Hand

- Hệ thống backend AMAS v1.4.0 hoàn chỉnh: Database models (`Channel`, `Product`, `VideoJob`, `VideoComment`, `Metric`, `Competitor`), các agents (`VideoStudioAgent`, `SmartPublisher`, `CommentAgent`), các services (`VideoDownloader`, `AudioTranscriber`, `VideoProcessor`, `TTSService`, `BrowserAdapter`, `HumanBehaviorService`).
- Bộ test suite 492 tests đang hoạt động và cấu hình Docker Compose (PostgreSQL, Redis).

## Product Principles

1. **Hiệu quả kinh tế trên hết:** Mọi tính năng render phải ưu tiên giảm thiểu chi phí API cho người dùng, tối đa hóa biên lợi nhuận affiliate.
2. **Minh bạch tiến độ & Trực quan:** Video render qua AI và quy trình nuôi nick tốn thời gian; giao diện phải luôn phản hồi trạng thái rõ ràng qua progress bar / SSE thời gian thực.
3. **An toàn tài khoản trước tốc độ:** Không bao giờ cho phép người dùng hay bot đăng bài vô tội vạ vi phạm giới hạn giãn cách (`cooldown`) hoặc khi tài khoản chưa đủ ngày nuôi (`warming`).
4. **Luồng thao tác mượt mà (Zero Friction):** Từ một link video đối thủ cào được, chỉ cần 1 click là chuyển thẳng sang Studio để tạo video mới và 1 click để đẩy sang kênh đích.
