from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from pathlib import Path

from . import __version__
from .benchmark import run_benchmark
from .bundle import load_blocks, route_to_directory
from .counterfactual import (
    CounterfactualSpec,
    load_counterfactual_spec,
    run_counterfactual,
)
from .demo import counterfactual_payload, write_counterfactual, write_demo
from .router import RouterConfig, route_blocks


def _config(args) -> RouterConfig:
    return RouterConfig(
        vision_allowed=not getattr(args, "no_images", False),
        recent_turns=getattr(args, "recent_turns", 2),
    )


def _open_report(path: Path, enabled: bool) -> None:
    if enabled:
        webbrowser.open(path.resolve().as_uri())


def cmd_analyze(args) -> int:
    blocks = load_blocks(Path(args.input))
    plan = route_blocks(blocks, _config(args))
    print(json.dumps(plan.to_dict(), indent=2))
    return 0


def cmd_route(args) -> int:
    blocks = load_blocks(Path(args.input))
    out = Path(args.out)
    plan = route_to_directory(blocks, out, _config(args))
    report = out / "report.html"
    print(f"Routed {len(blocks)} blocks to {out}")
    print(
        f"Estimated tokens: {plan.estimated_text_tokens:,} -> "
        f"{plan.estimated_routed_tokens:,} ({plan.reduction_percent}% reduction)"
    )
    print(f"Protected exact anchors: {plan.exact_anchor_count}")
    print(f"Open {report}")
    _open_report(report, args.open)
    return 0


def cmd_demo(args) -> int:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    fixture = out / "demo-input.json"
    write_demo(fixture)
    blocks = load_blocks(fixture)
    plan = route_to_directory(blocks, out, _config(args))
    report = out / "report.html"
    print(f"Demo created at {report}")
    print(json.dumps(plan.to_dict()["totals"], indent=2))
    _open_report(report, args.open)
    return 0


def cmd_benchmark(args) -> int:
    out = Path(args.out)
    result = run_benchmark(out, _config(args))
    status = "PASS" if result.passed else "FAIL"
    print(f"CrumbContext benchmark: {status}")
    print(
        f"Estimated tokens: {result.estimated_text_tokens:,} -> "
        f"{result.estimated_routed_tokens:,} "
        f"({result.estimated_reduction_percent}% reduction)"
    )
    print(
        f"Exact anchors: {result.exact_anchors_preserved}/"
        f"{result.exact_anchors_expected} preserved"
    )
    print(f"Share card: {out / 'share-card.svg'}")
    print(f"Interactive report: {out / 'report.html'}")
    _open_report(out / "report.html", args.open)
    return 0 if result.passed else 1


def _provider_options(args) -> dict:
    provider = args.provider.strip().lower()
    if provider == "mock":
        return {}
    common = {
        "model": args.model,
        "max_tokens": args.max_tokens,
        "timeout_seconds": args.timeout,
        "enable_cache": not args.no_cache,
        "api_url": args.api_url,
    }
    if provider == "openai":
        common.update(
            {
                "prompt_cache_key": args.prompt_cache_key,
                "image_detail": args.image_detail,
            }
        )
    return {key: value for key, value in common.items() if value is not None}


