"""Rich actor inspection, spawning and editing through EditorActorSubsystem."""

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
        """List loaded actors in the current editor world."""
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
                loc, rot, scale = actor.get_actor_location(), actor.get_actor_rotation(), actor.get_actor_scale3d()
                out.append({
                    "label": label,
                    "name": name,
                    "class": actor_class,
                    "path": actor.get_path_name(),
                    "location": [loc.x, loc.y, loc.z],
                    "rotation": [rot.pitch, rot.yaw, rot.roll],
                    "scale": [scale.x, scale.y, scale.z],
                    "tags": tags,
                    "folder": str(actor.get_folder_path()) if hasattr(actor, "get_folder_path") else None,
                })
                if len(out) >= int(args["limit"]):
                    break
            result = out
            """,
            {"query": query, "class_name": class_name, "tag": tag, "limit": limit},
        )

    @mcp.tool()
    def get_actor_details(actor_label: str) -> dict:
        """Inspect transform, parent, tags, folder and components for one actor."""
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
                "folder": str(actor.get_folder_path()) if hasattr(actor, "get_folder_path") else None,
                "parent": parent.get_actor_label() if parent else None,
                "components": [{
                    "name": c.get_name(),
                    "class": c.get_class().get_name(),
                    "path": c.get_path_name(),
                } for c in actor.get_components_by_class(unreal.ActorComponent)],
            }
            """,
            {"actor_label": actor_label},
        )

    @mcp.tool()
    def spawn_actor_from_asset(
        asset_path: str,
        location: list[float],
        rotation: list[float] | None = None,
        label: str | None = None,
        transient: bool = False,
    ) -> dict:
        """Spawn an actor from a placeable asset or Blueprint."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            asset = unreal.load_asset(args["asset_path"])
            if asset is None:
                raise RuntimeError(f'Asset not found: {args["asset_path"]}')
            loc = args["location"]
            rot = args.get("rotation") or [0.0, 0.0, 0.0]
            with unreal.ScopedEditorTransaction("UnrealMCP Spawn Actor From Asset"):
                actor = subsystem.spawn_actor_from_object(
                    asset,
                    unreal.Vector(float(loc[0]), float(loc[1]), float(loc[2])),
                    unreal.Rotator(pitch=float(rot[0]), yaw=float(rot[1]), roll=float(rot[2])),
                    bool(args["transient"]),
                )
                if actor is None:
                    raise RuntimeError("Actor spawn failed")
                if args.get("label"):
                    actor.set_actor_label(args["label"])
            result = {"label": actor.get_actor_label(), "name": actor.get_name(), "class": actor.get_class().get_name(), "path": actor.get_path_name()}
            """,
            {"asset_path": asset_path, "location": location, "rotation": rotation, "label": label, "transient": transient},
        )

    @mcp.tool()
    def spawn_actor_from_class(
        class_path: str,
        location: list[float],
        rotation: list[float] | None = None,
        label: str | None = None,
        transient: bool = False,
    ) -> dict:
        """Spawn an actor from a UClass path such as /Script/Engine.PointLight."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            cls = unreal.load_class(None, args["class_path"])
            if cls is None:
                raise RuntimeError(f'Class not found: {args["class_path"]}')
            loc = args["location"]
            rot = args.get("rotation") or [0.0, 0.0, 0.0]
            with unreal.ScopedEditorTransaction("UnrealMCP Spawn Actor From Class"):
                actor = subsystem.spawn_actor_from_class(
                    cls,
                    unreal.Vector(float(loc[0]), float(loc[1]), float(loc[2])),
                    unreal.Rotator(pitch=float(rot[0]), yaw=float(rot[1]), roll=float(rot[2])),
                    bool(args["transient"]),
                )
                if actor is None:
                    raise RuntimeError("Actor spawn failed")
                if args.get("label"):
                    actor.set_actor_label(args["label"])
            result = {"label": actor.get_actor_label(), "name": actor.get_name(), "class": actor.get_class().get_name(), "path": actor.get_path_name()}
            """,
            {"class_path": class_path, "location": location, "rotation": rotation, "label": label, "transient": transient},
        )

    @mcp.tool()
    def set_actor_transform(
        actor_label: str,
        location: list[float] | None = None,
        rotation: list[float] | None = None,
        scale: list[float] | None = None,
    ) -> dict:
        """Set one or more transform channels with an editor undo transaction."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            actor = next((a for a in subsystem.get_all_level_actors()
                          if a.get_actor_label() == args["actor_label"] or a.get_name() == args["actor_label"]), None)
            if actor is None:
                raise RuntimeError(f'Actor not found: {args["actor_label"]}')
            with unreal.ScopedEditorTransaction("UnrealMCP Set Actor Transform"):
                actor.modify()
                if args.get("location") is not None:
                    v = args["location"]
                    actor.set_actor_location(unreal.Vector(float(v[0]), float(v[1]), float(v[2])), False, False)
                if args.get("rotation") is not None:
                    r = args["rotation"]
                    actor.set_actor_rotation(unreal.Rotator(pitch=float(r[0]), yaw=float(r[1]), roll=float(r[2])), False)
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
        """Replace an actor's tags with undo support."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            actor = next((a for a in subsystem.get_all_level_actors()
                          if a.get_actor_label() == args["actor_label"] or a.get_name() == args["actor_label"]), None)
            if actor is None:
                raise RuntimeError(f'Actor not found: {args["actor_label"]}')
            with unreal.ScopedEditorTransaction("UnrealMCP Set Actor Tags"):
                actor.modify()
                actor.set_editor_property("tags", [unreal.Name(t) for t in args["tags"]])
            result = {"label": actor.get_actor_label(), "tags": [str(t) for t in actor.tags]}
            """,
            {"actor_label": actor_label, "tags": tags},
        )

    @mcp.tool()
    def set_actor_folder(actor_label: str, folder_path: str) -> dict:
        """Move an actor into a World Outliner folder."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            actor = next((a for a in subsystem.get_all_level_actors()
                          if a.get_actor_label() == args["actor_label"] or a.get_name() == args["actor_label"]), None)
            if actor is None:
                raise RuntimeError(f'Actor not found: {args["actor_label"]}')
            with unreal.ScopedEditorTransaction("UnrealMCP Set Actor Folder"):
                actor.set_folder_path(unreal.Name(args["folder_path"]))
            result = {"label": actor.get_actor_label(), "folder": str(actor.get_folder_path())}
            """,
            {"actor_label": actor_label, "folder_path": folder_path},
        )

    @mcp.tool()
    def set_actor_property(actor_label: str, property_name: str, value: Any) -> dict:
        """Set a JSON-compatible reflected editor property on an actor."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            actor = next((a for a in subsystem.get_all_level_actors()
                          if a.get_actor_label() == args["actor_label"] or a.get_name() == args["actor_label"]), None)
            if actor is None:
                raise RuntimeError(f'Actor not found: {args["actor_label"]}')
            with unreal.ScopedEditorTransaction("UnrealMCP Set Actor Property"):
                actor.modify()
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
    def duplicate_actor(actor_label: str, new_label: str | None = None, offset: list[float] | None = None) -> dict:
        """Duplicate an actor using EditorActorSubsystem."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            actor = next((a for a in subsystem.get_all_level_actors()
                          if a.get_actor_label() == args["actor_label"] or a.get_name() == args["actor_label"]), None)
            if actor is None:
                raise RuntimeError(f'Actor not found: {args["actor_label"]}')
            o = args.get("offset") or [0.0, 0.0, 0.0]
            with unreal.ScopedEditorTransaction("UnrealMCP Duplicate Actor"):
                duplicate = subsystem.duplicate_actor(actor, None, unreal.Vector(float(o[0]), float(o[1]), float(o[2])))
                if duplicate is None:
                    raise RuntimeError("Actor duplication failed")
                if args.get("new_label"):
                    duplicate.set_actor_label(args["new_label"])
            result = {"label": duplicate.get_actor_label(), "name": duplicate.get_name(), "path": duplicate.get_path_name()}
            """,
            {"actor_label": actor_label, "new_label": new_label, "offset": offset},
        )

    @mcp.tool()
    def delete_actors(labels: list[str]) -> dict:
        """Delete multiple actors through EditorActorSubsystem."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            wanted = set(args["labels"])
            actors = [a for a in subsystem.get_all_level_actors() if a.get_actor_label() in wanted or a.get_name() in wanted]
            with unreal.ScopedEditorTransaction("UnrealMCP Delete Actors"):
                ok = subsystem.destroy_actors(actors)
            result = {"requested": args["labels"], "matched": [a.get_actor_label() for a in actors], "deleted": bool(ok)}
            """,
            {"labels": labels},
        )

    @mcp.tool()
    def select_actors(labels: list[str]) -> list[str]:
        """Replace the level editor selection with the matching actors."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            wanted = set(args["labels"])
            matches = [a for a in subsystem.get_all_level_actors() if a.get_actor_label() in wanted or a.get_name() in wanted]
            subsystem.set_selected_level_actors(matches)
            result = [a.get_actor_label() for a in matches]
            """,
            {"labels": labels},
        )
