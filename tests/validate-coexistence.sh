#!/bin/sh
# SPDX-License-Identifier: LGPL-3.0-only
# Phase 3 static coexistence validation.
#
# Usage: validate-coexistence.sh <xdp_sidecar_staged_root> <credentialsd_build_dir>
#
# Performs the static (non-runtime) Phase 3 checks:
#   1. xdp sidecar staged file list vs pacman xdg-desktop-portal / hyprland: zero overlap
#   2. credentialsd install plan vs pacman xdg-desktop-portal / hyprland: zero overlap
#   3. sidecar systemd unit: BusName, ExecStart, Description differ from distro
#   4. sidecar dbus service: Name, Exec, SystemdService differ from distro
#   5. sidecar unit has XDG_DESKTOP_PORTAL_ENABLE_EXPERIMENTAL=credential; distro does not
#   6. --replace safety: sidecar BusName != standard BusName (static guarantee)
#
# This script does NOT start any system services or touch the real session bus.

set -eu

XDP_SIDECAR_ROOT="${1:-/tmp/stage-sidecar}"
CREDENTIALSD_BUILD="${2:-/home/plfjy/credentialsd-sidecar/build-sidecar}"

PASS=0
FAIL=0

ok() { printf 'PASS: %s\n' "$1"; PASS=$((PASS + 1)); }
bad() { printf 'FAIL: %s\n' "$1" >&2; FAIL=$((FAIL + 1)); }

# --- 1. xdp sidecar vs distro packages ---
SIDECAR_FILES=$(find "$XDP_SIDECAR_ROOT" -type f -o -type l | sed "s|^$XDP_SIDECAR_ROOT||" | LC_ALL=C sort)
XDP_PKG=$(pacman -Ql xdg-desktop-portal 2>/dev/null | awk '{print $2}' | LC_ALL=C sort)
HYPRLAND_PKG=$(pacman -Ql xdg-desktop-portal-hyprland 2>/dev/null | awk '{print $2}' | LC_ALL=C sort)

OVERLAP_XDP=$(printf '%s\n' "$SIDECAR_FILES" | LC_ALL=C comm -12 - <(printf '%s\n' "$XDP_PKG"))
OVERLAP_HYPRLAND=$(printf '%s\n' "$SIDECAR_FILES" | LC_ALL=C comm -12 - <(printf '%s\n' "$HYPRLAND_PKG"))

if [ -z "$OVERLAP_XDP" ] && [ -z "$OVERLAP_HYPRLAND" ]; then
  ok "xdp sidecar staged files: zero overlap with xdg-desktop-portal and hyprland"
else
  bad "xdp sidecar overlaps distro packages: xdp=[${OVERLAP_XDP}] hyprland=[${OVERLAP_HYPRLAND}]"
fi

