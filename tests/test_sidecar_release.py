#!/usr/bin/env python3
"""Static invariants for the self-hosted sidecar Firefox release path."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXTENSION_ID = "credentialsd-firefox-sidecar@plfjy.top"
UPDATE_URL = "https://github.com/PLFJY/credentialsd/releases/latest/download/updates.json"


def main(prepared: Path) -> None:
    manifest = json.loads((prepared / "manifest.json").read_text())
    gecko = manifest["browser_specific_settings"]["gecko"]
    assert gecko["id"] == EXTENSION_ID
    assert gecko["update_url"] == UPDATE_URL
    assert gecko["strict_min_version"] == "140.0"
    assert gecko["data_collection_permissions"]["required"] == [
        "authenticationInfo", "browsingActivity", "websiteContent",
    ]
    assert manifest["background"]["service_worker"] == "background.js"
    assert all(item["matches"] == ["<all_urls>"] for item in manifest["content_scripts"])
    helper_manifest = (ROOT / "webext/app/credential_manager_shim.json.in").read_text()
    assert EXTENSION_ID in helper_manifest
    shim = (ROOT / "webext/app/credential_manager_shim.py").read_text()
    assert 'PORTAL_BUS_NAME = "@PORTAL_BUS_NAME@"' in shim
    assert "os.getenv(\"PORTAL_BUS_NAME\")" not in shim
    assert "logging.debug(req_json)" not in shim
    assert "received bytes:" not in shim
    workflow = (ROOT / ".github/workflows/release-firefox-extension.yml").read_text()
    assert "--channel=unlisted" in workflow
    assert "AMO_JWT_SECRET" in workflow
    assert "META-INF/" in workflow
    assert "sha256sum" in workflow
    assert "published-updates.json" in workflow
    assert "workflow_dispatch" in workflow
    assert "inputs.publish == true" in workflow


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: test_sidecar_release.py PREPARED_DIR")
    main(Path(sys.argv[1]))
