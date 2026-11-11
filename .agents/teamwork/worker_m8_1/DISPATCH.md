## 2026-11-10T20:08:35Z
You are worker_m8_1 (role: "Milestone 8 TDD Implementer"), dispatched to implement Task 8: Hermes Orchestrator, CLI Runner, README.md, and E2E Dry-run according to strict TDD.

Working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/worker_m8_1/
Project root: /Users/tuanlva/Folder/workSpace/affiliate

## References
1. User Request: `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/ORIGINAL_REQUEST.md` (Requirement R7, R8 & Task 8)
2. Project Spec: `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/PROJECT.md`
3. Plan File: `/Users/tuanlva/Folder/workSpace/affiliate/docs/superpowers/plans/2026-11-10-autonomous-affiliate-system.md` (Task 8: Hermes Orchestrator & E2E Dry-run)
4. Architectural Blueprints:
   - StateGraph & HermesOrchestrator Blueprint: `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m8_explorer_1/handoff.md`
   - CLI Runner (`main.py`), README.md, and Integration Test Blueprint: `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m8_explorer_2/handoff.md`

## Files You Own Exclusively
- `src/agents/hermes_orchestrator.py`
- `src/agents/__init__.py`
- `main.py`
- `README.md`
- `.env.example`
- `tests/test_hermes_flow.py`
- `tests/test_e2e_dryrun.py`

## MANDATORY INTEGRITY WARNING
> DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
> ZERO MOCK IN SRC/: `unittest.mock` (`MagicMock`, `AsyncMock`, `patch`) must NEVER be imported or used anywhere inside `src/` or `main.py`. Genuine dependency injection and pure-Python stubs only.

## Step-by-Step TDD Instructions
1. **Write Tests First**:
   - Create `tests/test_hermes_flow.py` covering StateGraph compilation, `CompiledHermesGraph` dual execution & dict topological mapping (`"scout_products" in graph`, `"specialist_eval" in graph["scout_products"]`), `HermesState` schema, and `run_pipeline_step` for all steps (`scout`, `evaluate`, `render`, `publish`, `reply`).
   - Create `tests/test_e2e_dryrun.py` covering `run_cli` exit codes (0 for `--help`, `dry-run`, `bot`, `scout`, `daemon`; 1 for invalid mode; 2 for missing argument), CLI subprocess execution of `main.py`, and end-to-end dry-run execution.
2. **Run Tests to Verify Failure**:
   - `pytest tests/test_hermes_flow.py tests/test_e2e_dryrun.py` (confirm expected failure before code creation).
3. **Implement Components**:
   - Implement `src/agents/hermes_orchestrator.py` with `HermesState` TypedDict, `CompiledHermesGraph` wrapper, `HermesOrchestrator` with StateGraph compilation, the 5 async node functions (`_scout_node`, `_approval_node`, `_studio_node`, `_publisher_node`, `_engagement_node`), conditional routing, `run_pipeline`, and `run_pipeline_step`.
   - Update `src/agents/__init__.py` to re-export `HermesOrchestrator`, `HermesState`, `CompiledHermesGraph`.
   - Implement `main.py` with `AMASArgumentParser`, `run_cli`, `main()`, and execution handlers for the 4 modes (`dry-run`, `scout`, `bot`, `daemon`), supporting alias `TelegramBot = TelegramCommandCenter`.
   - Create `README.md` and `.env.example` according to the blueprints in `m8_explorer_2/handoff.md`.
4. **Run Verification**:
   - `pytest tests/test_hermes_flow.py -v`
   - `pytest tests/test_e2e_dryrun.py -v`
   - `python3 main.py --help`
   - `python3 main.py --mode dry-run`
   - Static check: verify zero `unittest.mock` imports in `src/` and `main.py`.
   - Full regression suite: `pytest tests/ -v` (confirm 100% passing across all existing and new tests).
5. **Report & Handoff**:
   - Write comprehensive report to `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/worker_m8_1/handoff.md`.
   - Send completion message to parent orchestrator via `send_message`. (Remember: do NOT run git commands per user instruction).
