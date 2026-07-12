from __future__ import annotations

from pathlib import Path

import pytest

from crumbcontext import (
    ContextBlock,
    Lane,
    ROUTE_PLAN_SCHEMA,
    RouterConfig,
    available_profiles,
    build_routed_request,
    resolve_profile,
    route_blocks,
)


def old_block(
    block_id: str,
    *,
    kind: str = "docs",
    content: str | None = None,
    reuse_count: int = 0,
) -> ContextBlock:
    return ContextBlock(
        id=block_id,
        role="user",
        kind=kind,
        content=content or ("key=value\n" * 900),
        age_turns=20,
        reuse_count=reuse_count,
    )


def test_expected_profiles_are_available_and_deterministic():
    assert available_profiles() == (
        "safe-default",
        "text-only",
        "cache-heavy",
        "strict-exact",
    )
    first = resolve_profile("text-only")
    second = resolve_profile("TEXT-ONLY")
    assert first == second
    assert first.config.vision_allowed is False


def test_text_only_profile_never_routes_images():
    policy = resolve_profile("text-only")
    plan = route_blocks(
        [old_block("dense")],
        policy.config,
        profile_name=policy.name,
    )
    assert all(item.lane is not Lane.IMAGE for item in plan.blocks)
    assert plan.profile_name == "text-only"
    assert plan.resolved_config["vision_allowed"] is False


def test_cache_heavy_profile_prefers_reused_reference_cache():
    policy = resolve_profile("cache-heavy")
    plan = route_blocks(
        [old_block("reused", reuse_count=1)],
        policy.config,
        profile_name=policy.name,
    )
    assert plan.blocks[0].lane is Lane.CACHE
    assert plan.resolved_config["cache_reuse_threshold"] == 1


def test_strict_exact_profile_keeps_practical_blocks_exact():
    policy = resolve_profile("strict-exact")
    plan = route_blocks(
        [
            old_block("dense"),
            old_block("memory", kind="memory", content="decision=yes\n" * 900),
        ],
        policy.config,
        profile_name=policy.name,
    )
    assert {item.lane for item in plan.blocks} == {Lane.EXACT}
    assert plan.estimated_routed_tokens == plan.estimated_text_tokens


def test_safe_overrides_are_explicit_and_recorded(tmp_path: Path):
    bundle = build_routed_request(
        "Return the exact value.",
        [
            {
                "id": "system",
                "role": "system",
                "kind": "instruction",
                "content": "Never alter exact values.",
                "authoritative": True,
            },
            {
                "id": "history",
                "role": "user",
                "kind": "docs",
                "content": "item=42\n" * 600,
                "age_turns": 10,
            },
        ],
        tmp_path / "bundle",
        profile="safe-default",
        config_overrides={"vision_allowed": False, "recent_turns": 4},
    )
    data = bundle.plan.to_dict()
    assert data["schema_version"] == ROUTE_PLAN_SCHEMA
    assert data["routing"]["profile"] == "safe-default+overrides"
    assert data["routing"]["config"]["vision_allowed"] is False
    assert data["routing"]["config"]["recent_turns"] == 4
    assert bundle.request.metadata["routing_profile"] == "safe-default+overrides"


def test_profile_and_config_cannot_be_mixed(tmp_path: Path):
    with pytest.raises(ValueError, match="either an explicit RouterConfig"):
        build_routed_request(
            "Task",
            [{"id": "one", "content": "hello"}],
            tmp_path,
            config=RouterConfig(),
            profile="text-only",
        )


def test_unknown_profile_override_and_unsafe_values_are_rejected():
    with pytest.raises(ValueError, match="unknown routing profile"):
        resolve_profile("aggressive-magic")
    with pytest.raises(ValueError, match="unknown RouterConfig override"):
        resolve_profile("safe-default", {"secret_mode": True})
    with pytest.raises(ValueError, match="summary_ratio"):
        resolve_profile("safe-default", {"summary_ratio": 0})
    with pytest.raises(ValueError, match="recent_turns"):
        resolve_profile("safe-default", {"recent_turns": -1})
    with pytest.raises(ValueError, match="vision_allowed"):
        resolve_profile("safe-default", {"vision_allowed": "yes"})
