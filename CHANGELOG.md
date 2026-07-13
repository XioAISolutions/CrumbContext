# Changelog

## Unreleased

- Consumed the one-shot `v0.1.0` release request after successful publication.
- Made the release agent idempotent by treating an existing release tag as a safe no-op.
- Added an inert release-request template for future versions.
- Added permanent public-PyPI verification across Python 3.10, 3.11, and 3.12 with exported benchmark and counterfactual proofs.
- Added a guarded provider-benchmark workflow using only the bundled public fixture, protected environment secrets, exact-request hashes, recall checks, credential-leak scanning, named routing profiles, response redaction, and private evidence artifacts.
- Added a tested provider-evidence validator and human-readable evidence summary generator.
- Made the release contract reusable across future versions instead of hard-coding the v0.1.0 release date.
- Added a documentation hub, provider-evidence guide, and post-release roadmap.
- Documented mandatory post-release request cleanup and the repeatable trusted-publishing lifecycle.
- Added a supported top-level Python API for block normalization, task specifications, baseline and routed requests, provider execution, and provider-native payload construction.
- Added duplicate block-ID rejection and explicit provider-instance option handling at the integration boundary.
- Added runnable offline Python examples and installed-wheel compatibility checks across Python 3.10, 3.11, and 3.12.
- Added a documented public-import stability policy and direct application integration guide.
- Added deterministic `safe-default`, `text-only`, `cache-heavy`, and `strict-exact` routing profiles with explicit safe overrides.
- Added resolved profile names and complete `RouterConfig` values to routing plans and routed request metadata.
- Added versioned route-plan, benchmark, counterfactual, provider-request, and provider-response schemas.
- Preserved legacy v0.1 evidence compatibility when schema markers are absent while rejecting unknown explicit schemas.
- Added optional provider response-body redaction for saved JSON and HTML without removing hashes, usage, routing policy, or evaluation.
- Added CLI, Python API, provider-evidence, compatibility, and redaction tests for the new policy surface.
- Added a responsive, searchable static documentation site generated directly from repository Markdown.
- Added local search, mobile navigation, canonical metadata, sitemap, `robots.txt`, and a custom 404 page without analytics, CDNs, or third-party runtime scripts.
- Added pull-request documentation previews, local-link and anchor validation, and least-privilege GitHub Pages deployment from Actions.
- Updated package metadata to point future PyPI releases at the configured GitHub Pages documentation URL.
- Added a separate supported async API that runs existing providers without blocking the event loop.
- Added normalized Anthropic Messages and OpenAI Responses streaming through Server-Sent Events without a mandatory async HTTP dependency.
- Added deterministic mock streaming, explicit complete/incomplete/failed/timeout/cancelled states, partial-result evidence, and response-text redaction.
- Added installed-wheel async imports, keyless examples, cancellation compatibility, and streaming contract tests across Python 3.10, 3.11, and 3.12.
- Added a versioned CC0 public workload manifest covering coding, research, operations, tool-heavy, and mixed-authority sessions.
- Added `crumbcontext workloads`, which evaluates five workloads across four named profiles and emits 20 inspectable deterministic results.
- Added workload-manifest, individual-result, and suite-result schemas with fail-closed validation, provenance, licensing, and SHA-256 fixture identity.
- Added aggregate JSON and HTML reports, per-run routing artifacts, a share card, five-lane coverage checks, and explicit planning-estimate claims boundaries.
- Added installed-wheel workload-suite validation and evidence export across Python 3.10, 3.11, and 3.12 without provider keys or paid calls.

## 0.1.0 - 2026-07-12

- Added safety-first routing across exact, cache, CRUMB, image, and summary lanes.
- Added exact-anchor extraction and native-text CRUMB sidecars for paths, hashes, IDs, URLs, dates, amounts, email addresses, environment variables, and other precision-critical values.
- Added sanitized historical-context image rendering and deterministic stale-context summaries.
- Added machine-readable routing plans, interactive HTML reports, and shareable benchmark cards.
- Added a deterministic offline benchmark with image-enabled and text-only self-checks.
- Added `crumbcontext counterfactual`, a same-task baseline-versus-routed measurement harness.
- Added canonical task, source, request, and response hashes; normalized usage and latency records; exact-value recall; required-rule recall; JSON validity; task completion; and response-similarity scoring.
- Added a deterministic offline mock provider that labels its token accounting as simulated rather than billed.
- Added a safety-preserving Anthropic Messages adapter with authority-preserving role mapping, exact-value sidecars, eligible historical image blocks, explicit cache breakpoints, provider-reported usage, latency, and request IDs.
- Added a safety-preserving OpenAI Responses adapter with native system, developer, user, and assistant roles; assistant phase preservation; verified image data URLs; exact-value sidecars; `store: false`; and fail-closed unknown-authority handling.
- Added provider-reported OpenAI cache reads, cache-write details when returned, reasoning/output tokens, latency, request and response IDs, request-body hashes, and hashed prompt-cache identifiers.
- Added path confinement, artifact hash verification, image format and size checks, and explicit text-only fallbacks.
- Added mocked HTTP coverage for provider success, errors, caching, images, privacy redaction, and complete baseline-versus-routed executions without paid CI calls or repository secrets.
- Added Python 3.10, 3.11, and 3.12 CI, distribution validation, CodeQL, Dependabot, Codespaces, issue forms, contribution guidance, security policy, citation metadata, and trusted-publishing workflow scaffolding.
- Added a machine-checkable release contract, isolated wheel smoke test, tag-to-version verification, release process, and v0.1.0 release notes.
- Added one-tag GitHub and PyPI release automation with SHA-256 checksums, a release manifest, SPDX 2.3 SBOM, GitHub provenance/SBOM attestations, verified release assets, and OIDC Trusted Publishing without a long-lived PyPI token.
- Expanded PyPI search metadata, typed-package classifiers, project links, and Python 3.10-compatible release tooling.
