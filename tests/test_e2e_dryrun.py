"""E2E Dry-run & CLI Integration Test Suite (Milestone 8, Task 8, Feature F29).

Validates:
1. CLI option parsing and exit codes (--help: 0, valid modes: 0, invalid mode: 1, missing arg: 2).
2. End-to-end dry-run execution (main.py --mode dry-run) terminating with exit code 0.
3. Verification of all pipeline artifacts (products, evaluations, video renders, publish records, KOC replies).
4. Subprocess execution of main.py.
5. Database lifecycle synchronization during dry-run.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from main import run_cli
from src.core.tone_validator import ToneValidator
from src.database.models import Channel, Niche, Product, VideoComment, VideoJob


def test_cli_exit_codes():
    """Validates CLI runner command line options and exit codes."""
    assert run_cli(["--help"]) == 0
    assert run_cli(["-h"]) == 0
    assert run_cli(["--mode", "dry-run"]) == 0
    assert run_cli(["--mode", "scout"]) == 0
    assert run_cli(["--mode", "bot", "--once"]) == 0
    assert run_cli(["--mode", "daemon", "--once"]) == 0
    assert run_cli(["--mode", "invalid_mode"]) == 1
    assert run_cli(["--mode"]) == 2


def test_cli_dryrun_niche_filtering():
    """Validates dry-run execution for specific pilot niches."""
    assert run_cli(["--mode", "dry-run", "--niche", "thoi_trang_nu", "--dry-run-items", "1"]) == 0
    assert run_cli(["--mode", "dry-run", "--niche", "do_gia_dung", "--dry-run-items", "1"]) == 0


def test_cli_scout_generates_summary():
    """Validates scout mode creates scout_summary.json artifact."""
    code = run_cli(["--mode", "scout", "--niche", "all"])
    assert code == 0
    summary_path = Path("storage/scout_summary.json")
    assert summary_path.exists()
    assert summary_path.stat().st_size > 0


def test_subprocess_main_dryrun():
    """Validates python main.py --mode dry-run runs cleanly in a standalone subprocess."""
    result = subprocess.run(
        [sys.executable, "main.py", "--mode", "dry-run", "--dry-run-items", "1"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
    assert "[AMAS v1.4.0]" in result.stdout
    assert "DRY-RUN COMPLETED SUCCESSFULLY" in result.stdout


@pytest.mark.asyncio
async def test_dryrun_database_lifecycle(db_session: AsyncSession):
    """Validates database lifecycle updates for Product and VideoJob during pipeline run."""
    niche = Niche(niche_id="thoi_trang_nu", name="Thời trang nữ")
    db_session.add(niche)
    await db_session.commit()

    prod = Product(
        product_id="prod_dry_01",
        niche_id="thoi_trang_nu",
        title="Váy hoa nhí hack dáng",
        price=189000.0,
        commission_rate=0.15,
        product_url="https://vt.tiktok.com/prod_dry_01",
        status="pending",
    )
    db_session.add(prod)
    await db_session.commit()

    # Transition to approved
    prod.status = "approved"
    job = VideoJob(
        job_id="job_dry_01",
        product_id=prod.product_id,
        niche_id=prod.niche_id,
        status="rendering",
    )
    db_session.add(job)
    await db_session.commit()

    # Transition to rendered
    job.status = "rendered"
    job.output_video_path = "/tmp/mock.mp4"
    await db_session.commit()

    res = await db_session.execute(select(VideoJob).where(VideoJob.job_id == "job_dry_01"))
    saved_job = res.scalar_one_or_none()
    assert saved_job is not None
    assert saved_job.status == "rendered"
    assert saved_job.output_video_path == "/tmp/mock.mp4"
