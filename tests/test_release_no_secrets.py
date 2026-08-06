#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-only
"""Release regression: no literal AMO credentials or GitHub PATs in repository.

Asserts that no tracked source file contains literal AMO JWT issuer/secret
values, GitHub PATs, or other credential patterns that would indicate a leaked
secret. The publish workflow supplies AMO credentials only through Environment
secrets scoped to ``amo-signing``; they must never be checked in.

Inspects every text file under the repository except:
  * .git/
  * build directories (build/, target/, */build/, */target/)
  * node_modules/
  * Cargo.lock (opaque hashes can false-positive)
  * this test file itself (it contains the patterns as test fixtures)

This is a heuristic, not a cryptographic secret scanner. It catches the
common accident of pasting a JWT or token into a config file.

Standalone: no build context required.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Heuristic patterns. These are deliberately conservative to avoid
# false-positives from base64-encoded binary blobs in Cargo.lock.
#
# AMO JWT issuer is a numeric string (Mozilla API key). AMO JWT secret is a
# 32+ character base64-ish string. GitHub PATs (classic) start with 'ghp_';
# fine-grained PATs start with 'github_pat_'; OAuth tokens start with 'gho_';
# refresh tokens start with 'ghr_'; app tokens start with 'ghu_'.
PATTERNS = (
    re.compile(r"\bghp_[A-Za-z0-9]{36,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgho_[A-Za-z0-9]{36,}\b"),
    re.compile(r"\bghr_[A-Za-z0-9]{36,}\b"),
    re.compile(r"\bghu_[A-Za-z0-9]{36,}\b"),
    # AMO JWTs are three base64url segments separated by dots. The header is
    # short, the payload is short, the signature is ~43 chars. Require a
    # realistic JWT shape.
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{30,}\b"),
)

# Variable-name references in workflow YAML are fine; only literal values
# matching the patterns above are flagged.

SKIP_DIRS = {".git", "build", "target", "node_modules", "__pycache__", ".venv"}
SKIP_FILES = {"Cargo.lock", "test_release_no_secrets.py"}

# Files where the literal secret names (AMO_JWT_ISSUER etc.) appear as
# variable references and are EXPECTED. This test does not flag the names;
# it only flags literal credential VALUES.

MAX_FILE_BYTES = 1_500_000  # skip files larger than ~1.5MB to avoid OOM


def fail(msg: str) -> "NoReturn":
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def iter_text_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.name in SKIP_FILES:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        try:
            st = path.stat()
        except OSError:
            continue
        if st.st_size > MAX_FILE_BYTES:
            continue
        # Read as bytes and try to decode utf-8; skip binary files.
        try:
            data = path.read_bytes()
            text = data.decode("utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        yield path, text


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    hits: list[str] = []

    for path, text in iter_text_files(repo_root):
        rel = path.relative_to(repo_root)
        for pat in PATTERNS:
            for m in pat.finditer(text):
                preview = m.group(0)[:8] + "..."
                hits.append(f"{rel}: matches {pat.pattern[:40]}... ({preview})")

    if hits:
        for h in hits:
            print(f"FAIL: {h}", file=sys.stderr)
        sys.exit(1)

    print("OK: no literal AMO credentials or GitHub PATs detected in repository")
    return 0


if __name__ == "__main__":
    sys.exit(main())
