install_data(
  'credentialsd.portal',
  install_dir: datadir / 'xdg-desktop-portal/portals/',
)

# Selected only by the separately-installed Credential Portal sidecar, whose
# unit sets XDG_CURRENT_DESKTOP=credentials-sidecar. This does not touch the
# user's regular portal service or desktop-specific configuration.
install_data(
  'credentials-sidecar-portals.conf',
  install_dir: datadir / 'xdg-desktop-portal/',
)
