#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-only
"""Release regression: signed XPI structural verification logic.

The publish workflow verifies each signed XPI before creating a GitHub
Release. The verification logic is duplicated here as a regression test so
that any change to the workflow's verification step is mirrored in the test
suite. If the two drift, the workflow is the source of truth; update this
test to match.

Asserts that the verification logic:
  * accepts a well-formed signed XPI containing manifest.json, META-INF/, and
    only the expected extension files;
  * rejects non-ZIP files;
  * rejects XPIs missing manifest.json;
  * rejects XPIs missing META-INF/ signing metadata;
  * rejects XPIs containing unexpected entries;
  * rejects XPIs whose manifest gecko.id != credentialsd-sidecar@plfjy.top;
  * rejects XPIs whose manifest version != expected version;
  * rejects XPIs whose manifest update_url is wrong;
  * rejects XPIs whose manifest strict_min_version is wrong.

Standalone: no build context required.
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import zipfile
from pathlib import Path

EXPECTED_EXTENSION_ID = "credentialsd-sidecar@plfjy.top"
EXPECTED_UPDATE_URL = (
    "https://github.com/PLFJY/credentialsd/releases/latest/download/updates.json"
)
EXPECTED_STRICT_MIN_VERSION = "140.0"
EXPECTED_EXTENSION_ENTRIES = {
    "manifest.json",
    "background.js",
    "content-bridge.js",
    "content-main.js",
    "icons/logo.svg",
}


def verify_signed_xpi(xpi_path: Path, expected_version: str) -> None:
    """Mirror of the publish workflow's signed-XPI verification step.

    Raises ``AssertionError`` (with a descriptive message) on any violation.
    Returns ``None`` on success.
    """
    assert xpi_path.is_file(), f"signed XPI not found: {xpi_path}"
    if not zipfile.is_zipfile(xpi_path):
        raise AssertionError("signed XPI is not a ZIP archive")

    with zipfile.ZipFile(xpi_path) as z:
        names = z.namelist()
        if "manifest.json" not in names:
            raise AssertionError("signed XPI missing manifest.json")
        if not any(n.startswith("META-INF/") for n in names):
            raise AssertionError("signed XPI missing META-INF/ signing metadata")

        unexpected = []
        for n in names:
            if n in EXPECTED_EXTENSION_ENTRIES:
                continue
            if n.startswith("META-INF/"):
                continue
            unexpected.append(n)
        if unexpected:
            raise AssertionError(
                f"signed XPI contains unexpected entries: {unexpected}"
            )

        with z.open("manifest.json") as f:
            manifest = json.load(f)

        gecko = manifest.get("browser_specific_settings", {}).get("gecko", {})
        if gecko.get("id") != EXPECTED_EXTENSION_ID:
            raise AssertionError(
                f"signed manifest gecko.id={gecko.get('id')!r} != "
                f"{EXPECTED_EXTENSION_ID!r}"
            )
        if manifest.get("version") != expected_version:
            raise AssertionError(
                f"signed manifest version={manifest.get('version')!r} != "
                f"{expected_version!r}"
            )
        if gecko.get("update_url") != EXPECTED_UPDATE_URL:
            raise AssertionError(
                f"signed manifest update_url={gecko.get('update_url')!r} != "
                f"{EXPECTED_UPDATE_URL!r}"
            )
        if gecko.get("strict_min_version") != EXPECTED_STRICT_MIN_VERSION:
            raise AssertionError(
                f"signed manifest strict_min_version="
                f"{gecko.get('strict_min_version')!r} != "
                f"{EXPECTED_STRICT_MIN_VERSION!r}"
            )


def fail(msg: str) -> "NoReturn":
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def make_manifest(
    ext_id: str = EXPECTED_EXTENSION_ID,
    version: str = "0.1.0",
    update_url: str = EXPECTED_UPDATE_URL,
    strict_min: str = EXPECTED_STRICT_MIN_VERSION,
) -> dict:
    return {
        "manifest_version": 3,
        "name": "credentialsd-helper",
        "version": version,
        "description": "test",
        "browser_specific_settings": {
            "gecko": {
                "id": ext_id,
                "strict_min_version": strict_min,
                "update_url": update_url,
                "data_collection_permissions": {
                    "required": [
                        "authenticationInfo",
                        "browsingActivity",
                        "websiteContent",
                    ]
                },
            }
        },
        "permissions": ["nativeMessaging"],
    }


def write_xpi(path: Path, entries: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in entries.items():
            z.writestr(name, data)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="credsd-xpi-") as tmp:
        tmp_path = Path(tmp)

        def good_entries() -> dict[str, bytes]:
            return {
                "manifest.json": json.dumps(make_manifest()).encode("utf-8"),
                "background.js": b"// bg",
                "content-bridge.js": b"// bridge",
                "content-main.js": b"// main",
                "icons/logo.svg": b"<svg/>",
                "META-INF/manifest.mf": b"Manifest-Version: 1.0\n",
                "META-INF/mozilla.sf": b"Signature-Version: 1.0\n",
                "META-INF/mozilla.rsa": b"\x00\x01\x02RSA",
            }

        # 1. Good XPI accepted.
        good = tmp_path / "good.xpi"
        write_xpi(good, good_entries())
        try:
            verify_signed_xpi(good, "0.1.0")
        except AssertionError as exc:
            fail(f"good XPI rejected: {exc}")

        # 2. Non-ZIP rejected.
        notzip = tmp_path / "notzip.xpi"
        notzip.write_bytes(b"not a zip")
        try:
            verify_signed_xpi(notzip, "0.1.0")
            fail("non-ZIP file was accepted")
        except AssertionError:
            pass

        # 3. Missing manifest.json rejected.
        e = good_entries()
        del e["manifest.json"]
        bad = tmp_path / "no-manifest.xpi"
        write_xpi(bad, e)
        try:
            verify_signed_xpi(bad, "0.1.0")
            fail("XPI missing manifest.json was accepted")
        except AssertionError:
            pass

        # 4. Missing META-INF/ rejected.
        e = good_entries()
        for k in list(e):
            if k.startswith("META-INF/"):
                del e[k]
        bad = tmp_path / "no-meta.xpi"
        write_xpi(bad, e)
        try:
            verify_signed_xpi(bad, "0.1.0")
            fail("XPI missing META-INF/ was accepted")
        except AssertionError:
            pass

        # 5. Unexpected entry rejected.
        e = good_entries()
        e["unexpected.txt"] = b"surprise"
        bad = tmp_path / "unexpected.xpi"
        write_xpi(bad, e)
        try:
            verify_signed_xpi(bad, "0.1.0")
            fail("XPI with unexpected entry was accepted")
        except AssertionError:
            pass

        # 6. Wrong extension ID rejected.
        e = good_entries()
        e["manifest.json"] = json.dumps(
            make_manifest(ext_id="wrong@id")
        ).encode("utf-8")
        bad = tmp_path / "wrong-id.xpi"
        write_xpi(bad, e)
        try:
            verify_signed_xpi(bad, "0.1.0")
            fail("XPI with wrong gecko.id was accepted")
        except AssertionError:
            pass

        # 7. Wrong version rejected.
        e = good_entries()
        e["manifest.json"] = json.dumps(
            make_manifest(version="9.9.9")
        ).encode("utf-8")
        bad = tmp_path / "wrong-ver.xpi"
        write_xpi(bad, e)
        try:
            verify_signed_xpi(bad, "0.1.0")
            fail("XPI with wrong version was accepted")
        except AssertionError:
            pass

        # 8. Wrong update_url rejected.
        e = good_entries()
        e["manifest.json"] = json.dumps(
            make_manifest(update_url="https://example.invalid/updates.json")
        ).encode("utf-8")
        bad = tmp_path / "wrong-url.xpi"
        write_xpi(bad, e)
        try:
            verify_signed_xpi(bad, "0.1.0")
            fail("XPI with wrong update_url was accepted")
        except AssertionError:
            pass

        # 9. Wrong strict_min_version rejected.
        e = good_entries()
        e["manifest.json"] = json.dumps(
            make_manifest(strict_min="100.0")
        ).encode("utf-8")
        bad = tmp_path / "wrong-min.xpi"
        write_xpi(bad, e)
        try:
            verify_signed_xpi(bad, "0.1.0")
            fail("XPI with wrong strict_min_version was accepted")
        except AssertionError:
            pass

    print(
        "OK: signed XPI structural verification logic accepts well-formed "
        "XPIs and rejects malformed/wrong-identity XPIs"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
