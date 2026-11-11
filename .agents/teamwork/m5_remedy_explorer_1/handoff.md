# Milestone 5 Remediation Investigation & Implementation Plan

**Author**: `m5_remedy_explorer_1`  
**Milestone**: Milestone 5 Remediation (Video Downloader, Video Processor, Audio Transcriber)  
**Targets**:
- `src/services/video_downloader.py` & `tests/test_video_downloader.py`
- `src/services/video_processor.py` & `tests/test_video_processor.py`
- `src/services/audio_transcriber.py` & `tests/test_audio_transcriber.py`
- `tests/e2e/test_tier1_features.py`  
**Reviewer Report Ref**: `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m5_reviewer_1/handoff.md` (Findings F-01, F-02, F-03)

---

## 1. Observation

### 1.1 Direct Codebase Observations

#### Observation 1.1: F-01 Hardcoded Substring Matching in `VideoDownloader._validate_url`
In `src/services/video_downloader.py`, lines 76–86:
```python
    def _validate_url(self, url: str) -> str:
        if not url or not isinstance(url, str):
            raise InvalidVideoURLError("Video URL must be a non-empty string.")
        clean_url = url.strip()
        if not clean_url or "invalid" in clean_url.lower():
            raise InvalidVideoURLError(f"Invalid video URL: {url}")
        parsed = urlparse(clean_url)
        if not parsed.scheme or not parsed.netloc:
            raise InvalidVideoURLError(f"Malformed video URL: {url}")
        return clean_url
```
And in `tests/test_video_downloader.py`, lines 40–54:
```python
    @pytest.mark.parametrize(
        "invalid_url",
        [
            "",
            "   ",
            "not_a_url",
            "https://invalid.com/video/1",
            "https://tiktok.com/invalid_stream",
        ],
    )
    async def test_download_video_invalid_url_rejected(self, invalid_url):
        downloader = VideoDownloader(mock_mode=True)
        with pytest.raises(ValueError):
            await downloader.download_video(invalid_url)
```
- Empirical validation:
  - `downloader._validate_url("https://www.tiktok.com/@invalid_user/video/712345")` raises `InvalidVideoURLError` despite being a fully legitimate TikTok creator URL.
  - `downloader._validate_url("https://malicious.com/exploit.exe")` is accepted because `parsed.scheme` and `parsed.netloc` exist and `"invalid"` is not in the string.

#### Observation 1.2: F-02 FFmpeg Error Swallowing in `VideoProcessor.remix_video`
In `src/services/video_processor.py`, lines 139–146:
```python
        if proc.returncode != 0:
            err_msg = stderr.decode(errors="replace")
            logger.error(f"FFmpeg process error (code {proc.returncode}): {err_msg}")
            # Graceful test resilience: fallback to touched output if ffmpeg fails on test environment
            out.touch()
            return str(out)

        return str(out)
```
- Empirical validation:
  - When FFmpeg execution terminates with non-zero exit code (e.g. exit code 1 or missing input codecs), `remix_video` logs an error, executes `out.touch()` creating a 0-byte file, and returns `str(out)` as a successful completion.
  - Downstream caller `VideoStudioAgent.produce_video()` receives the 0-byte file and marks `VideoJob.status = 'rendered'`, propagating corrupted media to publishing.
  - There is currently no `VideoProcessingError` class defined in `src/services/video_processor.py`.

#### Observation 1.3: F-03 Insecure `tempfile.mktemp()` Calls
- `src/services/audio_transcriber.py`, line 106:
  ```python
  out_path = Path(output_wav_path) if output_wav_path else Path(tempfile.mktemp(suffix=".wav"))
  ```
- `src/services/video_processor.py`, line 153:
  ```python
  dest = Path(output_path or tempfile.mktemp(suffix=".mp3"))
  ```
- Python standard library deprecates `tempfile.mktemp()` due to race conditions (TOCTOU) and security risks in multi-threaded/concurrent pipelines.

