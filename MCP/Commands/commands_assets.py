"""Content Browser and Asset Registry tools."""

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
        """Search assets by name/path and optional class."""
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
    def get_asset_info(asset_path: str) -> dict:
        """Inspect an asset without modifying it."""
        return run_unreal_json(
            """
            data = unreal.EditorAssetLibrary.find_asset_data(args["asset_path"])
            if not data or not data.is_valid():
                raise RuntimeError(f'Asset not found: {args["asset_path"]}')
            asset = data.get_asset()
            result = {
                "name": str(data.asset_name),
                "package": str(data.package_name),
                "object_path": str(data.get_soft_object_path()),
                "class": asset.get_class().get_name() if asset else str(getattr(data, "asset_class_path", "")),
                "loaded": asset is not None,
                "referencers": list(unreal.EditorAssetLibrary.find_package_referencers_for_asset(args["asset_path"], False)),
            }
            """,
            {"asset_path": asset_path},
        )

    @mcp.tool()
    def duplicate_asset(source_path: str, destination_path: str) -> dict:
        """Duplicate an asset to a new object path."""
        return run_unreal_json(
            """
            asset = unreal.EditorAssetLibrary.duplicate_asset(args["source_path"], args["destination_path"])
            if asset is None:
                raise RuntimeError("Duplicate failed")
            result = {"path": asset.get_path_name(), "name": asset.get_name()}
            """,
            {"source_path": source_path, "destination_path": destination_path},
        )

    @mcp.tool()
    def rename_asset(source_path: str, destination_path: str) -> dict:
        """Rename or move an asset."""
        return run_unreal_json(
            """
            ok = unreal.EditorAssetLibrary.rename_asset(args["source_path"], args["destination_path"])
            if not ok:
                raise RuntimeError("Rename failed")
            result = {"source": args["source_path"], "destination": args["destination_path"]}
            """,
            {"source_path": source_path, "destination_path": destination_path},
        )

    @mcp.tool()
    def delete_asset(asset_path: str) -> dict:
        """Delete an asset from the project."""
        return run_unreal_json(
            """
            ok = unreal.EditorAssetLibrary.delete_asset(args["asset_path"])
            if not ok:
                raise RuntimeError("Delete failed")
            result = {"deleted": args["asset_path"]}
            """,
            {"asset_path": asset_path},
        )

    @mcp.tool()
    def save_asset(asset_path: str, only_if_dirty: bool = True) -> dict:
        """Save one asset package."""
        return run_unreal_json(
            """
            ok = unreal.EditorAssetLibrary.save_asset(args["asset_path"], only_if_is_dirty=bool(args["only_if_dirty"]))
            result = {"path": args["asset_path"], "saved": bool(ok)}
            """,
            {"asset_path": asset_path, "only_if_dirty": only_if_dirty},
        )

    @mcp.tool()
    def create_content_folder(path: str) -> dict:
        """Create a Content Browser directory."""
        return run_unreal_json(
            """
            ok = unreal.EditorAssetLibrary.make_directory(args["path"])
            result = {"path": args["path"], "created": bool(ok)}
            """,
            {"path": path},
        )

    @mcp.tool()
    def import_asset(source_file: str, destination_path: str, replace_existing: bool = False) -> list[str]:
        """Import a source file into a Content Browser folder."""
        return run_unreal_json(
            """
            task = unreal.AssetImportTask()
            task.filename = args["source_file"]
            task.destination_path = args["destination_path"]
            task.automated = True
            task.save = True
            task.replace_existing = bool(args["replace_existing"])
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            result = list(task.imported_object_paths)
            """,
            {"source_file": source_file, "destination_path": destination_path, "replace_existing": replace_existing},
            timeout=120,
        )