def cmd_counterfactual(args) -> int:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.input:
        spec = load_counterfactual_spec(Path(args.input))
    else:
        fixture = out / "counterfactual-fixture.json"
        write_counterfactual(fixture)
        spec = CounterfactualSpec.from_dict(counterfactual_payload())
    result = run_counterfactual(
        spec,
        out,
        provider=args.provider,
        config=_config(args),
        provider_options=_provider_options(args),
    )
    status = "PASS" if result.passed else "FAIL"
    print(f"CrumbContext counterfactual: {status}")
    print(f"Provider: {result.provider} / {result.model}")
    print(f"Usage kind: {result.usage_kind}")
    print(
        "Input tokens: "
        f"{result.baseline.response['input_tokens']:,} -> "
        f"{result.routed.response['input_tokens']:,} "
        f"({result.input_token_reduction_percent}% reduction)"
    )
    print(
        "Routed exact recall: "
        f"{result.routed.evaluation.exact_found}/"
        f"{result.routed.evaluation.exact_expected}"
    )
    print(f"Response similarity: {result.response_similarity * 100:.1f}%")
    print(f"Report: {out / 'counterfactual.html'}")
    print(f"Share card: {out / 'counterfactual-card.svg'}")
    _open_report(out / "counterfactual.html", args.open)
    return 0 if result.passed else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crumbcontext",
        description=(
            "Protect exact facts, route stale AI context, and produce "
            "measurable context bundles."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"crumbcontext {__version__}",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    analyze = sub.add_parser(
        "analyze",
        help="Print a routing plan for a JSON transcript",
    )
    analyze.add_argument("input")
    analyze.add_argument("--no-images", action="store_true")
    analyze.add_argument("--recent-turns", type=int, default=2)
    analyze.set_defaults(func=cmd_analyze)

    route = sub.add_parser(
        "route",
        help="Write images, CRUMBs, summaries, exact anchors, and an HTML report",
    )
    route.add_argument("input")
    route.add_argument("--out", default="crumbcontext-output")
    route.add_argument("--no-images", action="store_true")
    route.add_argument("--recent-turns", type=int, default=2)
    route.add_argument("--open", action="store_true", help="Open the report in a browser")
    route.set_defaults(func=cmd_route)

    demo = sub.add_parser("demo", help="Generate a screenshot-ready routing demo")
    demo.add_argument("--out", default="crumbcontext-demo")
    demo.add_argument("--no-images", action="store_true")
    demo.add_argument("--recent-turns", type=int, default=2)
    demo.add_argument("--open", action="store_true", help="Open the report in a browser")
    demo.set_defaults(func=cmd_demo)

    benchmark = sub.add_parser(
        "benchmark",
        help="Run the reproducible self-check and generate a share card",
    )
    benchmark.add_argument("--out", default="crumbcontext-proof")
    benchmark.add_argument("--no-images", action="store_true")
    benchmark.add_argument("--recent-turns", type=int, default=2)
    benchmark.add_argument(
        "--open",
        action="store_true",
        help="Open the report in a browser",
    )
    benchmark.set_defaults(func=cmd_benchmark)

    counterfactual = sub.add_parser(
        "counterfactual",
        help="Run the same task against baseline and routed context payloads",
    )
    counterfactual.add_argument(
        "input",
        nargs="?",
        help="JSON counterfactual spec; omit to use the bundled fixture",
    )
    counterfactual.add_argument(
        "--provider",
        default="mock",
        help="mock, anthropic, or openai",
    )
    counterfactual.add_argument(
        "--model",
        help=(
            "Provider model; defaults to provider environment variable, "
            "claude-sonnet-4-6, or gpt-5.6"
        ),
    )
    counterfactual.add_argument("--max-tokens", type=int, default=1024)
    counterfactual.add_argument("--timeout", type=float, default=120.0)
    counterfactual.add_argument("--api-url", help=argparse.SUPPRESS)
    counterfactual.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable CrumbContext provider cache hints and breakpoints",
    )
    counterfactual.add_argument(
        "--prompt-cache-key",
        help="OpenAI prompt cache routing key; reports store only its SHA-256",
    )
    counterfactual.add_argument(
        "--image-detail",
        choices=("low", "high", "auto", "original"),
        default="high",
        help="OpenAI image detail for historical screenshot lanes",
    )
    counterfactual.add_argument("--out", default="crumbcontext-counterfactual")
    counterfactual.add_argument("--no-images", action="store_true")
    counterfactual.add_argument("--recent-turns", type=int, default=2)
    counterfactual.add_argument(
        "--open",
        action="store_true",
        help="Open the comparison report in a browser",
    )
    counterfactual.set_defaults(func=cmd_counterfactual)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
