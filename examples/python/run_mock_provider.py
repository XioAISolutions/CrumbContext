#!/usr/bin/env python3
"""Execute a canonical request through the offline mock provider."""

from __future__ import annotations

import json

from crumbcontext import build_baseline_request, execute_provider


BLOCKS = [
    {
        "id": "system",
        "role": "system",
        "kind": "instruction",
        "content": "Return JSON and preserve exact values.",
        "authoritative": True,
    },
    {
        "id": "current",
        "role": "user",
        "kind": "message",
        "content": "The release SHA is abcdef1234567890abcdef1234567890.",
        "age_turns": 0,
    },
]


def main() -> None:
    request = build_baseline_request(
        "Return JSON containing the release SHA.",
        BLOCKS,
        name="mock-provider-example",
    )
    response = execute_provider(request, "mock")
    print(json.dumps(response.to_dict(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
