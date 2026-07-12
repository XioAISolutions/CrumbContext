# Release process

This is the authoritative checklist for publishing CrumbContext. Build validation, GitHub release creation, checksums, SBOM generation, provenance, PyPI upload, and public-index verification are automated.

CrumbContext `0.1.0` is already published. The pending PyPI publisher used for the first release has become the project's active trusted publisher.

## Release invariants

A release must not proceed unless:

- `pyproject.toml`, `crumbcontext/__init__.py`, and `CITATION.cff` contain the same version;
- the release tag is exactly `v<version>`;
- tests pass on Python 3.10, 3.11, and 3.12;
- the offline benchmark and mock counterfactual pass;
- the built wheel installs and runs outside the source tree;
- `twine check` passes for the wheel and source distribution;
- CodeQL passes on the exact release commit;
- documentation names the supported Anthropic and OpenAI adapters accurately;
- the GitHub release includes the wheel, source archive, SHA-256 checksums, release manifest, and SPDX SBOM;
- GitHub provenance and SBOM attestations are created;
- the exact version installs from the public PyPI index after publishing;
- no provider-savings claim is published without provider, model, fixture, hashes, routing policy, token accounting, exact recall, task completion, and response-quality results.

## Prepare a version

Set the next version consistently in:

- `pyproject.toml`;
- `crumbcontext/__init__.py`;
- `CITATION.cff`;
- `CHANGELOG.md`;
- `docs/RELEASE_NOTES_v<version>.md`.

Run the local contract:

```bash
VERSION=0.2.0
python scripts/release-check.py --tag "v$VERSION"
python -m pytest
python -m build
python -m twine check dist/*
```

Never overwrite or reuse a version already uploaded to PyPI. Fix forward with a new patch release.

## Trusted Publishing

The active PyPI Trusted Publisher must continue to match:

| Field | Value |
|---|---|
| PyPI project | `crumb-context` |
| GitHub owner | `XioAISolutions` |
| Repository | `CrumbContext` |
| Workflow | `publish.yml` |
| Environment | `pypi` |

No PyPI password or API token belongs in the repository. Publishing uses GitHub OIDC.

The GitHub `pypi` environment may optionally require reviewers or deployment protections. Those controls must not change the environment name expected by PyPI.

## Agent-assisted deployment

Copy the inert template rather than editing it in place:

```bash
cp .github/release-request.example.json .github/release-request.json
```

Replace `NEXT_VERSION` with the package version:

```json
{
  "publish": true,
  "version": "0.2.0",
  "branch": "main"
}
```

Commit the request through a pull request. After it reaches `main`:

1. normal CI validates the exact commit on Python 3.10, 3.11, and 3.12;
2. the release agent validates the request against package metadata;
3. the agent refuses the request when the tag already exists;
4. the agent waits for CodeQL on the same commit;
5. the agent dispatches `publish.yml` with the exact tag and commit;
6. the publish workflow builds, attests, releases, and publishes;
7. `verify-pypi.yml` independently installs and runs the public package.

A request is rejected when:

- `publish` is not exactly `true`;
- the version differs from package metadata;
- the branch is not `main`;
- an optional commit differs from the CI-tested commit;
- release notes are missing;
- CI or CodeQL fails.

An already existing release tag is a safe no-op.

## Mandatory post-release cleanup

After public-index verification passes, remove `.github/release-request.json` from `main` in a small cleanup commit or pull request.

Do not leave a consumed release request active. The duplicate-tag guard prevents republishing, but removing the request keeps normal CI runs quiet and makes the next release explicit.

Keep `.github/release-request.example.json`; it is an inert template.

## Manual fallback

A maintainer may create and push the tag manually:

```bash
VERSION=0.2.0
git checkout main
git pull --ff-only
git tag -a "v$VERSION" -m "CrumbContext v$VERSION"
git push origin "v$VERSION"
```

`publish.yml` supports both direct tag pushes and release-agent dispatches.

## What the publish workflow does

