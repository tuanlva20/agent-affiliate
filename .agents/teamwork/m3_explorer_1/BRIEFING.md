# BRIEFING — 2026-11-10T09:07:00Z

## Mission
Investigate requirements, architecture, scoring formulas, rejection policies, hook generator, and Hoài My persona template for FashionScoutAgent (Feature F08) in Milestone 3.

## 🔒 My Identity
- Archetype: explorer
- Roles: investigation, synthesis
- Working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m3_explorer_1
- Original parent: f5177315-7404-4813-b8ba-56081885cdd4
- Milestone: Milestone 3 (Task 3: Specialist Scout Agents - FashionScoutAgent, Feature F08)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Scope: FashionScoutAgent (`src/agents/fashion_scout.py`) and Fashion Prompt Template (`src/core/prompt_templates.py`)
- Produce handoff.md with class architecture, scoring tables, and test scenarios
- Communicate via send_message to f5177315-7404-4813-b8ba-56081885cdd4

## Current Parent
- Conversation ID: f5177315-7404-4813-b8ba-56081885cdd4
- Updated: 2026-11-10T09:01:26Z

## Investigation State
- **Explored paths**:
  - `SYSTEM_SPEC.md` § 1, § 2, § 3 (Specialist Scout Agents, Pilot Niches, Biometrics)
  - `docs/superpowers/plans/2026-11-10-autonomous-affiliate-system.md` (Task 3 specification & interfaces)
  - `config.yaml` lines 52-109 (`thoi_trang_nu` niche config, thresholds, Hoài My persona, banned keywords)
  - `src/agents/base_scout.py` (`BaseScoutAgent`, `ProductCandidate`)
  - `src/core/tone_validator.py` (`ToneValidator`, `COUNTERFEIT_PATTERNS`, `ROBOTIC_PATTERNS`, `check_violations`)
  - `tests/e2e/conftest.py` lines 324-336 (`SpecialistEvaluation`), lines 438-474 (`FashionScoutAgent` stub)
  - `tests/e2e/test_tier1_features.py` lines 247-273 (`test_f08_fashion_scout_agent`)
  - `tests/e2e/test_tier2_boundaries.py` lines 86-120 (Counterfeit & trademark matrix)
  - `tests/e2e/test_tier3_combinations.py` lines 66-85 (Scout to Telegram card approval)
  - `tests/e2e/test_tier4_scenarios.py` lines 68-74 (E2E Fashion candidate workflow)
- **Key findings**:
  - Interface contract: `evaluate_product(item: Dict[str, Any]) -> SpecialistEvaluation`.
  - `SpecialistEvaluation` fields: `product_id`, `niche_id`, `passed_filter`, `score`, `hook_angle`, `target_audience`, `pros`, `cons`, `viral_factor`, `rejection_reason`.
  - Rejection requirement: `ToneValidator` detects counterfeit brand names; returns `passed_filter=False`, `score=0.0`, with explicit `"trademark policy"` or `"policy violation"` in `rejection_reason`.
  - Scoring requirement: Base score (6.5), body-hack keyword bonuses (che bụng, giấu mỡ, chiết eo, tôn vòng 1, chân dài, tôn dáng, hack chiều cao), viral sales velocity multiplier (up to 1.15x), rating adjustment. Target: body-hack items score >= 8.0 (viral >= 8.5), subthreshold items < 7.0 rejected.
  - Hook generator requirement: Produces natural Vietnamese KOC hooks containing "bụng" or "eo" or body-slimming angles without bot clichés.
  - Prompt template requirement: Define Hoài My persona (`vi-VN-HoaiMyNeural`, sweet, relatable, body-hack expert) in `src/core/prompt_templates.py`.
- **Unexplored areas**: None within the scope of F08. Ready to produce full handoff report.

## Key Decisions Made
- Designed comprehensive mathematical scoring algorithm balancing body-hack keywords and sales velocity.
- Designed zero-tolerance trademark violation policy directly leveraging `ToneValidator`.
- Designed Hoài My KOC persona and prompt templates adhering strictly to anti-robotic guidelines.
- Designed comprehensive test suite for `tests/test_specialist_scouts.py`.

## Artifact Index
- /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m3_explorer_1/handoff.md — Final exploration report
