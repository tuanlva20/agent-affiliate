## 2026-11-10T09:21:10Z

You are m3_challenger_2, performing adversarial stress testing against Milestone 3 HomeLifeScoutAgent and related prompt templates.

Working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m3_challenger_2/
You MUST read:
- ORIGINAL_REQUEST.md at /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/ORIGINAL_REQUEST.md
- PROJECT.md at /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/PROJECT.md
- worker_m3_1 handoff at /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/worker_m3_1/handoff.md

Inspect:
- `src/agents/homelife_scout.py`
- `src/core/prompt_templates.py`
- `src/core/tone_validator.py`

Write a dedicated adversarial challenge script in `scripts/m3_homelife_adversarial_harness.py` that empirically tests:
1. Exaggerated claims bypass attempts: spacing, punctuation, synonyms, capitalization (e.g. "trị dứt điểm 100%", "vĩnh viễn ko bám bẩn", "thần_dược", "trị dứt điểm 100 %", "chữa khỏi 100%"). Verify 100% are rejected with score=0.0 and rejection_reason containing "exaggerated" or "policy".
2. Pricing sweet spot boundary tests: 0 VND, 1 VND, 99.999 VND, 100.000 VND, 300.000 VND, 300.001 VND, 10.000.000 VND, negative, NaN/Inf.
3. Score threshold boundary tests: products right below and above the 8.5 threshold. Ensure correct classification.
4. Hook angle and viral factor validation: verify "3s" or "nhàn" is always present in hook angle, and "3s" or "vắt khô" in viral factor. Verify tone passes `ToneValidator`.
5. Corrupted inputs and concurrency: test robustness on nulls, malformed dicts, and concurrent execution of 100+ evaluations.

Execute your harness, run existing tests (`pytest tests/test_specialist_scouts.py -v`, `pytest tests/e2e/ -v`), and report results.
Write your findings to `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m3_challenger_2/handoff.md` with an explicit verdict: `APPROVE` or `REQUEST_CHANGES`. Send a message back to the orchestrator with your verdict.
