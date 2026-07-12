# Release process

This is the authoritative checklist for publishing CrumbContext. The repository-side checks are automated; GitHub and PyPI account settings still require an administrator.

## Release invariants

A release must not proceed unless:

- `pyproject.toml`, `crumbcontext/__init__.py`, and `CITATION.cff` contain the same version;
- the release tag is exactly `v<version>`;
- tests pass on Python 3.10, 3.11, and 3.12;
- the offline benchmark and mock counterfactual pass;
- the built wheel installs and runs from an isolated virtual environment;
- `twine check` passes for the wheel and source distribution;
- CodeQL passes;
- documentation names both Anthropic and OpenAI adapters accurately;
- no provider savings claim is published without provider, model, fixture, hashes, routing policy, and quality results.

Run the local contract:

```bash
python scripts/release-check.py --tag v0.1.0
python -m pytest
python -m build
python -m twine check dist/*
```

## One-time administrator setup

Before publishing the first GitHub release:

1. Create the PyPI project/trusted publisher for package `crumb-context`.
2. Configure the trusted publisher with:
   - owner: `XioAISolutions`
   - repository: `CrumbContext`
   - workflow: `publish.yml`
   - environment: `pypi`
3. In GitHub, create or confirm the `pypi` environment.
4. Require the CI and CodeQL checks on `main` through a branch ruleset.
5. Add the repository description, topics, and social preview listed in `docs/LAUNCH_KIT.md`.

Do not create the GitHub release before trusted publishing is configured. Publishing the release triggers `.github/workflows/publish.yml`.

## Publish v0.1.0

1. Confirm `main` is green and contains the release-hardening merge.
2. Open `docs/RELEASE_NOTES_v0.1.0.md` and use it as the GitHub release body.
3. Create tag and release `v0.1.0` from `main`.
4. Publish the release.
5. Watch the `Publish to PyPI` workflow.
6. Confirm the workflow built from the release tag, verified `v0.1.0` against package version `0.1.0`, passed the release contract, passed `twine check`, and completed trusted publishing.

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
- If exact recall is below 100% for a benchmark that requires exact values, stop and inspect the bundle.
- If a provider adapter cannot preserve role semantics, use text-only routing or exact-text fallback.
- If publishing partially succeeds, do not overwrite an existing PyPI version. Fix forward with a new patch version.
