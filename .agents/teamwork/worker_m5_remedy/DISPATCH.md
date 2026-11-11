## 2026-11-10T12:10:32Z
You are worker_m5_remedy, a teamwork_worker implementing the remediation fixes for Milestone 5 (Video Remix & Content Engine) of the Autonomous TikTok Affiliate System (AMAS v1.4.0).

Working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/worker_m5_remedy/
Project root: /Users/tuanlva/Folder/workSpace/affiliate

### MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

### Context & Inputs
1. User Request: Read `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/ORIGINAL_REQUEST.md`
2. Remediation Blueprints & Exact Code Blocks:
   - `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m5_remedy_explorer_1/handoff.md` (URL validation, FFmpeg failure raising, `mktemp` replacement)
   - `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m5_remedy_explorer_2/handoff.md` (ToneValidator accent patterns, leetspeak punctuation boundary, ScriptGenerator title sanitization, persona-aware emergency fallback, caption cleaning)
   - `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m5_remedy_explorer_3/handoff.md` (VideoStudioAgent voice routing, transcriber integration, SQLAlchemy ORM synonym)

### Exclusive Write Boundaries
You own and may modify the following files ONLY:
- `src/services/video_downloader.py`
- `src/services/video_processor.py`
- `src/services/audio_transcriber.py`
- `src/core/tone_validator.py`
- `src/services/script_generator.py`
- `src/agents/video_studio.py`
- `src/database/models.py`
- `tests/test_video_downloader.py`
- `tests/test_video_processor.py`
- `tests/test_audio_transcriber.py`
- `tests/test_database.py`

### Detailed Remediation Tasks
1. `src/services/video_downloader.py` & `tests/test_video_downloader.py`:
   - Replace `"invalid" in clean_url.lower()` shortcut with genuine `ALLOWED_DOMAINS` (`tiktok.com`, `douyin.com`, `vt.tiktok.com`, `vm.tiktok.com`, etc.) and path patterns (`/(?:video|v)/(\d+)` for standard hosts, `/([a-zA-Z0-9_-]+)/?` for shortlinks).
   - Ensure URLs like `https://www.tiktok.com/@invalid_user/video/712345` are accepted, while unsupported domains like `https://malicious.com/exploit.exe` or `https://tiktok.com.attacker.com/video/1` are rejected with `InvalidVideoURLError`.
   - Update `tests/test_video_downloader.py` with expanded test cases from explorer 1 handoff.

2. `src/services/video_processor.py` & `src/services/audio_transcriber.py`:
   - In `src/services/video_processor.py`: define `VideoProcessingError(Exception)`. In `remix_video`: when `proc.returncode != 0`, raise `VideoProcessingError` instead of silently touching empty file and returning success. Maintain simulated mock mode for 0-byte test dummy files.
   - Replace deprecated `tempfile.mktemp()` in `audio_transcriber.py` (line 106) and `video_processor.py` (line 153) with atomic `tempfile.NamedTemporaryFile(suffix=..., delete=False)` with immediate file descriptor closure.
   - Add unit tests in `tests/test_video_processor.py` and `tests/test_audio_transcriber.py` from explorer 1 handoff.

3. `src/core/tone_validator.py` & `src/services/script_generator.py`:
   - In `src/core/tone_validator.py`:
     * Harmonize `COUNTERFEIT_PATTERNS` so that canonical text checks catch both accented and unaccented canonical forms: `r"\b(like|chuan|chuẩn|tuon|tuồn)[\.\s\-_]*auth\b"` and `(r"(?<!mon )(?<!món )(?<!thit )(?<!thịt )\b(nhai|nhái)\b", "nhái")`.
     * Refine leetspeak `!` replacement in `canonicalize_brand_text` to `re.sub(r"!(?=[a-z0-9])", "i", tw)` so that sentence-ending `nha!` is not converted to `nhai`.
   - In `src/services/script_generator.py`:
     * Expand `_sanitize_title` to strip dot-separated trademarks, exaggerated/medical claims, and robotic clichés per explorer 2 handoff.
     * Upgrade emergency fallback to be persona-aware: if `persona == "nam_minh"`, use certified HomeLife lines (`voice_id="vi-VN-NamMinhNeural"`, male markers `các bác`, `3s`, `nhàn`), and if `persona == "hoai_my"`, use certified Fashion lines.
     * Reset `result.caption` to clean text in fallback to prevent token leakage.

4. `src/agents/video_studio.py` & `src/database/models.py`:
   - In `src/agents/video_studio.py`:
     * Prioritize voice from `script_data.voice_id` (or `script_data.get("voice_id")`) after script generation so that homelife products always use `vi-VN-NamMinhNeural` even when `niche_id` is omitted in `product_meta`.
     * Clean up and document `self.transcriber`, executing it when `options and options.get("transcribe_source")`.
   - In `src/database/models.py`:
     * Import `synonym` from `sqlalchemy.orm`.
     * Replace `@property rendered_video_path` on `VideoJob` with `rendered_video_path = synonym("output_video_path")`.
   - Add unit tests in `tests/test_database.py` and `tests/test_video_processor.py` per explorer 3 handoff.

### Verification Commands
1. `python3 scripts/m5_adversarial_script_harness.py` -> Must pass 737/737 (100%, 0 failures).
2. `python3 scripts/m5_adversarial_media_harness.py` -> Must pass 650/650 (100%, 0 failures).
3. `pytest tests/test_video_downloader.py tests/test_audio_transcriber.py tests/test_video_processor.py tests/test_script_generator.py tests/test_tts_service.py tests/test_database.py -v`
4. `pytest tests/e2e/test_tier1_features.py -k "f13 or f14 or f15 or f16 or f17 or f18" -v`
5. `pytest tests/ -v` (Full test suite: must pass 100% with 0 regressions).
