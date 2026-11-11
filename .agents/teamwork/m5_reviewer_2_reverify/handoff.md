# Review & Re-verification Report — Milestone 5 Remediation

**Reviewer Agent ID**: `m5_reviewer_2_reverify`  
**Roles**: `reviewer`, `critic`  
**Working Directory**: `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m5_reviewer_2_reverify/`  
**Target Milestone**: Milestone 5 (Video Remix & Content Engine) Remediation Re-verification  
**Prior Review**: `m5_reviewer_2` (Verdict: `REQUEST_CHANGES`)  
**Remediation Worker**: `worker_m5_remedy` (Hard Handoff: Task Complete)  
**Final Verdict**: **APPROVE**  

---

## 1. Observation

### 1.1 Direct Code Inspections

#### 1. ToneValidator Accent & False Positive Protection
- **File**: `src/core/tone_validator.py`
- **Lines 53–56 (`COUNTERFEIT_PATTERNS`)**:
  ```python
  (r"(?<!mon )(?<!món )(?<!thit )(?<!thịt )\b(nhai|nhái)\b", "nhái"),
  (r"\b(like|chuan|chuẩn|tuon|tuồn)[\.\s\-_]*auth\b", "like/chuẩn/tuồn auth"),
  (r"\b(hàng|hang)[\.\s\-_]*(tuồn|tuon)\b", "hàng tuồn"),
  (r"\bvnxk[\.\s\-_]*(chuẩn|chuan)[\.\s\-_]*auth\b", "vnxk chuẩn auth"),
  ```
  - Directly matches both accented and unaccented canonical forms for `tuồn`/`tuon`, `chuẩn`/`chuan`, and `nhái`/`nhai`.
  - Negative lookbehinds `(?<!mon )(?<!món )(?<!thit )(?<!thịt )` protect culinary/food terms in both accented and unaccented forms.
- **Line 159 (`canonicalize_brand_text`)**:
  ```python
  tw = re.sub(r"!(?=[a-z0-9])", "i", tw)
  ```
  - Replaces `!` with `i` ONLY when immediately followed by an alphanumeric character (e.g., `d!or` -> `dior`, `l!ke` -> `like`).
  - Sentence-ending conversational particles such as `Chị em mua ngay nha!` remain `nha!` and do NOT turn into `nhai`.

#### 2. ScriptGenerator Title Sanitization & Persona Emergency Fallback
- **File**: `src/services/script_generator.py`
- **Lines 184–236 (`BANNED_TITLE_PATTERNS` and `_sanitize_title`)**:
  - Covers dot-separated trademarks: `N.i.k.e`, `A.d.i.d.a.s`, `Z.a.r.a`, `C.h.a.n.e.l`, `r.e.p 1:1`, `s.u.p.e.r.f.a.k.e`, `t.u.ồ.n a.u.t.h`, `v.n.x.k chuẩn auth`.
  - Covers exaggerated claims: `trị dứt điểm 100%`, `chữa khỏi`, `cam kết chữa khỏi`, `thần dược`, `đặc trị`, `vĩnh viễn không hỏng`, `100% không bao giờ hỏng`, `vĩnh viễn không bám bẩn`.
  - Covers robotic greetings: `chào mừng bạn/quý khách đến với`, `kính chào quý khách`, `sản phẩm hoàn hảo`, `đáp ứng mọi nhu cầu`, `hãy nhanh tay sở hữu`, `rất hân hạnh được phục vụ`.
