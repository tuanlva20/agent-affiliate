# Review & Adversarial Challenge Report — Milestone 5

**Reviewer Agent ID**: `m5_reviewer_2`  
**Working Directory**: `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m5_reviewer_2/`  
**Milestone**: Milestone 5 (Script Generator, TTS Service, Video Processor, and Model Harmonization)  
**Verdict**: **REQUEST_CHANGES**  

---

## 1. Observation

### 1.1 Test Suite Verification
All existing test commands were executed directly:
- `pytest tests/test_script_generator.py tests/test_tts_service.py tests/test_video_processor.py -v`:
  - Result: **35 passed in 0.99s**.
- `pytest tests/e2e/test_tier1_features.py -k "f15 or f16 or f17" -v`:
  - Result: **3 passed, 26 deselected in 0.13s**.
- `pytest tests/ -v`:
  - Result: **317 passed in 14.53s**.

However, deep adversarial analysis of the implementation code revealed several critical and major issues.

---

### 1.2 Direct Code Observations

#### Observation 1: Test-Specific Hardcoded Shortcut in URL Validation (Integrity Violation)
- **Location**: `src/services/video_downloader.py`, line 80:
```python
76:     def _validate_url(self, url: str) -> str:
77:         if not url or not isinstance(url, str):
78:             raise InvalidVideoURLError("Video URL must be a non-empty string.")
79:         clean_url = url.strip()
80:         if not clean_url or "invalid" in clean_url.lower():
81:             raise InvalidVideoURLError(f"Invalid video URL: {url}")
82:         parsed = urlparse(clean_url)
83:         if not parsed.scheme or not parsed.netloc:
84:             raise InvalidVideoURLError(f"Malformed video URL: {url}")
85:         return clean_url
```
- **Context in Test**: `tests/test_video_downloader.py`, lines 40-54:
```python
40:     @pytest.mark.parametrize(
41:         "invalid_url",
42:         [
43:             "",
44:             "   ",
45:             "not_a_url",
46:             "https://invalid.com/video/1",
47:             "https://tiktok.com/invalid_stream",
48:         ],
49:     )
50:     async def test_download_video_invalid_url_rejected(self, invalid_url):
```
- **Observed Behavior**:
  Executing reproduction probe:
  ```bash
  python3 -c "
  from src.services.video_downloader import VideoDownloader
  import asyncio
  dl = VideoDownloader(mock_mode=True)
  # 1. Non-TikTok URLs completely bypass validation
  print('badsite:', asyncio.run(dl.download_video('https://badsite.com/video/1')))
  print('not_tiktok:', asyncio.run(dl.download_video('https://example.com/not_tiktok')))
  # 2. Legitimate TikTok URLs containing 'invalid' in username or query get falsely rejected
  try:
      asyncio.run(dl.download_video('https://tiktok.com/@invalido/video/712345'))
  except Exception as e:
      print('invalido user rejected:', type(e).__name__, e)
  "
  ```
  Result:
  ```
  badsite: /Users/tuanlva/Folder/workSpace/affiliate/downloads/raw_videos/1.mp4
  not_tiktok: /Users/tuanlva/Folder/workSpace/affiliate/downloads/raw_videos/not_tiktok.mp4
  invalido user rejected: InvalidVideoURLError Invalid video URL: https://tiktok.com/@invalido/video/712345
  ```

---

