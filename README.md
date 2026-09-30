# UnrealMCP

**UnrealMCP is an AI-facing Model Context Protocol (MCP) integration for Unreal Engine.**
It lets MCP-capable agents inspect and control a live Unreal Editor through structured tools.

This fork modernizes the original `kvick-games/UnrealMCP` implementation for the current MCP SDK
and expands it from a small scene/material demo into a broader editor automation surface.

## Architecture

```text
ChatGPT / Claude / Cursor / other MCP client
                  |
              MCP over stdio
                  |
        MCP/unreal_mcp_bridge.py
                  |
          JSON over localhost TCP
                  |
         UnrealMCP C++ editor plugin
                  |
        Unreal Editor + Unreal Python API
```

The Python process is the actual MCP server exposed to the AI client. The Unreal plugin is a
localhost editor bridge and native command host.

## Major capabilities

- **Project/system:** engine version, project paths, current world, selections, save dirty assets, console commands
- **Scene/actors:** list, inspect, create, delete, duplicate, select, transform, tags, reflected properties
- **Assets:** registry search, inspect, import, duplicate, rename/move, save, delete, create folders
- **Levels/maps:** list, inspect current level, load, create and save maps
- **Editor/PIE:** start/stop/query PIE, viewport camera get/set, actor focus
- **Materials:** create, modify, inspect, assign and enumerate actor material slots
- **Blueprints:** create, inspect, modify and add event nodes through native C++ handlers
- **Python escape hatch:** execute Unreal Python for APIs that do not yet have a dedicated tool
- **MCP primitives:** tools, an agent-oriented capability resource, and a safe inspect/edit prompt

The purpose-built tools are intentionally preferred over arbitrary Python because they give AI
clients stable schemas and smaller, auditable actions.

## MCP compatibility

The bridge targets the stable **MCP Python SDK v2** (`mcp>=2.2,<3`) and uses `MCPServer`.
It works over stdio, so it can be launched by any MCP client that supports local stdio servers.

## Unreal compatibility

Target: Unreal Engine 5.5+ editor builds with the **Python Editor Script Plugin** enabled.
Some Unreal Python APIs move between engine releases; when a dedicated wrapper is unavailable,
`execute_python` remains the compatibility fallback.

## Install

Clone this repository into your project's plugin directory:

```bash
git clone https://github.com/NightVibes33/UnrealMCP.git Plugins/UnrealMCP
```

Regenerate project files, build your editor target, open Unreal, then enable:

- UnrealMCP
- Python Editor Script Plugin
- Editor Scripting Utilities

In Unreal, open the **MCP Server Control Panel** from the toolbar and start the server.

### Python environment

From `Plugins/UnrealMCP/MCP`:

**Windows**

```bat
py -m venv python_env
python_env\Scripts\python -m pip install -r requirements.txt
```

**macOS / Linux**

```bash
python3 -m venv python_env
./python_env/bin/python -m pip install -r requirements.txt
```

## MCP client configuration

Point the client at the Python interpreter inside `MCP/python_env` and run
`MCP/unreal_mcp_bridge.py`.

Example on Windows:

```json
{
  "mcpServers": {
    "unreal": {
      "command": "C:\\YourProject\\Plugins\\UnrealMCP\\MCP\\python_env\\Scripts\\python.exe",
      "args": ["C:\\YourProject\\Plugins\\UnrealMCP\\MCP\\unreal_mcp_bridge.py"]
    }
  }
}
```

Example on macOS/Linux:

```json
{
  "mcpServers": {
    "unreal": {
      "command": "/path/to/Plugins/UnrealMCP/MCP/python_env/bin/python",
      "args": ["/path/to/Plugins/UnrealMCP/MCP/unreal_mcp_bridge.py"]
    }
  }
}
```

Optional environment overrides:

- `UNREAL_MCP_HOST` — defaults to `127.0.0.1`
- `UNREAL_MCP_PORT` — defaults to the C++ plugin port (`13377`)
- `UNREAL_MCP_TIMEOUT` — command timeout in seconds (default `30`)

## Tool groups

At runtime, use the MCP client's `tools/list` view for the authoritative JSON schemas.

| Group | Representative tools |
|---|---|
| System | `unreal_status`, `save_all_dirty_assets`, `get_selected_assets`, `execute_console_command` |
| Scene | `get_scene_info`, `create_object`, `modify_object`, `delete_object` |
| Actors | `list_actors`, `get_actor_details`, `set_actor_transform`, `set_actor_tags`, `duplicate_actor`, `select_actors` |
| Assets | `search_assets`, `get_asset_info`, `import_asset`, `duplicate_asset`, `rename_asset`, `save_asset`, `delete_asset` |
| Levels | `get_current_level`, `list_levels`, `load_level`, `create_level`, `save_current_level` |
| Editor | `is_pie_running`, `start_pie`, `stop_pie`, `get_viewport_camera`, `set_viewport_camera`, `focus_viewport_on_actor` |
| Materials | `create_material`, `modify_material`, `get_material_info`, `assign_material`, `get_actor_materials` |
| Blueprints | `create_blueprint`, `modify_blueprint`, `get_blueprint_info`, `create_blueprint_event` |
| Advanced | `execute_python` |

## Safety and transport

The Unreal-side TCP listener is bound to `127.0.0.1` by default. Do not expose the editor bridge
to untrusted networks: tools can modify and delete project content and `execute_python` can run
arbitrary Unreal Python.

Requests are newline-delimited JSON and are accumulated before parsing, so large tool payloads
are not assumed to arrive in one TCP read.

Use source control and review changes before committing them.

## Development

Python syntax check:

```bash
python -m compileall -q MCP
```

The command modules are discovered automatically from `MCP/Commands/commands_*.py`.
To add a tool category, create a module with `register_all(mcp)`.

User-specific extensions can live in `MCP/UserTools/*.py` and expose
`register_tools(mcp, helpers)`.

## Credits and license

Based on the original MIT-licensed project by **kvick / Dreamatron Studios**:
`kvick-games/UnrealMCP`.

Existing original-source copyright and license terms remain applicable.