The workflow:

1. checks out the exact CI-tested commit or tag;
2. confirms the tag equals `v<package-version>` and the checkout matches the requested commit;
3. builds one wheel and one source distribution;
4. runs `twine check`;
5. installs the wheel outside the source tree and runs the benchmark and mock counterfactual;
6. creates a release manifest, SPDX 2.3 SBOM, and `SHA256SUMS.txt`;
7. creates GitHub provenance and SBOM attestations;
8. creates or updates the GitHub release from matching release notes;
9. attaches all verified release assets;
10. publishes only the wheel and source distribution to PyPI using OIDC.

Expected release assets for version `X.Y.Z`:

```text
crumb_context-X.Y.Z-py3-none-any.whl
crumb_context-X.Y.Z.tar.gz
crumb-context-X.Y.Z-release-manifest.json
crumb-context-X.Y.Z.spdx.json
SHA256SUMS.txt
```

## Independent public-index verification

`.github/workflows/verify-pypi.yml` runs when a GitHub release is published and may also be dispatched manually.

For Python 3.10, 3.11, and 3.12 it:

1. installs the exact version only from `https://pypi.org/simple`;
2. verifies installed package metadata and CLI version;
3. runs the benchmark outside the repository;
4. runs the mock counterfactual outside the repository;
5. exports the generated proof artifacts.

The installer retries briefly because PyPI index propagation may lag behind the upload.

Manual clean-install equivalent:

```bash
VERSION=0.1.0
python -m venv /tmp/crumbcontext-release-test
/tmp/crumbcontext-release-test/bin/python -m pip install --upgrade pip
/tmp/crumbcontext-release-test/bin/python -m pip install \
  --index-url https://pypi.org/simple \
  "crumb-context==$VERSION"
cd /tmp
/tmp/crumbcontext-release-test/bin/crumbcontext --version
/tmp/crumbcontext-release-test/bin/crumbcontext benchmark --out crumbcontext-proof
/tmp/crumbcontext-release-test/bin/crumbcontext counterfactual \
  --provider mock \
  --out crumbcontext-counterfactual
```

Both generated JSON result files must contain `"passed": true`.

## Verify release integrity

Download release assets into one directory and run:

```bash
sha256sum --check SHA256SUMS.txt
```

Verify provenance with GitHub CLI:

```bash
gh attestation verify crumb_context-X.Y.Z-py3-none-any.whl \
  --repo XioAISolutions/CrumbContext

gh attestation verify crumb_context-X.Y.Z.tar.gz \
  --repo XioAISolutions/CrumbContext
```

The release manifest records the tag, commit, package metadata, dependency declaration, artifact sizes, and SHA-256 digests. The SPDX file records the package and declared dependencies.

## Provider-measured evidence

Provider calls are not required to publish a package. For measured evidence, run the same fixture and task against baseline and routed payloads:

```bash
export ANTHROPIC_API_KEY='...'
crumbcontext counterfactual --provider anthropic --model MODEL --out anthropic-proof

export OPENAI_API_KEY='...'
crumbcontext counterfactual --provider openai --model MODEL --out openai-proof
```

Publish the provider name, exact model identifier, fixture, request hashes, routing plan, token accounting, latency, exact recall, task completion, and response similarity. Never extrapolate one fixture into a universal cost claim.

## Failure policy

- If tag and package version differ, stop.
- If the requested commit differs from the CI-tested commit, stop.
- If the tag already exists, do not dispatch another publish.
- If CI or CodeQL fails, stop.
- If the isolated wheel smoke test fails, stop.
- If checksums, SBOM, or attestations fail, stop.
- If public-index installation fails after propagation retries, investigate before announcing the release.
- If exact recall is below 100% for a benchmark requiring exact values, stop and inspect the bundle.
- If a provider adapter cannot preserve role semantics, use text-only routing or exact-text fallback.
- If PyPI publishing partially succeeds, never overwrite the published version; fix forward with a new patch version.
