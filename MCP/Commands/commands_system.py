"""Project/system introspection and editor-wide utility tools."""

from __future__ import annotations
from utils import run_unreal_json

def register_all(mcp):
    @mcp.tool()
    def unreal_status() -> dict:
        """Return engine, Python, project, world and dirty-package information."""
        return run_unreal_json(
            """
            import sys
            editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
            world = editor.get_editor_world()
            dirty_content = unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()
            dirty_maps = unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
            result = {
                "engine_version": unreal.SystemLibrary.get_engine_version(),
                "python_version": sys.version,
                "project_dir": unreal.Paths.project_dir(),
                "project_content_dir": unreal.Paths.project_content_dir(),
                "project_file": unreal.Paths.get_project_file_path(),
                "world": world.get_path_name() if world else None,
                "is_game_world": bool(world and world.is_game_world()),
                "dirty_content_packages": [str(x) for x in dirty_content],
                "dirty_map_packages": [str(x) for x in dirty_maps],
            }
            """
        )

    @mcp.tool()
    def save_all_dirty_assets() -> dict:
        """Save dirty map and content packages."""
        return run_unreal_json(
            """
            ok = unreal.EditorLoadingAndSavingUtils.save_dirty_packages(
                save_map_packages=True,
                save_content_packages=True,
            )
            result = {"saved": bool(ok)}
            """
        )

    @mcp.tool()
    def get_selected_assets() -> list[dict]:
        """Return assets currently selected in the Content Browser."""
        return run_unreal_json(
            """
            selected = unreal.EditorUtilityLibrary.get_selected_assets()
            result = [
                {"name": a.get_name(), "class": a.get_class().get_name(), "path": a.get_path_name()}
                for a in selected
            ]
            """
        )

    @mcp.tool()
    def get_selected_actors() -> list[dict]:
        """Return actors currently selected in the level editor."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            result = [{
                "label": a.get_actor_label(),
                "name": a.get_name(),
                "class": a.get_class().get_name(),
                "path": a.get_path_name(),
            } for a in subsystem.get_selected_level_actors()]
            """
        )

    @mcp.tool()
    def execute_console_command(command: str) -> dict:
        """Execute an Unreal console command in the active editor world."""
        return run_unreal_json(
            """
            editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
            world = editor.get_editor_world()
            unreal.SystemLibrary.execute_console_command(world, args["command"])
            result = {"executed": args["command"]}
            """,
            {"command": command},
        )
