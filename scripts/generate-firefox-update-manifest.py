#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-only
"""Generate a versioned self-hosted Firefox update manifest."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

EXTENSION_ID = "credentialsd-firefox-sidecar@plfjy.top"
VERSION_RE = re.compile(r"^(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*)){0,3}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if not VERSION_RE.fullmatch(args.version):
        raise SystemExit("invalid extension version")
    if not SHA256_RE.fullmatch(args.sha256):
        raise SystemExit("invalid SHA-256")
    tag = f"firefox-v{args.version}"
    filename = f"credentialsd-sidecar-firefox-{args.version}.xpi"
    link = f"https://github.com/PLFJY/credentialsd/releases/download/{tag}/{filename}"
    data = {"addons": {EXTENSION_ID: {"updates": [{
        "version": args.version, "update_link": link, "update_hash": f"sha256:{args.sha256}",
    }]}}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
