"""Runtime Unreal API discovery for UE 5.8 and forward-compatible engine updates."""

from __future__ import annotations
from utils import run_unreal_json

def register_all(mcp):
    @mcp.tool()
    def get_unreal_capabilities() -> dict:
        """Inspect the live Unreal Python environment, plugins and key editor API availability."""
        return run_unreal_json(
            """
            import sys
            version = unreal.SystemLibrary.get_engine_version()
            plugin_names = []
            plugin_lib = getattr(unreal, "PluginBlueprintLibrary", None)
            if plugin_lib and hasattr(plugin_lib, "get_enabled_plugin_names"):
                plugin_names = [str(x) for x in plugin_lib.get_enabled_plugin_names()]

            symbols = [
                "EditorActorSubsystem",
                "EditorAssetSubsystem",
                "AssetEditorSubsystem",
                "LevelEditorSubsystem",
                "UnrealEditorSubsystem",
                "StaticMeshEditorSubsystem",
                "SkeletalMeshEditorSubsystem",
                "SubobjectDataSubsystem",
                "LevelSequenceEditorSubsystem",
                "DataLayerEditorSubsystem",
                "DataLayerManager",
                "WorldPartitionBlueprintLibrary",
                "EditorValidatorSubsystem",
                "PCGEngineSubsystem",
                "PCGComponent",
                "NiagaraSystem",
                "NiagaraComponent",
                "RemoteControlPreset",
                "ScopedEditorTransaction",
            ]
            result = {
                "engine_version": version,
                "python_version": sys.version,
                "python_version_info": list(sys.version_info[:3]),
                "project_file": unreal.Paths.get_project_file_path(),
                "enabled_plugins": plugin_names,
                "api": {name: hasattr(unreal, name) for name in symbols},
            }
            """
        )

    @mcp.tool()
    def search_unreal_python_api(query: str, limit: int = 100) -> list[dict]:
        """Search names exposed by the live `unreal` Python module instead of relying on stale docs."""
        return run_unreal_json(
            """
            import inspect
            q = args["query"].lower().strip()
            out = []
            for name in sorted(dir(unreal)):
                if q and q not in name.lower():
                    continue
                try:
                    obj = getattr(unreal, name)
                    doc = inspect.getdoc(obj) or ""
                    first = doc.splitlines()[0] if doc else ""
                    out.append({
                        "name": name,
                        "python_type": type(obj).__name__,
                        "callable": callable(obj),
                        "summary": first[:500],
                    })
                except Exception as exc:
                    out.append({"name": name, "error": str(exc)})
                if len(out) >= int(args["limit"]):
                    break
            result = out
            """,
            {"query": query, "limit": limit},
        )

    @mcp.tool()
    def describe_unreal_python_api(symbol: str, member_filter: str = "", limit: int = 250) -> dict:
        """Describe a live Unreal Python class/function and its public members."""
        return run_unreal_json(
            """
            import inspect
            parts = [p for p in args["symbol"].split(".") if p]
            obj = unreal
            for part in parts:
                if not hasattr(obj, part):
                    raise RuntimeError(f'Unreal Python symbol not found: {args["symbol"]}')
                obj = getattr(obj, part)

            members = []
            mf = args["member_filter"].lower().strip()
            for name in sorted(dir(obj)):
                if name.startswith("_"):
                    continue
                if mf and mf not in name.lower():
                    continue
                try:
                    value = getattr(obj, name)
                    entry = {"name": name, "callable": callable(value), "python_type": type(value).__name__}
                    if callable(value):
                        try:
                            entry["signature"] = str(inspect.signature(value))
                        except Exception:
                            pass
                    doc = inspect.getdoc(value) or ""
                    if doc:
                        entry["summary"] = doc.splitlines()[0][:500]
                    members.append(entry)
                except Exception as exc:
                    members.append({"name": name, "error": str(exc)})
                if len(members) >= int(args["limit"]):
                    break

            result = {
                "symbol": args["symbol"],
                "python_type": type(obj).__name__,
                "callable": callable(obj),
                "doc": (inspect.getdoc(obj) or "")[:12000],
                "members": members,
            }
            """,
            {"symbol": symbol, "member_filter": member_filter, "limit": limit},
        )

    @mcp.tool()
    def check_unreal_api_paths(paths: list[str]) -> dict:
        """Check whether dotted Unreal Python API paths exist in the running engine."""
        return run_unreal_json(
            """
            out = {}
            for path in args["paths"]:
                obj = unreal
                ok = True
                for part in [p for p in path.split(".") if p]:
                    if not hasattr(obj, part):
                        ok = False
                        break
                    obj = getattr(obj, part)
                out[path] = ok
            result = out
            """,
            {"paths": paths},
        )

    @mcp.tool()
    def get_enabled_plugins(query: str = "") -> list[dict]:
        """List enabled Unreal plugins and their versions using PluginBlueprintLibrary."""
        return run_unreal_json(
            """
            lib = getattr(unreal, "PluginBlueprintLibrary", None)
            if lib is None or not hasattr(lib, "get_enabled_plugin_names"):
                raise RuntimeError("PluginBlueprintLibrary is not available in this engine build")
            q = args["query"].lower().strip()
            out = []
            for name in lib.get_enabled_plugin_names():
                name = str(name)
                if q and q not in name.lower():
                    continue
                item = {"name": name}
                for method, key in [
                    ("get_plugin_version_name", "version_name"),
                    ("get_plugin_version", "version"),
                    ("get_plugin_description", "description"),
                    ("get_plugin_base_dir", "base_dir"),
                    ("get_plugin_content_dir", "content_dir"),
                ]:
                    fn = getattr(lib, method, None)
                    if fn:
                        try:
                            item[key] = fn(name)
                        except Exception:
                            pass
                out.append(item)
            result = out
            """,
            {"query": query},
        )
