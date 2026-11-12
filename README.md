# AMAS v1.4.0 — Autonomous Multi-Agent TikTok Affiliate System

AMAS is an autonomous, event-driven multi-agent affiliate automation system for TikTok Shop, operating across two pilot niches: **Women's Fashion** (`thoi_trang_nu`) and **Smart Home Utilities** (`do_gia_dung`).

---

## 🏗 System Architecture

```
[Kalodata / TikTok Scraper]
            │ (Raw Products)
            ▼
[Base & Specialist Scouts (Fashion & HomeLife)]
            │ (SpecialistEvaluation: Body-Hack / Before-After 3s)
            ▼
[Telegram Command Center] ◄── [Human-in-the-Loop 1-Tap Approval]
            │ (Approved Product)
            ▼
[Video Remix Studio (Whisper + edge-tts + FFmpeg)]
            │ (Rendered MP4 with Copyright Evasion)
            ▼
[Smart Publisher (AliasMode CDP + Human Biometrics Engine)]
            │ (Published Video + Attached Showcase Anchor)
            ▼
[Comment Engagement Agent (Intent Classification + KOC Conversion Reply)]
            ▲
            │ (State Coordination)
[Hermes LangGraph Orchestrator]
```

### Core Subsystems:
1. **Specialist Scouts**: `FashionScoutAgent` (body-hack criteria, zero counterfeit tolerance) and `HomeLifeScoutAgent` (Before/After 3s hooks, labor-saving utility).
2. **Video Remix Studio**: Audio extraction (Whisper), natural Vietnamese voiceover (`edge-tts`), and FFmpeg copyright evasion remuxing.
3. **Smart Publisher**: Anti-detect browser automation via AliasMode Local API / CDP with human behavioral biometrics (accelerated mouse scroll, variable keystroke latency, typo simulation with backspace, pre-posting warmup, emergency captcha alarm).
4. **Comment Engagement**: Vietnamese NLP intent classification (`ask_price`, `ask_material_usage`, `complaint`, `other`) and natural KOC persona response generation directing buyers to the yellow cart.
5. **Hermes Orchestrator & CLI Runner**: StateGraph coordination connecting all agents into an autonomous pipeline with human-in-the-loop governance.

---

## 📋 Prerequisites

- **Python**: 3.10+ (tested on Python 3.12)
- **PostgreSQL**: 14+ with JSONB support (or SQLite with aiosqlite for hermetic testing)
- **Redis**: 6+ (message broker & video rendering job queue)
- **FFmpeg**: 5+ with libx264, aac, and subtitle filter support
- **AliasMode Anti-Detect Browser**: Running with Local REST API at `http://127.0.0.1:50325` (or Playwright Chromium)

---

## 🚀 Installation & Setup

### 1. Clone Repository & Setup Virtual Environment
```bash
git clone <repository_url> affiliate
cd affiliate
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your credentials:
```bash
cp .env.example .env
```

Key configuration parameters in `.env`:
- `TELEGRAM_BOT_TOKEN`: Bot token from @BotFather
- `ADMIN_TELEGRAM_ID`: Numeric Telegram user ID of the admin
- `TELEGRAM_FORUM_CHAT_ID`: Supergroup chat ID for forum topics
- `DATABASE_URL`: PostgreSQL connection string (`postgresql+asyncpg://postgres:postgres@localhost:5433/affiliate_db`)
- `REDIS_URL`: Redis queue connection string (`redis://localhost:6379/0`)
- `BROWSER_API_URL`: AliasMode Local API endpoint (`http://127.0.0.1:50325`)
- `VERTEX_CREDENTIALS_PATH`: Path to Google Cloud Service Account JSON for Vertex AI (`gemini-3-flash-preview`)

### 3. Start PostgreSQL & Redis via Docker Compose
Start the isolated PostgreSQL (`postgres:16-alpine` on host port `5433`) and Redis (`redis:7-alpine` on host port `6379`) containers, then initialize the database schema:
```bash
docker compose up -d
python3 scripts/init_db.py
```

