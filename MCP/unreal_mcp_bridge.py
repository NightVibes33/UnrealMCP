"""UnrealMCP Model Context Protocol server.

The Python process speaks MCP over stdio to an AI client and translates tool
calls to the native Unreal Editor plugin over a loopback TCP bridge.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import sys
from pathlib import Path

try:
    from mcp.server import MCPServer
except ImportError:
    from mcp.server.mcpserver import MCPServer

VERSION = "1.2.2"
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def _compat_state() -> dict:
    path = ROOT.parent / "compat" / "epic-docs.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"latest_version": "unknown", "initialized": False, "sources": {}}


mcp = MCPServer(
    "UnrealMCP",
    title="Unreal Engine MCP",
    description="AI tools for inspecting, editing and automating a live Unreal Editor instance.",
    instructions=(
        "Inspect before editing. Prefer purpose-built tools over execute_python. "
        "Use get_unreal_capabilities/search_unreal_python_api when an engine API may differ "
        "between Unreal releases or plugins. Use editor undo-aware tools where available. "
        "Save affected assets or levels explicitly after mutations. Unreal coordinates are "
        "centimeters and rotations use pitch/yaw/roll degrees."
    ),
    version=VERSION,
)

def load_commands() -> int:
    """Discover and register every built-in commands_*.py module."""
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
        "UnrealMCP 1.2.2 provides project/system, live API discovery and dynamic invocation, actor/component, asset, "
        "level/world-partition/data-layer, editor/PIE/viewport, static-mesh/Nanite/collision, "
        "material, Blueprint, Level Sequence, Niagara/PCG discovery, validation and Unreal "
        "Python escape-hatch tools. Use tools/list for exact schemas and get_unreal_capabilities "
        "to detect the APIs/plugins exposed by the running Unreal build. Newly exposed public Unreal APIs can be called through the dynamic invocation tools before a dedicated wrapper exists."
    )

@mcp.resource("unrealmcp://engine-compatibility")
def engine_compatibility() -> str:
    """Explain the engine compatibility strategy using the tracked Epic docs state."""
    state = _compat_state()
    version = state.get("latest_version") or "unknown"
    return (
        f"The latest Epic Unreal documentation version tracked by this checkout is {version}. "
        "Forward compatibility is handled through runtime unreal-module reflection, dynamic "
        "public API invocation, feature guards, and subsystem-based APIs. Newly detected engine "
        "versions are not marked binary-compatible until the real-engine validation workflow "
        "compiles the plugin and runs live smoke tests."
    )


@mcp.resource("unrealmcp://update-status")
def update_status() -> str:
    """Return the machine-readable Epic documentation/update state."""
    return json.dumps(_compat_state(), indent=2, sort_keys=True)

@mcp.prompt()
def inspect_then_edit(task: str) -> str:
    """A robust workflow prompt for complex Unreal edits."""
    return (
        f"Task: {task}\n"
        "1. Call unreal_status/get_unreal_capabilities if engine or plugin support matters.\n"
        "2. Inspect relevant assets, actors, components or API symbols.\n"
        "3. Make the smallest necessary undo-aware edits with purpose-built tools.\n"
        "4. Read the changed objects back and validate where possible.\n"
        "5. Save affected assets/levels explicitly.\n"
        "6. If an API differs in this engine build, discover it with search/describe tools rather than guessing."
    )

def main() -> None:
    command_modules = load_commands()
    user_modules = load_user_tools()
    print(
        f"Starting UnrealMCP {VERSION} over stdio "
        f"({command_modules} built-in modules, {user_modules} user modules)",
        file=sys.stderr,
    )
    mcp.run()

if __name__ == "__main__":
    main()
