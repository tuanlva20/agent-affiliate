"""Initialize AMAS PostgreSQL/SQLite schema and seed pilot niches idempotently."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from urllib.parse import quote_plus

# Ensure repository root is importable when invoked as `python scripts/init_db.py`
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy import select
from sqlalchemy.engine import make_url

from src.core.config import AppConfig, load_config
from src.database.models import Base, Niche
from src.database.session import get_async_engine, get_session_factory


def _load_env_file(env_path: Path) -> None:
    """Load .env via python-dotenv if available, or fall back to KEY=VALUE parsing."""
    try:
        from dotenv import load_dotenv

        load_dotenv(env_path)
        return
    except ImportError:
        pass

    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value and value[0] in ('"', "'") and value[-1] == value[0] and len(value) >= 2:
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].strip()
        if key and key not in os.environ:
            os.environ[key] = value


def _resolve_config_path(config_path: str) -> Path:
    """Resolve config path from CWD first, then fall back to REPO_ROOT."""
    candidate = Path(config_path)
    if candidate.exists() or candidate.is_absolute():
        return candidate
    repo_candidate = REPO_ROOT / config_path
    return repo_candidate if repo_candidate.exists() else candidate


def _normalize_async_url(url: str) -> str:
    """Ensure PostgreSQL URLs use the asyncpg driver expected by SQLAlchemy AsyncEngine."""
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://") :]
    return url


def _resolve_database_url(config: AppConfig, explicit_url: str | None) -> str:
    """Resolve target database URL with explicit > env > POSTGRES_* > config.yaml precedence."""
    if explicit_url:
        return _normalize_async_url(explicit_url)

    env_url = os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL")
    if env_url:
        return _normalize_async_url(env_url)

    pg_keys = ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB", "POSTGRES_PORT")
    if any(os.getenv(k) for k in pg_keys):
        user = quote_plus(os.getenv("POSTGRES_USER", "postgres"))
        password = quote_plus(os.getenv("POSTGRES_PASSWORD", "postgres"))
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5433")
        db = os.getenv("POSTGRES_DB", "affiliate_db")
        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"

    return _normalize_async_url(config.database.url)


def _redact_url(url: str) -> str:
    """Format database URL for console output without exposing credentials."""
    try:
        return make_url(url).render_as_string(hide_password=True)
    except Exception:
        return "<database>"


async def init_database(
    config_path: str = "config.yaml",
    database_url: str | None = None,
    seed_niches: bool = True,
) -> str:
    """Create all ORM tables and seed configured pilot niches if missing."""
    _load_env_file(REPO_ROOT / ".env")
    resolved_cfg = _resolve_config_path(config_path)
    config = load_config(str(resolved_cfg))
    target_url = _resolve_database_url(config, database_url)

    engine = get_async_engine(target_url, force_new=True)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        if seed_niches and config.niches:
            session_factory = get_session_factory(target_url)
            async with session_factory() as session:
                for niche_cfg in config.niches:
                    existing = await session.scalar(
                        select(Niche).where(Niche.niche_id == niche_cfg.niche_id)
                    )
                    if existing is None:
                        session.add(
                            Niche(
                                niche_id=niche_cfg.niche_id,
                                name=niche_cfg.name,
                                description=niche_cfg.persona.role,
                            )
                        )
                await session.commit()
    finally:
        await engine.dispose()

    return target_url


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize AMAS database tables and pilot niches.")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    parser.add_argument("--url", default=None, help="Optional database URL override")
    parser.add_argument("--no-seed", action="store_true", help="Skip seeding pilot niches")
    args = parser.parse_args()

    try:
        target_url = asyncio.run(
            init_database(
                config_path=args.config,
                database_url=args.url,
                seed_niches=not args.no_seed,
            )
        )
    except Exception as exc:
        print(f"Failed to initialize database: {exc}", file=sys.stderr)
        return 1

    print(f"Database schema initialized successfully ({_redact_url(target_url)}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
