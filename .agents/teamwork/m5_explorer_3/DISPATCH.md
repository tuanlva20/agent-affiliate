# DISPATCH — m5_explorer_3
Role: TTS Service, Video Processor & Video Studio Pipeline Explorer (Milestone 5)
Workspace: /Users/tuanlva/Folder/workSpace/affiliate
Milestone: M5 (Task 5: Video Remix & Content Engine)
Working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m5_explorer_3/
Parent Conversation ID: f5177315-7404-4813-b8ba-56081885cdd4

Your task:
Khảo sát và thiết kế kiến trúc kỹ thuật cho:
1. `src/services/tts_service.py` (Feature F16):
   - Tích hợp `edge-tts` (Microsoft Edge TTS async) cho tiếng Việt (`vi-VN-HoaiMyNeural`, `vi-VN-NamMinhNeural`).
   - Mock/offline mode khi không có internet/API endpoint.
   - Tính toán duration của file audio xuất ra (mp3/wav) và xử lý lỗi rate-limit.
2. `src/services/video_processor.py` (Feature F17):
   - Pipeline xử lý video lách quét bản quyền bằng FFmpeg:
     * Lật gương ngang (`hflip`).
     * Biến thiên tốc độ nhẹ 1.02–1.08x (`setpts`, `atempo`).
     * Chỉnh màu nhẹ (`eq=contrast=...:brightness=...:saturation=...`).
     * Ghép audio voiceover mới đè lên âm thanh gốc hoặc mix âm lượng nền 10-15%.
     * Chèn khung viền mờ hoặc crop nhẹ (1-2%).
     * Xuất file chuẩn mp4 H.264 / AAC.
3. `src/agents/video_studio.py` (Feature F18):
   - Điều phối toàn bộ quy trình từ `VideoJob`: download video -> transcribe -> generate script -> TTS -> remix FFmpeg -> cập nhật `VideoJob.status = 'rendered'`, lưu `rendered_video_path`.
4. Thiết kế các test suite:
   - `tests/test_tts_service.py`
   - `tests/test_video_processor.py`
5. Viết báo cáo khảo sát kỹ thuật chi tiết tại handoff.md.

## 2026-11-10T11:27:56Z
You are m5_explorer_3, TTS Service, Video Processor & Video Studio Pipeline Explorer for Milestone 5 (Video Remix & Content Engine).
Your working directory is: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m5_explorer_3/
The original request file is: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/ORIGINAL_REQUEST.md
The dispatch file is: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m5_explorer_3/DISPATCH.md
The project scope is in: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/PROJECT.md

Read ORIGINAL_REQUEST.md, DISPATCH.md, and PROJECT.md.
Investigate the technical implementation requirements for:
1. `src/services/tts_service.py` (Feature F16):
   - Contract in `tests/e2e/test_tier1_features.py:test_f16_tts_speech_synthesis`.
   - `edge-tts` async integration, Vietnamese voices (`vi-VN-HoaiMyNeural`, `vi-VN-NamMinhNeural`), duration detection, offline fallback.
2. `src/services/video_processor.py` (Feature F17):
   - Contract in `tests/e2e/test_tier1_features.py:test_f17_ffmpeg_video_processing`.
   - FFmpeg copyright evasion pipeline: hflip, speed jitter 1.02-1.08x, subtle color grading, audio voiceover dubbing / background audio mixing, mp4 H264/AAC output.
3. `src/agents/video_studio.py` (Feature F18):
   - Contract in `tests/e2e/test_tier1_features.py:test_f18_video_studio_pipeline`.
   - End-to-end orchestration from `VideoJob`, database status updates (`VideoJob.status = 'rendered'`).
4. Test specifications for `tests/test_tts_service.py` and `tests/test_video_processor.py`.
Write your report to `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m5_explorer_3/handoff.md`.
Send a message back to parent orchestrator when done.