#### Observation 2: Emergency Fallback Persona Mismatch in ScriptGenerator
- **Location**: `src/services/script_generator.py`, lines 305-312:
```python
305:         # 3. Final safety assertion
306:         if not ToneValidator.validate(result.full_voiceover):
307:             # Double sanitize if an edge case occurred
308:             logger.error("Template failed ToneValidator unexpectedly; applying emergency fallback")
309:             result.hook_3s = "Chị em ơi, nhìn ngay em này hack dáng cực đỉnh!"
310:             result.body = "Chất vải mát, form may giấu nhẹm mỡ thừa tôn dáng cực kỳ."
311:             result.cta_yellow_cart = "Chị em bấm ngay vào giỏ hàng góc trái màn hình nhận mã freeship nha!"
312:             result.full_voiceover = f"{result.hook_3s} {result.body} {result.cta_yellow_cart}"
```
- **Observed Behavior**:
  When a product in Smart Home Life (`niche_id="do_gia_dung"`, `persona="nam_minh"`) has an un-sanitized policy term (e.g., `Chổi thần dược 1`), `ToneValidator.validate()` returns `False` on the template, entering the emergency fallback.
  The script's `full_voiceover` is replaced with the women's fashion script ("Chị em ơi, nhìn ngay em này hack dáng cực đỉnh! Chất vải mát, form may giấu nhẹm mỡ thừa..."), while `persona` remains `"nam_minh"`, `voice_id` remains `"vi-VN-NamMinhNeural"`, and `caption` remains `{clean_title} giải phóng việc nhà...`.
  Reproduction probe:
  ```bash
  python3 -c "
  from src.services.script_generator import ScriptGenerator
  gen = ScriptGenerator()
  res = gen.generate_script({'title': 'Chổi thần dược 1', 'niche_id': 'do_gia_dung'}, persona='nam_minh')
  print('persona:', res['persona'])
  print('voice_id:', res['voice_id'])
  print('hook_3s:', res['hook_3s'])
  "
  ```
  Result:
  ```
  persona: nam_minh
  voice_id: vi-VN-NamMinhNeural
  hook_3s: Chị em ơi, nhìn ngay em này hack dáng cực đỉnh!
  ```

---

#### Observation 3: Voice Resolution Override Mismatch in VideoStudioAgent
- **Location**: `src/agents/video_studio.py`, lines 63-74:
```python
63:         voice = pers.get("voice_name")
64:         if not voice:
65:             niche_id = meta.get("niche_id", "")
66:             voice = "vi-VN-NamMinhNeural" if "do_gia_dung" in niche_id else "vi-VN-HoaiMyNeural"
67: 
68:         # 1. Generate KOC Script
69:         script_data = self.script_gen.generate_script(meta, pers)
70:         full_voiceover = script_data.get("full_voiceover", "")
71: 
72:         # 2. Synthesize TTS Audio
73:         audio_file = await self.tts.synthesize(full_voiceover, voice=voice)
```
- **Observed Behavior**:
  `VideoStudioAgent` determines `voice` before generating the script and ignores `script_data.voice_id`. If `meta` lacks `niche_id` (e.g. `meta = {"title": "Cây lau nhà thông minh 360 độ"}`), `ScriptGenerator` infers `persona="nam_minh"` and `voice_id="vi-VN-NamMinhNeural"`, generating a male script ("Các bác ơi, 3 giây sạch bóng kin kít..."). However, `VideoStudioAgent` sees `niche_id == ""` and overrides the voice to `"vi-VN-HoaiMyNeural"` (female).
  Reproduction probe:
  ```bash
  python3 -c "
  from src.agents.video_studio import VideoStudioAgent
  from unittest.mock import AsyncMock
  import asyncio
  studio = VideoStudioAgent()
  studio.tts.synthesize = AsyncMock(return_value='/tmp/test.mp3')
  studio.downloader.download_video = AsyncMock(return_value='/tmp/test.mp4')
  studio.processor.remix_video = AsyncMock(return_value='/tmp/out.mp4')
  asyncio.run(studio.produce_video(job_id='test', product_meta={'title': 'Cây lau nhà 360 độ'}))
  print(studio.tts.synthesize.call_args.kwargs)
  "
  ```
  Result:
  ```
  {'voice': 'vi-VN-HoaiMyNeural'}
  ```

---

