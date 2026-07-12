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


def check_release(tag: str | None = None) -> str:
    pyproject = read("pyproject.toml")
    package_init = read("crumbcontext/__init__.py")
    citation = read("CITATION.cff")
    changelog = read("CHANGELOG.md")
    readme = read("README.md")
    security = read("SECURITY.md")
    publish = read(".github/workflows/publish.yml")
    release_assets = read("scripts/release_assets.py")

    project_version = capture(r'^version\s*=\s*"([^"]+)"', pyproject, "project version")
    package_version = capture(r'^__version__\s*=\s*"([^"]+)"', package_init, "package version")
    citation_version = capture(r'^version:\s*([^\s]+)', citation, "citation version")

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
        "docs/ANTHROPIC.md",
        "docs/OPENAI.md",
        "docs/RELEASE.md",
        release_notes,
        "scripts/release_assets.py",
        "tests/test_release_assets.py",
        "LICENSE",
        "SECURITY.md",
    )
    for relative in required_files:
        read(relative)

    required_readme_fragments = (
        "--provider anthropic",
        "--provider openai",
        "docs/ANTHROPIC.md",
        "docs/OPENAI.md",
        "store: false",
        "provider-reported",
        "Exact facts never depend on pixels.",
    )
    for fragment in required_readme_fragments:
        if fragment not in readme:
            raise AssertionError(f"README is missing release surface: {fragment}")

    stale_fragments = (
        "OpenAI remains on the roadmap",
        "provider network adapters are not included in v0.1",
        "The next milestone is a same-request provider counterfactual harness",
        "- [ ] OpenAI Responses adapter",
        "--provider mock|anthropic --out",
        "github.event.release.tag_name",
    )
    combined_docs = "\n".join((readme, security, changelog, read("docs/LAUNCH_KIT.md"), read("docs/RELEASE.md")))
    for fragment in stale_fragments:
        if fragment in combined_docs or fragment in publish:
            raise AssertionError(f"stale release statement remains: {fragment}")

    if f"## {project_version} - 2026-07-12" not in changelog:
        raise AssertionError("CHANGELOG must contain the dated v0.1.0 release section")

    publish_requirements = (
        'tags:',
        '"v*.*.*"',
        "python scripts/release-check.py --tag",
        "python -m build --outdir python-dist",
        "python -m twine check python-dist/*",
        "python scripts/release_assets.py",
        "actions/attest@v4",
        "artifact-metadata: write",
        "softprops/action-gh-release@v3",
        "contents: write",
        "body_path: docs/RELEASE_NOTES_${{ github.ref_name }}.md",
        "packages-dir: python-dist/",
        "pypa/gh-action-pypi-publish@release/v1",
    )
    for fragment in publish_requirements:
        if fragment not in publish:
            raise AssertionError(f"publish workflow is missing: {fragment}")

    asset_requirements = (
        '"SPDX-2.3"',
        '"SHA256SUMS.txt"',
        '"release-manifest.json"',
        '"provider_measurements"',
    )
    for fragment in asset_requirements:
        if fragment not in release_assets:
            raise AssertionError(f"release asset builder is missing: {fragment}")

    if "environment:\n      name: pypi" not in publish:
        raise AssertionError("trusted publishing must use the GitHub pypi environment")
    if "id-token: write" not in publish:
        raise AssertionError("trusted publishing and attestations require id-token: write")

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
