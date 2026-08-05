#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-only
"""Deterministic Firefox extension source preparation.

Copies the exact Firefox extension source set from ``webext/add-on/`` into an
output directory and validates the resulting ``manifest.json``. Used by local
validation, automated tests, the GitHub Actions signing job, and release
artifact preparation. Maintaining a single source of truth for the extension
file list avoids drift between temporary about:debugging loads, AMO signing,
and GitHub Releases.

The prepared directory is suitable for ``web-ext lint``, ``web-ext sign
--source-dir=<dir>``, and ``about:debugging`` temporary loads. It is NOT a
signed XPI; AMO signing is performed separately by the publish workflow.

Usage:
    prepare-firefox-extension.py <output-dir>

The output directory must be a non-empty, non-root, non-repository-root path.
The script deletes and recreates the directory safely.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path
from typing import NoReturn

# Permanent extension identity. Once the first AMO signing succeeds this value
# is immutable; AMO rejects reusing IDs across unrelated add-ons.
EXPECTED_EXTENSION_ID = "credentialsd-sidecar@plfjy.top"

# Stable update-manifest URL hosted on GitHub Releases. The XPI URL inside
# updates.json is the exact versioned Release asset URL, not this stable URL.
EXPECTED_UPDATE_URL = (
    "https://github.com/PLFJY/credentialsd/releases/latest/download/updates.json"
)

EXPECTED_STRICT_MIN_VERSION = "140.0"

# Mozilla AMO data_collection_permissions categories. The extension technically
# handles these data classes while intercepting WebAuthn operations on HTTPS
# pages; it does not transmit them to a PLFJY-operated remote service. See
# PRIVACY.md.
EXPECTED_DATA_COLLECTION = [
    "authenticationInfo",
    "browsingActivity",
    "websiteContent",
]

# Exact, ordered list of files copied from webext/add-on/ into the prepared
# extension directory. The manifest source is renamed to manifest.json. Do not
# add files to this list without updating tests and the privacy notice.
# Files deliberately excluded: .git, build directories, tests, logs,
# credentials, local configuration, PKGBUILD files, the Native Messaging
# executable, the Native Messaging manifest, release artifacts, node_modules,
# and any Chromium-only files (manifest.chromium.json).
EXTENSION_FILES = [
    ("manifest.firefox.json", "manifest.json"),
    ("background.js", "background.js"),
    ("content-bridge.js", "content-bridge.js"),
    ("content-main.js", "content-main.js"),
    ("icons/logo.svg", "icons/logo.svg"),
]

# Accepted version format: one to four dot-separated non-negative integer
# components. A zero component is exactly "0"; a non-zero component must not
# contain a leading zero. Rejects "v1.0.0", "1.0.0-beta", "1.02.0", "01.0.0",
# "1..0", etc.
VERSION_RE = re.compile(r"^(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*)){0,3}$")


def fail(msg: str) -> NoReturn:
    print(f"prepare-firefox-extension: FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def validate_output_path(output_dir: Path, repo_root: Path) -> None:
    """Refuse unsafe output paths.

    Reject empty, root, repository-root, parent-traversal, or suspicious
    paths. The output directory will be deleted and recreated, so a mistake
    here could destroy data.
    """
    if output_dir is None:
        fail("output directory argument is required")
    if not str(output_dir):
        fail("output directory is empty")

    resolved = output_dir.resolve()

    # Refuse the filesystem root.
    if resolved == resolved.parent:
        fail(f"refusing filesystem root as output directory: {resolved}")

    # Refuse the repository root.
    try:
        repo_resolved = repo_root.resolve()
    except FileNotFoundError:
        repo_resolved = repo_root
    if resolved == repo_resolved:
        fail(f"refusing repository root as output directory: {resolved}")

    # Refuse paths that traverse above the repository root via "..", and
    # refuse paths inside the webext/add-on source tree (which would shadow
    # the source files).
    try:
        add_on_resolved = (repo_root / "webext" / "add-on").resolve()
    except FileNotFoundError:
        add_on_resolved = repo_root / "webext" / "add-on"
    try:
        resolved.relative_to(add_on_resolved)
        fail(
            f"refusing output directory inside webext/add-on source tree: "
            f"{resolved}"
        )
    except ValueError:
        pass

    # Refuse the user's home directory.
    home = Path.home()
    try:
        home_resolved = home.resolve()
    except FileNotFoundError:
        home_resolved = home
    if resolved == home_resolved:
        fail(f"refusing home directory as output directory: {resolved}")

    # Refuse well-known dangerous absolute paths.
    dangerous = {"/", "/usr", "/etc", "/var", "/boot", "/dev", "/proc", "/sys"}
    if str(resolved) in dangerous:
        fail(f"refusing dangerous system path as output directory: {resolved}")


def validate_version(version: str) -> None:
    if not isinstance(version, str) or not version:
        fail("manifest version is missing or empty")
    if not VERSION_RE.match(version):
        fail(
            f"manifest version {version!r} is not 1-4 dot-separated non-negative "
            f"integer components (reject leading zeros, suffixes, 'v' prefixes)"
        )


def validate_manifest(manifest: dict) -> None:
    """Validate manifest fields used by signing, release, and update flow."""
    if not isinstance(manifest, dict):
        fail("manifest.json did not parse to a JSON object")

    gecko = (
        manifest.get("browser_specific_settings", {}).get("gecko", {})
        if isinstance(manifest.get("browser_specific_settings"), dict)
        else {}
    )
    if not isinstance(gecko, dict):
        fail("browser_specific_settings.gecko is not an object")

    ext_id = gecko.get("id")
    if ext_id != EXPECTED_EXTENSION_ID:
        fail(
            f"manifest gecko.id={ext_id!r} != expected {EXPECTED_EXTENSION_ID!r}"
        )

    update_url = gecko.get("update_url")
    if update_url != EXPECTED_UPDATE_URL:
        fail(
            f"manifest gecko.update_url={update_url!r} != expected "
            f"{EXPECTED_UPDATE_URL!r}"
        )

    strict_min = gecko.get("strict_min_version")
    if strict_min != EXPECTED_STRICT_MIN_VERSION:
        fail(
            f"manifest gecko.strict_min_version={strict_min!r} != expected "
            f"{EXPECTED_STRICT_MIN_VERSION!r}"
        )

    dcp = gecko.get("data_collection_permissions")
    if not isinstance(dcp, dict):
        fail("manifest gecko.data_collection_permissions is not an object")
    required = dcp.get("required")
    if not isinstance(required, list):
        fail("manifest gecko.data_collection_permissions.required is not a list")
    if required != EXPECTED_DATA_COLLECTION:
        fail(
            f"manifest gecko.data_collection_permissions.required={required!r} "
            f"!= expected {EXPECTED_DATA_COLLECTION!r}"
        )
    if "none" in required:
        fail(
            "manifest declares data_collection_permissions.required=['none']; "
            "this is not permitted"
        )

    validate_version(manifest.get("version", ""))

    # The match pattern must remain https://*/*; do not broaden it.
    content_scripts = manifest.get("content_scripts", [])
    if not isinstance(content_scripts, list) or not content_scripts:
        fail("manifest.content_scripts is missing or empty")
    for entry in content_scripts:
        matches = entry.get("matches") if isinstance(entry, dict) else None
        if matches != ["https://*/*"]:
            fail(
                f"manifest content_scripts.matches={matches!r} must be exactly "
                f"['https://*/*']; do not broaden the match pattern"
            )

    # The only permission must be nativeMessaging. Reject unrelated additions.
    permissions = manifest.get("permissions", [])
    if permissions != ["nativeMessaging"]:
        fail(
            f"manifest permissions={permissions!r} must be exactly "
            f"['nativeMessaging']; do not add unrelated permissions"
        )


def prepare(repo_root: Path, output_dir: Path) -> list[str]:
    """Delete and recreate output_dir, copy the extension file set, validate."""
    validate_output_path(output_dir, repo_root)

    add_on_dir = repo_root / "webext" / "add-on"

    # Verify all source files exist before deleting anything.
    for src_rel, _ in EXTENSION_FILES:
        src = add_on_dir / src_rel
        if not src.is_file():
            fail(f"required source file missing: {src}")

    # Delete and recreate the output directory.
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)

    copied: list[str] = []
    for src_rel, dst_rel in EXTENSION_FILES:
        src = add_on_dir / src_rel
        dst = output_dir / dst_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(dst_rel)

    manifest_path = output_dir / "manifest.json"
    try:
        manifest_text = manifest_path.read_text(encoding="utf-8")
    except OSError as exc:
        fail(f"could not read prepared manifest.json: {exc}")

    try:
        manifest = json.loads(manifest_text)
    except json.JSONDecodeError as exc:
        fail(f"prepared manifest.json is not valid JSON: {exc}")

    validate_manifest(manifest)

    return copied


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2

    output_dir = Path(argv[1])
    repo_root = Path(__file__).resolve().parent.parent

    copied = prepare(repo_root, output_dir)

    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    gecko = manifest["browser_specific_settings"]["gecko"]

    print("prepared extension ID:", gecko["id"])
    print("prepared extension version:", manifest["version"])
    print("output directory:", str(output_dir.resolve()))
    print("copied file list:")
    for name in copied:
        print(f"  - {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
