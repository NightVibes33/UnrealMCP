# UnrealMCP user tools

Drop Python files in this directory to add local MCP tools without modifying the
built-in command modules.

Each file must export:

```python
def register_tools(mcp, utils):
    send_command = utils["send_command"]

    @mcp.tool()
    def my_tool(name: str) -> dict:
        return {"hello": name}
```

Do not add an untyped `ctx` argument unless the installed MCP SDK explicitly
documents it as injected context for the decorator you are using; otherwise it
becomes part of the tool's input schema.

For engine operations, either call a native bridge command with `send_command`
or follow the patterns in `MCP/Commands` and `MCP/utils/unreal_python.py`.
