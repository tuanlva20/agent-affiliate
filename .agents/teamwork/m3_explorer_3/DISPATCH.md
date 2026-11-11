## 2026-11-10T09:01:47Z
From: f5177315-7404-4813-b8ba-56081885cdd4
Priority: MESSAGE_PRIORITY_HIGH

You are m3_explorer_3, an exploration agent for Milestone 3 (Task 3: Specialist Scout Agents - Prompt Templates & Test Suite).

Working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m3_explorer_3/
Maintain progress.md in your working directory.
Original request file: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/ORIGINAL_REQUEST.md
Project plan: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/PROJECT.md
System spec: /Users/tuanlva/Folder/workSpace/affiliate/SYSTEM_SPEC.md
Plan doc: /Users/tuanlva/Folder/workSpace/affiliate/docs/superpowers/plans/2026-11-10-autonomous-affiliate-system.md

Scope: `src/core/prompt_templates.py`, `SpecialistEvaluation` dataclass in `src/agents/fashion_scout.py` / `src/agents/homelife_scout.py`, and unit test suite `tests/test_specialist_scouts.py`.

Tasks:
1. Design `src/core/prompt_templates.py`:
   - System prompts and structured JSON templates for Gemini / LLM evaluators.
   - Fashion KOC persona (Hoài My) & HomeLife KOC persona (Nam Minh).
   - Hook 3s prompt guidelines and anti-robotic tone rules.
2. Align `SpecialistEvaluation` dataclass:
   - `product_id: str`, `niche_id: str`, `passed_filter: bool`, `score: float`, `hook_angle: str`, `target_audience: str`, `pros: List[str]`, `cons: List[str]`, `viral_factor: str`, `rejection_reason: Optional[str] = None`.
3. Design unit test suite `tests/test_specialist_scouts.py`:
   - Valid fashion body-hack product evaluation (score >= 8.0, hook with "bụng" / "eo").
   - Counterfeit fashion rejection (score = 0.0, passed_filter = False, rejection_reason contains "trademark" or "policy").
   - Valid homelife labor-saving product evaluation (score >= 8.5, hook with "3s" / "nhàn").
   - Exaggerated homelife claim rejection (score = 0.0, passed_filter = False, rejection_reason contains "exaggerated" or "policy").
   - Low-scoring mediocre products (score < 7.0, passed_filter = False).
   - Corrupted/empty product inputs handling.

Write your report to `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m3_explorer_3/handoff.md` and send a message when done. Do NOT modify source code.