- **Lines 326–345 (`generate_script` emergency fallback)**:
  ```python
  if not ToneValidator.validate(result.full_voiceover):
      logger.error("Template failed ToneValidator unexpectedly; applying emergency fallback")
      if persona_name == "nam_minh":
          result.hook_3s = "Các bác ơi, từ ngày tậu em này việc nhà nhàn hẳn, 3s là nhà sạch bóng!"
          result.body = "Cơ chế thông minh lau sạch kin kít không tốn một giọt mồ hôi, giải phóng sức lao động cực kỳ nhàn luôn."
          result.cta_yellow_cart = "Các bác bấm ngay vào giỏ hàng góc trái màn hình nhận mã ưu đãi nha!"
          result.voice_id = "vi-VN-NamMinhNeural"
          result.caption = "Giải phóng việc nhà nhàn tênh 3s sạch bóng #dogiadung #giadungthongminh #xuhuong #koc"
      else:
          result.hook_3s = "Chị em ơi, nhìn ngay em này hack dáng cực đỉnh!"
          result.body = "Chất vải mát, form may giấu nhẹm mỡ thừa tôn dáng cực kỳ."
          result.cta_yellow_cart = "Chị em bấm ngay vào giỏ hàng góc trái màn hình nhận mã freeship nha!"
          result.voice_id = "vi-VN-HoaiMyNeural"
          result.caption = "Tôn dáng cực đỉnh hack dáng che khuyết điểm cho chị em #outfit #thoitrangnu #xuhuong"
      result.persona = persona_name
      result.full_voiceover = f"{result.hook_3s} {result.body} {result.cta_yellow_cart}"
  ```
  - For `nam_minh`: Emits certified HomeLife lines (`voice_id="vi-VN-NamMinhNeural"`, male markers `các bác`, `3s`, `nhàn`, `lau sạch kin kít`), with zero female fashion markers (`chị em`, `hack dáng`, `giấu mỡ`).
  - `result.caption` is explicitly replaced with clean pre-certified text, preventing any unsanitized policy tokens from leaking into video captions.

#### 3. VideoStudioAgent Voice Routing Priority
- **File**: `src/agents/video_studio.py`
- **Lines 86–104 (`produce_video`)**:
  ```python
  # 1. Generate KOC Script first so persona and certified voice are resolved
  script_data = self.script_gen.generate_script(meta, pers)
  if hasattr(script_data, "get"):
      full_voiceover = script_data.get("full_voiceover", "")
      script_voice = script_data.get("voice_id")
  else:
      full_voiceover = getattr(script_data, "full_voiceover", "")
      script_voice = getattr(script_data, "voice_id", None)

  # Determine voice name: explicit persona voice -> script_data voice_id -> niche check fallback
  voice = None
  if isinstance(pers, dict):
      voice = pers.get("voice_name") or pers.get("voice_id")
  if not voice:
      voice = script_voice
  if not voice:
      niche_id = str(meta.get("niche_id", "") if isinstance(meta, dict) else getattr(meta, "niche_id", ""))
      voice = "vi-VN-NamMinhNeural" if "do_gia_dung" in niche_id else "vi-VN-HoaiMyNeural"
  ```
  - Calls `generate_script` prior to TTS synthesis.
  - Prioritizes `pers["voice_name"]/["voice_id"]` -> `script_voice` (`script_data.voice_id`) -> niche fallback.
  - When `product_meta={"title": "Cây lau nhà 360 độ"}` without `niche_id`, `ScriptGenerator` infers `nam_minh` and `script_voice="vi-VN-NamMinhNeural"`, which `VideoStudioAgent` uses directly for TTS synthesis.

#### 4. SQLAlchemy ORM Synonym Definition & SQL Compilation
- **File**: `src/database/models.py`
- **Lines 27, 222–225 (`VideoJob`)**:
  ```python
  from sqlalchemy.orm import (
      DeclarativeBase,
      Mapped,
      mapped_column,
      relationship,
      synonym,
      validates,
  )
  ...
  output_video_path: Mapped[Optional[str]] = mapped_column(
      String(500), nullable=True
  )
  rendered_video_path = synonym("output_video_path")
  ```
- **SQL Compilation Verification Probe**:
  Command:
  ```bash
  python3 -c "
  from sqlalchemy import select
  from src.database.models import VideoJob
  stmt = select(VideoJob).where(VideoJob.rendered_video_path == '/tmp/rendered.mp4')
  print(stmt.compile(compile_kwargs={'literal_binds': True}))
  "
  ```
  Output:
  ```sql
  SELECT video_jobs.job_id, video_jobs.product_id, video_jobs.niche_id, video_jobs.channel_id, video_jobs.source_video_url, video_jobs.script, video_jobs.audio_path, video_jobs.output_video_path, video_jobs.status, video_jobs.error_message, video_jobs.created_at, video_jobs.updated_at 
  FROM video_jobs 
  WHERE video_jobs.output_video_path = '/tmp/rendered.mp4'
  ```
  - Compiles directly to `WHERE video_jobs.output_video_path = '/tmp/rendered.mp4'`.
  - Zero occurrences of `WHERE false`.

#### 5. Verification of Removal of Integrity Violations and Deprecations
- **In `src/services/video_downloader.py`**:
  - The test-specific shortcut `if "invalid" in clean_url.lower()` was completely removed.
  - Implemented domain allowlisting (`tiktok.com`, `douyin.com`) and path regex verification (`r"/(?:video|v)/(\d+)"` and shortlink slug `r"^/[a-zA-Z0-9_-]+/?$"`).
