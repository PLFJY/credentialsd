if get_option('profile') == 'default'
  cargo_options += ['--release']
  rust_profile = 'release'
  message('Building in release mode')
else
  rust_profile = 'debug'
  message('Building in debug mode')
endif

cargo_env = ['CARGO_HOME=' + cargo_home]
# The hidapi crate (transitive via libwebauthn) builds a native static archive
# that rust-lld fails to resolve under release LTO. Pass CARGO_PROFILE_RELEASE_LTO
# explicitly so it reaches cargo regardless of the parent environment.
if get_option('profile') == 'default'
  cargo_env += 'CARGO_PROFILE_RELEASE_LTO=' + (get_option('cargo_lto') ? 'true' : 'false')
endif
message('@0@'.format(cargo_options))

custom_target(
  'credentialsd',
  build_by_default: true,
  build_always_stale: true,
  output: backend_executable_name,
  console: true,
  install: true,
  install_dir: bindir,
  command: [
    'rm',
    '-f', '@OUTPUT@',
    '&&',
    'env',
    cargo_env,
    cargo,
    'build',
    cargo_options,
    '&&',
    'ln',
    cargo_target_dir / rust_profile / backend_executable_name,
    '@OUTPUT@',
  ],
)

test(
  'credentialsd cargo-unit-tests',
  cargo,
  env: [cargo_env],
  args: [
    'test',
    '--bins',
    '--no-fail-fast', cargo_options,
    '--',
    '--nocapture',
  ],
  protocol: 'exitcode',
)