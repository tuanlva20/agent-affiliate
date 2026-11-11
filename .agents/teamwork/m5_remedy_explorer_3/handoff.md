# Handoff Report — VideoStudioAgent Voice Routing & Database Model Harmonization Remediation

**Author**: `m5_remedy_explorer_3`  
**Milestone**: Milestone 5 Remediation (AMAS v1.4.0)  
**Target Files**:
- `src/agents/video_studio.py`
- `src/database/models.py`
- `tests/test_database.py`
- `tests/test_video_processor.py`
- `tests/e2e/test_tier3_combinations.py`  
**Date**: 2026-11-10T12:06:00Z  
**Type**: Hard Handoff  

---

## 1. Observation

### 1.1 Direct Observation: Voice Resolution Mismatch in `VideoStudioAgent`
In `src/agents/video_studio.py`, lines 62–74:
```python
62:         # Determine voice name
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
- When `product_meta` contains a HomeLife title but omits `niche_id` (e.g., `{"title": "Cây lau nhà thông minh 360 độ"}`), `ScriptGenerator.generate_script` infers `persona="nam_minh"` and `voice_id="vi-VN-NamMinhNeural"` based on title heuristics in `_resolve_persona`. It generates a male HomeLife script ("Các bác ơi, 3 giây sạch bóng kin kít...").
- However, `produce_video()` determined `voice` *before* generating the script, evaluated `niche_id = ""` as false for `"do_gia_dung"`, and assigned `voice = "vi-VN-HoaiMyNeural"`.
- As a consequence, `self.tts.synthesize(full_voiceover, voice=voice)` generates a female voice reciting a male script.
- Empirical verification output:
  ```
  TTS voice kwargs passed: {'voice': 'vi-VN-HoaiMyNeural'} for script persona 'nam_minh'
  ```

### 1.2 Direct Observation: Dead Dependency `self.transcriber` in `VideoStudioAgent`
In `src/agents/video_studio.py`, lines 35 & 42:
```python
35:         transcriber: Optional[AudioTranscriber] = None,
...
42:         self.transcriber = transcriber or AudioTranscriber()
```
- In `produce_video()` (lines 49–101), `self.transcriber` is never referenced or called anywhere.
- Reviewer 1 (Finding F-04) flagged this dead dependency as creating confusion regarding whether competitor video transcription is part of the remix flow or an offline utility.

### 1.3 Direct Observation: SQL Query Failure on `VideoJob.rendered_video_path`
In `src/database/models.py`, lines 219–225:
```python
219:     @property
220:     def rendered_video_path(self) -> Optional[str]:
221:         return self.output_video_path
222: 
223:     @rendered_video_path.setter
224:     def rendered_video_path(self, value: Optional[str]) -> None:
225:         self.output_video_path = value
```
- Compiling a SQLAlchemy 2.0 query filtering on `VideoJob.rendered_video_path`:
  ```bash
  python3 -c "
  from sqlalchemy import select
  from src.database.models import VideoJob
  stmt = select(VideoJob).where(VideoJob.rendered_video_path == '/tmp/rendered.mp4')
  print(stmt)
  "
  ```
- Verbatim tool output:
  ```sql
  SELECT video_jobs.job_id, video_jobs.product_id, video_jobs.niche_id, video_jobs.channel_id,
         video_jobs.source_video_url, video_jobs.script, video_jobs.audio_path,
         video_jobs.output_video_path, video_jobs.status, video_jobs.error_message,
         video_jobs.created_at, video_jobs.updated_at 
  FROM video_jobs 
  WHERE false
  ```
- Because standard Python `@property` objects evaluate to `False` in Python comparisons when compared to strings, SQLAlchemy Core translates the clause to `WHERE false`. Any database query searching for jobs by `rendered_video_path` returns `None`.

---

## 2. Logic Chain

1. **Voice Routing Hierarchy**:
   - `ScriptGenerator` is the domain authority on persona-to-voice mapping (`KOCScriptResult.voice_id` and `KOCScriptResult.persona`).
   - `VideoStudioAgent.produce_video()` should generate the script first.
   - Voice selection must follow a clear priority:
     1. Explicit voice override requested by caller (`persona.get("voice_name")` or `persona.get("voice_id")`).
     2. Certified voice determined by `ScriptGenerator` (`script_data.get("voice_id")` or `getattr(script_data, "voice_id", None)`).
     3. Fallback niche check (`"vi-VN-NamMinhNeural"` if `"do_gia_dung"` in `niche_id` else `"vi-VN-HoaiMyNeural"`).
     4. Default `"vi-VN-HoaiMyNeural"`.
   - This ensures homelife products always receive Nam Minh voice even when `niche_id` is missing in `product_meta`.

2. **`self.transcriber` Integration**:
   - To make `self.transcriber` purposeful without breaking existing contracts or adding unwanted latency to default runs, `produce_video()` should check `if options and options.get("transcribe_source"):`.
   - When enabled, `raw_video` audio is transcribed via `await self.transcriber.transcribe(raw_video)`.
   - The operation is wrapped in a guarded `try/except` block to log warnings rather than crashing the primary video rendering pipeline.
   - Comprehensive docstrings in `VideoStudioAgent` clarify its dual role: inline competitor benchmark transcription and offline research extraction.

3. **SQLAlchemy ORM Synonym Harmonization**:
   - Replacing the manual Python `@property` with `rendered_video_path = synonym("output_video_path")` leverages SQLAlchemy ORM's native column aliasing.
   - With `synonym`:
     * Read access (`job.rendered_video_path`) proxies directly to `job.output_video_path`.
     * Write access (`job.rendered_video_path = val`) sets `job.output_video_path = val`.
     * Constructor kwargs (`VideoJob(rendered_video_path=...)`) populates `output_video_path`.
     * ORM expression queries (`select(VideoJob).where(VideoJob.rendered_video_path == val)`) compile to `WHERE video_jobs.output_video_path = :output_video_path_1`.
     * No extraneous column is added to the database table schema (`VideoJob.__table__.columns` remains clean and backwards-compatible with Alembic and SQLite/PostgreSQL migrations).

---

## 3. Caveats

1. In `tests/e2e/conftest.py`, a separate test-scoped `VideoJobModel` is declared that directly maps a column named `rendered_video_path`. The domain model in `src/database/models.py` uses `output_video_path`. Adding `synonym` bridges this gap completely across all layers.
2. The Whisper engine inside `AudioTranscriber` and `FFmpeg` inside `VideoProcessor` operate with mock/offline fallbacks in CI/local test environments when system binaries are absent. The proposed code preserves this fallback resilience.

---

## 4. Conclusion & Concrete Implementation Plan

### 4.1 Exact Code Replacement Blocks

#### Replacement 1: `src/database/models.py`
**Target File**: `src/database/models.py`  
**Rationale**: Import `synonym` from `sqlalchemy.orm` and replace `@property rendered_video_path` on `VideoJob` with `synonym("output_video_path")`.

**Block 1A — Imports (Lines 22–23)**:
*Target Content*:
```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, validates
```
*Replacement Content*:
```python
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    synonym,
    validates,
)
```

**Block 1B — VideoJob Model (Lines 215–226)**:
*Target Content*:
```python
    output_video_path: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )

    @property
    def rendered_video_path(self) -> Optional[str]:
        return self.output_video_path

    @rendered_video_path.setter
    def rendered_video_path(self, value: Optional[str]) -> None:
        self.output_video_path = value
    # Status: 'created', 'scripted', 'audio_generated', 'rendered', 'publishing', 'published', 'failed'
