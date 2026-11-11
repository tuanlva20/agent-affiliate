"""Unit & State Flow Test Suite for Hermes Orchestrator (Milestone 8, Task 8, Feature F28).

Covers:
1. StateGraph topological transitions & dict contract compatibility.
2. HermesState TypedDict keys initialization and schema conformance.
3. Atomic step execution via run_pipeline_step ('scout', 'evaluate', 'render', 'publish', 'reply').
4. Conditional edge routing (empty candidates, captcha blocked, warming channel).
5. Error handling and unknown step validation.
6. Full end-to-end pipeline execution (ainvoke / run_pipeline).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List
import pytest
import pytest_asyncio

from src.core.config import AppConfig, load_config
from src.core.tone_validator import ToneValidator
from src.agents.hermes_orchestrator import HermesOrchestrator, HermesState, CompiledHermesGraph


@pytest.fixture
def app_config() -> AppConfig:
    return AppConfig()


@pytest.fixture
def hermes_instance(app_config: AppConfig) -> HermesOrchestrator:
    return HermesOrchestrator(config=app_config, mock_mode=True)


@pytest.fixture
def sample_fashion_product() -> Dict[str, Any]:
    return {
        "product_id": "prod_fash_01",
        "niche_id": "thoi_trang_nu",
        "title": "Váy maxi voan hoa nhí dáng xòe che bụng cực xinh",
        "price": 199000.0,
        "price_vnd": 199000.0,
        "commission_rate": 0.15,
        "sales_30d": 1500,
        "product_url": "https://tiktok.com/@shop/p/01",
    }


@pytest.fixture
def sample_homelife_product() -> Dict[str, Any]:
    return {
        "product_id": "prod_home_01",
        "niche_id": "do_gia_dung",
        "title": "Cây lau nhà tự vắt thông minh xoay 360 độ Before/After",
        "price": 149000.0,
        "price_vnd": 149000.0,
        "commission_rate": 0.18,
        "sales_30d": 2500,
        "product_url": "https://tiktok.com/@shop/p/02",
    }


def test_hermes_state_graph_contract(hermes_instance: HermesOrchestrator):
    """Verifies build_state_graph conforms to contract and supports dict subscripting."""
    graph = hermes_instance.build_state_graph()
    assert isinstance(graph, CompiledHermesGraph)
    assert "scout_products" in graph
    assert "specialist_eval" in graph["scout_products"]
    assert "telegram_approval" in graph["specialist_eval"]
    assert "video_render" in graph["telegram_approval"]
    assert "smart_publish" in graph["video_render"]
    assert "comment_monitor" in graph["smart_publish"]
    assert "koc_reply" in graph["comment_monitor"]


def test_hermes_initial_state_schema(hermes_instance: HermesOrchestrator):
    """Verifies all required keys are present in orchestrator state dictionary."""
    state = hermes_instance.state
    assert "discovered_products" in state
    assert "approved_products" in state
    assert "rendered_jobs" in state
    assert "published_videos" in state
    assert "replied_comments" in state
    assert "candidate_products" in state
    assert "video_jobs" in state
    assert "publish_records" in state
    assert "scanned_comments" in state
    assert "replies" in state


@pytest.mark.asyncio
async def test_hermes_step_scout_fashion(hermes_instance: HermesOrchestrator):
    """Verifies atomic scout step execution for Women's Fashion."""
    res = await hermes_instance.run_pipeline_step("scout", {"niche_id": "thoi_trang_nu", "limit": 2})
    assert res["status"] == "success"
    assert res["count"] > 0
    assert len(res["items"]) > 0


@pytest.mark.asyncio
async def test_hermes_step_scout_homelife(hermes_instance: HermesOrchestrator):
    """Verifies atomic scout step execution for Smart Home Utilities."""
    res = await hermes_instance.run_pipeline_step("scout", {"niche_id": "do_gia_dung", "limit": 2})
    assert res["status"] == "success"
    assert res["count"] > 0
    assert len(res["items"]) > 0


@pytest.mark.asyncio
async def test_hermes_step_evaluate(
    hermes_instance: HermesOrchestrator, sample_fashion_product: Dict[str, Any]
):
    """Verifies atomic evaluate step execution with Specialist Scout."""
    res = await hermes_instance.run_pipeline_step(
        "evaluate", {"niche_id": "thoi_trang_nu", "product": sample_fashion_product}
    )
    assert res["status"] == "success"
    eval_obj = res["evaluation"]
    assert eval_obj.passed_filter is True
    assert eval_obj.score >= 7.0


