from __future__ import annotations

import json
import socket
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from Automation import mcp_bridge_smoke_test as smoke


class NativeBridgeSmokeClientTests(unittest.TestCase):
    def test_full_smoke_sequence_against_mock_bridge(self):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        listener.listen(8)
        port = listener.getsockname()[1]
        received = []

        def server():
            try:
                for _ in range(5):
                    conn, _addr = listener.accept()
                    with conn:
                        data = b""
                        while not data.endswith(b"\n"):
                            chunk = conn.recv(4096)
                            if not chunk:
                                break
                            data += chunk
                        request = json.loads(data.decode("utf-8"))
                        received.append(request["type"])
                        command = request["type"]

                        if command == "get_scene_info":
                            response = {"status": "success", "result": {"actor_count": 1, "actors": []}}
                        elif command == "execute_python":
                            response = {
                                "status": "success",
                                "result": {
                                    "output": "UNREAL_MCP_NATIVE_BRIDGE_OK\n5.8.0",
                                    "command_result": "",
                                },
                            }
                        elif command == "create_object":
                            response = {
                                "status": "success",
                                "result": {"name": "MockCube_1", "label": "UnrealMCP_NativeBridge_Smoke"},
                            }
                        elif command == "delete_object":
                            response = {"status": "success", "result": {}}
                        else:
                            response = {"status": "error", "message": f"unexpected command: {command}"}

                        conn.sendall(json.dumps(response).encode("utf-8"))
            finally:
                listener.close()

        thread = threading.Thread(target=server, daemon=True)
        thread.start()

        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "native-smoke.json"
            original_argv = sys.argv[:]
            try:
                sys.argv = [
                    "mcp_bridge_smoke_test.py",
                    "--port",
                    str(port),
                    "--wait-seconds",
                    "5",
                    "--json-out",
                    str(output),
                ]
                self.assertEqual(smoke.main(), 0)
            finally:
                sys.argv = original_argv

            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertTrue(payload["passed"])
            self.assertEqual(payload["engine_version"], "5.8.0")

        thread.join(timeout=5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(
            received,
            [
                "get_scene_info",
                "get_scene_info",
                "execute_python",
                "create_object",
                "delete_object",
            ],
        )


if __name__ == "__main__":
    unittest.main()
