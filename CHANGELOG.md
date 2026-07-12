# Changelog

## Unreleased

No unreleased changes.

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
