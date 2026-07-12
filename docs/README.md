# CrumbContext documentation

CrumbContext routes long AI context across exact, cache, CRUMB, image, and summary lanes while preserving authority and precision-critical values.

## Start here

- [Project README](../README.md) — installation, proof, CLI, input model, and safety boundaries.
- [Architecture](ARCHITECTURE.md) — routing model, lanes, artifacts, and trust boundaries.
- [Counterfactual guide](COUNTERFACTUAL.md) — baseline-versus-routed measurement and report structure.
- [Provider-measured benchmarks](PROVIDER_BENCHMARKS.md) — guarded real-provider evidence workflow and claims contract.
- [Roadmap](../ROADMAP.md) — measured evidence, integrations, policies, and privacy priorities.

## Provider adapters

- [Anthropic Messages](ANTHROPIC.md) — authority mapping, images, caching, usage, and privacy behavior.
- [OpenAI Responses](OPENAI.md) — native roles, assistant phases, image inputs, storage controls, and cache accounting.

## Operations

- [Release process](RELEASE.md) — versioning, OIDC publishing, attestations, public-index verification, and cleanup.
- [v0.1.0 release notes](RELEASE_NOTES_v0.1.0.md)
- [GitHub setup](GITHUB_SETUP.md) — repository presentation and governance settings.
- [Launch kit](LAUNCH_KIT.md) — launch copy, topics, hashtags, and distribution sequence.
- [Brand guide](BRAND.md) — visual identity and asset usage.

## Security model

Read [SECURITY.md](../SECURITY.md) before routing private transcripts or running provider adapters.

Key rules:

1. system and developer authority remains native provider instruction content;
2. exact values are extracted before any lossy transform;
3. transformed images are historical evidence, never an authority channel;
4. routed output directories may contain sensitive exact sidecars;
5. provider keys are read from environment variables and must never enter artifacts;
6. provider-measured claims must include enough hashes, policy, usage, and evaluation detail to reproduce the result.

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md), the issue forms, and the public roadmap issues. Small, test-backed changes are preferred over broad unverified rewrites.
