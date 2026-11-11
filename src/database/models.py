"""AMAS v1.4.0 Domain Data Models.

SQLAlchemy 2.0 DeclarativeBase models with PostgreSQL JSONB and SQLite compatibility.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    synonym,
    validates,
)


# Dual-dialect compilation hook: compile PostgreSQL JSONB as JSON in SQLite
@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


# Dual-dialect column type alias wrapped with MutableDict for in-place mutation tracking
JSONType = MutableDict.as_mutable(JSONB().with_variant(JSON(), "sqlite"))


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy 2.0 declarative models."""
    pass


class Niche(Base):
    """Target market niche partition (e.g. Women's Fashion, Home Utilities)."""
    __tablename__ = "niches"

    niche_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    channels: Mapped[List["Channel"]] = relationship(
        "Channel", back_populates="niche", cascade="all, delete-orphan"
    )
    products: Mapped[List["Product"]] = relationship(
        "Product", back_populates="niche", cascade="all, delete-orphan"
    )
    competitors: Mapped[List["Competitor"]] = relationship(
        "Competitor", back_populates="niche", cascade="all, delete-orphan"
    )
    video_jobs: Mapped[List["VideoJob"]] = relationship(
        "VideoJob", back_populates="niche"
    )


class Channel(Base):
    """TikTok affiliate channel managed via AliasMode anti-detect profile."""
    __tablename__ = "channels"
    __table_args__ = (
        CheckConstraint(
            "lifecycle_status IN ('warming', 'ready_to_post', 'cooldown', 'captcha_blocked')",
            name="chk_channel_lifecycle_status",
        ),
    )

    VALID_LIFECYCLE_STATUSES = {"warming", "ready_to_post", "cooldown", "captcha_blocked"}

    channel_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    niche_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("niches.niche_id", ondelete="CASCADE"), nullable=False
    )
    browser_provider: Mapped[str] = mapped_column(
        String(30), default="aliasmode", server_default="aliasmode"
    )
    browser_profile_id: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )
    proxy_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Lifecycle states: 'warming', 'ready_to_post', 'cooldown', 'captcha_blocked'
    lifecycle_status: Mapped[str] = mapped_column(
        String(30), default="warming", server_default="warming"
    )
    warmup_days_completed: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    last_posted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    max_posts_per_day: Mapped[int] = mapped_column(
        Integer, default=2, server_default="2"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )

    @validates("lifecycle_status")
    def validate_lifecycle_status(self, key: str, value: str) -> str:
        """Kiểm tra tính hợp lệ của lifecycle_status trước khi gán."""
        if value not in self.VALID_LIFECYCLE_STATUSES:
            raise ValueError(f"Invalid lifecycle_status: {value}")
        return value

    # Relationships
    niche: Mapped["Niche"] = relationship("Niche", back_populates="channels")
    video_jobs: Mapped[List["VideoJob"]] = relationship(
        "VideoJob", back_populates="channel"
    )
    comments: Mapped[List["VideoComment"]] = relationship(
        "VideoComment", back_populates="channel", cascade="all, delete-orphan"
    )
    metrics: Mapped[List["Metric"]] = relationship(
        "Metric", back_populates="channel", cascade="all, delete-orphan"
    )


class Competitor(Base):
    """Competitor channel monitored for viral content discovery."""
    __tablename__ = "competitors"

    competitor_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    niche_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("niches.niche_id", ondelete="CASCADE"), nullable=False
    )
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    profile_url: Mapped[str] = mapped_column(String(500), nullable=False)
    followers_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    track_status: Mapped[str] = mapped_column(
        String(30), default="active", server_default="active"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    niche: Mapped["Niche"] = relationship("Niche", back_populates="competitors")


class Product(Base):
    """Scouted and evaluated TikTok Shop affiliate product."""
    __tablename__ = "products"

    product_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    niche_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("niches.niche_id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    commission_rate: Mapped[float] = mapped_column(
        Float, default=0.0, server_default="0.0"
    )
    product_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    sales_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    rating: Mapped[float] = mapped_column(
        Float, default=0.0, server_default="0.0"
    )
    evaluation_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONType, nullable=True
    )
    # Status: 'pending', 'approved', 'rejected', 'published'
    status: Mapped[str] = mapped_column(
        String(30), default="pending", server_default="pending"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    niche: Mapped["Niche"] = relationship("Niche", back_populates="products")
    video_jobs: Mapped[List["VideoJob"]] = relationship(
        "VideoJob", back_populates="product", cascade="all, delete-orphan"
    )


class VideoJob(Base):
    """Video remix and generation workflow job."""
    __tablename__ = "video_jobs"

    job_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    product_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False
    )
    niche_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("niches.niche_id", ondelete="CASCADE"), nullable=False
    )
    channel_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("channels.channel_id", ondelete="SET NULL"), nullable=True
    )
    source_video_url: Mapped[Optional[str]] = mapped_column(
        String(1000), nullable=True
    )
    script: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    audio_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    output_video_path: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )
    rendered_video_path = synonym("output_video_path")

    # Status: 'created', 'scripted', 'audio_generated', 'rendered', 'publishing', 'published', 'failed'
    status: Mapped[str] = mapped_column(
        String(30), default="created", server_default="created"
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="video_jobs")
    niche: Mapped["Niche"] = relationship("Niche", back_populates="video_jobs")
    channel: Mapped[Optional["Channel"]] = relationship(
        "Channel", back_populates="video_jobs"
    )


class VideoComment(Base):
    """Video comment and automated KOC conversion reply."""
    __tablename__ = "video_comments"

    comment_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    channel_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("channels.channel_id", ondelete="CASCADE"), nullable=False
    )
    video_id: Mapped[str] = mapped_column(String(100), nullable=False)
    author_id: Mapped[str] = mapped_column(String(100), nullable=False)
    author_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    comment_text: Mapped[str] = mapped_column(Text, nullable=False)
    # Intent: 'ask_price', 'ask_material_usage', 'complaint', 'other'
    intent: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reply_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Reply status: 'pending', 'replied', 'ignored'
    reply_status: Mapped[str] = mapped_column(
        String(30), default="pending", server_default="pending"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )
    replied_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    channel: Mapped["Channel"] = relationship("Channel", back_populates="comments")


class Metric(Base):
    """Video and channel engagement performance snapshot."""
    __tablename__ = "metrics"

    metric_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    channel_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("channels.channel_id", ondelete="CASCADE"), nullable=False
    )
    video_id: Mapped[str] = mapped_column(String(100), nullable=False)
    views_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    likes_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    comments_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    shares_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    orders_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    estimated_revenue: Mapped[float] = mapped_column(
        Float, default=0.0, server_default="0.0"
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    channel: Mapped["Channel"] = relationship("Channel", back_populates="metrics")
