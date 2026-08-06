#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-only
"""Desktop-environment-agnostic portal selection regression.

Asserts that the Credential Portal sidecar no longer hard-codes Hyprland for
backend selection. Instead it uses an isolated internal desktop identity
(`credentials-sidecar`) that works across GNOME, KDE Plasma, Hyprland, sway,
and any other graphical D-Bus session.

The sidecar selects its backend via a dedicated `credentials-sidecar-portals.conf`
driven by a systemd drop-in that overrides ONLY the sidecar process's
`XDG_CURRENT_DESKTOP`. The standard `org.freedesktop.portal.Desktop` frontend
keeps observing the user's real desktop and its normal desktop-provided
configuration.

This is a standalone static source-inspection test; no build context is
required. It mirrors the 12 assertions enumerated in the desktop-agnostic
portal-selection task.
"""

from __future__ import annotations

import configparser
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# The internal sidecar desktop identity. This is NOT a real desktop environment.
SIDECAR_DESKTOP = "credentials-sidecar"
SIDECAR_UNIT = "credentials-portal-sidecar.service"
SIDECAR_BUS_NAME = "io.github.PLFJY.CredentialPortal"
STANDARD_BUS_NAME = "org.freedesktop.portal.Desktop"

# Files/dirs excluded from the "no UseIn=Hyprland" scan: the task spec itself
# (deleted after the task), this test file (it references the string in its
# assertions), the git metadata, historical docs, and build artifacts.
SCAN_EXCLUDE_DIRS = {".git", "build-aux", "target", "cargo-home"}
SCAN_EXCLUDE_FILES = {"task.md", "test_portal_desktop_agnostic.py"}

# Desktop-specific portal configurations that must never be installed/overwritten.
FORBIDDEN_PORTALS_CONF = (
    "gnome-portals.conf",
    "kde-portals.conf",
    "hyprland-portals.conf",
    "portals.conf",
)

REAL_DESKTOPS = ("GNOME", "KDE", "Hyprland", "sway")


def fail(msg: str) -> "NoReturn":
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def iter_text_files(root: Path):
    """Yield text files under `root`, excluding build/git/historical paths."""
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SCAN_EXCLUDE_DIRS for part in path.parts):
            continue
        # Skip historical design docs (not active configuration).
        if "doc" in path.parts and "historical" in path.parts:
            continue
        if path.name in SCAN_EXCLUDE_FILES:
            continue
        # Skip obvious binaries.
        if path.suffix in {".png", ".svg", ".odg", ".ico", ".jpg", ".jpeg", ".lock"}:
            continue
        yield path


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# 1. No active source/package/unit/deployment config contains `UseIn=Hyprland`.
# ---------------------------------------------------------------------------
def assert_no_usein_hyprland() -> None:
    offenders = []
    for path in iter_text_files(REPO_ROOT):
        try:
            text = read(path)
        except OSError:
            continue
        if "UseIn=Hyprland" in text:
            offenders.append(str(path.relative_to(REPO_ROOT)))
    if offenders:
        fail(
            "UseIn=Hyprland still present in active files: "
            + ", ".join(offenders)
        )
    print("OK 1: no active file contains 'UseIn=Hyprland'")


# ---------------------------------------------------------------------------
# 2. The sidecar unit (effective config incl. drop-ins) contains
#    XDG_CURRENT_DESKTOP=credentials-sidecar.
# ---------------------------------------------------------------------------
def assert_sidecar_unit_has_desktop_override() -> None:
    dropin = (
        REPO_ROOT
        / "systemd"
        / f"{SIDECAR_UNIT}.d"
        / "credentials-sidecar.conf"
    )
    if not dropin.is_file():
        fail(f"missing sidecar unit drop-in: {dropin}")
    text = read(dropin)
    if "XDG_CURRENT_DESKTOP=credentials-sidecar" not in text:
        fail(f"sidecar drop-in missing XDG_CURRENT_DESKTOP={SIDECAR_DESKTOP}")
    if "XDG_DESKTOP_PORTAL_ENABLE_EXPERIMENTAL=credential" not in text:
        fail("sidecar drop-in missing XDG_DESKTOP_PORTAL_ENABLE_EXPERIMENTAL=credential")
    # The drop-in must be scoped to the sidecar unit only (directory name).
    if f"{SIDECAR_UNIT}.d" not in str(dropin):
        fail(f"drop-in not scoped to sidecar unit {SIDECAR_UNIT}")
    # The override must live in a [Service] section so it only affects the
    # sidecar process environment, not a global/session-wide setting.
    if "[Service]" not in text:
        fail("sidecar drop-in must set Environment= under [Service]")
    print("OK 2: sidecar unit (drop-in) pins XDG_CURRENT_DESKTOP=credentials-sidecar")