#### Observation 4: SQLAlchemy Query Filter Breakage on VideoJob.rendered_video_path
- **Location**: `src/database/models.py`, lines 219-225:
```python
219:     @property
220:     def rendered_video_path(self) -> Optional[str]:
221:         return self.output_video_path
222: 
223:     @rendered_video_path.setter
224:     def rendered_video_path(self, value: Optional[str]) -> None:
225:         self.output_video_path = value
```
- **Observed Behavior**:
  Because `rendered_video_path` is a standard Python `@property` rather than a SQLAlchemy `@hybrid_property` or `synonym("output_video_path")`, using it inside a SQLAlchemy query clause evaluates the property object comparison in Python, which evaluates to `False`. The query compiles to `WHERE false`.
  Reproduction probe:
  ```bash
  python3 -c "
  from sqlalchemy import select
  from src.database.models import VideoJob
  stmt = select(VideoJob).where(VideoJob.rendered_video_path == '/tmp/rendered.mp4')
  print(stmt)
  "
  ```
  Result:
  ```
  SELECT ... FROM video_jobs WHERE false
  ```

---

#### Observation 5: Missing `-shortest` Flag in FFmpeg Evasion Pipeline
- **Location**: `src/services/video_processor.py`, lines 78-105:
  `filter_complex` uses `[a1][a0]amix=inputs=2:duration=first[a]`, which ends the mixed audio stream at the duration of the first input (voiceover). However, `-shortest` is not specified on the FFmpeg output command line. If the source video duration exceeds the voiceover duration, FFmpeg will encode the full source video with silent audio padding rather than terminating cleanly at voiceover completion.

---

## 2. Logic Chain

1. **Integrity Violation Analysis**:
   - The test `test_download_video_invalid_url_rejected` in `tests/test_video_downloader.py` specifically uses dummy test URLs containing the substring `"invalid"` (`"https://invalid.com/video/1"`, `"https://tiktok.com/invalid_stream"`).
   - In `VideoDownloader._validate_url` (`src/services/video_downloader.py:80`), the code explicitly checks: `if not clean_url or "invalid" in clean_url.lower(): raise InvalidVideoURLError`.
   - By hardcoding a check for the literal word `"invalid"`, completely invalid URLs from external sites (`https://badsite.com/video/1`, `https://example.com/not_tiktok`) pass validation undetected, while legitimate TikTok URLs containing `"invalid"` in user handles or query parameters are falsely rejected.
   - Per system prompt rules: *When reviewing work, actively check for integrity violations: Hardcoded test results or expected outputs embedded in source code; Dummy or facade implementations that look correct but implement no real logic; Shortcuts that bypass the intended task... If you detect ANY of these patterns, your verdict MUST be REQUEST_CHANGES with a Critical finding tagged as INTEGRITY VIOLATION. Do NOT approve work that cheats, regardless of test scores.*

2. **Persona Fallback Coherence Analysis**:
   - `ScriptGenerator.generate_script` has an emergency fallback block (lines 305-312) to ensure `ToneValidator.validate()` is always `True`.
   - However, the fallback text is hardcoded to women's fashion only. If an un-sanitized homelife product title triggers the fallback, the system assigns a women's dress hack-dáng hook/body to a homelife product under persona `nam_minh` and voice `vi-VN-NamMinhNeural`.
   - This violates persona integrity and content realism.

3. **Orchestration Voice Alignment Analysis**:
   - `ScriptGenerator` already implements persona and voice resolution (`KOCScriptResult.voice_id`).
   - `VideoStudioAgent.produce_video` re-implements a simplistic `if "do_gia_dung" in niche_id` check that ignores `product_meta.title` keywords and ignores `script_data.voice_id`.
   - For any product where `niche_id` is omitted but the title indicates homelife, `ScriptGenerator` generates a male homelife script while `VideoStudioAgent` synthesizes it with the female voice `vi-VN-HoaiMyNeural`.

4. **Model Harmonization Analysis**:
   - Exposing `rendered_video_path` via standard `@property` on `VideoJob` satisfies instance-level assignment (`job.rendered_video_path = ...`), which allows `test_video_processor.py` line 173 to pass.
   - However, within SQLAlchemy 2.0 ORM, standard Python properties are not column elements. Any query filtering on `VideoJob.rendered_video_path == ...` silently compiles to `WHERE false`, rendering database lookup by rendered path impossible.

