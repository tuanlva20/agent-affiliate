# BRIEFING — 2026-11-10T20:05:00Z

## Mission
Investigate and formulate the architectural blueprint for Feature F29 (`main.py`), `README.md`, and integration tests (`tests/test_hermes_flow.py`, `tests/test_e2e_dryrun.py`) in Milestone 8.

## 🔒 My Identity
- Archetype: explorer
- Roles: CLI Runner & E2E Integration Explorer
- Working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m8_explorer_2
- Original parent: f5177315-7404-4813-b8ba-56081885cdd4
- Milestone: Milestone 8 (Hermes Orchestrator & E2E Dry-run)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement production files directly
- 100% genuine logic with zero mock imports in `src/` and `main.py`
- All architectural proposals must align with existing project conventions, config, and state graph
- Output complete blueprint to handoff.md and notify parent

## Current Parent
- Conversation ID: f5177315-7404-4813-b8ba-56081885cdd4
- Updated: 2026-11-10T20:05:00Z

## Investigation State
- **Explored paths**:
  - `ORIGINAL_REQUEST.md`, `PROJECT.md`, `docs/superpowers/plans/2026-11-10-autonomous-affiliate-system.md`
  - `config.yaml`, `requirements.txt`
  - Existing codebase: `src/core/config.py`, `src/bot/telegram_bot.py`, `src/bot/handlers.py`, `src/agents/base_scout.py`, `src/agents/fashion_scout.py`, `src/agents/video_studio.py`, `src/agents/smart_publisher.py`, `src/agents/comment_agent.py`
  - Existing tests: `tests/e2e/test_tier1_features.py`, `tests/e2e/test_tier4_scenarios.py`, `tests/e2e/conftest.py`, `tests/conftest.py`
  - Peer agent: `m8_explorer_1` (Hermes StateGraph Explorer)
- **Key findings**:
  - `main.py` currently does not exist. Needs `run_cli` supporting 4 modes (`bot`, `scout`, `dry-run`, `daemon`).
  - Exit code contract: `--help` -> 0, valid modes -> 0, missing argument -> 2, invalid choice -> 1.
  - `README.md` and `.env.example` need to be authored with full specifications.
  - Existing test suite (474 tests) passes 100% in 21s.
  - Zero mock imports in `src/` verified.
  - `start_polling` method on `TelegramCommandCenter` or `TelegramBot` alias needed for clean bot runner.
  - Integration tests `tests/test_hermes_flow.py` and `tests/test_e2e_dryrun.py` formulated.
- **Unexplored areas**: None remaining for blueprint formulation.

## Key Decisions Made
- `main.py` CLI runner designed with dual invocation support: as Python module function `run_cli(args: List[str]) -> int` returning exit codes, and as script `main()` calling `sys.exit(run_cli())`.
- Full 5-component handoff report prepared in `handoff.md`.

## Artifact Index
- DISPATCH.md — Received dispatch instructions
- BRIEFING.md — Situational awareness and working memory
- progress.md — Heartbeat and milestone progress log
- handoff.md — Final 5-component architectural blueprint
