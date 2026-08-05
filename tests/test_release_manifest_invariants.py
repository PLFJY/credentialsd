#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-only
"""Release regression: Firefox manifest invariants and version format.

Asserts that ``webext/add-on/manifest.firefox.json`` declares:
  * gecko.id == credentialsd-sidecar@plfjy.top
  * gecko.update_url == https://github.com/PLFJY/credentialsd/releases/latest/download/updates.json
  * gecko.strict_min_version == 140.0
  * gecko.data_collection_permissions.required == [authenticationInfo,
    browsingActivity, websiteContent]
  * version is 1-4 dot-separated non-negative integer components; rejects
    'v1.0.0', '1.0.0-beta', '1.02.0', '01.0.0', '1..0'
  * content_scripts.matches == ['https://*/*'] (do not broaden)
  * permissions == ['nativeMessaging'] (do not add unrelated permissions)
  * data_collection_permissions.required does not contain 'none'

Also asserts that the Native Messaging manifest template
``webext/app/credential_manager_shim.json.in``:
  * declares allowed_extensions containing exactly the same ID
  * preserves the upstream Native Messaging host name
    ``xyz.iinuwa.credentialsd_helper``
  * preserves type == 'stdio'
  * preserves a non-empty path placeholder

Standalone: no build context required.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

EXPECTED_EXTENSION_ID = "credentialsd-sidecar@plfjy.top"
EXPECTED_UPDATE_URL = (
    "https://github.com/PLFJY/credentialsd/releases/latest/download/updates.json"
)
EXPECTED_STRICT_MIN_VERSION = "140.0"
EXPECTED_DATA_COLLECTION = [
    "authenticationInfo",
    "browsingActivity",
    "websiteContent",
]
EXPECTED_HOST_NAME = "xyz.iinuwa.credentialsd_helper"
VERSION_RE = re.compile(r"^(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*)){0,3}$")


def fail(msg: str) -> "NoReturn":
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    manifest_path = repo_root / "webext" / "add-on" / "manifest.firefox.json"
    nm_path = repo_root / "webext" / "app" / "credential_manager_shim.json.in"

    if not manifest_path.is_file():
        fail(f"missing Firefox manifest: {manifest_path}")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"Firefox manifest is not valid JSON: {exc}")

    gecko = manifest.get("browser_specific_settings", {}).get("gecko", {})
    if gecko.get("id") != EXPECTED_EXTENSION_ID:
        fail(f"gecko.id={gecko.get('id')!r} != expected {EXPECTED_EXTENSION_ID!r}")
    if gecko.get("update_url") != EXPECTED_UPDATE_URL:
        fail(
            f"gecko.update_url={gecko.get('update_url')!r} != expected "
            f"{EXPECTED_UPDATE_URL!r}"
        )
    if gecko.get("strict_min_version") != EXPECTED_STRICT_MIN_VERSION:
        fail(
            f"gecko.strict_min_version={gecko.get('strict_min_version')!r} != "
            f"expected {EXPECTED_STRICT_MIN_VERSION!r}"
        )

    dcp = gecko.get("data_collection_permissions")
    if not isinstance(dcp, dict):
        fail("gecko.data_collection_permissions is not an object")
    required = dcp.get("required")
    if not isinstance(required, list):
        fail("gecko.data_collection_permissions.required is not a list")
    if required != EXPECTED_DATA_COLLECTION:
        fail(
            f"gecko.data_collection_permissions.required={required!r} != "
            f"expected {EXPECTED_DATA_COLLECTION!r}"
        )
    if "none" in required:
        fail("gecko.data_collection_permissions.required contains 'none'")

    version = manifest.get("version", "")
    if not isinstance(version, str) or not VERSION_RE.match(version):
        fail(
            f"manifest.version={version!r} is not 1-4 dot-separated non-negative "
            f"integer components (reject 'v' prefix, suffixes, leading zeros, "
            f"empty components)"
        )

    content_scripts = manifest.get("content_scripts", [])
    if not isinstance(content_scripts, list) or not content_scripts:
        fail("manifest.content_scripts is missing or empty")
    for entry in content_scripts:
        matches = entry.get("matches") if isinstance(entry, dict) else None
        if matches != ["https://*/*"]:
            fail(
                f"content_scripts.matches={matches!r} must be exactly "
                f"['https://*/*']; do not broaden the match pattern"
            )

    permissions = manifest.get("permissions", [])
    if permissions != ["nativeMessaging"]:
        fail(
            f"manifest.permissions={permissions!r} must be exactly "
            f"['nativeMessaging']; do not add unrelated permissions"
        )

    # Native Messaging manifest template invariants.
    if not nm_path.is_file():
        fail(f"missing Native Messaging manifest template: {nm_path}")
    try:
        nm = json.loads(nm_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"Native Messaging manifest template is not valid JSON: {exc}")
    if nm.get("name") != EXPECTED_HOST_NAME:
        fail(f"nm.name={nm.get('name')!r} != expected {EXPECTED_HOST_NAME!r}")
    if nm.get("type") != "stdio":
        fail(f"nm.type={nm.get('type')!r} != 'stdio'")
    if not nm.get("path"):
        fail("nm.path is missing or empty")
    allowed = nm.get("allowed_extensions")
    if not isinstance(allowed, list) or allowed != [EXPECTED_EXTENSION_ID]:
        fail(
            f"nm.allowed_extensions={allowed!r} != expected "
            f"[{EXPECTED_EXTENSION_ID!r}]"
        )

    print(
        f"OK: manifest invariants verified (id, update_url, "
        f"strict_min_version, data_collection, version={version!r}, matches, "
        f"permissions, Native Messaging host name + allowed_extensions)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
