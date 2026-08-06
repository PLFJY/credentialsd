#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-only
"""Prepare and validate the deterministic Firefox extension source tree."""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path
from typing import NoReturn

EXPECTED_EXTENSION_ID = "credentialsd-firefox-sidecar@plfjy.top"
EXPECTED_UPDATE_URL = (
    "https://github.com/PLFJY/credentialsd/releases/latest/download/updates.json"
)
EXPECTED_STRICT_MIN_VERSION = "140.0"
EXPECTED_DATA_COLLECTION = [
    "authenticationInfo",
    "browsingActivity",
    "websiteContent",
]
EXTENSION_FILES = [
    ("manifest.firefox.json", "manifest.json"),
    ("background.js", "background.js"),
    ("content-bridge.js", "content-bridge.js"),
    ("content-main.js", "content-main.js"),
    ("icons/logo.svg", "icons/logo.svg"),
]
VERSION_RE = re.compile(r"^(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*)){0,3}$")


def fail(message: str) -> NoReturn:
    print(f"prepare-firefox-extension: FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def validate_output_path(output_dir: Path, repo_root: Path) -> Path:
    resolved = output_dir.expanduser().resolve()
    repo = repo_root.resolve()
    addon = (repo / "webext" / "add-on").resolve()
    home = Path.home().resolve()
    dangerous = {
        Path("/"), Path("/usr"), Path("/etc"), Path("/var"), Path("/boot"),
        Path("/dev"), Path("/proc"), Path("/sys"), home, repo,
    }
    if resolved in dangerous:
        fail(f"refusing dangerous output directory: {resolved}")
    try:
        resolved.relative_to(addon)
    except ValueError:
        pass
    else:
        fail(f"refusing output directory inside extension source: {resolved}")
    return resolved


def validate_manifest(manifest: object) -> dict:
    if not isinstance(manifest, dict):
        fail("manifest.json must contain a JSON object")
    gecko = manifest.get("browser_specific_settings", {}).get("gecko", {})
    if not isinstance(gecko, dict):
        fail("browser_specific_settings.gecko must be an object")
    if gecko.get("id") != EXPECTED_EXTENSION_ID:
        fail(f"unexpected extension ID: {gecko.get('id')!r}")
    if gecko.get("update_url") != EXPECTED_UPDATE_URL:
        fail(f"unexpected update_url: {gecko.get('update_url')!r}")
    if gecko.get("strict_min_version") != EXPECTED_STRICT_MIN_VERSION:
        fail(f"unexpected strict_min_version: {gecko.get('strict_min_version')!r}")
    required = gecko.get("data_collection_permissions", {}).get("required")
    if required != EXPECTED_DATA_COLLECTION:
        fail(f"unexpected data_collection_permissions.required: {required!r}")
    version = manifest.get("version")
    if not isinstance(version, str) or not VERSION_RE.fullmatch(version):
        fail(f"invalid extension version: {version!r}")
    if manifest.get("permissions") != ["nativeMessaging"]:
        fail("Firefox permissions must be exactly ['nativeMessaging']")
    content_scripts = manifest.get("content_scripts")
    if not isinstance(content_scripts, list) or not content_scripts:
        fail("content_scripts must be a non-empty list")
    for entry in content_scripts:
        if not isinstance(entry, dict) or entry.get("matches") != ["https://*/*"]:
            fail("each Firefox content script must match exactly https://*/*")
    return manifest


def prepare(repo_root: Path, output_dir: Path) -> list[str]:
    output = validate_output_path(output_dir, repo_root)
    source = repo_root / "webext" / "add-on"
    for source_name, _ in EXTENSION_FILES:
        if not (source / source_name).is_file():
            fail(f"missing extension source file: {source / source_name}")
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    copied: list[str] = []
    for source_name, destination_name in EXTENSION_FILES:
        destination = output / destination_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / source_name, destination)
        copied.append(destination_name)
    try:
        manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"invalid prepared manifest.json: {error}")
    validate_manifest(manifest)
    return copied


def main(argv: list[str]) -> int:
    if len(argv) != 2 or not argv[1].strip():
        print("usage: prepare-firefox-extension.py <output-dir>", file=sys.stderr)
        return 2
    repo_root = Path(__file__).resolve().parent.parent
    output = Path(argv[1])
    copied = prepare(repo_root, output)
    manifest = json.loads((output.resolve() / "manifest.json").read_text(encoding="utf-8"))
    gecko = manifest["browser_specific_settings"]["gecko"]
    print(f"prepared extension ID: {gecko['id']}")
    print(f"prepared extension version: {manifest['version']}")
    print(f"output directory: {output.resolve()}")
    print("copied file list:")
    for name in copied:
        print(f"  - {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
