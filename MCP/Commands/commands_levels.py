"""Level/map management aligned with UE 5.8 LevelEditorSubsystem."""

from __future__ import annotations
from utils import run_unreal_json

def register_all(mcp):
    @mcp.tool()
    def get_current_level() -> dict:
        """Return current editor world, level and streaming information."""
        return run_unreal_json(
            """
            editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
            level_editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
            world = editor.get_editor_world()
            level = level_editor.get_current_level()
            streaming = []
            if world:
                for item in world.get_streaming_levels():
                    if item:
                        streaming.append({
                            "name": item.get_name(),
                            "loaded": bool(item.is_level_loaded()),
                            "visible": bool(item.is_level_visible()),
                        })
            result = {
                "world_name": world.get_name() if world else None,
                "world_path": world.get_path_name() if world else None,
                "level_name": level.get_name() if level else None,
                "level_path": level.get_path_name() if level else None,
                "streaming_levels": streaming,
            }
            """
        )

    @mcp.tool()
    def list_levels(path: str = "/Game", limit: int = 200) -> list[dict]:
        """List World assets under a Content Browser path."""
        return run_unreal_json(
            """
            registry = unreal.AssetRegistryHelpers.get_asset_registry()
            assets = registry.get_assets_by_path(unreal.Name(args["path"]), recursive=True)
            out = []
            for data in assets:
                class_path = str(getattr(data, "asset_class_path", getattr(data, "asset_class", "")))
                if "World" not in class_path:
                    continue
                out.append({
                    "name": str(data.asset_name),
                    "package": str(data.package_name),
                    "object_path": str(data.get_soft_object_path()),
                })
                if len(out) >= int(args["limit"]):
                    break
            result = out
            """,
            {"path": path, "limit": limit},
        )

    @mcp.tool()
    def load_level(level_path: str) -> dict:
        """Close the current map without saving and load another level."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
            ok = subsystem.load_level(args["level_path"])
            result = {"level": args["level_path"], "loaded": bool(ok)}
            """,
            {"level_path": level_path},
            timeout=180,
        )

    @mcp.tool()
    def save_current_level() -> dict:
        """Save the active level."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
            result = {"saved": bool(subsystem.save_current_level())}
            """
        )

    @mcp.tool()
    def save_all_dirty_levels() -> dict:
        """Save all dirty levels loaded in the World Editor."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
            result = {"saved": bool(subsystem.save_all_dirty_levels())}
            """
        )

    @mcp.tool()
    def create_level(level_path: str, is_partitioned_world: bool = False) -> dict:
        """Create a blank map; UE 5.8 supports creating it as a World Partition map."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
            ok = subsystem.new_level(args["level_path"], bool(args["is_partitioned_world"]))
            result = {
                "level": args["level_path"],
                "created": bool(ok),
                "is_partitioned_world": bool(args["is_partitioned_world"]),
            }
            """,
            {"level_path": level_path, "is_partitioned_world": is_partitioned_world},
            timeout=180,
        )

    @mcp.tool()
    def create_level_from_template(level_path: str, template_level_path: str) -> dict:
        """Create a level from an existing map template."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
            ok = subsystem.new_level_from_template(args["level_path"], args["template_level_path"])
            result = {
                "level": args["level_path"],
                "template": args["template_level_path"],
                "created": bool(ok),
            }
            """,
            {"level_path": level_path, "template_level_path": template_level_path},
            timeout=180,
        )

    @mcp.tool()
    def set_current_level(level_name: str) -> dict:
        """Set the current sublevel by name."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
            ok = subsystem.set_current_level_by_name(unreal.Name(args["level_name"]))
            result = {"level_name": args["level_name"], "selected": bool(ok)}
            """,
            {"level_name": level_name},
        )
