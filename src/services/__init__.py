"""AMAS v1.4.0 — Services Package."""

from src.services.kalodata_client import (
    KalodataAPIError,
    KalodataAuthError,
    KalodataClient,
    KalodataError,
    KalodataNetworkError,
    KalodataTimeoutError,
)
from src.services.tiktok_scraper import (
    InvalidTikTokURLError,
    ScraperTimeoutError,
    TikTokScraper,
    TikTokScraperError,
    TikTokVideoMeta,
    VideoUnavailableError,
)

from src.services.browser_adapter import (
    BrowserAdapter,
    BrowserAdapterError,
    BrowserAPIError,
    BrowserConnectionError,
    BrowserProfileNotFoundError,
    BrowserProxyError,
    BrowserTimeoutError,
    PlaywrightConnectionError,
    ProxyConfig,
    parse_and_validate_proxy,
)
from src.services.comment_scanner import (
    CommentRateLimitError,
    CommentScanner,
    CommentScannerError,
    CommentScannerTimeoutError,
    InvalidVideoIdError,
    VideoNotFoundError,
)
from src.services.human_behavior import (
    HumanBehaviorService,
    compute_cubic_bezier_point,
    generate_bezier_trajectory,
)

__all__ = [
    "KalodataAPIError",
    "KalodataAuthError",
    "KalodataClient",
    "KalodataError",
    "KalodataNetworkError",
    "KalodataTimeoutError",
    "InvalidTikTokURLError",
    "ScraperTimeoutError",
    "TikTokScraper",
    "TikTokScraperError",
    "TikTokVideoMeta",
    "VideoUnavailableError",
    "BrowserAdapter",
    "BrowserAdapterError",
    "BrowserAPIError",
    "BrowserConnectionError",
    "BrowserProfileNotFoundError",
    "BrowserProxyError",
    "BrowserTimeoutError",
    "PlaywrightConnectionError",
    "ProxyConfig",
    "parse_and_validate_proxy",
    "CommentScanner",
    "CommentScannerError",
    "InvalidVideoIdError",
    "CommentScannerTimeoutError",
    "CommentRateLimitError",
    "VideoNotFoundError",
    "HumanBehaviorService",
    "compute_cubic_bezier_point",
    "generate_bezier_trajectory",
]
