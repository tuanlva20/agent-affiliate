# BRIEFING — 2026-11-10T16:27:00Z

## Mission
Implement Milestone 7: Comment Engagement & Conversion Agent (F26 & F27) for AMAS v1.4.0 following strict TDD, full authentic logic, zero mock in src/, and zero regression.

## 🔒 My Identity
- Archetype: worker_m7_1
- Roles: implementer, qa, specialist
- Working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/worker_m7_1/
- Original parent: f5177315-7404-4813-b8ba-56081885cdd4
- Milestone: Milestone 7 (Comment Engagement & Conversion Agent)

## 🔒 Key Constraints
- DO NOT CHEAT: Genuine implementation only. Real logic, no hardcoded test outputs, no fake flags.
- ZERO imports of `unittest.mock` in `src/`.
- No git commands.
- Exclusive file write boundaries:
  - `src/services/comment_scanner.py`
  - `src/agents/comment_agent.py`
  - `src/core/prompt_templates.py` (append HOMELIFE_COMMENT_REPLY_PROMPT & helper)
  - `src/services/__init__.py`
  - `src/agents/__init__.py`
  - `tests/test_comment_agent.py`
- TDD cycle: RED (tests fail) -> GREEN (implementation passes) -> REFACTOR & REGRESSION TEST.

## Current Parent
- Conversation ID: f5177315-7404-4813-b8ba-56081885cdd4
- Updated: 2026-11-10T16:27:00Z

## Task Summary
- **What to build**: `CommentScanner` (mock & live scanning, DB sync), `CommentIntent` & `CommentAgent` (Vietnamese NLP intent classification, persona-based reply generation, tone validation, title sanitization), prompt templates, and comprehensive tests.
- **Success criteria**: 100% test pass on `tests/test_comment_agent.py` and full suite `pytest tests/`, zero regressions, full adherence to architecture blueprints.
- **Interface contracts**: See explorer handoffs in `.agents/teamwork/m7_explorer_*/handoff.md`.
- **Code layout**: Co-located tests in `tests/`, code in `src/services/`, `src/agents/`, `src/core/`.

## Key Decisions Made
- [TBD]

## Artifact Index
- `.agents/teamwork/worker_m7_1/DISPATCH.md` — Dispatch requirements
- `.agents/teamwork/worker_m7_1/BRIEFING.md` — Persistent working memory
- `.agents/teamwork/worker_m7_1/progress.md` — Progress tracker

## Change Tracker
- **Files modified**: None yet
- **Build status**: Untested
- **Pending issues**: None

## Quality Status
- **Build/test result**: Pending
- **Lint status**: Clean
- **Tests added/modified**: Pending

## Loaded Skills
- None loaded yet
