"""Unit tests for Video Downloader Service (Feature F13)."""

import os
from pathlib import Path
import pytest

from src.services.video_downloader import (
    InvalidVideoURLError,
    VideoDownloader,
    VideoDownloaderError,
)


class TestVideoDownloader:
    """Verifies F13 Video Downloader contracts and behavior."""

    @pytest.mark.asyncio
    async def test_download_video_success_mock(self, tmp_path):
        downloader = VideoDownloader(output_dir=tmp_path / "downloads", mock_mode=True)
        url = "https://tiktok.com/@competitor/video/712345"
        path = await downloader.download_video(url)

        assert os.path.exists(path)
        assert path.endswith(".mp4")
        assert os.path.getsize(path) > 0

    @pytest.mark.asyncio
    async def test_download_video_custom_output_path(self, tmp_path):
        downloader = VideoDownloader(mock_mode=True)
        custom_out = tmp_path / "custom_dir" / "my_video.mp4"
        path = await downloader.download_video(
            "https://tiktok.com/@competitor/video/712345",
            output_path=str(custom_out),
        )

        assert path == str(custom_out)
        assert os.path.exists(custom_out)

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

    @pytest.mark.asyncio
    async def test_download_video_mp4_header(self, tmp_path):
        downloader = VideoDownloader(mock_mode=True)
        out = tmp_path / "header_test.mp4"
        await downloader.download_video(
            "https://tiktok.com/@competitor/video/9999",
            output_path=str(out),
        )
        assert out.exists()
        header = out.read_bytes()[:12]
        # MP4 ftyp box signature
        assert b"ftyp" in header
