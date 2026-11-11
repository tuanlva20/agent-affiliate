# BRIEFING — 2026-11-10T12:05:30Z

## Mission
Investigate and formulate exact remediation code blocks for VideoStudioAgent voice routing / cleanliness and SQLAlchemy ORM synonym harmonization for VideoJob.rendered_video_path.

## 🔒 My Identity
- Archetype: explorer
- Roles: investigator, synthesizer
- Working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m5_remedy_explorer_3/
- Original parent: f5177315-7404-4813-b8ba-56081885cdd4
- Milestone: Milestone 5 Remediation

## 🔒 Key Constraints
- Read-only investigation — do NOT implement in source code
- Formulate exact code replacement blocks, rationale, verification method in handoff report

## Current Parent
- Conversation ID: f5177315-7404-4813-b8ba-56081885cdd4
- Updated: 2026-11-10T12:05:30Z

## Investigation State
- **Explored paths**:
  * `src/agents/video_studio.py` (lines 1-101)
  * `src/database/models.py` (lines 1-60, 170-250)
  * `src/services/script_generator.py` (lines 1-60, 100-186)
  * `src/services/audio_transcriber.py` (lines 1-160)
  * `tests/test_database.py` (lines 1-271)
  * `tests/test_video_processor.py` (lines 110-176)
  * `tests/e2e/test_tier3_combinations.py` (lines 1-45, 120-170)
  * `tests/e2e/conftest.py` (lines 1-60, 175-210, 635-660)
  * `scripts/m5_adversarial_media_harness.py` (lines 640-765)
- **Key findings**:
  1. `VideoStudioAgent.produce_video()` pre-determines voice before calling `generate_script()`, completely ignoring `script_data.voice_id`. If `niche_id` is missing in `product_meta` (even when title is clearly homelife and ScriptGenerator picks Nam Minh), VideoStudioAgent defaults to Hoài My.
  2. `VideoStudioAgent` injected `self.transcriber` is unreferenced in `produce_video()`, causing dead code ambiguity. It should be activated when `options.get("transcribe_source")` is present and clearly documented.
  3. `VideoJob.rendered_video_path` was written as a bare Python `@property`, causing `select(VideoJob).where(VideoJob.rendered_video_path == ...)` to compile to `WHERE false`. Replacing with `synonym("output_video_path")` resolves attribute read/write, constructor kwargs, and SQL compilation cleanly.
- **Unexplored areas**: None within this sub-task scope.

## Key Decisions Made
- Retain read-only stance; construct detailed `.patch` and exact replacement chunks for `src/agents/video_studio.py`, `src/database/models.py`, `tests/test_database.py`, and `tests/test_video_processor.py`.
- Ensure voice resolution hierarchy: `pers.get("voice_name") or pers.get("voice_id")` -> `script_data.voice_id` -> fallback niche check -> default `"vi-VN-HoaiMyNeural"`.
- Support optional competitor transcription via `options.get("transcribe_source")` with exception isolation so primary remixing never fails.

## Artifact Index
- `handoff.md` — Complete 5-component handoff report with exact replacement blocks
- `progress.md` — Heartbeat and status tracking
- `DISPATCH.md` — Received dispatch records
