#!/usr/bin/env python
"""Install the supported MCP Python SDK into the active Python environment."""

from __future__ import annotations
import importlib.metadata
import subprocess
import sys

REQUIREMENT = "mcp>=2.2,<3"

def main() -> int:
    print(f"Python: {sys.executable}")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", REQUIREMENT])
    print(f"Installed MCP SDK {importlib.metadata.version('mcp')}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
