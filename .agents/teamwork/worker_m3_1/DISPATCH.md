## 2026-11-10T09:10:46Z
You are worker_m3_1, assigned to implement Milestone 3 (Task 3: Specialist Scout Agents: FashionScoutAgent, HomeLifeScoutAgent, Prompt Templates).

Your working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/worker_m3_1/
Maintain progress.md in your working directory.
Original request file: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/ORIGINAL_REQUEST.md
Project plan: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/PROJECT.md
System spec: /Users/tuanlva/Folder/workSpace/affiliate/SYSTEM_SPEC.md

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Explorer Blueprints to Read First:
1. /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m3_explorer_1/handoff.md (FashionScoutAgent & Hoài My Persona)
2. /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m3_explorer_2/handoff.md (HomeLifeScoutAgent & Nam Minh Persona)
3. /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m3_explorer_3/handoff.md (Prompt Templates, SpecialistEvaluation, and Unit Test Suite)

## Write Ownership:
You have exclusive write ownership of:
- `src/core/prompt_templates.py`
- `src/agents/fashion_scout.py`
- `src/agents/homelife_scout.py`
- `tests/test_specialist_scouts.py`
- Your working directory: `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/worker_m3_1/`

## TDD Implementation Instructions:
Follow strict TDD:

### Step 1: Write Unit Tests (RED Phase)
- In `tests/test_specialist_scouts.py`:
  - `test_fashion_scout_valid_body_hack`: validates valid body-hack fashion item passes with score >= 8.0 and hook angle containing "bụng" or "eo".
  - `test_fashion_scout_rejects_counterfeit_trademarks`: validates counterfeit brand items (Zara, Chanel, Gucci, Dior, LV, Hermes, Nike, Adidas, rep 1:1, super fake) are rejected with score == 0.0, passed_filter == False, and rejection_reason containing "trademark" or "policy".
  - `test_fashion_scout_subthreshold_rejection`: validates low-scoring items without fashion appeal score < 7.0 and passed_filter == False.
  - `test_homelife_scout_valid_labor_saving`: validates valid home utility item passes with score >= 8.5 and hook angle containing "3s" or "nhàn".
  - `test_homelife_scout_rejects_exaggerated_claims`: validates exaggerated claims (trị dứt điểm 100%, vĩnh viễn không bám bẩn/hỏng, thần dược) are rejected with score == 0.0, passed_filter == False, and rejection_reason containing "exaggerated" or "policy".
  - `test_homelife_scout_subthreshold_rejection`: validates mediocre items without visual contrast score < 7.0 and passed_filter == False.
  - `test_corrupted_inputs_handling`: validates None/empty/corrupted dictionary inputs do not crash and return valid SpecialistEvaluation instances with passed_filter == False.
  - `test_prompt_templates_contracts`: validates personas (Hoài My, Nam Minh), system prompts, and script guidelines exist and contain required keys.
- Run `pytest tests/test_specialist_scouts.py -v` and document that it FAILS (RED phase).

### Step 2: Implement Source Code (GREEN Phase)
1. `src/core/prompt_templates.py`:
   - System prompts, evaluation prompt templates, and script generation templates for Fashion (Hoài My - vi-VN-HoaiMyNeural) and Home Utilities (Nam Minh - vi-VN-NamMinhNeural).
   - Hook 3s formulas and anti-robotic tone rules.
2. `src/agents/fashion_scout.py`:
   - `@dataclass class SpecialistEvaluation`: `product_id: str`, `niche_id: str`, `passed_filter: bool`, `score: float`, `hook_angle: str`, `target_audience: str`, `pros: List[str]`, `cons: List[str]`, `viral_factor: str`, `rejection_reason: Optional[str] = None`.
   - `class FashionScoutAgent`:
     - `evaluate_product(self, item: Union[Dict[str, Any], ProductCandidate]) -> SpecialistEvaluation`:
       Uses `ToneValidator` to catch counterfeit brands -> rejects immediately.
       Calculates body-hack score (che bụng, giấu mỡ, chiết eo, tôn dáng, hack chiều cao, etc.).
       Generates natural hook angle containing "bụng" or "eo".
3. `src/agents/homelife_scout.py`:
   - `class HomeLifeScoutAgent`:
     - `evaluate_product(self, item: Union[Dict[str, Any], ProductCandidate]) -> SpecialistEvaluation`:
       Uses `ToneValidator` to catch exaggerated claims -> rejects immediately.
       Calculates labor-saving and Before/After 3s contrast score.
       Generates natural hook angle containing "3s" or "nhàn".
       Generates viral factor with "3s" and "vắt khô" (or cleaning contrast).
4. Export `FashionScoutAgent`, `HomeLifeScoutAgent`, `SpecialistEvaluation` in `src/agents/__init__.py`.

### Step 3: Verify All Test Suites (100% PASS)
Run and verify:
1. `pytest tests/test_specialist_scouts.py -v`
2. `pytest tests/e2e/ -v` (F08 and F09 will now run against production classes!)
3. `pytest tests/ -v` (full project test suite)
4. `python3 scripts/m1_stress_harness.py`
5. `python3 scripts/m2_stress_harness.py`
6. `python3 scripts/m2_kalodata_stress_harness.py`

Write your comprehensive `handoff.md` in `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/worker_m3_1/` with exact verbatim test outputs, and notify me with `send_message` when done.