@pytest.mark.asyncio
async def test_hermes_step_render(
    hermes_instance: HermesOrchestrator, sample_fashion_product: Dict[str, Any]
):
    """Verifies atomic render step execution returning valid video path."""
    res = await hermes_instance.run_pipeline_step(
        "render",
        {
            "job_id": "job_hermes_01",
            "product": sample_fashion_product,
            "persona": {"tone": "koc", "voice_name": "vi-VN-HoaiMyNeural"},
        },
    )
    assert res["status"] == "success"
    assert "video_path" in res
    assert os.path.exists(res["video_path"])


@pytest.mark.asyncio
async def test_hermes_step_publish(hermes_instance: HermesOrchestrator):
    """Verifies atomic publish step execution with channel status verification."""
    res = await hermes_instance.run_pipeline_step(
        "publish",
        {
            "job_id": "job_hermes_01",
            "channel": {"channel_id": "chan_01", "lifecycle_status": "ready_to_post"},
            "video_path": "/tmp/mock.mp4",
        },
    )
    assert res["status"] == "success"
    assert res["result"].success is True


@pytest.mark.asyncio
async def test_hermes_step_reply(
    hermes_instance: HermesOrchestrator, sample_fashion_product: Dict[str, Any]
):
    """Verifies atomic reply step execution returning ToneValidator-compliant KOC response."""
    res = await hermes_instance.run_pipeline_step(
        "reply",
        {"comment": "Váy này giá bao nhiêu thế?", "product": sample_fashion_product},
    )
    assert res["status"] == "success"
    assert ToneValidator.validate(res["reply"]) is True


@pytest.mark.asyncio
async def test_hermes_unknown_step_raises_value_error(hermes_instance: HermesOrchestrator):
    """Verifies unknown pipeline step names raise ValueError."""
    with pytest.raises(ValueError, match="Unknown pipeline step"):
        await hermes_instance.run_pipeline_step("invalid_step", {})


@pytest.mark.asyncio
async def test_hermes_full_pipeline_dryrun(hermes_instance: HermesOrchestrator):
    """Verifies full StateGraph execution via run_pipeline."""
    initial_state = {
        "run_mode": "dry-run",
        "niche_id": "thoi_trang_nu",
        "channels": {
            "chan_01": {"channel_id": "chan_01", "lifecycle_status": "ready_to_post"}
        },
    }
    final_state = await hermes_instance.run_pipeline(initial_state)
    assert "current_step" in final_state
    assert final_state["current_step"] in ["engagement", "publisher", "studio", "approval", "scout"]
    assert len(final_state.get("approved_products", [])) > 0 or final_state.get("stop_reason") is not None


def test_hermes_routing_conditions(hermes_instance: HermesOrchestrator):
    """Verifies conditional routing decisions."""
    # Scout with no candidates -> end
    assert hermes_instance._route_from_scout({"candidate_products": []}) == "end"
    assert hermes_instance._route_from_scout({"candidate_products": [{"id": 1}]}) == "approval"

    # Approval with no approved -> end
    assert hermes_instance._route_from_approval({"approved_products": []}) == "end"
    # Approval waiting for human -> end
    assert (
        hermes_instance._route_from_approval(
            {"approved_products": [{"id": 1}], "stop_reason": "awaiting_human_approval"}
        )
        == "end"
    )
    # Approval in dry run -> studio
    assert (
        hermes_instance._route_from_approval(
            {"approved_products": [{"id": 1}], "stop_reason": None}
        )
        == "studio"
    )

    # Studio with no rendered jobs -> end
    assert hermes_instance._route_from_studio({"video_jobs": []}) == "end"
    assert (
        hermes_instance._route_from_studio(
            {"video_jobs": [{"status": "rendered", "rendered_video_path": "/tmp/mock.mp4"}]}
        )
        == "publisher"
    )

    # Publisher with captcha alert -> end
    assert (
        hermes_instance._route_from_publisher({"captcha_alert": {"alert": True}})
        == "end"
    )
    assert hermes_instance._route_from_publisher({"captcha_alert": None}) == "engagement"
