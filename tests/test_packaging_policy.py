#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-only
"""Validate the Arch native-side-only packaging policy."""

from __future__ import annotations

import sys
from pathlib import Path

EXPECTED_EXTENSION_ID = "credentialsd-firefox-sidecar@plfjy.top"


def fail(message: str) -> "NoReturn":
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    if (root / "packaging/credentialsd-webextension-sidecar-git").exists():
        fail("retired split webextension package still exists")

    pkgbuild = root / "packaging/credentialsd-firefox-sidecar-git/PKGBUILD"
    if not pkgbuild.is_file():
        fail("all-in-one PKGBUILD missing")
    text = pkgbuild.read_text(encoding="utf-8")
    required_removals = (
        'rm -f "$pkgdir/usr/share/credentialsd/credentialsd-firefox-helper.xpi"',
        'rm -f "$pkgdir/usr/share/credentialsd/credentialsd-firefox-helper-unsigned.xpi"',
        'rm -f "$pkgdir/usr/share/credentialsd/credentialsd-chromium-helper.zip"',
    )
    for removal in required_removals:
        if removal not in text:
            fail(f"PKGBUILD missing archive cleanup: {removal}")
    if "*.xpi" not in text.replace("\\", "") or "*chromium*.zip" not in text.replace("\\", ""):
        fail("PKGBUILD does not assert browser archives are absent")
    if "return 1" not in text:
        fail("PKGBUILD does not fail on leftover browser archives")
    for forbidden in ("curl", "wget", "gh release download", "releases/latest/download"):
        if forbidden in text:
            fail(f"PKGBUILD downloads release artifacts using {forbidden!r}")

    native_manifest = root / "webext/app/credential_manager_shim.json.in"
    native_text = native_manifest.read_text(encoding="utf-8")
    if EXPECTED_EXTENSION_ID not in native_text:
        fail("Native Messaging manifest does not authorize the permanent extension ID")

    readme = root / "packaging/README.md"
    if not readme.is_file():
        fail("packaging/README.md missing")
    normalized = readme.read_text(encoding="utf-8").replace("**", "").lower()
    for phrase in (
        "credentialsd-firefox-sidecar-git",
        "github releases",
        "no supported arch package installs an xpi",
        "does not install the firefox extension",
    ):
        if phrase not in normalized:
            fail(f"packaging README missing policy phrase: {phrase!r}")

    print(
        f"OK: Arch packages remain native-side only and authorize {EXPECTED_EXTENSION_ID!r}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
