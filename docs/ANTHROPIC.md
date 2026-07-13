# Anthropic Messages adapter

CrumbContext can run a same-task baseline-versus-routed comparison against the Anthropic Messages API while preserving the provider's role model and reporting native usage.

## Run it

```bash
export ANTHROPIC_API_KEY='...'
crumbcontext counterfactual \
  --provider anthropic \
  --model claude-fable-5 \
  --max-tokens 4096 \
  --out anthropic-proof \
  --open
```

The key is read from the environment at request time. CrumbContext does not write it to configuration, reports, request fixtures, or response artifacts.

## Claude Fable 5 and Claude Mythos 5

`claude-fable-5` is the adapter default. `claude-mythos-5` uses the same Messages API surface but is available only to approved Project Glasswing customers.

Adaptive thinking is always enabled when the `thinking` parameter is omitted. CrumbContext intentionally continues to omit `thinking`, `temperature`, and assistant prefills. Thinking and visible output share the request's output allowance, so the adapter and CLI default to `max_tokens=4096`. Raise `--max-tokens` when a response ends with `stop_reason: "max_tokens"`.

Fable 5 can return a classifier refusal as HTTP 200 with `stop_reason: "refusal"`. CrumbContext reports the refusal category, explanation, and request ID instead of mislabelling it as missing text. By default, Fable 5 requests also enable Anthropic's server-side fallback beta with `claude-opus-4-8`:

```text
anthropic-beta: server-side-fallback-2026-06-01
fallbacks: [{"model": "claude-opus-4-8"}]
```

Disable that behavior for a refusal-only measurement:

```bash
crumbcontext counterfactual \
  --provider anthropic \
  --model claude-fable-5 \
  --no-fallback \
  --out fable-no-fallback
```

Fallback is attached only to Fable 5 requests. Anthropic documents that Mythos 5 does not include Fable's safety classifier, so CrumbContext does not send the Fable-only beta field to Mythos.

A fallback response records the serving model in the normalized response and preserves `fallback` content blocks plus `usage.iterations` in `raw_usage`.

### Retention troubleshooting

Fable 5 and Mythos 5 require 30-day data retention and are not eligible for zero data retention. An organization restricted to ZDR can receive a 400 when using these models; confirm the organization's model-retention policy before debugging the request payload.

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

The comparison JSON keeps the original usage object, request ID, stop reason, stop details, request-body hash, latency, fallback evidence, and normalized totals.

## Images

The adapter accepts local JPEG, PNG, GIF, and WebP artifacts. It verifies the artifact SHA-256, prevents path traversal, enforces the direct-API 10 MB limit, and sends image blocks before descriptive text.

`safe-default` remains at 1568 px for broad model compatibility. For Fable 5, Mythos 5, Opus 4.7+, or Sonnet 5, use the high-resolution profile:

```bash
crumbcontext counterfactual \
  --provider anthropic \
  --profile frontier-vision \
  --out frontier-vision-proof
```

The profile renders at 2576×1196 and records the exact dimensions in the routing plan. Exact values remain in native-text sidecars; they never depend on pixels.

Use `--no-images` to force text-only routing:

```bash
crumbcontext counterfactual --provider anthropic --no-images --out text-proof
```

## Caching

Anthropic allows no more than four explicit cache breakpoints. CrumbContext deterministically keeps the last four marked cache blocks across the complete `system` + `messages` prefix and strips earlier markers before sending the request.

The default TTL is five minutes. Select the one-hour variant explicitly:

```bash
crumbcontext counterfactual \
  --provider anthropic \
  --cache-ttl 1h \
  --out one-hour-cache-proof
```

The emitted values are:

```json
{"type": "ephemeral"}
{"type": "ephemeral", "ttl": "1h"}
```

On the Claude API, the minimum cacheable prefix is currently 512 tokens for Fable 5 and Mythos 5, and 1,024 tokens for Opus 4.8. Shorter marked prefixes are processed normally without a cache write; inspect `cache_creation_input_tokens` and `cache_read_input_tokens` rather than assuming a hit.

Disable cache hints for a clean no-cache comparison:

```bash
crumbcontext counterfactual --provider anthropic --no-cache --out no-cache-proof
```

A first request may report cache-creation tokens rather than cache-read tokens. The report preserves that distinction instead of presenting cache writes as free input.

## Errors and benchmark integrity

CrumbContext does not silently retry ordinary provider errors because retries can distort latency and usage comparisons. The only built-in rerun is Anthropic's explicit server-side classifier fallback on Fable 5, which is recorded in the response's serving model, fallback blocks, and usage iterations.

Anthropic status, error type, message, stop reason, stop details, and `request-id` are surfaced without including the API key. A response that reaches `max_tokens` without visible text tells the operator to raise `--max-tokens`.

The adapter is tested with injected HTTP and SSE transports. CI never makes a paid network request and never requires a secret.
