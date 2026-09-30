#!/usr/bin/env sh
set -eu
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
ENV_DIR="$SCRIPT_DIR/python_env"
PYTHON="${PYTHON:-python3}"

"$PYTHON" -m venv "$ENV_DIR"
"$ENV_DIR/bin/python" -m pip install --upgrade pip
"$ENV_DIR/bin/python" -m pip install -r "$SCRIPT_DIR/requirements.txt"

printf '%s\n' "UnrealMCP environment ready: $ENV_DIR/bin/python"
printf '%s\n' "Configure your MCP client to run:"
printf '  "%s" "%s"\n' "$ENV_DIR/bin/python" "$SCRIPT_DIR/unreal_mcp_bridge.py"
