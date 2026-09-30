"""Blueprint lifecycle tools backed by the plugin's native C++ handlers."""

from __future__ import annotations
from typing import Any
from utils import send_command

def _render(response):
    return response.get("result") if response.get("status") == "success" else response

def register_all(mcp):
    @mcp.tool()
    def create_blueprint(package_path: str, name: str, parent_class: str = "Actor") -> dict:
        """Create a Blueprint asset in Unreal."""
        return _render(send_command("create_blueprint", {
            "package_path": package_path,
            "name": name,
            "parent_class": parent_class,
        }))

    @mcp.tool()
    def modify_blueprint(blueprint_path: str, properties: dict[str, Any]) -> dict:
        """Modify supported Blueprint metadata/properties."""
        return _render(send_command("modify_blueprint", {
            "blueprint_path": blueprint_path,
            "properties": properties,
        }))

    @mcp.tool()
    def get_blueprint_info(blueprint_path: str) -> dict:
        """Inspect a Blueprint asset, variables and graphs supported by the native bridge."""
        return _render(send_command("get_blueprint_info", {"blueprint_path": blueprint_path}))

    @mcp.tool()
    def create_blueprint_event(
        blueprint_path: str,
        event_name: str,
        graph_name: str = "EventGraph",
        node_position: list[float] | None = None,
    ) -> dict:
        """Create an event node in an existing Blueprint."""
        params = {
            "blueprint_path": blueprint_path,
            "event_name": event_name,
            "graph_name": graph_name,
        }
        if node_position is not None:
            params["node_position"] = node_position
        return _render(send_command("create_blueprint_event", params))
