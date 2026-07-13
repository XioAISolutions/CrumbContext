# GitHub setup

Use this checklist for the public `XioAISolutions/CrumbContext` repository.

## About panel

**Description**

```text
Safety-first context routing for AI agents. Exact facts stay exact while stale context takes a cheaper, explainable lane.
```

**Website**

```text
https://xioaisolutions.github.io/CrumbContext/
```

**Topics**

See [`LAUNCH_KIT.md`](LAUNCH_KIT.md).

**Social preview**

Upload `docs/assets/social-preview.png` in **Settings → General → Social preview**.

## Features

Enable:

- Issues;
- Discussions when a maintainer will actively moderate them;
- Projects only when there is a maintained public roadmap;
- repository rulesets when the organization supports them.

Disable the Wiki unless it will contain material not already maintained in `docs/`.

## Main branch governance

Create a `main` ruleset that:

- requires a pull request before merging;
- requires the `CI / build` and Python 3.10–3.12 test jobs;
- requires CodeQL analysis;
- requires branches to be up to date before merge;
- blocks force pushes and branch deletion;
- allows squash merging;
- keeps an explicit administrator bypass for emergency repair.

Add the installed-wheel Python API and documentation build checks after they have run on `main` and appear as selectable required checks.

## GitHub Pages

The repository includes `.github/workflows/docs.yml`, which builds the site from repository Markdown and deploys it with GitHub Actions.

In **Settings → Pages → Build and deployment**, select:

```text
Source: GitHub Actions
```

The expected site is:

```text
https://xioaisolutions.github.io/CrumbContext/
```

The workflow uses:

- local CSS and JavaScript only;
- no analytics or third-party runtime scripts;
- local search generated during the build;
- pull-request preview artifacts;
- local-link and anchor validation;
- the `github-pages` deployment environment;
- `pages: write` and `id-token: write` only in the deployment job.

After the first deployment, verify the home page, mobile navigation, search, canonical URLs, social image, and a deep link such as `/CrumbContext/python-api/`.

## Environments and secrets

### `pypi`

Trusted publishing is configured for:

```text
project: crumb-context
owner: XioAISolutions
repository: CrumbContext
workflow: publish.yml
environment: pypi
```

Optionally add a required reviewer without changing the environment name.

### `provider-benchmarks`

Create this environment only when real provider measurement is ready. Recommended controls:

- limit deployment branches to `main`;
- require a maintainer reviewer;
- store `ANTHROPIC_API_KEY` and/or `OPENAI_API_KEY` as environment secrets rather than broad repository secrets;
- keep provider budgets and permissions minimal.

Never add provider keys to workflow inputs, issues, pull requests, fixtures, or artifacts.

## Releases and PyPI

CrumbContext `v0.1.0` is published. Future releases use the repeatable process in [`RELEASE.md`](RELEASE.md):

1. update version metadata, changelog, and release notes;
2. merge a validated one-shot release request;
3. let CI, CodeQL, attestations, GitHub Release, and PyPI Trusted Publishing complete;
4. independently install and run the public package on Python 3.10–3.12;
5. remove the consumed release request.

## Organization visibility

- Pin CrumbContext on the XioAISolutions organization page.
- Pin it on the maintainer profile.
- Link it from CrumbLLM and crumb-format.
- Keep the CrumbLLM migration notice pointing to the standalone repository.
