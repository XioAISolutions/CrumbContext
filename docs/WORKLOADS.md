# Public multi-workload evaluation

CrumbContext includes a versioned, synthetic workload suite for testing routing behavior across materially different agent-context shapes.

The suite is an **offline routing evaluation**. It does not call a model provider, measure answer quality, or report provider billing.

## Run the bundled suite

```bash
crumbcontext workloads --out workload-proof
```

The default matrix is:

```text
5 workloads × 4 named profiles = 20 deterministic runs
```

Profiles:

- `safe-default`
- `text-only`
- `cache-heavy`
- `strict-exact`

Run a subset:

```bash
crumbcontext workloads \
  --profiles safe-default text-only \
  --out workload-proof
```

Use a custom manifest:

```bash
crumbcontext workloads ./my-workloads.json --out custom-proof
```

## Bundled workload shapes

| Workload | Main context features |
|---|---|
| `coding-debug` | Authority rules, API reference, dense traces, handoff memory, current repair request |
| `research-synthesis` | Citation rules, methodology reference, evidence matrix, old synthesis notes |
| `operations-delivery` | Budget authority, contract reference, project map, historical meeting record |
| `tool-heavy-agent` | Destructive-action guardrails, tool schema, service docs, dense tool output, agent memory |
| `mixed-authority-session` | System/developer authority, reusable memory, stale conflicting dialogue, current override |

All bundled text is synthetic, released as `CC0-1.0`, and contains no private transcripts, provider output, or third-party copyrighted passages.

The source manifest is stored at:

```text
crumbcontext/fixtures/workloads/v1/manifest.json
```

It is included in the wheel and source distribution.

## What every run checks

Each workload/profile pair must pass all of these checks:

1. every anchor recognized in the original context is preserved in native-text sidecars;
2. every exact value declared by the fixture is preserved;
3. system, developer, and explicitly authoritative blocks remain exact;
4. required rules originate in authority blocks and remain exact;
5. recent context remains exact according to the resolved profile;
6. image routing is absent when vision is disabled and every image route has a real artifact;
7. `strict-exact` routes every block through the exact lane;
8. two independent routing passes produce the same plan;
9. routing plans, reports, sidecars, summaries, CRUMBs, and images referenced by the plan exist.

The aggregate suite additionally requires:

- a complete workload/profile matrix;
- every run to pass;
- complete exact-anchor preservation;
- coverage of exact, cache, CRUMB, image, and summary lanes when all default profiles run;
- SHA-256 hashes for the source manifest and every expanded fixture.

## Outputs

```text
workload-proof/
├── suite.json
├── manifest-expanded.json
├── report.html
├── share-card.svg
├── results/
│   ├── coding-debug--safe-default.json
│   └── ... one JSON result per workload/profile pair
└── runs/
    └── <workload>/<profile>/
        ├── plan.json
        ├── report.html
        ├── anchors-all.txt
        ├── images/
        ├── summaries/
        └── crumbs/
```

### `suite.json`

The aggregate result declares:

```text
schema_version = crumbcontext.workload-suite-result.v1
```

It records:

- suite and manifest metadata;
- manifest SHA-256;
- selected profiles;
- aggregate checks;
- run/pass counts;
- exact-anchor totals;
- lane totals;
- per-profile planning estimates;
- all individual run results.

### Individual results

Every file under `results/` declares:

```text
schema_version = crumbcontext.workload-result.v1
```

It records:

- suite and workload identifiers;
- source-manifest and expanded-fixture hashes;
- license and provenance;
- routing profile and complete resolved `RouterConfig`;
- pass/fail checks;
- estimated text and routed tokens;
- exact-anchor counts;
- lane counts;
- the complete routing plan;
- relative artifact root;
- the claims disclaimer.

## Manifest format

A workload manifest must explicitly declare:

```text
schema_version = crumbcontext.workload-manifest.v1
```

Missing or unknown schemas fail closed.

Top-level fields:

```json
{
  "schema_version": "crumbcontext.workload-manifest.v1",
  "suite_id": "example-suite",
  "version": "1.0.0",
  "title": "Example suite",
  "license": "CC0-1.0",
  "provenance": "Synthetic fixtures.",
  "workloads": []
}
```

Each workload declares:

```json
{
  "id": "example-workload",
  "title": "Example workload",
  "description": "What this context shape tests.",
  "tags": ["example"],
  "license": "CC0-1.0",
  "provenance": "Synthetic example.",
  "task": "Use the context safely.",
  "expected_exact": ["2026-07-12"],
  "required_rules": ["Never invent evidence."],
  "blocks": []
}
```

Validation rules:

- workload and block IDs must be lowercase filesystem-safe identifiers;
- IDs must be unique;
- every declared exact value must be recognized by CrumbContext's anchor extractor in the expanded source context;
- every required rule must appear in a system, developer, or explicitly authoritative block;
- every block declares exactly one of `content` or `segments`;
- manifests are bounded to 100 workloads, 500 blocks per workload, 500 segment repetitions, and 2,000,000 expanded characters per block.

## Compact synthetic segments

Long synthetic fixtures can use deterministic segments instead of duplicating large passages:

```json
{
  "id": "historical-log",
  "role": "tool",
  "kind": "message",
  "age_turns": 12,
  "segments": [
    {
      "repeat": 40,
      "text": "event[{index}]={status:ok,next:review};"
    }
  ]
}
```

`{index}` is replaced with a one-based repetition number. Expansion is deterministic and becomes part of the fixture SHA-256.

## Claims boundary

Use language such as:

> On the bundled public synthetic workload suite, profile X produced deterministic routing estimate A while preserving B/B exact anchors and passing all routing checks.

Do not say:

- “CrumbContext always cuts provider costs by N%.”
- “This proves model answers remain equally good.”
- “These token estimates are provider-billed usage.”
- “Images are universally cheaper than text.”

The workload suite measures **routing behavior and deterministic planning estimates**. Real provider evidence belongs in the guarded workflow documented in [PROVIDER_BENCHMARKS.md](PROVIDER_BENCHMARKS.md).

## Reproducibility

A credible published workload result should retain:

```text
CrumbContext version
manifest schema and version
manifest SHA-256
fixture SHA-256
selected profile
resolved RouterConfig
full suite.json
individual result JSON
routing artifacts
claims disclaimer
```

The GitHub Actions `Workload suite` workflow builds a wheel, installs it outside the source tree, runs all 20 bundled evaluations on Python 3.10, 3.11, and 3.12, and exports the Python 3.12 evidence bundle. It makes no paid network calls and uses no provider secrets.
