# Routing profiles and evidence schemas

CrumbContext profiles are named, deterministic starting points for `RouterConfig`. A profile never bypasses the core safety boundaries:

- system, developer, and explicitly authoritative context remains exact native text;
- current and recent turns remain exact according to the resolved policy;
- tool schemas, policies, instructions, approvals, and citations remain exact;
- exact anchors are extracted before any lossy transform;
- image artifacts are historical evidence, never an authority channel;
- exact facts never depend on pixels.

Every new routing plan records the profile name and the complete resolved configuration. A profile is convenience, not hidden behavior.

## Available profiles

### `safe-default`

The normal production policy:

- keeps authority and recent context exact;
- prefers provider caching for sufficiently reused stable references;
- uses CRUMB for structured old memory;
- allows sanitized images for eligible old dense context;
- uses deterministic extractive summaries for other old semantic context.

```bash
crumbcontext route transcript.json \
  --profile safe-default \
  --out routed-context
```

### `text-only`

Disables image routing while retaining exact, cache, CRUMB, and summary lanes.

Use it when:

- the selected provider or model does not accept images;
- image pricing is uncertain;
- policy prohibits image artifacts;
- the workload should be compared against a text-only routed baseline.

```bash
crumbcontext counterfactual \
  --provider mock \
  --profile text-only \
  --out text-only-proof
```

### `cache-heavy`

Prefers provider caching earlier for reusable reference, documentation, memory, and system-reference blocks. Image routing is disabled so the profile isolates native-text caching behavior.

This profile does not guarantee a cache hit. Provider caching depends on provider rules, request stability, model support, and account behavior. Reports use provider cache accounting only when the provider returns it.

### `frontier-vision`

Keeps the normal safety policy while rendering eligible historical image context at 2576×1196 with a 24,000-character page target. This profile targets Claude Fable 5, Claude Mythos 5, Claude Opus 4.7+, and Claude Sonnet 5.

`safe-default` remains at 1568×728 so it works across standard-resolution models. The larger profile changes image density and visual-token estimates only; exact-value sidecars and authority boundaries are unchanged.

```bash
crumbcontext analyze examples/transcript.json --profile frontier-vision
```

### `strict-exact`

Keeps every practical block in native text. It is intended for:

- routing regression baselines;
- audits;
- debugging provider-role behavior;
- comparing transformed and non-transformed request construction.

It is not intended to reduce context size.

## CLI overrides

The CLI accepts two explicit safe overrides:

```bash
crumbcontext route transcript.json \
  --profile safe-default \
  --no-images \
  --recent-turns 4 \
  --out routed-context
```

The plan records the profile as `safe-default+overrides` and stores the complete resolved configuration.

An unknown profile, negative recent-turn count, invalid ratio, or unknown configuration key is rejected.

## Python API

```python
from crumbcontext import build_routed_request

bundle = build_routed_request(
    "Return JSON with the exact SHA.",
    blocks,
    "routed-context",
    profile="text-only",
    config_overrides={"recent_turns": 4},
)

print(bundle.plan.profile_name)
print(bundle.plan.resolved_config)
```

Applications may instead pass an explicit `RouterConfig`. Mixing an explicit config with a named profile or profile overrides is rejected so the effective policy is never ambiguous.

## Versioned documents

New CrumbContext artifacts declare a `schema_version`:

| Document | Schema |
|---|---|
| Routing plan | `crumbcontext.route-plan.v1` |
| Offline benchmark result | `crumbcontext.benchmark-result.v1` |
| Counterfactual specification | `crumbcontext.counterfactual-spec.v1` |
| Counterfactual result | `crumbcontext.counterfactual-result.v1` |
| Provider-neutral request | `crumbcontext.provider-request.v1` |
| Provider-normalized response | `crumbcontext.provider-response.v1` |

CrumbContext v0.1 artifacts did not contain schema markers. Readers accept a missing marker as legacy v0.1 where compatibility is explicitly enabled.

An unknown explicit schema is rejected. CrumbContext does not silently reinterpret a future or foreign schema as a known one.

```python
from crumbcontext import (
    COUNTERFACTUAL_RESULT_SCHEMA,
    load_json_document,
)

report = load_json_document(
    "counterfactual.json",
    COUNTERFACTUAL_RESULT_SCHEMA,
)
```

Legacy documents returned by `load_json_document` receive:

```json
{
  "schema_version": "crumbcontext.counterfactual-result.v1",
  "legacy_schema_missing": true
}
```

This marks the compatibility assumption; it does not rewrite the source file.

## Response-body redaction

A counterfactual normally saves provider response bodies in:

- `baseline-response.json`;
- `routed-response.json`;
- `counterfactual.json`;
- `counterfactual.html`.

For sensitive workloads:

```bash
crumbcontext counterfactual \
  --provider openai \
  --model EXACT_MODEL_ID \
  --profile text-only \
  --redact-responses \
  --out provider-proof
```

Redaction removes response text from saved JSON and HTML while preserving:

- request and response SHA-256 hashes;
- provider and model identifiers;
- usage and latency;
- cache accounting returned by the provider;
- exact and required-rule recall;
- JSON validity and task completion;
- response similarity;
- routing profile and resolved configuration.

The response still exists in process memory while evaluation runs. Redaction is an artifact-storage policy, not a confidential-computing boundary.

Request bodies, exact sidecars, routed artifacts, and task text may still be sensitive. Protect the entire output directory.

## Provider evidence

The guarded `Provider benchmark` workflow records the selected profile and defaults to response-body redaction. A publishable result must include the profile and complete resolved configuration alongside provider/model, fixture hashes, request hashes, token accounting, latency, recall, task completion, and response similarity.

See [PROVIDER_BENCHMARKS.md](PROVIDER_BENCHMARKS.md).
