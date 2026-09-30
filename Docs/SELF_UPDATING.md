# Self-updating UnrealMCP

UnrealMCP 1.2.1 has two update loops: a GitHub-hosted documentation/dependency loop and a real-engine validation loop.

## 1. Epic documentation watcher

`.github/workflows/epic-docs-watch.yml` runs daily and can also be started manually.

It monitors official Epic sources, normalizes their visible content, hashes it, and tracks the latest observed Unreal documentation version in `compat/epic-docs.json`.

When documentation changes:

1. The generated state/report is validated with the normal Python/MCP tests.
2. An `automation/epic-docs-<version>` branch is created or refreshed.
3. A pull request is opened.
4. Same-version documentation-state changes are squash-merged after hosted validation.
5. A newly observed Unreal major/minor stays open until a real Unreal installation proves compatibility.

The watcher automatically changes the tracked release-notes URL when a new Unreal major/minor version appears.

## 2. Real Unreal compatibility validator

`.github/workflows/unreal-engine-validation.yml` runs on a Windows self-hosted runner labelled:

    self-hosted
    Windows
    X64
    unreal

The validator:

- reads `UNREAL_ENGINE_ROOT` when explicitly configured;
- also discovers Epic Launcher installs through `LauncherInstalled.dat`;
- also scans common `UE_*` install directories;
- selects the requested major/minor when several Unreal versions are installed;
- compiles the actual plugin with `RunUAT BuildPlugin`;
- creates a disposable Unreal project;
- captures a deterministic reflected `unreal` Python API snapshot;
- runs a direct Unreal editor/subsystem smoke test;
- launches Unreal headlessly with the actual UnrealMCP TCP server auto-started;
- tests `get_scene_info`, `execute_python`, actor creation, and actor deletion through the native TCP bridge;
- compares the new reflected API against the previous committed snapshot;
- checks whether removed or changed APIs are referenced by UnrealMCP source;
- records evidence under `compat/api` and `compat/reports`;
- can merge an automated version-update PR only when every compatibility gate passes.

### Headless bridge flags

The plugin supports these validation flags:

    -UnrealMCPServer
    -UnrealMCPPort=13377

`-UnrealMCPServer` starts the loopback bridge after engine initialization without requiring the toolbar. UI/Slate setup is skipped for unattended validation runs.

### Deterministic compatibility evidence

Generated snapshots intentionally omit timestamps, temporary project paths, and machine/platform strings. Smoke-test results also avoid unstable actor/object values.

That means source-control changes represent real Unreal/API/plugin changes rather than a different runner, temp directory, or execution time.

### Automatic dispatch

Set this repository Actions variable once:

    UNREAL_MCP_AUTOVALIDATE=true

Then a newly detected Unreal documentation version automatically dispatches the real-engine validation workflow on the update branch.

The self-hosted runner must already have the matching Unreal binaries installed. GitHub-hosted runners do not ship Unreal Engine, and Epic does not provide a general public unattended installer that can automatically install every future release.

If the new engine is not installed yet, the version-update PR remains open instead of being incorrectly marked compatible.

## 3. Runtime forward compatibility

Even before a purpose-built wrapper is added, new reflected Unreal Python APIs can be used through:

- `search_unreal_python_api`
- `describe_unreal_python_api`
- `invoke_unreal_api`
- `invoke_editor_subsystem`
- `invoke_engine_subsystem`

Dynamic invocation resolves public names from the live `unreal` module. Arguments support explicit JSON wire forms such as:

    {"$asset": "/Game/Props/SM_Box.SM_Box"}
    {"$class": "/Script/Engine.PointLight"}
    {"$name": "MyName"}
    {"$vector": [0, 0, 100]}
    {"$rotator": {"pitch": 0, "yaw": 90, "roll": 0}}
    {"$enum": "DataLayerRuntimeState.ACTIVATED"}

This makes newly reflected APIs usable immediately, while dedicated wrappers can be added later for better schemas and ergonomics.

## 4. Dependency updates

`.github/dependabot.yml` monitors GitHub Actions and the pinned external MCP Python SDK.

The MCP SDK is pinned exactly in `MCP/requirements.txt` so dependency changes are reproducible and tested rather than silently changing on installation.

`.github/workflows/dependabot-automerge.yml` only squash-merges Dependabot changes when:

1. the normal UnrealMCP hosted CI succeeded;
2. the PR is actually authored by Dependabot;
3. the update can be proven from its version transition to stay on the same major version.

Major dependency updates remain manual.

## 5. What is deliberately not automated

UnrealMCP does **not** generate arbitrary C++/Python source rewrites from documentation prose and merge them blindly.

Documentation is a signal that something changed. Actual compatibility is established from:

1. official docs/version detection;
2. the live reflected API;
3. a real C++ plugin build;
4. direct Unreal API smoke tests;
5. native MCP TCP smoke tests;
6. source-aware API-diff checks.

If a future Unreal version removes or changes something referenced by UnrealMCP, the automated PR stays open with compatibility evidence instead of guessing at a migration.

## Self-hosted runner checklist

For unattended version validation:

1. Install the Unreal versions you want the repository to validate.
2. Register a GitHub self-hosted Windows x64 runner.
3. Add the custom runner label `unreal`.
4. Ensure the runner account can launch Unreal and RunUAT.
5. Optionally set machine environment variable `UNREAL_ENGINE_ROOT` for a nonstandard/source-build path.
6. Set repository Actions variable `UNREAL_MCP_AUTOVALIDATE=true`.

After that, new Epic documentation versions can flow from detection -> PR -> real engine build/smoke/API diff -> safe merge automatically.
