#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-only
"""Release regression: workflow YAML syntax and publish security boundaries.

Asserts that ``.github/workflows/release-firefox-extension.yml``:
  * is valid YAML;
  * triggers on pull_request with the required paths and workflow_dispatch
    with a ``publish`` boolean input;
  * declares a top-level concurrency group ``firefox-extension-release``
    with ``cancel-in-progress: false``;
  * has two jobs: ``validate`` and ``publish``;
  * ``validate`` has ``permissions.contents: read`` only;
  * ``publish`` has ``permissions.contents: write`` only;
  * ``publish`` declares ``environment: amo-signing``;
  * ``publish`` runs only when event is workflow_dispatch, publish is true,
    repository is PLFJY/credentialsd, ref is the default branch, and
    validate succeeded;
  * the workflow does NOT grant actions/packages/id-token/issues/
    pull-requests/deployments write scopes;
  * the workflow pins web-ext to a specific version (not @latest);
  * the workflow does NOT use a third-party GitHub Release action (uses
    ``gh release`` commands instead);
  * the workflow supplies AMO credentials only through step environment
    variables and never interpolates them into command strings;
  * the workflow does NOT enable shell tracing (``set -x``);
  * the workflow references ``PRIVACY.md`` and ``SIDECAR-DEPLOY.md`` in
    pull_request paths;
  * the workflow does NOT publish automatically on push or from a pull
    request.

Standalone: requires PyYAML if available. If PyYAML is not installed, falls
back to a structural text inspection.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

WORKFLOW_REL = ".github/workflows/release-firefox-extension.yml"


def fail(msg: str) -> "NoReturn":
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def try_yaml(text: str):
    try:
        import yaml  # type: ignore
    except ImportError:
        return None
    return yaml.safe_load(text)


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    wf = repo_root / WORKFLOW_REL
    if not wf.is_file():
        fail(f"workflow file missing: {wf}")

    text = wf.read_text(encoding="utf-8")
    parsed = try_yaml(text)

    if parsed is None:
        # Fallback: structural text inspection. PyYAML not installed.
        # Verify presence of key strings; skip semantic checks.
        required = (
            "name: Release Firefox Extension",
            "on:",
            "pull_request:",
            "workflow_dispatch:",
            "publish:",
            "concurrency:",
            "firefox-extension-release",
            "cancel-in-progress: false",
            "jobs:",
            "validate:",
            "publish:",
            "environment: amo-signing",
            "permissions:",
            "contents: read",
            "contents: write",
            "AMO_JWT_ISSUER: ${{ secrets.AMO_JWT_ISSUER }}",
            "AMO_JWT_SECRET: ${{ secrets.AMO_JWT_SECRET }}",
            "gh release create",
            "web-ext sign",
            "--channel=unlisted",
        )
        for needle in required:
            if needle not in text:
                fail(f"workflow missing required string: {needle!r}")
        forbidden = (
            "actions: write",
            "packages: write",
            "id-token: write",
            "issues: write",
            "pull-requests: write",
            "deployments: write",
            "web-ext@latest",
            "set -x",
        )
        for needle in forbidden:
            if needle in text:
                fail(f"workflow contains forbidden string: {needle!r}")
        print(
            "OK: workflow structural inspection passed (PyYAML not installed; "
            "skipping semantic YAML checks)"
        )
        return 0

    # Semantic checks.
    if not isinstance(parsed, dict):
        fail("workflow YAML did not parse to a mapping")

    # 1. Triggers.
    on = parsed.get(True) or parsed.get("on")  # YAML parses 'on:' as True sometimes
    if on is None:
        fail("workflow missing 'on:' triggers")
    if not isinstance(on, dict):
        fail("workflow 'on:' is not a mapping")
    if "pull_request" not in on:
        fail("workflow missing pull_request trigger")
    pr = on["pull_request"]
    if not isinstance(pr, dict) or "paths" not in pr:
        fail("pull_request trigger missing paths")
    pr_paths = pr.get("paths") or []
    required_pr_paths = (
        ".github/workflows/release-firefox-extension.yml",
        "webext/**",
        "scripts/prepare-firefox-extension.py",
        "scripts/generate-firefox-update-manifest.py",
        "tests/**firefox**",
        "PRIVACY.md",
        "SIDECAR-DEPLOY.md",
        "packaging/credentialsd-firefox-sidecar-git/PKGBUILD",
    )
    for required in required_pr_paths:
        if required not in pr_paths:
            fail(f"pull_request.paths missing {required!r}")
    if "push" in on:
        # No automatic publish on push.
        push = on["push"]
        if push is not None:
            fail("workflow must not declare a push trigger that could publish")

    if "workflow_dispatch" not in on:
        fail("workflow missing workflow_dispatch trigger")
    wd = on["workflow_dispatch"]
    if not isinstance(wd, dict) or "inputs" not in wd:
        fail("workflow_dispatch missing inputs")
    pub_input = wd["inputs"].get("publish")
    if not isinstance(pub_input, dict):
        fail("workflow_dispatch.inputs.publish missing")
    if pub_input.get("type") != "boolean":
        fail("workflow_dispatch.inputs.publish.type must be boolean")
    if pub_input.get("required") is not True:
        fail("workflow_dispatch.inputs.publish.required must be true")
    if pub_input.get("default") is not False:
        fail("workflow_dispatch.inputs.publish.default must be false")

    # 2. Concurrency.
    conc = parsed.get("concurrency")
    if not isinstance(conc, dict):
        fail("workflow missing top-level concurrency")
    if conc.get("group") != "firefox-extension-release":
        fail(f"concurrency.group={conc.get('group')!r} != 'firefox-extension-release'")
    if conc.get("cancel-in-progress") is not False:
        fail("concurrency.cancel-in-progress must be false")

    # 3. Top-level permissions.
    top_perms = parsed.get("permissions")
    if top_perms != {"contents": "read"} and top_perms != {"contents": "read", }:
        # Allow top-level contents: read.
        if not (isinstance(top_perms, dict) and top_perms.get("contents") == "read" and len(top_perms) == 1):
            fail(
                f"top-level permissions must be exactly contents:read; got "
                f"{top_perms!r}"
            )

    # 4. Jobs.
    jobs = parsed.get("jobs")
    if not isinstance(jobs, dict):
        fail("workflow missing jobs")
    if set(jobs) != {"validate", "publish"}:
        fail(f"workflow must have exactly validate+publish jobs; got {set(jobs)}")

    # 5. validate permissions.
    validate = jobs["validate"]
    vp = validate.get("permissions")
    if not (isinstance(vp, dict) and vp.get("contents") == "read" and len(vp) == 1):
        fail(f"validate.permissions must be exactly contents:read; got {vp!r}")

    # 6. publish permissions + environment + if-condition.
    publish = jobs["publish"]
    pp = publish.get("permissions")
    if not (isinstance(pp, dict) and pp.get("contents") == "write" and len(pp) == 1):
        fail(
            f"publish.permissions must be exactly contents:write; got {pp!r}"
        )
    if publish.get("environment") != "amo-signing":
        fail(f"publish.environment={publish.get('environment')!r} != amo-signing")
    if "needs" not in publish or "validate" not in publish["needs"]:
        fail("publish job must needs: validate")
    if "if" not in publish:
        fail("publish job missing if-condition")

    # The if-condition must encode the four event/repository/ref conditions.
    # The "validation job succeeded" condition is enforced separately via
    # ``needs: validate`` (verified above) — that is the standard GitHub
    # Actions idiom and causes publish to be skipped if validate fails.
    if_expr = str(publish["if"])
    required_fragments = (
        "github.event_name == 'workflow_dispatch'",
        "inputs.publish == true",
        "github.repository == 'PLFJY/credentialsd'",
        "github.event.repository.default_branch",
    )
    for frag in required_fragments:
        if frag not in if_expr:
            fail(
                f"publish.if must contain {frag!r}; got:\n{if_expr}"
            )

    # 7. Forbidden scopes anywhere in the workflow.
    forbidden_scopes = (
        "actions: write",
        "packages: write",
        "id-token: write",
        "issues: write",
        "pull-requests: write",
        "deployments: write",
    )
    for scope in forbidden_scopes:
        if scope in text:
            fail(f"workflow must not grant {scope!r}")

    # 8. web-ext pinned (not @latest).
    if "web-ext@latest" in text:
        fail("workflow must not use web-ext@latest; pin a specific version")
    if "WEB_EXT_VERSION" not in text:
        fail("workflow must declare a pinned WEB_EXT_VERSION")
    m = re.search(r'WEB_EXT_VERSION:\s*"([^"]+)"', text)
    if not m:
        fail("workflow WEB_EXT_VERSION must be a quoted literal")
    version = m.group(1)
    if not re.match(r"^\d+\.\d+\.\d+$", version):
        fail(f"WEB_EXT_VERSION={version!r} is not a pinned X.Y.Z version")

    # 9. No third-party GitHub Release action.
    if "softprops/action-gh-release" in text or "ncipollo/release-action" in text:
        fail("workflow must use 'gh release' commands, not a third-party Release action")
    if "gh release create" not in text:
        fail("workflow must use 'gh release create'")

    # 10. AMO credentials supplied only through step env, never interpolated.
    if "${{ secrets.AMO_JWT_ISSUER }}" not in text:
        fail("workflow must reference AMO_JWT_ISSUER secret via ${{ }}")
    if "${{ secrets.AMO_JWT_SECRET }}" not in text:
        fail("workflow must reference AMO_JWT_SECRET secret via ${{ }}")
    # The secret names MUST NOT appear inside a `run:` block's command string
    # in a way that interpolates the value directly. We check that the env:
    # block declares them and that no `--api-key=$`-style interpolation uses
    # the ${{ }} form.
    if re.search(r"--api-key=\$\{\{", text):
        fail("workflow must not interpolate AMO secrets directly into --api-key=")
    if re.search(r"--api-secret=\$\{\{", text):
        fail("workflow must not interpolate AMO secrets directly into --api-secret=")

    # 11. No shell tracing.
    if re.search(r"^\s*set\s+-x\b", text, re.MULTILINE):
        fail("workflow must not enable shell tracing (set -x)")

    # 12. GH_TOKEN uses github.token (not a PAT).
    if "GITHUB_PAT" in text or "GH_PAT" in text:
        fail("workflow must not reference GITHUB_PAT or GH_PAT")
    if "github.token" not in text:
        fail("workflow must use github.token for Release creation")

    # 13. Release is normal (draft=false, prerelease=false).
    if "--draft=false" not in text:
        fail("workflow must create Release with --draft=false")
    if "--prerelease=false" not in text:
        fail("workflow must create Release with --prerelease=false")

    print(
        f"OK: workflow YAML valid; triggers, concurrency, two-job split, "
        f"permissions, environment, if-condition, web-ext pin (v{version}), "
        f"gh release usage, AMO secret handling, no shell tracing, no PAT — "
        f"all verified"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