```
*Replacement Content*:
```python
    output_video_path: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )
    rendered_video_path = synonym("output_video_path")

    # Status: 'created', 'scripted', 'audio_generated', 'rendered', 'publishing', 'published', 'failed'
```

---

#### Replacement 2: `src/agents/video_studio.py`
**Target File**: `src/agents/video_studio.py`  
**Rationale**: Clarify `AudioTranscriber` in class docstring, order script generation prior to voice resolution, adopt prioritized voice routing, and integrate optional competitor source transcription.

**Block 2A — Class & Method Docstrings, Voice Routing & Pipeline Integration (Lines 29–101)**:
*Target Content*:
```python
class VideoStudioAgent:
    """Coordinator of the end-to-end automated video remix studio."""

    def __init__(
        self,
        downloader: Optional[VideoDownloader] = None,
        transcriber: Optional[AudioTranscriber] = None,
        script_generator: Optional[ScriptGenerator] = None,
        tts_service: Optional[TTSService] = None,
        processor: Optional[VideoProcessor] = None,
        storage_dir: str = "storage/rendered",
    ) -> None:
        self.downloader = downloader or VideoDownloader()
        self.transcriber = transcriber or AudioTranscriber()
        self.script_gen = script_generator or ScriptGenerator()
        self.tts = tts_service or TTSService()
        self.processor = processor or VideoProcessor()
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    async def produce_video(
        self,
        job_id: str,
        product_meta: Optional[Dict[str, Any]] = None,
        persona: Optional[Dict[str, Any]] = None,
        source_video_url: Optional[str] = None,
        db_session: Optional[AsyncSession] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Executes full studio remix pipeline for a job."""
        meta = product_meta or {"title": "Sản phẩm xu hướng", "price": 199000.0}
        pers = persona or {"tone": "koc"}

        # Determine voice name
        voice = pers.get("voice_name")
        if not voice:
            niche_id = meta.get("niche_id", "")
            voice = "vi-VN-NamMinhNeural" if "do_gia_dung" in niche_id else "vi-VN-HoaiMyNeural"

        # 1. Generate KOC Script
        script_data = self.script_gen.generate_script(meta, pers)
        full_voiceover = script_data.get("full_voiceover", "")

        # 2. Synthesize TTS Audio
        audio_file = await self.tts.synthesize(full_voiceover, voice=voice)

        # 3. Video Acquisition (Download)
        url = (
            source_video_url
            or meta.get("source_video_url")
            or "https://tiktok.com/@competitor/video/1001"
        )
        raw_video = await self.downloader.download_video(url)

        # 4. Remux with FFmpeg Copyright Evasion
        rendered_file = str(self.storage_dir / f"remixed_{job_id}_final.mp4")
        await self.processor.remix_video(raw_video, audio_file, rendered_file, options=options)

        # 5. Database Synchronization (if session provided)
        if db_session:
            stmt = select(VideoJob).where(VideoJob.job_id == job_id)
            res = await db_session.execute(stmt)
            job = res.scalar_one_or_none()
            if job:
                job.status = "rendered"
                job.output_video_path = rendered_file
                job.rendered_video_path = rendered_file
                job.audio_path = audio_file
                job.script = full_voiceover
                await db_session.commit()

        return rendered_file
```
*Replacement Content*:
```python
class VideoStudioAgent:
    """Coordinator of the end-to-end automated video remix studio (Feature F18).

    Orchestrates the multi-step production pipeline:
    1. ScriptGenerator: Generates persona-aligned, ToneValidator-compliant KOC scripts.
    2. TTSService: Synthesizes high-fidelity Vietnamese voiceover with resolved persona voice.
    3. VideoDownloader: Acquires benchmark/competitor source videos.
    4. AudioTranscriber: Extracts audio and transcribes competitor scripts for inspiration/analysis
       (invoked on source video when options={'transcribe_source': True}).
    5. VideoProcessor: Remuxes video with FFmpeg copyright evasion transformations.
    6. Database: Synchronizes job state and outputs in VideoJob.
    """

    def __init__(
        self,
        downloader: Optional[VideoDownloader] = None,
        transcriber: Optional[AudioTranscriber] = None,
        script_generator: Optional[ScriptGenerator] = None,
        tts_service: Optional[TTSService] = None,
        processor: Optional[VideoProcessor] = None,
        storage_dir: str = "storage/rendered",
    ) -> None:
        self.downloader = downloader or VideoDownloader()
        self.transcriber = transcriber or AudioTranscriber()
        self.script_gen = script_generator or ScriptGenerator()
        self.tts = tts_service or TTSService()
        self.processor = processor or VideoProcessor()
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    async def produce_video(
        self,
        job_id: str,
        product_meta: Optional[Dict[str, Any]] = None,
        persona: Optional[Dict[str, Any]] = None,
        source_video_url: Optional[str] = None,
        db_session: Optional[AsyncSession] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Executes full studio remix pipeline for a job.

        Args:
            job_id: Unique identifier for the video rendering job.
            product_meta: Product metadata (title, niche_id, price, etc.).
            persona: Persona configuration (optional explicit voice_name/voice_id or tone).
            source_video_url: Benchmark TikTok URL to download and remix.
            db_session: Optional AsyncSession to persist rendered status and file paths.
            options: Rendering and pipeline options, e.g.:
                - 'transcribe_source': bool, run AudioTranscriber on source video.
                - FFmpeg evasion options passed to VideoProcessor.remix_video.

        Returns:
            Absolute path to final rendered remix video.
        """
        meta = product_meta or {"title": "Sản phẩm xu hướng", "price": 199000.0}
        pers = persona or {"tone": "koc"}

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

        # 2. Synthesize TTS Audio
        audio_file = await self.tts.synthesize(full_voiceover, voice=voice)

        # 3. Video Acquisition (Download)
        url = (
            source_video_url
            or meta.get("source_video_url")
            or "https://tiktok.com/@competitor/video/1001"
        )
        raw_video = await self.downloader.download_video(url)

        # Optional competitor audio transcription / research extraction (Feature F14)
        if options and options.get("transcribe_source"):
            try:
                transcription = await self.transcriber.transcribe(raw_video)
                logger.info(
                    "Source video %s transcribed successfully (%d chars) for competitor analysis.",
                    raw_video,
                    len(transcription),
                )
            except Exception as exc:
                logger.warning("Optional competitor transcription skipped: %s", exc)

        # 4. Remux with FFmpeg Copyright Evasion
        rendered_file = str(self.storage_dir / f"remixed_{job_id}_final.mp4")
        await self.processor.remix_video(raw_video, audio_file, rendered_file, options=options)

        # 5. Database Synchronization (if session provided)
        if db_session:
            stmt = select(VideoJob).where(VideoJob.job_id == job_id)
            res = await db_session.execute(stmt)
            job = res.scalar_one_or_none()
            if job:
                job.status = "rendered"
                job.output_video_path = rendered_file
                job.rendered_video_path = rendered_file
                job.audio_path = audio_file
                job.script = full_voiceover
                await db_session.commit()

        return rendered_file
```

---

#### Replacement 3: `tests/test_database.py`
**Target File**: `tests/test_database.py`  
**Rationale**: Add a dedicated unit test verifying `synonym("output_video_path")` behavior: attribute read/write, constructor kwarg, and SQLAlchemy select query compilation with `where(VideoJob.rendered_video_path == ...)`.

*Append to End of File*:
```python
@pytest.mark.asyncio
async def test_video_job_rendered_video_path_synonym_query(db_session: AsyncSession):
    """Verifies VideoJob.rendered_video_path synonym attribute and ORM query compilation."""
    niche = Niche(niche_id="thoi_trang_nu_synonym", name="Thời trang nữ")
    product = Product(
        product_id="prod_synonym_01",
        niche_id="thoi_trang_nu_synonym",
        title="Váy xếp ly công sở",
        price=210000.0,
        product_url="https://shop.tiktok.com/view/item/synonym_01",
    )
    # 1. Constructor instantiation with rendered_video_path kwarg
    job = VideoJob(
        job_id="job_synonym_001",
        product_id="prod_synonym_01",
        niche_id="thoi_trang_nu_synonym",
        rendered_video_path="storage/rendered/synonym_init.mp4",
        status="created",
    )
    db_session.add_all([niche, product, job])
    await db_session.commit()

    # 2. Verify attribute getter and setter reflection
    assert job.output_video_path == "storage/rendered/synonym_init.mp4"
    assert job.rendered_video_path == "storage/rendered/synonym_init.mp4"

    job.rendered_video_path = "storage/rendered/synonym_updated.mp4"
    await db_session.commit()
    assert job.output_video_path == "storage/rendered/synonym_updated.mp4"

    # 3. Query via select with where clause on synonym (must NOT compile to WHERE false)
    stmt = select(VideoJob).where(
        VideoJob.rendered_video_path == "storage/rendered/synonym_updated.mp4"
    )
    res = await db_session.execute(stmt)
    matched_job = res.scalar_one_or_none()
    assert matched_job is not None
    assert matched_job.job_id == "job_synonym_001"
    assert matched_job.output_video_path == "storage/rendered/synonym_updated.mp4"
```

---

#### Replacement 4: `tests/test_video_processor.py`
**Target File**: `tests/test_video_processor.py`  
**Rationale**: Add unit tests in `TestVideoStudioAgent` to verify:
1. Voice routing respects `ScriptGenerator`'s persona inference when `niche_id` is omitted in `product_meta`.
2. Voice override via `persona["voice_name"]` is honored.
3. `options["transcribe_source"] = True` triggers `self.transcriber.transcribe()`.

*Append to `TestVideoStudioAgent` class in `tests/test_video_processor.py`*:
```python
    @pytest.mark.asyncio
    async def test_video_studio_voice_routing_and_transcribe_source(self, tmp_path):
        from unittest.mock import AsyncMock
        from src.agents.video_studio import VideoStudioAgent

        studio = VideoStudioAgent(storage_dir=str(tmp_path / "rendered"))
        studio.transcriber.transcribe = AsyncMock(return_value="Kịch bản đối thủ mẫu")
        studio.tts.synthesize = AsyncMock(return_value=str(tmp_path / "audio.mp3"))
        studio.downloader.download_video = AsyncMock(return_value=str(tmp_path / "source.mp4"))
        studio.processor.remix_video = AsyncMock(return_value=str(tmp_path / "final.mp4"))

        # Case 1: Homelife title without niche_id -> must resolve to Nam Minh voice
        await studio.produce_video(
            job_id="job_voice_test_01",
            product_meta={"title": "Cây lau nhà thông minh tự vắt 360 độ"},
            persona={"tone": "koc"},
        )
        assert studio.tts.synthesize.call_args.kwargs["voice"] == "vi-VN-NamMinhNeural"

        # Case 2: Explicit persona voice override
        await studio.produce_video(
            job_id="job_voice_test_02",
            product_meta={"title": "Cây lau nhà thông minh tự vắt 360 độ"},
            persona={"voice_name": "vi-VN-CustomVoice"},
        )
        assert studio.tts.synthesize.call_args.kwargs["voice"] == "vi-VN-CustomVoice"

        # Case 3: options['transcribe_source'] activates transcriber
        await studio.produce_video(
            job_id="job_transcribe_test",
            product_meta={"title": "Váy body nhún eo"},
            options={"transcribe_source": True},
        )
        assert studio.transcriber.transcribe.called
```

---

## 5. Verification Method

To verify these changes independently:

1. **Verify Database Synonym Behavior**:
   ```bash
   python3 -c "
   from sqlalchemy import select
   from src.database.models import VideoJob
   stmt = select(VideoJob).where(VideoJob.rendered_video_path == '/tmp/test.mp4')
   sql = str(stmt)
   assert 'WHERE video_jobs.output_video_path =' in sql, f'Compilation failed: {sql}'
   print('Database synonym ORM expression verification PASSED!')
   "
   ```

2. **Verify Video Studio Voice Routing & Transcriber**:
   ```bash
   python3 -c "
   import asyncio
   from unittest.mock import AsyncMock
   from src.agents.video_studio import VideoStudioAgent

   async def check():
       studio = VideoStudioAgent()
       studio.tts.synthesize = AsyncMock(return_value='/tmp/a.mp3')
       studio.downloader.download_video = AsyncMock(return_value='/tmp/v.mp4')
       studio.processor.remix_video = AsyncMock(return_value='/tmp/o.mp4')
       studio.transcriber.transcribe = AsyncMock(return_value='transcription')

       # Test homelife title without niche_id
       await studio.produce_video(
           job_id='check_1',
           product_meta={'title': 'Cây lau nhà thông minh 360 độ'},
           options={'transcribe_source': True}
       )
       assert studio.tts.synthesize.call_args.kwargs['voice'] == 'vi-VN-NamMinhNeural', 'Voice mismatch'
       assert studio.transcriber.transcribe.called, 'Transcribe not called'
       print('VideoStudio voice routing & transcriber verification PASSED!')

   asyncio.run(check())
   "
   ```

3. **Run Full Test Suite**:
   ```bash
   pytest tests/test_database.py tests/test_video_processor.py tests/e2e/test_tier3_combinations.py -v
   pytest tests/ -v
   ```

### Invalidation Conditions
This plan is invalidated if:
1. `synonym("output_video_path")` generates any schema difference or extra column in `Base.metadata.tables["video_jobs"]`.
2. Existing tests that directly set `job.output_video_path` or `job.rendered_video_path` fail.
3. Voice resolution fails to select `"vi-VN-NamMinhNeural"` for products with HomeLife titles lacking explicit `niche_id`.
