# BRIEFING — 2026-11-10T09:08:30Z

## Mission
Investigate and design HomeLifeScoutAgent and HomeLife KOC Persona prompt template for Milestone 3 (F09).

## 🔒 My Identity
- Archetype: explorer
- Roles: investigation, analysis, synthesis
- Working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m3_explorer_2
- Original parent: f5177315-7404-4813-b8ba-56081885cdd4
- Milestone: Milestone 3 (Task 3: Specialist Scout Agents - HomeLifeScoutAgent)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Do NOT modify source code
- Files for content delivery, Messages for coordination
- Handoff report in handoff.md following 5-component protocol

## Current Parent
- Conversation ID: f5177315-7404-4813-b8ba-56081885cdd4
- Updated: 2026-11-10T09:01:34Z

## Investigation State
- **Explored paths**:
  - `SYSTEM_SPEC.md` § 1, § 2, § 3 (Multi-agent architecture, Specialist Scout Agents, Pilot Niches)
  - `PROJECT.md` (Milestones, Task 3, Interface Contracts for Scout Agents)
  - `docs/superpowers/plans/2026-11-10-autonomous-affiliate-system.md` (Task 3 step breakdown)
  - `config.yaml` lines 110-155 (`do_gia_dung` niche configuration, thresholds, Nam Minh persona, banned keywords)
  - `src/agents/base_scout.py` (`BaseScoutAgent`, `ProductCandidate`)
  - `src/core/tone_validator.py` (`ToneValidator`, `EXAGGERATED_PATTERNS`, `check_violations`, `validate`)
  - `tests/e2e/conftest.py` lines 324-336 (`SpecialistEvaluation`), lines 475-508 (`HomeLifeScoutAgent` stub)
  - `tests/e2e/test_tier1_features.py` lines 275-298 (`test_f09_homelife_scout_agent`)
  - `tests/e2e/test_tier2_boundaries.py` lines 124-149 (`test_boundary_exaggerated_claims_matrix`)
  - `tests/e2e/test_tier4_scenarios.py` lines 170-184 (`test_scenario_homelife_smart_cleaner_campaign`)
  - Peer explorer briefings: `m3_explorer_1` (FashionScoutAgent F08) & `m3_explorer_3` (Prompt templates & test suite)
- **Key findings**:
  - `HomeLifeScoutAgent.evaluate_product(item: Dict[str, Any]) -> SpecialistEvaluation` is the core interface contract.
  - Zero-tolerance policy violation: must detect exaggerated medical and cleaning promises (trị dứt điểm 100%, vĩnh viễn không bám bẩn/hỏng, thần dược, chữa khỏi) via `ToneValidator`. Returns `passed_filter=False`, `score=0.0`, with explicit `"exaggerated policy"` or `"policy violation"` in `rejection_reason`.
  - Quantitative scoring formula: Base score 6.0, labor-saving utility bonuses up to +2.0 (tự vắt, tự động, không chạm tay, rảnh tay, thông minh, đa năng, nhàn), Before/After 3s visual contrast potential up to +1.2, sales velocity up to +0.5, price sweet spot up to +0.3. High labor-saving items score >= 8.5 to 9.5 (passing tests). Subthreshold items (< 7.0) rejected.
  - Hook angle generator: Must produce compelling natural hooks containing "3s" or "nhàn" without bot clichés.
  - Viral factor: Must contain "3s" or "vắt khô".
  - Persona template: Nam Minh (`vi-VN-NamMinhNeural`, male, practical, life-hack & chore-reliever, authentic/unpretentious) to be defined in `src/core/prompt_templates.py`.
- **Unexplored areas**: None within the scope of F09. Ready to write full handoff report.

## Key Decisions Made
- Formulated an exact scoring breakdown ensuring `sample_homelife_product` scores >= 8.5, `target_cleaner` scores >= 8.8, and mediocre items score < 7.0.
- Standardized rejection reasons to include `"Violates exaggerated policy: ..."` for exaggerated claims and `"Policy violation: ..."` for other violations.
- Guaranteed all generated hooks contain both `"3s"` and `"nhàn"`, and viral factor contains `"3s"` and `"vắt khô"`.
- Formulated complete Nam Minh KOC persona prompt template and structured evaluation JSON prompts for `src/core/prompt_templates.py`.

## Artifact Index
- DISPATCH.md — Parent dispatch message
- BRIEFING.md — Persistent working memory
- progress.md — Heartbeat and step tracking
- handoff.md — Final 5-component handoff report
