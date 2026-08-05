addon_app_executable_name = 'credentialsd-firefox-helper'
addon_app_config = configuration_data()
addon_app_config.set('SHIM_SCRIPT', bindir / addon_app_executable_name)
addon_app_config.set(
  'DBUS_DOC_FILE',
  datadir / 'credentialsd' / 'xyz.iinuwa.credentialsd.Credentials.xml',
)

addon_app_config.set('APP_ID', 'org.mozilla.firefox')
# Build-time D-Bus destination for the Credential Portal frontend.
# Default reproduces upstream (org.freedesktop.portal.Desktop); the sidecar
# build overrides this to the sidecar identity. The shim must not accept this
# value from page content, extension messages, or environment variables.
addon_app_config.set('PORTAL_BUS_NAME', get_option('firefox_portal_bus_name'))
native_messaging_manifest_dir = libdir / 'mozilla' / 'native-messaging-hosts'

configure_file(
  input: 'credential_manager_shim.json.in',
  install_dir: native_messaging_manifest_dir,
  output: 'xyz.iinuwa.credentialsd_helper.json',
  configuration: addon_app_config,
)

configure_file(
  input: 'credential_manager_shim.py',
  install_dir: bindir,
  output: addon_app_executable_name,
  configuration: addon_app_config,
)

# Phase 2 regression: assert the generated shim targets the configured
# firefox_portal_bus_name at both the Registry and Credential proxy
# call-sites, and that the Native Messaging manifest keeps the upstream
# host name / extension ID / object path / interfaces regardless of the
# configured bus name. Runs in both default and sidecar build trees.
test(
  'unit/shim-dest',
  find_program('test_shim_dest.py', dirs: meson.project_source_root() / 'tests'),
  args: [
    meson.project_build_root(),
    get_option('firefox_portal_bus_name'),
  ],
  suite: ['unit'],
  is_parallel: true,
  protocol: 'exitcode',
)

# Phase 3 regression: prove the standard and sidecar D-Bus well-known names
# can coexist on a disposable session bus (separate holder processes),
# that killing one does not disturb the other, and that re-acquiring the
# freed standard name does not replace the sidecar name. Wrapped in
# dbus-run-session so it never touches the real session bus.
dbus_run_session = find_program('dbus-run-session', required: false)
if dbus_run_session.found()
  test(
    'unit/dbus-coexistence',
    dbus_run_session,
    args: [
      '--',
      find_program('python3'),
      meson.project_source_root() / 'tests' / 'test_dbus_coexistence.py',
    ],
    suite: ['unit'],
    is_parallel: true,
    protocol: 'exitcode',
  )
endif