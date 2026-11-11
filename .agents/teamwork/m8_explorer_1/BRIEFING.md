# BRIEFING — 2026-11-10T20:07:30Z

## Mission
Investigate and formulate the architectural blueprint for Feature F28 (`src/agents/hermes_orchestrator.py`) in Milestone 8.

## 🔒 My Identity
- Archetype: explorer
- Roles: Hermes StateGraph Explorer
- Working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m8_explorer_1
- Original parent: f5177315-7404-4813-b8ba-56081885cdd4
- Milestone: Milestone 8 (Hermes Orchestrator & E2E Dry-run)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement in `src/` directly
- Pure genuine implementation — zero mock imports in `src/`
- All coordination via files + send_message back to parent

## Current Parent
- Conversation ID: f5177315-7404-4813-b8ba-56081885cdd4
- Updated: 2026-11-10T20:07:30Z

## Investigation State
- **Explored paths**:
  - `requirements.txt` & virtualenv package inspection
  - Installed and verified `langgraph>=0.2.14` (installed 1.2.20) and `langchain-core>=0.2.34` (installed 1.7.7)
  - Full test suite execution: verified 474/474 tests pass
  - `src/agents/base_scout.py`, `src/agents/fashion_scout.py`, `src/agents/homelife_scout.py`
  - `src/bot/telegram_bot.py`, `src/bot/handlers.py`, `src/bot/keyboards.py`
  - `src/agents/video_studio.py`
  - `src/agents/smart_publisher.py`
  - `src/agents/comment_agent.py`, `src/services/comment_scanner.py`
  - `src/database/models.py`, `src/core/config.py`, `tests/conftest.py`
  - `tests/e2e/test_tier1_features.py` (F28 & F29 assertions), `tests/e2e/conftest.py`
- **Key findings**:
  - LangGraph `StateGraph(TypedDict)` supports `async def` node functions invoked via `await graph.ainvoke(state)`.
  - To support existing Tier 1 e2e test assertions (`"scout_products" in graph`, `graph["scout_products"]`), `CompiledHermesGraph` wrapper wraps the compiled StateGraph and implements the dictionary topological mapping protocol alongside native `ainvoke`/`invoke`.
  - Channel lifecycle statuses (`warming`, `ready_to_post`, `cooldown`, `captcha_blocked`) must strictly control the publisher node.
  - Zero mock imports in `src/agents/hermes_orchestrator.py` must be maintained; pure Python fallback mechanisms and `mock_mode` flags handle offline execution cleanly.
- **Unexplored areas**: None. All dependencies, subsystem contracts, and test constraints have been mapped.

## Key Decisions Made
- Architecture blueprint formulated with 5 core asynchronous StateGraph nodes: `scout_node`, `approval_node`, `studio_node`, `publisher_node`, `engagement_node`.
- Defined conditional edges for no-candidates early stop, human-approval pause vs dry-run auto-advance, video render failure handling, and emergency captcha alarm abort.
- `run_pipeline_step(step_name, payload)` supports both atomic step testing and live CLI execution.

## Artifact Index
- DISPATCH.md — incoming dispatch instructions
- progress.md — liveness heartbeat and tracking
- BRIEFING.md — persistent working memory
- handoff.md — comprehensive architectural blueprint report