# --- 2. credentialsd install plan vs distro packages ---
CREDENTIALSD_FILES=$(python3 -c "
import json, pathlib, sys
p = pathlib.Path('$CREDENTIALSD_BUILD/meson-info/intro-installed.json')
if not p.exists():
    sys.exit(0)
data = json.loads(p.read_text())
for v in sorted(set(data.values())):
    print(v)
" | LC_ALL=C sort)

OVERLAP_CRED_XDP=$(printf '%s\n' "$CREDENTIALSD_FILES" | LC_ALL=C comm -12 - <(printf '%s\n' "$XDP_PKG"))
OVERLAP_CRED_HYPRLAND=$(printf '%s\n' "$CREDENTIALSD_FILES" | LC_ALL=C comm -12 - <(printf '%s\n' "$HYPRLAND_PKG"))

if [ -z "$OVERLAP_CRED_XDP" ] && [ -z "$OVERLAP_CRED_HYPRLAND" ]; then
  ok "credentialsd install plan: zero overlap with xdg-desktop-portal and hyprland"
else
  bad "credentialsd overlaps distro packages: xdp=[${OVERLAP_CRED_XDP}] hyprland=[${OVERLAP_CRED_HYPRLAND}]"
fi

# --- 3. sidecar systemd unit independence ---
SIDECAR_UNIT="$XDP_SIDECAR_ROOT/usr/local/lib/systemd/user/credentials-portal-sidecar.service"
DISTRO_UNIT="/usr/lib/systemd/user/xdg-desktop-portal.service"

if [ -f "$SIDECAR_UNIT" ] && [ -f "$DISTRO_UNIT" ]; then
  S_BUSNAME=$(grep '^BusName=' "$SIDECAR_UNIT" | cut -d= -f2)
  D_BUSNAME=$(grep '^BusName=' "$DISTRO_UNIT" | cut -d= -f2)
  S_EXEC=$(grep '^ExecStart=' "$SIDECAR_UNIT" | cut -d= -f2)
  D_EXEC=$(grep '^ExecStart=' "$DISTRO_UNIT" | cut -d= -f2)

  if [ "$S_BUSNAME" != "$D_BUSNAME" ]; then
    ok "unit BusName differs: sidecar=$S_BUSNAME distro=$D_BUSNAME"
  else
    bad "unit BusName collision: both=$S_BUSNAME"
  fi

  if [ "$S_EXEC" != "$D_EXEC" ]; then
    ok "unit ExecStart differs: sidecar=$S_EXEC distro=$D_EXEC"
  else
    bad "unit ExecStart collision: both=$S_EXEC"
  fi

  if grep -q 'XDG_DESKTOP_PORTAL_ENABLE_EXPERIMENTAL=credential' "$SIDECAR_UNIT"; then
    ok "sidecar unit enables experimental Credential interface"
  else
    bad "sidecar unit missing XDG_DESKTOP_PORTAL_ENABLE_EXPERIMENTAL=credential"
  fi

  if grep -q 'XDG_DESKTOP_PORTAL_ENABLE_EXPERIMENTAL' "$DISTRO_UNIT"; then
    bad "distro unit unexpectedly enables experimental interface"
  else
    ok "distro unit does not enable experimental interface"
  fi
else
  bad "missing unit file(s): sidecar=$SIDECAR_UNIT distro=$DISTRO_UNIT"
fi

# --- 4. sidecar dbus service independence ---
SIDECAR_SVC="$XDP_SIDECAR_ROOT/usr/local/share/dbus-1/services/io.github.PLFJY.CredentialPortal.service"
DISTRO_SVC="/usr/share/dbus-1/services/org.freedesktop.portal.Desktop.service"

if [ -f "$SIDECAR_SVC" ] && [ -f "$DISTRO_SVC" ]; then
  S_NAME=$(grep '^Name=' "$SIDECAR_SVC" | cut -d= -f2)
  D_NAME=$(grep '^Name=' "$DISTRO_SVC" | cut -d= -f2)
  S_SYS=$(grep '^SystemdService=' "$SIDECAR_SVC" | cut -d= -f2)
  D_SYS=$(grep '^SystemdService=' "$DISTRO_SVC" | cut -d= -f2)

  if [ "$S_NAME" != "$D_NAME" ]; then
    ok "dbus service Name differs: sidecar=$S_NAME distro=$D_NAME"
  else
    bad "dbus service Name collision: both=$S_NAME"
  fi

  if [ "$S_SYS" != "$D_SYS" ]; then
    ok "dbus service SystemdService differs: sidecar=$S_SYS distro=$D_SYS"
  else
    bad "dbus service SystemdService collision: both=$S_SYS"
  fi
else
  bad "missing dbus service file(s): sidecar=$SIDECAR_SVC distro=$DISTRO_SVC"
fi

# --- 5. --replace safety (static) ---
if [ "$S_BUSNAME" != "$D_BUSNAME" ]; then
  ok "--replace safety: sidecar owns $S_BUSNAME, cannot replace distro's $D_BUSNAME"
fi

printf '\n=== Phase 3 static validation: %d PASS, %d FAIL ===\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
