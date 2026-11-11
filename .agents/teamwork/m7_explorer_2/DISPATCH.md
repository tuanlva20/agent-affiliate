## 2026-11-10T16:10:25Z
From: f5177315-7404-4813-b8ba-56081885cdd4
Priority: MESSAGE_PRIORITY_HIGH

You are m7_explorer_2, an exploration agent investigating Intent Classification for Milestone 7 (Task 7: Comment Engagement & Conversion Agent).

Working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m7_explorer_2/
Read ORIGINAL_REQUEST.md first: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/ORIGINAL_REQUEST.md
Also read:
- /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/PROJECT.md (Feature F27)
- /Users/tuanlva/Folder/workSpace/affiliate/tests/e2e/test_tier1_features.py (F27 contract, lines 573-590)
- /Users/tuanlva/Folder/workSpace/affiliate/docs/superpowers/plans/2026-11-10-autonomous-affiliate-system.md (Task 7)

Your Focus:
1. Detailed design for `CommentIntent` enum and `CommentAgent.classify_intent`:
   - `CommentIntent` enum:
     * `ASK_PRICE = "ask_price"` (Hỏi giá: "giá", "bao nhiêu", "bao tiền", "tiền", "nhiêu xiền", "inbox giá", "rổ giá", etc.)
     * `ASK_MATERIAL_USAGE = "ask_material_usage"` (Hỏi chất liệu, kích cỡ, cách dùng: "chất", "size", "vải", "dùng", "bụng", "kg", "mặc", "cao 1m55", "nặng 50kg", "form", "co giãn", "giặt", etc.)
     * `COMPLAINT = "complaint"` (Khiếu nại: "chậm", "kém", "lỗi", "hỏng", "lừa", "lâu", "tệ", "chưa nhận được", "sai mẫu", "rách", "không giống hình", etc.)
     * `OTHER = "other"` (Khen ngợi, hỏi vu vơ, spam: "tuyệt vời", "đẹp quá", "haha", "chấm", etc.)
   - Classification Algorithm:
     * Robust Vietnamese NLP text normalization (lowercase, tone-aware, unaccented fallback, punctuation stripping).
     * Rule-based keyword matching with regex word boundary support.
     * High precision and recall: handles Vietnamese internet slang ("nhiu", "xiền", "m7 60kg", "55 cân", "đổi trả", etc.).
   - Contract verification against `test_f27_intent_and_koc_reply_agent`:
     * `"Váy này giá bao nhiêu vậy shop?"` -> `CommentIntent.ASK_PRICE`
     * `"Bụng 75cm mặc size nào vừa ạ?"` -> `CommentIntent.ASK_MATERIAL_USAGE`
     * `"Giao hàng lâu quá shop ơi!"` -> `CommentIntent.COMPLAINT`
     * `"Tuyệt vời"` -> `CommentIntent.OTHER`
2. Test Strategy for intent classification:
   - Exhaustive equivalence partition and boundary value test cases.
   - Stress testing ambiguous comments, questions with multiple intents, and short slang.

Deliverables:
- Write comprehensive blueprint and analysis to `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m7_explorer_2/handoff.md`.
- Include exact keyword maps, normalization rules, edge case handlers, and sample tests.
- DO NOT edit or create any source code outside your directory.
- Send a completion message back when done.
