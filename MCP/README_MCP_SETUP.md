# UnrealMCP MCP setup

The Python process in this directory is the MCP server. The Unreal C++ plugin is
a localhost bridge to the live Editor.

## 1. Build and enable the Unreal plugin

Place this repository at:

```text
YourProject/Plugins/UnrealMCP
```

Regenerate project files, build the Editor target, and enable **UnrealMCP** and
**Python Editor Script Plugin**.

## 2. Create the MCP Python environment

Windows:

```bat
MCP\setup_unreal_mcp.bat
```

macOS/Linux:

```bash
./MCP/setup_unreal_mcp.sh
```

## 3. Start the Unreal bridge

Open Unreal Editor and start the MCP server from the UnrealMCP toolbar/control panel.

## 4. Configure any stdio MCP client

Use the venv Python executable as the command and `MCP/unreal_mcp_bridge.py` as
the first argument.

The bridge defaults to `127.0.0.1:13377`. You can override the Python client's
connection with `UNREAL_MCP_HOST`, `UNREAL_MCP_PORT`, and `UNREAL_MCP_TIMEOUT`.

## Engine compatibility

The public Epic API documentation currently verified by this repository is
**Unreal Engine 5.8**. Runtime discovery tools (`get_unreal_capabilities`,
`search_unreal_python_api`, and `describe_unreal_python_api`) are provided so
agents can adapt to newer engine/plugin surfaces without hard-coded undocumented symbols.
