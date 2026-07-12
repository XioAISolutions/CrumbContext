from __future__ import annotations

import json
import re
import time
from typing import Any

from ..anchors import extract_anchors, unique_anchors
from ..router import estimate_text_tokens
from .base import ProviderRequest, ProviderResponse

_AUTHORITY_WORDS = re.compile(
    r"\b(never|must|require|required|approval|authoritative|do not|don't|constraint)\b",
    re.IGNORECASE,
)
_SEMANTIC_WORDS = re.compile(
    r"\b(decision|constraint|warning|risk|todo|next|blocked|preserve|rename|deploy)\b",
    re.IGNORECASE,
)


def _artifact_text(value: Any) -> list[str]:
    if isinstance(value, dict):
        if value.get("type") == "text" and isinstance(value.get("content"), str):
            return [value["content"]]
        return []
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(_artifact_text(item))
        return result
    return []


def _source_texts(
    blocks: list[dict[str, Any]],
) -> tuple[list[str], list[str], list[str]]:
    """Return model-visible source text and authoritative native text.

    Operational metadata such as hashes, artifact paths, lane reasons, and IDs
    is intentionally excluded so the mock evaluates payload content rather than
    its packaging.
    """

    source: list[str] = []
    authority: list[str] = []
    sidecar_values: list[str] = []
    for block in blocks:
        for key in ("content", "cached_content", "mock_vision_source"):
            value = block.get(key)
            if isinstance(value, str):
                source.append(value)
                if key == "content" and block.get("authoritative"):
                    authority.append(value)
        sidecar = block.get("exact_anchor_sidecar")
        if isinstance(sidecar, str):
            for line in sidecar.splitlines():
                match = re.match(r"^- EXACT_\d+ kind=\S+ value=(.*)$", line)
                if match:
                    sidecar_values.append(match.group(1).replace("\\n", "\n"))
        source.extend(_artifact_text(block.get("artifact")))
    return source, authority, sidecar_values


def _unique_lines(texts: list[str], pattern: re.Pattern[str], limit: int = 24) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for text in texts:
        for line in text.splitlines():
            compact = " ".join(line.strip().split())
            if (
                not compact
                or compact in seen
                or compact.startswith(("- deny=", "- require="))
                or not pattern.search(compact)
            ):
                continue
            seen.add(compact)
            result.append(compact[:320])
            if len(result) >= limit:
                return sorted(result)
    return sorted(result)


class MockProvider:
    """Deterministic local provider for validating harness mechanics.

    This provider intentionally reports simulated token accounting. It is not a
    model-quality benchmark and its usage is never labelled as provider billed.
    """

    name = "mock"
    model = "crumbcontext-deterministic-extractor-v1"

    def run(self, request: ProviderRequest) -> ProviderResponse:
        started = time.perf_counter()
        source_texts, authority_texts, sidecar_values = _source_texts(request.blocks)
        joined = "\n".join(source_texts)
        anchors = unique_anchors(extract_anchors(joined))
        exact_values = {anchor.value for anchor in anchors}
        exact_values.update(sidecar_values)

        result = {
            "task": request.task,
            "exact_values": sorted(exact_values),
            "authority_rules": _unique_lines(authority_texts, _AUTHORITY_WORDS),
            "semantic_points": _unique_lines(source_texts, _SEMANTIC_WORDS),
        }
        text = json.dumps(result, sort_keys=True, ensure_ascii=False)
        latency_ms = (time.perf_counter() - started) * 1000
        input_tokens = (
            request.token_accounting_hint
            if request.token_accounting_hint is not None
            else estimate_text_tokens(request.canonical_json())
        )
        output_tokens = estimate_text_tokens(text)
        return ProviderResponse(
            provider=self.name,
            model=self.model,
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=round(latency_ms, 3),
            usage_kind="mock_simulated_not_billed",
            raw_usage={
                "source": "deterministic local estimate",
                "provider_billed": False,
            },
        )
