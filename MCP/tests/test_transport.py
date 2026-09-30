from __future__ import annotations

import json
import socket
import threading
import unittest

from utils.command_utils import send_command

class TransportTests(unittest.TestCase):
    def test_newline_json_request_and_response(self):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        seen = {}

        def server():
            conn, _ = listener.accept()
            with conn:
                data = b""
                while not data.endswith(b"\n"):
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                seen["payload"] = json.loads(data.decode("utf-8"))
                conn.sendall(json.dumps({"status": "success", "result": {"ok": True}}).encode("utf-8"))
            listener.close()

        thread = threading.Thread(target=server, daemon=True)
        thread.start()
        response = send_command("ping", {"value": 7}, host="127.0.0.1", port=port, timeout=3)
        thread.join(timeout=3)

        self.assertEqual(seen["payload"], {"type": "ping", "params": {"value": 7}})
        self.assertEqual(response["result"]["ok"], True)

if __name__ == "__main__":
    unittest.main()
