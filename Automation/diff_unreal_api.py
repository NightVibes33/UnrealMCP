#!/usr/bin/env python3
"""Diff two Unreal Python API snapshots and classify breaking changes."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def repo_references(repo_root: Path) -> str:
    chunks = []
    for root in (repo_root / "MCP" / "Commands", repo_root / "Source" / "UnrealMCP"):
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.suffix.lower() not in {".py", ".cpp", ".h", ".cs"}:
                continue
            try:
                chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
            except OSError:
                pass
    return "\n".join(chunks)


def diff_snapshots(old: dict[str, Any], new: dict[str, Any], source_text: str) -> dict[str, Any]:
    old_symbols = old.get("symbols") or {}
    new_symbols = new.get("symbols") or {}
    old_names = set(old_symbols)
    new_names = set(new_symbols)

    added_symbols = sorted(new_names - old_names)
    removed_symbols = sorted(old_names - new_names)
    changed_signatures = []
    removed_members = []
    added_members = []

    for name in sorted(old_names & new_names):
        old_entry = old_symbols[name] or {}
        new_entry = new_symbols[name] or {}
        if old_entry.get("signature") and new_entry.get("signature") and old_entry.get("signature") != new_entry.get("signature"):
            changed_signatures.append(
                {
                    "symbol": name,
                    "before": old_entry.get("signature"),
                    "after": new_entry.get("signature"),
                }
            )

        old_members = old_entry.get("members") or {}
        new_members = new_entry.get("members") or {}
        old_member_names = set(old_members)
        new_member_names = set(new_members)

        for member in sorted(old_member_names - new_member_names):
            removed_members.append(f"{name}.{member}")
        for member in sorted(new_member_names - old_member_names):
            added_members.append(f"{name}.{member}")
        for member in sorted(old_member_names & new_member_names):
            before = (old_members[member] or {}).get("signature")
            after = (new_members[member] or {}).get("signature")
            if before and after and before != after:
                changed_signatures.append(
                    {
                        "symbol": f"{name}.{member}",
                        "before": before,
                        "after": after,
                    }
                )

    breaking_keys = removed_symbols + removed_members + [item["symbol"] for item in changed_signatures]
    referenced_breaking = []
    for key in breaking_keys:
        parts = key.split(".")
        tokens = [re.escape(parts[0])]
        if len(parts) > 1:
            tokens.append(re.escape(parts[-1]))
        if any(re.search(rf"\b{token}\b", source_text) for token in tokens):
            referenced_breaking.append(key)

    return {
        "schema": 1,
        "from_engine": old.get("engine_version"),
        "to_engine": new.get("engine_version"),
        "added_symbols": added_symbols,
        "removed_symbols": removed_symbols,
        "added_members": added_members,
        "removed_members": removed_members,
        "changed_signatures": changed_signatures,
        "breaking_count": len(breaking_keys),
        "referenced_breaking": sorted(set(referenced_breaking)),
        "safe_for_automatic_compatibility_merge": not referenced_breaking,
    }


def write_markdown(path: Path, diff: dict[str, Any]) -> None:
    def section(title: str, values: list[Any], limit: int = 250):
        lines.append(f"## {title}")
        lines.append("")
        if not values:
            lines.append("_None._")
        else:
            for value in values[:limit]:
                if isinstance(value, dict):
                    lines.append(
                        f"- `{value['symbol']}`: `{value.get('before')}` → `{value.get('after')}`"
                    )
                else:
                    lines.append(f"- `{value}`")
            if len(values) > limit:
                lines.append(f"- …and {len(values) - limit} more")
        lines.append("")

    lines = [
        "# Unreal Python API compatibility diff",
        "",
        f"- From: `{diff.get('from_engine')}`",
        f"- To: `{diff.get('to_engine')}`",
        f"- Breaking API changes detected: **{diff.get('breaking_count', 0)}**",
        f"- Breaking changes referenced by UnrealMCP source: **{len(diff.get('referenced_breaking') or [])}**",
        f"- Automatic compatibility merge eligible: **{diff.get('safe_for_automatic_compatibility_merge')}**",
        "",
    ]
    section("Referenced breaking changes", diff.get("referenced_breaking") or [])
    section("Removed top-level symbols", diff.get("removed_symbols") or [])
    section("Removed members", diff.get("removed_members") or [])
    section("Changed signatures", diff.get("changed_signatures") or [])
    section("Added top-level symbols", diff.get("added_symbols") or [])
    section("Added members", diff.get("added_members") or [])

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("old")
    parser.add_argument("new")
    parser.add_argument("--json-out", required=True)
    parser.add_argument("--markdown-out", required=True)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--fail-on-referenced-breaking", action="store_true")
    args = parser.parse_args()

    old = load(Path(args.old))
    new = load(Path(args.new))
    source_text = repo_references(Path(args.repo_root))
    result = diff_snapshots(old, new, source_text)

    json_out = Path(args.json_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(Path(args.markdown_out), result)

    print(json.dumps(result, indent=2))
    if args.fail_on_referenced_breaking and result["referenced_breaking"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
