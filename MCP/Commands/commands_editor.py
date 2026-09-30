"""Editor, PIE, lighting and viewport controls using UE 5.8 subsystems."""

from __future__ import annotations
from utils import run_unreal_json

def register_all(mcp):
    @mcp.tool()
    def is_pie_running() -> bool:
        """Return whether Play-In-Editor is active."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
            result = bool(subsystem.is_in_play_in_editor())
            """
        )

    @mcp.tool()
    def start_pie(simulate: bool = False) -> dict:
        """Start Play-In-Editor or Simulate-In-Editor."""
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
    def get_viewport_camera(viewport_config_key: str = "None") -> dict:
        """Return primary level viewport camera information and configured viewport keys."""
        return run_unreal_json(
            """
            editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
            level_editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
            camera = editor.get_level_viewport_camera_info()
            location, rotation = camera if camera else (None, None)
            result = {
                "available": camera is not None,
                "location": [location.x, location.y, location.z] if location else None,
                "rotation": [rotation.pitch, rotation.yaw, rotation.roll] if rotation else None,
                "viewport_config_keys": [str(x) for x in level_editor.get_viewport_config_keys()],
                "game_view": bool(level_editor.editor_get_game_view(unreal.Name(args["viewport_config_key"]))),
            }
            """,
            {"viewport_config_key": viewport_config_key},
        )

    @mcp.tool()
    def set_viewport_camera(location: list[float], rotation: list[float]) -> dict:
        """Move the primary level viewport camera."""
        return run_unreal_json(
            """
            editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
            loc = args["location"]
            rot = args["rotation"]
            editor.set_level_viewport_camera_info(
                unreal.Vector(float(loc[0]), float(loc[1]), float(loc[2])),
                unreal.Rotator(pitch=float(rot[0]), yaw=float(rot[1]), roll=float(rot[2])),
            )
            result = {"location": loc, "rotation": rot}
            """,
            {"location": location, "rotation": rotation},
        )

    @mcp.tool()
    def set_viewport_game_view(enabled: bool, viewport_config_key: str = "None") -> dict:
        """Toggle Game View for a level viewport."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
            key = unreal.Name(args["viewport_config_key"])
            subsystem.editor_set_game_view(bool(args["enabled"]), key)
            result = {
                "viewport_config_key": args["viewport_config_key"],
                "game_view": bool(subsystem.editor_get_game_view(key)),
            }
            """,
            {"enabled": enabled, "viewport_config_key": viewport_config_key},
        )

    @mcp.tool()
    def pilot_viewport_actor(actor_label: str, viewport_config_key: str = "None") -> dict:
        """Pilot a level actor in a viewport."""
        return run_unreal_json(
            """
            actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            actor = next((a for a in actors.get_all_level_actors()
                          if a.get_actor_label() == args["actor_label"] or a.get_name() == args["actor_label"]), None)
            if actor is None:
                raise RuntimeError(f'Actor not found: {args["actor_label"]}')
            subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
            subsystem.pilot_level_actor(actor, unreal.Name(args["viewport_config_key"]))
            result = {"piloting": actor.get_actor_label(), "viewport_config_key": args["viewport_config_key"]}
            """,
            {"actor_label": actor_label, "viewport_config_key": viewport_config_key},
        )

    @mcp.tool()
    def eject_viewport_pilot(viewport_config_key: str = "None") -> dict:
        """Stop piloting an actor in the selected viewport."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
            subsystem.eject_pilot_level_actor(unreal.Name(args["viewport_config_key"]))
            result = {"ejected": True, "viewport_config_key": args["viewport_config_key"]}
            """,
            {"viewport_config_key": viewport_config_key},
        )

    @mcp.tool()
    def invalidate_viewports() -> dict:
        """Invalidate level editor viewports so they redraw."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
            subsystem.editor_invalidate_viewports()
            result = {"invalidated": True}
            """
        )

    @mcp.tool()
    def build_light_maps(quality: str = "QUALITY_PRODUCTION", with_reflection_captures: bool = False) -> dict:
        """Build light maps using LevelEditorSubsystem and a LightingBuildQuality enum value."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
            enum_type = unreal.LightingBuildQuality
            name = args["quality"].upper()
            if not hasattr(enum_type, name):
                available = [x for x in dir(enum_type) if x.startswith("QUALITY_")]
                raise RuntimeError(f'Unknown lighting quality {name}; available: {available}')
            ok = subsystem.build_light_maps(getattr(enum_type, name), bool(args["with_reflection_captures"]))
            result = {"built": bool(ok), "quality": name, "with_reflection_captures": bool(args["with_reflection_captures"])}
            """,
            {"quality": quality, "with_reflection_captures": with_reflection_captures},
            timeout=600,
        )
