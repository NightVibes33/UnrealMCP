"""UnrealMCP Model Context Protocol server.

This process speaks MCP to AI clients over stdio and translates tool calls to the
native Unreal Editor plugin over a localhost TCP bridge.
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import sys
from pathlib import Path

try:
    from mcp.server import MCPServer
except ImportError:
    # Compatibility with the v2 canonical module path.
    from mcp.server.mcpserver import MCPServer

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

mcp = MCPServer(
    "UnrealMCP",
    title="Unreal Engine MCP",
    description="AI tools for inspecting and controlling a live Unreal Editor instance.",
    instructions=(
        "Use read/inspect tools before destructive edits. Prefer purpose-built tools over "
        "execute_python. Save assets/levels explicitly after mutations. Unreal coordinates "
        "are centimeters and rotations are pitch/yaw/roll degrees."
    ),
    version="1.0.0",
)

def load_commands() -> int:
    """Discover and register every built-in command module."""
    commands_dir = ROOT / "Commands"
    count = 0
    for filename in sorted(commands_dir.glob("commands_*.py")):
        module_name = f"Commands.{filename.stem}"
        module = importlib.import_module(module_name)
        register = getattr(module, "register_all", None)
        if callable(register):
            register(mcp)
            count += 1
            print(f"Registered UnrealMCP command module: {filename.name}", file=sys.stderr)
    return count

def load_user_tools() -> int:
    """Load optional user-authored tools from MCP/UserTools."""
    user_tools_dir = ROOT / "UserTools"
    count = 0
    if not user_tools_dir.exists():
        return count

    for filename in sorted(user_tools_dir.glob("*.py")):
        if filename.name.startswith("_"):
            continue
        module_name = f"unreal_mcp_user_tool_{filename.stem}"
        spec = importlib.util.spec_from_file_location(module_name, filename)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        register = getattr(module, "register_tools", None)
        if callable(register):
            from utils import send_command
            register(mcp, {"send_command": send_command})
            count += 1
            print(f"Registered UnrealMCP user tool: {filename.name}", file=sys.stderr)
    return count

@mcp.resource("unrealmcp://capabilities")
def capabilities() -> str:
    """High-level capability map for agents."""
    return (
        "UnrealMCP provides scene/actor, asset, level, editor/PIE/viewport, material, "
        "Blueprint, project/system and raw Unreal Python tools. Use tools/list for the "
        "authoritative runtime tool schemas."
    )

@mcp.prompt()
def inspect_then_edit(task: str) -> str:
    """A safe workflow prompt for complex Unreal edits."""
    return (
        f"Task: {task}\n"
        "1. Inspect project/status and relevant assets or actors first.\n"
        "2. Make the smallest necessary edits with purpose-built UnrealMCP tools.\n"
        "3. Verify the changed objects by reading them back.\n"
        "4. Save the affected assets or level explicitly.\n"
        "5. Report any Unreal API limitation instead of guessing."
    )

def main() -> None:
    load_commands()
    load_user_tools()
    print("Starting UnrealMCP v1.0.0 (MCP SDK v2) over stdio", file=sys.stderr)
    mcp.run()

if __name__ == "__main__":
    main()
