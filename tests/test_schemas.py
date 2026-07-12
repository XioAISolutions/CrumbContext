from __future__ import annotations

import json
from pathlib import Path

import pytest

from crumbcontext import (
    COUNTERFACTUAL_RESULT_SCHEMA,
    COUNTERFACTUAL_SPEC_SCHEMA,
    PROVIDER_REQUEST_SCHEMA,
    PROVIDER_RESPONSE_SCHEMA,
    ROUTE_PLAN_SCHEMA,
    ContextBlock,
    CounterfactualSpec,
    ProviderRequest,
    ProviderResponse,
    SchemaError,
    load_json_document,
    require_schema,
    route_blocks,
)


def test_current_schema_is_accepted_and_unknown_schema_is_rejected():
    assert require_schema(
        {"schema_version": ROUTE_PLAN_SCHEMA},
        ROUTE_PLAN_SCHEMA,
    ) is False
    with pytest.raises(SchemaError, match="unsupported schema_version"):
        require_schema(
            {"schema_version": "crumbcontext.route-plan.v999"},
            ROUTE_PLAN_SCHEMA,
        )


def test_legacy_missing_schema_remains_readable_and_is_marked(tmp_path: Path):
    path = tmp_path / "legacy.json"
    path.write_text('{"blocks":[]}', encoding="utf-8")
    value = load_json_document(path, ROUTE_PLAN_SCHEMA)
    assert value["schema_version"] == ROUTE_PLAN_SCHEMA
    assert value["legacy_schema_missing"] is True


def test_missing_schema_can_be_required():
    with pytest.raises(SchemaError, match="missing required schema_version"):
        require_schema({}, ROUTE_PLAN_SCHEMA, allow_legacy_missing=False)


def test_counterfactual_spec_reads_legacy_and_emits_current_schema():
    legacy = {
        "name": "legacy",
        "task": "Return JSON.",
        "blocks": [
            {
                "id": "current",
                "role": "user",
                "kind": "message",
                "content": "hello",
            }
        ],
    }
    spec = CounterfactualSpec.from_dict(legacy)
    assert spec.to_dict()["schema_version"] == COUNTERFACTUAL_SPEC_SCHEMA

    current = dict(legacy, schema_version=COUNTERFACTUAL_SPEC_SCHEMA)
    assert CounterfactualSpec.from_dict(current).name == "legacy"

    unknown = dict(legacy, schema_version="crumbcontext.counterfactual-spec.v99")
    with pytest.raises(SchemaError, match="unsupported schema_version"):
        CounterfactualSpec.from_dict(unknown)


def test_route_plan_and_provider_documents_emit_schemas():
    plan = route_blocks(
        [ContextBlock("one", "user", "message", "hello")],
        profile_name="safe-default",
    )
    assert plan.to_dict()["schema_version"] == ROUTE_PLAN_SCHEMA

    request = ProviderRequest(
        mode="baseline",
        task="Task",
        blocks=[{"id": "one", "content": "hello"}],
    )
    response = ProviderResponse(
        provider="mock",
        model="mock-v1",
        text="{}",
        input_tokens=1,
        output_tokens=1,
        latency_ms=0.0,
        usage_kind="test",
    )
    assert request.to_dict()["schema_version"] == PROVIDER_REQUEST_SCHEMA
    assert response.to_dict()["schema_version"] == PROVIDER_RESPONSE_SCHEMA


def test_counterfactual_result_schema_constant_is_stable():
    assert COUNTERFACTUAL_RESULT_SCHEMA == "crumbcontext.counterfactual-result.v1"


def test_non_object_document_is_rejected(tmp_path: Path):
    path = tmp_path / "list.json"
    path.write_text(json.dumps([]), encoding="utf-8")
    with pytest.raises(SchemaError, match="must be a JSON object"):
        load_json_document(path, ROUTE_PLAN_SCHEMA)
