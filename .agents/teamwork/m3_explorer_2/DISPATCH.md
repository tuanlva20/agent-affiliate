## 2026-11-10T09:01:34Z
You are m3_explorer_2, an exploration agent for Milestone 3 (Task 3: Specialist Scout Agents - HomeLifeScoutAgent).

Working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m3_explorer_2/
Maintain progress.md in your working directory.
Original request file: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/ORIGINAL_REQUEST.md
Project plan: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/PROJECT.md
System spec: /Users/tuanlva/Folder/workSpace/affiliate/SYSTEM_SPEC.md
Plan doc: /Users/tuanlva/Folder/workSpace/affiliate/docs/superpowers/plans/2026-11-10-autonomous-affiliate-system.md

Scope: `HomeLifeScoutAgent` (`src/agents/homelife_scout.py`) and HomeLife Prompt Template.
Feature: F09 (HomeLife Scout Agent).

Tasks:
1. Investigate requirements for `HomeLifeScoutAgent`:
   - Scoring algorithm: evaluates Home Utilities items on labor-saving utility (giải phóng sức lao động, nhàn việc nhà, tiết kiệm thời gian, đa năng, thông minh) and Before/After 3s visual contrast hooks.
   - Rejection mechanism: uses `ToneValidator` to detect exaggerated medical/cleaning claims (trị dứt điểm 100%, vĩnh viễn không bám bẩn/hỏng, thần dược). Returns `passed_filter=False`, `score=0.0`, with explicit `"exaggerated policy"` or `"policy violation"` in `rejection_reason`.
   - Hook angle generator: produces compelling natural hook angles containing "3s" or "nhàn".
   - Target audience, pros, cons, viral factor generation.
   - Method signature: `evaluate_product(self, item: Dict[str, Any]) -> SpecialistEvaluation`.
2. Define HomeLife KOC Persona prompt template in `src/core/prompt_templates.py` (Nam Minh - thực tế, chân thật, mẹo vặt gia đình tiện ích).
3. Produce a detailed exploration report with class architecture, scoring tables, and test scenarios.

Write your report to `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m3_explorer_2/handoff.md` and send a message when done. Do NOT modify source code.
