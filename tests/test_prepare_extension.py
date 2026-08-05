#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-only
"""Release regression: deterministic prepared extension file list.

Asserts that ``scripts/prepare-firefox-extension.py`` produces a deterministic
extension directory whose file list exactly matches the canonical set, and
that the prepared ``manifest.json`` carries the permanent extension ID,
update URL, Firefox minimum version, data collection permissions, and version
format declared in ``webext/add-on/manifest.firefox.json``.

Run with:
    python3 tests/test_prepare_extension.py [prepared-dir]

If ``prepared-dir`` is provided, the test inspects that directory. If not, the
test invokes the preparation script itself into a temporary directory and
inspects that.

Standalone: no build context required.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

EXPECTED_EXTENSION_ID = "credentialsd-sidecar@plfjy.top"
EXPECTED_UPDATE_URL = (
    "https://github.com/PLFJY/credentialsd/releases/latest/download/updates.json"
)
EXPECTED_STRICT_MIN_VERSION = "140.0"
EXPECTED_DATA_COLLECTION = [
    "authenticationInfo",
    "browsingActivity",
    "websiteContent",
]
EXPECTED_FILES = {
    "manifest.json",
    "background.js",
    "content-bridge.js",
    "content-main.js",
    "icons/logo.svg",
}
FORBIDDEN_FILES = {
    "manifest.chromium.json",
    "manifest.firefox.json",
    "credential_manager_shim.py",
    "credential_manager_shim.json.in",
    "credential_manager_shim.json",
    "PKGBUILD",
    "Cargo.lock",
    "Cargo.toml",
    ".git",
    ".gitignore",
}
VERSION_RE = re.compile(r"^(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*)){0,3}$")


def fail(msg: str) -> "NoReturn":
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def list_files(root: Path) -> set[str]:
    return {
        str(p.relative_to(root)).replace(os.sep, "/")
        for p in root.rglob("*")
        if p.is_file()
    }


def validate_prepared_dir(prepared: Path) -> None:
    if not prepared.is_dir():
        fail(f"prepared directory not found: {prepared}")

    files = list_files(prepared)

    # 1. Exact file set match.
    if files != EXPECTED_FILES:
        missing = EXPECTED_FILES - files
        extra = files - EXPECTED_FILES
        if missing:
            fail(f"prepared directory missing files: {sorted(missing)}")
        if extra:
            fail(
                f"prepared directory contains extra files: {sorted(extra)}; "
                f"the extension file list must be deterministic"
            )

    # 2. No forbidden files ever appear.
    intersection = files & FORBIDDEN_FILES
    if intersection:
        fail(
            f"prepared directory contains forbidden files: {sorted(intersection)}"
        )

    # 3. Manifest invariants.
    manifest_path = prepared / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"prepared manifest.json is not valid JSON: {exc}")

    gecko = manifest.get("browser_specific_settings", {}).get("gecko", {})
    if gecko.get("id") != EXPECTED_EXTENSION_ID:
        fail(
            f"prepared manifest gecko.id={gecko.get('id')!r} != expected "
            f"{EXPECTED_EXTENSION_ID!r}"
        )
    if gecko.get("update_url") != EXPECTED_UPDATE_URL:
        fail(
            f"prepared manifest gecko.update_url={gecko.get('update_url')!r} != "
            f"expected {EXPECTED_UPDATE_URL!r}"
        )
    if gecko.get("strict_min_version") != EXPECTED_STRICT_MIN_VERSION:
        fail(
            f"prepared manifest gecko.strict_min_version="
            f"{gecko.get('strict_min_version')!r} != expected "
            f"{EXPECTED_STRICT_MIN_VERSION!r}"
        )
    dcp = gecko.get("data_collection_permissions", {})
    if dcp.get("required") != EXPECTED_DATA_COLLECTION:
        fail(
            f"prepared manifest data_collection_permissions.required="
            f"{dcp.get('required')!r} != expected {EXPECTED_DATA_COLLECTION!r}"
        )

    version = manifest.get("version", "")
    if not isinstance(version, str) or not VERSION_RE.match(version):
        fail(
            f"prepared manifest.version={version!r} is not 1-4 dot-separated "
            f"non-negative integer components"
        )

    # 4. Match pattern and permissions invariants.
    for entry in manifest.get("content_scripts", []):
        if entry.get("matches") != ["https://*/*"]:
            fail(
                f"prepared content_scripts.matches={entry.get('matches')!r} must "
                f"be exactly ['https://*/*']"
            )
    if manifest.get("permissions") != ["nativeMessaging"]:
        fail(
            f"prepared permissions={manifest.get('permissions')!r} must be "
            f"exactly ['nativeMessaging']"
        )

    print(
        f"OK: prepared extension file list is deterministic; manifest "
        f"invariants verified (id={gecko['id']!r}, version={version!r})"
    )


def main(argv: list[str]) -> int:
    repo_root = Path(__file__).resolve().parent.parent
    script = repo_root / "scripts" / "prepare-firefox-extension.py"

    if len(argv) >= 2:
        validate_prepared_dir(Path(argv[1]))
        return 0

    if not script.is_file():
        fail(f"preparation script not found: {script}")

    with tempfile.TemporaryDirectory(prefix="credsd-prep-") as tmp:
        prepared = Path(tmp) / "prepared-extension"
        result = subprocess.run(
            [sys.executable, str(script), str(prepared)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            fail(
                f"preparation script failed (exit {result.returncode}):\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )
        validate_prepared_dir(prepared)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
