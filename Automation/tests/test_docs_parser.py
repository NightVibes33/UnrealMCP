from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "check_epic_docs.py"
SPEC = importlib.util.spec_from_file_location("check_epic_docs", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class DocsParserTests(unittest.TestCase):
    def test_extracts_versions_and_ignores_script_noise(self):
        raw = b"""
        <html><head><script>Unreal Engine 99.9</script></head>
        <body><h1>Unreal Engine 5.8 Release Notes</h1>
        <a href='/unreal-engine-5-9-release-notes'>next</a></body></html>
        """
        text, versions = MODULE.normalize_document(raw, "text/html")
        self.assertIn("5.8", versions)
        self.assertIn("5.9", versions)
        self.assertNotIn("99.9", text)


if __name__ == "__main__":
    unittest.main()
