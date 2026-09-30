"""Core scene manipulation tools backed by native C++ handlers."""

from __future__ import annotations
import json
from utils import send_command

def _render(response):
    return response.get("result") if response.get("status") == "success" else response

def register_all(mcp):
    @mcp.tool()
    def get_scene_info() -> dict:
        """Return a summary of actors in the currently open Unreal level."""
        return _render(send_command("get_scene_info"))

    @mcp.tool()
    def create_object(type: str, location: list[float] | None = None, label: str | None = None) -> dict:
        """Create an actor. Native types include Cube and StaticMeshActor."""
        params = {"type": type}
        if location is not None:
            params["location"] = location
        if label:
            params["label"] = label
        return _render(send_command("create_object", params))

    @mcp.tool()
    def modify_object(
        name: str,
        location: list[float] | None = None,
        rotation: list[float] | None = None,
        scale: list[float] | None = None,
    ) -> dict:
        """Modify an actor transform by actor name/label."""
        params = {"name": name}
        if location is not None:
            params["location"] = location
        if rotation is not None:
            params["rotation"] = rotation
        if scale is not None:
            params["scale"] = scale
        return _render(send_command("modify_object", params))

    @mcp.tool()
    def delete_object(name: str) -> dict:
        """Delete an actor by name/label."""
        return _render(send_command("delete_object", {"name": name}))
