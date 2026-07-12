from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.release_agent import validate_request


HEAD = "a" * 40


def write_request(path: Path, **overrides):
    data = {"publish": True, "version": "0.1.0", "branch": "main"}
    data.update(overrides)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_valid_release_request(tmp_path: Path):
    request = tmp_path / "release-request.json"
    write_request(request, commit=HEAD)
    values = validate_request(request, HEAD)
    assert values == {
        "requested": "true",
        "version": "0.1.0",
        "tag": "v0.1.0",
        "commit": HEAD,
        "notes": "docs/RELEASE_NOTES_v0.1.0.md",
    }


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"publish": False}, "publish to true"),
        ({"version": "0.2.0"}, "does not match package version"),
        ({"branch": "develop"}, "only main"),
        ({"commit": "b" * 40}, "does not match"),
    ],
)
def test_rejects_unsafe_requests(tmp_path: Path, overrides: dict, message: str):
    request = tmp_path / "release-request.json"
    write_request(request, **overrides)
    with pytest.raises(ValueError, match=message):
        validate_request(request, HEAD)


def test_rejects_short_commit(tmp_path: Path):
    request = tmp_path / "release-request.json"
    write_request(request)
    with pytest.raises(ValueError, match="40-character"):
        validate_request(request, "abc123")
