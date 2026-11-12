# Design System — AMAS Studio

<!-- impeccable:design-schema 1 -->

## Visual Authority & Theme

- **Theme Mode:** Dark Mode OLED / Deep Slate (ưu tiên chống mỏi mắt cho creator làm việc ban đêm).
- **Màu Chủ Đạo (Primary Brand Accent):** `#41AA6C` (Emerald/Mint Green — biểu trưng cho sự tăng trưởng doanh số, đơn hàng affiliate và nút tạo video).
- **Core Font:** `Inter`, `-apple-system`, `BlinkMacSystemFont`, `sans-serif`.
- **Master Tokens Reference:** Đã được khóa cứng tại [`design-system/amas-studio/MASTER.md`](file:///Users/tuanlva/Folder/workSpace/affiliate/design-system/amas-studio/MASTER.md).

---

## 1. Color System (Bảng Màu Khóa Cứng 100%)

Tất cả component và file UI **bắt buộc** dùng CSS variables hoặc Tailwind classes tương ứng, tuyệt đối không tự ý pha mã hex ngẫu nhiên:

| Vai trò | Mã Hex | CSS Variable | Tailwind Class tương đương | Mô tả / Ứng dụng |
| :--- | :--- | :--- | :--- | :--- |
| **Màu Chủ Đạo / Accent chính** | **`#41AA6C`** | `--color-accent` | **`bg-[#41AA6C]`** / **`text-[#41AA6C]`** | **Nút CTA chính, Nút Tạo Video, Highlight doanh thu, Active tab** |
| **Hover của Màu Chủ Đạo** | `#348B58` | `--color-accent-hover` | `hover:bg-[#348B58]` | Trạng thái hover của nút bấm chính |
| **Background chính** | `#000000` | `--color-background` | `bg-black` / `bg-[#000000]` | Nền tổng thể toàn bộ trang |
| **Surface / Card nền 1** | `#0C0C0D` / `#12121E` | `--color-card` | `bg-[#0C0C0D]` / `bg-[#12121E]` | Nền card, form điều khiển, thanh sidebar |
| **Surface Hover / Active** | `#1A1A2E` | `--color-card-hover` | `hover:bg-[#1A1A2E]` | Hover trên row bảng hoặc list item |
| **Card Border** | `#252538` | `--color-border` | `border-[#252538]` | Viền tinh tế ngăn cách các vùng |
| **Text chính (Primary)** | `#F8FAFC` | `--color-foreground` | `text-slate-50` / `text-[#F8FAFC]` | Tiêu đề, nhãn chính, số liệu |
| **Text phụ (Muted)** | `#94A3B8` | `--color-muted-foreground` | `text-slate-400` / `text-[#94A3B8]` | Ghi chú, metadata, thời gian |
| **Secondary Accent** | `#6366F1` (Indigo) | `--color-secondary` | `bg-indigo-600` | Dùng cho nhãn phụ hoặc bộ lọc platform |
| **Cảnh báo lỗi / Danger** | `#EF4444` (Red) | `--color-destructive` | `bg-red-500` / `text-red-500` | Nút xóa, dừng tác vụ |

### Màu Trạng Thái Nghiệp Vụ (Semantic Badges):
- **Ready to post (Sẵn sàng đăng):** Xanh lá chuẩn thương hiệu `#41AA6C` (`bg-[#41AA6C]/10 text-[#41AA6C] border-[#41AA6C]/30`).
- **Warming (Đang nuôi nick):** Vàng Amber (`bg-amber-500/10 text-amber-400 border-amber-500/20`).
- **Cooldown (Nghỉ giãn cách):** Xanh Slate (`bg-slate-500/10 text-slate-400 border-slate-500/20`).
- **Captcha Blocked (Bị khóa):** Đỏ Crimson (`bg-rose-500/10 text-rose-400 border-rose-500/20`).

---

## 2. Typography Hierarchy (Quy Chuẩn Font Chữ)

Sử dụng duy nhất bộ font **`Inter`** với độ co giãn phân cấp rõ ràng:

* **Page Title (H1):** `text-2xl font-bold tracking-tight text-[#F8FAFC]` (24px).
* **Section Title (H2):** `text-lg font-semibold tracking-tight text-[#F8FAFC]` (18px).
* **Card Subheading (H3):** `text-sm font-medium text-slate-300` (14px).
* **Body / Data Text:** `text-sm text-[#F8FAFC]` (14px, leading-5).
* **Muted Caption / Metadata:** `text-xs text-[#94A3B8]` (12px, tracking-normal).
* **Số liệu Metric / Doanh thu:** `text-xl font-bold font-mono tracking-tight text-[#41AA6C]` (số tiền VNĐ và lượt view dùng font monospace kết hợp màu chủ đạo `#41AA6C`).

---

## 3. UI Component Standards (Quy Chuẩn Thành Phần)

1. **Button Action:**
   - Bo góc: `rounded-lg` (8px).
   - Chiều cao: 36px (Compact) hoặc 40px (Default).
   - **Nút Tạo Video / Primary CTA:** Nền `#41AA6C`, text trắng hoặc text `#000000 font-semibold`, hover `#348B58`, `transition-all duration-150 shadow-sm shadow-[#41AA6C]/20`.
   - **Nút Secondary / Outline:** Border `#252538`, nền trong suốt, hover `bg-[#41AA6C]/10 hover:border-[#41AA6C]/40 hover:text-[#41AA6C]`.
2. **Cards / Containers:**
   - Bo góc `rounded-xl` (12px).
   - Nền `#0C0C0D` hoặc `#12121E`, viền 1px `border-[#252538]`.
   - Khi hover (nếu là thẻ click được): `hover:border-[#41AA6C]/50 transition-colors duration-150`.
3. **Icons:**
   - 100% SVG từ `lucide-react`. Kích thước chuẩn: `w-4 h-4` (inline) hoặc `w-5 h-5` (nút lớn). Tuyệt đối cấm emoji.
