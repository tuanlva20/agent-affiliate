import asyncio
import os
import sys
from pathlib import Path
from sqlalchemy import select, func

# Add project root to sys.path
REPO_ROOT = Path("/Users/tuanlva/Folder/workSpace/affiliate")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.database.models import Channel, Product, VideoJob
from src.database.session import get_db
from src.core.config import load_config

async def get_status():
    config = load_config(str(REPO_ROOT / "config.yaml"))
    db_url = os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL") or config.database.url
    
    async with get_db(db_url) as session:
        # Channels
        channels = (await session.execute(select(Channel))).scalars().all()
        
        # Products by status
        product_rows = (await session.execute(select(Product.status, func.count()).group_by(Product.status))).all()
        products_by_status = {str(key): int(cnt) for key, cnt in product_rows}
        
        # VideoJobs by status
        job_rows = (await session.execute(select(VideoJob.status, func.count()).group_by(VideoJob.status))).all()
        jobs_by_status = {str(key): int(cnt) for key, cnt in job_rows}
        
        print("--- AMAS Status ---")
        print(f"Total Channels: {len(channels)}")
        for c in channels:
            print(f"  - {c.channel_id} ({c.niche_id}): {c.lifecycle_status} (Warmup: {c.warmup_days_completed} days)")
        
        print("\nProducts by Status:")
        for status, count in products_by_status.items():
            print(f"  - {status}: {count}")
            
        print("\nVideo Jobs by Status:")
        for status, count in jobs_by_status.items():
            print(f"  - {status}: {count}")

if __name__ == "__main__":
    asyncio.run(get_status())
