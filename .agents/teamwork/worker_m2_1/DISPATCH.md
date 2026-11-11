## 2026-11-10T08:18:47Z
You are worker_m2_1, assigned to implement Milestone 2 (Task 2: Base Scout Infrastructure & Scraper Service: Kalodata Client, TikTok Scraper, Base Scout Agent).

Your working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/worker_m2_1/
Maintain progress.md in your working directory.
Original request file: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/ORIGINAL_REQUEST.md
Project plan: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/PROJECT.md
System spec: /Users/tuanlva/Folder/workSpace/affiliate/SYSTEM_SPEC.md

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Explorer Blueprints to Read First:
1. /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m2_explorer_1/handoff.md (KalodataClient)
2. /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m2_explorer_2/handoff.md (TikTokScraper)
3. /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m2_explorer_3/handoff.md (BaseScoutAgent & ProductCandidate)

## Write Ownership:
You have exclusive write ownership of:
- `src/services/kalodata_client.py`
- `src/services/tiktok_scraper.py`
- `src/agents/base_scout.py`
- `tests/test_kalodata_client.py`
- `tests/test_tiktok_scraper.py`
- Your working directory: `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/worker_m2_1/`

## TDD Implementation Instructions:
Follow strict TDD:

### Step 1: Write Unit Tests (RED Phase)
- In `tests/test_kalodata_client.py`:
  - `test_kalodata_client_token_resolution`: explicit token vs env `KALOPILOT_TOKEN` vs default.
  - `test_kalodata_client_missing_or_expired_token`: raises `PermissionError` when token is missing, empty, or `"expired_token"`.
  - `test_kalodata_client_get_top_products_schema`: returns list of dicts with `product_id`, `title`, `price` > 0, `commission_rate` > 0, `sales_30d`, `revenue_30d`, `product_url`, `category_id`.
  - `test_kalodata_client_limit_and_category`: respects limit argument.
- In `tests/test_tiktok_scraper.py`:
  - `test_tiktok_scraper_download_video_metadata`: returns `TikTokVideoMeta` with `video_id`, `channel_id`, `view_count`, `caption`, `anchor_product_id`.
  - `test_tiktok_scraper_invalid_urls`: raises `ValueError` on empty string or non-tiktok URL.
  - `test_tiktok_scraper_get_recent_videos`: returns list of `TikTokVideoMeta`.
  - `test_tiktok_scraper_extract_anchor_product`: extracts yellow cart anchor product metadata.
  - `test_tiktok_scraper_offline_fallback`: works reliably in test environments without live network or external tools.
- Run `pytest tests/test_kalodata_client.py tests/test_tiktok_scraper.py -v` and document that it FAILS (RED).

### Step 2: Implement Source Code (GREEN Phase)
1. `src/services/kalodata_client.py`:
   - `KalodataClient(token=None, timeout=30.0)`
   - Token precedence: explicit argument -> `os.environ.get("KALOPILOT_TOKEN")` -> `~/.kalopilot/token` file -> mock token fallback.
   - Validation: if token is empty or `"expired_token"`, raise `PermissionError("Kalodata token is missing or expired...")` (or `KalodataAuthError(PermissionError)`).
   - `async def get_top_products(self, category_id: str, limit: int = 10) -> List[Dict[str, Any]]`:
     Returns normalized product dicts.
2. `src/services/tiktok_scraper.py`:
   - `@dataclass class TikTokVideoMeta`: `video_id: str`, `video_url: str`, `channel_id: str`, `channel_url: str`, `view_count: int`, `like_count: int`, `comment_count: int`, `caption: str`, `anchor_product_id: Optional[str] = None`, `anchor_product_title: Optional[str] = None`.
   - `class TikTokScraper`:
     - `async def download_video_metadata(self, video_url: str) -> TikTokVideoMeta`:
       Validate URL (raises `ValueError` if empty or `"tiktok.com"` not in url).
       Parse video_id, channel_id, caption, view_count, anchor_product_id.
     - `async def get_recent_videos(self, channel_url: str, limit: int = 10) -> List[TikTokVideoMeta]`.
     - `async def extract_anchor_product(self, video_url: str) -> Optional[Dict[str, Any]]`.
3. `src/agents/base_scout.py`:
   - `@dataclass class ProductCandidate`: `product_id: str`, `niche_id: str`, `title: str`, `price_vnd: float`, `commission_rate: float`, `sales_30d: int`, `revenue_30d: float`, `product_url: str`, `image_url: Optional[str] = None`, `raw_data: Dict[str, Any] = field(default_factory=dict)`.
     Methods: `to_dict()`, `to_db_product()`.
   - `class BaseScoutAgent`:
     - `__init__(self, config=None)`.
     - `filter_product(self, raw_item: Dict[str, Any], niche_cfg: Any) -> bool`:
       Inspects `niche_cfg` (handles both `niche_cfg.thresholds.min_price_vnd` and flat `niche_cfg.min_price_vnd`).
       Validates price and commission rate.
     - `async def discover_candidates(self, niche_id: str, raw_items: Optional[List[Dict[str, Any]]] = None) -> List[ProductCandidate]`.

### Step 3: Verify All Test Suites (100% PASS)
Run and verify:
1. `pytest tests/test_kalodata_client.py tests/test_tiktok_scraper.py -v`
2. `pytest tests/test_config.py tests/test_database.py tests/test_database_stress.py -v`
3. `pytest tests/e2e/ -v`
4. `python3 scripts/m1_stress_harness.py`
5. Full project suite: `pytest tests/ -v`
