"""Helpers for executing structured Python inside Unreal Editor."""

from __future__ import annotations

import json
import textwrap
from typing import Any

from .command_utils import send_command

SENTINEL = "__UNREAL_MCP_JSON__"

def run_unreal_python(code: str, *, timeout: float = 60) -> str:
    """Execute Python in Unreal and return captured stdout."""
    response = send_command("execute_python", {"code": code}, timeout=timeout)
    result = response.get("result") or {}
    output = result.get("output", "")

    if response.get("status") != "success":
        detail = result.get("error") or response.get("message") or "Unreal Python execution failed"
        raise RuntimeError(str(detail).strip())

    return str(output).strip()

def run_unreal_json(script: str, args: dict[str, Any] | None = None, *, timeout: float = 60) -> Any:
    """Run a script that assigns to ``result`` and return JSON-safe structured data."""
    encoded_args = json.dumps(args or {}, ensure_ascii=False)
    body = textwrap.indent(textwrap.dedent(script).strip(), "    ")
    wrapper = f"""
import json
import traceback
import unreal

args = json.loads({encoded_args!r})
try:
    result = None
{body}
    print({SENTINEL!r} + json.dumps({{"ok": True, "result": result}}, default=str, ensure_ascii=False))
except Exception as exc:
    print({SENTINEL!r} + json.dumps({{
        "ok": False,
        "error": str(exc),
        "traceback": traceback.format_exc()
    }}, ensure_ascii=False))
"""
    output = run_unreal_python(textwrap.dedent(wrapper), timeout=timeout)
    payload_line = None
    for line in reversed(output.splitlines()):
        if line.startswith(SENTINEL):
            payload_line = line[len(SENTINEL):]
            break

    if payload_line is None:
        raise RuntimeError(f"Unreal Python returned no structured result. Output: {output[-4000:]}")

    payload = json.loads(payload_line)
    if not payload.get("ok"):
        raise RuntimeError(payload.get("traceback") or payload.get("error") or "Unreal Python failed")
    return payload.get("result")
