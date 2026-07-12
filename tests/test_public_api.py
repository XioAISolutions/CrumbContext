from __future__ import annotations

from pathlib import Path

import pytest

import crumbcontext
from crumbcontext import (
    ContextBlock,
    EvaluationSpec,
    ProviderRequest,
    ProviderResponse,
    RouterConfig,
    build_anthropic_payload,
    build_baseline_request,
    build_openai_payload,
    build_routed_request,
    create_spec,
    execute_provider,
    normalize_blocks,
)


BLOCKS = [
    {
        "id": "system",
        "role": "system",
        "kind": "instruction",
        "content": "Never change exact values.",
        "authoritative": True,
    },
    {
        "id": "memory",
        "role": "user",
        "kind": "memory",
        "content": "Decision: use the stable public API.",
        "age_turns": 8,
        "reuse_count": 4,
    },
    {
        "id": "old-log",
        "role": "tool",
        "kind": "tool_result",
        "content": (
            "Historical output references https://example.com/orders/123 and "
            "SHA abcdef1234567890abcdef1234567890."
        ),
        "age_turns": 14,
    },
    {
        "id": "current",
        "role": "user",
        "kind": "message",
        "content": "Return the SHA exactly.",
        "age_turns": 0,
    },
]


def test_top_level_public_contract_is_importable():
    required = {
        "BlockInput",
        "EvaluationSpec",
        "ProviderRequest",
        "ProviderResponse",
        "RoutedRequestBundle",
        "build_anthropic_payload",
        "build_baseline_request",
        "build_openai_payload",
        "build_routed_request",
        "create_spec",
        "execute_provider",
        "normalize_blocks",
    }
    assert required <= set(crumbcontext.__all__)
    for name in crumbcontext.__all__:
        assert hasattr(crumbcontext, name)


def test_normalize_blocks_accepts_mappings_and_objects():
    values = normalize_blocks(
        [
            ContextBlock("one", "user", "message", "hello"),
            {"id": "two", "role": "assistant", "content": "world"},
        ]
    )
    assert [item.id for item in values] == ["one", "two"]
    assert values[1].kind == "message"


def test_normalize_blocks_rejects_empty_duplicate_and_unknown_values():
    with pytest.raises(ValueError, match="at least one"):
        normalize_blocks([])
    with pytest.raises(ValueError, match="duplicate"):
        normalize_blocks(
            [
                {"id": "same", "content": "one"},
                {"id": "same", "content": "two"},
            ]
        )
    with pytest.raises(TypeError, match="mapping objects"):
        normalize_blocks(["not-a-block"])  # type: ignore[list-item]


def test_create_spec_preserves_task_and_accepts_evaluation_mapping():
    task = "  Preserve task whitespace exactly.  "
    spec = create_spec(
        task,
        BLOCKS,
        name="integration",
        evaluation={"expected_exact": ["abcdef1234567890abcdef1234567890"]},
    )
    assert spec.task == task
    assert spec.name == "integration"
    assert isinstance(spec.evaluation, EvaluationSpec)
    assert spec.evaluation.expected_exact == (
        "abcdef1234567890abcdef1234567890",
    )


def test_create_spec_rejects_invalid_task_name_and_evaluation():
    with pytest.raises(ValueError, match="task"):
        create_spec("   ", BLOCKS)
    with pytest.raises(ValueError, match="name"):
        create_spec("task", BLOCKS, name="")
    with pytest.raises(TypeError, match="evaluation"):
        create_spec("task", BLOCKS, evaluation="wrong")  # type: ignore[arg-type]


def test_build_baseline_request_preserves_native_roles_and_content():
    request = build_baseline_request("Summarize safely.", BLOCKS, name="baseline")
    assert isinstance(request, ProviderRequest)
    assert request.mode == "baseline"
    assert request.metadata["compression"] == "none"
    assert request.blocks[0]["role"] == "system"
    assert request.blocks[0]["content"] == "Never change exact values."
    assert request.sha256


def test_build_routed_request_writes_inspectable_artifacts(tmp_path: Path):
    bundle = build_routed_request(
        "Return JSON with the exact SHA.",
        BLOCKS,
        tmp_path / "routed",
        config=RouterConfig(vision_allowed=False, recent_turns=2),
        name="routed",
    )
    assert bundle.request.mode == "routed"
    assert bundle.artifact_root == tmp_path / "routed"
    assert bundle.plan.exact_anchor_count >= 2
    assert (bundle.artifact_root / "plan.json").is_file()
    assert bundle.to_dict()["artifact_root"] == str(tmp_path / "routed")
    system = next(item for item in bundle.request.blocks if item["id"] == "system")
    assert system["lane"] == "exact"
    assert system["content"] == "Never change exact values."
    old_log = next(item for item in bundle.request.blocks if item["id"] == "old-log")
    assert "exact_anchor_sidecar" in old_log
    assert "abcdef1234567890abcdef1234567890" in old_log["exact_anchor_sidecar"]


def test_provider_native_payload_builders_preserve_authority(tmp_path: Path):
    bundle = build_routed_request(
        "Return the result.",
        BLOCKS,
        tmp_path / "native",
        config=RouterConfig(vision_allowed=False),
    )
    anthropic = build_anthropic_payload(
        bundle.request,
        model="exact-anthropic-model-id",
        max_tokens=256,
        artifact_root=bundle.artifact_root,
        enable_cache=True,
    )
    assert anthropic["model"] == "exact-anthropic-model-id"
    assert anthropic["system"]
    assert anthropic["messages"][-1]["role"] == "user"

    openai = build_openai_payload(
        bundle.request,
        model="exact-openai-model-id",
        max_tokens=256,
        artifact_root=bundle.artifact_root,
        enable_cache=True,
        prompt_cache_key=None,
        image_detail="high",
    )
    assert openai["model"] == "exact-openai-model-id"
    assert openai["store"] is False
    assert any(item["role"] == "system" for item in openai["input"])


def test_execute_provider_uses_mock_and_supports_injected_provider():
    request = build_baseline_request("Return JSON.", BLOCKS)
    response = execute_provider(request)
    assert isinstance(response, ProviderResponse)
    assert response.provider == "mock"
    assert response.usage_kind == "mock_simulated_not_billed"

    class InjectedProvider:
        name = "injected"
        model = "deterministic"

        def run(self, value: ProviderRequest) -> ProviderResponse:
            assert value is request
            return ProviderResponse(
                provider=self.name,
                model=self.model,
                text="{}",
                input_tokens=1,
                output_tokens=1,
                latency_ms=0.0,
                usage_kind="test",
            )

    injected = execute_provider(request, InjectedProvider())
    assert injected.provider == "injected"
    with pytest.raises(ValueError, match="provider_options"):
        execute_provider(
            request,
            InjectedProvider(),
            provider_options={"model": "not-allowed"},
        )
