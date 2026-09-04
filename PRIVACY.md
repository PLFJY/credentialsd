# Privacy Notice — credentialsd Firefox Sidecar

The sidecar extension intercepts WebAuthn calls on web pages and forwards them
only to the locally installed Native Messaging helper and credentialsd service.
It sends no telemetry or WebAuthn data to PLFJY-operated services. Mozilla AMO
signs the unlisted XPI; GitHub Releases hosts that signed XPI and the update
manifest. Those distribution actions are separate from WebAuthn processing.

The manifest declares `authenticationInfo`, `browsingActivity`, and
`websiteContent` because the extension technically processes that data locally
while performing WebAuthn. The Native Messaging helper deliberately logs only
operation structure and lengths, never complete requests, credential IDs,
challenges, attestation objects, authenticator data, or response payloads.
