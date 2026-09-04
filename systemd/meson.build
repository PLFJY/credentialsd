systemd_config = configuration_data()
# HACK: Not using libdir option, since on some distros (Fedora), libdir is `lib64`, but systemd is always in `lib`
# If you know of a better way to do this, let me know
systemd_user_service_dir = prefix / 'lib' / 'systemd' / 'user'
systemd_config.set('DAEMON_EXECUTABLE', bindir / backend_executable_name)
systemd_config.set(
  'UI_EXECUTABLE',
  bindir / gui_executable_name,
)
configure_file(
  input: 'xyz.iinuwa.credentialsd.Credentials.service.in',
  install_dir: systemd_user_service_dir,
  output: 'xyz.iinuwa.credentialsd.Credentials.service',
  configuration: systemd_config,
)
configure_file(
  input: 'xyz.iinuwa.credentialsd.UiControl.service.in',
  install_dir: systemd_user_service_dir,
  output: 'xyz.iinuwa.credentialsd.UiControl.service',
  configuration: systemd_config,
)

# The named unit is provided by the xdg-desktop-portal sidecar package. The
# drop-in intentionally does not affect xdg-desktop-portal.service.
install_data(
  'credentials-portal-sidecar.service.d' / 'credentials-sidecar.conf',
  install_dir: systemd_user_service_dir / 'credentials-portal-sidecar.service.d',
)
