#!/usr/bin/env python3
"""Fail fast when release metadata, docs, assets, and publishing workflows disagree."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    path = ROOT / relative
    if not path.is_file():
        raise AssertionError(f"missing required release file: {relative}")
    return path.read_text(encoding="utf-8")


def capture(pattern: str, text: str, label: str) -> str:
    match = re.search(pattern, text, flags=re.MULTILINE)
    if not match:
        raise AssertionError(f"could not find {label}")
    return match.group(1)


def require_fragments(text: str, fragments: tuple[str, ...], label: str) -> None:
    for fragment in fragments:
        if fragment not in text:
            raise AssertionError(f"{label} is missing: {fragment}")


def check_release(tag: str | None = None) -> str:
    pyproject = read("pyproject.toml")
    package_init = read("crumbcontext/__init__.py")
    citation = read("CITATION.cff")
    changelog = read("CHANGELOG.md")
    readme = read("README.md")
    security = read("SECURITY.md")
    publish = read(".github/workflows/publish.yml")
    release_agent_workflow = read(".github/workflows/release-agent.yml")
    verify_pypi = read(".github/workflows/verify-pypi.yml")
    provider_benchmark = read(".github/workflows/provider-benchmark.yml")
    release_request_example = read(".github/release-request.example.json")
    release_agent_script = read("scripts/release_agent.py")
    release_assets = read("scripts/release_assets.py")

    project_version = capture(
        r'^version\s*=\s*"([^"]+)"',
        pyproject,
        "project version",
    )
    package_version = capture(
        r'^__version__\s*=\s*"([^"]+)"',
        package_init,
        "package version",
    )
    citation_version = capture(
        r'^version:\s*([^\s]+)',
        citation,
        "citation version",
    )

    versions = {
        "pyproject.toml": project_version,
        "crumbcontext/__init__.py": package_version,
        "CITATION.cff": citation_version,
    }
    if len(set(versions.values())) != 1:
        raise AssertionError(f"release versions disagree: {versions}")

    expected_tag = f"v{project_version}"
    if tag and tag != expected_tag:
        raise AssertionError(f"release tag {tag!r} must equal {expected_tag!r}")

    release_notes = f"docs/RELEASE_NOTES_{expected_tag}.md"
    required_files = (
        "crumbcontext/providers/anthropic.py",
        "crumbcontext/providers/openai.py",
        "crumbcontext/evidence.py",
        "docs/ANTHROPIC.md",
        "docs/OPENAI.md",
        "docs/COUNTERFACTUAL.md",
        "docs/PROVIDER_BENCHMARKS.md",
        "docs/RELEASE.md",
        release_notes,
        "scripts/release_assets.py",
        "scripts/release_agent.py",
        "tests/test_evidence.py",
        "tests/test_release_assets.py",
        "tests/test_release_agent.py",
        ".github/release-request.example.json",
        ".github/workflows/provider-benchmark.yml",
        ".github/workflows/release-agent.yml",
        ".github/workflows/verify-pypi.yml",
        "LICENSE",
        "SECURITY.md",
    )
    for relative in required_files:
        read(relative)

    require_fragments(
        readme,
        (
            "--provider anthropic",
            "--provider openai",
            "docs/ANTHROPIC.md",
            "docs/OPENAI.md",
            "store: false",
            "provider-reported",
            "Exact facts never depend on pixels.",
        ),
        "README release surface",
    )

    stale_fragments = (
        "OpenAI remains on the roadmap",
        "provider network adapters are not included in v0.1",
        "The next milestone is a same-request provider counterfactual harness",
        "- [ ] OpenAI Responses adapter",
        "--provider mock|anthropic --out",
        "github.event.release.tag_name",
    )
    combined_docs = "\n".join(
        (
            readme,
            security,
            changelog,
            read("docs/LAUNCH_KIT.md"),
            read("docs/RELEASE.md"),
        )
    )
    for fragment in stale_fragments:
        if fragment in combined_docs or fragment in publish:
            raise AssertionError(f"stale release statement remains: {fragment}")

    dated_release = re.compile(
        rf"^##\s+{re.escape(project_version)}\s+-\s+\d{{4}}-\d{{2}}-\d{{2}}$",
        flags=re.MULTILINE,
    )
    if not dated_release.search(changelog):
        raise AssertionError(
            f"CHANGELOG must contain a dated {project_version} release section"
        )

    require_fragments(
        publish,
        (
            "workflow_dispatch:",
            "commit:",
            "tags:",
            '"v*.*.*"',
            "RELEASE_TAG:",
            "RELEASE_COMMIT:",
            "python scripts/release-check.py --tag",
            'test "$(git rev-parse HEAD)" = "$RELEASE_COMMIT"',
            "python -m build --outdir python-dist",
            "python -m twine check python-dist/*",
            "python scripts/release_assets.py",
            "actions/attest@v4",
            "artifact-metadata: write",
            "softprops/action-gh-release@v3",
            "target_commitish: ${{ env.RELEASE_COMMIT }}",
            "contents: write",
            "body_path: docs/RELEASE_NOTES_${{ env.RELEASE_TAG }}.md",
            "packages-dir: python-dist/",
            "pypa/gh-action-pypi-publish@release/v1",
        ),
        "publish workflow",
    )

    require_fragments(
        release_agent_workflow,
        (
            'workflows: ["CI"]',
            "github.event.workflow_run.conclusion == 'success'",
            "scripts/release_agent.py",
            "Refuse an already published tag",
            "/git/ref/tags/$TAG",
            'echo "dispatch=false"',
            "Wait for CodeQL on the same commit",
            "gh workflow run publish.yml",
            '-f tag="$TAG" -f commit="$COMMIT"',
        ),
        "release-agent workflow",
    )

    require_fragments(
        verify_pypi,
        (
            "release:",
            "workflow_dispatch:",
            "https://pypi.org/simple",
            '"crumb-context==$VERSION"',
            'matrix:\n        python-version: ["3.10", "3.11", "3.12"]',
            "crumbcontext benchmark",
            "crumbcontext counterfactual --provider mock",
            "actions/upload-artifact@v7",
        ),
        "PyPI verification workflow",
    )

    require_fragments(
        provider_benchmark,
        (
            "workflow_dispatch:",
            "environment: provider-benchmarks",
            "ANTHROPIC_API_KEY",
            "OPENAI_API_KEY",
            "python -m crumbcontext.evidence",
            "--provider \"$PROVIDER\"",
            "--requested-model \"$MODEL\"",
            "actions/upload-artifact@v7",
        ),
        "provider benchmark workflow",
    )

    require_fragments(
        release_agent_script,
        (
            'request.get("publish") is not True',
            'branch != "main"',
            "release request commit does not match the CI-tested main commit",
            'tag = f"v{version}"',
        ),
        "release-agent validator",
    )

    require_fragments(
        release_assets,
        (
            '"SPDX-2.3"',
            '"SHA256SUMS.txt"',
            "release-manifest.json",
            '"provider_measurements"',
        ),
        "release asset builder",
    )

    require_fragments(
        release_request_example,
        (
            '"publish": true',
            '"version": "NEXT_VERSION"',
            '"branch": "main"',
        ),
        "release-request template",
    )

    if "environment:\n      name: pypi" not in publish:
        raise AssertionError("trusted publishing must use the GitHub pypi environment")
    if "id-token: write" not in publish:
        raise AssertionError(
            "trusted publishing and attestations require id-token: write"
        )

    print(f"CrumbContext release contract: PASS ({expected_tag})")
    return project_version


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", help="Expected GitHub tag, for example v0.1.0")
    args = parser.parse_args(argv)
    try:
        check_release(args.tag)
    except AssertionError as exc:
        print(f"release contract failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
