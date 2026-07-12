# GitHub setup

Use this checklist after the empty `XioAISolutions/CrumbContext` repository is created.

## About panel

**Description**

```text
Safety-first context routing for AI agents. Exact facts stay exact while stale context takes a cheaper lane.
```

**Topics**

See [`LAUNCH_KIT.md`](LAUNCH_KIT.md).

**Social preview**

Upload `docs/assets/social-preview.svg`.

## Features

Enable:

- Issues
- Discussions
- Projects only when there is a maintained public roadmap
- Preserve this repository if the organization supports repository rulesets

Disable the Wiki unless it will contain material not already maintained in `docs/`.

## Main branch protection

After the initial import:

- require a pull request before merging;
- require the `CI / test` and `CI / build` checks;
- dismiss stale approvals after new commits when outside contributors arrive;
- block force pushes and branch deletion;
- allow squash merging;
- use linear history if the team prefers it consistently.

## Releases and PyPI

1. Configure a PyPI trusted publisher for repository `XioAISolutions/CrumbContext`, workflow `publish.yml`, environment `pypi`.
2. Confirm CI passes from a clean GitHub runner.
3. Publish GitHub release `v0.1.0`.
4. The release workflow builds and publishes the package.
5. Verify `pip install crumb-context` from a clean virtual environment.

## Organization visibility

- Pin CrumbContext on the XioAISolutions organization page.
- Pin it on the maintainer profile.
- Link it from CrumbLLM and crumb-format.
- Replace the CrumbLLM incubator with a migration notice after the standalone repo is green.
