"""CrumbContext: safety-first routing for long AI context."""

from .anchors import extract_anchors, sanitize_with_anchors
from .counterfactual import CounterfactualResult, CounterfactualSpec, run_counterfactual
from .models import Anchor, ContextBlock, Lane, RoutePlan, RoutedBlock
from .router import RouterConfig, route_blocks

__all__ = [
    "Anchor",
    "ContextBlock",
    "CounterfactualResult",
    "CounterfactualSpec",
    "Lane",
    "RoutePlan",
    "RoutedBlock",
    "RouterConfig",
    "extract_anchors",
    "sanitize_with_anchors",
    "route_blocks",
    "run_counterfactual",
]

__version__ = "0.1.0"
