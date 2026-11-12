# AGENTS.md — Hướng Dẫn Phối Hợp UI/UX: Impeccable + UI-UX-Pro-Max

> Tài liệu này thiết lập quy trình phối hợp tiêu chuẩn giữa hai kỹ năng **Impeccable** và **UI-UX-Pro-Max** dành cho các AI Agent khi phát triển giao diện Web UI (Next.js/React + Tailwind CSS) cho hệ thống **AMAS v1.4.0**.

---

## 1. Phân Vai & Trách Nhiệm (Division of Roles)

Để tránh chồng chéo hoặc mâu thuẫn, hai công cụ đảm nhiệm hai nửa của quy trình thiết kế:

```
┌────────────────────────────────────────────────────────────────────────┐
│ 1. ĐỊNH HƯỚNG & NỀN TẢNG THIẾT KẾ: UI-UX-PRO-MAX                       │
│    - Tra cứu dữ liệu thiết kế: Style, Palette, Font Pairing, Tokens.   │
│    - Nguyên tắc UX tương tác, Data Viz, Mobile responsive checklist.   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ (Cung cấp Token & Design System)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 2. KIỂM SOÁT BẢN SẮC & CHẤT LƯỢNG SẢN PHẨM: IMPECCABLE                │
│    - Giữ vững Product Truth trong PRODUCT.md và DESIGN.md.             │
│    - Thực thi Craft Floor (Chống lỗi cẩu thả, typography hierarchy).   │
│    - Chạy bộ kiểm tra cơ học: `impeccable detect` trước khi bàn giao. │
└────────────────────────────────────────────────────────────────────────┘
```

| Tiêu chí | **UI-UX-Pro-Max** | **Impeccable** |
| :--- | :--- | :--- |
| **Vai trò chính** | **Kiến trúc sư Design System & Kho tri thức UI** | **Giám đốc Thiết kế (Design Director) & Chất lượng Code** |
| **Thời điểm kích hoạt** | Bắt đầu dựng màn hình mới, chọn màu/font, xử lý responsive/a11y | Lập PRODUCT.md/DESIGN.md, review bản sắc, và pass kiểm thử cuối |
| **Công cụ cốt lõi** | `search.py` (79 styles, 192 palettes, 74 font pairings) | `impeccable context`, `impeccable detect`, Craft Floor |

---

## 2. Quy Trình 4 Bước Phối Hợp Chuẩn (Standard 4-Step Workflow)

Khi triển khai bất kỳ màn hình hoặc component nào (ví dụ: *Tab 1 Motion Control Studio*, *Tab 2 Quản lý Kênh*, *Tab 3 Lịch sử*), Agent bắt buộc tuân thủ 4 bước:

### Bước 1: Khởi Động Ngữ Cảnh Sản Phẩm (Impeccable Context)
* Chạy kiểm tra bối cảnh dự án:
  ```bash
  /Users/tuanlva/.gemini/config/skills/impeccable/scripts/impeccable context
  ```
