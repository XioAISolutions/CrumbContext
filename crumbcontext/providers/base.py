from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class ProviderRequest:
    """Canonical provider-neutral request used by the comparison harness."""

    mode: str
    task: str
    blocks: list[dict[str, Any]]
    token_accounting_hint: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def canonical_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ProviderResponse:
    provider: str
    model: str
    text: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    usage_kind: str
    raw_usage: dict[str, Any] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["total_tokens"] = self.total_tokens
        return value


class Provider(Protocol):
    name: str
    model: str

    def run(self, request: ProviderRequest) -> ProviderResponse:
        """Execute one request and return normalized usage and latency."""