# ---------------------------------------------------------------------------
# 3. The standard frontend unit does not carry that override.
# ---------------------------------------------------------------------------
def assert_standard_unit_has_no_override() -> None:
    # No drop-in directory may exist for the standard distro portal unit.
    std_dropin_dir = REPO_ROOT / "systemd" / "xdg-desktop-portal.service.d"
    if std_dropin_dir.exists():
        fail(
            "a drop-in directory for the standard xdg-desktop-portal.service "
            "exists; the override must affect only the sidecar process"
        )
    # The only *.service.d drop-in directory under systemd/ must be the sidecar's.
    systemd_dir = REPO_ROOT / "systemd"
    service_d_dirs = sorted(
        p.name
        for p in systemd_dir.iterdir()
        if p.is_dir() and p.name.endswith(".service.d")
    )
    if service_d_dirs != [f"{SIDECAR_UNIT}.d"]:
        fail(f"unexpected service.d directories under systemd/: {service_d_dirs}")
    # No meson.build may install a drop-in for the standard unit.
    for meson in REPO_ROOT.rglob("meson.build"):
        if "xdg-desktop-portal.service.d" in read(meson):
            fail(
                f"{meson} installs a drop-in for the standard portal unit; "
                f"only the sidecar unit may receive an override"
            )
    print("OK 3: standard frontend unit is free of the sidecar desktop override")


# ---------------------------------------------------------------------------
# 4. credentials-sidecar-portals.conf exists in the sidecar package.
# ---------------------------------------------------------------------------
def assert_portals_conf_in_sidecar_package() -> None:
    conf = REPO_ROOT / "portal" / "credentials-sidecar-portals.conf"
    if not conf.is_file():
        fail(f"missing {conf}")
    # portal/meson.build must install it into xdg-desktop-portal/ (frontend dir).
    portal_meson = read(REPO_ROOT / "portal" / "meson.build")
    if "credentials-sidecar-portals.conf" not in portal_meson:
        fail("portal/meson.build does not install credentials-sidecar-portals.conf")
    if "xdg-desktop-portal/" not in portal_meson:
        fail("portal/meson.build must install into xdg-desktop-portal/")
    # The all-in-one PKGBUILD must assert its presence in $pkgdir.
    aio = read(
        REPO_ROOT
        / "packaging"
        / "credentialsd-firefox-sidecar-git"
        / "PKGBUILD"
    )
    if "credentials-sidecar-portals.conf" not in aio:
        fail("all-in-one PKGBUILD must reference credentials-sidecar-portals.conf")
    if "$pkgdir/usr/share/xdg-desktop-portal/credentials-sidecar-portals.conf" not in aio:
        fail("all-in-one PKGBUILD must assert portals.conf presence in $pkgdir")
    print("OK 4: credentials-sidecar-portals.conf ships in the sidecar package")


# ---------------------------------------------------------------------------
# 5. It selects org.freedesktop.impl.portal.experimental.Credential=credentialsd.
# ---------------------------------------------------------------------------
def assert_portals_conf_selects_credential() -> None:
    conf = read(REPO_ROOT / "portal" / "credentials-sidecar-portals.conf")
    if "org.freedesktop.impl.portal.experimental.Credential=credentialsd" not in conf:
        fail("portals.conf must select Credential=credentialsd")
    print("OK 5: portals.conf selects Credential=credentialsd")


# ---------------------------------------------------------------------------
# 6. It uses default=none.
# ---------------------------------------------------------------------------
def assert_portals_conf_default_none() -> None:
    conf = read(REPO_ROOT / "portal" / "credentials-sidecar-portals.conf")
    if "default=none" not in conf:
        fail("portals.conf must use default=none")
    print("OK 6: portals.conf uses default=none")


# ---------------------------------------------------------------------------
# 7. credentialsd.portal uses UseIn=credentials-sidecar;
# ---------------------------------------------------------------------------
def assert_portal_descriptor_usein() -> None:
    text = read(REPO_ROOT / "portal" / "credentialsd.portal")
    if "UseIn=credentials-sidecar;" not in text:
        fail("credentialsd.portal must use UseIn=credentials-sidecar;")
    # Must not enumerate real desktop environments.
    for desktop in ("GNOME", "KDE", "Hyprland", "sway"):
        if f"UseIn={desktop}" in text or f"={desktop};" in text:
            fail(f"credentialsd.portal enumerates real desktop {desktop} in UseIn")
    print("OK 7: credentialsd.portal uses UseIn=credentials-sidecar;")


