#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-only
"""Validate Firefox manifest and Native Messaging release invariants."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

EXPECTED_EXTENSION_ID = "credentialsd-firefox-sidecar@plfjy.top"
EXPECTED_UPDATE_URL = "https://github.com/PLFJY/credentialsd/releases/latest/download/updates.json"
EXPECTED_DATA_COLLECTION = ["authenticationInfo", "browsingActivity", "websiteContent"]
VERSION_RE = re.compile(r"^(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*)){0,3}$")


def fail(message: str) -> "NoReturn":
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    manifest = json.loads((root / "webext/add-on/manifest.firefox.json").read_text(encoding="utf-8"))
    native = json.loads((root / "webext/app/credential_manager_shim.json.in").read_text(encoding="utf-8"))
    gecko = manifest.get("browser_specific_settings", {}).get("gecko", {})
    if gecko.get("id") != EXPECTED_EXTENSION_ID:
        fail(f"unexpected gecko.id: {gecko.get('id')!r}")
    if gecko.get("update_url") != EXPECTED_UPDATE_URL:
        fail(f"unexpected update_url: {gecko.get('update_url')!r}")
    if gecko.get("strict_min_version") != "140.0":
        fail(f"unexpected strict_min_version: {gecko.get('strict_min_version')!r}")
    if gecko.get("data_collection_permissions", {}).get("required") != EXPECTED_DATA_COLLECTION:
        fail("unexpected data_collection_permissions.required")
    version = manifest.get("version")
    if not isinstance(version, str) or not VERSION_RE.fullmatch(version):
        fail(f"invalid manifest version: {version!r}")
    if manifest.get("permissions") != ["nativeMessaging"]:
        fail("permissions must be exactly ['nativeMessaging']")
    scripts = manifest.get("content_scripts")
    if not isinstance(scripts, list) or not scripts:
        fail("content_scripts must be a non-empty list")
    if any(entry.get("matches") != ["https://*/*"] for entry in scripts if isinstance(entry, dict)):
        fail("content script matches must be exactly ['https://*/*']")
    if native.get("name") != "xyz.iinuwa.credentialsd_helper":
        fail("Native Messaging host name changed")
    if native.get("type") != "stdio" or not native.get("path"):
        fail("Native Messaging type/path invalid")
    if native.get("allowed_extensions") != [EXPECTED_EXTENSION_ID]:
        fail("Native Messaging allowed_extensions mismatch")
    print(f"OK: release manifest invariants verified for {EXPECTED_EXTENSION_ID!r}, version={version!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
