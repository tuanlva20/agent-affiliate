#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

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

stop_existing() {
  echo "Cleaning up any existing AMAS / Hermes processes..."
  hermes gateway stop >/dev/null 2>&1 || true
  pkill -f "main\.py --mode (bot|daemon)" 2>/dev/null || true
  pkill -f "amas_mcp_server\.py" 2>/dev/null || true
  pkill -f "hermes.*gateway" 2>/dev/null || true
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
  kill 0 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Starting AMAS Bot, AMAS Daemon, and Hermes Gateway (Ctrl+C to stop all)..."
python main.py --mode bot &
python main.py --mode daemon &
hermes gateway &

wait