- **In `src/services/video_processor.py`**:
  - Silent failure swallowing removed. `VideoProcessingError` is raised when `proc.returncode != 0`.
- **In `src/`**:
  - Grep search for `tempfile.mktemp()` in `src/` returned **0 matches**. All temp files use `tempfile.NamedTemporaryFile`.

---

### 1.2 Test Execution Results

1. **Targeted Milestone 5 Unit Test Suite**:
   Command: `pytest tests/test_database.py tests/test_script_generator.py tests/test_video_processor.py -v`
   Result: **35 passed in 1.29s** (100% pass).

2. **Adversarial Script Harness (737 assertions)**:
   Command: `python3 scripts/m5_adversarial_script_harness.py`
   Result:
   - Suite 1 (Adversarial Title Injections & Leakage): 144/144 passed (100.0%)
   - Suite 2 (KOC Marker Guarantee & Contract Integrity): 464/464 passed (100.0%)
   - Suite 3 (Extreme & Corrupt Metadata Inputs): 84/84 passed (100.0%)
   - Suite 4 (Persona & Voice Mapping Integrity): 45/45 passed (100.0%)
   - **Total**: **737/737 passed (100.0%)**, 0 failures.

3. **Adversarial Media Harness (650 assertions)**:
   Command: `python3 scripts/m5_adversarial_media_harness.py`
   Result:
   - Suite 1 (Video Processor Filter Graph Integrity): 561/561 passed (100.0%)
   - Suite 2 (0-Byte Media & Missing File Resilience): 9/9 passed (100.0%)
   - Suite 3 (TTS Service Edge-Cases): 22/22 passed (100.0%)
   - Suite 4 (Video Downloader URL Adversarial Attacks): 42/42 passed (100.0%)
   - Suite 5 (Video Studio Pipeline Resilience): 16/16 passed (100.0%)
   - **Total**: **650/650 passed (100.0%)**, 0 failures.

4. **Full Regression Test Suite**:
   Command: `pytest tests/ -v`
   Result: **334 passed in 16.56s** (100% pass, 0 failures, 0 regressions).

---

## 2. Logic Chain

1. **Resolution of Finding 1 (Integrity Violation in VideoDownloader)**:
   - In prior review, `VideoDownloader._validate_url` checked `"invalid" in clean_url.lower()`, rejecting legitimate handles like `https://www.tiktok.com/@invalid_user/video/712345` while admitting arbitrary third-party URLs.
   - Observation 1.1(5) confirms the keyword check was removed and replaced by strict domain allowlisting and regex route checking.
   - Test `test_download_video_valid_url_accepted[.../@invalid_user/video/712345...]` and adversarial URL suite pass 100%. Integrity violation is resolved.

2. **Resolution of Finding 2 (Persona Mismatch in ScriptGenerator Fallback)**:
   - In prior review, emergency fallback returned hardcoded female fashion copy for all personas.
   - Observation 1.1(2) confirms `generate_script` now branches on `persona_name == "nam_minh"`. HomeLife products receive `vi-VN-NamMinhNeural` voice, male markers (`các bác`, `3s`, `nhàn`), and clean homelife caption without female fashion copy.
   - Both unit tests and empirical probes confirm persona alignment.

3. **Resolution of Finding 3 (Voice Resolution Override in VideoStudioAgent)**:
   - In prior review, `VideoStudioAgent.produce_video()` resolved voice before calling `generate_script`, defaulting to female `vi-VN-HoaiMyNeural` whenever `niche_id` was absent in `product_meta`.
   - Observation 1.1(3) confirms `VideoStudioAgent` generates script first and prioritizes `script_data.voice_id`.
   - Empirical probe confirmed that `product_meta={'title': 'Cây lau nhà 360 độ thông minh'}` correctly routed to `vi-VN-NamMinhNeural`.

4. **Resolution of Finding 4 (SQLAlchemy ORM Synonym on VideoJob)**:
   - In prior review, `VideoJob.rendered_video_path` was a Python `@property`, causing `VideoJob.rendered_video_path == ...` to compile to `WHERE false`.
   - Observation 1.1(4) confirms `rendered_video_path = synonym("output_video_path")` using SQLAlchemy ORM's native `synonym` descriptor.
   - Direct query compilation probe and unit test `test_video_job_rendered_video_path_synonym_query` in `tests/test_database.py` confirm query compiles directly to `WHERE video_jobs.output_video_path = ...`.

