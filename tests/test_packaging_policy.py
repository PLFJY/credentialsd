#!/usr/bin/env python3
"""Keep the Arch sidecar package isolated and reproducible."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKGBUILD = (ROOT / "packaging/credentialsd-firefox-sidecar-git/PKGBUILD").read_text()

assert "/home/plfjy" not in PKGBUILD
assert "git+https://github.com/PLFJY/credentialsd.git" in PKGBUILD
assert "io.github.PLFJY.CredentialPortal" in PKGBUILD
assert "-Dfirefox_portal_bus_name=io.github.PLFJY.CredentialPortal" in PKGBUILD
assert "-Dcargo_lto" not in PKGBUILD
assert "credentials-sidecar-portals.conf" in PKGBUILD
assert "credentials-portal-sidecar.service.d" in PKGBUILD
assert "*.xpi" in PKGBUILD
