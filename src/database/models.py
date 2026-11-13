"""AMAS v1.4.0 Domain Data Models.

SQLAlchemy 2.0 DeclarativeBase models with PostgreSQL JSONB and SQLite compatibility.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.mutable import MutableDict, MutableList
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


# Dual-dialect column type alias wrapped with MutableDict/MutableList for in-place mutation tracking
JSONType = MutableDict.as_mutable(JSONB().with_variant(JSON(), "sqlite"))
JSONListType = MutableList.as_mutable(JSONB().with_variant(JSON(), "sqlite"))



class Base(DeclarativeBase):
    """Base class for all SQLAlchemy 2.0 declarative models."""
    pass


class Project(Base):
    """Google Cloud Console style Multi-Project Workspace partition."""
    __tablename__ = "projects"

    project_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    niche_brief: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    target_audience: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tone_of_voice: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    trigger_keywords: Mapped[Optional[List[str]]] = mapped_column(JSONListType, nullable=True)
    negative_keywords: Mapped[Optional[List[str]]] = mapped_column(JSONListType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )


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
    project_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("projects.project_id", ondelete="SET NULL"), nullable=True
    )
    niche_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("niches.niche_id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[str] = mapped_column(
        String(30), default="tiktok", server_default="tiktok"
    )
    account_type: Mapped[str] = mapped_column(
        String(30), default="profile", server_default="profile"
    )
    platform_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONType, nullable=True
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
    __table_args__ = (
        CheckConstraint("scrape_interval_hours >= 2", name="chk_competitor_scrape_interval_hours"),
    )

    competitor_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    project_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("projects.project_id", ondelete="SET NULL"), nullable=True
    )
    niche_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("niches.niche_id", ondelete="CASCADE"), nullable=False
    )
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    profile_url: Mapped[str] = mapped_column(String(500), nullable=False)
    followers_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    platform: Mapped[str] = mapped_column(
        String(30), default="tiktok", server_default="tiktok"
    )
    scrape_interval_hours: Mapped[int] = mapped_column(
        Integer, default=4, server_default="4"
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
    project_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("projects.project_id", ondelete="SET NULL"), nullable=True
    )
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
    motion_mode: Mapped[str] = mapped_column(
        String(50), default="replicate_motion_control", server_default="replicate_motion_control"
    )
    character_image_url: Mapped[Optional[str]] = mapped_column(
        String(1000), nullable=True
    )
    product_image_url: Mapped[Optional[str]] = mapped_column(
        String(1000), nullable=True
    )
    segments_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONType, nullable=True
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


class Proxy(Base):
    """Managed proxy pool inventory for channel assignment."""
    __tablename__ = "proxies"

    proxy_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    proxy_url: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    protocol: Mapped[str] = mapped_column(String(20), default="http", server_default="http")
    status: Mapped[str] = mapped_column(String(30), default="unchecked", server_default="unchecked")
    assigned_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )


class MotionAsset(Base):
    """Motion template and extracted movement patterns for Motion Control."""
    __tablename__ = "motion_assets"

    asset_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    source_type: Mapped[str] = mapped_column(String(50), default="competitor_video", server_default="competitor_video")
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    cover_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    duration: Mapped[float] = mapped_column(Float, default=0.0, server_default="0.0")
    motion_features: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONType, nullable=True)
    is_official: Mapped[bool] = mapped_column(default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )


class PublishLog(Base):
    """Multi-channel video publishing dispatch history and outcomes."""
    __tablename__ = "publish_logs"

    log_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    project_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("projects.project_id", ondelete="SET NULL"), nullable=True
    )
    job_id: Mapped[str] = mapped_column(String(50), ForeignKey("video_jobs.job_id", ondelete="CASCADE"), nullable=False)
    channel_id: Mapped[str] = mapped_column(String(50), ForeignKey("channels.channel_id", ondelete="CASCADE"), nullable=False)
    platform: Mapped[str] = mapped_column(String(30), default="tiktok", server_default="tiktok")
    published_video_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    published_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", server_default="pending")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )


class CompetitorScrapeLog(Base):
    """Historical record of competitor scanning and scraping runs."""
    __tablename__ = "competitor_scrape_logs"

    log_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    competitor_id: Mapped[str] = mapped_column(String(50), ForeignKey("competitors.competitor_id", ondelete="CASCADE"), nullable=False)
    videos_found: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    status: Mapped[str] = mapped_column(String(30), default="success", server_default="success")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )


class CompetitorVideo(Base):
    """Individual competitor video assets discovered and archived."""
    __tablename__ = "competitor_videos"

    video_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    project_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("projects.project_id", ondelete="SET NULL"), nullable=True
    )
    competitor_id: Mapped[str] = mapped_column(String(50), ForeignKey("competitors.competitor_id", ondelete="CASCADE"), nullable=False)
    platform: Mapped[str] = mapped_column(String(30), default="tiktok", server_default="tiktok")
    video_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    caption: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    views_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    likes_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    product_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )


class ProjectGroup(Base):
    """Facebook Group managed within a Project workspace."""
    __tablename__ = "project_groups"
    __table_args__ = (
        CheckConstraint("privacy IN ('public', 'private')", name="chk_project_group_privacy"),
    )

    group_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False
    )
    group_url: Mapped[str] = mapped_column(String(500), nullable=False)
    group_name: Mapped[str] = mapped_column(String(200), nullable=False)
    privacy: Mapped[str] = mapped_column(String(20), default="public", server_default="public")
    approval_mode: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    last_scanned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )


class GroupCommentLog(Base):
    """Marketing and interaction log for comments in monitored groups."""
    __tablename__ = "group_comment_logs"
    __table_args__ = (
        UniqueConstraint("group_id", "post_id", name="uq_group_comment_log_group_post"),
    )

    log_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    group_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("project_groups.group_id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=True
    )
    post_id: Mapped[str] = mapped_column(String(150), nullable=False)
    post_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    matched_keyword: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    comment_text: Mapped[str] = mapped_column(Text, nullable=False)
    channel_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("channels.channel_id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )


class PublishSchedule(Base):
    """Multi-platform content calendar publishing schedule."""
    __tablename__ = "publish_schedules"
    __table_args__ = (
        CheckConstraint(
            "status IN ('scheduled', 'publishing', 'published', 'failed')",
            name="chk_publish_schedule_status",
        ),
        CheckConstraint(
            "platform IN ('tiktok', 'facebook', 'instagram')",
            name="chk_publish_schedule_platform",
        ),
        CheckConstraint(
            "target_type IN ('reel', 'post', 'group')",
            name="chk_publish_schedule_target_type",
        ),
    )

    schedule_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    project_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=True
    )
    channel_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("channels.channel_id", ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("video_jobs.job_id", ondelete="SET NULL"), nullable=True
    )
    platform: Mapped[str] = mapped_column(String(30), default="tiktok", server_default="tiktok")
    target_type: Mapped[str] = mapped_column(String(30), default="reel", server_default="reel")
    target_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    caption: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="scheduled", server_default="scheduled")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )


