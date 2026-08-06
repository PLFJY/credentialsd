#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-only
"""Validate the Firefox updates.json generator."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

EXPECTED_EXTENSION_ID = "credentialsd-firefox-sidecar@plfjy.top"
VERSION = "0.1.1"
FAKE_SHA = "0" * 64


def fail(message: str) -> "NoReturn":
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    script = root / "scripts/generate-firefox-update-manifest.py"
    with tempfile.TemporaryDirectory(prefix="credentialsd-updates-") as temp:
        output = Path(temp) / "updates.json"
        command = [
            sys.executable,
            str(script),
            "--extension-id", EXPECTED_EXTENSION_ID,
            "--version", VERSION,
            "--release-tag", f"firefox-v{VERSION}",
            "--xpi-filename", f"credentialsd-sidecar-firefox-{VERSION}.xpi",
            "--xpi-sha256", FAKE_SHA,
            "--repository", "PLFJY/credentialsd",
            "--output", str(output),
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode:
            fail(f"generator failed:\n{result.stdout}\n{result.stderr}")
        data = json.loads(output.read_text(encoding="utf-8"))
        if set(data.get("addons", {})) != {EXPECTED_EXTENSION_ID}:
            fail("updates.json add-on ID mismatch")
        entry = data["addons"][EXPECTED_EXTENSION_ID]["updates"][0]
        expected_link = (
            f"https://github.com/PLFJY/credentialsd/releases/download/"
            f"firefox-v{VERSION}/credentialsd-sidecar-firefox-{VERSION}.xpi"
        )
        if entry != {
            "version": VERSION,
            "update_link": expected_link,
            "update_hash": f"sha256:{FAKE_SHA}",
        }:
            fail(f"unexpected update entry: {entry!r}")
        bad = list(command)
        bad[bad.index(EXPECTED_EXTENSION_ID)] = "wrong@id"
        if subprocess.run(bad, capture_output=True).returncode == 0:
            fail("generator accepted a wrong extension ID")
    print(f"OK: updates.json generator uses {EXPECTED_EXTENSION_ID!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