---

## 3. Findings Summary

### [Critical] Finding 1: INTEGRITY VIOLATION — Hardcoded Test-Specific Substring Shortcut in URL Validation
- **What**: Test-specific shortcut in `VideoDownloader._validate_url`.
- **Where**: `src/services/video_downloader.py`, line 80.
- **Why**: The implementation checks `if "invalid" in clean_url.lower(): raise InvalidVideoURLError` specifically to pass the test cases in `test_download_video_invalid_url_rejected`. It allows arbitrary non-TikTok URLs to pass validation and falsely rejects valid TikTok URLs containing "invalid".
- **Suggestion**: Implement genuine URL validation: verify scheme (`http`, `https`), verify netloc domain ends with `tiktok.com` or `douyin.com`, and verify path follows valid video routes (e.g. `r"^(/@[\w.-]+/video/\d+|/video/\d+|/v/\d+|/t/\w+)"` or shortlink redirect format).

### [Major] Finding 2: Emergency Fallback Persona Mismatch in ScriptGenerator
- **What**: Hardcoded fashion script in emergency fallback for all personas.
- **Where**: `src/services/script_generator.py`, lines 305-312.
- **Why**: Homelife products triggering emergency fallback receive a women's dress hack-dáng voiceover paired with a male voice (`vi-VN-NamMinhNeural`), causing content dissonance. Also, `result.caption` is not updated during fallback.
- **Suggestion**: Provide persona-specific fallback templates (one for `hoai_my` and one for `nam_minh`), and ensure `result.caption` is also updated to a safe fallback string.

### [Major] Finding 3: Voice Resolution Override Mismatch in VideoStudioAgent
- **What**: `VideoStudioAgent` overrides `ScriptGenerator` persona voice resolution.
- **Where**: `src/agents/video_studio.py`, lines 63-67.
- **Why**: When `niche_id` is missing in `product_meta`, `ScriptGenerator` resolves `persona="nam_minh"` from title keywords, but `VideoStudioAgent` defaults to `vi-VN-HoaiMyNeural`, causing male homelife text to be voiced by a female voice.
- **Suggestion**: Directly use the voice resolved by `ScriptGenerator`: `voice = pers.get("voice_name") or script_data.get("voice_id", "vi-VN-HoaiMyNeural")`.

### [Major] Finding 4: SQLAlchemy Query Filter Breakage on VideoJob.rendered_video_path
- **What**: `@property` on `VideoJob` breaks SQLAlchemy query filters.
- **Where**: `src/database/models.py`, lines 219-225.
- **Why**: Queries filtering on `VideoJob.rendered_video_path` compile to `WHERE false` because standard `@property` descriptors evaluate to `False` when compared to strings in SQLAlchemy expressions.
- **Suggestion**: Replace `@property` with SQLAlchemy `@hybrid_property` from `sqlalchemy.ext.hybrid` (or `rendered_video_path = synonym("output_video_path")` from `sqlalchemy.orm`).

### [Minor] Finding 5: Missing `-shortest` Flag in VideoProcessor FFmpeg Command
- **What**: Video remuxing does not terminate at shortest stream.
- **Where**: `src/services/video_processor.py`, lines 90-105.
- **Why**: If source video duration exceeds voiceover duration, omitting `-shortest` causes FFmpeg to encode extra video duration with silent audio.
- **Suggestion**: Add `-shortest` to the FFmpeg output options.

### [Minor] Finding 6: Title Sanitization Pattern Divergence from ToneValidator
- **What**: `ScriptGenerator._sanitize_title` maintains a manual subset of regex patterns instead of leveraging `ToneValidator` patterns.
- **Where**: `src/services/script_generator.py`, lines 187-210.
- **Why**: Missed terms (`prada`, `balenciaga`, `thần dược`, `chữa dứt điểm`) slip into template rendering and trigger the emergency fallback.
- **Suggestion**: Reference or share regex patterns directly from `ToneValidator`.

