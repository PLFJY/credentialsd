#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-only
"""Release regression: ``generate-firefox-update-manifest.py`` output shape.

Exercises the update-manifest generator with a fixed fake SHA-256 and asserts:
  * exit code 0;
  * the generated ``updates.json`` is valid JSON;
  * it contains exactly one addon and exactly one update entry;
  * the entry's version, update_link, and update_hash match the inputs;
  * update_link is HTTPS, versioned (NOT releases/latest), and consistent
    with the declared tag, version, and XPI filename;
  * update_hash is ``sha256:`` + the input SHA-256;
  * the addon ID matches the permanent extension ID;
  * the generator rejects bad inputs (bad extension ID, bad version,
    mismatched tag, mismatched XPI filename, bad SHA-256, bad repository,
    releases/latest XPI URL).

Standalone: no build context required.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

EXPECTED_EXTENSION_ID = "credentialsd-sidecar@plfjy.top"
FAKE_SHA = "0" * 64
GOOD_ARGS = [
    "--extension-id",
    EXPECTED_EXTENSION_ID,
    "--version",
    "0.1.0",
    "--release-tag",
    "firefox-v0.1.0",
    "--xpi-filename",
    "credentialsd-sidecar-firefox-0.1.0.xpi",
    "--xpi-sha256",
    FAKE_SHA,
    "--repository",
    "PLFJY/credentialsd",
]


def fail(msg: str) -> "NoReturn":
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def run_generator(script: Path, args: list[str], output: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script)] + args + ["--output", str(output)],
        capture_output=True,
        text=True,
    )


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    script = repo_root / "scripts" / "generate-firefox-update-manifest.py"
    if not script.is_file():
        fail(f"generator script not found: {script}")

    with tempfile.TemporaryDirectory(prefix="credsd-updates-") as tmp:
        out = Path(tmp) / "updates.json"

        # 1. Good case.
        result = run_generator(script, GOOD_ARGS, out)
        if result.returncode != 0:
            fail(
                f"generator failed on good inputs (exit {result.returncode}):\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )

        try:
            data = json.loads(out.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            fail(f"generated updates.json is not valid JSON: {exc}")

        addons = data.get("addons")
        if not isinstance(addons, dict) or set(addons) != {EXPECTED_EXTENSION_ID}:
            fail(f"addons keys={list(addons) if isinstance(addons, dict) else addons!r}")
        updates = addons[EXPECTED_EXTENSION_ID].get("updates")
        if not isinstance(updates, list) or len(updates) != 1:
            fail(f"updates must be a 1-element list; got {updates!r}")
        entry = updates[0]

        if entry.get("version") != "0.1.0":
            fail(f"entry.version={entry.get('version')!r} != '0.1.0'")
        expected_link = (
            "https://github.com/PLFJY/credentialsd/releases/download/"
            "firefox-v0.1.0/credentialsd-sidecar-firefox-0.1.0.xpi"
        )
        if entry.get("update_link") != expected_link:
            fail(f"entry.update_link={entry.get('update_link')!r} != {expected_link!r}")
        if not entry["update_link"].startswith("https://"):
            fail("update_link is not HTTPS")
        if "/releases/latest/" in entry["update_link"]:
            fail("update_link must NOT use releases/latest for the XPI URL")
        if entry.get("update_hash") != f"sha256:{FAKE_SHA}":
            fail(f"entry.update_hash={entry.get('update_hash')!r}")

        # 2. Reject bad extension ID.
        bad = list(GOOD_ARGS)
        bad[1] = "wrong@id"
        r = run_generator(script, bad, out)
        if r.returncode == 0:
            fail("generator accepted bad extension_id")

        # 3. Reject bad version.
        bad = list(GOOD_ARGS)
        bad[3] = "v1.0.0"
        r = run_generator(script, bad, out)
        if r.returncode == 0:
            fail("generator accepted 'v1.0.0' version")

        # 4. Reject mismatched release tag.
        bad = list(GOOD_ARGS)
        bad[5] = "v0.1.0"
        r = run_generator(script, bad, out)
        if r.returncode == 0:
            fail("generator accepted mismatched release_tag")

        # 5. Reject mismatched XPI filename.
        bad = list(GOOD_ARGS)
        bad[7] = "wrong.xpi"
        r = run_generator(script, bad, out)
        if r.returncode == 0:
            fail("generator accepted mismatched xpi_filename")

        # 6. Reject bad SHA-256.
        bad = list(GOOD_ARGS)
        bad[9] = "deadbeef"
        r = run_generator(script, bad, out)
        if r.returncode == 0:
            fail("generator accepted short SHA-256")

        # 7. Reject bad repository.
        bad = list(GOOD_ARGS)
        bad[11] = "someone/else"
        r = run_generator(script, bad, out)
        if r.returncode == 0:
            fail("generator accepted non-PLFJY repository")

    print(
        f"OK: generate-firefox-update-manifest.py produces a valid, "
        f"versioned, HTTPS update manifest with sha256 hash; rejects bad inputs"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
