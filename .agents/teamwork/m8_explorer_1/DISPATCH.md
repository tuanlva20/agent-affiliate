## 2026-11-10T19:57:57Z
Sender: f5177315-7404-4813-b8ba-56081885cdd4
Priority: MESSAGE_PRIORITY_HIGH

You are m8_explorer_1 (role: "Hermes StateGraph Explorer"), dispatched to investigate and formulate the architectural blueprint for Feature F28 (`src/agents/hermes_orchestrator.py`) in Milestone 8.

Working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m8_explorer_1/
Project root: /Users/tuanlva/Folder/workSpace/affiliate

## References
1. User Request: `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/ORIGINAL_REQUEST.md` (Requirement R7 & Task 8)
2. Project Spec: `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/PROJECT.md`
3. Plan File: `/Users/tuanlva/Folder/workSpace/affiliate/docs/superpowers/plans/2026-11-10-autonomous-affiliate-system.md` (Task 8: Hermes Orchestrator & E2E Dry-run)
4. Existing Agent Implementations:
   - `src/agents/base_scout.py`, `src/agents/fashion_scout.py`, `src/agents/homelife_scout.py`
   - `src/bot/telegram_bot.py`, `src/bot/handlers.py`
   - `src/agents/video_studio.py`
   - `src/agents/smart_publisher.py`
   - `src/agents/comment_agent.py`, `src/services/comment_scanner.py`
   - `src/database/models.py`, `src/core/config.py`

## Instructions
1. Investigate LangGraph availability and usage in the virtualenv (`langgraph`).
2. Design `HermesState` TypedDict:
   - State keys for channels, candidate products, approved products, video jobs, publish records, scanned comments, replies, errors, run_mode.
3. Design StateGraph node functions:
   - `scout_node`: Triggers specialist scouts for pilot niches (`thoi_trang_nu`, `do_gia_dung`), filters candidates.
   - `approval_node`: Routes candidates to Telegram bot or auto-approves in dry-run mode.
   - `studio_node`: Calls `VideoStudioAgent.produce_video` for approved items.
   - `publisher_node`: Checks channel status (`warming`, `ready_to_post`, `cooldown`, `captcha_blocked`), executes `SmartPublisher.publish_video`.
   - `engagement_node`: Scans comments and generates KOC conversion replies via `CommentAgent`.
4. Define conditional edges and termination conditions (e.g., empty candidates, captcha alert, cooldown, end of pipeline).
5. Ensure 100% genuine implementation with zero mock imports in `src/` (use pure-Python stubs or mock_mode flags if needed for offline hermetic testing).
6. Document the complete architectural blueprint in `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m8_explorer_1/handoff.md`.
7. Notify parent orchestrator via `send_message`.
