#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-only
"""Prepare the signed Firefox-sidecar extension from the current source."""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

EXTENSION_ID = "credentialsd-firefox-sidecar@plfjy.top"
UPDATE_URL = "https://github.com/PLFJY/credentialsd/releases/latest/download/updates.json"
FILES = {
    "manifest.firefox.json": "manifest.json",
    "background.js": "background.js",
    "content-bridge.js": "content-bridge.js",
    "content-main.js": "content-main.js",
    "icons/logo.svg": "icons/logo.svg",
}
VERSION_RE = re.compile(r"^(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*)){0,3}$")


def fail(message: str) -> None:
    raise SystemExit(f"prepare-firefox-extension: FAIL: {message}")


def validate_manifest(manifest: object) -> dict:
    if not isinstance(manifest, dict):
        fail("manifest must be an object")
    gecko = manifest.get("browser_specific_settings", {}).get("gecko", {})
    if gecko.get("id") != EXTENSION_ID:
        fail("unexpected extension ID")
    if gecko.get("update_url") != UPDATE_URL:
        fail("unexpected update URL")
    if gecko.get("strict_min_version") != "140.0":
        fail("Firefox 140+ is required")
    if gecko.get("data_collection_permissions", {}).get("required") != [
        "authenticationInfo", "browsingActivity", "websiteContent",
    ]:
        fail("unexpected data collection declaration")
    if not isinstance(manifest.get("version"), str) or not VERSION_RE.fullmatch(manifest["version"]):
        fail("invalid version")
    if manifest.get("permissions") != ["nativeMessaging"]:
        fail("unexpected permissions")
    if manifest.get("background", {}).get("service_worker") != "background.js":
        fail("current service-worker architecture is required")
    scripts = manifest.get("content_scripts")
    if not isinstance(scripts, list) or len(scripts) != 2:
        fail("expected both current content-script worlds")
    if any(item.get("matches") != ["<all_urls>"] for item in scripts if isinstance(item, dict)):
        fail("content scripts must cover all URLs")
    return manifest


def prepare(repo_root: Path, output: Path) -> None:
    source = repo_root / "webext" / "add-on"
    if output.resolve() in {Path("/"), repo_root.resolve(), source.resolve()}:
        fail("refusing dangerous output path")
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    for source_name, destination_name in FILES.items():
        target = output / destination_name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / source_name, target)
    validate_manifest(json.loads((output / "manifest.json").read_text(encoding="utf-8")))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: prepare-firefox-extension.py OUTPUT_DIR")
    prepare(Path(__file__).resolve().parent.parent, Path(sys.argv[1]))
