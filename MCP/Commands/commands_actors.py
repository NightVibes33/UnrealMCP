"""Rich actor inspection and editing tools."""

from __future__ import annotations
from typing import Any
from utils import run_unreal_json

def register_all(mcp):
    @mcp.tool()
    def list_actors(
        query: str = "",
        class_name: str | None = None,
        tag: str | None = None,
        limit: int = 500,
    ) -> list[dict]:
        """List actors in the current level with optional label/name/class/tag filters."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            q = args["query"].lower()
            cls = (args.get("class_name") or "").lower()
            tag = args.get("tag")
            out = []
            for actor in subsystem.get_all_level_actors():
                label = actor.get_actor_label()
                name = actor.get_name()
                actor_class = actor.get_class().get_name()
                tags = [str(x) for x in actor.tags]
                if q and q not in label.lower() and q not in name.lower():
                    continue
                if cls and cls not in actor_class.lower():
                    continue
                if tag and tag not in tags:
                    continue
                loc = actor.get_actor_location()
                rot = actor.get_actor_rotation()
                scale = actor.get_actor_scale3d()
                out.append({
                    "label": label, "name": name, "class": actor_class,
                    "location": [loc.x, loc.y, loc.z],
                    "rotation": [rot.pitch, rot.yaw, rot.roll],
                    "scale": [scale.x, scale.y, scale.z],
                    "tags": tags,
                })
                if len(out) >= int(args["limit"]):
                    break
            result = out
            """,
            {"query": query, "class_name": class_name, "tag": tag, "limit": limit},
        )

    @mcp.tool()
    def get_actor_details(actor_label: str) -> dict:
        """Inspect transform, tags, parent and components for one actor."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            actor = next((a for a in subsystem.get_all_level_actors()
                          if a.get_actor_label() == args["actor_label"] or a.get_name() == args["actor_label"]), None)
            if actor is None:
                raise RuntimeError(f'Actor not found: {args["actor_label"]}')
            loc, rot, scale = actor.get_actor_location(), actor.get_actor_rotation(), actor.get_actor_scale3d()
            parent = actor.get_attach_parent_actor()
            result = {
                "label": actor.get_actor_label(),
                "name": actor.get_name(),
                "class": actor.get_class().get_name(),
                "path": actor.get_path_name(),
                "location": [loc.x, loc.y, loc.z],
                "rotation": [rot.pitch, rot.yaw, rot.roll],
                "scale": [scale.x, scale.y, scale.z],
                "tags": [str(x) for x in actor.tags],
                "parent": parent.get_actor_label() if parent else None,
                "components": [{
                    "name": c.get_name(),
                    "class": c.get_class().get_name(),
                } for c in actor.get_components_by_class(unreal.ActorComponent)],
            }
            """,
            {"actor_label": actor_label},
        )

    @mcp.tool()
    def set_actor_transform(
        actor_label: str,
        location: list[float] | None = None,
        rotation: list[float] | None = None,
        scale: list[float] | None = None,
    ) -> dict:
        """Set one or more transform channels on an actor."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            actor = next((a for a in subsystem.get_all_level_actors()
                          if a.get_actor_label() == args["actor_label"] or a.get_name() == args["actor_label"]), None)
            if actor is None:
                raise RuntimeError(f'Actor not found: {args["actor_label"]}')
            if args.get("location") is not None:
                v = args["location"]
                actor.set_actor_location(unreal.Vector(float(v[0]), float(v[1]), float(v[2])), False, False)
            if args.get("rotation") is not None:
                r = args["rotation"]
                actor.set_actor_rotation(unreal.Rotator(float(r[0]), float(r[1]), float(r[2])), False)
            if args.get("scale") is not None:
                s = args["scale"]
                actor.set_actor_scale3d(unreal.Vector(float(s[0]), float(s[1]), float(s[2])))
            loc, rot, scl = actor.get_actor_location(), actor.get_actor_rotation(), actor.get_actor_scale3d()
            result = {
                "label": actor.get_actor_label(),
                "location": [loc.x, loc.y, loc.z],
                "rotation": [rot.pitch, rot.yaw, rot.roll],
                "scale": [scl.x, scl.y, scl.z],
            }
            """,
            {"actor_label": actor_label, "location": location, "rotation": rotation, "scale": scale},
        )

    @mcp.tool()
    def set_actor_tags(actor_label: str, tags: list[str]) -> dict:
        """Replace an actor's tag list."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            actor = next((a for a in subsystem.get_all_level_actors()
                          if a.get_actor_label() == args["actor_label"] or a.get_name() == args["actor_label"]), None)
            if actor is None:
                raise RuntimeError(f'Actor not found: {args["actor_label"]}')
            actor.tags = [unreal.Name(t) for t in args["tags"]]
            result = {"label": actor.get_actor_label(), "tags": [str(t) for t in actor.tags]}
            """,
            {"actor_label": actor_label, "tags": tags},
        )

    @mcp.tool()
    def set_actor_property(actor_label: str, property_name: str, value: Any) -> dict:
        """Set a reflected editor property on an actor. Intended for JSON-compatible scalar/list values."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            actor = next((a for a in subsystem.get_all_level_actors()
                          if a.get_actor_label() == args["actor_label"] or a.get_name() == args["actor_label"]), None)
            if actor is None:
                raise RuntimeError(f'Actor not found: {args["actor_label"]}')
            actor.set_editor_property(args["property_name"], args["value"])
            result = {
                "label": actor.get_actor_label(),
                "property": args["property_name"],
                "value": str(actor.get_editor_property(args["property_name"])),
            }
            """,
            {"actor_label": actor_label, "property_name": property_name, "value": value},
        )

    @mcp.tool()
    def duplicate_actor(actor_label: str, new_label: str | None = None) -> dict:
        """Duplicate an actor in the current level."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            actor = next((a for a in subsystem.get_all_level_actors()
                          if a.get_actor_label() == args["actor_label"] or a.get_name() == args["actor_label"]), None)
            if actor is None:
                raise RuntimeError(f'Actor not found: {args["actor_label"]}')
            duplicate = subsystem.duplicate_actor(actor)
            if duplicate is None:
                raise RuntimeError("Actor duplication failed")
            if args.get("new_label"):
                duplicate.set_actor_label(args["new_label"])
            result = {"label": duplicate.get_actor_label(), "name": duplicate.get_name(), "path": duplicate.get_path_name()}
            """,
            {"actor_label": actor_label, "new_label": new_label},
        )

    @mcp.tool()
    def select_actors(labels: list[str], clear_existing: bool = True) -> list[str]:
        """Select actors in the level editor."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            actors = subsystem.get_all_level_actors()
            wanted = set(args["labels"])
            matches = [a for a in actors if a.get_actor_label() in wanted or a.get_name() in wanted]
            if bool(args["clear_existing"]):
                subsystem.clear_actor_selection_set()
            subsystem.set_selected_level_actors(matches)
            result = [a.get_actor_label() for a in matches]
            """,
            {"labels": labels, "clear_existing": clear_existing},
        )
