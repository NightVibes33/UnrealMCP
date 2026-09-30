# UnrealMCP

> **AI control and automation for Unreal Editor through the Model Context Protocol (MCP).**

[![UnrealMCP checks](https://github.com/NightVibes33/UnrealMCP/actions/workflows/python-ci.yml/badge.svg?branch=master)](https://github.com/NightVibes33/UnrealMCP/actions/workflows/python-ci.yml)
[![Epic docs watcher](https://github.com/NightVibes33/UnrealMCP/actions/workflows/epic-docs-watch.yml/badge.svg?branch=master)](https://github.com/NightVibes33/UnrealMCP/actions/workflows/epic-docs-watch.yml)

UnrealMCP connects MCP-capable AI clients to a live Unreal Editor instance. The external Python process exposes structured MCP tools over **stdio**; the native Unreal Editor plugin performs editor operations through a loopback-only TCP bridge and Unreal's reflected Python/C++ editor APIs.

This fork extends the original `kvick-games/UnrealMCP` project into a much broader Unreal automation layer with runtime API discovery, dynamic invocation, real-engine compatibility validation, and automated tracking of new Epic documentation/releases.

**Current UnrealMCP version:** `1.2.2`  
**Default branch:** `master`  
**Current documented Unreal target:** **Unreal Engine 5.8**  
**External MCP SDK:** `mcp==2.2.0`

---

## What UnrealMCP does

An AI client can use UnrealMCP to inspect and modify a real Unreal Editor project using typed MCP tools instead of generating blind editor instructions.

Examples include:

- inspect the current project, world, actors, selections, assets, plugins, and available Unreal APIs;
- create, duplicate, transform, tag, select, organize, and delete actors;
- inspect and edit actor components and reflected editor properties;
- browse, import, duplicate, rename, save, open, and delete assets;
- create/load/save levels, including World Partition maps;
- inspect and manipulate Data Layers and World Partition state;
- control Play-In-Editor and editor viewport state;
- inspect and modify static meshes, Nanite, collision, UV channels, and CPU access;
- create and inspect materials and Blueprints;
- create and inspect Level Sequences;
- discover Niagara and PCG assets/components;
- run Unreal asset validation;
- execute Unreal Python for APIs that do not yet have a dedicated wrapper;
- discover and call newly reflected Unreal APIs at runtime before UnrealMCP has a purpose-built tool for them.

UnrealMCP is an **Editor integration**, not a packaged-game runtime API.

---

## Architecture

```text
MCP-capable AI client
(ChatGPT / Claude / Cursor / custom MCP host)
                    |
                    | Model Context Protocol over stdio
                    v
          MCP/unreal_mcp_bridge.py
                    |
                    | newline-delimited JSON
                    | TCP 127.0.0.1:13377 by default
                    v
          UnrealMCP native C++ plugin
                    |
                    +--> native C++ command handlers
                    |
                    +--> IPythonScriptPlugin
                    |
                    +--> reflected Unreal Python API
                    |
                    v
              Unreal Editor
```

### Why two layers?

The Python process is the actual MCP server. It owns MCP tool schemas, resources, prompts, discovery, and AI-facing behavior.

The C++ Unreal plugin owns the editor-side connection. It binds to loopback only, accepts framed JSON commands, provides native handlers, and can execute Unreal Python through `IPythonScriptPlugin::ExecPythonCommandEx`.

This keeps the MCP protocol independent from Unreal's process while still allowing direct editor control.

---

## Engine compatibility

UnrealMCP `1.2.2` is implemented against Epic's currently tracked **Unreal Engine 5.8** public documentation and reflected editor APIs.

The project does **not** invent undocumented UE6 symbols. Instead, compatibility with a future Unreal release is handled in three stages:

1. **Documentation detection** — official Epic pages are monitored for changed content and newly published engine versions.
2. **Runtime discovery** — the connected editor exposes its real `unreal` module, enabled plugins, classes, methods, and subsystems to the MCP.
3. **Real-engine validation** — a self-hosted Unreal runner compiles the C++ plugin, launches Unreal, runs direct editor smoke tests, tests the actual native MCP TCP bridge, snapshots the reflected API, and compares it with previous versions.

A newly detected Unreal version is therefore **not automatically claimed compatible simply because docs appeared**.

See:

- [Engine compatibility](Docs/ENGINE_COMPATIBILITY.md)
- [Self-updating system](Docs/SELF_UPDATING.md)
- [Compatibility evidence](compat/README.md)

---

## MCP tool surface

Built-in tools are automatically discovered from **17 command modules** in `MCP/Commands`.

| Area | Main capabilities |
| --- | --- |
| Runtime/API discovery | Engine/Python capability detection, plugin enumeration, symbol search, API description, API-path checks |
| Dynamic invocation | Call newly reflected Unreal APIs, EditorSubsystems, EngineSubsystems, assets, and reflected properties |
| System/project | Project paths, engine version, active world, selections, dirty packages, save operations, console commands |
| Scene | Scene summary, native object creation/modification/deletion |
| Actors | Search/list actors, inspect details, spawn by asset/class, transforms, tags, folders, reflected properties, duplicate/select/delete |
| Components | List components, edit component properties, SceneComponent transforms |
| Assets | Asset Registry search, list/load/inspect, import, duplicate, rename/move, save, delete, folders, asset editors |
| Levels | Current map info, list/load/create/save levels, partitioned-world creation, template maps, current sublevel |
| World building | World Partition information, Data Layers, editor Data Layer visibility/state |
| Editor/PIE | Start/stop PIE, viewport camera, game view, pilot/eject actor, redraw, light-map builds |
| Static meshes | LOD/triangle/vertex/UV inspection, materials, bounds, Nanite, collision, CPU access, UV channels |
| Materials | Create/modify/inspect materials, assign materials, inspect actor material slots |
| Blueprints | Create/modify/inspect Blueprints and create Blueprint event nodes |
| Sequencer | List/create/open/inspect Level Sequences and discover LevelSequenceEditorSubsystem support |
| Niagara / PCG | Niagara System discovery, PCG Graph discovery, PCG component discovery |
| Validation | EditorValidatorSubsystem discovery and asset validation |
| Python | Raw Unreal Python execution as the compatibility escape hatch |

The authoritative schemas for a running installation are always the MCP client's `tools/list` result.

### Runtime discovery tools

Important forward-compatibility tools include:

```text
get_unreal_capabilities
search_unreal_python_api
describe_unreal_python_api
check_unreal_api_paths
get_enabled_plugins
invoke_unreal_api
invoke_editor_subsystem
invoke_engine_subsystem
```

These allow an agent to inspect the **actual APIs exposed by the current Unreal build** rather than assuming a method exists because it existed in another engine version.

---

## Dynamic Unreal API invocation

Purpose-built tools should be preferred because they have stable, understandable schemas. For newly exposed Unreal APIs, UnrealMCP also provides dynamic invocation.

Supported tagged argument forms include patterns such as:

```json
{"$asset": "/Game/Props/SM_Box.SM_Box"}
```

```json
{"$class": "/Script/Engine.PointLight"}
```

```json
{"$name": "ExampleName"}
```

```json
{"$vector": [0, 0, 100]}
```

```json
{"$rotator": {"pitch": 0, "yaw": 90, "roll": 0}}
```

```json
{"$enum": "DataLayerRuntimeState.ACTIVATED"}
```

This is what allows a newer reflected API to become usable immediately even before a dedicated UnrealMCP wrapper is added.

---

## Requirements

### Unreal side

- Unreal Editor with the **Python Editor Script Plugin** available.
- **Editor Scripting Utilities**.
- A C++-capable Unreal project/toolchain when compiling the plugin.
- UE 5.8 is the currently documented target tracked by this repository.

Optional feature groups depend on the corresponding Unreal plugins being enabled. Examples include Niagara, PCG, Level Sequence Editor, or Data Validation.

### External MCP side

- Python 3.10+ recommended.
- Python 3.11 and 3.13 are continuously tested by hosted CI.
- `mcp==2.2.0` is currently pinned for reproducibility.

UE 5.8 embeds Python 3.11.8 for in-editor Python according to the tracked Epic documentation.

---

## Installation

### 1. Add the plugin to an Unreal project

From the Unreal project's root:

```bash
git clone https://github.com/NightVibes33/UnrealMCP.git Plugins/UnrealMCP
```

Your project should then contain:

```text
YourProject/
├── YourProject.uproject
└── Plugins/
    └── UnrealMCP/
        ├── UnrealMCP.uplugin
        ├── Source/
        ├── MCP/
        ├── Automation/
        └── compat/
```

Regenerate project files if your Unreal setup requires it, then build the Editor target.

The plugin descriptor enables these dependencies:

- `PythonScriptPlugin`
- `EditorScriptingUtilities`

### 2. Create the external MCP Python environment

#### Windows

```bat
Plugins\UnrealMCP\MCP\setup_unreal_mcp.bat
```

#### macOS / Linux

```bash
./Plugins/UnrealMCP/MCP/setup_unreal_mcp.sh
```

The scripts create:

```text
MCP/python_env/
```

and install the pinned dependency set from `MCP/requirements.txt`.

### 3. Open Unreal Editor

Enable **UnrealMCP** if necessary and start the UnrealMCP server from its Editor toolbar/control UI.

Default editor bridge endpoint:

```text
127.0.0.1:13377
```

### 4. Configure an MCP client

The MCP client launches `MCP/unreal_mcp_bridge.py` using the Python environment created above.

#### Windows example

```json
{
  "mcpServers": {
    "unreal": {
      "command": "C:\\YourProject\\Plugins\\UnrealMCP\\MCP\\python_env\\Scripts\\python.exe",
      "args": [
        "C:\\YourProject\\Plugins\\UnrealMCP\\MCP\\unreal_mcp_bridge.py"
      ]
    }
  }
}
```

#### macOS / Linux example

```json
{
  "mcpServers": {
    "unreal": {
      "command": "/path/to/YourProject/Plugins/UnrealMCP/MCP/python_env/bin/python",
      "args": [
        "/path/to/YourProject/Plugins/UnrealMCP/MCP/unreal_mcp_bridge.py"
      ]
    }
  }
}
```

Any MCP host that supports local **stdio** servers can use this pattern.

---

## Configuration

The external bridge recognizes:

| Variable | Default | Purpose |
| --- | --- | --- |
| `UNREAL_MCP_HOST` | `127.0.0.1` | Unreal TCP bridge host |
| `UNREAL_MCP_PORT` | `13377` | Unreal TCP bridge port |
| `UNREAL_MCP_TIMEOUT` | `30` | Command timeout in seconds |
| `UNREAL_MCP_BUFFER_SIZE` | internal/default | Socket receive buffer override |

The native bridge intentionally binds to loopback rather than all interfaces.

### Headless validation flags

The C++ plugin also supports:

```text
-UnrealMCPServer
-UnrealMCPPort=13377
```

`-UnrealMCPServer` starts the TCP bridge after engine initialization without requiring toolbar interaction. This is used by the real-engine compatibility workflow.

---

## MCP resources and prompt

The MCP server also publishes resources describing itself:

```text
unrealmcp://capabilities
unrealmcp://engine-compatibility
unrealmcp://update-status
```

It also exposes an `inspect_then_edit` prompt intended to encourage a robust workflow:

```text
inspect -> edit -> read back -> validate -> save
```

---

## Self-updating compatibility system

UnrealMCP contains a complete update/compatibility pipeline rather than relying on manual documentation checks.

### Epic documentation watcher

`.github/workflows/epic-docs-watch.yml` runs daily and can also run manually.

It tracks official Epic sources including:

- What's New;
- engine release notes;
- Unreal Python API;
- Unreal Editor Python scripting documentation;
- Unreal C++ API.

Normalized page content is hashed and stored in:

```text
compat/epic-docs.json
```

The current baseline is initialized and tracks **UE 5.8**.

For changes that do not introduce a new Unreal engine version, the generated documentation state/evidence can be committed directly after hosted validation.

When a new major/minor Unreal version is detected, the watcher creates an automation branch such as:

```text
automation/epic-docs-6.0
```

That branch is not considered engine-compatible until the real Unreal validator passes.

If repository settings prevent GitHub Actions from creating a PR, the update branch is preserved instead of failing the entire detection pipeline.

### Real Unreal compatibility validation

`.github/workflows/unreal-engine-validation.yml` is designed for a Windows x64 self-hosted runner with these labels:

```text
self-hosted
Windows
X64
unreal
```

The validator:

1. discovers Unreal through `UNREAL_ENGINE_ROOT`, Epic Launcher's `LauncherInstalled.dat`, or common `UE_*` install locations;
2. selects the expected major/minor when more than one Unreal version is installed;
3. compiles the real plugin using `RunUAT BuildPlugin`;
4. creates a disposable Unreal validation project;
5. snapshots the live reflected `unreal` API;
6. runs a direct Unreal Editor/subsystem smoke test;
7. launches the actual native UnrealMCP server headlessly;
8. sends real TCP bridge commands including:
   - `get_scene_info`
   - `execute_python`
   - actor creation
   - actor deletion
9. compares the reflected API against the prior committed snapshot;
10. checks whether removed/changed APIs are actually referenced by UnrealMCP source;
11. stores compatibility evidence under `compat/api` and `compat/reports`;
12. promotes the update only when the compatibility gates are safe.

To allow newly detected engine versions to dispatch real validation automatically, configure the repository Actions variable:

```text
UNREAL_MCP_AUTOVALIDATE=true
```

A matching Unreal installation must already exist on the self-hosted runner.

### Compatibility evidence

```text
compat/
├── epic-docs.json
├── api/
└── reports/
```

Generated API/smoke evidence intentionally avoids volatile timestamps, temporary project paths, and machine-specific values where possible, reducing meaningless source-control changes.

### Dependency updates

Dependabot monitors:

- GitHub Actions;
- the external MCP Python SDK.

Minor/patch updates are grouped and tested. Major dependency changes are intentionally excluded from unattended updates.

The Dependabot merge workflow only automatically merges a same-major version transition after normal UnrealMCP hosted CI succeeds.

See [Docs/SELF_UPDATING.md](Docs/SELF_UPDATING.md) for the complete behavior and failure model.

---

## CI and validation

Hosted CI runs on Python **3.11** and **3.13**.

Current hosted checks include:

- install the pinned MCP SDK;
- compile all Python in `MCP/` and `Automation/`;
- import/register the complete command surface;
- MCP TCP transport tests;
- updater/API-diff unit tests;
- native MCP smoke-client regression tests;
- GitHub workflow YAML parsing;
- PowerShell parser validation for the Unreal runner script;
- guards against deprecated API paths that the project intentionally replaced.

The hosted environment does **not** prove Unreal C++ binary compatibility because GitHub-hosted runners do not contain Unreal Engine. That proof belongs to the real-engine self-hosted workflow described above.

---

## Transport behavior

The native TCP layer uses newline-delimited UTF-8 JSON.

Key behavior:

- binds to `127.0.0.1`;
- supports requests split across multiple socket reads;
- keeps partial request data until a complete frame is available;
- maintains compatibility with the original one-object request behavior;
- enforces request-size limits;
- tracks client inactivity correctly;
- allows large AI-generated Python/tool payloads without assuming one socket read contains the complete request.

---

## Unreal Python execution

The native `execute_python` path uses:

```text
IPythonScriptPlugin::ExecPythonCommandEx
```

instead of writing temporary wrapper scripts and routing commands through `GEngine->Exec("py ...")`.

Literal multi-line Python is safely escaped into a single Python `exec(...)` statement and executed in statement mode so captured log output remains available.

File-based execution uses file execution mode.

Use purpose-built MCP tools whenever possible. `execute_python` exists as a compatibility/advanced escape hatch.

---

## Safety

UnrealMCP can perform destructive editor operations.

Tools can:

- change actor/component state;
- overwrite reflected properties;
- rename or move assets;
- delete actors/assets;
- execute arbitrary Unreal Python.

Recommended practice:

1. keep the project under source control;
2. inspect relevant actors/assets before mutating them;
3. use Unreal transactions/undo-aware tools where available;
4. read changes back after mutation;
5. explicitly save affected maps/assets;
6. do not expose the native TCP editor bridge to untrusted networks.

The native bridge is loopback-only by default specifically to reduce unnecessary network exposure.

---

## Troubleshooting

### MCP client starts but Unreal tools fail

Verify that Unreal Editor is open and the native UnrealMCP server is running.

Default target:

```text
127.0.0.1:13377
```

### Connection refused

The external MCP Python process is running, but the Unreal plugin's TCP server is not listening. Start UnrealMCP from the Editor UI or use the headless `-UnrealMCPServer` flag for automation.

### A tool exists but the Unreal API is missing

The tool may depend on an optional plugin or an engine-specific API.

Use:

```text
get_unreal_capabilities
search_unreal_python_api
describe_unreal_python_api
get_enabled_plugins
```

to inspect the current editor rather than assuming feature availability.

### New Unreal version detected but not automatically promoted

That is expected until a self-hosted runner with the matching Unreal release compiles and validates the plugin.

Check:

- the `automation/epic-docs-<version>` branch;
- the real-engine validation workflow;
- `compat/reports/`;
- whether `UNREAL_MCP_AUTOVALIDATE=true` is configured;
- whether the self-hosted runner has labels `self-hosted, Windows, X64, unreal`;
- whether the requested Unreal version is installed.

### Optional subsystem/tool is unavailable

Enable the corresponding Unreal plugin, restart the Editor if required, then rerun `get_unreal_capabilities`.

---

## Development

### Python checks

From the repository root:

```bash
python -m pip install -r MCP/requirements.txt
python -m compileall -q MCP Automation
python -m unittest discover -s Automation/tests -v
```

Transport tests:

```bash
cd MCP
python -m unittest tests.test_transport -v
```

### Command modules

Built-in modules live in:

```text
MCP/Commands/commands_*.py
```

The bridge imports every matching module and calls its `register_all(mcp)` function.

### User extensions

Local/custom MCP tools can live under:

```text
MCP/UserTools/
```

See `MCP/UserTools/README.md` and `MCP/UserTools/example_tool.py`.

### Automation

Compatibility/update tooling lives under:

```text
Automation/
```

Important pieces include:

```text
check_epic_docs.py
snapshot_unreal_api.py
diff_unreal_api.py
unreal_smoke_test.py
mcp_bridge_smoke_test.py
run_unreal_validation.ps1
```

---

## Repository layout

```text
UnrealMCP/
├── .github/
│   ├── dependabot.yml
│   └── workflows/
├── Automation/
│   ├── tests/
│   ├── check_epic_docs.py
│   ├── diff_unreal_api.py
│   ├── mcp_bridge_smoke_test.py
│   ├── run_unreal_validation.ps1
│   ├── snapshot_unreal_api.py
│   └── unreal_smoke_test.py
├── compat/
│   ├── api/
│   ├── reports/
│   ├── README.md
│   └── epic-docs.json
├── Docs/
│   ├── ENGINE_COMPATIBILITY.md
│   └── SELF_UPDATING.md
├── MCP/
│   ├── Commands/
│   ├── UserTools/
│   ├── tests/
│   ├── requirements.txt
│   ├── setup_unreal_mcp.bat
│   ├── setup_unreal_mcp.sh
│   └── unreal_mcp_bridge.py
├── Resources/
├── Source/
│   └── UnrealMCP/
├── UnrealMCP.uplugin
└── README.md
```

---

## Project status

At the current `master` baseline:

- UnrealMCP version: **1.2.2**
- tracked Epic Unreal docs version: **5.8**
- Epic docs baseline: **initialized**
- MCP command modules: **17**
- hosted Python matrix: **3.11 + 3.13**
- native bridge endpoint: **loopback only**
- real-engine compatibility proof: performed by the self-hosted Unreal workflow
- future engine APIs: supported through runtime discovery/dynamic invocation, then promoted to dedicated wrappers as needed

---

## Credits

UnrealMCP is based on the original project by **kvick / Dreamatron Studios**:

https://github.com/kvick-games/UnrealMCP

This fork extends that foundation with a substantially larger MCP tool surface, modern Unreal editor subsystem usage, current MCP SDK support, runtime compatibility discovery, dynamic API invocation, automated Epic documentation tracking, and real-engine/native-MCP compatibility validation.
