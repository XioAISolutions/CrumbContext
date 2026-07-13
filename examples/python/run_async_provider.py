#!/usr/bin/env python3
"""Run an existing provider through the supported async API."""

from __future__ import annotations

import asyncio
import json

from crumbcontext import build_baseline_request
from crumbcontext.async_api import execute_named_provider_async


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
        name="async-provider-example",
    )
    response = await execute_named_provider_async(request, "mock")
    print(json.dumps(response.to_dict(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