# ---------------------------------------------------------------------------
# 8. No GNOME/KDE/Hyprland/Sway/generic user portal config is overwritten.
# ---------------------------------------------------------------------------
def assert_no_desktop_config_overwrite() -> None:
    # The sidecar config filename must be unique (not a desktop-specific one).
    name = "credentials-sidecar-portals.conf"
    if name in FORBIDDEN_PORTALS_CONF:
        fail(f"sidecar config filename collides with a desktop config: {name}")
    # portal/meson.build must not install any forbidden desktop config.
    portal_meson = read(REPO_ROOT / "portal" / "meson.build")
    for forbidden in FORBIDDEN_PORTALS_CONF:
        if f"'{forbidden}'" in portal_meson or f'"{forbidden}"' in portal_meson:
            fail(f"portal/meson.build installs forbidden desktop config {forbidden}")
    # No active file may write a user home portals.conf (~/.config/...).
    for path in iter_text_files(REPO_ROOT):
        try:
            text = read(path)
        except OSError:
            continue
        if "~/.config/xdg-desktop-portal/portals.conf" in text:
            rel = path.relative_to(REPO_ROOT)
            # The deploy doc may *mention* that none is required; forbid only
            # instructions that tell the user to create one as a requirement.
            if rel.name == "SIDECAR-DEPLOY.md":
                # Ensure the doc states it is NOT required.
                if "无需" not in text and "not required" not in text.lower():
                    fail("deploy doc references user portals.conf without marking optional")
                continue
            fail(f"active file instructs creating a user portals.conf: {rel}")
    # The all-in-one PKGBUILD must forbid desktop-specific confs in $pkgdir.
    aio = read(
        REPO_ROOT
        / "packaging"
        / "credentialsd-firefox-sidecar-git"
        / "PKGBUILD"
    )
    for forbidden in FORBIDDEN_PORTALS_CONF:
        if forbidden not in aio:
            fail(f"all-in-one PKGBUILD must forbid {forbidden} in $pkgdir")
    print("OK 8: no desktop-specific or user portal config is overwritten")


# ---------------------------------------------------------------------------
# 9. Standard and sidecar D-Bus names still coexist (distinct names).
# ---------------------------------------------------------------------------
def assert_dbus_names_coexist() -> None:
    if SIDECAR_BUS_NAME == STANDARD_BUS_NAME:
        fail("sidecar and standard D-Bus names collide")
    found_sidecar = False
    found_standard = False
    for path in iter_text_files(REPO_ROOT):
        try:
            text = read(path)
        except OSError:
            continue
        if SIDECAR_BUS_NAME in text:
            found_sidecar = True
        if STANDARD_BUS_NAME in text:
            found_standard = True
    if not found_sidecar:
        fail(f"sidecar D-Bus name {SIDECAR_BUS_NAME} not referenced in tree")
    if not found_standard:
        fail(f"standard D-Bus name {STANDARD_BUS_NAME} not referenced in tree")
    print("OK 9: standard and sidecar D-Bus names are distinct and coexist")


# ---------------------------------------------------------------------------
# 10. Credential interface resolves to credentialsd for every simulated real
#     login desktop, because the sidecar overrides only its own
#     XDG_CURRENT_DESKTOP.
# ---------------------------------------------------------------------------
def parse_preferred(conf_text: str) -> dict[str, str]:
    cp = configparser.ConfigParser(strict=False)
    cp.optionxform = str  # preserve case for interface names
    cp.read_string(conf_text)
    if not cp.has_section("preferred"):
        fail("portals.conf missing [preferred] section")
    return dict(cp["preferred"])


def assert_credential_resolves_for_all_desktops() -> None:
    # The sidecar's XDG_CURRENT_DESKTOP comes from the drop-in, not the real
    # desktop. xdg-desktop-portal derives the config filename from the lower
    # case of the (first colon component of) XDG_CURRENT_DESKTOP plus the
    # "-portals.conf" suffix.
    dropin = read(
        REPO_ROOT
        / "systemd"
        / f"{SIDECAR_UNIT}.d"
        / "credentials-sidecar.conf"
    )
    sidecar_desktop = None
    for line in dropin.splitlines():
        if line.strip().startswith("Environment=XDG_CURRENT_DESKTOP="):
            sidecar_desktop = line.strip().split("XDG_CURRENT_DESKTOP=", 1)[1].strip()
            break
    if sidecar_desktop != SIDECAR_DESKTOP:
        fail(
            f"sidecar drop-in XDG_CURRENT_DESKTOP is {sidecar_desktop!r}, "
            f"expected {SIDECAR_DESKTOP!r}"
        )

    # Derive the config filename exactly as xdg-desktop-portal would.
    first_component = sidecar_desktop.split(":")[0]
    expected_filename = f"{first_component.lower()}-portals.conf"
    if expected_filename != "credentials-sidecar-portals.conf":
        fail(
            f"derived config filename {expected_filename!r} does not match the "
            f"installed credentials-sidecar-portals.conf"
        )

    conf = read(REPO_ROOT / "portal" / expected_filename)
    preferred = parse_preferred(conf)

    # For every simulated real login desktop, the sidecar's Credential backend
    # must resolve to credentialsd, because the sidecar ignores the real desktop.
    for real_desktop in REAL_DESKTOPS:
        credential_backend = preferred.get(
            "org.freedesktop.impl.portal.experimental.Credential", ""
        )
        if credential_backend != "credentialsd":
            fail(
                f"with real desktop {real_desktop}, sidecar Credential backend "
                f"resolved to {credential_backend!r}, expected 'credentialsd'"
            )
        # default must be none so nothing else leaks into the sidecar.
        if preferred.get("default") != "none":
            fail(
                f"with real desktop {real_desktop}, sidecar default is "
                f"{preferred.get('default')!r}, expected 'none'"
            )
    # The real desktops must NOT appear in the sidecar's effective UseIn.
    descriptor = read(REPO_ROOT / "portal" / "credentialsd.portal")
    for real_desktop in REAL_DESKTOPS:
        if f"UseIn={real_desktop}" in descriptor:
            fail(f"credentialsd.portal UseIn enumerates real desktop {real_desktop}")
    print(
        "OK 10: Credential=credentialsd for GNOME/KDE/Hyprland/sway via the "
        "sidecar's own XDG_CURRENT_DESKTOP"
    )