5. **Resolution of ToneValidator False Positives and Accent Bypasses**:
   - In prior review, stripping diacritics combined with leetspeak `!` replacement caused `nha!` to convert to `nhai`, triggering false positive counterfeit flags on natural KOC CTAs.
   - Lookahead `re.sub(r"!(?=[a-z0-9])", "i", tw)` leaves trailing conversational `nha!` untouched while correctly resolving `d!or` -> `dior` and `l!ke` -> `like`.
   - Expanded `COUNTERFEIT_PATTERNS` matches both unaccented and accented forms (`tuon`/`tuồn`, `chuan`/`chuẩn`, `nhai`/`nhái`), closing obfuscation bypasses.

---

## 3. Caveats

- In the current macOS test environment, system binaries for `ffmpeg`, `yt-dlp`, and `whisper` are not installed; simulation fallback logic is exercised as designed by project architecture. All contract requirements for offline fallback remain satisfied.
- Per user instruction: No git commands were executed during this verification.
- No caveats: All 5 re-verification checklist items pass completely.

---

## 4. Conclusion

All 4 defects and 1 integrity violation flagged in the prior review of Milestone 5 have been remediated with genuine, robust implementations. The code exhibits high quality, correct persona alignment, zero test-matching shortcuts, zero `mktemp` TOCTOU hazards, and 100% test pass rate across unit, adversarial, and full regression suites (334/334 passed).

The verdict is **APPROVE**.

---

## 5. Verification Method

To independently re-verify all assertions in this report:

```bash
# 1. Targeted Milestone 5 Unit Test Suite
pytest tests/test_database.py tests/test_script_generator.py tests/test_video_processor.py -v

# 2. Adversarial Script Stress Harness (737 assertions)
python3 scripts/m5_adversarial_script_harness.py

# 3. Adversarial Media Stress Harness (650 assertions)
python3 scripts/m5_adversarial_media_harness.py

# 4. Full Test Suite Regression Check (334 tests)
pytest tests/ -v

# 5. Independent Probe for ToneValidator Accent & False Positive Protection
python3 -c "
from src.core.tone_validator import ToneValidator
assert ToneValidator.validate('Chị em bấm vào giỏ hàng nha!'), 'False positive on nha!'
assert not ToneValidator.validate('Váy t.u.ồ.n a.u.t.h'), 'Bypassed tuồn auth'
assert not ToneValidator.validate('Hàng vnxk chuẩn auth'), 'Bypassed chuẩn auth'
assert ToneValidator.validate('Món nhái chiên giòn'), 'False positive on món nhái'
print('ToneValidator verification passed!')
"

# 6. Independent Probe for VideoStudioAgent Voice Routing
python3 -c "
from src.agents.video_studio import VideoStudioAgent
from unittest.mock import AsyncMock
import asyncio
studio = VideoStudioAgent()
studio.tts.synthesize = AsyncMock(return_value='/tmp/test.mp3')
studio.downloader.download_video = AsyncMock(return_value='/tmp/test.mp4')
studio.processor.remix_video = AsyncMock(return_value='/tmp/out.mp4')
asyncio.run(studio.produce_video(job_id='test', product_meta={'title': 'Cây lau nhà 360 độ'}))
assert studio.tts.synthesize.call_args.kwargs['voice'] == 'vi-VN-NamMinhNeural'
print('VideoStudioAgent voice routing verification passed!')
"

# 7. Independent Probe for SQLAlchemy Synonym
python3 -c "
from sqlalchemy import select
from src.database.models import VideoJob
stmt = select(VideoJob).where(VideoJob.rendered_video_path == '/tmp/rendered.mp4')
compiled = str(stmt.compile(compile_kwargs={'literal_binds': True}))
assert 'WHERE false' not in compiled and 'video_jobs.output_video_path' in compiled
print('SQLAlchemy synonym verification passed!')
"
```

### Invalidation Conditions
- Any occurrence of `WHERE false` when querying `VideoJob.rendered_video_path`.
- Any false positive triggered by natural conversational particle `nha!` in `ToneValidator`.
- Any homelife product without explicit `niche_id` being synthesized with female voice `vi-VN-HoaiMyNeural` instead of male `vi-VN-NamMinhNeural`.
- Any failure across the 334 tests or 1,387 adversarial assertions.
