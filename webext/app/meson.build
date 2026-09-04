addon_app_executable_name = 'credentialsd-firefox-helper'
addon_app_config = configuration_data()
addon_app_config.set('SHIM_SCRIPT', bindir / addon_app_executable_name)
addon_app_config.set(
  'DBUS_DOC_FILE',
  datadir / 'credentialsd' / 'xyz.iinuwa.credentialsd.Credentials.xml',
)

addon_app_config.set('APP_ID', 'org.mozilla.firefox')
addon_app_config.set('PORTAL_BUS_NAME', get_option('firefox_portal_bus_name'))
native_messaging_manifest_dir = libdir / 'mozilla' / 'native-messaging-hosts'

configure_file(
  input: 'credential_manager_shim.json.in',
  install_dir: native_messaging_manifest_dir,
  output: 'xyz.iinuwa.credentialsd_helper.json',
  configuration: addon_app_config,
)

test(
  'unit/sidecar-build-routing',
  find_program('python3'),
  args: [meson.project_source_root() / 'tests' / 'test_sidecar_build.py', meson.project_build_root(), get_option('firefox_portal_bus_name')],
  suite: ['unit'],
)

configure_file(
  input: 'credential_manager_shim.py',
  install_dir: bindir,
  output: addon_app_executable_name,
  configuration: addon_app_config,
)
