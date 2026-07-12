"""CrumbContext: safety-first routing for long AI context."""

from .anchors import extract_anchors, sanitize_with_anchors
from .api import (
    BlockInput,
    RoutedRequestBundle,
    build_baseline_request,
    build_routed_request,
    create_spec,
    execute_provider,
    normalize_blocks,
)
from .counterfactual import CounterfactualResult, CounterfactualSpec, run_counterfactual
from .counterfactual_models import EvaluationSpec
from .models import Anchor, ContextBlock, Lane, RoutePlan, RoutedBlock
from .profiles import (
    ResolvedProfile,
    available_profiles,
    custom_profile,
    resolve_profile,
    validate_router_config,
)
from .providers import (
    AnthropicProvider,
    MockProvider,
    OpenAIProvider,
    Provider,
    ProviderRequest,
    ProviderResponse,
    build_anthropic_payload,
    build_openai_payload,
    get_provider,
)
from .router import RouterConfig, route_blocks
from .schemas import (
    COUNTERFACTUAL_RESULT_SCHEMA,
    COUNTERFACTUAL_SPEC_SCHEMA,
    PROVIDER_REQUEST_SCHEMA,
    PROVIDER_RESPONSE_SCHEMA,
    ROUTE_PLAN_SCHEMA,
    SchemaError,
    load_json_document,
    require_schema,
)

__all__ = [
    "Anchor",
    "AnthropicProvider",
    "BlockInput",
    "COUNTERFACTUAL_RESULT_SCHEMA",
    "COUNTERFACTUAL_SPEC_SCHEMA",
    "ContextBlock",
    "CounterfactualResult",
    "CounterfactualSpec",
    "EvaluationSpec",
    "Lane",
    "MockProvider",
    "OpenAIProvider",
    "PROVIDER_REQUEST_SCHEMA",
    "PROVIDER_RESPONSE_SCHEMA",
    "Provider",
    "ProviderRequest",
    "ProviderResponse",
    "ROUTE_PLAN_SCHEMA",
    "ResolvedProfile",
    "RoutePlan",
    "RoutedBlock",
    "RoutedRequestBundle",
    "RouterConfig",
    "SchemaError",
    "available_profiles",
    "build_anthropic_payload",
    "build_baseline_request",
    "build_openai_payload",
    "build_routed_request",
    "create_spec",
    "custom_profile",
    "execute_provider",
    "extract_anchors",
    "get_provider",
    "load_json_document",
    "normalize_blocks",
    "require_schema",
    "resolve_profile",
    "route_blocks",
    "run_counterfactual",
    "sanitize_with_anchors",
    "validate_router_config",
]

__version__ = "0.1.0"
