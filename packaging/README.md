# Arch sidecar packaging

`credentialsd-firefox-sidecar-git` builds credentialsd and the isolated
`io.github.PLFJY.CredentialPortal` frontend together. It coexists with the
distribution's `org.freedesktop.portal.Desktop`; it does not replace the normal
xdg-desktop-portal package or install desktop-specific portal configuration.

The package installs the daemon, UI, Native Messaging host, sidecar executable,
sidecar D-Bus activation, sidecar unit/drop-in, and the dedicated portal
configuration. It deliberately removes all XPI and Chromium archives. Install
the Mozilla-signed Firefox XPI from the GitHub Release instead.
