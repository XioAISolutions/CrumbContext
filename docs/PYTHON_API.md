# Python integration API

CrumbContext exposes a small provider-neutral API for applications that do not want to shell out to the CLI.

The supported surface is exported from the top-level `crumbcontext` package and covered by compatibility tests. Modules and names not documented here should be treated as implementation details.

> The API described here is present on the repository `main` branch after the v0.1.0 release and will be included in the next published package version.

## Install from source during development

```bash
git clone https://github.com/XioAISolutions/CrumbContext.git
cd CrumbContext
python -m pip install -e '.[dev]'
```

The latest published stable package remains available with:

```bash
python -m pip install crumb-context
```

## Core types

```python
from crumbcontext import (
    ContextBlock,
    EvaluationSpec,
    ProviderRequest,
    ProviderResponse,
    RoutePlan,
    RouterConfig,
    RoutedRequestBundle,
)
```

- `ContextBlock` is one unit of context with role, kind, recency, reuse, authority, and metadata.
- `RouterConfig` controls routing policy such as image eligibility and recent-turn retention.
- `ProviderRequest` is the canonical provider-neutral request.
- `RoutedRequestBundle` contains the routed request, its `RoutePlan`, and the artifact root.
- `ProviderResponse` normalizes provider text, usage, latency, model, and usage kind.
- `EvaluationSpec` declares exact values, required strings, and JSON expectations for counterfactual measurement.

## Normalize application data

`normalize_blocks` accepts `ContextBlock` objects, mapping objects, or a mixture of both.

```python
from crumbcontext import ContextBlock, normalize_blocks

blocks = normalize_blocks(
    [
        ContextBlock(
            id="system",
            role="system",
            kind="instruction",
            content="Return JSON and preserve exact values.",
            authoritative=True,
        ),
        {
            "id": "current",
            "role": "user",
            "kind": "message",
            "content": "The SHA is abcdef1234567890abcdef1234567890.",
        },
    ]
)
```

The function rejects:

- an empty collection;
- duplicate IDs;
- empty IDs;
- unsupported value types.

Unique IDs are required because plans and artifacts use IDs as stable joins.

## Build an uncompressed baseline request

```python
from crumbcontext import build_baseline_request

request = build_baseline_request(
    "Return JSON containing the exact SHA.",
    blocks,
    name="my-agent-task",
)

print(request.sha256)
print(request.to_dict())
```

The baseline request preserves original block roles and text without routing transforms. It is useful for measurement and debugging; it is not the cost-optimized path.

## Build a routed request

```python
from pathlib import Path

from crumbcontext import RouterConfig, build_routed_request

bundle = build_routed_request(
    "Return JSON containing the exact SHA.",
    blocks,
    Path("routed-context"),
    config=RouterConfig(
        vision_allowed=False,
        recent_turns=2,
    ),
    name="my-agent-task",
)

print(bundle.request.sha256)
print(bundle.plan.to_dict())
print(bundle.artifact_root)
```

The output directory is part of the request contract. Provider payload builders may need it to verify and read image artifacts. Treat it as sensitive because exact sidecars intentionally preserve literal values.

`bundle.to_dict()` gives an inspectable representation containing:

```text
request
plan
artifact_root
```

## Execute through the provider protocol

The offline mock requires no network or key:

```python
from crumbcontext import execute_provider

response = execute_provider(bundle.request, "mock")
print(response.to_dict())
```

For a real provider, pass explicit options and the routed artifact root:

```python
import os

response = execute_provider(
    bundle.request,
    "anthropic",
    provider_options={
        "api_key": os.environ["ANTHROPIC_API_KEY"],
        "model": "EXACT_ANTHROPIC_MODEL_ID",
        "artifact_root": bundle.artifact_root,
        "max_tokens": 1024,
    },
)
```

