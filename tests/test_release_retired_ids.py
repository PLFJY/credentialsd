#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-only
"""Release regression: retired extension IDs must not be present.

Asserts that retired IDs:
  * ``credentialsd-helper@iinuwa.xyz``
  * ``credentialsd-sidecar@plfjy.github.io``

do not appear in active Firefox packaging or release configuration. Historical
references in upstream commit history are out of scope.

Inspects:
  * webext/add-on/manifest.firefox.json
  * webext/app/credential_manager_shim.json.in
  * packaging/credentialsd-firefox-sidecar-git/PKGBUILD
  * packaging/README.md
  * packaging/credentialsd-git/PKGBUILD
  * packaging/xdg-credential-portal-sidecar-git/PKGBUILD
  * .github/workflows/release-firefox-extension.yml
  * SIDECAR-DEPLOY.md
  * webext/README.md
  * PRIVACY.md

Standalone: no build context required. Run with ``python3 tests/test_release_retired_ids.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

RETIRED_IDS = (
    "credentialsd-helper@iinuwa.xyz",
    "credentialsd-sidecar@plfjy.github.io",
)

INSPECT_PATHS = (
    "webext/add-on/manifest.firefox.json",
    "webext/add-on/manifest.chromium.json",
    "webext/app/credential_manager_shim.json.in",
    "packaging/credentialsd-firefox-sidecar-git/PKGBUILD",
    "packaging/credentialsd-git/PKGBUILD",
    "packaging/xdg-credential-portal-sidecar-git/PKGBUILD",
    "packaging/README.md",
    ".github/workflows/release-firefox-extension.yml",
    "SIDECAR-DEPLOY.md",
    "webext/README.md",
    "PRIVACY.md",
)


def fail(msg: str) -> "NoReturn":
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    failures: list[str] = []

    for rel in INSPECT_PATHS:
        path = repo_root / rel
        if not path.is_file():
            # Skip silently if the file has been removed in a future refactor;
            # presence of the retired IDs is what matters.
            continue
        text = path.read_text(encoding="utf-8")
        for retired in RETIRED_IDS:
            if retired in text:
                failures.append(f"{rel}: contains retired ID {retired!r}")

    if failures:
        for f in failures:
            print(f"FAIL: {f}", file=sys.stderr)
        sys.exit(1)

    print(
        f"OK: retired IDs {RETIRED_IDS} absent from active Firefox packaging "
        f"and release configuration"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
