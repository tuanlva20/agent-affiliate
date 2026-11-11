## 2026-11-10T11:58:01Z
You are m5_remedy_explorer_3, a teamwork_explorer planning the remediation for VideoStudioAgent and Database Model Harmonization in Milestone 5 of AMAS v1.4.0.

Working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m5_remedy_explorer_3/
Project root: /Users/tuanlva/Folder/workSpace/affiliate

### Inputs
1. User Request: Read `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/ORIGINAL_REQUEST.md`
2. Reviewer 1 Findings: `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m5_reviewer_1/handoff.md` (Finding F-04)
3. Reviewer 2 Findings: `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m5_reviewer_2/handoff.md` (Findings 3 & 4)
4. Target Files:
   - `src/agents/video_studio.py`
   - `src/database/models.py`
   - `tests/test_database.py`
   - `tests/e2e/test_tier3_combinations.py`

### Investigation Scope & Objectives
1. **VideoStudioAgent Voice Routing & Code Cleanliness (`src/agents/video_studio.py`)**:
   - In `produce_video()`:
     * ScriptGenerator already determines the exact, certified persona voice (`script_data.voice_id` or `script_data["voice_id"]`).
     * `produce_video()` currently does a crude manual niche check in lines 57-61, ignoring `script_data.voice_id` and using female voice when `niche_id` is omitted in `product_meta` even for Nam Minh scripts.
     * Fix: Prioritize explicit `persona.get("voice_name")`, then `script_data.get("voice_id")` or `getattr(script_data, "voice_id", None)`, and only fallback to niche check if both are missing.
     * Clarify or integrate `self.transcriber`: allow optional `options.get("transcribe_source")` or add clear docstring explaining its role in competitor script extraction.
2. **SQLAlchemy ORM Synonym Harmonization (`src/database/models.py`)**:
   - `VideoJob.rendered_video_path` was implemented as a simple Python `@property`. While attribute assignment works, any SQLAlchemy ORM query such as `select(VideoJob).where(VideoJob.rendered_video_path == ...)` compiles to `WHERE false` or errors out because SQLAlchemy core does not map a bare Python property to a SQL column.
   - Replace the `@property` with `from sqlalchemy.orm import synonym`:
     ```python
     rendered_video_path = synonym("output_video_path")
     ```
   - Verify that:
     * `job.rendered_video_path = "path/to/video.mp4"` sets `job.output_video_path`.
     * `job.rendered_video_path` returns `job.output_video_path`.
     * `select(VideoJob).where(VideoJob.rendered_video_path == "path/to/video.mp4")` generates valid SQL referencing `output_video_path`.

### Deliverable
Formulate exact code replacement blocks and rationale in your handoff report:
`/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m5_remedy_explorer_3/handoff.md`.
Send a completion message to the orchestrator when done.
