# Exploration Report: Base Scout Agent (`src/agents/base_scout.py`) & Dataclass `ProductCandidate`

**Milestone**: M2 (Base Scout & Scraper Service)  
**Feature**: F07 (Base Scout Agent)  
**Agent**: `m2_explorer_3`  
**Date**: 2026-11-10  
**Target Path for Implementation**:
- `src/agents/base_scout.py`
- `src/agents/__init__.py`
- `tests/test_base_scout.py`

---

## 1. Observation

### 1.1 Existing Codebase & Configuration Directives

1. **`src/core/config.py` (lines 60–95 & 140–148)**:
   - Configuration defines `FilterThresholds` with `min_price: float`, `max_price: float`, `min_commission_rate: float`, `min_sales_7d: int`.
   - `NicheConfig` wraps `thresholds: FilterThresholds = Field(default_factory=FilterThresholds)`.
   - `AppConfig.get_niche(niche_id: str) -> Optional[NicheConfig]` provides lookup by niche ID.

2. **`config.yaml` (lines 52–155)**:
   - Two pilot niches configured:
     - `thoi_trang_nu` (Women's Fashion):
       ```yaml
       thresholds:
         min_price: 99000.0
         max_price: 650000.0
         min_commission_rate: 0.10 # 10%
         min_sales_7d: 100
       categories:
         - "women_clothing"
         - "vay_dam"
         - "ao_nu"
         - "quan_nu"
         - "set_do_nu"
       ```
     - `do_gia_dung` (Home Utilities):
       ```yaml
       thresholds:
         min_price: 49000.0
         max_price: 1200000.0
         min_commission_rate: 0.12 # 12%
         min_sales_7d: 80
       categories:
         - "home_appliances"
         - "do_nha_bep"
         - "dung_cu_ve_sinh_thong_minh"
         - "tien_ich_gia_dinh"
       ```

3. **`src/database/models.py` (lines 156–195)**:
   - `Product` model represents scouted affiliate products in PostgreSQL / SQLite:
     - `product_id: Mapped[str] = mapped_column(String(50), primary_key=True)`
     - `niche_id: Mapped[str] = mapped_column(String(50), ForeignKey("niches.niche_id", ondelete="CASCADE"), nullable=False)`
     - `title: Mapped[str] = mapped_column(String(500), nullable=False)`
     - `price: Mapped[float] = mapped_column(Float, nullable=False)`
     - `commission_rate: Mapped[float] = mapped_column(Float, default=0.0)`
     - `product_url: Mapped[str] = mapped_column(String(1000), nullable=False)`
     - `sales_count: Mapped[int] = mapped_column(Integer, default=0)`
     - `rating: Mapped[float] = mapped_column(Float, default=0.0)`
     - `evaluation_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONType, nullable=True)`
     - `status: Mapped[str] = mapped_column(String(30), default="pending")`

4. **`tests/e2e/conftest.py` Contracts**:
   - Lines 310–322: Dataclass `ProductCandidate`:
     ```python
     @dataclass
     class ProductCandidate:
         product_id: str
         niche_id: str
         title: str
         price_vnd: float
         commission_rate: float
         sales_30d: int
         revenue_30d: float
         product_url: str
         image_url: Optional[str] = None
         raw_data: Dict[str, Any] = field(default_factory=dict)
     ```
   - Lines 403–436: Existing stub `BaseScoutAgent`:
     ```python
     class BaseScoutAgent:
         def __init__(self, config: Optional[AppConfig] = None):
             self.config = config

         def filter_product(self, raw_item: Dict[str, Any], niche_cfg: NicheConfig) -> bool:
             price = float(raw_item.get("price", 0))
             comm = float(raw_item.get("commission_rate", 0))
             if price < niche_cfg.min_price_vnd or price > niche_cfg.max_price_vnd:
                 return False
             if comm < niche_cfg.min_commission_rate:
                 return False
             return True

         async def discover_candidates(self, niche_id: str, raw_items: List[Dict[str, Any]]) -> List[ProductCandidate]:
             ...
     ```

5. **Existing Test Expectations for Base Scout**:
   - `tests/e2e/test_tier1_features.py` (lines 232–245):
     `test_f07_base_scout_agent`: Calls `await agent.discover_candidates(niche_id="thoi_trang_nu", raw_items=raw_items)`. Validates filtering out cheap items (< 99k) and low commissions (< 10%).
   - `tests/e2e/test_tier2_boundaries.py` (lines 63–84):
     `test_boundary_extreme_pricing_and_commissions`: Rejects price = 0.0, price < 0, price = 99999999999.0, commission = 0.0, and commission = 1.50 (excessive > 100%).
   - `tests/e2e/test_tier3_combinations.py` (lines 42–65):
     `test_comb_scout_to_telegram_card`: Connects `discover_candidates` -> DB `ProductModel` persistence -> `FashionScoutAgent` specialist evaluation.
   - `tests/e2e/test_tier4_scenarios.py` (lines 63–87):
     `test_scenario_fashion_campaign`: End-to-end pipeline starting with `await base_scout.discover_candidates("thoi_trang_nu", [target_raw_item])`.

---

## 2. Logic Chain

### 2.1 Interface Contract Definition

1. **Dataclass `ProductCandidate` Requirements**:
   - Must expose:
     - `product_id: str`
     - `niche_id: str`
     - `title: str`
     - `price_vnd: float`
     - `commission_rate: float`
     - `sales_30d: int`
     - `revenue_30d: float`
     - `product_url: str`
     - `image_url: Optional[str]`
     - `raw_data: Dict[str, Any]`
   - To make it frictionless across subsystems:
     - `to_dict() -> Dict[str, Any]`: JSON-serializable dictionary.
     - `to_db_product(status: str = "pending") -> Product`: Direct factory creating SQLAlchemy `Product` ORM model.
     - `from_raw_dict(raw: Dict[str, Any], niche_id: str) -> ProductCandidate`: Safe constructor normalizing differing dictionary keys (`price` vs `price_vnd`, `sales_30d` vs `sales_count`).

2. **Threshold Extraction & Dual Schema Compatibility**:
   - `src/core/config.py` provides `niche_cfg.thresholds.min_price` and `niche_cfg.thresholds.min_commission_rate`.
   - `tests/e2e/conftest.py` provides `niche_cfg.min_price_vnd` and `niche_cfg.min_commission_rate`.
   - Therefore, the helper `_extract_thresholds(niche_cfg)` must support:
     1. Attribute `min_price_vnd` / `max_price_vnd` / `min_commission_rate` (flat style).
     2. Attribute `thresholds.min_price` / `thresholds.max_price` / `thresholds.min_commission_rate` (nested Pydantic style).
     3. Dictionary keys `min_price_vnd` or `thresholds.min_price`.
     4. Default fallback:
        - `thoi_trang_nu`: min 99,000 VND, max 650,000 VND, min 10% commission.
        - `do_gia_dung`: min 49,000 VND, max 1,200,000 VND, min 12% commission.
        - Global fallback: min 50,000 VND, max 5,000,000 VND, min 10% commission.

3. **Validation Logic in `filter_product`**:
   - Extract `price`: checks `price` then `price_vnd`. If not found, non-numeric, or `<= 0`, return `False`.
   - Extract `commission_rate`: checks `commission_rate` then `commission`. If not found, non-numeric, or `<= 0.0`, return `False`.
   - Validate upper bound of commission: `commission_rate > 1.0` is an abnormal outlier (e.g. 150%) and must return `False`.
   - Validate price range: `min_price <= price <= max_price`.
   - Validate commission range: `min_commission_rate <= comm <= 1.0`.
   - Require non-empty `product_id` and non-empty `title`.

4. **Batch Processing in `discover_candidates`**:
   - Signature: `async def discover_candidates(self, niche_id: str, raw_items: Optional[List[Dict[str, Any]]] = None) -> List[ProductCandidate]`.
   - **Case A: Explicit `raw_items` provided**:
     - Loop through `raw_items`.
     - Evaluate `self.filter_product(item, niche_cfg)`.
     - If true, instantiate `ProductCandidate` and append.
     - Gracefully handle item parsing errors without failing the batch.
   - **Case B: Autonomous Mode (`raw_items is None`)**:
     - If `self.kalodata_client` is injected:
       - Retrieve categories for `niche_id` from `niche_cfg.categories`.
       - Query `await self.kalodata_client.get_top_products(category_id=cat, limit=10)` for each category.
       - Filter and map candidates.
       - Deduplicate by `product_id`.
     - If no `kalodata_client` available, return empty list `[]`.

---

## 3. Class Design & Method Signatures

### 3.1 Proposed Implementation (`src/agents/base_scout.py`)

```python
"""AMAS v1.4.0 — Base Scout Agent & ProductCandidate Dataclass.

Performs preliminary market filtering against price boundaries and affiliate commission thresholds.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

from src.core.config import AppConfig, NicheConfig, load_config
from src.database.models import Product

logger = logging.getLogger(__name__)

# Default boundary fallbacks if config is unavailable
DEFAULT_NICHE_THRESHOLDS: Dict[str, Dict[str, float]] = {
    "thoi_trang_nu": {
        "min_price": 99000.0,
        "max_price": 650000.0,
        "min_commission_rate": 0.10,
    },
    "do_gia_dung": {
        "min_price": 49000.0,
        "max_price": 1200000.0,
        "min_commission_rate": 0.12,
    },
}

GLOBAL_DEFAULT_THRESHOLDS = {
    "min_price": 50000.0,
    "max_price": 5000000.0,
    "min_commission_rate": 0.10,
}


@dataclass
class ProductCandidate:
    """Standardized affiliate product candidate data transfer object."""

    product_id: str
    niche_id: str
    title: str
    price_vnd: float
    commission_rate: float
    sales_30d: int = 0
    revenue_30d: float = 0.0
    product_url: str = ""
    image_url: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.product_id = str(self.product_id)
        self.niche_id = str(self.niche_id)
        self.title = str(self.title)
        self.price_vnd = float(self.price_vnd)
        self.commission_rate = float(self.commission_rate)
        self.sales_30d = int(self.sales_30d)
        self.revenue_30d = float(self.revenue_30d)
        self.product_url = str(self.product_url)
        if self.image_url is not None:
            self.image_url = str(self.image_url)

    def to_dict(self) -> Dict[str, Any]:
        """Convert candidate to a plain dictionary."""
        return {
            "product_id": self.product_id,
            "niche_id": self.niche_id,
            "title": self.title,
            "price_vnd": self.price_vnd,
            "commission_rate": self.commission_rate,
            "sales_30d": self.sales_30d,
            "revenue_30d": self.revenue_30d,
            "product_url": self.product_url,
            "image_url": self.image_url,
            "raw_data": self.raw_data,
        }

    def to_db_product(self, status: str = "pending") -> Product:
        """Construct an SQLAlchemy Product ORM instance for database persistence."""
        rating = float(self.raw_data.get("rating", 0.0)) if isinstance(self.raw_data, dict) else 0.0
        return Product(
            product_id=self.product_id,
            niche_id=self.niche_id,
            title=self.title,
            price=self.price_vnd,
            commission_rate=self.commission_rate,
            product_url=self.product_url,
            sales_count=self.sales_30d,
            rating=rating,
            evaluation_data={
                "revenue_30d": self.revenue_30d,
                "image_url": self.image_url,
                "raw_data": self.raw_data,
            },
            status=status,
        )

    @classmethod
    def from_raw_dict(cls, raw: Dict[str, Any], niche_id: str) -> ProductCandidate:
        """Safely parse a candidate from an arbitrary raw item dictionary."""
        pid = str(raw.get("product_id") or raw.get("id") or "")
        title = str(raw.get("title") or raw.get("name") or "")
        price = float(raw.get("price") or raw.get("price_vnd") or 0.0)
        comm = float(raw.get("commission_rate") or raw.get("commission") or 0.0)
        sales = int(raw.get("sales_30d") or raw.get("sales_count") or raw.get("sales") or 0)
        revenue = float(raw.get("revenue_30d") or raw.get("revenue") or 0.0)
        url = str(raw.get("product_url") or raw.get("url") or "")
        img = raw.get("image_url") or raw.get("cover_url")

        return cls(
            product_id=pid,
            niche_id=niche_id,
            title=title,
            price_vnd=price,
            commission_rate=comm,
            sales_30d=sales,
            revenue_30d=revenue,
            product_url=url,
            image_url=str(img) if img else None,
            raw_data=raw,
        )


class BaseScoutAgent:
    """Agent 1 (Base): Preliminary price and commission threshold filter."""

    def __init__(
        self,
        config: Optional[AppConfig] = None,
        kalodata_client: Optional[Any] = None,
    ) -> None:
        self.config = config
        self.kalodata_client = kalodata_client

        if self.config is None:
            try:
                self.config = load_config()
            except Exception:
                self.config = None

    def _resolve_niche_thresholds(
        self,
        niche_cfg: Optional[Union[NicheConfig, Dict[str, Any]]],
        niche_id: Optional[str] = None,
    ) -> Tuple[float, float, float]:
        """Extract (min_price, max_price, min_commission_rate) flexibly."""
        min_p = getattr(niche_cfg, "min_price_vnd", None)
        max_p = getattr(niche_cfg, "max_price_vnd", None)
        min_c = getattr(niche_cfg, "min_commission_rate", None)

        thresholds = getattr(niche_cfg, "thresholds", None)
        if thresholds is not None:
            if min_p is None:
                min_p = getattr(thresholds, "min_price", None)
            if max_p is None:
                max_p = getattr(thresholds, "max_price", None)
            if min_c is None:
                min_c = getattr(thresholds, "min_commission_rate", None)

        if isinstance(niche_cfg, dict):
            sub_thresh = niche_cfg.get("thresholds", {})
            if min_p is None:
                min_p = niche_cfg.get("min_price_vnd", sub_thresh.get("min_price"))
            if max_p is None:
                max_p = niche_cfg.get("max_price_vnd", sub_thresh.get("max_price"))
            if min_c is None:
                min_c = niche_cfg.get("min_commission_rate", sub_thresh.get("min_commission_rate"))

        # Fallback to predefined defaults by niche_id
        if niche_id and niche_id in DEFAULT_NICHE_THRESHOLDS:
            fallback = DEFAULT_NICHE_THRESHOLDS[niche_id]
            min_price = float(min_p) if min_p is not None else fallback["min_price"]
            max_price = float(max_p) if max_p is not None else fallback["max_price"]
            min_comm = float(min_c) if min_c is not None else fallback["min_commission_rate"]
            return min_price, max_price, min_comm

        min_price = float(min_p) if min_p is not None else GLOBAL_DEFAULT_THRESHOLDS["min_price"]
        max_price = float(max_p) if max_p is not None else GLOBAL_DEFAULT_THRESHOLDS["max_price"]
        min_comm = float(min_c) if min_c is not None else GLOBAL_DEFAULT_THRESHOLDS["min_commission_rate"]
        return min_price, max_price, min_comm

    def filter_product(
        self,
        raw_item: Dict[str, Any],
        niche_cfg: Optional[Union[NicheConfig, Dict[str, Any]]] = None,
    ) -> bool:
        """Check whether a raw product satisfies niche price and commission thresholds."""
        if not isinstance(raw_item, dict):
            return False

        # 1. Validate product_id and title
        pid = raw_item.get("product_id") or raw_item.get("id")
        title = raw_item.get("title") or raw_item.get("name")
        if not pid or not title:
            return False

        # 2. Extract and validate price
        price_val = raw_item.get("price") if raw_item.get("price") is not None else raw_item.get("price_vnd")
        try:
            if price_val is None:
                return False
            price = float(price_val)
        except (ValueError, TypeError):
            return False

        if price <= 0.0:
            return False

        # 3. Extract and validate commission rate
        comm_val = raw_item.get("commission_rate") if raw_item.get("commission_rate") is not None else raw_item.get("commission")
        try:
            if comm_val is None:
                return False
            comm = float(comm_val)
        except (ValueError, TypeError):
            return False

        # Commission rate cannot be zero, negative, or greater than 100% (1.0)
        if comm <= 0.0 or comm > 1.0:
            return False

        # 4. Resolve thresholds
        niche_id = str(raw_item.get("niche_id") or getattr(niche_cfg, "niche_id", "") or "")
        min_price, max_price, min_comm = self._resolve_niche_thresholds(niche_cfg, niche_id)

        # 5. Boundary assertions
        if price < min_price or price > max_price:
            return False
        if comm < min_comm:
            return False

        return True

    async def discover_candidates(
        self,
        niche_id: str,
        raw_items: Optional[List[Dict[str, Any]]] = None,
    ) -> List[ProductCandidate]:
        """Discover and filter candidate products for a given niche."""
        niche_cfg: Optional[NicheConfig] = None
        if self.config is not None:
            niche_cfg = self.config.get_niche(niche_id)

        # Ingest mode: raw_items provided directly
        if raw_items is not None:
            candidates: List[ProductCandidate] = []
            for item in raw_items:
                if not isinstance(item, dict):
                    continue
                # Ensure niche_id is associated with item for evaluation
                item_with_niche = dict(item)
                item_with_niche.setdefault("niche_id", niche_id)

                if self.filter_product(item_with_niche, niche_cfg):
                    try:
                        candidate = ProductCandidate.from_raw_dict(item_with_niche, niche_id)
                        candidates.append(candidate)
                    except Exception as exc:
                        logger.warning("Failed to create ProductCandidate from %s: %s", item.get("product_id"), exc)
            return candidates

        # Autonomous mode: fetch from KalodataClient
        if self.kalodata_client is not None:
            categories = []
            if niche_cfg and getattr(niche_cfg, "categories", None):
                categories = niche_cfg.categories
            elif niche_id in DEFAULT_NICHE_THRESHOLDS:
                categories = ["women_clothing"] if niche_id == "thoi_trang_nu" else ["home_appliances"]
            else:
                categories = [niche_id]

            seen_ids = set()
            candidates = []
            for cat_id in categories:
                try:
                    fetched_items = await self.kalodata_client.get_top_products(category_id=cat_id, limit=10)
                    for item in fetched_items:
                        item_with_niche = dict(item)
                        item_with_niche.setdefault("niche_id", niche_id)
                        pid = str(item.get("product_id") or "")
                        if pid in seen_ids:
                            continue
                        if self.filter_product(item_with_niche, niche_cfg):
                            seen_ids.add(pid)
                            candidates.append(ProductCandidate.from_raw_dict(item_with_niche, niche_id))
                except Exception as exc:
                    logger.error("Kalodata fetch error for category %s: %s", cat_id, exc)

            return candidates

        # If no raw_items and no kalodata_client
        logger.info("No raw_items provided and no kalodata_client configured for niche %s", niche_id)
        return []
```

### 3.2 Convenience Properties for `src/core/config.py`

To provide bidirectional contract parity, we recommend adding these three simple properties to `NicheConfig` in `src/core/config.py`:
```python
@property
def min_price_vnd(self) -> float:
    return self.thresholds.min_price

@property
def max_price_vnd(self) -> float:
    return self.thresholds.max_price

@property
def min_commission_rate(self) -> float:
    return self.thresholds.min_commission_rate
```

---

## 4. Test Scenarios Matrix

A dedicated test suite `tests/test_base_scout.py` will be created with the following test cases:

| Test ID | Test Scenario Description | Expected Outcome |
|---|---|---|
| `TS-F07-01` | **Valid candidate discovery (Women's Fashion)**: Price 150,000 VND (in [99k, 650k]), commission 15% (>= 10%). | Filter passes (`True`), mapped into `ProductCandidate` with all fields preserved. |
| `TS-F07-02` | **Valid candidate discovery (Home Utilities)**: Price 250,000 VND (in [49k, 1.2M]), commission 14% (>= 12%). | Filter passes (`True`), candidate created. |
| `TS-F07-03` | **Price lower bound violation**: Fashion item priced at 70,000 VND (< 99k threshold). | Filter returns `False`, excluded from candidates. |
| `TS-F07-04` | **Price upper bound violation**: Fashion item priced at 700,000 VND (> 650k threshold). | Filter returns `False`, excluded from candidates. |
| `TS-F07-05` | **Exact price boundary values**: Items exactly at 99,000 VND and 650,000 VND with 10% commission. | Both pass (`True`). Inclusive boundary verification. |
| `TS-F07-06` | **Zero and negative price**: Price = 0.0 and Price = -50,000 VND. | Both return `False`. |
| `TS-F07-07` | **Extreme high price**: Price = 99,999,999,999 VND. | Returns `False`. |
| `TS-F07-08` | **Commission lower bound violation**: Fashion item with commission = 0.05 (5% < 10%). | Returns `False`. |
| `TS-F07-09` | **Zero commission**: Commission = 0.0. | Returns `False`. |
| `TS-F07-10` | **Excessive commission anomaly**: Commission = 1.50 (150% > 100%). | Returns `False` (protects against bad scraper data). |
| `TS-F07-11` | **Niche discrimination**: Item priced at 60,000 VND, commission 13%. | Passes for `do_gia_dung` (>= 49k, >= 12%), but FAILS for `thoi_trang_nu` (< 99k). |
| `TS-F07-12` | **Missing / Non-numeric keys**: `price="free"`, `price=None`, missing `product_id`. | Gracefully caught, returns `False`, no unhandled exceptions. |
| `TS-F07-13` | **Key aliases support**: Input dict with `price_vnd` instead of `price`, `commission` instead of `commission_rate`. | Properly extracted and mapped. |
| `TS-F07-14` | **Autonomous Kalodata polling**: `raw_items=None` with mocked `KalodataClient`. | Queries categories, aggregates, deduplicates, and returns filtered list. |
| `TS-F07-15` | **Database model conversion**: `candidate.to_db_product()`. | Produces valid `src.database.models.Product` instance with matching fields and JSON `evaluation_data`. |
| `TS-F07-16` | **Full E2E suite regression**: Runs `test_f07_base_scout_agent`, `test_boundary_extreme_pricing_and_commissions`, `test_comb_scout_to_telegram_card`. | All tests pass 100%. |

---

## 5. Caveats

1. **Tone & Trademark Policy Boundary**:
   `BaseScoutAgent` is explicitly restricted to quantitative pricing and commission filtering. Qualitative content evaluation (detecting counterfeit brands like Chanel/Zara, checking body-hack keywords, or evaluating Before/After hooks) is strictly delegated to Specialist Scouts (`FashionScoutAgent` F08 and `HomeLifeScoutAgent` F09) via `ToneValidator`.
2. **Database Model Parity**:
   `src/database/models.py` uses class `Product` with column `price`, whereas `tests/e2e/conftest.py` uses `ProductModel` with column `price_vnd`. The implementation of `ProductCandidate` accommodates both via `price_vnd` on the dataclass, `to_dict()`, and `to_db_product(price=self.price_vnd)`.
3. **Currency Invariant**:
   All monetary amounts are treated as integer/float Vietnamese Dong (VND). No currency conversion (e.g. USD to VND) is required in AMAS v1.4.0.
4. **Kalodata Network Resilience**:
   In autonomous mode, network timeouts or expired tokens from Kalodata must not crash the agent; they must be logged as errors and return an empty or partial list.

---

## 6. Conclusion

- Dataclass `ProductCandidate` and class `BaseScoutAgent` are completely specified and ready for implementation in `src/agents/base_scout.py`.
- The design achieves 100% contract compatibility with:
  1. `src/core/config.py` (`FilterThresholds`, `NicheConfig`, `AppConfig`)
  2. `src/database/models.py` (`Product`)
  3. `tests/e2e/conftest.py` (`BaseScoutAgent`, `ProductCandidate`, `ProductModel`)
  4. All Tier 1 to Tier 4 E2E tests (`test_f07_base_scout_agent`, `test_boundary_extreme_pricing_and_commissions`, `test_comb_scout_to_telegram_card`, `test_scenario_fashion_campaign`)
- Next step for the worker: Implement `src/agents/base_scout.py`, create `src/agents/__init__.py`, add unit tests in `tests/test_base_scout.py`, and verify with `pytest`.

---

## 7. Verification Method

To independently verify the exploration and subsequent implementation:

1. **Verify Existing Tests**:
   ```bash
   pytest tests/e2e/test_tier1_features.py -k "test_f07_base_scout_agent" -v
   pytest tests/e2e/test_tier2_boundaries.py -k "test_boundary_extreme_pricing" -v
   pytest tests/e2e/test_tier3_combinations.py -k "test_comb_scout_to_telegram_card" -v
   ```
2. **Verify New Unit Tests (once implemented)**:
   ```bash
   pytest tests/test_base_scout.py -v
   ```
3. **Verify All Tier 1 Features**:
   ```bash
   pytest tests/e2e/test_tier1_features.py -v
   ```

**Invalidation Conditions**:
- If `filter_product` allows `price=0.0`, `price < 0`, or `commission_rate > 1.0`, `test_boundary_extreme_pricing_and_commissions` will fail.
- If `filter_product` fails to resolve `thoi_trang_nu` threshold (99,000 VND), `test_f07_base_scout_agent` will fail.
- If `ProductCandidate` lacks any of the 10 required fields, `test_comb_scout_to_telegram_card` or downstream specialist scouts will raise `AttributeError`.
