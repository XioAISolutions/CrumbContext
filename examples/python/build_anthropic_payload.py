#!/usr/bin/env python3
"""Build a Fable 5 Messages payload without making a network request."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from crumbcontext import build_anthropic_payload, build_routed_request


BLOCKS = [
    {
        "id": "system",
        "role": "system",
        "kind": "instruction",
        "content": "Return JSON. Never alter exact values.",
        "authoritative": True,
    },
    *[
        {
            "id": f"stable-reference-{index}",
            "role": "user",
            "kind": "docs",
            "content": (
                f"Stable reference section {index}. "
                "The approved build SHA is abcdef1234567890abcdef1234567890.\n"
            )
            * 24,
            "age_turns": 10 + index,
            "reuse_count": 3,
        }
        for index in range(6)
    ],
    {
        "id": "current",
        "role": "user",
        "kind": "message",
        "content": "Return the approved build SHA.",
        "age_turns": 0,
    },
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="claude-fable-5")
    parser.add_argument("--out", type=Path, default=Path("anthropic-payload-example"))
    args = parser.parse_args()

    bundle = build_routed_request(
        "Return JSON containing the approved build SHA.",
        BLOCKS,
        args.out,
        profile="cache-heavy",
        name="anthropic-payload-example",
    )
    payload = build_anthropic_payload(
        bundle.request,
        model=args.model,
        max_tokens=4096,
        artifact_root=bundle.artifact_root,
        enable_cache=True,
        cache_ttl="1h",
        enable_fallback=True,
    )

    # Pass this dictionary to the Messages method exposed by the version of the
    # official Anthropic Python SDK used by your application.
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