```python
response = execute_provider(
    bundle.request,
    "openai",
    provider_options={
        "api_key": os.environ["OPENAI_API_KEY"],
        "model": "EXACT_OPENAI_MODEL_ID",
        "artifact_root": bundle.artifact_root,
        "max_tokens": 1024,
    },
)
```

Do not hard-code provider keys. CrumbContext does not write keys into reports or artifacts.

An application may inject its own object implementing the provider protocol:

```python
from crumbcontext import ProviderRequest, ProviderResponse, execute_provider

class InternalProvider:
    name = "internal"
    model = "internal-model-v1"

    def run(self, request: ProviderRequest) -> ProviderResponse:
        # Call an internal gateway here.
        return ProviderResponse(
            provider=self.name,
            model=self.model,
            text='{"status":"ok"}',
            input_tokens=0,
            output_tokens=0,
            latency_ms=0.0,
            usage_kind="internal_gateway",
        )

response = execute_provider(bundle.request, InternalProvider())
```

When a provider instance is injected, `provider_options` is rejected. This prevents options intended for one provider from being silently ignored by another.

## Build provider-native payloads without sending them

Use these functions when an application already owns its provider client, retry policy, telemetry, or network boundary.

### Anthropic Messages payload

```python
from crumbcontext import build_anthropic_payload

payload = build_anthropic_payload(
    bundle.request,
    model="EXACT_ANTHROPIC_MODEL_ID",
    max_tokens=1024,
    artifact_root=bundle.artifact_root,
    enable_cache=True,
)
```

### OpenAI Responses payload

```python
from crumbcontext import build_openai_payload

payload = build_openai_payload(
    bundle.request,
    model="EXACT_OPENAI_MODEL_ID",
    max_tokens=1024,
    artifact_root=bundle.artifact_root,
    enable_cache=True,
    prompt_cache_key=None,
    image_detail="high",
)
```

The resulting dictionaries preserve the adapter safety behavior documented in [ANTHROPIC.md](ANTHROPIC.md) and [OPENAI.md](OPENAI.md). Pass them to the matching method exposed by the official SDK version used by the application.

CrumbContext deliberately does not require either provider SDK.

## Counterfactual measurement

The existing counterfactual API remains supported:

```python
from pathlib import Path

from crumbcontext import create_spec, run_counterfactual

spec = create_spec(
    "Return JSON containing the exact SHA.",
    blocks,
    name="measurement",
    evaluation={
        "expected_exact": ["abcdef1234567890abcdef1234567890"],
        "required_substrings": ["SHA"],
        "expect_json": True,
    },
)

result = run_counterfactual(
    spec,
    Path("comparison"),
    provider="mock",
    config=RouterConfig(vision_allowed=False),
)

assert result.passed
```

For provider-measured evidence, follow [PROVIDER_BENCHMARKS.md](PROVIDER_BENCHMARKS.md). One fixture and model run must not be presented as a universal cost claim.

## Public stability policy

The following are supported public imports:

```text
Anchor
AnthropicProvider
BlockInput
ContextBlock
CounterfactualResult
CounterfactualSpec
EvaluationSpec
Lane
MockProvider
OpenAIProvider
Provider
ProviderRequest
ProviderResponse
RoutePlan
RoutedBlock
RoutedRequestBundle
RouterConfig
build_anthropic_payload
build_baseline_request
build_openai_payload
build_routed_request
create_spec
execute_provider
extract_anchors
get_provider
normalize_blocks
route_blocks
run_counterfactual
sanitize_with_anchors
```

Before version `1.0`, additions may occur in minor releases. Breaking changes to this documented surface require release notes, a migration path, and an intentional version change. Internal modules may change without that guarantee.

## Runnable examples

```bash
python examples/python/route_and_inspect.py --out /tmp/crumbcontext-api
python examples/python/run_mock_provider.py
python examples/python/build_anthropic_payload.py --out /tmp/crumbcontext-anthropic
python examples/python/build_openai_payload.py --out /tmp/crumbcontext-openai
```

All four examples run without a provider key or paid network call.
