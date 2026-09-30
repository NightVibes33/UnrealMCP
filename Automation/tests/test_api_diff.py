from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "diff_unreal_api.py"
SPEC = importlib.util.spec_from_file_location("diff_unreal_api", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class ApiDiffTests(unittest.TestCase):
    def test_removed_referenced_symbol_is_unsafe(self):
        old = {
            "engine_version": "5.8",
            "symbols": {
                "OldSubsystem": {
                    "members": {"old_method": {"signature": "(self)"}}
                }
            },
        }
        new = {"engine_version": "6.0", "symbols": {}}
        result = MODULE.diff_snapshots(old, new, "unreal.OldSubsystem")
        self.assertFalse(result["safe_for_automatic_compatibility_merge"])
        self.assertIn("OldSubsystem", result["referenced_breaking"])

    def test_additions_only_are_safe(self):
        old = {"engine_version": "5.8", "symbols": {}}
        new = {"engine_version": "6.0", "symbols": {"NewThing": {"members": {}}}}
        result = MODULE.diff_snapshots(old, new, "")
        self.assertTrue(result["safe_for_automatic_compatibility_merge"])
        self.assertEqual(result["breaking_count"], 0)


if __name__ == "__main__":
    unittest.main()