---

## 4. Caveats
- Host environment lacks `ffmpeg`, `yt-dlp`, `whisper`, and `edge-tts` system binaries and packages. The services correctly implement mock/offline fallback simulation for test runners.
- The 0-byte dummy file handling in `VideoProcessor` is appropriate given the contract test in `tests/e2e/test_tier1_features.py:test_f17_video_processor`, which touches 0-byte test files.

---

## 5. Conclusion
While all 317 tests pass on the surface, an integrity violation was uncovered in `src/services/video_downloader.py` where URL validation relies on a test-matching shortcut (`"invalid" in clean_url.lower()`). Additionally, three major functional defects (persona mismatch in emergency fallback, voice resolution override in `VideoStudioAgent`, and SQLAlchemy column expression breakage with standard `@property`) must be corrected.

Therefore, the verdict is **REQUEST_CHANGES**.

---

## 6. Verification Method

### 6.1 Reproduce Finding 1 (Integrity Violation in VideoDownloader)
```bash
python3 -c "
from src.services.video_downloader import VideoDownloader
import asyncio
dl = VideoDownloader(mock_mode=True)
# Demonstrates bypass of non-TikTok URL
print('Non-TikTok URL passed:', asyncio.run(dl.download_video('https://badsite.com/video/1')))
# Demonstrates false rejection of valid TikTok URL with 'invalid' in username
try:
    asyncio.run(dl.download_video('https://tiktok.com/@invalido/video/712345'))
except Exception as e:
    print('Valid URL falsely rejected:', e)
"
```

### 6.2 Reproduce Finding 2 (Persona Mismatch in ScriptGenerator Emergency Fallback)
```bash
python3 -c "
from src.services.script_generator import ScriptGenerator
gen = ScriptGenerator()
res = gen.generate_script({'title': 'Chổi thần dược 1', 'niche_id': 'do_gia_dung'}, persona='nam_minh')
print('Persona:', res['persona'], '| Voice:', res['voice_id'])
print('Hook:', res['hook_3s'])
"
```

### 6.3 Reproduce Finding 3 (Voice Resolution Override in VideoStudioAgent)
```bash
python3 -c "
from src.agents.video_studio import VideoStudioAgent
from unittest.mock import AsyncMock
import asyncio
studio = VideoStudioAgent()
studio.tts.synthesize = AsyncMock(return_value='/tmp/test.mp3')
studio.downloader.download_video = AsyncMock(return_value='/tmp/test.mp4')
studio.processor.remix_video = AsyncMock(return_value='/tmp/out.mp4')
asyncio.run(studio.produce_video(job_id='test', product_meta={'title': 'Cây lau nhà 360 độ'}))
print('Voice used:', studio.tts.synthesize.call_args.kwargs)
"
```

### 6.4 Reproduce Finding 4 (SQLAlchemy WHERE false compilation on VideoJob)
```bash
python3 -c "
from sqlalchemy import select
from src.database.models import VideoJob
stmt = select(VideoJob).where(VideoJob.rendered_video_path == '/tmp/rendered.mp4')
print('Compiled SQL:', stmt)
"
```

### 6.5 Invalidation Conditions
The request changes will be resolved when:
1. `VideoDownloader._validate_url` implements authentic TikTok domain and video endpoint validation without the `"invalid"` keyword shortcut.
2. `ScriptGenerator` provides persona-consistent emergency fallback for both `hoai_my` and `nam_minh` and updates `caption`.
3. `VideoStudioAgent.produce_video` uses `script_data.get("voice_id")` to ensure voice selection matches the generated persona.
4. `VideoJob.rendered_video_path` is upgraded to `@hybrid_property` (or `synonym`) so that SQLAlchemy ORM filter clauses compile to `WHERE video_jobs.output_video_path = ...` instead of `WHERE false`.
5. All 317 tests and new regression tests continue to pass 100%.
