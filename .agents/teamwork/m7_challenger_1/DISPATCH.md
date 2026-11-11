## 2026-11-10T16:57:03Z
You are m7_challenger_1 (role: "Scanner & Intent Adversarial Challenger"), dispatched to empirically stress test `CommentScanner` and `CommentAgent.classify_intent` in Milestone 7.

Working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m7_challenger_1/
Project root: /Users/tuanlva/Folder/workSpace/affiliate

## References
1. `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/ORIGINAL_REQUEST.md`
2. Implementer report: `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/worker_m7_2/handoff.md`
3. Target components: `src/services/comment_scanner.py` and `src/agents/comment_agent.py`

## Adversarial Testing Instructions
Write an executable standalone stress test script (e.g. `scripts/m7_adversarial_scanner_intent_harness.py`) and execute it.
Cover:
1. `CommentScanner` robustness:
   - Extreme inputs: empty strings, whitespace, unicode emojis, huge strings, non-string inputs.
   - Limit boundary testing: limit=0, limit=-10, limit=1000.
   - Concurrent scans and intra-batch duplicate comment insertions into SQLite database.
2. `CommentAgent.classify_intent` adversarial stress:
   - Slang & teen code: `bnhiu z sop`, `mấy xèng`, `rổ rá`, `vải gì dợ`, `m7 50kg vừa hơm`, `đắt wa ko giống video`, `shop lừa à`.
   - Homograph traps: test `bụng` vs `bung chỉ`, `lâu` vs `lau nhà`, `lụa` vs `lừa đảo`, `hong` vs `hỏng`.
   - Multi-intent priority: ensure comments with mixed signals (e.g. "áo rách rồi, giá thì đắt mà ship lâu quá") are ALWAYS classified as `COMPLAINT`.
   - False-positive guards: ensure `"đánh giá 5 sao"`, `"giá như biết sớm"`, `"cái giá treo quần áo này"` do not falsely trigger `ASK_PRICE`.
3. Assert 0 unhandled exceptions or crashes.
4. Record your findings, test script path, and test execution results in `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m7_challenger_1/handoff.md`.
5. Explicit verdict: **APPROVE** or **REQUEST_CHANGES**.
6. Send completion message to parent orchestrator via `send_message`.
