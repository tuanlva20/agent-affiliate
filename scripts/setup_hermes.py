"""Register AMAS MCP server and amas-orchestrator skill into local ~/.hermes."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MCP_SERVER_PATH = REPO_ROOT / "src" / "mcp" / "amas_mcp_server.py"
SKILL_SRC = REPO_ROOT / "integrations" / "hermes" / "skills" / "amas-orchestrator" / "SKILL.md"


def main() -> int:
    hermes_bin = shutil.which("hermes")
    if not hermes_bin:
        print("`hermes` CLI not found. Install first: pip install hermes-agent mcp", file=sys.stderr)
        return 1

    # Register/overwrite the stdio MCP server in ~/.hermes/config.yaml via official CLI
    cmd = [
        hermes_bin,
        "mcp",
        "add",
        "amas",
        "--command",
        sys.executable,
        "--args",
        str(MCP_SERVER_PATH),
    ]
    # Provide two 'y' answers: overwrite prompt (if existing) + enable-all-tools prompt.
    res = subprocess.run(cmd, input="y\ny\n", capture_output=True, text=True, timeout=60)
    if res.returncode != 0:
        print(res.stdout, res.stderr, file=sys.stderr)
        return res.returncode

    # Install the AMAS orchestration & self-learning skill into ~/.hermes/skills/
    skill_dest = Path.home() / ".hermes" / "skills" / "amas-orchestrator" / "SKILL.md"
    skill_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SKILL_SRC, skill_dest)

    print(f"Registered MCP server 'amas' -> {MCP_SERVER_PATH}")
    print(f"Installed skill -> {skill_dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
