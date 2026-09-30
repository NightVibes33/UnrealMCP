"""TCP transport helpers for the Unreal editor bridge."""

from __future__ import annotations

import json
import os
import socket
import sys
from typing import Any

DEFAULT_HOST = os.getenv("UNREAL_MCP_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.getenv("UNREAL_MCP_PORT", "13377"))
DEFAULT_BUFFER_SIZE = int(os.getenv("UNREAL_MCP_BUFFER_SIZE", "65536"))
DEFAULT_TIMEOUT = float(os.getenv("UNREAL_MCP_TIMEOUT", "30"))

def _load_cpp_defaults() -> tuple[int, int]:
    port = DEFAULT_PORT
    buffer_size = DEFAULT_BUFFER_SIZE
    try:
        plugin_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        constants_path = os.path.join(plugin_dir, "Source", "UnrealMCP", "Public", "MCPConstants.h")
        if not os.path.exists(constants_path):
            return port, buffer_size

        content = open(constants_path, "r", encoding="utf-8").read()
        port_match = re_search_int(content, "DEFAULT_PORT")
        buffer_match = re_search_int(content, "DEFAULT_RECEIVE_BUFFER_SIZE")
        if port_match is not None and "UNREAL_MCP_PORT" not in os.environ:
            port = port_match
        if buffer_match is not None and "UNREAL_MCP_BUFFER_SIZE" not in os.environ:
            buffer_size = buffer_match
    except Exception as exc:
        print(f"Warning: could not read MCPConstants.h: {exc}", file=sys.stderr)
    return port, buffer_size

def re_search_int(content: str, name: str) -> int | None:
    import re
    match = re.search(rf"\b{name}\s*=\s*(\d+)", content)
    return int(match.group(1)) if match else None

DEFAULT_PORT, DEFAULT_BUFFER_SIZE = _load_cpp_defaults()

class UnrealMCPConnectionError(RuntimeError):
    """Raised when the Python MCP server cannot reach the Unreal editor plugin."""

def send_command(
    command_type: str,
    params: dict[str, Any] | None = None,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
) -> dict[str, Any]:
    """Send one newline-delimited JSON command to the Unreal editor plugin."""
    payload = json.dumps(
        {"type": command_type, "params": params or {}},
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8") + b"\n"

    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            sock.sendall(payload)
            chunks: list[bytes] = []
            total = 0

            while True:
                chunk = sock.recv(DEFAULT_BUFFER_SIZE)
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
                if total > 32 * 1024 * 1024:
                    raise UnrealMCPConnectionError("Unreal MCP response exceeded 32 MiB")

                raw = b"".join(chunks).strip()
                try:
                    return json.loads(raw.decode("utf-8"))
                except json.JSONDecodeError:
                    continue

        raise UnrealMCPConnectionError("Unreal MCP closed the connection without a JSON response")
    except (ConnectionRefusedError, TimeoutError, socket.timeout, OSError) as exc:
        raise UnrealMCPConnectionError(
            f"Could not communicate with Unreal MCP at {host}:{port}: {exc}"
        ) from exc

__all__ = [
    "DEFAULT_HOST",
    "DEFAULT_PORT",
    "DEFAULT_TIMEOUT",
    "UnrealMCPConnectionError",
    "send_command",
]
