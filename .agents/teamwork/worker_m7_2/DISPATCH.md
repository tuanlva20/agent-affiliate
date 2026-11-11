## 2026-11-10T16:36:24Z
[Message] timestamp=2026-11-10T16:36:24Z sender=f5177315-7404-4813-b8ba-56081885cdd4 priority=MESSAGE_PRIORITY_HIGH content=You are worker_m7_2 (role: "Milestone 7 Replacement Implementer"), spawned as an immediate replacement for worker_m7_1, who was interrupted by a network error during Milestone 7 (Comment Engagement & Conversion Agent: Features F26 & F27) implementation.

Working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/worker_m7_2/
Project root: /Users/tuanlva/Folder/workSpace/affiliate

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
CRITICAL INTEGRITY CONSTRAINTS:
- ZERO imports of `unittest.mock` (MagicMock, AsyncMock, patch) in any file under `src/`! Mocking libraries belong exclusively in `tests/`.
- NO dummy bypass flags, whitelist strings, or fake sleep shortcuts in `src/`.
- Full authentic logic must be implemented in all components.

## User Constraints
- Do NOT run git commands (không cần chạy lệnh git).

## File Write Boundaries
You have exclusive write ownership over:
- `src/services/comment_scanner.py`
- `src/agents/comment_agent.py`
- `src/core/prompt_templates.py` (append HOMELIFE_COMMENT_REPLY_PROMPT & helper if not already present)
- `src/services/__init__.py` (re-export CommentScanner and custom exceptions)
- `src/agents/__init__.py` (re-export CommentAgent and CommentIntent)
- `tests/test_comment_agent.py`
Do NOT modify existing files outside this scope unless strictly necessary for imports.

## Inputs & Blueprints
1. `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/ORIGINAL_REQUEST.md`
2. Predecessor progress: `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/worker_m7_1/progress.md`
3. Explorer handoffs:
   - `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m7_explorer_1/handoff.md` (CommentScanner architecture, dual-mode, database synchronization)
   - `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m7_explorer_2/handoff.md` (CommentIntent enum, Vietnamese NLP normalization, homograph collision protection, priority classification)
   - `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m7_explorer_3/handoff.md` (KOC persona reply generation, ToneValidator guarantee, title sanitization, comprehensive test suite architecture)

## Current Interruption Point & Your Objective
`worker_m7_1` created `tests/test_comment_agent.py`, `src/services/comment_scanner.py`, and `src/agents/comment_agent.py` right before crashing.
Your task is to:
1. Inspect the existing code in `tests/test_comment_agent.py`, `src/services/comment_scanner.py`, `src/agents/comment_agent.py`, `src/core/prompt_templates.py`, and `src/*/__init__.py`.
2. Verify that they are completely implemented, have no syntax or runtime errors, and meet all functional requirements:
   - `CommentScanner`: `scan_comments(video_id, limit=10)` returning dicts with `comment_id`, `text`, `user`, `author_name`, `author_id`, `timestamp`, `like_count`, `reply_count`; `sync_comments_to_db` with idempotency; exception hierarchy.
   - `CommentIntent`: `ASK_PRICE`, `ASK_MATERIAL_USAGE`, `COMPLAINT`, `OTHER`.
   - `CommentAgent.classify_intent`: High-precision Vietnamese NLP with homograph collision protection and complaint priority.
   - `CommentAgent.generate_reply`: Pilot niches (Hoài My for fashion, Nam Minh for home utilities), title sanitization against counterfeit brands and exaggerated claims, 100% `ToneValidator.validate()` guarantee.
   - Re-exports in `src/services/__init__.py` and `src/agents/__init__.py`.
   - Static integrity check: Verify 0 occurrences of `unittest.mock` in `src/`.
3. Run test verification:
   - Run `pytest tests/test_comment_agent.py -v` and ensure 100% PASS.
   - Run full repository regression `pytest tests/ -v` and ensure 100% PASS (zero regressions).
4. Write your completion report in `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/worker_m7_2/handoff.md` with:
   - Summary of verified/fixed implementations.
   - Commands executed and verbatim test outputs.
   - Static integrity check confirmation.
5. Send completion message to parent orchestrator via `send_message`.
