#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-only
"""Release regression: extension ID and Native Messaging ID consistency.

Asserts that:
  * the Firefox manifest declares the permanent extension ID
    ``credentialsd-sidecar@plfjy.top``;
  * the Native Messaging manifest template authorizes exactly the same ID;
  * the two IDs are byte-for-byte identical.

The two IDs must always be identical. AMO treats the manifest gecko.id as
immutable once the first signing succeeds; mismatched IDs would silently break
Native Messaging after a signed install.

Standalone: no build context required. Run with ``python3 tests/test_release_id_consistency.py``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

EXPECTED_EXTENSION_ID = "credentialsd-sidecar@plfjy.top"


def fail(msg: str) -> "NoReturn":
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    manifest_path = repo_root / "webext" / "add-on" / "manifest.firefox.json"
    nm_path = repo_root / "webext" / "app" / "credential_manager_shim.json.in"

    if not manifest_path.is_file():
        fail(f"missing Firefox manifest: {manifest_path}")
    if not nm_path.is_file():
        fail(f"missing Native Messaging manifest template: {nm_path}")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"Firefox manifest is not valid JSON: {exc}")

    gecko = manifest.get("browser_specific_settings", {}).get("gecko", {})
    ext_id = gecko.get("id")
    if ext_id != EXPECTED_EXTENSION_ID:
        fail(
            f"manifest gecko.id={ext_id!r} != expected {EXPECTED_EXTENSION_ID!r}"
        )

    try:
        nm = json.loads(nm_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"Native Messaging manifest template is not valid JSON: {exc}")

    allowed = nm.get("allowed_extensions")
    if not isinstance(allowed, list):
        fail(f"allowed_extensions is not a list: {allowed!r}")
    if len(allowed) != 1:
        fail(
            f"allowed_extensions must contain exactly one entry; got {allowed!r}"
        )
    if allowed[0] != EXPECTED_EXTENSION_ID:
        fail(
            f"allowed_extensions[0]={allowed[0]!r} != expected "
            f"{EXPECTED_EXTENSION_ID!r}"
        )

    if allowed[0] != ext_id:
        fail(
            f"manifest ID {ext_id!r} != Native Messaging ID {allowed[0]!r}; "
            f"the two IDs must be identical"
        )

    print(
        f"OK: extension ID and Native Messaging allowed_extensions are both "
        f"{EXPECTED_EXTENSION_ID!r}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
