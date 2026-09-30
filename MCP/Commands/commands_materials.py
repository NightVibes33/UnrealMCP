"""Material creation, inspection and assignment tools."""

from __future__ import annotations
from typing import Any
from utils import run_unreal_json, send_command

def _render(response):
    return response.get("result") if response.get("status") == "success" else response

def register_all(mcp):
    @mcp.tool()
    def create_material(package_path: str, name: str, properties: dict[str, Any] | None = None) -> dict:
        """Create a Material asset."""
        return _render(send_command("create_material", {
            "package_path": package_path,
            "name": name,
            "properties": properties or {},
        }))

    @mcp.tool()
    def modify_material(path: str, properties: dict[str, Any]) -> dict:
        """Modify supported Material properties."""
        return _render(send_command("modify_material", {"path": path, "properties": properties}))

    @mcp.tool()
    def get_material_info(path: str) -> dict:
        """Inspect a Material asset."""
        return _render(send_command("get_material_info", {"path": path}))

    @mcp.tool()
    def assign_material(actor_label: str, material_path: str, slot: int = 0) -> dict:
        """Assign a material to the first primitive component on an actor."""
        return run_unreal_json(
            """
            actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            actor = next((a for a in actor_subsystem.get_all_level_actors()
                          if a.get_actor_label() == args["actor_label"] or a.get_name() == args["actor_label"]), None)
            if actor is None:
                raise RuntimeError(f'Actor not found: {args["actor_label"]}')
            material = unreal.load_asset(args["material_path"])
            if material is None:
                raise RuntimeError(f'Material not found: {args["material_path"]}')
            primitive = next((c for c in actor.get_components_by_class(unreal.PrimitiveComponent)), None)
            if primitive is None:
                raise RuntimeError("Actor has no PrimitiveComponent")
            primitive.set_material(int(args["slot"]), material)
            result = {"actor": actor.get_actor_label(), "material": material.get_path_name(), "slot": int(args["slot"])}
            """,
            {"actor_label": actor_label, "material_path": material_path, "slot": slot},
        )

    @mcp.tool()
    def get_actor_materials(actor_label: str) -> list[dict]:
        """List material slots on an actor's primitive components."""
        return run_unreal_json(
            """
            actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            actor = next((a for a in actor_subsystem.get_all_level_actors()
                          if a.get_actor_label() == args["actor_label"] or a.get_name() == args["actor_label"]), None)
            if actor is None:
                raise RuntimeError(f'Actor not found: {args["actor_label"]}')
            items = []
            for component in actor.get_components_by_class(unreal.PrimitiveComponent):
                for index, material in enumerate(component.get_materials()):
                    items.append({
                        "component": component.get_name(),
                        "slot": index,
                        "material": material.get_path_name() if material else None,
                    })
            result = items
            """,
            {"actor_label": actor_label},
        )
