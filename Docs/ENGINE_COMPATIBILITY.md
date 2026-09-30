# Engine compatibility

## Current documented target

As of 2026-09-30, Epic's public Unreal documentation exposed by the developer
site is **Unreal Engine 5.8**. This repository is therefore implemented and
documented against UE 5.8's public editor, C++, and Python API surface.

Relevant Epic references:

- https://dev.epicgames.com/documentation/en-us/unreal-engine/scripting-the-unreal-editor-using-python
- https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/
- https://dev.epicgames.com/documentation/en-us/unreal-engine/API
- https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5-8-release-notes

There is no public Unreal Engine 6 Python/C++ API reference to bind against at
the time of this update. UnrealMCP does **not** invent UE6 class or function
names.

## Forward compatibility strategy

UnrealMCP 1.2.2 combines runtime discovery, dynamic invocation, and real-engine
validation:

- `get_unreal_capabilities`
- `search_unreal_python_api`
- `describe_unreal_python_api`
- `check_unreal_api_paths`
- `get_enabled_plugins`
- `invoke_unreal_api`
- `invoke_editor_subsystem`
- `invoke_engine_subsystem`

Epic's Python `unreal` module is reflected from the C++/Blueprint surface
available in the running Editor and its enabled plugins. Runtime discovery is
therefore the authoritative way to determine what a future engine actually
exposes.

Purpose-built tools use current subsystem APIs such as:

- `EditorActorSubsystem`
- `EditorAssetSubsystem`
- `AssetEditorSubsystem`
- `LevelEditorSubsystem`
- `UnrealEditorSubsystem`
- `StaticMeshEditorSubsystem`
- `DataLayerManager`
- `WorldPartitionBlueprintLibrary`
- `LevelSequenceEditorSubsystem`
- `EditorValidatorSubsystem`

Optional/plugin-specific domains are guarded at runtime rather than assumed.

## Deprecated paths avoided

Where UE exposes subsystem replacements, UnrealMCP prefers them over legacy
Blueprint libraries. Static-mesh editing uses `StaticMeshEditorSubsystem`
instead of deprecated `EditorStaticMeshLibrary`, and Data Layer runtime state
uses `DataLayerManager` instead of deprecated `DataLayerSubsystem`.

The C++ UI uses `FAppStyle` from `Styling/AppStyle.h`.

The native Python handler uses `IPythonScriptPlugin::ExecPythonCommandEx`.
Literal multi-line code is executed in statement mode through a single
`exec(...)` wrapper, while file paths use file-execution mode.

## Automated tracking and proof

Official Epic documentation is checked daily by
`.github/workflows/epic-docs-watch.yml`. The tracked version and source hashes
are stored in `compat/epic-docs.json`.

A newly detected engine version is not marked compatible from documentation
alone. The self-hosted validation workflow must:

1. compile the plugin with that Unreal installation;
2. snapshot the live reflected Python API;
3. pass direct editor/subsystem smoke tests;
4. start the actual UnrealMCP TCP server headlessly;
5. pass native MCP commands over TCP;
6. pass the source-aware reflected API diff.

Compatibility evidence is stored in `compat/api` and `compat/reports`.

See `Docs/SELF_UPDATING.md` for the full update pipeline.
