#!/usr/bin/env python3
"""Validate a maintainer-authored release request before an agent creates a tag."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:[-+][0-9A-Za-z.-]+)?$")
SHA = re.compile(r"^[0-9a-fA-F]{40}$")


def project_version(root: Path = ROOT) -> str:
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    project = data.get("project")
    if not isinstance(project, dict) or not isinstance(project.get("version"), str):
        raise ValueError("pyproject.toml is missing project.version")
    return project["version"]


def validate_request(request_path: Path, head_sha: str, root: Path = ROOT) -> dict[str, str]:
    if not request_path.is_file():
        raise ValueError(f"release request does not exist: {request_path}")
    request: Any = json.loads(request_path.read_text(encoding="utf-8"))
    if not isinstance(request, dict):
        raise ValueError("release request must be a JSON object")
    if request.get("publish") is not True:
        raise ValueError("release request must set publish to true")

    version = request.get("version")
    if not isinstance(version, str) or not SEMVER.fullmatch(version):
        raise ValueError("release request version must be valid semantic version text")
    expected = project_version(root)
    if version != expected:
        raise ValueError(f"release request version {version!r} does not match package version {expected!r}")

    branch = request.get("branch", "main")
    if branch != "main":
        raise ValueError("release requests may target only main")
    if not SHA.fullmatch(head_sha):
        raise ValueError("head SHA must be a full 40-character hexadecimal commit")

    requested_commit = request.get("commit")
    if requested_commit is not None and requested_commit != head_sha:
        raise ValueError("release request commit does not match the CI-tested main commit")

    tag = f"v{version}"
    notes = root / "docs" / f"RELEASE_NOTES_{tag}.md"
    if not notes.is_file():
        raise ValueError(f"missing release notes: {notes.relative_to(root)}")

    return {
        "requested": "true",
        "version": version,
        "tag": tag,
        "commit": head_sha.lower(),
        "notes": str(notes.relative_to(root)),
    }


def write_github_output(path: Path, values: dict[str, str]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args(argv)
    try:
        values = validate_request(args.request, args.head_sha)
        if args.github_output:
            write_github_output(args.github_output, values)
        print(json.dumps(values, indent=2, sort_keys=True))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"release request rejected: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
