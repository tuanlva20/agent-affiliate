# BRIEFING — 2026-11-10T16:16:30Z

## Mission
Design KOC conversion reply generation and comprehensive test suite architecture for CommentAgent (Milestone 7, Task 7).

## 🔒 My Identity
- Archetype: explorer
- Roles: investigator, architect, test strategist
- Working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m7_explorer_3
- Original parent: f5177315-7404-4813-b8ba-56081885cdd4
- Milestone: Milestone 7 - Task 7 (Comment Engagement & Conversion Agent)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement outside working directory
- Strict tone validation guarantee: 100% of replies must pass `ToneValidator.validate`
- Zero robotic AI cliches or counterfeit/policy-violating words
- Complete evidence chain with file paths and line numbers
- Write comprehensive handoff.md following 5-component protocol

## Current Parent
- Conversation ID: f5177315-7404-4813-b8ba-56081885cdd4
- Updated: 2026-11-10T16:16:30Z

## Investigation State
- **Explored paths**: `ORIGINAL_REQUEST.md`, `PROJECT.md` (F26-F27), `SYSTEM_SPEC.md`, `src/core/prompt_templates.py`, `src/core/tone_validator.py`, `tests/e2e/test_tier1_features.py` (lines 558-590), `tests/e2e/test_tier3_combinations.py`, `tests/e2e/test_tier4_scenarios.py`, `src/database/models.py` (`VideoComment`), `src/services/script_generator.py`.
- **Key findings**:
  1. `test_tier1_features.py` defines contract for `CommentAgent.classify_intent` (4 intents) and `generate_reply` (F27).
  2. In `generate_reply`, price must be formatted (e.g. `189,000đ` or `189k`), yellow cart navigation is required for ASK_PRICE and ASK_MATERIAL_USAGE.
  3. COMPLAINT must strictly de-escalate without sales push, sincerely apologizing and directing to DM/inbox.
  4. Both Hoài My (Fashion) and Nam Minh (HomeLife) personas must be supported with distinct voice, pronouns, and benefit hooks.
  5. Title sanitization is mandatory to eliminate counterfeit brand leaks into replies.
  6. 100% compliance with `ToneValidator.validate()` is strictly verified.
  7. Comprehensive test suite architecture designed across 7 test classes for `tests/test_comment_agent.py`.
- **Unexplored areas**: None. All core focus points fully mapped.

## Key Decisions Made
- Architecture follows dual LLM + certified rotating offline templates pattern from `ScriptGenerator`.
- Title sanitization strips 14+ trademark and policy-violating patterns before template interpolation.
- Full 7-class test suite structure for `tests/test_comment_agent.py` covering Scanner, Classifier, Fashion replies, HomeLife replies, ToneValidator guarantee, DB integration, and LLM fallback.

## Artifact Index
- DISPATCH.md — Initial dispatch instructions
- BRIEFING.md — Situational awareness and state
- progress.md — Heartbeat and step tracking
- handoff.md — Comprehensive blueprint, architectural design, and test suite specification
