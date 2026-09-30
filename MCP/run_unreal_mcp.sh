#!/usr/bin/env sh
set -eu
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PYTHON="$SCRIPT_DIR/python_env/bin/python"
if [ ! -x "$PYTHON" ]; then
  echo "ERROR: $PYTHON not found. Create the venv and install requirements.txt first." >&2
  exit 1
fi
exec "$PYTHON" "$SCRIPT_DIR/unreal_mcp_bridge.py" "$@"
