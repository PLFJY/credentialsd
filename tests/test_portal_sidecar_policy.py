#!/usr/bin/env python3
"""Keep sidecar portal selection isolated from desktop portal policy."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
portal = (ROOT / "portal/credentialsd.portal").read_text()
selection = (ROOT / "portal/credentials-sidecar-portals.conf").read_text()
dropin = (ROOT / "systemd/credentials-portal-sidecar.service.d/credentials-sidecar.conf").read_text()

assert "UseIn=credentials-sidecar;" in portal
assert "org.freedesktop.impl.portal.experimental.Credential=credentialsd" in selection
assert "XDG_CURRENT_DESKTOP=credentials-sidecar" in dropin
assert "XDG_DESKTOP_PORTAL_ENABLE_EXPERIMENTAL=credential" in dropin
assert "xdg-desktop-portal.service.d" not in (ROOT / "systemd/meson.build").read_text()
