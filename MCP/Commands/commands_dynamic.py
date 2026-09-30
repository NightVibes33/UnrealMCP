"""Forward-compatible dynamic Unreal Python invocation tools.

These tools intentionally operate on public symbols under the live `unreal`
module. They make newly exposed engine/plugin APIs usable before UnrealMCP has a
purpose-built wrapper for them.
"""

from __future__ import annotations
from typing import Any
from utils import run_unreal_json

_WIRE_HELPERS = r"""
def _decode(value):
    if isinstance(value, list):
        return [_decode(v) for v in value]
    if not isinstance(value, dict):
        return value
    if "$asset" in value:
        asset = unreal.load_asset(value["$asset"])
        if asset is None:
            raise RuntimeError(f'Asset not found: {value["$asset"]}')
        return asset
    if "$class" in value:
        cls = unreal.load_class(None, value["$class"])
        if cls is None:
            raise RuntimeError(f'Class not found: {value["$class"]}')
        return cls
    if "$name" in value:
        return unreal.Name(str(value["$name"]))
    if "$vector" in value:
        v = value["$vector"]
        return unreal.Vector(float(v[0]), float(v[1]), float(v[2]))
    if "$rotator" in value:
        r = value["$rotator"]
        if isinstance(r, dict):
            return unreal.Rotator(
                pitch=float(r.get("pitch", 0.0)),
                yaw=float(r.get("yaw", 0.0)),
                roll=float(r.get("roll", 0.0)),
            )
        return unreal.Rotator(pitch=float(r[0]), yaw=float(r[1]), roll=float(r[2]))
    if "$enum" in value:
        enum_path = str(value["$enum"])
        parts = enum_path.split(".")
        if len(parts) != 2 or any(not p or p.startswith("_") for p in parts):
            raise RuntimeError(f'Invalid enum path: {enum_path}')
        enum_type = getattr(unreal, parts[0], None)
        if enum_type is None or not hasattr(enum_type, parts[1]):
            raise RuntimeError(f'Enum value not found: {enum_path}')
        return getattr(enum_type, parts[1])
    if "$soft_object_path" in value:
        return unreal.SoftObjectPath(str(value["$soft_object_path"]))
    return {k: _decode(v) for k, v in value.items()}

def _encode(value, depth=0):
    if depth > 5:
        return str(value)
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        return [_encode(v, depth + 1) for v in value]
    if isinstance(value, dict):
        return {str(k): _encode(v, depth + 1) for k, v in value.items()}
    if isinstance(value, unreal.Vector):
        return {"x": value.x, "y": value.y, "z": value.z}
    if isinstance(value, unreal.Rotator):
        return {"pitch": value.pitch, "yaw": value.yaw, "roll": value.roll}
    if hasattr(unreal, "Transform") and isinstance(value, unreal.Transform):
        return str(value)
    if hasattr(value, "get_path_name"):
        try:
            return {
                "object_path": value.get_path_name(),
                "name": value.get_name() if hasattr(value, "get_name") else None,
                "class": value.get_class().get_name() if hasattr(value, "get_class") else type(value).__name__,
            }
        except Exception:
            pass
    return str(value)

def _resolve_unreal_path(path):
    parts = [p for p in str(path).split(".") if p]
    if not parts or any(p.startswith("_") for p in parts):
        raise RuntimeError(f'Invalid public Unreal API path: {path}')
    obj = unreal
    for part in parts:
        if not hasattr(obj, part):
            raise RuntimeError(f'Unreal API path not found: {path}')
        obj = getattr(obj, part)
    return obj
"""

def register_all(mcp):
    @mcp.tool()
    def invoke_unreal_api(
        symbol: str,
        arguments: list[Any] | None = None,
        keyword_arguments: dict[str, Any] | None = None,
    ) -> Any:
        """Call a public callable under the live unreal module.

        Wire values may use {"$asset":"/Game/..."}, {"$class":"/Script/..."},
        {"$name":"..."}, {"$vector":[x,y,z]}, {"$rotator":{"pitch":0,"yaw":0,"roll":0}},
        {"$enum":"EnumType.MEMBER"}, or {"$soft_object_path":"..."}.
        """
        return run_unreal_json(
            _WIRE_HELPERS + r"""
target = _resolve_unreal_path(args["symbol"])
if not callable(target):
    raise RuntimeError(f'Unreal API symbol is not callable: {args["symbol"]}')
call_args = [_decode(v) for v in (args.get("arguments") or [])]
call_kwargs = {k: _decode(v) for k, v in (args.get("keyword_arguments") or {}).items()}
result = _encode(target(*call_args, **call_kwargs))
""",
            {
                "symbol": symbol,
                "arguments": arguments or [],
                "keyword_arguments": keyword_arguments or {},
            },
            timeout=120,
        )

    @mcp.tool()
    def invoke_editor_subsystem(
        subsystem_class: str,
        method: str,
        arguments: list[Any] | None = None,
        keyword_arguments: dict[str, Any] | None = None,
    ) -> Any:
        """Call a method on a live Unreal EditorSubsystem by class name."""
        return run_unreal_json(
            _WIRE_HELPERS + r"""
cls = _resolve_unreal_path(args["subsystem_class"])
subsystem = unreal.get_editor_subsystem(cls)
if subsystem is None:
    raise RuntimeError(f'Editor subsystem unavailable: {args["subsystem_class"]}')
method_name = args["method"]
if not method_name or method_name.startswith("_") or not hasattr(subsystem, method_name):
    raise RuntimeError(f'Method not found: {args["subsystem_class"]}.{method_name}')
target = getattr(subsystem, method_name)
if not callable(target):
    raise RuntimeError(f'Subsystem member is not callable: {method_name}')
call_args = [_decode(v) for v in (args.get("arguments") or [])]
call_kwargs = {k: _decode(v) for k, v in (args.get("keyword_arguments") or {}).items()}
result = _encode(target(*call_args, **call_kwargs))
""",
            {
                "subsystem_class": subsystem_class,
                "method": method,
                "arguments": arguments or [],
                "keyword_arguments": keyword_arguments or {},
            },
            timeout=120,
        )

    @mcp.tool()
    def invoke_engine_subsystem(
        subsystem_class: str,
        method: str,
        arguments: list[Any] | None = None,
        keyword_arguments: dict[str, Any] | None = None,
    ) -> Any:
        """Call a method on a live Unreal EngineSubsystem by class name."""
        return run_unreal_json(
            _WIRE_HELPERS + r"""
cls = _resolve_unreal_path(args["subsystem_class"])
subsystem = unreal.get_engine_subsystem(cls)
if subsystem is None:
    raise RuntimeError(f'Engine subsystem unavailable: {args["subsystem_class"]}')
method_name = args["method"]
if not method_name or method_name.startswith("_") or not hasattr(subsystem, method_name):
    raise RuntimeError(f'Method not found: {args["subsystem_class"]}.{method_name}')
target = getattr(subsystem, method_name)
if not callable(target):
    raise RuntimeError(f'Subsystem member is not callable: {method_name}')
call_args = [_decode(v) for v in (args.get("arguments") or [])]
call_kwargs = {k: _decode(v) for k, v in (args.get("keyword_arguments") or {}).items()}
result = _encode(target(*call_args, **call_kwargs))
""",
            {
                "subsystem_class": subsystem_class,
                "method": method,
                "arguments": arguments or [],
                "keyword_arguments": keyword_arguments or {},
            },
            timeout=120,
        )
