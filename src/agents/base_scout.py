"""AMAS v1.4.0 — Base Scout Agent & ProductCandidate Dataclass (Feature F07).

Performs preliminary market filtering against price boundaries and affiliate commission thresholds.
Normalizes candidate schemas and supports database persistence and autonomous scout discovery.
"""

from __future__ import annotations

import asyncio
import logging
import math
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

GLOBAL_DEFAULT_THRESHOLDS: Dict[str, float] = {
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
        rating = 0.0
        if isinstance(self.raw_data, dict):
            try:
                rating = float(self.raw_data.get("rating", 0.0) or 0.0)
            except (ValueError, TypeError):
                rating = 0.0

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

        price_raw = raw.get("price") if raw.get("price") is not None else raw.get("price_vnd")
        comm_raw = raw.get("commission_rate") if raw.get("commission_rate") is not None else raw.get("commission")
        sales_raw = raw.get("sales_30d") or raw.get("sales_count") or raw.get("sales") or 0
        rev_raw = raw.get("revenue_30d") or raw.get("revenue") or 0.0

        try:
            p_val = float(price_raw) if price_raw is not None else 0.0
            price = 0.0 if (math.isnan(p_val) or math.isinf(p_val)) else p_val
        except (ValueError, TypeError):
            price = 0.0

        try:
            c_val = float(comm_raw) if comm_raw is not None else 0.0
            comm = 0.0 if (math.isnan(c_val) or math.isinf(c_val)) else c_val
        except (ValueError, TypeError):
            comm = 0.0

        try:
            s_val = float(sales_raw)
            sales = 0 if (math.isnan(s_val) or math.isinf(s_val)) else int(s_val)
        except (ValueError, TypeError):
            sales = 0

        try:
            r_val = float(rev_raw) if rev_raw is not None else 0.0
            revenue = 0.0 if (math.isnan(r_val) or math.isinf(r_val)) else r_val
        except (ValueError, TypeError):
            revenue = 0.0
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

        # 1. Validate product_id and title (must be non-empty and not whitespace-only)
        pid = raw_item.get("product_id") or raw_item.get("id")
        title = raw_item.get("title") or raw_item.get("name")
        if pid is None or title is None:
            return False
        pid_clean = str(pid).strip()
        title_clean = str(title).strip()
        if not pid_clean or not title_clean:
            return False

        # 2. Extract and validate price (reject None, NaN, Inf, <= 0.0)
        price_val = raw_item.get("price") if raw_item.get("price") is not None else raw_item.get("price_vnd")
        try:
            if price_val is None:
                return False
            price = float(price_val)
        except (ValueError, TypeError):
            return False

        if math.isnan(price) or math.isinf(price) or price <= 0.0:
            return False

        # 3. Extract and validate commission rate (reject None, NaN, Inf, <= 0.0, > 1.0)
        comm_val = raw_item.get("commission_rate") if raw_item.get("commission_rate") is not None else raw_item.get("commission")
        try:
            if comm_val is None:
                return False
            comm = float(comm_val)
        except (ValueError, TypeError):
            return False

        if math.isnan(comm) or math.isinf(comm) or comm <= 0.0 or comm > 1.0:
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
            categories: List[str] = []
            if niche_cfg and getattr(niche_cfg, "categories", None):
                categories = list(niche_cfg.categories)
            elif niche_id in DEFAULT_NICHE_THRESHOLDS:
                categories = ["women_clothing"] if niche_id == "thoi_trang_nu" else ["home_appliances"]
            else:
                categories = [niche_id]

            # Query at most 2 primary categories concurrently so total runtime stays well under the 300s MCP timeout.
            target_cats = categories[:2]
            batches = await asyncio.gather(
                *(self.kalodata_client.get_top_products(category_id=cat_id, limit=10) for cat_id in target_cats),
                return_exceptions=True,
            )
            seen_ids = set()
            candidates = []
            for cat_id, fetched in zip(target_cats, batches):
                if isinstance(fetched, Exception):
                    logger.error("Kalodata fetch error for category %s: %s", cat_id, fetched)
                    continue
                for item in fetched:
                    item_with_niche = dict(item)
                    item_with_niche.setdefault("niche_id", niche_id)
                    pid = str(item.get("product_id") or "")
                    if pid in seen_ids:
                        continue
                    if self.filter_product(item_with_niche, niche_cfg):
                        seen_ids.add(pid)
                        candidates.append(ProductCandidate.from_raw_dict(item_with_niche, niche_id))

            return candidates

        # If no raw_items and no kalodata_client
        logger.info("No raw_items provided and no kalodata_client configured for niche %s", niche_id)
        return []
