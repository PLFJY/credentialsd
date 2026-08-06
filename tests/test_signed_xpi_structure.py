#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-only
"""Regression tests for signed Firefox XPI structural validation."""

from __future__ import annotations

import json
import sys
import tempfile
import zipfile
from pathlib import Path

EXPECTED_EXTENSION_ID = "credentialsd-firefox-sidecar@plfjy.top"
EXPECTED_UPDATE_URL = "https://github.com/PLFJY/credentialsd/releases/latest/download/updates.json"
EXPECTED_FILES = {
    "manifest.json",
    "background.js",
    "content-bridge.js",
    "content-main.js",
    "icons/logo.svg",
}


def verify(path: Path, version: str) -> None:
    if not zipfile.is_zipfile(path):
        raise AssertionError("not a ZIP archive")
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if "manifest.json" not in names:
            raise AssertionError("manifest.json missing")
        if not any(name.startswith("META-INF/") for name in names):
            raise AssertionError("META-INF signing metadata missing")
        unexpected = [
            name for name in names
            if name not in EXPECTED_FILES and not name.startswith("META-INF/")
        ]
        if unexpected:
            raise AssertionError(f"unexpected entries: {unexpected!r}")
        manifest = json.loads(archive.read("manifest.json"))
    gecko = manifest.get("browser_specific_settings", {}).get("gecko", {})
    if gecko.get("id") != EXPECTED_EXTENSION_ID:
        raise AssertionError("wrong extension ID")
    if manifest.get("version") != version:
        raise AssertionError("wrong version")
    if gecko.get("update_url") != EXPECTED_UPDATE_URL:
        raise AssertionError("wrong update_url")
    if gecko.get("strict_min_version") != "140.0":
        raise AssertionError("wrong strict_min_version")


def manifest(extension_id: str = EXPECTED_EXTENSION_ID, version: str = "0.1.1") -> dict:
    return {
        "manifest_version": 3,
        "name": "credentialsd-helper",
        "version": version,
        "browser_specific_settings": {
            "gecko": {
                "id": extension_id,
                "strict_min_version": "140.0",
                "update_url": EXPECTED_UPDATE_URL,
            }
        },
    }


def write_xpi(path: Path, extension_manifest: dict, *, signed: bool = True) -> None:
    entries = {
        "manifest.json": json.dumps(extension_manifest).encode(),
        "background.js": b"",
        "content-bridge.js": b"",
        "content-main.js": b"",
        "icons/logo.svg": b"<svg/>",
    }
    if signed:
        entries["META-INF/manifest.mf"] = b"Manifest-Version: 1.0\n"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in entries.items():
            archive.writestr(name, content)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="credentialsd-xpi-") as temp:
        root = Path(temp)
        good = root / "good.xpi"
        write_xpi(good, manifest())
        verify(good, "0.1.1")

        wrong_id = root / "wrong-id.xpi"
        write_xpi(wrong_id, manifest("wrong@id"))
        try:
            verify(wrong_id, "0.1.1")
        except AssertionError:
            pass
        else:
            raise SystemExit("FAIL: wrong extension ID accepted")

        unsigned = root / "unsigned.xpi"
        write_xpi(unsigned, manifest(), signed=False)
        try:
            verify(unsigned, "0.1.1")
        except AssertionError:
            pass
        else:
            raise SystemExit("FAIL: unsigned XPI accepted")

    print(f"OK: signed XPI validation uses {EXPECTED_EXTENSION_ID!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
