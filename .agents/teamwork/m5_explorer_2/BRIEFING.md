# BRIEFING — 2026-11-10T11:34:00Z

## Mission
Investigate and design technical specifications for `src/services/script_generator.py` (Feature F15 - KOC Natural Script Generator) for Milestone 5, ensuring strict compliance with ToneValidator and contract test requirements.

## 🔒 My Identity
- Archetype: explorer
- Roles: KOC Natural Script Generator Explorer (Milestone 5)
- Working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m5_explorer_2/
- Original parent: f5177315-7404-4813-b8ba-56081885cdd4
- Milestone: M5 (Task 5: Video Remix & Content Engine)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement production source code directly
- Strict ToneValidator integration: ToneValidator.validate() == True and ToneValidator.has_koc_markers() == True
- Script structure: Hook 3s, Core problem/solution, and Call to action (yellow cart)
- Personas: "hoai_my" (women's fashion) and "nam_minh" (smart home utilities)
- Write handoff report with 5 components (Observation, Logic Chain, Caveats, Conclusion, Verification Method) to /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m5_explorer_2/handoff.md

## Current Parent
- Conversation ID: f5177315-7404-4813-b8ba-56081885cdd4
- Updated: 2026-11-10T11:34:00Z

## Investigation State
- **Explored paths**:
  - `tests/e2e/test_tier1_features.py` (contract `test_f15_koc_script_generator`)
  - `tests/e2e/conftest.py` (mock `ScriptGenerator`, `sample_fashion_product`, `sample_homelife_product`)
  - `src/core/tone_validator.py` (`validate`, `has_koc_markers`, `check_violations`, `canonicalize_brand_text`)
  - `src/core/prompt_templates.py` (personas Hoài My & Nam Minh, system prompts, Hook 3s guidelines)
  - `src/agents/fashion_scout.py`, `src/agents/homelife_scout.py`, `src/database/models.py`
  - Workspace Python environment & installed packages (confirmed lack of `google-genai` SDK)
- **Key findings**:
  - The script generator MUST provide synchronous `generate_script` returning a dict or dict-like dataclass (`KOCScriptResult`) with keys `hook_3s`, `body`, `cta_yellow_cart`, `caption`, `full_voiceover`, `voice_id`, `persona`.
  - Persona mapping: Hoài My for `thoi_trang_nu` (`vi-VN-HoaiMyNeural`), Nam Minh for `do_gia_dung` (`vi-VN-NamMinhNeural`).
  - Strict ToneValidator guarantee: All scripts (LLM or template) must pass `ToneValidator.validate() == True` and `ToneValidator.has_koc_markers() == True`. Self-cleansing loop handles dirty raw titles.
  - Zero external SDK reliance: Deterministic rotating template engine ensures 100% offline unit and E2E test success.
- **Unexplored areas**: None. Technical design and test specification for F15 are complete.

## Key Decisions Made
- Designed `KOCScriptResult` dataclass supporting both dictionary indexation and attribute access.
- Designed deterministic rotating template bank for Hoài My and Nam Minh that guarantees 100% pass rate on `ToneValidator`.
- Designed 20-test case suite for `tests/test_script_generator.py`.

## Artifact Index
- /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m5_explorer_2/DISPATCH.md — Received tasks and instructions
- /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m5_explorer_2/BRIEFING.md — Working memory and situational awareness
- /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m5_explorer_2/progress.md — Liveness heartbeat
- /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m5_explorer_2/handoff.md — Final investigation report
