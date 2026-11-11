## 2026-11-10T09:20:56Z
You are m3_reviewer_2, reviewing Milestone 3 (Task 3: Specialist Scout Agents - Fashion & HomeLife, Prompt Templates) for domain criteria compliance, persona accuracy, and policy enforcement.

Working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m3_reviewer_2/
You MUST read:
- ORIGINAL_REQUEST.md at /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/ORIGINAL_REQUEST.md
- PROJECT.md at /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/PROJECT.md
- worker_m3_1 handoff at /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/worker_m3_1/handoff.md

Inspect:
- `src/agents/fashion_scout.py`
- `src/agents/homelife_scout.py`
- `src/core/prompt_templates.py`
- `tests/test_specialist_scouts.py`

Execute verification commands:
- `pytest tests/test_specialist_scouts.py -v`
- `pytest tests/e2e/ -v`
- `pytest tests/ -v`

Domain Criteria to Verify:
1. FashionScoutAgent:
   - Body-hack criteria (che bụng, giấu mỡ, chiết eo, tôn vòng 1/3, chân dài, tôn dáng) score >= 8.0.
   - Hook angles must naturally contain "bụng" or "eo".
   - Counterfeit brands (Zara, Chanel, Gucci, Dior, LV, Hermes, Nike, Adidas, rep 1:1, super fake) rejected with score=0.0 and rejection_reason containing "trademark" or "policy".
   - Persona Hoài My (vi-VN-HoaiMyNeural) warm, sisterly, anti-robotic.
2. HomeLifeScoutAgent:
   - Labor-saving utility and Before/After 3s contrast score >= 8.5.
   - Hook angles must naturally contain "3s" or "nhàn".
   - Viral factor must contain "3s" or "vắt khô".
   - Exaggerated claims (trị dứt điểm 100%, vĩnh viễn không bám bẩn/hỏng, thần dược) rejected with score=0.0 and rejection_reason containing "exaggerated" or "policy".
   - Persona Nam Minh (vi-VN-NamMinhNeural) practical, humorous, anti-robotic.

Write your review report to `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m3_reviewer_2/handoff.md` with an explicit verdict: `APPROVE` or `REQUEST_CHANGES`. Send a message back to the orchestrator with your verdict.
