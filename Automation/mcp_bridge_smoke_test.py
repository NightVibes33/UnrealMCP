#!/usr/bin/env python3
"""External smoke test for the actual native UnrealMCP TCP bridge."""

from __future__ import annotations

import argparse
import json
import socket
import time


def send_command(host: str, port: int, command: str, params: dict, timeout: float = 20.0) -> dict:
    payload = json.dumps({"type": command, "params": params}, separators=(",", ":")).encode("utf-8") + b"\n"
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.settimeout(timeout)
        sock.sendall(payload)
        chunks: list[bytes] = []
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
            raw = b"".join(chunks).strip()
            try:
                return json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                continue
    raise RuntimeError(f"No JSON response for command {command}")


def wait_for_bridge(host: str, port: int, wait_seconds: int) -> None:
    deadline = time.time() + wait_seconds
    last_error = None
    while time.time() < deadline:
        try:
            response = send_command(host, port, "get_scene_info", {}, timeout=5)
            if response.get("status") == "success":
                return
            last_error = response
        except Exception as exc:
            last_error = exc
        time.sleep(2)
    raise RuntimeError(f"UnrealMCP bridge did not become ready: {last_error}")


def require_success(name: str, response: dict) -> dict:
    if response.get("status") != "success":
        raise RuntimeError(f"{name} failed: {response}")
    return response.get("result") or {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=13377)
    parser.add_argument("--wait-seconds", type=int, default=240)
    parser.add_argument("--json-out")
    args = parser.parse_args()

    wait_for_bridge(args.host, args.port, args.wait_seconds)

    scene = require_success(
        "get_scene_info",
        send_command(args.host, args.port, "get_scene_info", {}, timeout=20),
    )
    if "actor_count" not in scene:
        raise RuntimeError(f"get_scene_info returned no actor_count: {scene}")

    marker = "UNREAL_MCP_NATIVE_BRIDGE_OK"
    python_result = None
    python_deadline = time.time() + args.wait_seconds
    last_python_error = None
    while time.time() < python_deadline:
        try:
            response = send_command(
                args.host,
                args.port,
                "execute_python",
                {"code": f"import unreal\nprint('{marker}')\nprint(unreal.SystemLibrary.get_engine_version())"},
                timeout=30,
            )
            if response.get("status") == "success":
                candidate = response.get("result") or {}
                if marker in str(candidate.get("output", "")):
                    python_result = candidate
                    break
            last_python_error = response
        except Exception as exc:
            last_python_error = exc
        time.sleep(2)

    if python_result is None:
        raise RuntimeError(f"Unreal Python did not become ready through MCP: {last_python_error}")

    python_output = str(python_result.get("output", ""))

    created = require_success(
        "create_object",
        send_command(
            args.host,
            args.port,
            "create_object",
            {
                "type": "Cube",
                "location": [123.0, 456.0, 789.0],
                "label": "UnrealMCP_NativeBridge_Smoke",
            },
            timeout=30,
        ),
    )
    actor_name = created.get("name")
    if not actor_name:
        raise RuntimeError(f"create_object returned no actor name: {created}")

    require_success(
        "delete_object",
        send_command(args.host, args.port, "delete_object", {"name": actor_name}, timeout=30),
    )

    if args.json_out:
        output_lines = [line.strip() for line in python_output.splitlines() if line.strip()]
        engine_version = next((line for line in output_lines if line != marker), None)
        payload = {
            "schema": 1,
            "passed": True,
            "engine_version": engine_version,
            "checks": [
                "get_scene_info",
                "execute_python",
                "create_object",
                "delete_object",
            ],
        }
        with open(args.json_out, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")

    print("UnrealMCP native TCP bridge smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
