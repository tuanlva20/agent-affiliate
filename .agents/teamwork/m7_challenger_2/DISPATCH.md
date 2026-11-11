## 2026-11-10T16:57:10Z
[Message] timestamp=2026-11-10T16:57:10Z sender=f5177315-7404-4813-b8ba-56081885cdd4 priority=MESSAGE_PRIORITY_HIGH content=You are m7_challenger_2 (role: "KOC Reply & Tone Adversarial Challenger"), dispatched to empirically stress test `CommentAgent.generate_reply` and `ToneValidator` compliance in Milestone 7.

Working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m7_challenger_2/
Project root: /Users/tuanlva/Folder/workSpace/affiliate

## References
1. `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/ORIGINAL_REQUEST.md`
2. Implementer report: `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/worker_m7_2/handoff.md`
3. Target components: `src/agents/comment_agent.py` and `src/core/tone_validator.py`

## Adversarial Testing Instructions
Write an executable standalone stress test script (e.g. `scripts/m7_adversarial_koc_reply_harness.py`) and execute it.
Cover:
1. Permutation Matrix:
   - Generate replies for 20+ diverse comments across both pilot niches (Fashion & HomeLife) and both personas (Hoài My, Nam Minh).
   - Test with dirty product titles containing brand obfuscations (`Z.a.r.a`, `c.h.a.n.e.l`, `r.e.p 1:1`, `super fake`, `t.u.ồ.n auth`) and exaggerated claims (`tốt nhất thị trường`, `vĩnh viễn không bám bẩn`).
   - Verify that 100% of generated replies PASS `ToneValidator.validate(reply)`.
2. Conversion Guardrails:
   - For `ASK_PRICE` and `ASK_MATERIAL_USAGE`, verify that generated replies include yellow cart navigation tokens ("giỏ hàng vàng", "góc trái", "freeship", "voucher").
   - For `COMPLAINT`, verify that replies do NOT push sales and instead offer sincere apology and direct messaging support ("nhắn tin", "hộp thư", "kiểm tra đơn").
3. Boundary & Malformed Inputs:
   - Empty comments, `None` product meta, missing prices, prices with non-numeric strings, weird characters.
4. Record your findings, test script path, and test execution results in `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m7_challenger_2/handoff.md`.
5. Explicit verdict: **APPROVE** or **REQUEST_CHANGES**.
6. Send completion message to parent orchestrator via `send_message`.
