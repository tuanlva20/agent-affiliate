## 2026-11-10T07:06:12Z
sender=f5177315-7404-4813-b8ba-56081885cdd4 priority=MESSAGE_PRIORITY_HIGH
content:
You are teamwork_spec_miner.
Your working directory is: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/spec_miner_survey_1/
You MUST read the authoritative user request at:
/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/ORIGINAL_REQUEST.md

Your mission in this Survey Phase is to thoroughly investigate the specification and implementation plan:
1. /Users/tuanlva/Folder/workSpace/affiliate/docs/superpowers/plans/2026-11-10-autonomous-affiliate-system.md
2. /Users/tuanlva/Folder/workSpace/affiliate/SYSTEM_SPEC.md

Extract and document:
- Complete feature inventory across all 8 tasks (Task 1 to Task 8)
- Exact component architecture, modules, classes, and function signatures required
- Acceptance criteria for each task
- Interface contracts between modules (e.g., Scout -> DB/Queue -> Telegram -> Video Processor -> Publisher -> Comment Agent -> Hermes)
- Concrete requirements for TDD, mock fixtures, and test files required
- Identify any potential ambiguity, edge cases, or strict constraints (e.g., ToneValidator anti-robotic rules, KOC persona, 3% typo, captcha alert)

Output requirements:
Write your comprehensive findings and feature catalog to `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/spec_miner_survey_1/handoff.md`.
Maintain your progress in `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/spec_miner_survey_1/progress.md`.
When finished, send a message to the orchestrator with the summary and report path.
