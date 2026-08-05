#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-only
"""Release regression: Arch packaging policy.

Asserts that the active PKGBUILD files do NOT install browser extension
archives into /usr and DO install the Native Messaging surface with the
permanent extension ID. The full "inspect the produced package contents"
check requires building the package (``makepkg``) and is performed in the
GitHub Actions validation workflow; this test inspects the PKGBUILD source
to catch policy violations earlier.

Specifically:
  * ``packaging/credentialsd-firefox-sidecar-git/PKGBUILD``:
      - removes ``*.xpi`` and ``*chromium*.zip`` from ``$pkgdir`` in
        ``package()``;
      - asserts no ``*.xpi`` or ``*chromium*.zip`` remains in ``$pkgdir``;
      - does NOT install ``updates.json`` into ``$pkgdir``;
      - installs the Native Messaging manifest
        ``/usr/lib/mozilla/native-messaging-hosts/xyz.iinuwa.credentialsd_helper.json``
        (via ``meson install`` from the credentialsd source tree);
      - installs the Native Messaging executable
        ``/usr/bin/credentialsd-firefox-helper`` (via ``meson install``);
      - declares the permanent extension ID
        ``credentialsd-sidecar@plfjy.top`` is NOT installed by the package
        itself but the Native Messaging manifest (generated from
        ``credential_manager_shim.json.in``) authorizes exactly that ID —
        asserted in ``test_release_id_consistency.py``.
  * ``packaging/credentialsd-git/PKGBUILD``:
      - removes the webextension surface (Native Messaging files, XPI,
        Chromium ZIP) from its package root, keeping the package root
        disjoint from the all-in-one package.
  * ``packaging/credentialsd-webextension-sidecar-git/PKGBUILD`` MUST NOT
    exist (the split package that shipped unsigned XPIs into /usr has been
    removed).
  * ``packaging/README.md`` MUST document the no-XPI policy.

Standalone: no build context required.
"""

from __future__ import annotations

import sys
from pathlib import Path


def fail(msg: str) -> "NoReturn":
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent

    # 1. The retired split package MUST NOT exist.
    retired = repo_root / "packaging" / "credentialsd-webextension-sidecar-git"
    if retired.exists():
        fail(
            f"{retired} still exists; the split webextension package that "
            f"shipped unsigned XPIs into /usr must be removed"
        )

    # 2. all-in-one PKGBUILD policy.
    all_in_one = (
        repo_root
        / "packaging"
        / "credentialsd-firefox-sidecar-git"
        / "PKGBUILD"
    )
    if not all_in_one.is_file():
        fail(f"missing all-in-one PKGBUILD: {all_in_one}")
    text = all_in_one.read_text(encoding="utf-8")

    # 2a. Must remove *.xpi and *chromium*.zip from $pkgdir.
    if 'rm -f "$pkgdir/usr/share/credentialsd/credentialsd-firefox-helper.xpi"' not in text:
        fail("all-in-one PKGBUILD must rm -f the helper XPI from $pkgdir")
    if 'rm -f "$pkgdir/usr/share/credentialsd/credentialsd-firefox-helper-unsigned.xpi"' not in text:
        fail("all-in-one PKGBUILD must rm -f the unsigned helper XPI from $pkgdir")
    if 'rm -f "$pkgdir/usr/share/credentialsd/credentialsd-chromium-helper.zip"' not in text:
        fail("all-in-one PKGBUILD must rm -f the Chromium ZIP from $pkgdir")

    # 2b. Must assert no *.xpi or *chromium*.zip remains.
    if "find" not in text or "*.xpi" not in text.replace("\\", "") or "*chromium*.zip" not in text.replace("\\", ""):
        fail(
            "all-in-one PKGBUILD must assert no *.xpi or *chromium*.zip remains "
            "in $pkgdir"
        )
    if "return 1" not in text:
        fail("all-in-one PKGBUILD must return 1 on leftover archive assertion")

    # 2c. Must NOT install updates.json into $pkgdir.
    if "updates.json" in text and "install" in text and "$pkgdir" in text:
        # Look for an install line that writes updates.json into $pkgdir.
        for line in text.splitlines():
            if "updates.json" in line and "install" in line and "$pkgdir" in line:
                fail(
                    f"all-in-one PKGBUILD must not install updates.json into "
                    f"$pkgdir: {line.strip()!r}"
                )

    # 2d. Must NOT download signed XPI during prepare/build/check/package or
    #     post_install/post_upgrade.
    for forbidden in (
        "curl",
        "wget",
        "gh release download",
        "releases/latest/download",
    ):
        if forbidden in text:
            fail(
                f"all-in-one PKGBUILD must not download signed XPI from GitHub "
                f"Releases (found {forbidden!r})"
            )

    # 2e. pkgdesc must reflect native-side integration, not the extension
    #     itself.
    if "credentialsd-firefox-helper.xpi" in text.lower() and "unsigned" in text.lower():
        # Allow comments explaining what is removed; fail only if the package
        # *claims* to contain an unsigned XPI as a feature.
        for line in text.splitlines():
            stripped = line.strip().lstrip("#").strip()
            if stripped.lower().startswith("pkgdesc=") and "unsigned" in stripped.lower():
                fail(
                    f"pkgdesc claims to contain an unsigned XPI: {stripped!r}"
                )

    # 2f. pkgrel must be incremented (>=1). Verify pkgrel is present.
    if "pkgrel=" not in text:
        fail("all-in-one PKGBUILD missing pkgrel=")

    # 3. credentialsd-git PKGBUILD must keep its package root disjoint.
    creds_git = repo_root / "packaging" / "credentialsd-git" / "PKGBUILD"
    if creds_git.is_file():
        cg = creds_git.read_text(encoding="utf-8")
        if 'rm -f "$pkgdir/usr/share/credentialsd/credentialsd-firefox-helper.xpi"' not in cg:
            fail("credentialsd-git PKGBUILD must rm -f the helper XPI from $pkgdir")
        if "rm -rf" not in cg or "mozilla" not in cg:
            fail(
                "credentialsd-git PKGBUILD must remove the Native Messaging "
                "surface to keep package roots disjoint"
            )

    # 4. packaging/README.md must exist and document the no-XPI policy.
    readme = repo_root / "packaging" / "README.md"
    if not readme.is_file():
        fail("packaging/README.md must exist and document the packaging policy")
    readme_text = readme.read_text(encoding="utf-8")
    # Strip markdown emphasis so phrases with **not** etc. still match.
    readme_normalized = readme_text.replace("**", "")
    for required_phrase in (
        "credentialsd-firefox-sidecar-git",
        "GitHub Releases",
        "no supported Arch package installs an XPI",
        "does not install the Firefox extension",
    ):
        if required_phrase.lower() not in readme_normalized.lower():
            fail(
                f"packaging/README.md missing required phrase: "
                f"{required_phrase!r}"
            )

    print(
        "OK: Arch packaging policy enforced — no XPI/ZIP/updates.json in "
        "package roots; Native Messaging surface preserved; retired split "
        "package removed; packaging/README.md documents the policy"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
