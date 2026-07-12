#!/usr/bin/env python3
"""Build checksums, a release manifest, and an SPDX SBOM for CrumbContext."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
PROJECT_URL = "https://github.com/XioAISolutions/CrumbContext"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dependency_name(requirement: str) -> str:
    match = re.match(r"\s*([A-Za-z0-9_.-]+)", requirement)
    if not match:
        raise ValueError(f"cannot parse dependency name from {requirement!r}")
    return match.group(1)


def load_project(root: Path = ROOT) -> dict[str, Any]:
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    project = data.get("project")
    if not isinstance(project, dict):
        raise ValueError("pyproject.toml is missing [project]")
    return project


def normalized_created(value: str | None) -> str:
    if value:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        parsed = datetime.now(timezone.utc)
    return (
        parsed.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def build_release_assets(
    input_dir: Path,
    output_dir: Path,
    tag: str,
    commit: str,
    created: str | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
    project = load_project(root)
    name = str(project["name"])
    version = str(project["version"])
    expected_tag = f"v{version}"
    if tag != expected_tag:
        raise ValueError(f"release tag {tag!r} must equal {expected_tag!r}")
    if not re.fullmatch(r"[0-9a-fA-F]{7,64}", commit):
        raise ValueError("commit must be a 7-64 character hexadecimal Git commit")

    wheels = sorted(input_dir.glob("*.whl"))
    sdists = sorted(input_dir.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise ValueError(
            "expected exactly one wheel and one source distribution, "
            f"found {len(wheels)} wheel(s) and {len(sdists)} sdist(s)"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    for old in output_dir.iterdir():
        if old.is_file():
            old.unlink()
        elif old.is_dir():
            shutil.rmtree(old)

    copied: list[Path] = []
    for source in (*wheels, *sdists):
        destination = output_dir / source.name
        shutil.copy2(source, destination)
        copied.append(destination)

    dependencies = [str(item) for item in project.get("dependencies", [])]
    artifact_records = [
        {
            "filename": path.name,
            "sha256": sha256(path),
            "size_bytes": path.stat().st_size,
        }
        for path in copied
    ]
    timestamp = normalized_created(created)
    manifest = {
        "schema_version": 1,
        "package": name,
        "version": version,
        "tag": tag,
        "commit": commit.lower(),
        "created": timestamp,
        "repository": PROJECT_URL,
        "requires_python": project.get("requires-python"),
        "dependencies": dependencies,
        "artifacts": artifact_records,
        "claims": {
            "bundled_benchmark": (
                "deterministic planning estimate for one synthetic fixture"
            ),
            "provider_measurements": (
                "must identify provider, model, fixture, request hashes, routing "
                "policy, exact recall, task completion, and response quality"
            ),
        },
    }
    manifest_path = output_dir / f"{name}-{version}-release-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    package_spdx = "SPDXRef-Package-CrumbContext"
    packages: list[dict[str, Any]] = [
        {
            "SPDXID": package_spdx,
            "name": name,
            "versionInfo": version,
            "downloadLocation": f"{PROJECT_URL}/releases/tag/{tag}",
            "filesAnalyzed": False,
            "licenseConcluded": "MIT",
            "licenseDeclared": "MIT",
            "copyrightText": "NOASSERTION",
            "supplier": "Organization: XIO AI Solutions",
            "externalRefs": [
                {
                    "referenceCategory": "PACKAGE-MANAGER",
                    "referenceType": "purl",
                    "referenceLocator": f"pkg:pypi/{name}@{version}",
                }
            ],
        }
    ]
    relationships: list[dict[str, str]] = [
        {
            "spdxElementId": "SPDXRef-DOCUMENT",
            "relationshipType": "DESCRIBES",
            "relatedSpdxElement": package_spdx,
        }
    ]
    for index, requirement in enumerate(dependencies, start=1):
        dep_name = dependency_name(requirement)
        dep_spdx = (
            f"SPDXRef-Dependency-{index}-"
            f"{re.sub(r'[^A-Za-z0-9.-]', '-', dep_name)}"
        )
        packages.append(
            {
                "SPDXID": dep_spdx,
                "name": dep_name,
                "versionInfo": requirement,
                "downloadLocation": "NOASSERTION",
                "filesAnalyzed": False,
                "licenseConcluded": "NOASSERTION",
                "licenseDeclared": "NOASSERTION",
                "copyrightText": "NOASSERTION",
                "externalRefs": [
                    {
                        "referenceCategory": "PACKAGE-MANAGER",
                        "referenceType": "purl",
                        "referenceLocator": f"pkg:pypi/{dep_name.lower()}",
                    }
                ],
            }
        )
        relationships.append(
            {
                "spdxElementId": package_spdx,
                "relationshipType": "DEPENDS_ON",
                "relatedSpdxElement": dep_spdx,
            }
        )

    sbom = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"{name}-{version}",
        "documentNamespace": (
            f"{PROJECT_URL}/releases/tag/{tag}#spdx-{commit.lower()}"
        ),
        "creationInfo": {
            "created": timestamp,
            "creators": [
                "Organization: XIO AI Solutions",
                "Tool: CrumbContext release_assets.py",
            ],
        },
        "packages": packages,
        "relationships": relationships,
    }
    sbom_path = output_dir / f"{name}-{version}.spdx.json"
    sbom_path.write_text(
        json.dumps(sbom, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    checksum_targets = sorted(path for path in output_dir.iterdir() if path.is_file())
    checksums_path = output_dir / "SHA256SUMS.txt"
    checksums_path.write_text(
        "".join(f"{sha256(path)}  {path.name}\n" for path in checksum_targets),
        encoding="utf-8",
    )

    result = {
        "manifest": str(manifest_path),
        "sbom": str(sbom_path),
        "checksums": str(checksums_path),
        "artifacts": [path.name for path in checksum_targets],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("python-dist"))
    parser.add_argument("--output", type=Path, default=Path("release-dist"))
    parser.add_argument("--tag", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--created")
    args = parser.parse_args(argv)
    try:
        build_release_assets(
            input_dir=args.input,
            output_dir=args.output,
            tag=args.tag,
            commit=args.commit,
            created=args.created,
        )
    except (OSError, KeyError, TypeError, ValueError) as exc:
        print(f"release asset build failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
