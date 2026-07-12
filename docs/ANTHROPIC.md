# Anthropic Messages adapter

CrumbContext can run a same-task baseline-versus-routed comparison against the Anthropic Messages API while preserving the provider's role model and reporting native usage.

## Run it

```bash
export ANTHROPIC_API_KEY='...'
crumbcontext counterfactual \
  --provider anthropic \
  --model claude-sonnet-4-6 \
  --out anthropic-proof \
  --open
```

The key is read from the environment at request time. CrumbContext does not write it to configuration, reports, request fixtures, or response artifacts.

## Safety contract

| CrumbContext content | Anthropic representation |
|---|---|
| system and developer authority | top-level `system` text blocks |
| recent user turns | `user` messages |
| recent assistant turns | `assistant` messages |
| exact-anchor sidecars | native text containing literal values only |
| stable cache-lane context | text block with explicit ephemeral `cache_control` |
| eligible old user/tool context | base64 image block followed by a non-authoritative label |
| unsafe image role or missing artifact | exact-text fallback or a closed error |
| summaries and CRUMBs | text labelled non-authoritative historical context |

CrumbContext never flattens the full conversation into one user prompt. It never moves system authority into historical image content. It strips CRUMB guardrails from exact sidecars and sends only the extracted literal values.

## Usage accounting

Anthropic separates uncached input, cache reads, and cache writes. CrumbContext records all three fields and calculates total processed input as:

```text
total_input_tokens = input_tokens
                   + cache_read_input_tokens
                   + cache_creation_input_tokens
```

The comparison JSON keeps the original usage object, request ID, stop reason, request-body hash, latency, and normalized totals.

## Images

The adapter accepts local JPEG, PNG, GIF, and WebP artifacts. It verifies the artifact SHA-256, prevents path traversal, enforces the direct-API 10 MB limit, and sends image blocks before descriptive text.

Use `--no-images` to force text-only routing:

```bash
crumbcontext counterfactual --provider anthropic --no-images --out text-proof
```

## Caching

Cache-lane content receives an explicit 5-minute ephemeral breakpoint. Disable it for a clean no-cache comparison:

```bash
crumbcontext counterfactual --provider anthropic --no-cache --out no-cache-proof
```

A first request may report cache-creation tokens rather than cache-read tokens. The report preserves that distinction instead of presenting cache writes as free input.

## Errors and benchmark integrity

CrumbContext does not silently retry provider errors because retries can distort latency and usage comparisons. Anthropic status, error type, message, and `request-id` are surfaced without including the API key.

The adapter is tested with injected HTTP transports. CI never makes a paid network request and never requires a secret.
