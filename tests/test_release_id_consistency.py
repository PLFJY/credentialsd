#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-only
"""Verify Firefox and Native Messaging extension IDs are identical."""

from __future__ import annotations

import json
import sys
from pathlib import Path

EXPECTED_EXTENSION_ID = "credentialsd-firefox-sidecar@plfjy.top"


def fail(message: str) -> "NoReturn":
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    manifest = json.loads(
        (root / "webext/add-on/manifest.firefox.json").read_text(encoding="utf-8")
    )
    native = json.loads(
        (root / "webext/app/credential_manager_shim.json.in").read_text(encoding="utf-8")
    )
    extension_id = manifest.get("browser_specific_settings", {}).get("gecko", {}).get("id")
    allowed = native.get("allowed_extensions")
    if extension_id != EXPECTED_EXTENSION_ID:
        fail(f"manifest ID {extension_id!r} != {EXPECTED_EXTENSION_ID!r}")
    if allowed != [EXPECTED_EXTENSION_ID]:
        fail(f"allowed_extensions {allowed!r} != [{EXPECTED_EXTENSION_ID!r}]")
    print(f"OK: Firefox and Native Messaging IDs are {EXPECTED_EXTENSION_ID!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
