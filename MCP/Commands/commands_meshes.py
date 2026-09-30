"""UE 5.8 static mesh tools using StaticMeshEditorSubsystem rather than deprecated libraries."""

from __future__ import annotations
from utils import run_unreal_json

def register_all(mcp):
    @mcp.tool()
    def get_static_mesh_info(asset_path: str) -> dict:
        """Inspect LODs, sections, triangles, vertices, UVs, materials, collision and Nanite data."""
        return run_unreal_json(
            """
            mesh = unreal.load_asset(args["asset_path"])
            if mesh is None or not isinstance(mesh, unreal.StaticMesh):
                raise RuntimeError(f'Not a StaticMesh: {args["asset_path"]}')

            subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
            lod_count = mesh.get_num_lods()
            lods = []
            for lod in range(lod_count):
                lods.append({
                    "lod": lod,
                    "sections": mesh.get_num_sections(lod),
                    "triangles": mesh.get_num_triangles(lod),
                    "vertices": mesh.get_num_vertices(lod),
                    "tex_coords": mesh.get_num_tex_coords(lod),
                    "uv_channels": subsystem.get_num_uv_channels(mesh, lod),
                })
            bounds = mesh.get_bounds()
            materials = []
            for index, slot in enumerate(mesh.get_editor_property("static_materials")):
                material = slot.material_interface
                materials.append({
                    "index": index,
                    "slot_name": str(slot.material_slot_name),
                    "material": material.get_path_name() if material else None,
                })
            nanite = mesh.get_editor_property("nanite_settings")
            result = {
                "path": mesh.get_path_name(),
                "lod_count": lod_count,
                "lods": lods,
                "materials": materials,
                "simple_collision_count": subsystem.get_simple_collision_count(mesh),
                "convex_collision_count": subsystem.get_convex_collision_count(mesh),
                "nanite_enabled": bool(nanite.get_editor_property("enabled")) if nanite else False,
                "nanite_triangles": mesh.get_num_nanite_triangles(),
                "nanite_vertices": mesh.get_num_nanite_vertices(),
                "allow_cpu_access": bool(mesh.get_editor_property("allow_cpu_access")),
                "support_ray_tracing": bool(mesh.get_editor_property("support_ray_tracing")),
                "bounds": {
                    "origin": [bounds.origin.x, bounds.origin.y, bounds.origin.z],
                    "box_extent": [bounds.box_extent.x, bounds.box_extent.y, bounds.box_extent.z],
                    "sphere_radius": bounds.sphere_radius,
                },
            }
            """,
            {"asset_path": asset_path},
        )

    @mcp.tool()
    def set_static_mesh_nanite(asset_path: str, enabled: bool, save: bool = True) -> dict:
        """Enable or disable Nanite through the UE 5.8 MeshNaniteSettings struct."""
        return run_unreal_json(
            """
            mesh = unreal.load_asset(args["asset_path"])
            if mesh is None or not isinstance(mesh, unreal.StaticMesh):
                raise RuntimeError(f'Not a StaticMesh: {args["asset_path"]}')
            with unreal.ScopedEditorTransaction("UnrealMCP Set Static Mesh Nanite"):
                settings = mesh.get_editor_property("nanite_settings")
                settings.set_editor_property("enabled", bool(args["enabled"]))
                mesh.set_editor_property("nanite_settings", settings)
                mesh.modify()
            saved = False
            if bool(args["save"]):
                saved = bool(unreal.get_editor_subsystem(unreal.EditorAssetSubsystem).save_loaded_asset(mesh, True))
            result = {"path": mesh.get_path_name(), "nanite_enabled": bool(args["enabled"]), "saved": saved}
            """,
            {"asset_path": asset_path, "enabled": enabled, "save": save},
            timeout=120,
        )

    @mcp.tool()
    def set_static_mesh_cpu_access(asset_path: str, enabled: bool, save: bool = True) -> dict:
        """Set StaticMesh Allow CPU Access through StaticMeshEditorSubsystem."""
        return run_unreal_json(
            """
            mesh = unreal.load_asset(args["asset_path"])
            if mesh is None or not isinstance(mesh, unreal.StaticMesh):
                raise RuntimeError(f'Not a StaticMesh: {args["asset_path"]}')
            subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
            with unreal.ScopedEditorTransaction("UnrealMCP Set Static Mesh CPU Access"):
                subsystem.set_allow_cpu_access(mesh, bool(args["enabled"]))
            saved = False
            if bool(args["save"]):
                saved = bool(unreal.get_editor_subsystem(unreal.EditorAssetSubsystem).save_loaded_asset(mesh, True))
            result = {"path": mesh.get_path_name(), "allow_cpu_access": bool(args["enabled"]), "saved": saved}
            """,
            {"asset_path": asset_path, "enabled": enabled, "save": save},
        )

    @mcp.tool()
    def add_static_mesh_simple_collision(asset_path: str, shape: str = "BOX", save: bool = True) -> dict:
        """Add simple collision using ScriptCollisionShapeType (for example BOX, SPHERE or CAPSULE)."""
        return run_unreal_json(
            """
            mesh = unreal.load_asset(args["asset_path"])
            if mesh is None or not isinstance(mesh, unreal.StaticMesh):
                raise RuntimeError(f'Not a StaticMesh: {args["asset_path"]}')
            enum_type = getattr(unreal, "ScriptCollisionShapeType", None)
            if enum_type is None:
                raise RuntimeError("ScriptCollisionShapeType is unavailable")
            shape_name = args["shape"].upper()
            if not hasattr(enum_type, shape_name):
                available = [x for x in dir(enum_type) if x.isupper()]
                raise RuntimeError(f'Unknown collision shape {shape_name}; available: {available}')
            subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
            index = subsystem.add_simple_collisions(mesh, getattr(enum_type, shape_name))
            saved = False
            if bool(args["save"]):
                saved = bool(unreal.get_editor_subsystem(unreal.EditorAssetSubsystem).save_loaded_asset(mesh, True))
            result = {"path": mesh.get_path_name(), "shape": shape_name, "collision_index": index, "saved": saved}
            """,
            {"asset_path": asset_path, "shape": shape, "save": save},
        )

    @mcp.tool()
    def set_static_mesh_convex_collision(
        asset_path: str,
        hull_count: int = 8,
        max_hull_vertices: int = 16,
        hull_precision: int = 100000,
        save: bool = True,
    ) -> dict:
        """Generate convex decomposition collision through StaticMeshEditorSubsystem."""
        return run_unreal_json(
            """
            mesh = unreal.load_asset(args["asset_path"])
            if mesh is None or not isinstance(mesh, unreal.StaticMesh):
                raise RuntimeError(f'Not a StaticMesh: {args["asset_path"]}')
            subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
            ok = subsystem.set_convex_decomposition_collisions(
                mesh,
                int(args["hull_count"]),
                int(args["max_hull_vertices"]),
                int(args["hull_precision"]),
            )
            saved = False
            if bool(args["save"]):
                saved = bool(unreal.get_editor_subsystem(unreal.EditorAssetSubsystem).save_loaded_asset(mesh, True))
            result = {"path": mesh.get_path_name(), "generated": bool(ok), "saved": saved}
            """,
            {
                "asset_path": asset_path,
                "hull_count": hull_count,
                "max_hull_vertices": max_hull_vertices,
                "hull_precision": hull_precision,
                "save": save,
            },
            timeout=120,
        )

    @mcp.tool()
    def add_static_mesh_uv_channel(asset_path: str, lod_index: int = 0, save: bool = True) -> dict:
        """Add an empty UV channel to a StaticMesh LOD."""
        return run_unreal_json(
            """
            mesh = unreal.load_asset(args["asset_path"])
            if mesh is None or not isinstance(mesh, unreal.StaticMesh):
                raise RuntimeError(f'Not a StaticMesh: {args["asset_path"]}')
            subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
            ok = subsystem.add_uv_channel(mesh, int(args["lod_index"]))
            count = subsystem.get_num_uv_channels(mesh, int(args["lod_index"]))
            saved = False
            if bool(args["save"]):
                saved = bool(unreal.get_editor_subsystem(unreal.EditorAssetSubsystem).save_loaded_asset(mesh, True))
            result = {"path": mesh.get_path_name(), "lod": int(args["lod_index"]), "added": bool(ok), "uv_channels": count, "saved": saved}
            """,
            {"asset_path": asset_path, "lod_index": lod_index, "save": save},
        )
