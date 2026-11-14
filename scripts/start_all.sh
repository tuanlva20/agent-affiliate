#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

START_WEB=false

# Parse command line flags
for arg in "$@"; do
  case "$arg" in
    --all|-a|--full)
      START_WEB=true
      ;;
    --help|-h)
      echo "Cách dùng: ./scripts/start_all.sh [options]"
      echo ""
      echo "Tùy chọn:"
      echo "  --all, -a, --full   Khởi động toàn bộ Full-Stack (Bao gồm FastAPI :8000 và Next.js Web UI :3000)"
      echo "  --help, -h          Hiển thị trợ giúp này"
      exit 0
      ;;
    *)
      echo "Tùy chọn không hợp lệ: $arg" >&2
      echo "Dùng './scripts/start_all.sh --help' để xem các tùy chọn hỗ trợ." >&2
      exit 1
      ;;
  esac
done

if [[ ! -f ".venv/bin/activate" ]]; then
  echo "Missing .venv. Create it first: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt" >&2
  exit 1
fi

if [[ ! -f ".env" ]]; then
  echo "Missing .env. Copy .env.example to .env and fill in your credentials first." >&2
  exit 1
fi

source ".venv/bin/activate"
set -a
source ".env"
set +a

# Validate node and dependencies if running with --all
if [[ "$START_WEB" == "true" ]]; then
  if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
    echo "Error: Node.js và npm là bắt buộc khi dùng cờ --all nhưng chưa được cài đặt trong PATH." >&2
    exit 1
  fi
  if [[ ! -d "web/node_modules" ]]; then
    echo "Thư mục web/node_modules chưa tồn tại, đang cài đặt dependencies..."
    npm --prefix web install
  fi
fi

stop_existing() {
  echo "Cleaning up any existing AMAS / Hermes / Web processes..."
  hermes gateway stop >/dev/null 2>&1 || true
  pkill -f "main\.py --mode (bot|daemon)" 2>/dev/null || true
  pkill -f "amas_mcp_server\.py" 2>/dev/null || true
  pkill -f "hermes.*gateway" 2>/dev/null || true
  if [[ "$START_WEB" == "true" ]]; then
    pkill -f "uvicorn.*src\.api\.main:app" 2>/dev/null || true
    pkill -f "next.*dev" 2>/dev/null || true
  fi
  sleep 1
  if ! pgrep -f "hermes.*gateway" >/dev/null 2>&1; then
    rm -f "$HOME/.hermes/gateway.pid" "$HOME/.hermes/gateway.lock"
  fi
}

stop_existing

# Only start Docker services if either container is not currently running
if [[ -z "$(docker ps -q -f name='^amas-postgres$' -f status=running)" ]] || \
   [[ -z "$(docker ps -q -f name='^amas-redis$' -f status=running)" ]]; then
  docker compose up -d --wait
fi

python scripts/init_db.py

cleanup() {
  trap - EXIT INT TERM
  echo ""
  echo "Shutting down all AMAS processes..."
  kill 0 2>/dev/null || true
}
trap cleanup EXIT INT TERM

if [[ "$START_WEB" == "true" ]]; then
  echo "============================================================"
  echo "🚀 KHỞI ĐỘNG FULL STACK AMAS (Ctrl+C để dừng toàn bộ):"
  echo "   - Telegram Bot:     Đang chạy polling"
  echo "   - Background Daemon: Đang chạy scheduler"
  echo "   - Hermes Gateway:    Đang lắng nghe"
  echo "   - Backend API:       http://localhost:8000 (Swagger: /docs)"
  echo "   - Web UI:            http://localhost:3000"
  echo "============================================================"
  python main.py --mode bot &
  python main.py --mode daemon &
  hermes gateway &
  python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload &
  npm --prefix web run dev &
else
  echo "============================================================"
  echo "🤖 KHỞI ĐỘNG AMAS CORE (Bot, Daemon, Hermes Gateway):"
  echo "   (Ctrl+C để dừng toàn bộ)"
  echo ""
  echo "   💡 Mẹo: Chạy './scripts/start_all.sh --all' để khởi động"
  echo "           đồng thời cả Backend API (:8000) và Web UI (:3000)"
  echo "============================================================"
  python main.py --mode bot &
  python main.py --mode daemon &
  hermes gateway &
fi

wait
