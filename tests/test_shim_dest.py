#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-only
"""Validate generated Native Messaging shim destination and manifest identity."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

EXPECTED_EXTENSION_ID = "credentialsd-firefox-sidecar@plfjy.top"
EXPECTED_HOST_NAME = "xyz.iinuwa.credentialsd_helper"
EXPECTED_OBJECT_PATH = "/org/freedesktop/portal/desktop"
EXPECTED_IDENTIFIERS = (
    "org.freedesktop.host.portal.Registry",
    "org.freedesktop.portal.experimental.Credential",
    "org.freedesktop.portal.Request",
)
BUS_RE = re.compile(r'^PORTAL_BUS_NAME\s*=\s*"([^"]*)"\s*$', re.MULTILINE)


def fail(message: str) -> "NoReturn":
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: test_shim_dest.py <build-dir> <expected-bus-name>", file=sys.stderr)
        return 2
    build = Path(argv[1])
    expected_bus = argv[2]
    shim_path = build / "webext/app/credentialsd-firefox-helper"
    manifest_path = build / "webext/app/xyz.iinuwa.credentialsd_helper.json"
    if not shim_path.is_file() or not manifest_path.is_file():
        fail("generated shim or Native Messaging manifest missing")
    shim = shim_path.read_text(encoding="utf-8")
    match = BUS_RE.search(shim)
    if not match or match.group(1) != expected_bus:
        fail(f"generated PORTAL_BUS_NAME does not match {expected_bus!r}")
    if EXPECTED_OBJECT_PATH not in shim:
        fail("portal object path changed")
    for identifier in EXPECTED_IDENTIFIERS:
        if identifier not in shim:
            fail(f"generated shim missing {identifier!r}")
    if expected_bus != "org.freedesktop.portal.Desktop" and "org.freedesktop.portal.Desktop" in shim:
        fail("sidecar shim retains a hard-coded standard portal bus")
    for forbidden in ("os.environ", "sys.argv", "getenv("):
        if forbidden in shim:
            fail(f"shim reads portal destination from runtime input: {forbidden}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("name") != EXPECTED_HOST_NAME or manifest.get("type") != "stdio":
        fail("Native Messaging host invariants changed")
    if manifest.get("allowed_extensions") != [EXPECTED_EXTENSION_ID]:
        fail(f"Native Messaging ID mismatch: {manifest.get('allowed_extensions')!r}")
    if not manifest.get("path"):
        fail("Native Messaging executable path missing")
    print(f"OK: shim targets {expected_bus!r} and authorizes {EXPECTED_EXTENSION_ID!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
