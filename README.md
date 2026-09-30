# UnrealMCP

UnrealMCP is an **AI-facing Model Context Protocol server for Unreal Editor**.
An MCP-capable AI client receives structured Unreal tools; the Python MCP server
forwards editor operations to the native Unreal plugin over a loopback TCP bridge.

## Current engine target

This release is updated against **Epic's public Unreal Engine 5.8 documentation
and Python API**. As of September 30, 2026, Epic's public developer site does
not expose Unreal Engine 6 Python/C++ API documentation, so the project does not
invent undocumented UE6 symbols.

Instead, UnrealMCP 1.2.2 is **UE6-forward-compatible by discovery, live invocation, and real-engine validation**: agents can
query the live reflected `unreal` module, detect subsystems/plugins at runtime,
and adapt when newer engine builds expose changed APIs.

See [Docs/ENGINE_COMPATIBILITY.md](Docs/ENGINE_COMPATIBILITY.md).

## Architecture

```text
ChatGPT / Claude / Cursor / another MCP client
                     |
                 MCP over stdio
                     |
           MCP/unreal_mcp_bridge.py
                     |
       newline-delimited JSON over 127.0.0.1
                     |
           UnrealMCP C++ editor plugin
                     |
       Unreal Editor + reflected Python API
```

The Python process is the MCP server. The C++ plugin is a localhost editor bridge
and native command host.

## 1.2.2 tool surface

### Runtime/API discovery

- `get_unreal_capabilities`
- `search_unreal_python_api`
- `describe_unreal_python_api`
- `check_unreal_api_paths`
- `get_enabled_plugins`
- `invoke_unreal_api`
- `invoke_editor_subsystem`
- `invoke_engine_subsystem`

These are the compatibility layer for plugin-specific APIs and future engine versions. The dynamic invocation tools can call newly reflected public Unreal APIs before a dedicated wrapper exists.

### Project/system

- engine/Python/project/world status
- dirty map/content package inspection
- save dirty packages
- selected assets/actors
- editor console commands

### Actors and components

- list and inspect loaded actors
- spawn from assets/Blueprints or UClass paths
- transforms, tags, folders and reflected properties
- duplicate, select and bulk delete
- list components
- component reflected-property editing
- SceneComponent relative transforms
- editor undo transactions for mutations

### Assets and Content Browser

- Asset Registry search
- EditorAssetSubsystem listing/inspection
- import, duplicate, move/rename, save and delete
- create content directories
- open and close native asset editors

### Levels, World Partition and Data Layers

- list/load/create/save maps
- create blank **World Partition** maps
- create maps from templates
- inspect streaming levels
- inspect World Partition bounds/actor descriptors
- Data Layer enumeration through `DataLayerManager`
- Data Layer runtime state
- editor Data Layer visibility

### Editor / viewport / PIE

- start/stop/query Play-In-Editor
- viewport camera get/set
- viewport config keys and Game View
- pilot/eject actor
- viewport invalidation
- light-map builds

### Static Mesh / Nanite

Uses the current `StaticMeshEditorSubsystem` rather than deprecated
`EditorStaticMeshLibrary` calls.

- LOD/section/triangle/vertex/UV inspection
- material slots and bounds
- Nanite state and Nanite triangle/vertex counts
- toggle Nanite
- CPU-access flag
- simple collision generation
- convex decomposition collision
- add UV channels

### Materials and Blueprints

- native material create/modify/inspect handlers
- material assignment
- Blueprint create/modify/inspect
- Blueprint event creation
- raw Unreal Python fallback for unsupported editor APIs

### Sequencer / VFX / PCG / validation

- Level Sequence discovery, creation, inspection and editor opening
- LevelSequenceEditorSubsystem capability discovery
- Niagara System discovery
- PCG Graph/component discovery
- EditorValidatorSubsystem capability discovery and compatible asset validation

## Why runtime discovery matters

Epic's Python API is reflected from what the current editor exposes to
Blueprint/C++. Plugins can add more classes and functions. If an API differs in
a future engine version, the AI can inspect the live build instead of blindly
calling an old method.

## Requirements

- Unreal Engine editor build with Python Editor Script Plugin
- Current documented target: UE 5.8
- Python 3.11.8 is embedded by UE 5.8 for in-editor Python
- Python 3.10+ recommended for the external MCP bridge environment
- MCP Python SDK v2 (`mcp==2.2.0` currently; Dependabot tests future minor/patch releases)

Optional tool groups require their corresponding Unreal plugins, for example
Niagara, PCG, Level Sequence Editor, or Data Validation.

## Install

Clone into the project's plugin directory:

```bash
git clone https://github.com/NightVibes33/UnrealMCP.git Plugins/UnrealMCP
```

Regenerate project files and build the Unreal Editor target. Then enable
**UnrealMCP** and the **Python Editor Script Plugin**.

### Set up the external MCP environment

Windows:

```bat
MCP\setup_unreal_mcp.bat
```

macOS/Linux:

```bash
./MCP/setup_unreal_mcp.sh
```

Open Unreal and start the MCP bridge from the UnrealMCP toolbar/control panel.

## MCP client configuration

Any local stdio MCP client can launch the bridge.

Windows example:

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

macOS/Linux example:

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

Optional bridge overrides:

- `UNREAL_MCP_HOST` (default `127.0.0.1`)
- `UNREAL_MCP_PORT` (default `13377`)
- `UNREAL_MCP_TIMEOUT` (default `30` seconds)

## Self-updating compatibility

UnrealMCP now includes an automated compatibility pipeline:

- daily official Epic documentation monitoring;
- generated documentation-state PRs;
- automatic tracking of newly published Unreal release notes;
- deterministic live Unreal Python API snapshots and version-to-version diffs;
- a real Windows Unreal build workflow for a self-hosted runner;
- direct Unreal editor/subsystem smoke tests;
- native UnrealMCP TCP bridge smoke tests using real MCP commands;
- automatic safe promotion only when compatibility gates pass, with a PR-preferred/direct-promotion fallback when repository settings block Actions-created PRs;
- Dependabot updates for GitHub Actions and the pinned MCP SDK.

The real-engine validator can auto-detect Epic Launcher installs, select the requested
major/minor when multiple Unreal versions are present, and can auto-start the MCP bridge
headlessly with `-UnrealMCPServer`.

For the full setup and safety model, see [Docs/SELF_UPDATING.md](Docs/SELF_UPDATING.md).

## Transport and safety

The native bridge binds to loopback only. Requests are newline-delimited JSON,
accumulated across socket reads, and size-limited. Do not expose an editor-control
bridge to untrusted networks.

Tools can mutate or delete project content and `execute_python` can run arbitrary
Unreal Python. Keep the project under source control.

## Development

Python validation:

```bash
python -m compileall -q MCP
cd MCP
python -m unittest tests.test_transport -v
```

Built-in command modules are auto-discovered from
`MCP/Commands/commands_*.py`. Local extensions can be added under
`MCP/UserTools`.

## Credits

Based on the original MIT-licensed UnrealMCP project by kvick / Dreamatron
Studios, with the NightVibes33 fork extending the MCP and Unreal editor surface.
