# Arch Packaging

This directory contains the Arch Linux `PKGBUILD` files for the credentialsd
Credential Portal sidecar build.

## Packages

### `credentialsd-firefox-sidecar-git` (recommended all-in-one)

Installs the native Linux integration only:

- credentialsd daemon
- credentialsd UI
- Credential Portal sidecar frontend (`io.github.PLFJY.CredentialPortal`)
- systemd user units
- D-Bus service files
- Portal backend metadata
- `/usr/bin/credentialsd-firefox-helper`
- `/usr/lib/mozilla/native-messaging-hosts/xyz.iinuwa.credentialsd_helper.json`
- schemas, icons, locale and required runtime data

The package does **not** install the Firefox extension itself. The
Mozilla-signed Firefox XPI is distributed only through GitHub Releases:

```
https://github.com/PLFJY/credentialsd/releases/latest
```

`makepkg -si` installs only the native Linux integration. To permanently
install the Firefox extension, download the signed XPI from the latest GitHub
Release and install it via
`Firefox → about:addons → gear menu → Install Add-on From File…`.

### `credentialsd-git`

Daemon and UI built from the `integration/credential-portal-sidecar` branch,
without the webextension surface. Useful when the sidecar frontend is provided
by `xdg-credential-portal-sidecar-git` and the user wants the daemon/UI only.

### `xdg-credential-portal-sidecar-git`

Credential Portal sidecar frontend built from the
`PLFJY/xdg-desktop-portal` `sidecar/credential-portal` branch. Installs only
the sidecar frontend (`credentials-portal-sidecar`), its systemd user unit, and
its D-Bus activation service under the dedicated bus name
`io.github.PLFJY.CredentialPortal`. Coexists with the standard distro
`xdg-desktop-portal` package.

## Browser extension distribution policy

Signed Firefox extensions are distributed **only** through GitHub Releases.

No supported Arch package installs an XPI, a Chromium extension ZIP,
`updates.json`, or any Mozilla-signed Release artifact into `/usr`. The
all-in-one `credentialsd-firefox-sidecar-git` package removes any browser
extension archives produced by the Meson install step and asserts that none
remain in the package root before completing `package()`.

The Meson build may continue generating an unsigned XPI as an intermediate
development artifact. That artifact remains in the build directory only and is
suitable for temporary loading through `about:debugging → This Firefox → Load
Temporary Add-on…`. It is never installed into `/usr`, never uploaded to a
GitHub Release, and never referenced in permanent-install documentation.

## Split-package cleanup

The previous `credentialsd-webextension-sidecar-git` split package existed
primarily to install unsigned browser archives into `/usr`. It has been
removed. The Native Messaging surface it installed is now provided by the
all-in-one `credentialsd-firefox-sidecar-git` package, which is the
recommended way to install the native Linux integration.
