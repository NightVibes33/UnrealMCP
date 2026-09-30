"""Level Sequence inspection and editor integration for UE 5.8."""

from __future__ import annotations
from utils import run_unreal_json

def register_all(mcp):
    @mcp.tool()
    def list_level_sequences(path: str = "/Game", limit: int = 200) -> list[dict]:
        """List LevelSequence assets under a Content Browser path."""
        return run_unreal_json(
            """
            registry = unreal.AssetRegistryHelpers.get_asset_registry()
            assets = registry.get_assets_by_path(unreal.Name(args["path"]), recursive=True)
            out = []
            for data in assets:
                class_path = str(getattr(data, "asset_class_path", getattr(data, "asset_class", "")))
                if "LevelSequence" not in class_path:
                    continue
                out.append({
                    "name": str(data.asset_name),
                    "package": str(data.package_name),
                    "object_path": str(data.get_soft_object_path()),
                    "class": class_path,
                })
                if len(out) >= int(args["limit"]):
                    break
            result = out
            """,
            {"path": path, "limit": limit},
        )

    @mcp.tool()
    def get_level_sequence_info(asset_path: str) -> dict:
        """Inspect a LevelSequence's playback range, display rate and bindings."""
        return run_unreal_json(
            """
            sequence = unreal.load_asset(args["asset_path"])
            if sequence is None or not isinstance(sequence, unreal.LevelSequence):
                raise RuntimeError(f'Not a LevelSequence: {args["asset_path"]}')
            movie_scene = sequence.get_movie_scene()
            bindings = []
            try:
                for binding in sequence.get_bindings():
                    bindings.append({
                        "name": str(binding.get_name()),
                        "id": str(binding.get_id()),
                    })
            except Exception:
                pass
            result = {
                "path": sequence.get_path_name(),
                "display_rate": str(sequence.get_display_rate()) if hasattr(sequence, "get_display_rate") else None,
                "tick_resolution": str(sequence.get_tick_resolution()) if hasattr(sequence, "get_tick_resolution") else None,
                "playback_start": sequence.get_playback_start() if hasattr(sequence, "get_playback_start") else None,
                "playback_end": sequence.get_playback_end() if hasattr(sequence, "get_playback_end") else None,
                "binding_count": len(bindings),
                "bindings": bindings,
                "movie_scene": movie_scene.get_path_name() if movie_scene else None,
            }
            """,
            {"asset_path": asset_path},
        )

    @mcp.tool()
    def create_level_sequence(package_path: str, name: str, open_editor: bool = False) -> dict:
        """Create a LevelSequence asset with LevelSequenceFactoryNew."""
        return run_unreal_json(
            """
            tools = unreal.AssetToolsHelpers.get_asset_tools()
            factory = unreal.LevelSequenceFactoryNew()
            sequence = tools.create_asset(args["name"], args["package_path"], unreal.LevelSequence, factory)
            if sequence is None:
                raise RuntimeError("Failed to create LevelSequence")
            unreal.get_editor_subsystem(unreal.EditorAssetSubsystem).save_loaded_asset(sequence, False)
            opened = False
            if bool(args["open_editor"]):
                opened = bool(unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).open_editor_for_assets([sequence]))
            result = {"path": sequence.get_path_name(), "opened": opened}
            """,
            {"package_path": package_path, "name": name, "open_editor": open_editor},
        )

    @mcp.tool()
    def open_level_sequence(asset_path: str) -> dict:
        """Open a LevelSequence in its asset editor."""
        return run_unreal_json(
            """
            sequence = unreal.load_asset(args["asset_path"])
            if sequence is None or not isinstance(sequence, unreal.LevelSequence):
                raise RuntimeError(f'Not a LevelSequence: {args["asset_path"]}')
            ok = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).open_editor_for_assets([sequence])
            result = {"path": sequence.get_path_name(), "opened": bool(ok)}
            """,
            {"asset_path": asset_path},
        )

    @mcp.tool()
    def get_level_sequence_editor_capabilities() -> dict:
        """Describe LevelSequenceEditorSubsystem availability in the running engine."""
        return run_unreal_json(
            """
            cls = getattr(unreal, "LevelSequenceEditorSubsystem", None)
            result = {
                "available": cls is not None,
                "methods": [name for name in dir(cls) if not name.startswith("_")] if cls else [],
            }
            """
        )
