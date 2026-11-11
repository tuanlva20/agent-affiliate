## 2026-11-10T19:58:05Z
You are m8_explorer_2 (role: "CLI Runner & E2E Integration Explorer"), dispatched to investigate and formulate the architectural blueprint for Feature F29 (`main.py`), `README.md`, and integration tests in Milestone 8.

Working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m8_explorer_2/
Project root: /Users/tuanlva/Folder/workSpace/affiliate

## References
1. User Request: `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/ORIGINAL_REQUEST.md` (Requirement R7, R8 & Task 8)
2. Project Spec: `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/PROJECT.md`
3. Plan File: `/Users/tuanlva/Folder/workSpace/affiliate/docs/superpowers/plans/2026-11-10-autonomous-affiliate-system.md` (Task 8: Hermes Orchestrator & E2E Dry-run)
4. Config & Existing tests:
   - `config.yaml`, `.env.example`
   - `tests/e2e/test_tier1_features.py`, `tests/e2e/test_tier4_scenarios.py`

## Instructions
1. Investigate the CLI entrypoint design for `main.py`:
   - Argument parsing (`argparse` or `click`) supporting `--mode [bot|scout|dry-run|daemon]`, `--config`, `--niche`, `--dry-run-items`.
   - Mode `bot`: Starts `TelegramBot.start_polling()`.
   - Mode `scout`: Runs specialist scouting for pilot niches and prints/saves candidate summary.
   - Mode `dry-run`: Runs an end-to-end dry-run through `HermesOrchestrator` without real network calls or long sleeps, verifying every pipeline stage.
   - Mode `daemon`: Schedules periodic background tasks (hourly scout, batch studio rendering, publisher queue processor, comment scanner).
2. Design `README.md`:
   - System overview (AMAS v1.4.0 Autonomous Multi-Agent TikTok Affiliate System).
   - Prerequisites (Python 3.10+, PostgreSQL, Redis, FFmpeg, Playwright/AliasMode).
   - Installation & Setup (`pip install -r requirements.txt`, `.env` configuration from `.env.example`).
   - Running the system (CLI commands for all 4 modes).
   - Telegram bot commands and approval workflow.
   - Verification commands (`pytest tests/ -v`).
3. Formulate test architecture for:
   - `tests/test_hermes_flow.py`: Unit and state flow tests for StateGraph transitions.
   - `tests/test_e2e_dryrun.py`: Full dry-run execution tests validating that `main.py --mode dry-run` executes to completion with exit code 0 and verifies all pipeline artifacts.
4. Ensure 100% genuine logic with zero mock imports in `src/`.
5. Document the complete architectural blueprint in `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m8_explorer_2/handoff.md`.
6. Notify parent orchestrator via `send_message`.
