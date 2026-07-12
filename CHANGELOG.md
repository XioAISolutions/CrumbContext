# Changelog

## Unreleased

- Added `crumbcontext counterfactual`, a same-task baseline-versus-routed comparison harness.
- Added canonical request/source hashes, normalized usage and latency records, exact-value recall, JSON validity, required-string recall, task completion, and response-similarity scoring.
- Added a deterministic offline mock provider, comparison HTML report, machine-readable result, and shareable counterfactual card.
- Added a provider contract and custom fixture documentation without making provider-billing claims.
- Expanded CI to verify the counterfactual on Python 3.10, 3.11, and 3.12.

## 0.1.0

- Safety-first routing across exact, cache, CRUMB, image, and summary lanes.
- Exact-anchor extraction and native-text CRUMB sidecars.
- Sanitized historical-context PNG rendering.
- Deterministic summaries and machine-readable routing plans.
- Interactive HTML report and shareable benchmark card.
- Self-verifying image and text-only benchmark modes.
