#!/usr/bin/env python3
"""Stream a canonical request with the offline mock provider."""

from __future__ import annotations

import asyncio
import json

from crumbcontext import build_baseline_request
from crumbcontext.async_api import execute_provider_stream


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
        "content": "The exact release ID is ABC-42.",
        "age_turns": 0,
    },
]


async def main() -> None:
    request = build_baseline_request(
        "Return JSON containing the exact release ID.",
        BLOCKS,
        name="streaming-example",
    )
    result = await execute_provider_stream(
        request,
        "mock",
        provider_options={"chunk_chars": 16},
        retain_events=True,
        require_complete=True,
    )
    print(
        json.dumps(
            result.to_dict(include_events=True),
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
