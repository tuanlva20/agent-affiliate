# DISPATCH — m5_explorer_2
Role: KOC Natural Script Generator Explorer (Milestone 5)
Workspace: /Users/tuanlva/Folder/workSpace/affiliate
Milestone: M5 (Task 5: Video Remix & Content Engine)
Working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m5_explorer_2/
Parent Conversation ID: f5177315-7404-4813-b8ba-56081885cdd4

Your task:
Khảo sát và thiết kế kiến trúc kỹ thuật cho `src/services/script_generator.py` (Feature F15):
1. Cấu trúc kịch bản KOC theo công thức Hook 3s:
   - Hook (3s đầu): Đánh trúng nỗi đau / điểm nhấn thị giác gây tò mò.
   - Problem / Solution: Trải nghiệm thực tế của KOC (không tâng bốc, chân thật).
   - CTA (Call to action): Điều hướng vào giỏ hàng vàng góc trái màn hình.
2. Personas:
   - "hoai_my" (Thời trang nữ): Giọng nữ ngọt ngào, gần gũi, xưng hô bà - tôi / các nàng.
   - "nam_minh" (Đồ gia dụng thông minh): Giọng nam chân chất, chuyên nghiệp, test thực tế trước/sau.
3. Tuân thủ tuyệt đối `ToneValidator`:
   - 0 từ ngữ rập khuôn AI (clichés).
   - 0 từ khóa hàng nhái / vi phạm thương hiệu (đã chuẩn hóa qua NFD canonicalize).
   - 0 tuyên bố phóng đại quá đà (100% hết, trị dứt điểm, vĩnh viễn không hỏng...).
   - Bắt buộc có markers tự nhiên của KOC (`ToneValidator.has_koc_markers(script) == True`).
4. Kiểm tra contract tests: `tests/e2e/test_tier1_features.py:test_f15_natural_koc_script_generator` và thiết kế test suite `tests/test_script_generator.py`.
5. Viết báo cáo khảo sát kỹ thuật chi tiết tại handoff.md.


## 2026-11-10T11:27:47Z
Message received from parent orchestrator:
You are m5_explorer_2, KOC Natural Script Generator Explorer for Milestone 5 (Video Remix & Content Engine).
Your working directory is: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m5_explorer_2/
The original request file is: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/ORIGINAL_REQUEST.md
The dispatch file is: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m5_explorer_2/DISPATCH.md
The project scope is in: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/PROJECT.md

Read ORIGINAL_REQUEST.md, DISPATCH.md, and PROJECT.md.
Investigate the technical implementation requirements for:
1. `src/services/script_generator.py` (Feature F15):
   - Contract in `tests/e2e/test_tier1_features.py:test_f15_natural_koc_script_generator`.
   - Script generation structure: Hook 3s, Core problem/solution, and Call to action (yellow cart).
   - Persona customization: Hoài My for women's fashion, Nam Minh for smart home utilities.
   - Strict `ToneValidator` integration: must pass `ToneValidator.validate() == True` and `ToneValidator.has_koc_markers() == True`.
2. Formulate concrete prompt templates, generation logic, fallback offline generators, and test suite specifications for `tests/test_script_generator.py` in your handoff report.
Write your report to `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m5_explorer_2/handoff.md`.
Send a message back to parent orchestrator when done.