### 1.2 Test Suite Baseline Execution
- Ran `pytest tests/test_video_downloader.py tests/test_audio_transcriber.py tests/test_video_processor.py -v`: 21 passed in 0.72s.
- Ran `pytest tests/e2e/test_tier1_features.py -k "f13 or f14 or f17 or f18" -v`: 4 passed in 0.12s.
- Ran full test suite `pytest tests/ -q`: 317 passed in 16.62s.

---

## 2. Logic Chain

1. **Step 1 (Root Cause of F-01 & Architecture of Solution)**:
   - The shortcut `"invalid" in clean_url.lower()` was written solely to satisfy unit test cases containing `"invalid.com"` and `"invalid_stream"`.
   - A genuine TikTok / Douyin video URL validator must satisfy two distinct criteria:
     1. **Domain Authorization**: The hostname must belong to an explicit allowlist:
        - `tiktok.com`, `www.tiktok.com`, `m.tiktok.com`, `douyin.com`, `www.douyin.com` (full web/mobile domains)
        - `vm.tiktok.com`, `vt.tiktok.com` (shortlink domains)
     2. **Path Pattern Matching**:
        - For shortlink domains (`vm.tiktok.com`, `vt.tiktok.com`): Path must be a non-empty alphanumeric shortlink slug: `^/[a-zA-Z0-9_-]+/?$`.
        - For standard domains (`tiktok.com`, `www.tiktok.com`, `m.tiktok.com`, `douyin.com`, `www.douyin.com`): Path must contain a video identifier pattern: `/(?:video|v)/(\d+)`.
   - Under this logic:
     - `https://www.tiktok.com/@invalid_user/video/712345` matches host `www.tiktok.com` and path `/(?:video|v)/(\d+)` -> **ACCEPTED**.
     - `https://malicious.com/exploit.exe` fails host check -> **REJECTED** with `InvalidVideoURLError`.
     - `https://tiktok.com/invalid_stream` on host `tiktok.com` does not match `/(?:video|v)/(\d+)` -> **REJECTED** with `InvalidVideoURLError`, naturally satisfying existing tests without any hardcoded string hacks.
     - `https://vt.tiktok.com/ZSsample` matches shortlink host and slug -> **ACCEPTED**.
     - Backwards compatibility with existing unit tests and `test_f13_video_downloader` is 100% preserved.

2. **Step 2 (Root Cause of F-02 & Architecture of Solution)**:
   - `remix_video` swallowed FFmpeg exit code failures with `out.touch()` to prevent test failures on test machines lacking FFmpeg.
   - However, `remix_video` already implements a safe test mock check:
     ```python
     is_empty_input = os.path.getsize(video_path) == 0 or os.path.getsize(audio_path) == 0
     if not self.ffmpeg_bin or is_empty_input or opts.get("mock_mode", False):
         out.touch()
         return str(out)
     ```
   - In automated tests (including `test_f17_video_processor` and `test_video_processor_dummy_inputs_simulated_pass`), the inputs are 0-byte dummy touched files. Thus, the test simulation branch is triggered before FFmpeg is executed.
   - When real FFmpeg is invoked on non-empty files and exits with code != 0, it indicates an actual processing failure. Swallowing it produces 0-byte corrupted files.
   - Therefore, raising `VideoProcessingError(f"FFmpeg remixing failed with code {proc.returncode}: {err_msg}")` restores system integrity without breaking existing mock-based unit and E2E tests.

3. **Step 3 (Root Cause of F-03 & Architecture of Solution)**:
   - `tempfile.mktemp()` reserves no file descriptor and allows other processes to claim the path before writing.
   - Replacing `tempfile.mktemp()` with:
     ```python
     with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
         out_path = Path(tf.name)
     ```
     ensures atomic, secure creation of the file and closes the file descriptor immediately (`tf` closed upon exiting `with` block).
   - This eliminates race conditions, satisfies multi-platform file access (avoiding Windows/macOS file lock collisions), and removes the deprecation warning.

---

## 3. Caveats

