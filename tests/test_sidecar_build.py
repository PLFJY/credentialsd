#!/usr/bin/env python3
"""Check the generated helper's fixed D-Bus routing configuration."""

from __future__ import annotations

import sys
from pathlib import Path


def main(build_root: Path, expected_bus_name: str) -> None:
    shim = build_root / "webext" / "app" / "credentialsd-firefox-helper"
    content = shim.read_text(encoding="utf-8")
    assert "@PORTAL_BUS_NAME@" not in content
    assert content.count(f'PORTAL_BUS_NAME = "{expected_bus_name}"') == 1
    assert content.count("PORTAL_BUS_NAME,") == 2
    assert "os.getenv(\"PORTAL_BUS_NAME\")" not in content


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2])
