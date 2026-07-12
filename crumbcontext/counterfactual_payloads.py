from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .anchors import extract_anchors, unique_anchors
from .bundle import route_to_directory
from .counterfactual_models import CounterfactualSpec
from .models import ContextBlock, Lane, RoutePlan
from .providers import ProviderRequest
from .router import RouterConfig, estimate_text_tokens


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def all_exact_values(blocks: tuple[ContextBlock, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    values: list[str] = []
    for block in blocks:
        for anchor in unique_anchors(extract_anchors(block.content)):
            if anchor.value not in seen:
                seen.add(anchor.value)
                values.append(anchor.value)
    return tuple(values)


def baseline_request(spec: CounterfactualSpec) -> ProviderRequest:
    blocks = []
    for block in spec.blocks:
        item: dict[str, Any] = {
            "id": block.id,
            "role": block.role,
            "kind": block.kind,
            "authoritative": block.authoritative,
            "content": block.content,
        }
        if block.metadata:
            item["metadata"] = block.metadata
        blocks.append(item)
    payload_text = canonical_json({"task": spec.task, "blocks": blocks})
    return ProviderRequest(
        mode="baseline",
        task=spec.task,
        blocks=blocks,
        token_accounting_hint=estimate_text_tokens(payload_text),
        metadata={
            "name": spec.name,
            "compression": "none",
            "provider_billed": False,
        },
    )


def _safe_id(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-")
    return safe or "block"


def _read_artifact(output_dir: Path, artifact: str | None) -> Any:
    if not artifact:
        return None
    values: list[dict[str, Any]] = []
    for relative in (item for item in artifact.split(",") if item):
        path = output_dir / relative
        if path.suffix.lower() == ".png":
            values.append(
                {
                    "type": "image",
                    "path": relative,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            )
        else:
            values.append(
                {
                    "type": "text",
                    "path": relative,
                    "content": path.read_text(encoding="utf-8"),
                }
            )
    return values[0] if len(values) == 1 else values


def routed_request(
    spec: CounterfactualSpec,
    output_dir: Path,
    config: RouterConfig,
) -> tuple[ProviderRequest, RoutePlan]:
    plan = route_to_directory(list(spec.blocks), output_dir, config)
    by_id = {item.block_id: item for item in plan.blocks}
    routed_blocks: list[dict[str, Any]] = []

    for block in spec.blocks:
        route = by_id[block.id]
        item: dict[str, Any] = {
            "id": block.id,
            "role": block.role,
            "kind": block.kind,
            "lane": route.lane.value,
            "reason": route.reason,
            "authoritative": block.authoritative,
        }
        if block.metadata:
            item["metadata"] = block.metadata
        anchor_path = output_dir / "crumbs" / f"{_safe_id(block.id)}-anchors.crumb"
        if anchor_path.is_file():
            item["exact_anchor_sidecar"] = anchor_path.read_text(encoding="utf-8")

        if route.lane is Lane.EXACT:
            item["content"] = block.content
        elif route.lane is Lane.CACHE:
            item["cached_content"] = block.content
            item["cache_sha256"] = sha256_text(block.content)
        elif route.lane is Lane.IMAGE:
            item["artifact"] = _read_artifact(output_dir, route.artifact)
            item["mock_vision_source"] = block.content
            item["non_authoritative"] = True
            if block.role.lower() not in {"user", "tool"}:
                item["fallback_content"] = block.content
        elif route.lane in {Lane.SUMMARY, Lane.CRUMB}:
            item["artifact"] = _read_artifact(output_dir, route.artifact)
            item["non_authoritative"] = True
        routed_blocks.append(item)

    request = ProviderRequest(
        mode="routed",
        task=spec.task,
        blocks=routed_blocks,
        token_accounting_hint=plan.estimated_routed_tokens,
        metadata={
            "name": spec.name,
            "compression": "crumbcontext",
            "provider_billed": False,
            "mock_vision_source_present": any(
                "mock_vision_source" in item for item in routed_blocks
            ),
        },
    )
    return request, plan
