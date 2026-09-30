"""Niagara and PCG discovery helpers using the live UE 5.8 Python API."""

from __future__ import annotations
from utils import run_unreal_json

def register_all(mcp):
    @mcp.tool()
    def list_niagara_systems(path: str = "/Game", limit: int = 200) -> list[dict]:
        """List NiagaraSystem assets when the Niagara plugin is enabled."""
        return run_unreal_json(
            """
            if not hasattr(unreal, "NiagaraSystem"):
                raise RuntimeError("Niagara Python API is unavailable")
            registry = unreal.AssetRegistryHelpers.get_asset_registry()
            out = []
            for data in registry.get_assets_by_path(unreal.Name(args["path"]), recursive=True):
                cls = str(getattr(data, "asset_class_path", getattr(data, "asset_class", "")))
                if "NiagaraSystem" not in cls:
                    continue
                out.append({"name": str(data.asset_name), "package": str(data.package_name), "object_path": str(data.get_soft_object_path())})
                if len(out) >= int(args["limit"]):
                    break
            result = out
            """,
            {"path": path, "limit": limit},
        )

    @mcp.tool()
    def list_pcg_graphs(path: str = "/Game", limit: int = 200) -> list[dict]:
        """List PCGGraph assets when PCG is enabled."""
        return run_unreal_json(
            """
            if not hasattr(unreal, "PCGGraph"):
                raise RuntimeError("PCG Python API is unavailable; enable PCG/PCG Python Interop as needed")
            registry = unreal.AssetRegistryHelpers.get_asset_registry()
            out = []
            for data in registry.get_assets_by_path(unreal.Name(args["path"]), recursive=True):
                cls = str(getattr(data, "asset_class_path", getattr(data, "asset_class", "")))
                if "PCGGraph" not in cls:
                    continue
                out.append({"name": str(data.asset_name), "package": str(data.package_name), "object_path": str(data.get_soft_object_path())})
                if len(out) >= int(args["limit"]):
                    break
            result = out
            """,
            {"path": path, "limit": limit},
        )

    @mcp.tool()
    def list_pcg_components() -> list[dict]:
        """List PCG components in the current editor world and expose available generation methods."""
        return run_unreal_json(
            """
            cls = getattr(unreal, "PCGComponent", None)
            if cls is None:
                raise RuntimeError("PCGComponent is unavailable")
            actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            out = []
            for actor in actors.get_all_level_actors():
                for component in actor.get_components_by_class(cls):
                    out.append({
                        "actor": actor.get_actor_label(),
                        "component": component.get_name(),
                        "path": component.get_path_name(),
                        "methods": [name for name in dir(component) if "generate" in name.lower() and not name.startswith("_")],
                    })
            result = out
            """
        )
