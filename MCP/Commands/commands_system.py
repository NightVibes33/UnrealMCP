"""Project/system introspection and editor-wide utility tools."""

from __future__ import annotations
from utils import run_unreal_json

def register_all(mcp):
    @mcp.tool()
    def unreal_status() -> dict:
        """Return engine, project, world and editor connection information."""
        return run_unreal_json(
            """
            editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
            world = editor.get_editor_world()
            result = {
                "engine_version": unreal.SystemLibrary.get_engine_version(),
                "project_dir": unreal.Paths.project_dir(),
                "project_content_dir": unreal.Paths.project_content_dir(),
                "project_file": unreal.Paths.get_project_file_path(),
                "world": world.get_path_name() if world else None,
                "is_game_world": bool(world and world.is_game_world()),
            }
            """
        )

    @mcp.tool()
    def save_all_dirty_assets() -> dict:
        """Save dirty content packages and the current map."""
        return run_unreal_json(
            """
            content_saved = unreal.EditorLoadingAndSavingUtils.save_dirty_packages(
                save_map_packages=True, save_content_packages=True
            )
            result = {"saved": bool(content_saved)}
            """
        )

    @mcp.tool()
    def get_selected_assets() -> list[dict]:
        """Return assets currently selected in the Content Browser."""
        return run_unreal_json(
            """
            selected = unreal.EditorUtilityLibrary.get_selected_assets()
            result = [{"name": a.get_name(), "class": a.get_class().get_name(), "path": a.get_path_name()} for a in selected]
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
