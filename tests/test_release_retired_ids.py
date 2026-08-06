#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-only
"""Ensure retired Firefox extension IDs never return to active configuration."""

from __future__ import annotations

import sys
from pathlib import Path

RETIRED_IDS = (
    "credentialsd-helper@iinuwa.xyz",
    "credentialsd-sidecar@plfjy.github.io",
    "credentialsd-sidecar@plfjy.top",
)
ACTIVE_PATHS = (
    "webext/add-on/manifest.firefox.json",
    "webext/app/credential_manager_shim.json.in",
    "scripts/prepare-firefox-extension.py",
    "scripts/generate-firefox-update-manifest.py",
    ".github/workflows/release-firefox-extension.yml",
    "tests/test_release_id_consistency.py",
    "tests/test_release_manifest_invariants.py",
    "tests/test_prepare_extension.py",
    "tests/test_signed_xpi_structure.py",
    "tests/test_update_manifest_generator.py",
    "tests/test_shim_dest.py",
    "README.md",
    "SIDECAR-DEPLOY.md",
    "webext/README.md",
    "PRIVACY.md",
    "packaging/README.md",
    "packaging/credentialsd-firefox-sidecar-git/PKGBUILD",
)


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    failures: list[str] = []
    for relative in ACTIVE_PATHS:
        path = root / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for retired in RETIRED_IDS:
            if retired in text:
                failures.append(f"{relative}: contains retired ID {retired!r}")
    if failures:
        print("\n".join(f"FAIL: {failure}" for failure in failures), file=sys.stderr)
        return 1
    print(f"OK: retired IDs absent from active configuration: {RETIRED_IDS!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
