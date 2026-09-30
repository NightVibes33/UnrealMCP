"""Data validation tools using UE's editor validation system when available."""

from __future__ import annotations
from utils import run_unreal_json

def register_all(mcp):
    @mcp.tool()
    def get_validation_capabilities() -> dict:
        """Inspect the live EditorValidatorSubsystem API."""
        return run_unreal_json(
            """
            cls = getattr(unreal, "EditorValidatorSubsystem", None)
            result = {
                "available": cls is not None,
                "methods": [name for name in dir(cls) if not name.startswith("_")] if cls else [],
            }
            """
        )

    @mcp.tool()
    def validate_asset(asset_path: str) -> dict:
        """Run Unreal asset validation using whichever validation method UE exposes in this build."""
        return run_unreal_json(
            """
            cls = getattr(unreal, "EditorValidatorSubsystem", None)
            if cls is None:
                raise RuntimeError("EditorValidatorSubsystem is unavailable; enable the Data Validation plugin")
            subsystem = unreal.get_editor_subsystem(cls)
            asset = unreal.load_asset(args["asset_path"])
            if asset is None:
                raise RuntimeError(f'Asset not found: {args["asset_path"]}')

            outcome = None
            method_used = None
            for method_name in ("is_object_valid", "validate_loaded_asset", "validate_asset"):
                method = getattr(subsystem, method_name, None)
                if method is None:
                    continue
                try:
                    outcome = method(asset)
                    method_used = method_name
                    break
                except TypeError:
                    continue

            if method_used is None:
                raise RuntimeError(
                    "This engine exposes EditorValidatorSubsystem but not a simple single-asset validation signature; "
                    "use describe_unreal_python_api('EditorValidatorSubsystem') for the exact runtime API."
                )
            result = {"path": asset.get_path_name(), "method": method_used, "result": str(outcome)}
            """,
            {"asset_path": asset_path},
            timeout=120,
        )
