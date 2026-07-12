from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "release_assets.py"
SPEC = importlib.util.spec_from_file_location("release_assets", MODULE_PATH)
assert SPEC and SPEC.loader
release_assets = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release_assets)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_build_release_assets(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    input_dir = tmp_path / "python-dist"
    output_dir = tmp_path / "release-dist"
    root.mkdir()
    input_dir.mkdir()
    (root / "pyproject.toml").write_text(
        """
[project]
name = "crumb-context"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = ["Pillow>=10.0"]
""".strip()
        + "\n",
        encoding="utf-8",
    )
    wheel = input_dir / "crumb_context-0.1.0-py3-none-any.whl"
    sdist = input_dir / "crumb_context-0.1.0.tar.gz"
    wheel.write_bytes(b"wheel-bytes")
    sdist.write_bytes(b"sdist-bytes")

    result = release_assets.build_release_assets(
        input_dir=input_dir,
        output_dir=output_dir,
        tag="v0.1.0",
        commit="c18ffec9f8afc76418f390698352b98197c8bcdb",
        created="2026-07-12T14:47:13Z",
        root=root,
    )

    manifest_path = Path(result["manifest"])
    sbom_path = Path(result["sbom"])
    checksums_path = Path(result["checksums"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sbom = json.loads(sbom_path.read_text(encoding="utf-8"))

    assert manifest["package"] == "crumb-context"
    assert manifest["tag"] == "v0.1.0"
    assert manifest["commit"] == "c18ffec9f8afc76418f390698352b98197c8bcdb"
    assert {item["filename"] for item in manifest["artifacts"]} == {wheel.name, sdist.name}
    assert sbom["spdxVersion"] == "SPDX-2.3"
    assert sbom["packages"][0]["name"] == "crumb-context"
    assert any(item["name"] == "Pillow" for item in sbom["packages"])

    checksum_lines = checksums_path.read_text(encoding="utf-8").splitlines()
    expected_names = {
        wheel.name,
        sdist.name,
        manifest_path.name,
        sbom_path.name,
    }
    assert {line.split("  ", 1)[1] for line in checksum_lines} == expected_names
    for line in checksum_lines:
        expected_digest, name = line.split("  ", 1)
        assert expected_digest == digest(output_dir / name)


def test_rejects_wrong_tag(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    input_dir = tmp_path / "python-dist"
    output_dir = tmp_path / "release-dist"
    root.mkdir()
    input_dir.mkdir()
    (root / "pyproject.toml").write_text(
        '[project]\nname = "crumb-context"\nversion = "0.1.0"\n',
        encoding="utf-8",
    )
    (input_dir / "crumb_context-0.1.0-py3-none-any.whl").write_bytes(b"wheel")
    (input_dir / "crumb_context-0.1.0.tar.gz").write_bytes(b"sdist")

    try:
        release_assets.build_release_assets(
            input_dir=input_dir,
            output_dir=output_dir,
            tag="v0.2.0",
            commit="c18ffec",
            root=root,
        )
    except ValueError as exc:
        assert "must equal 'v0.1.0'" in str(exc)
    else:
        raise AssertionError("wrong release tag was accepted")
