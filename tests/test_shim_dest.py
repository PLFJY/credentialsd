#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-only
"""Phase 2 regression test: generated Native Messaging shim destinations.

Asserts that the meson-generated ``credentialsd-firefox-helper`` shim:
  * targets the build-time ``firefox_portal_bus_name`` for both the
    ``org.freedesktop.host.portal.Registry.Register`` message and the
    ``org.freedesktop.portal.experimental.Credential`` proxy object;
  * preserves the upstream object path ``/org/freedesktop/portal/desktop``;
  * preserves the upstream interface names;
  * contains no residual hard-coded ``org.freedesktop.portal.Desktop``
    unless that is the configured destination;

and that the Native Messaging manifest keeps the upstream host name and
extension ID regardless of the configured bus name.

Usage:
    test_shim_dest.py <build_dir> <expected_bus_name>
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SHIM_NAME = "credentialsd-firefox-helper"
MANIFEST_NAME = "xyz.iinuwa.credentialsd_helper.json"

EXPECTED_HOST_NAME = "xyz.iinuwa.credentialsd_helper"
EXPECTED_EXTENSION_ID = "credentialsd-helper@iinuwa.xyz"
EXPECTED_OBJECT_PATH = "/org/freedesktop/portal/desktop"
EXPECTED_REGISTRY_INTERFACE = "org.freedesktop.host.portal.Registry"
EXPECTED_CREDENTIAL_INTERFACE = "org.freedesktop.portal.experimental.Credential"
EXPECTED_REQUEST_INTERFACE = "org.freedesktop.portal.Request"

PORTAL_BUS_NAME_RE = re.compile(r'^PORTAL_BUS_NAME\s*=\s*"([^"]*)"\s*$', re.MULTILINE)


def fail(msg: str) -> "NoReturn":
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    build_dir = Path(argv[1])
    expected_bus_name = argv[2]

    shim_path = build_dir / "webext" / "app" / SHIM_NAME
    manifest_path = build_dir / "webext" / "app" / MANIFEST_NAME

    if not shim_path.is_file():
        fail(f"generated shim not found: {shim_path}")
    if not manifest_path.is_file():
        fail(f"generated manifest not found: {manifest_path}")

    shim = shim_path.read_text(encoding="utf-8")
    manifest_text = manifest_path.read_text(encoding="utf-8")

    # 1. PORTAL_BUS_NAME constant matches the configured option.
    m = PORTAL_BUS_NAME_RE.search(shim)
    if not m:
        fail("PORTAL_BUS_NAME constant not found in generated shim")
    actual_bus_name = m.group(1)
    if actual_bus_name != expected_bus_name:
        fail(
            f"PORTAL_BUS_NAME={actual_bus_name!r} != expected {expected_bus_name!r}"
        )

    # 2. The constant is used for both the Registry message destination and the
    #    Credential proxy object destination. We assert by locating the two
    #    call-sites that previously hard-coded the bus name.
    registry_block = (
        f'msg = Message(\n'
        f'        PORTAL_BUS_NAME,\n'
        f'        "{EXPECTED_OBJECT_PATH}",\n'
        f'        "{EXPECTED_REGISTRY_INTERFACE}",'
    )
    proxy_block = (
        f'proxy_object = bus.get_proxy_object(\n'
        f'        PORTAL_BUS_NAME,\n'
        f'        "{EXPECTED_OBJECT_PATH}",'
    )
    if registry_block not in shim:
        fail("Registry.Register message does not target PORTAL_BUS_NAME at the upstream object path")
    if proxy_block not in shim:
        fail("Credential proxy object does not target PORTAL_BUS_NAME at the upstream object path")

    # 3. No residual hard-coded org.freedesktop.portal.Desktop unless it is the
    #    configured destination.
    if expected_bus_name != "org.freedesktop.portal.Desktop":
        if "org.freedesktop.portal.Desktop" in shim:
            fail(
                "residual hard-coded 'org.freedesktop.portal.Desktop' present in "
                "generated shim despite sidecar bus name"
            )

    # 4. Object path and interface names are preserved.
    for expected in (
        EXPECTED_OBJECT_PATH,
        EXPECTED_REGISTRY_INTERFACE,
        EXPECTED_CREDENTIAL_INTERFACE,
        EXPECTED_REQUEST_INTERFACE,
    ):
        if expected not in shim:
            fail(f"expected identifier missing from generated shim: {expected}")

    # 5. Manifest consistency: host name and extension ID are unchanged.
    try:
        manifest = json.loads(manifest_text)
    except json.JSONDecodeError as exc:
        fail(f"manifest is not valid JSON: {exc}")
    if manifest.get("name") != EXPECTED_HOST_NAME:
        fail(f"manifest name={manifest.get('name')!r} != expected {EXPECTED_HOST_NAME!r}")
    if manifest.get("type") != "stdio":
        fail(f"manifest type={manifest.get('type')!r} != 'stdio'")
    allowed = manifest.get("allowed_extensions") or []
    if EXPECTED_EXTENSION_ID not in allowed:
        fail(f"manifest allowed_extensions missing {EXPECTED_EXTENSION_ID!r}: {allowed}")
    if "path" not in manifest or not manifest["path"]:
        fail("manifest missing non-empty 'path'")

    # 6. The shim must not accept the bus name from untrusted runtime input.
    #    Assert no env-var or argv read feeds PORTAL_BUS_NAME.
    for forbidden in (
        "os.environ",
        "sys.argv",
        "getenv(",
        "PORTAL_BUS_NAME = input",
        "PORTAL_BUS_NAME = sys",
    ):
        if forbidden in shim:
            fail(f"shim appears to read runtime input near PORTAL_BUS_NAME: {forbidden!r}")

    print(
        f"OK: shim targets {actual_bus_name!r}; "
        f"manifest host={manifest['name']!r}, ext={EXPECTED_EXTENSION_ID!r}; "
        f"object path + interfaces preserved."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
