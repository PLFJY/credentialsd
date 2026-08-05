# Privacy Notice — credentialsd Firefox Sidecar Extension

This notice covers the Firefox sidecar extension distributed from this
repository as `credentialsd-sidecar-firefox-VERSION.xpi` (extension ID
`credentialsd-sidecar@plfjy.top`). It does not cover the credentialsd daemon,
the credentialsd UI, the Credential Portal sidecar frontend, or any other
component shipped by the Arch package; those components have their own behavior
described in their respective sources.

## What the extension does

The extension intercepts WebAuthn `navigator.credentials.create()` and
`navigator.credentials.get()` operations on HTTPS pages. When a page calls one
of those APIs, the extension forwards the website origin and the WebAuthn
request and response data to the locally installed `credentialsd-firefox-helper`
Native Messaging host. The Native Messaging host forwards the data over D-Bus to
the locally installed credentialsd daemon and the Credential Portal sidecar
frontend, which process the WebAuthn ceremony on the user's device.

All WebAuthn request and response processing occurs locally on the user's
device. The extension does not send telemetry or analytics to PLFJY. The
extension does not send browsing history, WebAuthn payloads, credential IDs,
attestation objects, authenticator data, or authentication responses to any
PLFJY-operated remote service.

## Distribution channels

Two distribution channels are used and they are independent:

* **Mozilla AMO** is used to sign the extension package. Signing produces a
  Mozilla-signed XPI. AMO signing is separate from runtime credential
  processing.
* **GitHub Releases** is used to distribute the signed XPI, the `updates.json`
  update manifest, the `SHA256SUMS` checksums file, and the
  `release-metadata.json` metadata file. Downloading from GitHub Releases is
  separate from runtime credential processing.

Mozilla signing and GitHub downloading do not transmit WebAuthn payloads,
credential IDs, attestation objects, authenticator data, or authentication
responses through PLFJY. The Mozilla AMO and GitHub infrastructure are operated
by their respective providers; their own privacy notices apply to those
interactions.

## Automatic updates

The extension manifest declares an `update_url` that points at
`https://github.com/PLFJY/credentialsd/releases/latest/download/updates.json`.
Firefox periodically fetches that URL to learn whether a newer signed version is
available. The fetch is performed by Firefox against GitHub Releases and is
separate from runtime credential processing. The fetch does not include
WebAuthn payloads, credential IDs, attestation objects, authenticator data, or
authentication responses.

## Data declarations

The extension manifest declares the following `data_collection_permissions`:

```json
"data_collection_permissions": {
  "required": [
    "authenticationInfo",
    "browsingActivity",
    "websiteContent"
  ]
}
```

These categories reflect the data the extension technically handles while
intercepting WebAuthn operations on HTTPS pages. The extension does not
transmit that data to PLFJY; it forwards it only to the locally installed
Native Messaging host on the same device. No PLFJY-operated remote service
receives this data.

## Uninstall behavior

Uninstalling the Firefox extension stops browser integration. After
uninstallation, the extension no longer intercepts WebAuthn operations and no
longer communicates with the Native Messaging host.

Uninstalling the Firefox extension does not automatically uninstall credentialsd
or the Credential Portal sidecar. The daemon, the UI, the sidecar frontend, the
systemd user units, the D-Bus service files, and the Native Messaging manifest
remain installed on the system until they are removed through the system package
manager.

Uninstalling the Arch package does not automatically remove an already installed
Firefox extension. Firefox extensions are managed by Firefox; the Arch package
only installs the native Linux integration. Once a signed XPI has been installed
into a Firefox profile, removing the Arch package does not uninstall that XPI.

## Scope of this notice

This notice describes only the behavior supported by the source code in
`webext/add-on/` and `webext/app/`. It does not make privacy guarantees broader
than the source code supports.
