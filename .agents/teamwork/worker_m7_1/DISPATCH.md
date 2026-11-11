## 2026-11-10T16:26:28Z
You are worker_m7_1 (role: "Milestone 7 Implementer"), dispatched to implement Task 7 (Comment Engagement & Conversion Agent: Feature F26 & F27) for the Autonomous TikTok Affiliate System (AMAS v1.4.0).

Working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/worker_m7_1/
Project root: /Users/tuanlva/Folder/workSpace/affiliate

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
CRITICAL LESSON FROM PREVIOUS MILESTONES:
- ZERO imports of `unittest.mock` (MagicMock, AsyncMock, patch) in any file under `src/`! Mocking libraries belong exclusively in `tests/`.
- NO dummy bypass flags, whitelist strings, or fake sleep shortcuts in `src/`.
- Full authentic logic must be implemented in all components.

## User Constraints
- Do NOT run git commands (không cần chạy lệnh git).

## File Write Boundaries
You have exclusive write ownership over:
- `src/services/comment_scanner.py`
- `src/agents/comment_agent.py`
- `src/core/prompt_templates.py` (append HOMELIFE_COMMENT_REPLY_PROMPT & helper)
- `src/services/__init__.py` (re-export CommentScanner and custom exceptions)
- `src/agents/__init__.py` (re-export CommentAgent and CommentIntent)
- `tests/test_comment_agent.py`
Do NOT modify existing files outside this scope unless strictly necessary for imports.

## Inputs & Blueprints
Read the following authoritative sources before writing any code:
1. `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/ORIGINAL_REQUEST.md`
2. `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m7_explorer_1/handoff.md` (CommentScanner architecture, dual-mode, database synchronization)
3. `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m7_explorer_2/handoff.md` (CommentIntent enum, Vietnamese NLP normalization, homograph collision protection, priority classification)
4. `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m7_explorer_3/handoff.md` (KOC persona reply generation, ToneValidator guarantee, title sanitization, comprehensive test suite architecture)

## Functional Requirements
1. `CommentScanner` (`src/services/comment_scanner.py`):
   - `scan_comments(self, video_id: str, limit: int = 10) -> List[Dict[str, Any]]`:
     Returns list of dicts with: `comment_id`, `text`, `user`, `author_name`, `author_id`, `timestamp` (ISO UTC), `like_count`, `reply_count`.
     Supports default offline mock mode (deterministic high-fidelity Vietnamese comments) and live TikTok Web API extraction with timeout, rate limit handling, and exponential backoff.
   - `sync_comments_to_db(self, video_id: str, channel_id: str, comments: List[Dict], session: AsyncSession) -> List[VideoComment]`:
     Idempotently persists comments to SQLite/PostgreSQL `VideoComment` ORM table. Handles intra-batch duplicates and preserves existing status/reply fields.
   - Custom exceptions: `CommentScannerError`, `InvalidVideoIdError`, `CommentScannerTimeoutError`, `CommentRateLimitError`, `VideoNotFoundError`.

2. `CommentIntent` & `CommentAgent` (`src/agents/comment_agent.py`):
   - `CommentIntent(str, Enum)`: `ASK_PRICE = "ask_price"`, `ASK_MATERIAL_USAGE = "ask_material_usage"`, `COMPLAINT = "complaint"`, `OTHER = "other"`.
   - `classify_intent(self, comment_text: str) -> CommentIntent`:
     High-precision Vietnamese NLP with Unicode NFC normalization, unaccented transliteration fallback, homograph protection (`bụng` vs `bung chỉ`, `lâu` vs `cây lau`, `lừa` vs `vải lụa`), false-positive price guards (`giá như`, `đánh giá`), and strict priority (`COMPLAINT` > `ASK_PRICE` > `ASK_MATERIAL_USAGE` > `OTHER`).
   - `generate_reply(self, comment_text: str, product_meta: Dict, persona: Dict) -> str`:
     Generates authentic KOC response:
     - Pilot niches: Hoài My for `thoi_trang_nu` (sweet, "chị em ơi", body hack, yellow cart CTA), Nam Minh for `do_gia_dung` (practical, "các bác ơi", 3s Before/After, yellow cart CTA).
     - Title sanitization: Strips counterfeit brands and exaggerated claims from product title before interpolation.
     - 100% compliance guarantee with `ToneValidator.validate(reply)`.

3. Strict TDD Process:
   - Step 1: Write `tests/test_comment_agent.py` containing comprehensive test classes covering Scanner, Intent, Replies, Tone, Title sanitization, and DB persistence.
   - Step 2: Run `pytest tests/test_comment_agent.py -v` to confirm failure (RED phase).
   - Step 3: Implement `src/services/comment_scanner.py`, `src/agents/comment_agent.py`, update `src/core/prompt_templates.py`, and re-exports.
   - Step 4: Run `pytest tests/test_comment_agent.py -v` to confirm 100% PASS (GREEN phase).
   - Step 5: Run full repository regression `pytest tests/ -v` to ensure zero regressions across all prior milestones and E2E suites.
