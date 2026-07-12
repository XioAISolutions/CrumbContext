#!/usr/bin/env python3
"""Build and inspect a routed provider-neutral request without a provider key."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from crumbcontext import RouterConfig, build_routed_request


BLOCKS = [
    {
        "id": "system",
        "role": "system",
        "kind": "instruction",
        "content": "Return JSON and preserve exact values.",
        "authoritative": True,
    },
    {
        "id": "project-memory",
        "role": "user",
        "kind": "memory",
        "content": "Decision: keep the public API provider-neutral.",
        "age_turns": 8,
        "reuse_count": 4,
    },
    {
        "id": "historical-log",
        "role": "tool",
        "kind": "tool_result",
        "content": (
            "Old output used SHA abcdef1234567890abcdef1234567890 "
            "and https://example.com/build/42."
        ),
        "age_turns": 14,
    },
    {
        "id": "current-task",
        "role": "user",
        "kind": "message",
        "content": "Report the decision and SHA.",
        "age_turns": 0,
    },
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("python-api-example"))
    parser.add_argument("--images", action="store_true")
    args = parser.parse_args()

    bundle = build_routed_request(
        "Return JSON containing the project decision and exact SHA.",
        BLOCKS,
        args.out,
        config=RouterConfig(vision_allowed=args.images, recent_turns=2),
        name="python-api-example",
    )

    print(json.dumps(bundle.to_dict(), indent=2, ensure_ascii=False))
    print(f"\nArtifacts: {bundle.artifact_root.resolve()}")
    print(f"Estimated planning reduction: {bundle.plan.reduction_percent}%")
    print(f"Exact anchors protected: {bundle.plan.exact_anchor_count}")


if __name__ == "__main__":
    main()
