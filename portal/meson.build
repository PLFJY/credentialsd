# Backend descriptor for the credentialsd Credential portal backend.
# UseIn is retained only as a legacy fallback; the sidecar frontend selects this
# backend via the dedicated credentials-sidecar-portals.conf, driven by the
# sidecar's own XDG_CURRENT_DESKTOP=credentials-sidecar. This is intentionally
# desktop-environment-agnostic and does not enumerate real desktops.
install_data(
  'credentialsd.portal',
  install_dir: datadir / 'xdg-desktop-portal/portals/',
)

# Dedicated frontend portal configuration for the Credential Portal sidecar.
# The filename matches the lower-case sidecar XDG_CURRENT_DESKTOP value
# (credentials-sidecar), so xdg-desktop-portal loads it only for the sidecar
# process. It does not touch any desktop-specific *-portals.conf and selects
# only the Credential interface; every other interface resolves to none.
install_data(
  'credentials-sidecar-portals.conf',
  install_dir: datadir / 'xdg-desktop-portal/',
)