* Đọc [PRODUCT.md](file:///Users/tuanlva/Folder/workSpace/affiliate/PRODUCT.md) để nắm chắc: Đối tượng người dùng (Affiliate/Creator), mục đích (Motion Control 4 khúc, Quản lý tài khoản), ràng buộc chi phí (≤ 1.000đ/video).
* Xác định **Chế độ màn hình (Mode)**:
  * Toàn bộ AMAS Web UI thuộc chế độ **Operate** (Dashboard công cụ, ưu tiên độ tập trung cao, quét nhanh thông tin, thao tác chính xác, hạn chế trang trí thừa thãi).

### Bước 2: Truy Vấn Thiết Kế & Tokens Cụ Thể (UI-UX-Pro-Max Search)
* Khi dựng layout tổng thể hoặc component mới, dùng `search.py` để lấy bộ quy chuẩn chính xác thay vì tự chế:
  ```bash
  # 1. Truy vấn Design System cho Dashboard Dark Mode
  python3 /Users/tuanlva/.gemini/config/skills/ui-ux-pro-max/scripts/search.py "video creator affiliate dashboard dark mode" --design-system -p "AMAS Studio"

  # 2. Truy vấn tương tác hoặc component cụ thể (ví dụ: Video Timeline, Badge trạng thái)
  python3 /Users/tuanlva/.gemini/config/skills/ui-ux-pro-max/scripts/search.py "video timeline scrubbing playback" --domain ux
  python3 /Users/tuanlva/.gemini/config/skills/ui-ux-pro-max/scripts/search.py "badge status indicator" --domain ux
  ```
* **Bộ Token Tiêu Chuẩn Cho AMAS Web UI:**
  * **Theme:** Dark Mode (OLED / Deep Slate) chống mỏi mắt khi làm việc ban đêm.
  * **Màu sắc:**
    * Background chính: `#000000` / `#0B0B14`
    * Card / Surface: `#12121E` (Border: `#252538`)
    * Primary Text: `#F8FAFC`, Muted Text: `#94A3B8`
    * **Màu Chủ Đạo / CTA:** **`#41AA6C`** (Emerald Growth Green - tượng trưng cho doanh thu, hoa hồng affiliate và nút tạo video) kết hợp phụ trợ `#6366F1` (Indigo).
    * Trạng thái kênh: `Ready` (`#41AA6C` - Xanh lá chủ đạo), `Warming` (Amber/Vàng), `Captcha Blocked` (Crimson/Đỏ).
  * **Typography:** `Inter` / `system-ui` (sạch sẽ, độ giãn dòng chuẩn cho số liệu dashboard).

### Bước 3: Triển Khai Code Giao Diện (Tuân Thủ Craft Floor)
* Đọc nhanh các điều cấm kỵ trong Craft Floor trước khi viết code React/Tailwind:
  * ❌ **Không dùng Emoji làm Icon:** Luôn dùng Lucide Icons (`lucide-react`) hoặc Heroicons dạng SVG sạch.
  * ❌ **Không để trạng thái hover giật cục:** Tất cả nút bấm, row bảng, thẻ card phải có `transition-all duration-150` hoặc `duration-200` và `cursor-pointer`.
  * ❌ **Không bỏ qua Empty States & Loading:** Mọi danh sách (danh sách video, bảng proxy, comment) phải có skeleton loading khi tải và empty state khi trống.
  * ❌ **Tránh chữ mờ bệt thiếu tương phản:** Muted text phải đạt độ tương phản tối thiểu WCAG 4.5:1 so với nền card.
  * ❌ **Không hardcode layout cố định:** Hỗ trợ co giãn mượt từ màn hình laptop nhỏ (1280px) đến màn hình lớn (1920px+).

### Bước 4: Kiểm Tra Cơ Học Bằng Detector (Impeccable Detect)
* Sau khi hoàn tất file giao diện, chạy detector cơ học để phát hiện các lỗi vô thức:
  ```bash
  /Users/tuanlva/.gemini/config/skills/impeccable/scripts/impeccable detect --json <đường_dẫn_file_ui>
  ```
* Sửa triệt để các cảnh báo nếu có trước khi commit hoặc chuyển trạng thái task sang Testing.

---

## 3. Bản Đồ Ứng Dụng Vào 3 Màn Hình Chính Của AMAS

### Tab 1: Motion Control Studio
* **UI-UX-Pro-Max cung cấp:** Quy chuẩn UX cho **Timeline 4 phân đoạn** (Hook, Vấn đề, Demo, CTA), thanh kéo chỉnh tham số (slider/knob), preview so sánh Before/After khi Face Swap.
* **Impeccable kiểm soát:** Đảm bảo bố cục 2 cột cân bằng (cột trái điều khiển, cột phải xem trước video), trạng thái loading thời gian thực qua thanh tiến độ SSE không bị giật layout.

### Tab 2: Quản Lý Tài Khoản & Kho Proxy
* **UI-UX-Pro-Max cung cấp:** Data table chuẩn UX: phân trang, sort, filter theo platform (TikTok/Facebook), huy hiệu trạng thái (status badges) rõ ràng, modal xem ảnh Captcha khẩn cấp.
* **Impeccable kiểm soát:** Màu sắc cảnh báo rủi ro (`captcha_blocked` phải nổi bật ngay lập tức), micro-copy mạch lạc, hành vi xác nhận (confirmation dialog) khi chạy Warmup hoặc gán lại Proxy.

### Tab 3: Lịch Sử & Kho Dữ Liệu Đối Thủ
* **UI-UX-Pro-Max cung cấp:** Thiết kế bảng hiển thị chỉ số tài chính (Doanh thu, Đơn hàng, View, Conversion Rate), badge intent comment (`ask_price`, `complaint`).
* **Impeccable kiểm soát:** Định dạng hiển thị tiền tệ VNĐ và thời gian trực quan, nút thao tác 1-click *"Dùng làm Motion Reference"* liền mạch sang Tab 1.

---

## 4. Checklist Nhanh Dành Cho Agent Trước Khi Giao Bài
- [ ] Đã đọc [PRODUCT.md](file:///Users/tuanlva/Folder/workSpace/affiliate/PRODUCT.md) để bám sát mục tiêu kinh tế và an toàn tài khoản.
- [ ] Đã dùng Lucide SVG Icons, không dùng emoji cho các action buttons.
- [ ] Mọi nút bấm/thao tác dài hạn (tạo video, warmup) đều có trạng thái Disable + Loading spinner.
- [ ] Giao diện hỗ trợ Dark Mode chuẩn `#000000` / `#12121E` nhất quán.
- [ ] Đã chạy lệnh `impeccable detect` và giải quyết hết các vi phạm chất lượng.
