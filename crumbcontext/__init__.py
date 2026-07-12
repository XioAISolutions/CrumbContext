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

__all__ = [
    "Anchor",
    "AnthropicProvider",
    "BlockInput",
    "ContextBlock",
    "CounterfactualResult",
    "CounterfactualSpec",
    "EvaluationSpec",
    "Lane",
    "MockProvider",
    "OpenAIProvider",
    "Provider",
    "ProviderRequest",
    "ProviderResponse",
    "RoutePlan",
    "RoutedBlock",
    "RoutedRequestBundle",
    "RouterConfig",
    "build_anthropic_payload",
    "build_baseline_request",
    "build_openai_payload",
    "build_routed_request",
    "create_spec",
    "execute_provider",
    "extract_anchors",
    "get_provider",
    "normalize_blocks",
    "route_blocks",
    "run_counterfactual",
    "sanitize_with_anchors",
]

__version__ = "0.1.0"
