"""Level/map management tools."""

from __future__ import annotations
from utils import run_unreal_json

def register_all(mcp):
    @mcp.tool()
    def get_current_level() -> dict:
        """Return current editor world and level information."""
        return run_unreal_json(
            """
            editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
            level_editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
            world = editor.get_editor_world()
            level = level_editor.get_current_level()
            result = {
                "world_name": world.get_name() if world else None,
                "world_path": world.get_path_name() if world else None,
                "level_name": level.get_name() if level else None,
                "level_path": level.get_path_name() if level else None,
            }
            """
        )

    @mcp.tool()
    def list_levels(path: str = "/Game", limit: int = 200) -> list[dict]:
        """List World assets available under a Content Browser path."""
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
        """Open a level/map in the Unreal Editor."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
            ok = subsystem.load_level(args["level_path"])
            result = {"level": args["level_path"], "loaded": bool(ok)}
            """,
            {"level_path": level_path},
            timeout=120,
        )

    @mcp.tool()
    def save_current_level() -> dict:
        """Save the active level."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
            ok = subsystem.save_current_level()
            result = {"saved": bool(ok)}
            """
        )

    @mcp.tool()
    def create_level(level_path: str) -> dict:
        """Create and open a new level at a /Game/... asset path."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
            ok = subsystem.new_level(args["level_path"])
            result = {"level": args["level_path"], "created": bool(ok)}
            """,
            {"level_path": level_path},
            timeout=120,
        )
