# Changelog

## Unreleased

- Added `crumbcontext counterfactual`, a same-task baseline-versus-routed comparison harness.
- Added canonical request/source hashes, normalized usage and latency records, exact-value recall, JSON validity, required-string recall, task completion, and response-similarity scoring.
- Added a deterministic offline mock provider, comparison HTML report, machine-readable result, and shareable counterfactual card.
- Added a safety-preserving Anthropic Messages adapter with native role mapping, exact-value sidecars, eligible historical image blocks, explicit prompt-cache breakpoints, provider-reported usage, latency, and request IDs.
- Added a safety-preserving OpenAI Responses adapter with native system, developer, user, and assistant roles; verified image data URLs; exact-value sidecars; assistant phase preservation; and fail-closed unknown-authority handling.
- Added provider-reported OpenAI cache reads, cache writes, reasoning tokens, latency, request and response IDs, request-body hashes, `store: false`, and hashed prompt-cache identifiers.
- Added fail-closed exact-text behavior for unsafe image-role mappings and mocked HTTP coverage for success, errors, caching, images, and full counterfactual runs.
- Added provider documentation without making universal provider-billing claims.
- Expanded CI to verify the counterfactual on Python 3.10, 3.11, and 3.12.

## 0.1.0

- Safety-first routing across exact, cache, CRUMB, image, and summary lanes.
- Exact-anchor extraction and native-text CRUMB sidecars.
- Sanitized historical-context PNG rendering.
- Deterministic summaries and machine-readable routing plans.
- Interactive HTML report and shareable benchmark card.
- Self-verifying image and text-only benchmark modes.
