"""Escape hatch for Unreal Python API operations not yet wrapped as dedicated tools."""

from __future__ import annotations
from utils import send_command

def register_all(mcp):
    @mcp.tool()
    def execute_python(code: str | None = None, file: str | None = None) -> dict:
        """Execute Python inside Unreal Editor. Prefer a dedicated UnrealMCP tool when one exists."""
        if not code and not file:
            raise ValueError("Provide code or file")
        params = {}
        if code:
            params["code"] = code
        if file:
            params["file"] = file
        return send_command("execute_python", params, timeout=120)
