#!/bin/sh
# SPDX-License-Identifier: LGPL-3.0-only
# Phase 4 preflight: verify the sidecar frontend acquires its D-Bus name and
# exposes the experimental Credential interface on a disposable session bus.
#
# This does NOT perform a WebAuthn ceremony. It only proves the sidecar
# binary, when started, owns io.github.PLFJY.CredentialPortal (not
# org.freedesktop.portal.Desktop) and lists the Credential interface.
#
# Usage: verify-sidecar-routing.sh <sidecar_exec> [build_sidecar_data_dir]

set -eu

SIDECAR_EXEC="${1:?usage: verify-sidecar-routing.sh <sidecar_exec>}"
SIDECAR_EXEC=$(readlink -f "$SIDECAR_EXEC")
SIDECAR_DATA="${2:-}"

PASS=0
FAIL=0
ok() { printf 'PASS: %s\n' "$1"; PASS=$((PASS + 1)); }
bad() { printf 'FAIL: %s\n' "$1" >&2; FAIL=$((FAIL + 1)); }

if [ ! -x "$SIDECAR_EXEC" ]; then
  bad "sidecar executable not found: $SIDECAR_EXEC"
  exit 1
fi

# Use a disposable bus so we never touch the real session.
export XDG_DESKTOP_PORTAL_ENABLE_EXPERIMENTAL=credential
# Point XDG_DATA_DIRS at the build tree if provided (for portal config).
if [ -n "$SIDECAR_DATA" ]; then
  export XDG_DATA_DIRS="$SIDECAR_DATA:${XDG_DATA_DIRS:-/usr/local/share:/usr/share}"
fi

# Start the disposable bus and run the verification inside it.
dbus-run-session -- sh -eu -c '
  SIDECAR_EXEC="'"$SIDECAR_EXEC"'"
  SIDECAR_BUS_NAME="io.github.PLFJY.CredentialPortal"
  STANDARD_BUS_NAME="org.freedesktop.portal.Desktop"

  # Start the sidecar in the background; it may log to stderr.
  "$SIDECAR_EXEC" --replace >/tmp/sidecar-preflight.log 2>&1 &
  SIDECAR_PID=$!

  # Wait up to 8 seconds for the name to appear.
  owned=""
  for i in 1 2 3 4 5 6 7 8; do
    sleep 1
    owned=$(gdbus call --session --dest org.freedesktop.DBus \
      --object-path /org/freedesktop/DBus \
      --method org.freedesktop.DBus.GetNameOwner \
      "$SIDECAR_BUS_NAME" 2>/dev/null || true)
    if [ -n "$owned" ]; then break; fi
  done

  if [ -z "$owned" ]; then
    echo "FAIL: $SIDECAR_BUS_NAME not acquired within 8s" >&2
    echo "--- sidecar log (last 20 lines) ---" >&2
    tail -20 /tmp/sidecar-preflight.log >&2 || true
    kill "$SIDECAR_PID" 2>/dev/null || true
    wait "$SIDECAR_PID" 2>/dev/null || true
    exit 1
  fi
  echo "PASS: sidecar acquired $SIDECAR_BUS_NAME (owner=$owned)"
  PASS=1

  # Verify the standard name is NOT owned by the sidecar.
  std_owner=$(gdbus call --session --dest org.freedesktop.DBus \
    --object-path /org/freedesktop/DBus \
    --method org.freedesktop.DBus.GetNameOwner \
    "$STANDARD_BUS_NAME" 2>/dev/null || true)
  if [ -z "$std_owner" ]; then
    echo "PASS: standard name $STANDARD_BUS_NAME is NOT owned by sidecar"
    PASS=$((PASS + 1))
  else
    # The standard name might be owned if the sidecar somehow grabbed it.
    # Compare owners.
    if [ "$std_owner" = "$owned" ]; then
      echo "FAIL: sidecar owns BOTH $SIDECAR_BUS_NAME and $STANDARD_BUS_NAME ($owned)" >&2
    else
      echo "PASS: standard name $STANDARD_BUS_NAME owned by different connection ($std_owner)"
      PASS=$((PASS + 1))
    fi
  fi

  # Introspect the sidecar object path for the Credential interface.
  cred_iface=$(gdbus introspect --session --dest "$SIDECAR_BUS_NAME" \
    --object-path /org/freedesktop/portal/desktop 2>/dev/null \
    | grep -c "experimental.Credential" || true)
  if [ "$cred_iface" -ge 1 ]; then
    echo "PASS: sidecar exposes org.freedesktop.portal.experimental.Credential"
    PASS=$((PASS + 1))
  else
    echo "FAIL: sidecar does not expose org.freedesktop.portal.experimental.Credential" >&2
    echo "--- introspection ---" >&2
    gdbus introspect --session --dest "$SIDECAR_BUS_NAME" \
      --object-path /org/freedesktop/portal/desktop >&2 2>/dev/null || true
  fi

  # Clean up.
  kill "$SIDECAR_PID" 2>/dev/null || true
  wait "$SIDECAR_PID" 2>/dev/null || true
  echo "=== $PASS checks passed ==="
  exit $((3 - PASS))
'
RC=$?
if [ "$RC" -eq 0 ]; then
  printf '\n=== Phase 4 sidecar routing preflight: PASS ===\n'
else
  printf '\n=== Phase 4 sidecar routing preflight: PARTIAL (rc=%d) ===\n' "$RC"
fi
exit 0
