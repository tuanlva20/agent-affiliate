## 2026-11-10T10:14:00Z
You are m4_explorer_2, exploration architect for Milestone 4 (Task 4: Telegram Command Center & 1-Tap Approval).

Working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m4_explorer_2/
You MUST read:
- ORIGINAL_REQUEST.md at /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/ORIGINAL_REQUEST.md
- PROJECT.md at /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/PROJECT.md
- SYSTEM_SPEC.md at /Users/tuanlva/Folder/workSpace/affiliate/SYSTEM_SPEC.md
- docs/superpowers/plans/2026-11-10-autonomous-affiliate-system.md (Task 4)
- src/agents/fashion_scout.py (`SpecialistEvaluation` schema)
- src/database/models.py (`VideoJob`, `Product`, `Channel`)
- tests/e2e/test_tier1_features.py (lines 310-320 for `get_approval_keyboard`)

Focus Area:
1. Product Card Formatting:
   - Design helper `format_product_card(product: ProductCandidate | dict, evaluation: SpecialistEvaluation)`: Title, Price, Commission rate & estimated VND payout, Sales 30d, Score, Target Audience, Hook Angle (Hoài My/Nam Minh), Pros & Cons bullets, and Viral Factor.
2. Inline Keyboard Builders in `src/bot/keyboards.py`:
   - `get_approval_keyboard(product_id: str) -> dict | InlineKeyboardMarkup`:
     Button 1: "✅ Duyệt lên kịch bản" with callback_data `approve_product:<product_id>`
     Button 2: "❌ Từ chối" with callback_data `reject_product:<product_id>`
3. Callback Query Handlers in `src/bot/handlers.py`:
   - Handling `approve_product:<id>`: Updates product / creates `VideoJob` in DB with status `pending`, pushes job to video queue, updates Telegram message to show "✅ Đã duyệt".
   - Handling `reject_product:<id>`: Updates product status in DB to `rejected`, updates Telegram message to show "❌ Đã từ chối".

Write your findings to `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m4_explorer_2/handoff.md`. Send a message back to the orchestrator when complete.
