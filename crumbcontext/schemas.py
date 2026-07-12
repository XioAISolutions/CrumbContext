from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROUTE_PLAN_SCHEMA = "crumbcontext.route-plan.v1"
BENCHMARK_RESULT_SCHEMA = "crumbcontext.benchmark-result.v1"
COUNTERFACTUAL_SPEC_SCHEMA = "crumbcontext.counterfactual-spec.v1"
COUNTERFACTUAL_RESULT_SCHEMA = "crumbcontext.counterfactual-result.v1"
PROVIDER_REQUEST_SCHEMA = "crumbcontext.provider-request.v1"
PROVIDER_RESPONSE_SCHEMA = "crumbcontext.provider-response.v1"

SUPPORTED_SCHEMAS = frozenset(
    {
        ROUTE_PLAN_SCHEMA,
        BENCHMARK_RESULT_SCHEMA,
        COUNTERFACTUAL_SPEC_SCHEMA,
        COUNTERFACTUAL_RESULT_SCHEMA,
        PROVIDER_REQUEST_SCHEMA,
        PROVIDER_RESPONSE_SCHEMA,
    }
)


class SchemaError(ValueError):
    """Raised when a document declares an unsupported explicit schema."""


def require_schema(
    value: dict[str, Any],
    expected: str,
    *,
    allow_legacy_missing: bool = True,
) -> bool:
    """Validate a document schema and return whether it was a legacy document.

    CrumbContext v0.1 documents had no ``schema_version`` field. They remain
    readable when ``allow_legacy_missing`` is true. Any unknown explicit schema
    is rejected instead of being guessed.
    """

    declared = value.get("schema_version")
    if declared is None:
        if allow_legacy_missing:
            return True
        raise SchemaError(f"document is missing required schema_version {expected!r}")
    if not isinstance(declared, str) or not declared.strip():
        raise SchemaError("schema_version must be non-empty text")
    if declared != expected:
        supported = ", ".join(sorted(SUPPORTED_SCHEMAS))
        raise SchemaError(
            f"unsupported schema_version {declared!r}; expected {expected!r}. "
            f"Supported schemas: {supported}"
        )
    return False


def normalize_document(
    value: dict[str, Any],
    expected: str,
    *,
    allow_legacy_missing: bool = True,
) -> dict[str, Any]:
    """Return a copy with the expected schema and legacy provenance marker."""

    legacy = require_schema(
        value,
        expected,
        allow_legacy_missing=allow_legacy_missing,
    )
    normalized = dict(value)
    normalized["schema_version"] = expected
    if legacy:
        normalized["legacy_schema_missing"] = True
    return normalized


def load_json_document(
    path: str | Path,
    expected: str,
    *,
    allow_legacy_missing: bool = True,
) -> dict[str, Any]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise SchemaError("versioned CrumbContext document must be a JSON object")
    return normalize_document(
        raw,
        expected,
        allow_legacy_missing=allow_legacy_missing,
    )


__all__ = [
    "BENCHMARK_RESULT_SCHEMA",
    "COUNTERFACTUAL_RESULT_SCHEMA",
    "COUNTERFACTUAL_SPEC_SCHEMA",
    "PROVIDER_REQUEST_SCHEMA",
    "PROVIDER_RESPONSE_SCHEMA",
    "ROUTE_PLAN_SCHEMA",
    "SUPPORTED_SCHEMAS",
    "SchemaError",
    "load_json_document",
    "normalize_document",
    "require_schema",
]