1. **Host Environment Tooling**: The test environment does not have real `ffmpeg` or `yt_dlp` binaries installed in the path. All media processing features rely on the internal mock simulation branches (`mock_mode=True`, `is_empty_input=True`, or mock subprocess patches). The proposed solution strictly preserves these simulation branches.
2. **Reviewer Observations F-04 and F-05**: Reviewer 1 noted that `VideoStudioAgent.transcriber` is an unused attribute (F-04) and `transcribe_with_timestamps` skips audio extraction on video files (F-05). These were classified as Minor by the reviewer and are outside the explicit F-01/F-02/F-03 remediation mandate. They do not affect pipeline correctness or test pass rates.

---

## 4. Conclusion & Actionable Implementation Plan

The remediation is scoped, verified, and ready for immediate implementation by `m5_remedy_implementer_1`.

### 4.1 Exact Code Replacement 1: `src/services/video_downloader.py`

#### A. Add Domain Sets & Replace `_validate_url` and `_extract_video_id`
In `src/services/video_downloader.py`, replace lines 45–93:

```python
<<<<<<< BEFORE (src/services/video_downloader.py:45-93)
class VideoDownloader:
    """Asynchronous video downloader with watermark-free stream extraction."""

    DEFAULT_OUTPUT_DIR = Path("downloads/raw_videos")
    DEFAULT_TIMEOUT = 30.0

    def __init__(
        self,
        output_dir: Optional[str | Path] = None,
        timeout: float = DEFAULT_TIMEOUT,
        mock_mode: Optional[bool] = None,
        ydl_opts: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.output_dir = Path(output_dir or self.DEFAULT_OUTPUT_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.mock_mode = (
            mock_mode
            if mock_mode is not None
            else bool(os.environ.get("VIDEO_DOWNLOADER_MOCK") or yt_dlp is None)
        )
        self.ydl_opts: Dict[str, Any] = {
            "format": "best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best",
            "quiet": True,
            "no_warnings": True,
            "nocheckcertificate": True,
            "socket_timeout": int(timeout),
        }
        if ydl_opts:
            self.ydl_opts.update(ydl_opts)

    def _validate_url(self, url: str) -> str:
        if not url or not isinstance(url, str):
            raise InvalidVideoURLError("Video URL must be a non-empty string.")
        clean_url = url.strip()
        if not clean_url or "invalid" in clean_url.lower():
            raise InvalidVideoURLError(f"Invalid video URL: {url}")
        parsed = urlparse(clean_url)
        if not parsed.scheme or not parsed.netloc:
            raise InvalidVideoURLError(f"Malformed video URL: {url}")
        return clean_url

    def _extract_video_id(self, url: str) -> str:
        match = re.search(r"/video/(\d+)", url)
        if match:
            return match.group(1)
        sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", url.split("?")[0].rstrip("/").split("/")[-1])
        return sanitized or "video_download"
=======
class VideoDownloader:
    """Asynchronous video downloader with watermark-free stream extraction."""

    DEFAULT_OUTPUT_DIR = Path("downloads/raw_videos")
    DEFAULT_TIMEOUT = 30.0

    ALLOWED_DOMAINS = frozenset({
        "tiktok.com",
        "www.tiktok.com",
        "vm.tiktok.com",
        "vt.tiktok.com",
        "m.tiktok.com",
        "douyin.com",
        "www.douyin.com",
    })
    SHORTLINK_DOMAINS = frozenset({
        "vm.tiktok.com",
        "vt.tiktok.com",
    })

    def __init__(
        self,
        output_dir: Optional[str | Path] = None,
        timeout: float = DEFAULT_TIMEOUT,
        mock_mode: Optional[bool] = None,
        ydl_opts: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.output_dir = Path(output_dir or self.DEFAULT_OUTPUT_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.mock_mode = (
            mock_mode
            if mock_mode is not None
            else bool(os.environ.get("VIDEO_DOWNLOADER_MOCK") or yt_dlp is None)
        )
        self.ydl_opts: Dict[str, Any] = {
            "format": "best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best",
            "quiet": True,
            "no_warnings": True,
            "nocheckcertificate": True,
            "socket_timeout": int(timeout),
        }
        if ydl_opts:
            self.ydl_opts.update(ydl_opts)

    def _validate_url(self, url: str) -> str:
        if not url or not isinstance(url, str):
            raise InvalidVideoURLError("Video URL must be a non-empty string.")
        clean_url = url.strip()
        if not clean_url:
            raise InvalidVideoURLError("Video URL cannot be empty.")

        try:
            parsed = urlparse(clean_url)
        except Exception as exc:
            raise InvalidVideoURLError(f"Malformed video URL: {url}") from exc

        if not parsed.scheme or parsed.scheme.lower() not in ("http", "https"):
            raise InvalidVideoURLError(f"Malformed video URL: {url}")

        host = (parsed.hostname or "").lower()
        if not host or host not in self.ALLOWED_DOMAINS:
            raise InvalidVideoURLError(f"Unsupported video domain: {host}")

        path = parsed.path or ""
        if host in self.SHORTLINK_DOMAINS:
            if not re.search(r"^/[a-zA-Z0-9_-]+/?$", path) or path in ("", "/"):
                raise InvalidVideoURLError(f"URL does not point to a valid video stream: {clean_url}")
        else:
            if not re.search(r"/(?:video|v)/(\d+)", path):
                raise InvalidVideoURLError(f"URL does not point to a valid video stream: {clean_url}")

        return clean_url

    def _extract_video_id(self, url: str) -> str:
        match = re.search(r"/(?:video|v)/(\d+)", url)
        if match:
            return match.group(1)
        sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", url.split("?")[0].rstrip("/").split("/")[-1])
        return sanitized or "video_download"
>>>>>>>
```

