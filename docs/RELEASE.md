# Release process

This is the authoritative checklist for publishing CrumbContext. Repository-side build, validation, release creation, checksums, SBOM generation, provenance, and PyPI upload are automated. GitHub and PyPI account settings still require an administrator once.

## Release invariants

A release must not proceed unless:

- `pyproject.toml`, `crumbcontext/__init__.py`, and `CITATION.cff` contain the same version;
- the pushed tag is exactly `v<version>`;
- tests pass on Python 3.10, 3.11, and 3.12;
- the offline benchmark and mock counterfactual pass;
- the built wheel installs and runs from an isolated virtual environment;
- `twine check` passes for the wheel and source distribution;
- CodeQL passes;
- documentation names both Anthropic and OpenAI adapters accurately;
- the GitHub release includes the wheel, source archive, SHA-256 checksums, release manifest, and SPDX SBOM;
- GitHub provenance and SBOM attestations are created for the Python distributions;
- no provider-savings claim is published without provider, model, fixture, hashes, routing policy, token accounting, exact recall, task completion, and response-quality results.

Run the local contract:

```bash
python scripts/release-check.py --tag v0.1.0
python -m pytest
python -m build
python -m twine check dist/*
```

## One-time administrator setup

### 1. Create the GitHub environment

In `XioAISolutions/CrumbContext`:

1. Open **Settings → Environments**.
2. Create an environment named exactly `pypi`.
3. Optionally require an administrator approval before deployment. This is recommended because the environment gates the final upload job.

No PyPI token or repository secret is required.

### 2. Register the pending PyPI Trusted Publisher

The PyPI project does not need to exist first. PyPI supports a **pending publisher** that creates the project during the first successful trusted publish.

While signed in to the intended PyPI owner account, open the account publishing settings and add a GitHub publisher using exactly:

| Field | Value |
|---|---|
| PyPI project name | `crumb-context` |
| GitHub owner | `XioAISolutions` |
| Repository name | `CrumbContext` |
| Workflow filename | `publish.yml` |
| Environment name | `pypi` |

Important: a pending publisher does not reserve the package name. Push the first release tag soon after registering it.

### 3. Finish GitHub repository settings

- Require CI and CodeQL on `main` through a branch ruleset.
- Add the description, topics, and social preview from `docs/LAUNCH_KIT.md`.
- Enable Discussions only if it will be actively maintained.

## What the tag pipeline does

A tag matching `v*.*.*` triggers `.github/workflows/publish.yml`.

The workflow then:

1. checks out the exact tag;
2. confirms the tag equals `v<package-version>`;
3. builds one wheel and one source distribution;
4. runs `twine check`;
5. installs the wheel outside the source tree and runs the benchmark and mock counterfactual;
6. creates a release manifest, SPDX 2.3 SBOM, and `SHA256SUMS.txt`;
7. creates GitHub provenance and SBOM attestations;
8. creates or updates the GitHub release using the matching `docs/RELEASE_NOTES_<tag>.md` file;
9. attaches all verified release assets;
10. publishes only the wheel and source distribution to PyPI using GitHub OIDC.

The GitHub release is created before the PyPI job. The PyPI job still requires the `pypi` environment and the matching trusted publisher.

## Publish v0.1.0

After the one-time setup is complete and `main` is green:

```bash
git checkout main
git pull --ff-only
git tag -a v0.1.0 -m "CrumbContext v0.1.0"
git push origin v0.1.0
```

Do not manually upload files to PyPI and do not create a duplicate PyPI API token. The tag push is the release command.

Watch the **Publish release** workflow. It should finish in this order:

```text
build → release → publish
```

Expected GitHub release assets:

```text
crumb_context-0.1.0-py3-none-any.whl
crumb_context-0.1.0.tar.gz
crumb-context-0.1.0-release-manifest.json
crumb-context-0.1.0.spdx.json
SHA256SUMS.txt
```

## Verify release integrity

Download the release assets into one directory and verify:

```bash
sha256sum --check SHA256SUMS.txt
```

Verify GitHub provenance with a current GitHub CLI:

```bash
gh attestation verify crumb_context-0.1.0-py3-none-any.whl \
  --repo XioAISolutions/CrumbContext

gh attestation verify crumb_context-0.1.0.tar.gz \
  --repo XioAISolutions/CrumbContext
```

The release manifest records the tag, commit, package metadata, dependency declaration, artifact sizes, and SHA-256 digests. The SPDX file records the package and declared dependencies.

## Clean-install verification

After PyPI publishing succeeds:

```bash
python -m venv /tmp/crumbcontext-release-test
/tmp/crumbcontext-release-test/bin/python -m pip install --upgrade pip
/tmp/crumbcontext-release-test/bin/python -m pip install crumb-context==0.1.0
cd /tmp
/tmp/crumbcontext-release-test/bin/crumbcontext --version
/tmp/crumbcontext-release-test/bin/crumbcontext benchmark --out crumbcontext-proof
/tmp/crumbcontext-release-test/bin/crumbcontext counterfactual --provider mock --out crumbcontext-counterfactual
```

Expected version output:

```text
crumbcontext 0.1.0
```

Both generated JSON result files must contain `"passed": true`.

## Provider-measured evidence

Provider calls are not required to publish the package. When publishing a measured benchmark later, run the same fixture and task against both payloads:

```bash
export ANTHROPIC_API_KEY='...'
crumbcontext counterfactual --provider anthropic --model MODEL --out anthropic-proof

export OPENAI_API_KEY='...'
crumbcontext counterfactual --provider openai --model MODEL --out openai-proof
```

Publish the provider name, exact model identifier, fixture, request hashes, routing plan, token accounting, latency, exact recall, task completion, and response similarity. Never extrapolate one synthetic result into a universal cost claim.

## Failure policy

- If the tag and package version differ, stop.
- If the isolated wheel smoke test fails, stop.
- If checksums, the SBOM, or attestations fail, stop.
- If exact recall is below 100% for a benchmark that requires exact values, stop and inspect the bundle.
- If a provider adapter cannot preserve role semantics, use text-only routing or exact-text fallback.
- If PyPI publishing partially succeeds, never overwrite version `0.1.0`. Fix forward with a new patch version.
