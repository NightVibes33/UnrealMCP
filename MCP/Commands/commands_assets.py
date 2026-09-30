"""Content Browser and Asset Registry tools using UE 5.8 editor subsystems."""

from __future__ import annotations
from utils import run_unreal_json

def register_all(mcp):
    @mcp.tool()
    def search_assets(
        query: str = "",
        path: str = "/Game",
        class_name: str | None = None,
        recursive: bool = True,
        limit: int = 200,
    ) -> list[dict]:
        """Search assets by name/path and optional class using AssetRegistry."""
        return run_unreal_json(
            """
            registry = unreal.AssetRegistryHelpers.get_asset_registry()
            assets = registry.get_assets_by_path(unreal.Name(args["path"]), recursive=bool(args["recursive"]))
            query = args["query"].lower()
            class_name = (args.get("class_name") or "").lower()
            out = []
            for data in assets:
                name = str(data.asset_name)
                package = str(data.package_name)
                class_path = str(getattr(data, "asset_class_path", getattr(data, "asset_class", "")))
                if query and query not in name.lower() and query not in package.lower():
                    continue
                if class_name and class_name not in class_path.lower():
                    continue
                out.append({
                    "name": name,
                    "package": package,
                    "object_path": str(data.get_soft_object_path()),
                    "class": class_path,
                })
                if len(out) >= int(args["limit"]):
                    break
            result = out
            """,
            {"query": query, "path": path, "class_name": class_name, "recursive": recursive, "limit": limit},
        )

    @mcp.tool()
    def list_assets(path: str = "/Game", recursive: bool = True, include_folders: bool = False, limit: int = 1000) -> list[str]:
        """List asset paths through EditorAssetSubsystem."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
            paths = subsystem.list_assets(args["path"], recursive=bool(args["recursive"]), include_folder=bool(args["include_folders"]))
            result = [str(x) for x in list(paths)[:int(args["limit"])]]
            """,
            {"path": path, "recursive": recursive, "include_folders": include_folders, "limit": limit},
        )

    @mcp.tool()
    def get_asset_info(asset_path: str) -> dict:
        """Inspect an asset, its package metadata and referencers."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
            if not subsystem.does_asset_exist(args["asset_path"]):
                raise RuntimeError(f'Asset not found: {args["asset_path"]}')
            data = subsystem.find_asset_data(args["asset_path"])
            asset = subsystem.load_asset(args["asset_path"])
            referencers = []
            try:
                referencers = list(subsystem.find_package_referencers_for_asset(args["asset_path"], False))
            except Exception:
                pass
            result = {
                "name": str(data.asset_name) if data else (asset.get_name() if asset else None),
                "package": str(data.package_name) if data else None,
                "object_path": str(data.get_soft_object_path()) if data else (asset.get_path_name() if asset else args["asset_path"]),
                "class": asset.get_class().get_name() if asset else str(getattr(data, "asset_class_path", "")),
                "loaded": asset is not None,
                "referencers": [str(x) for x in referencers],
            }
            """,
            {"asset_path": asset_path},
        )

    @mcp.tool()
    def duplicate_asset(source_path: str, destination_path: str, save: bool = True) -> dict:
        """Duplicate an asset using EditorAssetSubsystem."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
            with unreal.ScopedEditorTransaction("UnrealMCP Duplicate Asset"):
                asset = subsystem.duplicate_asset(args["source_path"], args["destination_path"])
            if asset is None:
                raise RuntimeError("Duplicate failed")
            saved = bool(subsystem.save_loaded_asset(asset, True)) if bool(args["save"]) else False
            result = {"path": asset.get_path_name(), "name": asset.get_name(), "saved": saved}
            """,
            {"source_path": source_path, "destination_path": destination_path, "save": save},
        )

    @mcp.tool()
    def rename_asset(source_path: str, destination_path: str) -> dict:
        """Rename or move an asset using EditorAssetSubsystem."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
            with unreal.ScopedEditorTransaction("UnrealMCP Rename Asset"):
                ok = subsystem.rename_asset(args["source_path"], args["destination_path"])
            if not ok:
                raise RuntimeError("Rename failed")
            result = {"source": args["source_path"], "destination": args["destination_path"], "renamed": True}
            """,
            {"source_path": source_path, "destination_path": destination_path},
        )

    @mcp.tool()
    def delete_asset(asset_path: str) -> dict:
        """Force-delete an asset through EditorAssetSubsystem."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
            with unreal.ScopedEditorTransaction("UnrealMCP Delete Asset"):
                ok = subsystem.delete_asset(args["asset_path"])
            if not ok:
                raise RuntimeError("Delete failed")
            result = {"deleted": args["asset_path"]}
            """,
            {"asset_path": asset_path},
        )

    @mcp.tool()
    def save_asset(asset_path: str, only_if_dirty: bool = True) -> dict:
        """Save one asset package through EditorAssetSubsystem."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
            ok = subsystem.save_asset(args["asset_path"], only_if_is_dirty=bool(args["only_if_dirty"]))
            result = {"path": args["asset_path"], "saved": bool(ok)}
            """,
            {"asset_path": asset_path, "only_if_dirty": only_if_dirty},
        )

    @mcp.tool()
    def create_content_folder(path: str) -> dict:
        """Create a Content Browser directory through EditorAssetSubsystem."""
        return run_unreal_json(
            """
            subsystem = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
            ok = subsystem.make_directory(args["path"])
            result = {"path": args["path"], "created": bool(ok)}
            """,
            {"path": path},
        )

    @mcp.tool()
    def import_asset(source_file: str, destination_path: str, replace_existing: bool = False) -> list[str]:
        """Import a source file with AssetImportTask."""
        return run_unreal_json(
            """
            task = unreal.AssetImportTask()
            task.filename = args["source_file"]
            task.destination_path = args["destination_path"]
            task.automated = True
            task.save = True
            task.replace_existing = bool(args["replace_existing"])
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            result = [str(x) for x in task.imported_object_paths]
            """,
            {"source_file": source_file, "destination_path": destination_path, "replace_existing": replace_existing},
            timeout=180,
        )

    @mcp.tool()
    def open_asset_editor(asset_path: str) -> dict:
        """Open an asset in its native Unreal asset editor."""
        return run_unreal_json(
            """
            asset = unreal.load_asset(args["asset_path"])
            if asset is None:
                raise RuntimeError(f'Asset not found: {args["asset_path"]}')
            subsystem = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
            ok = subsystem.open_editor_for_assets([asset])
            result = {"path": asset.get_path_name(), "opened": bool(ok)}
            """,
            {"asset_path": asset_path},
        )

    @mcp.tool()
    def close_asset_editor(asset_path: str) -> dict:
        """Close all open editors for an asset."""
        return run_unreal_json(
            """
            asset = unreal.load_asset(args["asset_path"])
            if asset is None:
                raise RuntimeError(f'Asset not found: {args["asset_path"]}')
            count = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(asset)
            result = {"path": asset.get_path_name(), "closed_editors": int(count)}
            """,
            {"asset_path": asset_path},
        )
