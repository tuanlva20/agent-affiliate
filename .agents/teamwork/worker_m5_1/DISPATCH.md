## 2026-11-10T11:36:42Z
You are worker_m5_1, a teamwork_worker implementing Milestone 5 (Task 5: Video Remix & Content Engine) of the Autonomous TikTok Affiliate System (AMAS v1.4.0).

Working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/worker_m5_1/
Project root: /Users/tuanlva/Folder/workSpace/affiliate

### MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

### Context & Inputs
1. User Request: Read `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/ORIGINAL_REQUEST.md`
2. Architectural Blueprints from Milestone 5 Explorers:
   - `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m5_explorer_1/handoff.md` (F13 Video Downloader & F14 Audio Transcriber)
   - `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m5_explorer_2/handoff.md` (F15 KOC Natural Script Generator)
   - `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m5_explorer_3/handoff.md` (F16 TTS Service, F17 Video Processor, F18 Video Studio Agent, Database Harmonization)
3. Existing Codebase:
   - `src/core/tone_validator.py` (Must strictly satisfy `ToneValidator.validate()` and `ToneValidator.has_koc_markers()`)
   - `src/core/prompt_templates.py` (Hoài My & Nam Minh personas)
   - `src/database/models.py` (`VideoJob` model)
   - `tests/e2e/test_tier1_features.py` (Features F13, F14, F15, F16, F17, F18 contract tests)

### Exclusive Write Ownership
You own and may modify or create the following files ONLY:
- `src/services/video_downloader.py`
- `src/services/audio_transcriber.py`
- `src/services/script_generator.py`
- `src/services/tts_service.py`
- `src/services/video_processor.py`
- `src/agents/video_studio.py`
- `src/database/models.py` (Harmonization: add `@property def rendered_video_path` and `@rendered_video_path.setter` alias to `VideoJob`)
- `tests/test_script_generator.py`
- `tests/test_tts_service.py`
- `tests/test_video_processor.py`
- `tests/test_video_downloader.py` (optional extra coverage)
- `tests/test_audio_transcriber.py` (optional extra coverage)

### Implementation Requirements
1. **F13 Video Downloader (`src/services/video_downloader.py`)**:
   - Asynchronous `download_video(url, output_path=None, timeout=None) -> str`.
   - Dual-mode execution: use `yt-dlp` in background thread when available, or high-fidelity mock MP4 header generation when `mock_mode=True` or `yt_dlp is None`.
   - Validate URL: raise `InvalidVideoURLError(ValueError, VideoDownloaderError)` on empty, whitespace, or invalid URL (containing `"invalid"`).
   - Ensure output file exists and ends with `.mp4`.

2. **F14 Audio Transcriber (`src/services/audio_transcriber.py`)**:
   - Asynchronous `transcribe(media_path, language="vi") -> str`.
   - Support `extract_audio(video_path, output_wav_path=None) -> str` via FFmpeg to 16kHz mono WAV.
   - Dual-mode: if Whisper models (`faster-whisper` / `whisper`) are missing or `mock_mode=True` or 0-byte input, return realistic Vietnamese KOC transcript with length > 10.
   - Raise `MediaNotFoundError(FileNotFoundError)` if `not os.path.exists(media_path)`.

3. **F15 KOC Natural Script Generator (`src/services/script_generator.py`)**:
   - `generate_script(product_meta, persona) -> KOCScriptResult / Dict[str, Any]`.
   - Must return dict-accessible keys: `hook_3s`, `body`, `cta_yellow_cart`, `caption`, `full_voiceover`.
   - 3-stage formula:
     * Hook 3s (Hoài My: belly/waist body-hack + KOC address; Nam Minh: 3s labor-saving + KOC address).
     * Body: Problem/solution + authentic review with honest caveat.
     * CTA: Yellow cart navigation ("giỏ hàng góc trái", "góc trái màn hình", "giỏ hàng vàng").
     * Caption: TikTok hashtags.
   - Persona resolution: "hoai_my" (`vi-VN-HoaiMyNeural` for fashion) vs "nam_minh" (`vi-VN-NamMinhNeural` for homelife). Auto-infer from `niche_id` or product title.
   - Title sanitization: remove counterfeit marks (Zara, Chanel, rep 1:1) and exaggerated medical claims before generating.
   - Guaranteed `ToneValidator.validate(full_voiceover) is True` (zero robotic clichés, zero counterfeit, zero exaggerated claims) AND `ToneValidator.has_koc_markers(full_voiceover) is True`.

4. **F16 Natural TTS Service (`src/services/tts_service.py`)**:
   - Asynchronous `synthesize(text, voice=None, output_path=None, ...) -> str`.
   - Vietnamese edge-tts integration (`vi-VN-HoaiMyNeural`, `vi-VN-NamMinhNeural`) with retry logic and offline fallback MP3 generation (valid MP3 sync frame `b"\xff\xfb\x90\x00..."`).
   - Raise `ValueError` if `text` is empty or whitespace.
   - Provide `get_audio_duration(audio_path, text=None) -> float`.

5. **F17 FFmpeg Video Processor (`src/services/video_processor.py`)**:
   - Asynchronous `remix_video(video_path, audio_path, output_path, options=None) -> str`.
   - Copyright evasion filter graph: `hflip`, speed jitter 1.02–1.08x (`setpts` and `atempo`), `eq` color grading, 1–2% crop & scale to 1080:1920, audio voiceover dubbing & original audio ducking via `amix`.
   - Provide `build_ffmpeg_command(...) -> List[str]`.
   - Crucial test resilience: if FFmpeg binary is missing OR either input file is 0 bytes (`video.touch()`), operate in simulated mock mode by touching/creating output file. Raise `FileNotFoundError` if input paths do not exist.

6. **F18 Video Studio Agent (`src/agents/video_studio.py`)**:
   - Asynchronous `produce_video(job_id, product_meta, persona, source_video_url=None, db_session=None, options=None) -> str`.
   - Orchestrates: script generation -> TTS audio -> video download -> FFmpeg remix.
   - If `db_session` provided, update `VideoJob.status = "rendered"`, `output_video_path`, `rendered_video_path`, `audio_path`, `script`.
   - Output video path must include `job_id` and exist on disk.

7. **Database Model Harmonization (`src/database/models.py`)**:
   - In `VideoJob` class, add:
     ```python
     @property
     def rendered_video_path(self) -> Optional[str]:
         return self.output_video_path

     @rendered_video_path.setter
     def rendered_video_path(self, value: Optional[str]) -> None:
         self.output_video_path = value
     ```

### Strict TDD Execution Steps
1. **RED Phase**: Write comprehensive tests in `tests/test_script_generator.py`, `tests/test_tts_service.py`, `tests/test_video_processor.py`. Run pytest to observe RED failure.
2. **GREEN Phase**: Implement all services, agent, and model harmonization.
3. **VERIFY Phase**:
   - Run `pytest tests/test_script_generator.py tests/test_tts_service.py tests/test_video_processor.py -v`
   - Run `pytest tests/e2e/test_tier1_features.py -k "f13 or f14 or f15 or f16 or f17 or f18" -v`
   - Run `pytest tests/ -v` (Full test suite: must pass 100% with 0 regressions).
4. **Handoff**: Write `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/worker_m5_1/handoff.md` with:
   - Summary of implemented components and exact file paths
   - Test execution commands and verbatim outputs
   - Verification checklist

Send a message to orchestrator upon completion.
