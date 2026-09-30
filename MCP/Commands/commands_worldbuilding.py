"""World Partition and Data Layer tools aligned with UE 5.8 APIs."""

from __future__ import annotations
from utils import run_unreal_json

def register_all(mcp):
    @mcp.tool()
    def get_world_partition_info() -> dict:
        """Inspect World Partition availability, world bounds and actor descriptor count."""
        return run_unreal_json(
            """
            editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
            world = editor.get_editor_world()
            lib = getattr(unreal, "WorldPartitionBlueprintLibrary", None)
            if world is None:
                raise RuntimeError("No editor world")
            manager = world.get_data_layer_manager() if hasattr(world, "get_data_layer_manager") else None
            out = {
                "world": world.get_path_name(),
                "has_world_partition_library": lib is not None,
                "has_data_layer_manager": manager is not None,
            }
            if lib:
                try:
                    bounds = lib.get_editor_world_bounds()
                    out["editor_bounds"] = {
                        "min": [bounds.min.x, bounds.min.y, bounds.min.z],
                        "max": [bounds.max.x, bounds.max.y, bounds.max.z],
                    }
                except Exception:
                    pass
                try:
                    descs = lib.get_actor_descs()
                    out["actor_descriptor_count"] = len(descs or [])
                except Exception:
                    pass
            result = out
            """
        )

    @mcp.tool()
    def list_data_layers() -> list[dict]:
        """List Data Layer instances using DataLayerManager, replacing the deprecated DataLayerSubsystem path."""
        return run_unreal_json(
            """
            editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
            world = editor.get_editor_world()
            if world is None or not hasattr(world, "get_data_layer_manager"):
                raise RuntimeError("DataLayerManager is unavailable in the current editor world")
            manager = world.get_data_layer_manager()
            if manager is None:
                result = []
            else:
                out = []
                for layer in manager.get_data_layer_instances():
                    item = {
                        "name": str(layer.get_name()),
                        "full_name": str(layer.get_data_layer_full_name()) if hasattr(layer, "get_data_layer_full_name") else str(layer.get_name()),
                        "short_name": str(layer.get_data_layer_short_name()) if hasattr(layer, "get_data_layer_short_name") else str(layer.get_name()),
                    }
                    try:
                        item["runtime_state"] = str(manager.get_data_layer_instance_runtime_state(layer))
                        item["effective_runtime_state"] = str(manager.get_data_layer_instance_effective_runtime_state(layer))
                    except Exception:
                        pass
                    out.append(item)
                result = out
            """
        )

    @mcp.tool()
    def set_data_layer_runtime_state(name: str, state: str, recursive: bool = False) -> dict:
        """Set a Data Layer runtime state through UE 5.8 DataLayerManager (UNLOADED, LOADED, ACTIVATED)."""
        return run_unreal_json(
            """
            editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
            world = editor.get_editor_world()
            if world is None or not hasattr(world, "get_data_layer_manager"):
                raise RuntimeError("DataLayerManager is unavailable")
            manager = world.get_data_layer_manager()
            layer = manager.get_data_layer_instance_from_name(unreal.Name(args["name"]))
            if layer is None:
                raise RuntimeError(f'Data Layer not found: {args["name"]}')
            enum_type = unreal.DataLayerRuntimeState
            state_name = args["state"].upper()
            if not hasattr(enum_type, state_name):
                raise RuntimeError(f'Unknown DataLayerRuntimeState: {state_name}')
            ok = manager.set_data_layer_instance_runtime_state(
                layer, getattr(enum_type, state_name), bool(args["recursive"])
            )
            result = {
                "name": args["name"],
                "state": state_name,
                "recursive": bool(args["recursive"]),
                "changed": bool(ok),
            }
            """,
            {"name": name, "state": state, "recursive": recursive},
        )

    @mcp.tool()
    def get_editor_data_layers() -> list[dict]:
        """Inspect editor Data Layers when DataLayerEditorSubsystem is available."""
        return run_unreal_json(
            """
            cls = getattr(unreal, "DataLayerEditorSubsystem", None)
            if cls is None:
                raise RuntimeError("DataLayerEditorSubsystem is unavailable")
            subsystem = unreal.get_editor_subsystem(cls)
            getter = getattr(subsystem, "get_all_data_layers", None) or getattr(subsystem, "get_data_layer_instances", None)
            if getter is None:
                raise RuntimeError("No Data Layer enumeration API is exposed by this engine build")
            out = []
            for layer in getter():
                out.append({
                    "name": str(layer.get_name()),
                    "full_name": str(layer.get_data_layer_full_name()) if hasattr(layer, "get_data_layer_full_name") else str(layer.get_name()),
                    "short_name": str(layer.get_data_layer_short_name()) if hasattr(layer, "get_data_layer_short_name") else str(layer.get_name()),
                })
            result = out
            """
        )

    @mcp.tool()
    def set_editor_data_layer_visibility(name: str, visible: bool) -> dict:
        """Show or hide an editor Data Layer using DataLayerEditorSubsystem."""
        return run_unreal_json(
            """
            cls = getattr(unreal, "DataLayerEditorSubsystem", None)
            if cls is None:
                raise RuntimeError("DataLayerEditorSubsystem is unavailable")
            subsystem = unreal.get_editor_subsystem(cls)
            layer = None
            for candidate in subsystem.get_data_layer_instances():
                short_name = str(candidate.get_data_layer_short_name()) if hasattr(candidate, "get_data_layer_short_name") else str(candidate.get_name())
                if short_name == args["name"] or str(candidate.get_name()) == args["name"]:
                    layer = candidate
                    break
            if layer is None:
                raise RuntimeError(f'Editor Data Layer not found: {args["name"]}')
            subsystem.set_data_layer_visibility(layer, bool(args["visible"]))
            result = {"name": args["name"], "visible": bool(args["visible"])}
            """,
            {"name": name, "visible": visible},
        )
