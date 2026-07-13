from __future__ import annotations

from dataclasses import asdict, dataclass, fields, replace
from typing import Any, Mapping

from .router import RouterConfig


@dataclass(frozen=True)
class ResolvedProfile:
    name: str
    description: str
    config: RouterConfig

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "config": asdict(self.config),
        }


_PROFILES: dict[str, ResolvedProfile] = {
    "safe-default": ResolvedProfile(
        name="safe-default",
        description=(
            "Keep authority and recent context exact, prefer caching for stable reused "
            "references, and allow sanitized images for eligible old dense context."
        ),
        config=RouterConfig(),
    ),
    "text-only": ResolvedProfile(
        name="text-only",
        description=(
            "Use exact, cache, CRUMB, and summary lanes without image artifacts."
        ),
        config=RouterConfig(vision_allowed=False),
    ),
    "cache-heavy": ResolvedProfile(
        name="cache-heavy",
        description=(
            "Prefer provider caching earlier for reusable references while keeping the "
            "normal authority and exactness boundaries."
        ),
        config=RouterConfig(
            minimum_compress_chars=1200,
            cache_reuse_threshold=1,
            cache_equivalent_ratio=0.10,
            vision_allowed=False,
        ),
    ),
    "frontier-vision": ResolvedProfile(
        name="frontier-vision",
        description=(
            "Use the high-resolution 2576 px image tier available on Claude Fable 5, "
            "Claude Mythos 5, Claude Opus 4.7+, and Claude Sonnet 5 while preserving "
            "the normal authority and exact-value boundaries."
        ),
        config=RouterConfig(
            image_width=2576,
            image_height=1196,
            image_page_chars=24000,
        ),
    ),
    "strict-exact": ResolvedProfile(
        name="strict-exact",
        description=(
            "Keep every practical block in native text. Useful for audits and routing "
            "regression baselines, not token reduction."
        ),
        config=RouterConfig(
            recent_turns=1_000_000_000,
            minimum_compress_chars=1_000_000_000,
            image_min_chars=1_000_000_000,
            cache_reuse_threshold=1_000_000_000,
            vision_allowed=False,
        ),
    ),
}


def available_profiles() -> tuple[str, ...]:
    return tuple(_PROFILES)


def resolve_profile(
    name: str = "safe-default",
    overrides: Mapping[str, Any] | None = None,
) -> ResolvedProfile:
    normalized = name.strip().lower()
    if normalized not in _PROFILES:
        options = ", ".join(available_profiles())
        raise ValueError(f"unknown routing profile {name!r}; available profiles: {options}")
    base = _PROFILES[normalized]
    values = dict(overrides or {})
    allowed = {item.name for item in fields(RouterConfig)}
    unknown = sorted(set(values) - allowed)
    if unknown:
        raise ValueError(f"unknown RouterConfig override(s): {', '.join(unknown)}")
    config = replace(base.config, **values) if values else base.config
    validate_router_config(config)
    resolved_name = normalized if not values else f"{normalized}+overrides"
    return ResolvedProfile(
        name=resolved_name,
        description=base.description,
        config=config,
    )


def custom_profile(config: RouterConfig, name: str = "custom") -> ResolvedProfile:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("custom profile name must be non-empty text")
    validate_router_config(config)
    return ResolvedProfile(
        name=name.strip(),
        description="Explicit RouterConfig supplied by the application.",
        config=config,
    )


def validate_router_config(config: RouterConfig) -> None:
    non_negative = (
        "recent_turns",
        "minimum_compress_chars",
        "image_min_chars",
        "cache_reuse_threshold",
    )
    positive = (
        "image_width",
        "image_height",
        "image_page_chars",
    )
    ratios = (
        "summary_ratio",
        "crumb_ratio",
        "cache_equivalent_ratio",
    )
    for name in non_negative:
        value = getattr(config, name)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"RouterConfig.{name} must be a non-negative integer")
    for name in positive:
        value = getattr(config, name)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ValueError(f"RouterConfig.{name} must be a positive integer")
    for name in ratios:
        value = getattr(config, name)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(f"RouterConfig.{name} must be numeric")
        if not 0 < float(value) <= 1:
            raise ValueError(f"RouterConfig.{name} must be greater than 0 and at most 1")
    if not isinstance(config.vision_allowed, bool):
        raise ValueError("RouterConfig.vision_allowed must be boolean")


__all__ = [
    "ResolvedProfile",
    "available_profiles",
    "custom_profile",
    "resolve_profile",
    "validate_router_config",
]
