# Credential Portal sidecar deployment

The sidecar is an additional Portal frontend, not a replacement for the
distribution's `org.freedesktop.portal.Desktop`. Build the paired
`PLFJY/xdg-desktop-portal` `sidecar/credential-portal` branch with its
`io.github.PLFJY.CredentialPortal` identity, then build this project with:

```sh
meson setup build-sidecar -Dprofile=development -Dcargo_locked=true \
  -Dfirefox_portal_bus_name=io.github.PLFJY.CredentialPortal
```

The installed sidecar unit is assigned `XDG_CURRENT_DESKTOP=credentials-sidecar`.
That selects `credentials-sidecar-portals.conf`, which maps only the experimental
Credential interface to credentialsd. It never writes `portals.conf` or any
GNOME, KDE, or Hyprland portal configuration.

After package installation, run `systemctl --user daemon-reload`. A real session
should expose both well-known names. Verify the sidecar interface with:

```sh
gdbus introspect --session --dest io.github.PLFJY.CredentialPortal \
  --object-path /org/freedesktop/portal/desktop
```

Install the Mozilla-signed XPI from the matching GitHub Release; packages do not
install unsigned browser archives. Hybrid QR registration and authentication
remain manual Firefox/phone smoke tests.
