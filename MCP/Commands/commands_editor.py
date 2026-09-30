"""Editor, PIE and viewport controls."""

from __future__ import annotations
from utils import run_unreal_json

def register_all(mcp):
    @mcp.tool()
    def is_pie_running() -> bool:
        """Return whether Play-In-Editor is currently active."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
            result = bool(subsystem.is_in_play_in_editor())
            """
        )

    @mcp.tool()
    def start_pie(simulate: bool = False) -> dict:
        """Start Play-In-Editor. Use simulate=True for Simulate-In-Editor."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
            if subsystem.is_in_play_in_editor():
                result = {"started": False, "reason": "PIE already running"}
            else:
                if bool(args["simulate"]):
                    subsystem.editor_play_simulate()
                else:
                    subsystem.editor_request_begin_play()
                result = {"started": True, "simulate": bool(args["simulate"])}
            """,
            {"simulate": simulate},
        )

    @mcp.tool()
    def stop_pie() -> dict:
        """Stop an active Play-In-Editor session."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
            was_running = bool(subsystem.is_in_play_in_editor())
            if was_running:
                subsystem.editor_request_end_play()
            result = {"stopped": was_running}
            """
        )

    @mcp.tool()
    def get_viewport_camera() -> dict:
        """Return the active level viewport camera transform."""
        return run_unreal_json(
            """
            editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
            camera = editor.get_level_viewport_camera_info()
            if not camera:
                result = {"available": False}
            else:
                location, rotation = camera
                result = {
                    "available": True,
                    "location": [location.x, location.y, location.z],
                    "rotation": [rotation.pitch, rotation.yaw, rotation.roll],
                }
            """
        )

    @mcp.tool()
    def set_viewport_camera(location: list[float], rotation: list[float]) -> dict:
        """Move the active level viewport camera."""
        return run_unreal_json(
            """
            editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
            loc = args["location"]
            rot = args["rotation"]
            editor.set_level_viewport_camera_info(
                unreal.Vector(float(loc[0]), float(loc[1]), float(loc[2])),
                unreal.Rotator(float(rot[0]), float(rot[1]), float(rot[2])),
            )
            result = {"location": loc, "rotation": rot}
            """,
            {"location": location, "rotation": rotation},
        )

    @mcp.tool()
    def focus_viewport_on_actor(actor_label: str) -> dict:
        """Select an actor and frame it in the active level viewport."""
        return run_unreal_json(
            """
            actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            actor = next((a for a in actors.get_all_level_actors()
                          if a.get_actor_label() == args["actor_label"] or a.get_name() == args["actor_label"]), None)
            if actor is None:
                raise RuntimeError(f'Actor not found: {args["actor_label"]}')
            actors.set_selected_level_actors([actor])
            level_editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
            level_editor.pilot_level_actor(actor)
            level_editor.eject_pilot_level_actor()
            result = {"focused": actor.get_actor_label()}
            """,
            {"actor_label": actor_label},
        )
