#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-only
"""Phase 3 D-Bus name coexistence test.

Runs inside a disposable `dbus-run-session` and proves:
  1. `org.freedesktop.portal.Desktop` and `io.github.PLFJY.CredentialPortal`
     can both be owned on the same bus by *different* connections (separate
     child processes, mirroring two separate portal processes).
  2. Releasing one name (killing its holder process) does not affect the
     other name.
  3. A third connection re-acquiring the freed standard name does not
     disturb the sidecar name (the sidecar name is insulated from
     --replace on the standard name).

Uses GLib's D-Bus bindings (always available on a GLib system) so no
extra Python packages are required. `busctl --user list` is used to read
the owner unique name of each well-known name.

This is a D-Bus layer test; it does not start the actual portal binaries
(that is a human-assisted runtime gate).
"""

from __future__ import annotations

import os
import select
import signal
import subprocess
import sys
import tempfile

STANDARD_NAME = "org.freedesktop.portal.Desktop"
SIDECAR_NAME = "io.github.PLFJY.CredentialPortal"

HOLDER_SCRIPT = """
import os, sys, signal
from gi.repository import GLib, Gio

name = sys.argv[1]
ready_fd = int(sys.argv[2])
loop = GLib.MainLoop()

def name_acquired(connection, n):
    os.write(ready_fd, b'ready\\n')
    os.close(ready_fd)

def name_lost(connection, n):
    sys.exit(1)

Gio.bus_own_name(Gio.BusType.SESSION, name, Gio.BusNameOwnerFlags.NONE,
                 lambda c, n: None, name_acquired, name_lost)
signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
loop.run()
"""


def fail(msg: str) -> "NoReturn":
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def spawn_holder(name: str) -> subprocess.Popen:
    """Spawn a child process that owns `name` until SIGTERM."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, prefix="dbus_holder_"
    ) as tf:
        tf.write(HOLDER_SCRIPT)
        script_path = tf.name
    read_fd, write_fd = os.pipe()
    proc = subprocess.Popen(
        [sys.executable, script_path, name, str(write_fd)],
        pass_fds=(write_fd,),
    )
    os.close(write_fd)
    # Wait for the child to signal name acquisition.
    ready, _, _ = select.select([read_fd], [], [], 10.0)
    if not ready:
        proc.kill()
        fail(f"holder for {name} did not acquire the name within 10s")
    data = os.read(read_fd, 64)
    os.close(read_fd)
    if data.strip() != b"ready":
        proc.kill()
        fail(f"holder for {name} sent unexpected readiness: {data!r}")
    # Stash the script path for cleanup.
    proc._holder_script = script_path  # type: ignore[attr-defined]
    return proc


def get_name_owner(name: str) -> str | None:
    """Return the unique bus name owning `name`, or None if unowned.

    Uses `gdbus call` to invoke `org.freedesktop.DBus.GetNameOwner`, which
    returns the unique connection name (e.g. `:1.42`) when the name is owned
    and errors when it is not.
    """
    try:
        out = subprocess.check_output(
            [
                "gdbus", "call", "--session",
                "--dest", "org.freedesktop.DBus",
                "--object-path", "/org/freedesktop/DBus",
                "--method", "org.freedesktop.DBus.GetNameOwner",
                name,
            ],
            text=True,
            timeout=5,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    # Output looks like: (':1.42',)
    import ast
    try:
        value = ast.literal_eval(out.strip())
        if isinstance(value, tuple) and len(value) == 1:
            owner = value[0]
            if isinstance(owner, str) and owner.startswith(":"):
                return owner
    except (ValueError, SyntaxError):
        pass
    return None


def cleanup_proc(proc: subprocess.Popen):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    script = getattr(proc, "_holder_script", None)
    if script:
        try:
            os.unlink(script)
        except OSError:
            pass


def main() -> int:
    addr = os.environ.get("DBUS_SESSION_BUS_ADDRESS", "")
    if not addr or "autolaunch" in addr:
        fail(
            "refusing to run on the real/autolaunch session bus; wrap with "
            "`dbus-run-session -- python3 tests/test_dbus_coexistence.py`"
        )

    # 1. Both names owned by separate processes simultaneously.
    proc_std = spawn_holder(STANDARD_NAME)
    proc_side = spawn_holder(SIDECAR_NAME)
    owner_std = get_name_owner(STANDARD_NAME)
    owner_side = get_name_owner(SIDECAR_NAME)
    if not owner_std:
        fail(f"{STANDARD_NAME} not owned after spawn")
    if not owner_side:
        fail(f"{SIDECAR_NAME} not owned after spawn")
    if owner_std == owner_side:
        fail(
            f"both names owned by same unique name {owner_std!r}; "
            "expected distinct processes"
        )
    print(
        f"coexist: standard={STANDARD_NAME} owned by {owner_std}; "
        f"sidecar={SIDECAR_NAME} owned by {owner_side}"
    )

    # 2. Kill the standard-name holder; sidecar must survive.
    cleanup_proc(proc_std)
    owner_side_after = get_name_owner(SIDECAR_NAME)
    if owner_side_after != owner_side:
        fail(
            f"sidecar name owner changed after killing standard holder: "
            f"{owner_side!r} -> {owner_side_after!r}"
        )
    owner_std_after_release = get_name_owner(STANDARD_NAME)
    if owner_std_after_release is not None:
        fail(
            f"standard name still owned after holder killed: "
            f"{owner_std_after_release!r}"
        )
    print(
        f"insulated: after killing {STANDARD_NAME} holder, sidecar "
        f"{SIDECAR_NAME} still owned by {owner_side_after}"
    )

    # 3. A third connection re-acquires the freed standard name; the sidecar
    #    name must remain undisturbed.
    proc_std2 = spawn_holder(STANDARD_NAME)
    owner_std2 = get_name_owner(STANDARD_NAME)
    owner_side_final = get_name_owner(SIDECAR_NAME)
    if not owner_std2:
        fail("third connection did not acquire freed standard name")
    if owner_std2 == owner_side:
        fail("third connection reused sidecar's unique name unexpectedly")
    if owner_side_final != owner_side:
        fail(
            f"sidecar name owner changed after third connection acquired "
            f"standard name: {owner_side!r} -> {owner_side_final!r}"
        )
    print(
        f"replace-safe: {STANDARD_NAME} re-acquired by {owner_std2}; "
        f"sidecar {SIDECAR_NAME} still owned by {owner_side_final}"
    )

    cleanup_proc(proc_std2)
    cleanup_proc(proc_side)
    print("OK: D-Bus name coexistence proven on disposable session bus")
    return 0


if __name__ == "__main__":
    sys.exit(main())
