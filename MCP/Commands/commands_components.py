"""Actor component inspection and reflected property editing."""

from __future__ import annotations
from typing import Any
from utils import run_unreal_json

def register_all(mcp):
    @mcp.tool()
    def list_actor_components(actor_label: str) -> list[dict]:
        """List all ActorComponents on an actor."""
        return run_unreal_json(
            """
            actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            actor = next((a for a in actors.get_all_level_actors()
                          if a.get_actor_label() == args["actor_label"] or a.get_name() == args["actor_label"]), None)
            if actor is None:
                raise RuntimeError(f'Actor not found: {args["actor_label"]}')
            out = []
            for component in actor.get_components_by_class(unreal.ActorComponent):
                item = {
                    "name": component.get_name(),
                    "class": component.get_class().get_name(),
                    "path": component.get_path_name(),
                    "active": bool(component.is_active()),
                }
                if isinstance(component, unreal.SceneComponent):
                    loc = component.get_world_location()
                    rot = component.get_world_rotation()
                    scale = component.get_world_scale()
                    item["world_location"] = [loc.x, loc.y, loc.z]
                    item["world_rotation"] = [rot.pitch, rot.yaw, rot.roll]
                    item["world_scale"] = [scale.x, scale.y, scale.z]
                out.append(item)
            result = out
            """,
            {"actor_label": actor_label},
        )

    @mcp.tool()
    def set_component_property(actor_label: str, component_name: str, property_name: str, value: Any) -> dict:
        """Set a reflected editor property on an actor component."""
        return run_unreal_json(
            """
            actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            actor = next((a for a in actors.get_all_level_actors()
                          if a.get_actor_label() == args["actor_label"] or a.get_name() == args["actor_label"]), None)
            if actor is None:
                raise RuntimeError(f'Actor not found: {args["actor_label"]}')
            component = next((c for c in actor.get_components_by_class(unreal.ActorComponent)
                              if c.get_name() == args["component_name"]), None)
            if component is None:
                raise RuntimeError(f'Component not found: {args["component_name"]}')
            with unreal.ScopedEditorTransaction("UnrealMCP Set Component Property"):
                component.modify()
                component.set_editor_property(args["property_name"], args["value"])
            result = {
                "actor": actor.get_actor_label(),
                "component": component.get_name(),
                "property": args["property_name"],
                "value": str(component.get_editor_property(args["property_name"])),
            }
            """,
            {"actor_label": actor_label, "component_name": component_name, "property_name": property_name, "value": value},
        )

    @mcp.tool()
    def set_scene_component_transform(
        actor_label: str,
        component_name: str,
        location: list[float] | None = None,
        rotation: list[float] | None = None,
        scale: list[float] | None = None,
    ) -> dict:
        """Set relative transform channels on a SceneComponent."""
        return run_unreal_json(
            """
            actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            actor = next((a for a in actors.get_all_level_actors()
                          if a.get_actor_label() == args["actor_label"] or a.get_name() == args["actor_label"]), None)
            if actor is None:
                raise RuntimeError(f'Actor not found: {args["actor_label"]}')
            component = next((c for c in actor.get_components_by_class(unreal.SceneComponent)
                              if c.get_name() == args["component_name"]), None)
            if component is None:
                raise RuntimeError(f'SceneComponent not found: {args["component_name"]}')
            with unreal.ScopedEditorTransaction("UnrealMCP Set Component Transform"):
                component.modify()
                if args.get("location") is not None:
                    v = args["location"]
                    component.set_relative_location(unreal.Vector(float(v[0]), float(v[1]), float(v[2])), False, False)
                if args.get("rotation") is not None:
                    r = args["rotation"]
                    component.set_relative_rotation(unreal.Rotator(pitch=float(r[0]), yaw=float(r[1]), roll=float(r[2])), False, False)
                if args.get("scale") is not None:
                    s = args["scale"]
                    component.set_relative_scale3d(unreal.Vector(float(s[0]), float(s[1]), float(s[2])))
            loc = component.get_relative_location()
            rot = component.get_relative_rotation()
            scl = component.get_relative_scale3d()
            result = {
                "actor": actor.get_actor_label(),
                "component": component.get_name(),
                "relative_location": [loc.x, loc.y, loc.z],
                "relative_rotation": [rot.pitch, rot.yaw, rot.roll],
                "relative_scale": [scl.x, scl.y, scl.z],
            }
            """,
            {"actor_label": actor_label, "component_name": component_name, "location": location, "rotation": rotation, "scale": scale},
        )
