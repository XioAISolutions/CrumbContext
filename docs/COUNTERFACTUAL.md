# Same-request counterfactual harness

CrumbContext should not claim savings from a routing estimate alone. The
counterfactual harness runs the **same task** against two payloads:

1. an uncompressed baseline containing every source block;
2. a routed payload containing exact text, cache-marked content, CRUMBs,
   sanitized image artifacts, summaries, and exact-anchor sidecars.

It records both payload hashes, task and source hashes, normalized provider
usage, latency, exact-value recall, structured-output validity, required-string
recall, task completion, and response similarity.

## Offline proof

```bash
crumbcontext counterfactual --provider mock --out proof --open
```

The output contains:

```text
proof/
├── counterfactual.json
├── counterfactual.html
├── counterfactual-card.svg
├── baseline-request.json
├── routed-request.json
├── baseline-response.json
├── routed-response.json
└── routed-artifacts/
```

The mock provider is a deterministic local extractor. It validates the harness,
request integrity, evaluators, and artifact flow. Its token accounting is a
simulation based on CrumbContext's estimator and **is not provider billing**.

## Custom fixture

```json
{
  "name": "my-comparison",
  "task": "Return JSON with the exact deployment values and active rules.",
  "blocks": [
    {
      "id": "system",
      "role": "system",
      "kind": "instruction",
      "content": "Never deploy without approval.",
      "authoritative": true
    },
    {
      "id": "history",
      "role": "user",
      "kind": "tool_result",
      "content": "Build https://example.com/12345678 cost CAD $900.00",
      "age_turns": 12
    }
  ],
  "evaluation": {
    "expect_json": true,
    "expected_exact": ["https://example.com/12345678", "CAD $900.00"],
    "required_substrings": ["Never deploy without approval."]
  }
}
```

```bash
crumbcontext counterfactual fixture.json --provider mock --out proof
```

## Provider contract

A real adapter returns normalized input/output token usage, latency, response
text, model identifier, and a usage-kind label. It must preserve role and
authority semantics and fail closed to exact text when a routed artifact cannot
be represented safely.

Anthropic and OpenAI adapters are intentionally separate roadmap items. Public
provider-billed savings claims remain blocked until one of those adapters
produces a reproducible same-request result.
