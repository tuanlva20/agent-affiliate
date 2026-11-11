# BRIEFING — 2026-11-10T09:08:30Z

## Mission
Design prompt templates (`src/core/prompt_templates.py`), align `SpecialistEvaluation` dataclass contracts, and specify comprehensive unit test suite (`tests/test_specialist_scouts.py`) for Specialist Scout Agents (Fashion KOC Hoài My & HomeLife KOC Nam Minh).

## 🔒 My Identity
- Archetype: explorer
- Roles: read-only investigation, prompt template engineering, specialist evaluation schema design, test suite design
- Working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m3_explorer_3
- Original parent: f5177315-7404-4813-b8ba-56081885cdd4
- Milestone: Milestone 3 (Task 3: Specialist Scout Agents - Prompt Templates & Test Suite)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement or modify source code files directly
- Write only to working directory `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m3_explorer_3/`
- Output analysis and specifications in `handoff.md` adhering strictly to 5-Component Handoff Protocol
- Send message to parent upon completion

## Current Parent
- Conversation ID: f5177315-7404-4813-b8ba-56081885cdd4
- Updated: 2026-11-10T09:02:30Z

## Investigation State
- **Explored paths**:
  - `SYSTEM_SPEC.md` (Specialist scouts overview, biometrics engine, channel lifecycles)
  - `docs/superpowers/plans/2026-11-10-autonomous-affiliate-system.md` (Task 3 specifications, interfaces, files)
  - `config.yaml` (Niche personas: Hoài My `vi-VN-HoaiMyNeural` & Nam Minh `vi-VN-NamMinhNeural`, thresholds, banned keywords)
  - `src/core/config.py` (Pydantic models `PersonaConfig`, `NicheConfig`, `FilterThresholds`, `AppConfig`)
  - `src/core/tone_validator.py` (`ToneValidator` with robotic, counterfeit, and exaggerated regex patterns, and KOC markers)
  - `src/agents/base_scout.py` (`ProductCandidate` schema, `BaseScoutAgent` filtering logic)
  - `src/database/models.py` (`Product` ORM model, `evaluation_data` JSONB column)
  - `tests/e2e/conftest.py` (`SpecialistEvaluation` dataclass prototype, scout stubs, product fixtures)
  - `tests/e2e/test_tier1_features.py` (F08, F09 assertions on score, hooks, rejections)
  - `tests/e2e/test_tier2_boundaries.py` (counterfeit trademark matrix, exaggerated claims matrix)
  - `tests/e2e/test_tier3_combinations.py` (scout to Telegram card pipeline)
  - Peer explorer work (`m3_explorer_1`, `m3_explorer_2`)
- **Key findings**:
  - `SpecialistEvaluation` contract aligned across all 10 fields with `to_dict` and `from_dict` serialization.
  - Persona specifications for Hoài My and Nam Minh mapped cleanly to system prompts, hook 3s guidelines, and anti-robotic tone rules.
  - Scoring thresholds: valid fashion body-hack product must reach score >= 8.0 with "bụng"/"eo" in hook; valid homelife labor-saving product must reach score >= 8.5 with "3s"/"nhàn" in hook. Counterfeit fashion products must be rejected with score = 0.0 and "trademark" or "policy" in rejection_reason. Exaggerated homelife claims must be rejected with score = 0.0 and "exaggerated" or "policy" in rejection_reason. Low-scoring items (< 7.0) rejected. Corrupted/empty inputs handled gracefully without uncaught exceptions.
  - Complete 12-test suite defined for `tests/test_specialist_scouts.py`.
- **Unexplored areas**: None within the scope of Task 3 prompt templates and test suite.

## Key Decisions Made
- `SpecialistEvaluation` dataclass defined in `src/agents/fashion_scout.py` and imported by `src/agents/homelife_scout.py` and `src/agents/__init__.py`.
- `src/core/prompt_templates.py` structured with KOC personas, 3s hook guidelines, LLM evaluation system prompts, prompt builders, structured JSON schemas, and forward-compatible script/reply templates.
- Complete drop-in code proposals drafted for `src/core/prompt_templates.py`, `SpecialistEvaluation` dataclass, and `tests/test_specialist_scouts.py`.

## Artifact Index
- `progress.md` — Heartbeat and task checklist
- `DISPATCH.md` — Input instructions and dispatch log
- `BRIEFING.md` — Working memory and investigation state
- `handoff.md` — Final 5-component report