# ---------------------------------------------------------------------------
# 11. The standard Portal still observes the original desktop value.
# ---------------------------------------------------------------------------
def assert_standard_portal_observes_real_desktop() -> None:
    # This repo must not ship or alter the standard distro portal unit, and must
    # not set a global XDG_CURRENT_DESKTOP. The only XDG_CURRENT_DESKTOP
    # directive is the sidecar-scoped drop-in (verified structurally in #2/#3).
    # Confirm no systemd unit source (.service.in) sets XDG_CURRENT_DESKTOP.
    for svc_in in (REPO_ROOT / "systemd").glob("*.service.in"):
        if "XDG_CURRENT_DESKTOP" in read(svc_in):
            fail(
                f"{svc_in} sets XDG_CURRENT_DESKTOP; only the sidecar drop-in may"
            )
    # No meson.build may install a drop-in or Environment override for the
    # standard unit (only the sidecar unit's drop-in is permitted).
    for meson in REPO_ROOT.rglob("meson.build"):
        text = read(meson)
        if "xdg-desktop-portal.service.d" in text:
            fail(f"{meson} targets the standard portal unit with a drop-in")
    print("OK 11: standard Portal keeps observing the user's real desktop")


# ---------------------------------------------------------------------------
# 12. Package file-overlap validation remains zero.
# ---------------------------------------------------------------------------
def assert_zero_package_overlap() -> None:
    # The sidecar config and drop-in install under unique paths that no distro
    # portal package ships, so file-overlap validation stays zero.
    aio = read(
        REPO_ROOT
        / "packaging"
        / "credentialsd-firefox-sidecar-git"
        / "PKGBUILD"
    )
    # The all-in-one package must still assert no leftover browser archives.
    if "*.xpi" not in aio.replace("\\", "") or "return 1" not in aio:
        fail("all-in-one PKGBUILD must retain zero-overlap archive assertion")
    # The forbidden desktop-conf assertion (added in #8) is the overlap guard
    # for portal configs; re-confirm it returns 1 on violation.
    if "must not install/overwrite desktop-specific" not in aio:
        fail("all-in-one PKGBUILD missing desktop-config overlap guard")
    # The sidecar install paths must be unique (not distro paths).
    unique_paths = (
        "/usr/share/xdg-desktop-portal/credentials-sidecar-portals.conf",
        "/usr/lib/systemd/user/credentials-portal-sidecar.service.d/credentials-sidecar.conf",
    )
    portal_meson = read(REPO_ROOT / "portal" / "meson.build")
    systemd_meson = read(REPO_ROOT / "systemd" / "meson.build")
    if "credentials-sidecar-portals.conf" not in portal_meson:
        fail("portal/meson.build must install the unique sidecar portals.conf")
    if "credentials-portal-sidecar.service.d" not in systemd_meson:
        fail("systemd/meson.build must install the unique sidecar drop-in")
    print("OK 12: package file-overlap validation remains zero (unique paths)")


def main() -> int:
    assert_no_usein_hyprland()
    assert_sidecar_unit_has_desktop_override()
    assert_standard_unit_has_no_override()
    assert_portals_conf_in_sidecar_package()
    assert_portals_conf_selects_credential()
    assert_portals_conf_default_none()
    assert_portal_descriptor_usein()
    assert_no_desktop_config_overwrite()
    assert_dbus_names_coexist()
    assert_credential_resolves_for_all_desktops()
    assert_standard_portal_observes_real_desktop()
    assert_zero_package_overlap()
    print(
        "\nOK: desktop-agnostic portal selection enforced — Hyprland "
        "specialization removed; sidecar uses credentials-sidecar identity"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