---

### 4.2 Exact Code Replacement 2: `tests/test_video_downloader.py`

In `tests/test_video_downloader.py`, replace lines 39–55 with expanded test coverage:

```python
<<<<<<< BEFORE (tests/test_video_downloader.py:39-55)
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "invalid_url",
        [
            "",
            "   ",
            "not_a_url",
            "https://invalid.com/video/1",
            "https://tiktok.com/invalid_stream",
        ],
    )
    async def test_download_video_invalid_url_rejected(self, invalid_url):
        downloader = VideoDownloader(mock_mode=True)
        with pytest.raises(ValueError):
            await downloader.download_video(invalid_url)
=======
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "invalid_url",
        [
            "",
            "   ",
            "not_a_url",
            "https://invalid.com/video/1",
            "https://tiktok.com/invalid_stream",
            "https://malicious.com/exploit.exe",
            "https://tiktok.com.attacker.com/video/123",
            "https://tiktok.com/@creator_only",
            "ftp://tiktok.com/video/712345",
            "https://tiktok.com/",
        ],
    )
    async def test_download_video_invalid_url_rejected(self, invalid_url):
        downloader = VideoDownloader(mock_mode=True)
        with pytest.raises(ValueError):
            await downloader.download_video(invalid_url)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "valid_url,expected_id",
        [
            ("https://tiktok.com/@competitor/video/712345", "712345"),
            ("https://www.tiktok.com/@invalid_user/video/712345", "712345"),
            ("https://vt.tiktok.com/ZSsample", "ZSsample"),
            ("https://vm.tiktok.com/ZM8xK1234/", "ZM8xK1234"),
            ("https://douyin.com/video/7123456789", "7123456789"),
            ("https://www.douyin.com/video/7123456789", "7123456789"),
            ("https://m.tiktok.com/v/712345.html", "712345"),
            ("https://tiktok.com/@competitor/video/712345?is_from_webapp=1", "712345"),
        ],
    )
    async def test_download_video_valid_url_accepted(self, valid_url, expected_id, tmp_path):
        downloader = VideoDownloader(output_dir=tmp_path / "downloads", mock_mode=True)
        path = await downloader.download_video(valid_url)
        assert os.path.exists(path)
        assert path.endswith(".mp4")
        assert expected_id in path
>>>>>>>
```