---

## 💻 System Execution (`main.py`)

AMAS provides a unified CLI runner with 4 operational modes:

### Mode 1: Dry-Run Pipeline (Hermetic Integration Test)
Executes an end-to-end dry-run through Hermes Orchestrator verifying every pipeline stage:
```bash
python main.py --mode dry-run
```
Options:
- `--niche [thoi_trang_nu|do_gia_dung|all]`: Target specific niche (default: `all`)
- `--dry-run-items <n>`: Number of products to process (default: `2`)

### Mode 2: Specialist Sourcing (`scout`)
Discovers and evaluates products for pilot niches and outputs a summary table:
```bash
python main.py --mode scout --niche thoi_trang_nu
```

### Mode 3: Telegram Command Center (`bot`)
Starts the live Telegram bot long-polling service:
```bash
python main.py --mode bot
```
*(Add `--once` for hermetic initialization check)*

### Mode 4: Autonomous Background Daemon (`daemon`)
Runs the periodic background scheduler executing hourly scouting, batch video rendering, scheduled publishing, and comment scanning:
```bash
python main.py --mode daemon
```
*(Add `--once` to execute one full cycle and exit)*

---

## 📱 Telegram Bot & Human-in-the-Loop Workflow

### Forum Topic Routing
- Topic `#thoi-trang-nu` (Thread ID 101/2): Women's fashion product approval cards
- Topic `#do-gia-dung` (Thread ID 102/4): Home utilities product approval cards
- Topic `#dashboard-tong` (Thread ID 100/1): System alerts, status updates, and emergency Captcha alarms

### 1-Tap Inline Approval
Each product candidate sent to Telegram features inline buttons:
- `✅ Duyệt sản phẩm`: Approves product (`Product.status = 'approved'`), queuing it for Video Remix Studio.
- `❌ Từ chối`: Rejects candidate (`Product.status = 'rejected'`).

### Administrative Slash Commands
- `/test_scout [niche]`: Triggers on-demand specialist scout discovery.
- `/test_video`: Tests video remixing and Vietnamese TTS synthesis.
- `/test_reply`: Verifies Comment Agent intent classification.
- `/status`: Displays system health, channel lifecycle states, and active queues.
- `/create_channel [alias]`: Registers a new channel profile.
- `/warmup [channel_id]`: Initiates pre-posting feed warmup browsing session.

---

## 🧠 Agent 4 via NousResearch Hermes Agent (MCP Integration)

AMAS exposes an MCP `stdio` server (`src/mcp/amas_mcp_server.py`) and an orchestration skill (`integrations/hermes/skills/amas-orchestrator/SKILL.md`) so open-source `hermes-agent` provides persistent memory (`MEMORY.md`), skill self-improvement, and natural Telegram conversation on top of the deterministic AMAS pipeline:

```bash
# 1. Register the AMAS MCP server and skill into ~/.hermes/
python3 scripts/setup_hermes.py
hermes mcp test amas

# 2. Configure your LLM provider (e.g., Gemini) & a dedicated Telegram bot token for Hermes
hermes model
hermes gateway setup

# 3. Start Hermes Telegram gateway (keep `main.py --mode bot` on a separate token for 1-tap cards)
hermes gateway
```

---

## 🧪 Testing & Verification

AMAS includes a comprehensive hermetic test suite with 100% genuine logic and zero mock imports in `src/`.

```bash
# Run entire test suite
pytest tests/ -v

# Run Hermes Orchestrator state flow tests
pytest tests/test_hermes_flow.py -v

# Run End-to-End Dry-Run integration tests
pytest tests/test_e2e_dryrun.py -v

# Run Tier 1 Feature Isolation tests
pytest tests/e2e/test_tier1_features.py -v

# Run Tier 4 Realistic Production Scenarios
pytest tests/e2e/test_tier4_scenarios.py -v
```
