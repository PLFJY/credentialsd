#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-only
"""Validate deterministic prepared Firefox extension output."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

EXPECTED_EXTENSION_ID = "credentialsd-firefox-sidecar@plfjy.top"
EXPECTED_FILES = {
    "manifest.json",
    "background.js",
    "content-bridge.js",
    "content-main.js",
    "icons/logo.svg",
}


def fail(message: str) -> "NoReturn":
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def validate(path: Path) -> None:
    files = {
        str(item.relative_to(path)).replace(os.sep, "/")
        for item in path.rglob("*")
        if item.is_file()
    }
    if files != EXPECTED_FILES:
        fail(f"prepared file set mismatch: {sorted(files)!r}")
    manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    gecko = manifest.get("browser_specific_settings", {}).get("gecko", {})
    if gecko.get("id") != EXPECTED_EXTENSION_ID:
        fail(f"unexpected prepared extension ID: {gecko.get('id')!r}")
    print(f"OK: deterministic extension prepared for {EXPECTED_EXTENSION_ID!r}")


def main(argv: list[str]) -> int:
    root = Path(__file__).resolve().parent.parent
    if len(argv) > 1:
        validate(Path(argv[1]))
        return 0
    with tempfile.TemporaryDirectory(prefix="credentialsd-firefox-") as temp:
        output = Path(temp) / "prepared"
        result = subprocess.run(
            [sys.executable, str(root / "scripts/prepare-firefox-extension.py"), str(output)],
            capture_output=True,
            text=True,
        )
        if result.returncode:
            fail(f"prepare script failed:\n{result.stdout}\n{result.stderr}")
        validate(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