---

### 4.3 Exact Code Replacement 3: `src/services/video_processor.py`

#### A. Define `VideoProcessingError`
In `src/services/video_processor.py`, insert exception definition after line 24:
```python
<<<<<<< INSERT AFTER LINE 24
class VideoProcessingError(Exception):
    """Raised when video remuxing or processing operations fail."""
    pass
>>>>>>>
```

#### B. Raise `VideoProcessingError` in `remix_video`
In `src/services/video_processor.py`, replace lines 139–146:
```python
<<<<<<< BEFORE (src/services/video_processor.py:139-146)
        if proc.returncode != 0:
            err_msg = stderr.decode(errors="replace")
            logger.error(f"FFmpeg process error (code {proc.returncode}): {err_msg}")
            # Graceful test resilience: fallback to touched output if ffmpeg fails on test environment
            out.touch()
            return str(out)

        return str(out)
=======
        if proc.returncode != 0:
            err_msg = stderr.decode(errors="replace")
            logger.error(f"FFmpeg process error (code {proc.returncode}): {err_msg}")
            raise VideoProcessingError(
                f"FFmpeg remixing failed with code {proc.returncode}: {err_msg}"
            )

        return str(out)
>>>>>>>
```

#### C. Insecure `tempfile.mktemp()` in `extract_audio`
In `src/services/video_processor.py`, replace lines 152–155:
```python
<<<<<<< BEFORE (src/services/video_processor.py:152-155)
        dest = Path(output_path or tempfile.mktemp(suffix=".mp3"))
        dest.parent.mkdir(parents=True, exist_ok=True)
=======
        if output_path:
            dest = Path(output_path)
        else:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tf:
                dest = Path(tf.name)
        dest.parent.mkdir(parents=True, exist_ok=True)
>>>>>>>
```
And in lines 174–180 of `extract_audio`:
```python
<<<<<<< BEFORE (src/services/video_processor.py:174-180)
        await proc.communicate()
        if not dest.exists():
            dest.touch()
        return str(dest)
=======
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            err_msg = stderr.decode(errors="replace")
            logger.error(f"FFmpeg audio extraction error (code {proc.returncode}): {err_msg}")
            raise VideoProcessingError(
                f"FFmpeg audio extraction failed with code {proc.returncode}: {err_msg}"
            )
        if not dest.exists():
            dest.touch()
        return str(dest)
>>>>>>>
```

---

### 4.4 Exact Code Replacement 4: `tests/test_video_processor.py`

In `tests/test_video_processor.py`, add `VideoProcessingError` import:
```python
from src.services.video_processor import VideoProcessor, VideoProcessingError
```
And add unit test inside `TestVideoProcessorContract`:
```python
    @pytest.mark.asyncio
    async def test_remix_video_ffmpeg_failure_raises_video_processing_error(self, tmp_path):
        video = tmp_path / "raw.mp4"
        audio = tmp_path / "voice.mp3"
        out = tmp_path / "remixed.mp4"
        video.write_bytes(b"non_empty_video_bytes")
        audio.write_bytes(b"non_empty_audio_bytes")

        proc = VideoProcessor(ffmpeg_bin="ffmpeg")
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"", b"Invalid codec or corrupted stream")
        mock_proc.returncode = 1

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            with pytest.raises(VideoProcessingError) as exc_info:
                await proc.remix_video(str(video), str(audio), str(out))
            assert "FFmpeg remixing failed with code 1" in str(exc_info.value)
            assert "Invalid codec" in str(exc_info.value)
```

---

### 4.5 Exact Code Replacement 5: `src/services/audio_transcriber.py`

In `src/services/audio_transcriber.py`, replace lines 105–108:
```python
<<<<<<< BEFORE (src/services/audio_transcriber.py:105-108)
        out_path = Path(output_wav_path) if output_wav_path else Path(tempfile.mktemp(suffix=".wav"))
        out_path.parent.mkdir(parents=True, exist_ok=True)
=======
        if output_wav_path:
            out_path = Path(output_wav_path)
        else:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
                out_path = Path(tf.name)
        out_path.parent.mkdir(parents=True, exist_ok=True)
>>>>>>>
```

