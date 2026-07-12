# CrumbContext v0.1.0

**Give every AI the context it needs—not the entire conversation.**

CrumbContext v0.1.0 is the first public alpha of a safety-first context router for long AI sessions. It protects authority and exact values before routing stale context to one of five explainable lanes: exact text, provider cache candidates, CRUMB memory, sanitized images, or deterministic summaries.

## Highlights

- Five-lane context routing with a reason recorded for every block.
- Exact-anchor extraction for paths, hashes, UUIDs, URLs, emails, dates, money, environment variables, and long identifiers.
- Native-text CRUMB sidecars so exact facts never depend on image recognition.
- Sanitized historical-context images and deterministic summaries.
- Interactive HTML reports, machine-readable plans, and share cards.
- Offline self-verifying benchmark with image-enabled and text-only policies.
- Same-task baseline-versus-routed counterfactual harness.
- Safety-preserving Anthropic Messages adapter.
- Safety-preserving OpenAI Responses adapter.
- Provider usage, latency, request/response hashes, exact recall, rule recall, JSON validity, task completion, and response-similarity records.

## Reproducible offline proof

```bash
python -m pip install crumb-context==0.1.0
crumbcontext benchmark --out proof --open
crumbcontext counterfactual --provider mock --out comparison --open
```

The bundled fixture reports a **65.8% deterministic planning reduction** while preserving **31/31 exact anchors**. This is a fixture-specific planning estimate, not a universal provider-billing claim.

## Anthropic Messages

```bash
export ANTHROPIC_API_KEY='...'
crumbcontext counterfactual \
  --provider anthropic \
  --model claude-sonnet-4-6 \
  --out anthropic-proof \
  --open
```

The adapter preserves system/developer authority, user/assistant ordering, exact-text sidecars, eligible historical images, and prompt-cache usage details.

## OpenAI Responses

```bash
export OPENAI_API_KEY='...'
crumbcontext counterfactual \
  --provider openai \
  --model gpt-5.6 \
  --out openai-proof \
  --open
```

The adapter preserves native system/developer/user/assistant roles, assistant phases when supplied, verified image data URLs, provider usage details, and `store: false`. Raw prompt-cache keys are never written to reports.

## Release integrity

The GitHub release includes:

- the universal Python wheel;
- the source distribution;
- `SHA256SUMS.txt` covering every attached release artifact except the checksum file itself;
- a machine-readable release manifest containing the exact tag, commit, package metadata, dependency declaration, sizes, and SHA-256 digests;
- an SPDX 2.3 SBOM covering CrumbContext and its declared runtime dependencies.

The wheel and source archive also receive GitHub-hosted SLSA provenance and SPDX SBOM attestations signed through short-lived OIDC credentials. They can be verified with `gh attestation verify` against `XioAISolutions/CrumbContext`.

PyPI publishing uses a Trusted Publisher. No long-lived PyPI password or repository API token is stored in GitHub.

## Safety boundaries

- Provider calls are explicit and opt-in.
- API keys are read from environment variables and are not stored.
- Exact sidecars intentionally contain sensitive literal values and must be protected.
- Historical compressed context is labelled non-authoritative.
- Unsafe or ambiguous mappings fail closed to exact text or a clear error.
- v0.1.0 is an alpha reference implementation, not a universal proxy, DLP system, or guaranteed cost reducer.

## Verification

The release is gated by:

- Python 3.10, 3.11, and 3.12 tests;
- offline benchmark and mock counterfactual checks;
- isolated installation and execution of the built wheel;
- wheel and source-distribution validation with `twine check`;
- deterministic checksum, manifest, and SPDX-generation tests;
- release metadata and documentation consistency checks;
- CodeQL analysis;
- exact tag-to-version verification;
- GitHub provenance and SBOM attestation creation before trusted PyPI publishing.

## Documentation

- [README](https://github.com/XioAISolutions/CrumbContext#readme)
- [Architecture](https://github.com/XioAISolutions/CrumbContext/blob/main/docs/ARCHITECTURE.md)
- [Anthropic adapter](https://github.com/XioAISolutions/CrumbContext/blob/main/docs/ANTHROPIC.md)
- [OpenAI adapter](https://github.com/XioAISolutions/CrumbContext/blob/main/docs/OPENAI.md)
- [Release process](https://github.com/XioAISolutions/CrumbContext/blob/main/docs/RELEASE.md)
- [Security policy](https://github.com/XioAISolutions/CrumbContext/blob/main/SECURITY.md)

**Core rule:** Exact facts never become pixels.
