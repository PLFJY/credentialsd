#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-only
"""Generate and validate Firefox self-hosted updates.json."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import NoReturn
from urllib.parse import urlparse

EXPECTED_EXTENSION_ID = "credentialsd-firefox-sidecar@plfjy.top"
EXPECTED_REPOSITORY = "PLFJY/credentialsd"
VERSION_RE = re.compile(r"^(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*)){0,3}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def fail(message: str) -> NoReturn:
    print(f"generate-firefox-update-manifest: FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def build_update_link(repository: str, release_tag: str, xpi_filename: str) -> str:
    return f"https://github.com/{repository}/releases/download/{release_tag}/{xpi_filename}"


def validate(
    extension_id: str,
    version: str,
    release_tag: str,
    xpi_filename: str,
    xpi_sha256: str,
    repository: str,
) -> str:
    if extension_id != EXPECTED_EXTENSION_ID:
        fail(f"unexpected extension ID: {extension_id!r}")
    if not VERSION_RE.fullmatch(version):
        fail(f"invalid version: {version!r}")
    expected_tag = f"firefox-v{version}"
    if release_tag != expected_tag:
        fail(f"release tag {release_tag!r} != {expected_tag!r}")
    expected_xpi = f"credentialsd-sidecar-firefox-{version}.xpi"
    if xpi_filename != expected_xpi:
        fail(f"XPI filename {xpi_filename!r} != {expected_xpi!r}")
    if not SHA256_RE.fullmatch(xpi_sha256):
        fail("xpi-sha256 must be 64 lowercase hexadecimal characters")
    if repository != EXPECTED_REPOSITORY:
        fail(f"unexpected repository: {repository!r}")
    update_link = build_update_link(repository, release_tag, xpi_filename)
    parsed = urlparse(update_link)
    if parsed.scheme != "https" or not parsed.netloc:
        fail(f"update link is not a valid HTTPS URL: {update_link!r}")
    if "/releases/latest/" in update_link:
        fail("the XPI update_link must be versioned, not releases/latest")
    return update_link


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
    manifest = {
        "addons": {
            args.extension_id: {
                "updates": [
                    {
                        "version": args.version,
                        "update_link": update_link,
                        "update_hash": f"sha256:{args.xpi_sha256}",
                    }
                ]
            }
        }
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {output}")
    print(f"  extension_id: {args.extension_id}")
    print(f"  version:      {args.version}")
    print(f"  release_tag:  {args.release_tag}")
    print(f"  update_link:  {update_link}")
    print(f"  update_hash:  sha256:{args.xpi_sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