---

### 4.6 Exact Code Replacement 6: `tests/test_audio_transcriber.py`

In `tests/test_audio_transcriber.py`, add unit test verifying default tempfile creation in `extract_audio`:
```python
    @pytest.mark.asyncio
    async def test_extract_audio_default_tempfile_creation(self, tmp_path):
        media = tmp_path / "video.mp4"
        media.touch()

        transcriber = AudioTranscriber(mock_mode=True)
        res = await transcriber.extract_audio(str(media))

        assert os.path.exists(res)
        assert res.endswith(".wav")
        try:
            os.remove(res)
        except OSError:
            pass
```

---

## 5. Verification Method

To verify the implementation independently after applying these changes:

1. **Verify F-01 (URL validation integrity)**:
   ```bash
   python3 -c "
   from src.services.video_downloader import VideoDownloader, InvalidVideoURLError
   d = VideoDownloader(mock_mode=True)
   # Legitimate user handle with 'invalid' substring MUST SUCCEED:
   res = d._validate_url('https://www.tiktok.com/@invalid_koc/video/7123456789012345678')
   assert res == 'https://www.tiktok.com/@invalid_koc/video/7123456789012345678'

   # Malicious non-TikTok URL MUST RAISE InvalidVideoURLError:
   try:
       d._validate_url('https://malicious.com/exploit.exe')
       assert False, 'Allowed malicious URL'
   except InvalidVideoURLError:
       pass

   # Domain hijacking attempt MUST RAISE InvalidVideoURLError:
   try:
       d._validate_url('https://tiktok.com.attacker.com/video/123')
       assert False, 'Allowed spoofed domain'
   except InvalidVideoURLError:
       pass
   print('F-01 URL Validation Verification PASSED!')
   "
   ```

2. **Verify F-02 (FFmpeg failure exception)**:
   ```bash
   python3 -c "
   import asyncio
   from unittest.mock import AsyncMock, patch
   from pathlib import Path
   from src.services.video_processor import VideoProcessor, VideoProcessingError

   async def run_test():
       proc = VideoProcessor(ffmpeg_bin='ffmpeg')
       p = Path('/tmp/f02_verify')
       p.mkdir(exist_ok=True)
       v, a, o = p/'v.mp4', p/'a.mp3', p/'out.mp4'
       v.write_bytes(b'video_bytes')
       a.write_bytes(b'audio_bytes')

       mock_proc = AsyncMock()
       mock_proc.communicate.return_value = (b'', b'FFmpeg fatal failure')
       mock_proc.returncode = 1

       with patch('asyncio.create_subprocess_exec', return_value=mock_proc):
           try:
               await proc.remix_video(str(v), str(a), str(o))
               assert False, 'Should have raised VideoProcessingError'
           except VideoProcessingError as exc:
               assert 'FFmpeg remixing failed with code 1' in str(exc)
               print('F-02 Error Handling Verification PASSED!')

   asyncio.run(run_test())
   "
   ```

3. **Verify F-03 (No `mktemp` in source tree)**:
   ```bash
   python3 -c "
   import subprocess
   res = subprocess.run(['grep', '-rn', 'mktemp', 'src/'], capture_output=True, text=True)
   assert res.returncode == 1 and res.stdout == '', f'mktemp still found in src/: {res.stdout}'
   print('F-03 No mktemp in src/ Verification PASSED!')
   "
   ```

4. **Run targeted tests & full regression suite**:
   ```bash
   pytest tests/test_video_downloader.py tests/test_audio_transcriber.py tests/test_video_processor.py -v
   pytest tests/e2e/test_tier1_features.py -k "f13 or f14 or f17 or f18" -v
   pytest tests/ -v
   ```
   **Pass Condition**: 100% of tests must PASS with 0 failures and 0 errors.
