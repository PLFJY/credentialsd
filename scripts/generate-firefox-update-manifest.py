#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-only
"""Generate a Firefox update manifest (``updates.json``) for a signed Release.

Produces the JSON document Firefox fetches from the stable URL
``releases/latest/download/updates.json``. The ``update_link`` inside the
document is the exact versioned Release asset URL (NOT a ``releases/latest``
XPI URL), so Firefox always downloads the specific signed XPI that matches
the declared ``update_hash``.

Inputs are passed as named arguments and validated together:

    --extension-id      credentialsd-sidecar@plfjy.top
    --version           manifest version (e.g. 0.1.0)
    --release-tag       firefox-v${VERSION}
    --xpi-filename      credentialsd-sidecar-firefox-${VERSION}.xpi
    --xpi-sha256        lowercase hex SHA-256 of the signed XPI
    --repository        PLFJY/credentialsd
    --output            path to write updates.json

JSON is produced with ``json.dumps``; no shell concatenation is used.

The generator only emits the latest release entry. Older entries are not
preserved here; Firefox only needs the latest entry to discover updates.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import NoReturn
from urllib.parse import urlparse

EXPECTED_EXTENSION_ID = "credentialsd-sidecar@plfjy.top"
EXPECTED_REPOSITORY = "PLFJY/credentialsd"

VERSION_RE = re.compile(r"^(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*)){0,3}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def fail(msg: str) -> NoReturn:
    print(f"generate-firefox-update-manifest: FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def assert_https(url: str, label: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        fail(f"{label} is not HTTPS: {url!r}")
    if not parsed.netloc:
        fail(f"{label} has no host: {url!r}")


def build_update_link(repository: str, release_tag: str, xpi_filename: str) -> str:
    return (
        f"https://github.com/{repository}/releases/download/"
        f"{release_tag}/{xpi_filename}"
    )


def validate(
    extension_id: str,
    version: str,
    release_tag: str,
    xpi_filename: str,
    xpi_sha256: str,
    repository: str,
) -> str:
    if extension_id != EXPECTED_EXTENSION_ID:
        fail(
            f"extension_id={extension_id!r} != expected {EXPECTED_EXTENSION_ID!r}"
        )

    if not VERSION_RE.match(version):
        fail(f"version {version!r} is not a valid 1-4 component dotted version")

    expected_tag = f"firefox-v{version}"
    if release_tag != expected_tag:
        fail(
            f"release_tag={release_tag!r} != expected firefox-v{version!r}"
        )

    expected_xpi = f"credentialsd-sidecar-firefox-{version}.xpi"
    if xpi_filename != expected_xpi:
        fail(
            f"xpi_filename={xpi_filename!r} != expected {expected_xpi!r}"
        )

    if not SHA256_RE.match(xpi_sha256):
        fail(
            f"xpi_sha256 must be 64 lowercase hex digits; got {xpi_sha256!r}"
        )

    if repository != EXPECTED_REPOSITORY:
        fail(
            f"repository={repository!r} != expected {EXPECTED_REPOSITORY!r}"
        )

    update_link = build_update_link(repository, release_tag, xpi_filename)
    assert_https(update_link, "update_link")

    # The XPI URL must NOT be a releases/latest URL; only the updates.json
    # stable URL is latest-based.
    if "/releases/latest/" in update_link:
        fail(
            f"update_link must use the exact versioned Release URL, not "
            f"releases/latest: {update_link!r}"
        )

    return update_link


def build_manifest(
    extension_id: str,
    version: str,
    update_link: str,
    xpi_sha256: str,
) -> dict:
    return {
        "addons": {
            extension_id: {
                "updates": [
                    {
                        "version": version,
                        "update_link": update_link,
                        "update_hash": f"sha256:{xpi_sha256}",
                    }
                ]
            }
        }
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extension-id", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--release-tag", required=True)
    parser.add_argument("--xpi-filename", required=True)
    parser.add_argument("--xpi-sha256", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv[1:])

    update_link = validate(
        args.extension_id,
        args.version,
        args.release_tag,
        args.xpi_filename,
        args.xpi_sha256,
        args.repository,
    )

    manifest = build_manifest(
        args.extension_id,
        args.version,
        update_link,
        args.xpi_sha256,
    )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    print(f"wrote {output}")
    print(f"  extension_id: {args.extension_id}")
    print(f"  version:      {args.version}")
    print(f"  release_tag:  {args.release_tag}")
    print(f"  update_link:  {update_link}")
    print(f"  update_hash:  sha256:{args.xpi_sha256}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
