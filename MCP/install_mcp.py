#!/usr/bin/env python
"""Install the exact MCP SDK version declared in requirements.txt."""

from __future__ import annotations

import importlib.metadata
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REQUIREMENTS = ROOT / "requirements.txt"

def main() -> int:
    print(f"Python: {sys.executable}")
    subprocess.check_call([
        sys.executable,
        "-m",
        "pip",
        "install",
        "--upgrade",
        "-r",
        str(REQUIREMENTS),
    ])
    print(f"Installed MCP SDK {importlib.metadata.version('mcp')}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
