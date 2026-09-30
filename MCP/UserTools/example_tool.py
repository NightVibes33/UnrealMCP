"""Example user extension for UnrealMCP 1.1."""

def register_tools(mcp, utils):
    send_command = utils["send_command"]

    @mcp.tool()
    def my_custom_tool() -> str:
        """Return a simple custom-tool response."""
        return "Hello from a custom UnrealMCP tool!"

    @mcp.tool()
    def get_actor_count() -> dict:
        """Return the actor count reported by the native scene-info handler."""
        response = send_command("get_scene_info")
        if response.get("status") != "success":
            raise RuntimeError(response.get("message", "get_scene_info failed"))
        result = response.get("result") or {}
        return {
            "actor_count": result.get("actor_count", 0),
            "returned_actor_count": result.get("returned_actor_count", len(result.get("actors", []))),
            "limit_reached": bool(result.get("limit_reached", False)),
        }
