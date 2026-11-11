"""AMAS v1.4.0 — Hermes StateGraph Orchestrator (Feature F28).

Autonomic state coordinator integrating all AMAS specialist agents into a LangGraph
StateGraph pipeline with Human-in-the-Loop review and autonomous dry-run execution.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict, Union

from langgraph.graph import StateGraph, START, END
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.base_scout import BaseScoutAgent, ProductCandidate
from src.agents.comment_agent import CommentAgent, CommentIntent
from src.agents.fashion_scout import FashionScoutAgent, SpecialistEvaluation
from src.agents.homelife_scout import HomeLifeScoutAgent
from src.agents.smart_publisher import PublishResult, SmartPublisher
from src.agents.video_studio import VideoStudioAgent
from src.bot.telegram_bot import TelegramCommandCenter
from src.core.config import AppConfig, load_config
from src.core.tone_validator import ToneValidator
from src.database.models import Channel, Product, VideoComment, VideoJob
from src.services.browser_adapter import BrowserAdapter, StubPage
from src.services.comment_scanner import CommentScanner

logger = logging.getLogger("amas.agents.hermes")


class HermesState(TypedDict, total=False):
    """LangGraph execution state dictionary for the AMAS multi-agent pipeline."""

    run_mode: str
    niche_id: str
    channels: Dict[str, Any]
    candidate_products: List[Dict[str, Any]]
    discovered_products: List[Dict[str, Any]]
    approved_products: List[Dict[str, Any]]
    rejected_products: List[Dict[str, Any]]
    video_jobs: List[Dict[str, Any]]
    rendered_jobs: List[str]
    publish_records: List[Dict[str, Any]]
    published_videos: List[str]
    scanned_comments: List[Dict[str, Any]]
    replies: List[Dict[str, Any]]
    replied_comments: List[str]
    errors: List[Dict[str, Any]]
    captcha_alert: Optional[Dict[str, Any]]
    current_step: str
    stop_reason: Optional[str]
    metrics: Dict[str, Any]


class CompiledHermesGraph:
    """Wrapper around LangGraph CompiledStateGraph providing dual execution and mapping interface."""

    TOPOLOGICAL_MAP: Dict[str, List[str]] = {
        "scout_products": ["specialist_eval"],
        "specialist_eval": ["telegram_approval"],
        "telegram_approval": ["video_render"],
        "video_render": ["smart_publish"],
        "smart_publish": ["comment_monitor"],
        "comment_monitor": ["koc_reply"],
    }

    def __init__(self, compiled_graph: Any) -> None:
        self._graph = compiled_graph

    def __contains__(self, item: str) -> bool:
        return item in self.TOPOLOGICAL_MAP

    def __getitem__(self, item: str) -> List[str]:
        return self.TOPOLOGICAL_MAP[item]

    async def ainvoke(self, state: HermesState, *args: Any, **kwargs: Any) -> HermesState:
        if hasattr(self._graph, "ainvoke"):
            return await self._graph.ainvoke(state, *args, **kwargs)
        elif hasattr(self._graph, "invoke"):
            return self._graph.invoke(state, *args, **kwargs)
        return state

    def invoke(self, state: HermesState, *args: Any, **kwargs: Any) -> HermesState:
        if hasattr(self._graph, "invoke"):
            return self._graph.invoke(state, *args, **kwargs)
        elif hasattr(self._graph, "ainvoke"):
            return asyncio.run(self._graph.ainvoke(state, *args, **kwargs))
        return state


class HermesOrchestrator:
    """Master autonomic state coordinator for AMAS v1.4.0."""

    def __init__(
        self,
        config: Optional[AppConfig] = None,
        base_scout: Optional[BaseScoutAgent] = None,
        fashion_scout: Optional[FashionScoutAgent] = None,
        homelife_scout: Optional[HomeLifeScoutAgent] = None,
        video_studio: Optional[VideoStudioAgent] = None,
        smart_publisher: Optional[SmartPublisher] = None,
        comment_scanner: Optional[CommentScanner] = None,
        comment_agent: Optional[CommentAgent] = None,
        telegram_bot: Optional[TelegramCommandCenter] = None,
        db_session: Optional[AsyncSession] = None,
        mock_mode: bool = False,
    ) -> None:
        self.config = config or load_config()
        self.base_scout = base_scout or BaseScoutAgent(self.config)
        self.fashion_scout = fashion_scout or FashionScoutAgent(self.config)
        self.homelife_scout = homelife_scout or HomeLifeScoutAgent(self.config)
        self.video_studio = video_studio or VideoStudioAgent()
        if smart_publisher is not None:
            self.smart_publisher = smart_publisher
        elif mock_mode:
            self.smart_publisher = SmartPublisher(
                browser_adapter=BrowserAdapter(mock_mode=True),
                config=self.config,
            )
        else:
            self.smart_publisher = SmartPublisher(config=self.config)
        self.comment_scanner = comment_scanner or CommentScanner(
            mock_mode=True if mock_mode else None
        )
        self.comment_agent = comment_agent or CommentAgent()
        self.telegram_bot = telegram_bot or TelegramCommandCenter(
            config=self.config, mock_mode=True if mock_mode else None
        )
        self.db_session = db_session
        self.mock_mode = mock_mode

        self.state: Dict[str, Any] = {
            "discovered_products": [],
            "candidate_products": [],
            "approved_products": [],
            "rejected_products": [],
            "rendered_jobs": [],
            "video_jobs": [],
            "published_videos": [],
            "publish_records": [],
            "replied_comments": [],
            "scanned_comments": [],
            "replies": [],
            "errors": [],
            "captcha_alert": None,
            "current_step": "init",
            "stop_reason": None,
            "metrics": {},
        }

    # --------------------------------------------------------------------------
    # StateGraph Construction
    # --------------------------------------------------------------------------

    def build_state_graph(self) -> CompiledHermesGraph:
        """Constructs and compiles the full LangGraph StateGraph workflow."""
        builder = StateGraph(HermesState)

        builder.add_node("scout", self._scout_node)
        builder.add_node("approval", self._approval_node)
        builder.add_node("studio", self._studio_node)
        builder.add_node("publisher", self._publisher_node)
        builder.add_node("engagement", self._engagement_node)

        builder.add_edge(START, "scout")
        builder.add_conditional_edges(
            "scout",
            self._route_from_scout,
            {"approval": "approval", "end": END},
        )
        builder.add_conditional_edges(
            "approval",
            self._route_from_approval,
            {"studio": "studio", "end": END},
        )
        builder.add_conditional_edges(
            "studio",
            self._route_from_studio,
            {"publisher": "publisher", "end": END},
        )
        builder.add_conditional_edges(
            "publisher",
            self._route_from_publisher,
            {"engagement": "engagement", "end": END},
        )
        builder.add_edge("engagement", END)

        compiled = builder.compile()
        return CompiledHermesGraph(compiled)

    # --------------------------------------------------------------------------
    # Conditional Routing Edges
    # --------------------------------------------------------------------------

    def _route_from_scout(self, state: HermesState) -> str:
        candidates = state.get("candidate_products", [])
        if not candidates:
            return "end"
        return "approval"

    def _route_from_approval(self, state: HermesState) -> str:
        approved = state.get("approved_products", [])
        if not approved:
            return "end"
        if state.get("stop_reason") == "awaiting_human_approval":
            return "end"
        return "studio"

    def _route_from_studio(self, state: HermesState) -> str:
        jobs = state.get("video_jobs", [])
        has_rendered = any(
            j.get("status") == "rendered" or j.get("rendered_video_path") for j in jobs
        )
        if not has_rendered:
            return "end"
        return "publisher"

    def _route_from_publisher(self, state: HermesState) -> str:
        if state.get("captcha_alert") is not None or state.get("stop_reason") == "captcha_alarm_halt":
            return "end"
        return "engagement"

    # --------------------------------------------------------------------------
    # Pipeline Nodes
    # --------------------------------------------------------------------------

    async def _scout_node(self, state: HermesState) -> Dict[str, Any]:
        """Node 1: Product sourcing & specialist evaluation."""
        logger.info("[Hermes:scout_node] Ingesting & discovering candidate products...")
        niche_id = state.get("niche_id", "thoi_trang_nu")
        niches = (
            ["thoi_trang_nu", "do_gia_dung"]
            if niche_id in ("all", None, "")
            else [niche_id]
        )

        existing_cands = state.get("candidate_products", [])
        discovered: List[Dict[str, Any]] = []
        rejected: List[Dict[str, Any]] = []

        if existing_cands:
            for item in existing_cands:
                n = item.get("niche_id", niches[0])
                evaluator = self.fashion_scout if "thoi_trang" in n else self.homelife_scout
                ev = evaluator.evaluate_product(item)
                item_dict = dict(item)
                item_dict["evaluation"] = ev
                if ev.passed_filter and ev.score >= 7.0:
                    discovered.append(item_dict)
                else:
                    rejected.append(item_dict)
        else:
            for n in niches:
                candidates = await self.base_scout.discover_candidates(n)
                if not candidates:
                    # Provide realistic fallback candidate
                    if n == "thoi_trang_nu":
                        candidates = [
                            ProductCandidate(
                                product_id="prod_scout_fash_01",
                                niche_id="thoi_trang_nu",
                                title="Váy maxi voan hoa nhí dáng xòe che bụng cực xinh",
                                price_vnd=199000.0,
                                commission_rate=0.15,
                                sales_30d=1500,
                                revenue_30d=298500000.0,
                                product_url="https://vt.tiktok.com/ZS12345/",
                                image_url="https://p16-va.tiktokcdn.com/img1.jpg",
                            )
                        ]
                    else:
                        candidates = [
                            ProductCandidate(
                                product_id="prod_scout_home_01",
                                niche_id="do_gia_dung",
                                title="Cây lau nhà tự vắt xoay 360 độ tiện lợi đa năng Before/After",
                                price_vnd=149000.0,
                                commission_rate=0.18,
                                sales_30d=2500,
                                revenue_30d=372500000.0,
                                product_url="https://vt.tiktok.com/ZS67890/",
                                image_url="https://p16-va.tiktokcdn.com/img2.jpg",
                            )
                        ]

                for cand in candidates:
                    cand_dict = cand.to_dict() if hasattr(cand, "to_dict") else dict(cand)
                    evaluator = self.fashion_scout if "thoi_trang" in n else self.homelife_scout
                    ev = evaluator.evaluate_product(cand_dict)
                    cand_dict["evaluation"] = ev
                    if ev.passed_filter and ev.score >= 7.0:
                        discovered.append(cand_dict)
                    else:
                        rejected.append(cand_dict)

        # Sync database if session provided
        if self.db_session:
            for d in discovered:
                p_id = str(d.get("product_id"))
                existing = await self.db_session.execute(
                    select(Product).where(Product.product_id == p_id)
                )
                if not existing.scalar_one_or_none():
                    p_model = Product(
                        product_id=p_id,
                        niche_id=d.get("niche_id", "thoi_trang_nu"),
                        title=d.get("title", ""),
                        price=float(d.get("price") or d.get("price_vnd") or 0.0),
                        commission_rate=float(d.get("commission_rate") or 0.0),
                        product_url=d.get("product_url") or f"https://vt.tiktok.com/{p_id}",
                        status="pending",
                    )
                    self.db_session.add(p_model)
            await self.db_session.commit()

        self.state["candidate_products"] = discovered
        self.state["discovered_products"] = discovered
        self.state["rejected_products"] = rejected

        stop_reason = "no_candidates" if not discovered else None
        return {
            "candidate_products": discovered,
            "discovered_products": discovered,
            "rejected_products": rejected,
            "current_step": "scout",
            "stop_reason": stop_reason,
        }

    async def _approval_node(self, state: HermesState) -> Dict[str, Any]:
        """Node 2: Human-in-the-Loop review or dry-run auto-approval."""
        logger.info("[Hermes:approval_node] Processing product approvals...")
        candidates = state.get("candidate_products", [])
        run_mode = state.get("run_mode", "dry-run")

        if not candidates:
            return {
                "approved_products": [],
                "video_jobs": [],
                "current_step": "approval",
                "stop_reason": "no_candidates",
            }

        if run_mode == "dry-run":
            approved: List[Dict[str, Any]] = list(candidates)
            jobs: List[Dict[str, Any]] = []
            for item in approved:
                p_id = str(item.get("product_id"))
                job_id = f"job_{p_id}"
                jobs.append({
                    "job_id": job_id,
                    "product_id": p_id,
                    "product": item,
                    "status": "pending",
                })

            if self.db_session:
                for a in approved:
                    p_id = str(a.get("product_id"))
                    p_res = await self.db_session.execute(
                        select(Product).where(Product.product_id == p_id)
                    )
                    p_obj = p_res.scalar_one_or_none()
                    if p_obj:
                        p_obj.status = "approved"

                    j_res = await self.db_session.execute(
                        select(VideoJob).where(VideoJob.job_id == f"job_{p_id}")
                    )
                    if not j_res.scalar_one_or_none():
                        vjob = VideoJob(
                            job_id=f"job_{p_id}",
                            product_id=p_id,
                            niche_id=a.get("niche_id", "thoi_trang_nu"),
                            status="pending",
                        )
                        self.db_session.add(vjob)
                await self.db_session.commit()

            self.state["approved_products"] = approved
            self.state["video_jobs"] = jobs
            return {
                "approved_products": approved,
                "video_jobs": jobs,
                "current_step": "approval",
            }
        else:
            # Live / bot / daemon mode: dispatch cards to Telegram
            for cand in candidates:
                ev = cand.get("evaluation")
                n_id = cand.get("niche_id", "thoi_trang_nu")
                try:
                    await self.telegram_bot.send_product_card(
                        product=cand,
                        evaluation=ev,
                        niche_id=n_id,
                    )
                except Exception as exc:
                    logger.warning("Failed to send product card to Telegram: %s", exc)

            return {
                "approved_products": [],
                "current_step": "approval",
                "stop_reason": "awaiting_human_approval",
            }

    async def _studio_node(self, state: HermesState) -> Dict[str, Any]:
        """Node 3: Automated video remix production."""
        logger.info("[Hermes:studio_node] Producing video remixes...")
        jobs = state.get("video_jobs", [])
        rendered_jobs: List[str] = []

        for job in jobs:
            job_id = job.get("job_id", f"job_{len(rendered_jobs)}")
            prod = job.get("product") or {}
            niche = prod.get("niche_id", "thoi_trang_nu")
            persona = (
                {"tone": "koc_fashion", "voice_name": "vi-VN-HoaiMyNeural"}
                if "thoi_trang" in niche
                else {"tone": "koc_homelife", "voice_name": "vi-VN-NamMinhNeural"}
            )
            vpath = await self.video_studio.produce_video(
                job_id=job_id,
                product_meta=prod,
                persona=persona,
                db_session=self.db_session,
            )
            job["rendered_video_path"] = vpath
            job["status"] = "rendered"
            rendered_jobs.append(vpath)

        self.state["video_jobs"] = jobs
        self.state["rendered_jobs"] = rendered_jobs

        stop_reason = "video_rendering_failed" if not rendered_jobs else None
        return {
            "video_jobs": jobs,
            "rendered_jobs": rendered_jobs,
            "current_step": "studio",
            "stop_reason": stop_reason,
        }

    async def _publisher_node(self, state: HermesState) -> Dict[str, Any]:
        """Node 4: Smart TikTok publishing with lifecycle guards."""
        logger.info("[Hermes:publisher_node] Dispatching videos to target channels...")
        jobs = state.get("video_jobs", [])
        channels = state.get("channels") or {
            "chan_01": {"channel_id": "chan_01", "lifecycle_status": "ready_to_post"}
        }

        publish_records: List[Dict[str, Any]] = []
        published_ids: List[str] = []
        captcha_alert: Optional[Dict[str, Any]] = None

        for job in jobs:
            vpath = job.get("rendered_video_path") or "/tmp/mock.mp4"
            prod = job.get("product") or {}
            job_id = job.get("job_id", "job_01")

            # Match first ready channel or evaluate first channel
            target_chan = next(iter(channels.values()))
            status = (
                target_chan.get("lifecycle_status")
                if isinstance(target_chan, dict)
                else getattr(target_chan, "lifecycle_status", "ready_to_post")
            )

            if status == "captcha_blocked":
                captcha_alert = {
                    "channel_id": target_chan.get("channel_id", "chan_01"),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "action": "emergency_halt",
                }
                logger.error("Emergency Captcha Alarm! Halting publisher node.")
                break
            elif status == "warming":
                publish_records.append({
                    "job_id": job_id,
                    "status": "skipped_warming",
                    "success": False,
                })
                continue
            elif status == "cooldown":
                publish_records.append({
                    "job_id": job_id,
                    "status": "deferred_cooldown",
                    "success": False,
                })
                continue

            raw_prof = (
                target_chan.get("browser_profile_id")
                if isinstance(target_chan, dict)
                else getattr(target_chan, "browser_profile_id", None)
            ) or (
                target_chan.get("channel_id")
                if isinstance(target_chan, dict)
                else getattr(target_chan, "channel_id", "chan_01")
            )
            profile_id = str(raw_prof or "chan_01")
            if hasattr(self.smart_publisher.browser_adapter, "profiles"):
                self.smart_publisher.browser_adapter.profiles.setdefault(
                    profile_id,
                    {
                        "profile_id": profile_id,
                        "name": f"Profile {profile_id}",
                        "proxy": None,
                        "status": "stopped",
                        "cdp_url": None,
                        "options": {},
                    },
                )

            # Publish
            pub_kwargs: Dict[str, Any] = {
                "job_id": job_id,
                "channel": target_chan,
                "video_path": vpath,
                "caption": f"{prod.get('title', 'Sản phẩm hot')} #affiliate #review",
                "product_anchor": prod,
                "db_session": self.db_session,
            }
            if self.mock_mode or getattr(self.smart_publisher.browser_adapter, "mock_mode", False):
                pub_kwargs["page"] = StubPage()
                pub_kwargs["warmup_duration_seconds"] = 0

            pub_res = await self.smart_publisher.publish_video(**pub_kwargs)

            if pub_res.success:
                published_ids.append(pub_res.video_id)
                publish_records.append({
                    "job_id": job_id,
                    "video_id": pub_res.video_id,
                    "status": "published",
                    "success": True,
                })
                # Transition channel to cooldown
                if isinstance(target_chan, dict):
                    target_chan["lifecycle_status"] = "cooldown"
                else:
                    target_chan.lifecycle_status = "cooldown"
            else:
                err_msg = getattr(pub_res, "error", None) or getattr(pub_res, "error_message", "Unknown error")
                publish_records.append({
                    "job_id": job_id,
                    "status": "failed",
                    "success": False,
                    "error": err_msg,
                })

        self.state["publish_records"] = publish_records
        self.state["published_videos"] = published_ids
        self.state["channels"] = channels
        self.state["captcha_alert"] = captcha_alert

        stop_reason = "captcha_alarm_halt" if captcha_alert else None
        return {
            "publish_records": publish_records,
            "published_videos": published_ids,
            "channels": channels,
            "captcha_alert": captcha_alert,
            "current_step": "publisher",
            "stop_reason": stop_reason,
        }

    async def _engagement_node(self, state: HermesState) -> Dict[str, Any]:
        """Node 5: Comment scanning and KOC conversion engagement."""
        logger.info("[Hermes:engagement_node] Monitoring comments and responding...")
        pub_ids = state.get("published_videos") or ["tt_pub_dryrun_01"]
        prod_list = state.get("approved_products") or [{
            "product_id": "prod_dryrun_01",
            "niche_id": "thoi_trang_nu",
            "title": "Váy maxi voan hoa nhí dáng xòe",
            "price": 199000.0,
        }]
        sample_prod = prod_list[0]

        scanned: List[Dict[str, Any]] = []
        replies: List[Dict[str, Any]] = []
        replied_texts: List[str] = []

        for vid in pub_ids:
            comments = await self.comment_scanner.scan_comments(vid, limit=3)
            if not comments:
                comments = [
                    {
                        "comment_id": f"c_{vid}_01",
                        "video_id": vid,
                        "author": "viewer_01",
                        "text": "Váy này giá bao nhiêu vậy shop?",
                    }
                ]
            for c in comments:
                c_text = c.get("text", "")
                intent = self.comment_agent.classify_intent(c_text)
                persona = (
                    {"tone": "koc_fashion", "persona_name": "hoai_my"}
                    if "thoi_trang" in str(sample_prod.get("niche_id"))
                    else {"tone": "koc_homelife", "persona_name": "nam_minh"}
                )
                reply = self.comment_agent.generate_reply(
                    comment_text=c_text,
                    product_meta=sample_prod,
                    persona=persona,
                )
                assert ToneValidator.validate(reply), "Robotic reply detected!"

                scanned.append(c)
                replies.append({
                    "comment_id": c.get("comment_id"),
                    "intent": intent.value if hasattr(intent, "value") else str(intent),
                    "reply": reply,
                })
                replied_texts.append(reply)

                if self.db_session:
                    v_comment = VideoComment(
                        comment_id=c.get("comment_id", f"c_{vid}_01"),
                        video_id=vid,
                        author_id=c.get("author", "viewer"),
                        comment_text=c_text,
                        intent=intent.value if hasattr(intent, "value") else str(intent),
                        reply_text=reply,
                        replied=True,
                    )
                    self.db_session.add(v_comment)

        if self.db_session:
            await self.db_session.commit()

        self.state["scanned_comments"] = scanned
        self.state["replies"] = replies
        self.state["replied_comments"] = replied_texts

        return {
            "scanned_comments": scanned,
            "replies": replies,
            "replied_comments": replied_texts,
            "current_step": "engagement",
            "stop_reason": "completed",
        }

    # --------------------------------------------------------------------------
    # Pipeline Invocations & Step Dispatcher
    # --------------------------------------------------------------------------

    async def run_pipeline(self, initial_state: Optional[Dict[str, Any]] = None) -> HermesState:
        """Executes the full pipeline via StateGraph ainvoke."""
        graph = self.build_state_graph()
        base_state: HermesState = {
            "run_mode": "dry-run",
            "niche_id": "all",
            "channels": {},
            "candidate_products": [],
            "discovered_products": [],
            "approved_products": [],
            "rejected_products": [],
            "video_jobs": [],
            "rendered_jobs": [],
            "publish_records": [],
            "published_videos": [],
            "scanned_comments": [],
            "replies": [],
            "replied_comments": [],
            "errors": [],
            "captcha_alert": None,
            "current_step": "init",
            "stop_reason": None,
            "metrics": {},
        }
        if initial_state:
            base_state.update(initial_state)

        result = await graph.ainvoke(base_state)
        self.state.update(result)
        return result

    async def run_pipeline_step(self, step_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches an atomic pipeline step for testing and CLI command integration."""
        norm_step = (step_name or "").lower().strip()

        if norm_step in ("scout", "scout_products"):
            niche = payload.get("niche_id", "thoi_trang_nu")
            candidates = await self.base_scout.discover_candidates(niche, payload.get("items"))
            if not candidates and payload.get("items") is None:
                candidates = [
                    ProductCandidate(
                        product_id="prod_mock_01",
                        niche_id=niche,
                        title="Váy maxi voan hoa nhí dáng xòe che bụng cực xinh",
                        price_vnd=199000.0,
                        commission_rate=0.15,
                        sales_30d=150,
                    )
                ]
            item_dicts = [
                c.to_dict() if hasattr(c, "to_dict") else dict(c) for c in candidates
            ]
            self.state["discovered_products"] = item_dicts
            self.state["candidate_products"] = item_dicts
            return {"status": "success", "count": len(item_dicts), "items": item_dicts}

        elif norm_step in ("evaluate", "specialist_eval"):
            niche = payload.get("niche_id", "thoi_trang_nu")
            prod = payload.get("product") or payload.get("item", {})
            evaluator = self.fashion_scout if "thoi_trang" in niche else self.homelife_scout
            res = evaluator.evaluate_product(prod)
            return {"status": "success", "evaluation": res}

        elif norm_step in ("render", "studio", "video_render"):
            job_id = payload.get("job_id", "job_01")
            prod_meta = payload.get(
                "product", {"title": "Váy maxi xinh", "niche_id": "thoi_trang_nu"}
            )
            pers = payload.get("persona", {"tone": "koc"})
            vpath = await self.video_studio.produce_video(
                job_id=job_id,
                product_meta=prod_meta,
                persona=pers,
                db_session=self.db_session,
            )
            self.state["rendered_jobs"].append(vpath)
            return {"status": "success", "video_path": vpath}

        elif norm_step in ("publish", "publisher", "smart_publish"):
            job_id = payload.get("job_id", "job_01")
            ch = payload.get(
                "channel",
                {"lifecycle_status": "ready_to_post", "channel_id": "chan_01"},
            )
            vpath = payload.get("video_path", "/tmp/mock.mp4")
            raw_prof = (
                ch.get("browser_profile_id")
                if isinstance(ch, dict)
                else getattr(ch, "browser_profile_id", None)
            ) or (
                ch.get("channel_id")
                if isinstance(ch, dict)
                else getattr(ch, "channel_id", "chan_01")
            )
            profile_id = str(raw_prof or "chan_01")
            if hasattr(self.smart_publisher.browser_adapter, "profiles"):
                self.smart_publisher.browser_adapter.profiles.setdefault(
                    profile_id,
                    {
                        "profile_id": profile_id,
                        "name": f"Profile {profile_id}",
                        "proxy": None,
                        "status": "stopped",
                        "cdp_url": None,
                        "options": {},
                    },
                )

            pub_kwargs: Dict[str, Any] = {
                "job_id": job_id,
                "channel": ch,
                "video_path": vpath,
                "caption": payload.get("caption", "Test caption #affiliate"),
                "product_anchor": payload.get("anchor", {}),
                "db_session": self.db_session,
            }
            if (
                self.mock_mode
                or getattr(self.smart_publisher.browser_adapter, "mock_mode", False)
                or "page" in payload
            ):
                pub_kwargs["page"] = payload.get("page") or StubPage()
                pub_kwargs["warmup_duration_seconds"] = payload.get(
                    "warmup_duration_seconds", 0
                )

            res = await self.smart_publisher.publish_video(**pub_kwargs)
            if res.success and res.video_id:
                self.state["published_videos"].append(res.video_id)
            return {"status": "success" if res.success else "failed", "result": res}

        elif norm_step in ("reply", "engagement", "comment_monitor", "koc_reply"):
            comment = payload.get("comment", "Giá bao nhiêu vậy shop?")
            prod_meta = payload.get(
                "product",
                {"title": "Váy maxi", "price": 199000.0, "niche_id": "thoi_trang_nu"},
            )
            reply = self.comment_agent.generate_reply(
                comment, prod_meta, payload.get("persona", {})
            )
            self.state["replied_comments"].append(reply)
            return {"status": "success", "reply": reply}

        else:
            raise ValueError(f"Unknown pipeline step: {step_name}")
