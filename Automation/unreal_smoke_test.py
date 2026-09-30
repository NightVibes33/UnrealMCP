"""Live Unreal Editor smoke test for UnrealMCP compatibility validation."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import unreal


def check(name, fn, results):
    try:
        value = fn()
        results.append({"name": name, "ok": True, "value": str(value)})
        return value
    except Exception as exc:
        results.append({"name": name, "ok": False, "error": repr(exc)})
        return None


def main():
    output = os.environ.get("UNREAL_MCP_SMOKE_RESULT")
    if not output:
        output = str(Path(unreal.Paths.project_saved_dir()) / "UnrealMCP" / "smoke-result.json")

    results = []
    required_symbols = [
        "EditorActorSubsystem",
        "EditorAssetSubsystem",
        "AssetEditorSubsystem",
        "LevelEditorSubsystem",
        "UnrealEditorSubsystem",
        "StaticMeshEditorSubsystem",
        "ScopedEditorTransaction",
        "StaticMeshActor",
    ]

    for symbol in required_symbols:
        check(f"symbol:{symbol}", lambda s=symbol: getattr(unreal, s), results)

    actor_subsystem = check(
        "subsystem:EditorActorSubsystem",
        lambda: unreal.get_editor_subsystem(unreal.EditorActorSubsystem),
        results,
    )
    asset_subsystem = check(
        "subsystem:EditorAssetSubsystem",
        lambda: unreal.get_editor_subsystem(unreal.EditorAssetSubsystem),
        results,
    )
    check(
        "subsystem:LevelEditorSubsystem",
        lambda: unreal.get_editor_subsystem(unreal.LevelEditorSubsystem),
        results,
    )
    check(
        "subsystem:StaticMeshEditorSubsystem",
        lambda: unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem),
        results,
    )

    temp_dir = "/Game/__UnrealMCPValidation"
    if asset_subsystem:
        check("asset:make_directory", lambda: asset_subsystem.make_directory(temp_dir), results)

    spawned = None
    if actor_subsystem:
        def spawn():
            with unreal.ScopedEditorTransaction("UnrealMCP Validation Spawn"):
                return actor_subsystem.spawn_actor_from_class(
                    unreal.StaticMeshActor,
                    unreal.Vector(10.0, 20.0, 30.0),
                    unreal.Rotator(pitch=0.0, yaw=15.0, roll=0.0),
                    True,
                )
        spawned = check("actor:spawn_actor_from_class", spawn, results)
        if spawned:
            check("actor:get_location", lambda: spawned.get_actor_location(), results)
            check("actor:destroy_actor", lambda: actor_subsystem.destroy_actor(spawned), results)

    if asset_subsystem and hasattr(asset_subsystem, "delete_directory"):
        check("asset:delete_directory", lambda: asset_subsystem.delete_directory(temp_dir), results)

    failures = [item for item in results if not item["ok"]]
    payload = {
        "schema": 1,
        "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "engine_version": unreal.SystemLibrary.get_engine_version(),
        "passed": not failures,
        "failure_count": len(failures),
        "checks": results,
    }

    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"UNREAL_MCP_SMOKE_RESULT={path}")
    print(f"UNREAL_MCP_SMOKE_PASSED={str(payload['passed']).lower()}")

    if failures:
        raise RuntimeError(f"UnrealMCP smoke test failed: {len(failures)} check(s)")


main()
