## 2026-11-10T17:14:48Z
You are worker_m7_remedy (role: "Milestone 7 Remediation Implementer"), dispatched to implement the verified regex remediation in `src/agents/comment_agent.py` to resolve all 9 empirical failures reported by `m7_challenger_1`.

Working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/worker_m7_remedy/
Project root: /Users/tuanlva/Folder/workSpace/affiliate

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
CRITICAL INTEGRITY CONSTRAINTS:
- ZERO imports of `unittest.mock` (MagicMock, AsyncMock, patch) in any file under `src/`! Mocking libraries belong exclusively in `tests/`.
- NO dummy bypass flags, whitelist strings, or fake sleep shortcuts in `src/`.
- Full authentic logic must be implemented in all components.

## User Constraints
- Do NOT run git commands (không cần chạy lệnh git).

## File Write Boundaries
You have exclusive write ownership over:
- `src/agents/comment_agent.py`
- `tests/test_comment_agent.py` (if adding regression tests)

## Instructions & Blueprint
Read the exact remediation blueprint and patch at:
`/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m7_remedy_explorer_1/handoff.md`
and `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m7_remedy_explorer_1/remedy_comment_agent.patch`.

Key updates to `src/agents/comment_agent.py`:
1. In `raw_complaints`, add fabric defect/quality patterns and price dissatisfaction patterns:
   - `r"\b(vải|chất|chất vải|hàng|đồ|áo|váy)\s*(xấu|quá xấu|xấu quá|đểu|dỏm|tệ|kém|mỏng tang|mỏng dính)\b"`
   - `r"\b(quá xấu|xấu quá|xấu tệ|xấu thật|như giẻ lau|như giẻ rách|giẻ rách|mỏng tang|mỏng dính)\b"`
   - `r"\b(giá|gia)\s*(quá\s+)?(đắt|chát)\b|\b(đắt|mắc)\s*(quá|qua|wa|thế|kinh|ghê|vãi)\b"`
2. In `_init_intent_patterns()`, protect unaccented homographs for `mac` (mặc vs mắc) and `dat` (đặt vs đắt):
   `unacc_p = unacc_p.replace(r"\b(dat|mac)\s*", r"\bgia\s*(dat|mac)\s*")`
3. In `raw_prices`:
   - Support `r"\brổ\s+(giá|rá)\b"`
   - Support `r"\b(giá|nhiêu|nhiu|bn|bnh|bnhieu|bnhiu)\s*(\?|\!|\.|\s)*$"`
   - Support `r"^\s*(giá|nhiêu|nhiu|bao nhiêu|bao tiền|bn|bnh|bnhieu|bnhiu)\s*(\?|\!|\.|\s)*$"`
   - Support `r"\b(nhiêu|nhiu|bnhiu|bnhieu|bao nhiêu)\s+(ạ|thế|vậy|shop|sop|v|z|hả)\b"`
   - Support `r"\bbn\s+(thế|vậy|v|z|shop|sop|hả)\b"`
4. In `_re_explicit_q`, add `bnh`, `bnhieu`, `bnhiu`.

## Verification Commands
1. Run the challenger harness:
   `python3 scripts/m7_adversarial_scanner_intent_harness.py`
   Ensure 77/77 PASS (100%), exit code 0.
2. Run the KOC reply harness:
   `python3 scripts/m7_adversarial_koc_reply_harness.py`
   Ensure 1143/1143 PASS (100%), exit code 0.
3. Run Milestone 7 test suite:
   `pytest tests/test_comment_agent.py -v`
   Ensure 100% PASS.
4. Run full repository regression test suite:
   `pytest tests/ -v`
   Ensure all tests PASS (zero regressions).
5. Verify static integrity: zero `unittest.mock` imports in `src/`.
