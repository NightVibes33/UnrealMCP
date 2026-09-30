# Self-updating UnrealMCP

UnrealMCP 1.2 has two update loops: one fully hosted by GitHub, and one that validates against a real Unreal installation.

## 1. Epic documentation watcher

.github/workflows/epic-docs-watch.yml runs every day and can also be started manually.

It monitors official Epic sources, normalizes their visible content, hashes it, and tracks the latest observed Unreal documentation version in compat/epic-docs.json.

When documentation changes:

1. The generated state/report is validated with the normal Python/MCP tests.
2. An automation/epic-docs-<version> branch is created or refreshed.
3. A pull request is opened.
4. Same-version documentation-state changes are automatically squash-merged.
5. A newly observed Unreal version is not treated as proven compatibility until a real Unreal Editor build validates it.

The watcher also updates its tracked release-notes URL when a new Unreal major/minor version appears.

## 2. Live Unreal compatibility validator

.github/workflows/unreal-engine-validation.yml runs on a Windows self-hosted runner labelled:

    self-hosted
    Windows
    X64
    unreal

The workflow:

- auto-detects the newest installed UE_* installation, or uses UNREAL_ENGINE_ROOT;
- compiles the actual UnrealMCP plugin with RunUAT BuildPlugin;
- creates a disposable Unreal project;
- launches UnrealEditor-Cmd.exe;
- snapshots the reflected unreal Python module;
- runs live editor/subsystem smoke tests;
- compares the new API snapshot with the prior version;
- checks whether removed/changed APIs are referenced by UnrealMCP;
- records compatibility evidence under compat/api and compat/reports;
- can automatically merge the docs-update PR only when the plugin build, runtime smoke test, and API-diff gate all pass.

### Automatic dispatch

Set this repository Actions variable once:

    UNREAL_MCP_AUTOVALIDATE=true

Then a newly detected Unreal version automatically dispatches the real-engine validation workflow on the update branch.

The runner still needs the new Unreal binaries installed. GitHub-hosted runners do not include Unreal Engine, and Epic does not provide a general public headless installer suitable for silently installing every future engine release.

## 3. Runtime forward compatibility

Even before a purpose-built wrapper is added, new reflected Unreal Python APIs can be used through:

- search_unreal_python_api
- describe_unreal_python_api
- invoke_unreal_api
- invoke_editor_subsystem
- invoke_engine_subsystem

Dynamic invocation only resolves public names under the live unreal module. Arguments use explicit JSON wire forms such as:

    {"$asset": "/Game/Props/SM_Box.SM_Box"}
    {"$class": "/Script/Engine.PointLight"}
    {"$name": "MyName"}
    {"$vector": [0, 0, 100]}
    {"$rotator": {"pitch": 0, "yaw": 90, "roll": 0}}
    {"$enum": "DataLayerRuntimeState.ACTIVATED"}

This lets new engine/plugin APIs become usable immediately through reflection instead of waiting for a hard-coded tool release.

## 4. Dependency updates

.github/dependabot.yml monitors GitHub Actions and the external MCP Python SDK.

The MCP SDK is intentionally pinned exactly in MCP/requirements.txt. Dependabot can therefore produce deterministic minor/patch upgrade PRs instead of silently changing the installed SDK.

.github/workflows/dependabot-automerge.yml merges Dependabot minor/patch updates only after the normal UnrealMCP checks workflow succeeds.

Major dependency upgrades remain manual because they can contain breaking API changes.

## Safety model

UnrealMCP does not generate and merge arbitrary source-code rewrites from documentation text. Documentation is evidence, not an executable specification.

Automatic source compatibility is based on:

1. the live reflected API;
2. an actual Unreal plugin compile;
3. live smoke tests;
4. API-diff checks against source references.

If those checks detect a breaking change, the automated PR stays open with the generated report instead of modifying implementation code blindly.
