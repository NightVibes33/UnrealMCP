#!/usr/bin/env python3
"""Watch official Epic Unreal documentation for version/content changes."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

USER_AGENT = "UnrealMCP-docs-watcher/1.0 (+https://github.com/NightVibes33/UnrealMCP)"
VERSION_RE = re.compile(r"\bUnreal(?:\s+Engine)?\s+(\d+\.\d+)\b", re.IGNORECASE)
URL_VERSION_RE = re.compile(r"unreal-engine-(\d+)-(\d+)", re.IGNORECASE)


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignored = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self._ignored += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"} and self._ignored:
            self._ignored -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignored:
            text = " ".join(data.split())
            if text:
                self.parts.append(text)


def version_key(value: str) -> tuple[int, ...]:
    return tuple(int(part) for part in value.split("."))


def normalize_document(raw: bytes, content_type: str) -> tuple[str, list[str]]:
    decoded = raw.decode("utf-8", errors="replace")

    if "html" in content_type.lower() or "<html" in decoded[:1000].lower():
        parser = TextExtractor()
        parser.feed(decoded)
        text = "\n".join(parser.parts)
    else:
        text = html.unescape(decoded)

    text = re.sub(r"\s+", " ", text).strip()
    versions = set(VERSION_RE.findall(text))
    # Epic links encode versions as unreal-engine-5-8-..., so include those too.
    # Ignore obviously implausible values to avoid script/sidebar noise becoming a fake release.
    for major, minor in URL_VERSION_RE.findall(decoded):
        if int(major) <= 20 and int(minor) <= 99:
            versions.add(f"{major}.{minor}")
    return text, sorted(versions, key=version_key)


def fetch(url: str, timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read(12 * 1024 * 1024)
        content_type = response.headers.get("Content-Type", "")
        normalized, versions = normalize_document(raw, content_type)
        return {
            "url": response.geturl(),
            "sha256": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
            "normalized_bytes": len(normalized.encode("utf-8")),
            "versions": versions,
            "etag": response.headers.get("ETag"),
            "last_modified": response.headers.get("Last-Modified"),
        }


def load_state(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def emit_output(name: str, value: str) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as handle:
            handle.write(f"{name}={value}\n")
    print(f"{name}={value}")


def write_report(
    path: Path,
    old_state: dict[str, Any],
    new_state: dict[str, Any],
    changed_sources: list[str],
    version_changed: bool,
    baseline: bool,
) -> None:
    lines = [
        "# Epic documentation change report",
        "",
        f"- Checked: {new_state['last_change_utc']}",
        f"- Previous Unreal docs version: {old_state.get('latest_version') or 'unknown'}",
        f"- Latest observed Unreal docs version: {new_state.get('latest_version') or 'unknown'}",
        f"- Engine-version change: {'yes' if version_changed else 'no'}",
        f"- Initial watcher baseline: {'yes' if baseline else 'no'}",
        "",
        "## Changed sources",
        "",
    ]
    for name in changed_sources:
        source = new_state["sources"][name]
        lines.append(f"- **{name}** — {source['url']}")
    lines.extend(
        [
            "",
            "## Update policy",
            "",
            "Documentation metadata can be updated automatically. A newly observed Unreal "
            "version is not treated as proof of binary compatibility: the self-hosted Unreal "
            "validation workflow must compile the plugin and run the live API smoke test before "
            "version-specific implementation changes can be auto-merged.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", default="compat/epic-docs.json")
    parser.add_argument("--report", default="compat/reports/epic-docs-change.md")
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    state_path = Path(args.state)
    report_path = Path(args.report)
    old_state = load_state(state_path)
    sources = old_state.get("sources") or {}
    if not sources:
        raise RuntimeError("No Epic documentation sources configured")

    new_sources: dict[str, Any] = {}
    all_versions: set[str] = set()
    changed_sources: list[str] = []

    for name, configured in sources.items():
        observed = fetch(str(configured["url"]), args.timeout)
        merged = {**configured, **observed}
        new_sources[name] = merged
        all_versions.update(observed.get("versions") or [])
        if configured.get("sha256") != observed.get("sha256"):
            changed_sources.append(name)

    latest = max(all_versions, key=version_key) if all_versions else old_state.get("latest_version")

    # When a new version appears on What's New, automatically move the tracked
    # release-notes source to that version if Epic has published the page.
    if latest:
        release_name = "release_notes"
        release_slug = latest.replace(".", "-")
        desired_release_url = (
            "https://dev.epicgames.com/documentation/en-us/unreal-engine/"
            f"unreal-engine-{release_slug}-release-notes"
        )
        current_release = new_sources.get(release_name) or {}
        if release_slug not in str(current_release.get("url", "")):
            try:
                observed_release = fetch(desired_release_url, args.timeout)
                previous_release_hash = (sources.get(release_name) or {}).get("sha256")
                new_sources[release_name] = {
                    **(sources.get(release_name) or {}),
                    **observed_release,
                }
                if previous_release_hash != observed_release.get("sha256") and release_name not in changed_sources:
                    changed_sources.append(release_name)
            except Exception as exc:
                print(
                    f"Warning: detected Unreal {latest}, but release notes are not reachable yet: {exc}",
                    file=sys.stderr,
                )

    old_latest = old_state.get("latest_version")
    baseline = not bool(old_state.get("initialized"))
    version_changed = bool(old_latest and latest and old_latest != latest)
    changed = baseline or version_changed or bool(changed_sources)

    emit_output("changed", str(changed).lower())
    emit_output("engine_version_changed", str(version_changed).lower())
    emit_output("baseline_initialized", str(baseline).lower())
    emit_output("latest_version", str(latest or ""))

    if not changed:
        print("No Epic documentation changes detected.")
        return 0

    new_state = {
        "schema": 1,
        "initialized": True,
        "latest_version": latest,
        "last_change_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "sources": new_sources,
    }
    state_path.write_text(json.dumps(new_state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report_path, old_state, new_state, changed_sources, version_changed, baseline)

    print(
        json.dumps(
            {
                "changed_sources": changed_sources,
                "latest_version": latest,
                "version_changed": version_changed,
                "baseline": baseline,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
