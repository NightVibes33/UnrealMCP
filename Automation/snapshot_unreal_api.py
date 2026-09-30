"""Generate a machine-readable snapshot of the live reflected Unreal Python API.

Run inside Unreal Editor. The output path comes from UNREAL_MCP_API_SNAPSHOT.
"""

from __future__ import annotations

import inspect
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import unreal


def safe_doc(obj) -> str:
    try:
        value = inspect.getdoc(obj) or ""
        return value[:1200]
    except Exception:
        return ""


def safe_signature(obj):
    try:
        return str(inspect.signature(obj))
    except Exception:
        return None


def describe_symbol(name: str):
    try:
        obj = getattr(unreal, name)
    except Exception as exc:
        return {"name": name, "error": str(exc)}

    entry = {
        "name": name,
        "python_type": type(obj).__name__,
        "callable": callable(obj),
        "signature": safe_signature(obj) if callable(obj) else None,
        "doc": safe_doc(obj),
    }

    if inspect.isclass(obj):
        members = {}
        for member_name in sorted(dir(obj)):
            if member_name.startswith("_"):
                continue
            item = {"name": member_name}
            try:
                member = getattr(obj, member_name)
                item["python_type"] = type(member).__name__
                item["callable"] = callable(member)
                item["signature"] = safe_signature(member) if callable(member) else None
                doc = safe_doc(member)
                if doc:
                    item["doc"] = doc
            except Exception as exc:
                item["error"] = str(exc)
            members[member_name] = item
        entry["members"] = members

    return entry


def enabled_plugins():
    library = getattr(unreal, "PluginBlueprintLibrary", None)
    if library is None or not hasattr(library, "get_enabled_plugin_names"):
        return []
    result = []
    for plugin_name in library.get_enabled_plugin_names():
        name = str(plugin_name)
        item = {"name": name}
        for method_name, key in (
            ("get_plugin_version_name", "version_name"),
            ("get_plugin_version", "version"),
            ("get_plugin_description", "description"),
        ):
            method = getattr(library, method_name, None)
            if method:
                try:
                    item[key] = method(name)
                except Exception:
                    pass
        result.append(item)
    return sorted(result, key=lambda x: x["name"].lower())


def main():
    output = os.environ.get("UNREAL_MCP_API_SNAPSHOT")
    if not output:
        output = str(Path(unreal.Paths.project_saved_dir()) / "UnrealMCP" / "api-snapshot.json")

    symbols = {}
    for name in sorted(dir(unreal)):
        if name.startswith("_"):
            continue
        symbols[name] = describe_symbol(name)

    payload = {
        "schema": 1,
        "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "engine_version": unreal.SystemLibrary.get_engine_version(),
        "python_version": sys.version,
        "platform": platform.platform(),
        "project_file": unreal.Paths.get_project_file_path(),
        "enabled_plugins": enabled_plugins(),
        "symbols": symbols,
    }

    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(f"UNREAL_MCP_API_SNAPSHOT={path}")
    print(f"UNREAL_MCP_SYMBOL_COUNT={len(symbols)}")


main()
