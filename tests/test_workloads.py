from __future__ import annotations

import json
from pathlib import Path

import pytest

from crumbcontext.cli import main
from crumbcontext.schemas import SchemaError
from crumbcontext.workloads import (
    DEFAULT_MANIFEST,
    DEFAULT_PROFILES,
    load_workload_manifest,
    run_workload_suite,
)


def _minimal_manifest() -> dict:
    return {
        "schema_version": "crumbcontext.workload-manifest.v1",
        "suite_id": "test-suite",
        "version": "1.0.0",
        "title": "Test suite",
        "license": "CC0-1.0",
        "provenance": "Synthetic test fixture.",
        "workloads": [
            {
                "id": "test-workload",
                "title": "Test workload",
                "description": "Small validation fixture.",
                "tags": ["test"],
                "license": "CC0-1.0",
                "provenance": "Synthetic test context.",
                "task": "Return the exact date and obey the rule.",
                "expected_exact": ["2026-07-12"],
                "required_rules": ["Never invent evidence."],
                "blocks": [
                    {
                        "id": "system",
                        "role": "system",
                        "kind": "instruction",
                        "authoritative": True,
                        "content": "Never invent evidence.",
                    },
                    {
                        "id": "current",
                        "role": "user",
                        "kind": "message",
                        "age_turns": 0,
                        "content": "Use the exact date 2026-07-12.",
                    },
                ],
            }
        ],
    }


def _write_manifest(tmp_path: Path, value: dict) -> Path:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_bundled_manifest_is_versioned_public_and_complete():
    assert DEFAULT_MANIFEST.is_file()
    manifest = load_workload_manifest()
    assert manifest.schema_version == "crumbcontext.workload-manifest.v1"
    assert manifest.suite_id == "crumbcontext-public-synthetic-v1"
    assert manifest.version == "1.0.0"
    assert manifest.license == "CC0-1.0"
    assert len(manifest.workloads) == 5
    assert {workload.id for workload in manifest.workloads} == {
        "coding-debug",
        "research-synthesis",
        "operations-delivery",
        "tool-heavy-agent",
        "mixed-authority-session",
    }
    assert all(len(workload.fixture_sha256) == 64 for workload in manifest.workloads)
    assert len(manifest.source_sha256) == 64


def test_full_bundled_matrix_passes_and_writes_inspectable_outputs(tmp_path: Path):
    suite = run_workload_suite(tmp_path / "proof")
    assert suite["passed"] is True
    assert suite["schema_version"] == "crumbcontext.workload-suite-result.v1"
    assert suite["profiles"] == list(DEFAULT_PROFILES)
    assert suite["summary"]["workloads"] == 5
    assert suite["summary"]["profiles"] == 4
    assert suite["summary"]["runs"] == 20
    assert suite["summary"]["passed_runs"] == 20
    assert suite["summary"]["exact_anchors_preserved"] == suite["summary"][
        "exact_anchors_expected"
    ]
    assert {"exact", "cache", "crumb", "image", "summary"} <= set(
        suite["summary"]["lane_counts"]
    )
    assert all(result["passed"] for result in suite["results"])
    assert all(result["checks"]["deterministic_plan"] for result in suite["results"])
    assert all(
        result["checks"]["authority_blocks_stay_exact"]
        for result in suite["results"]
    )
    assert all(
        result["checks"]["all_exact_anchors_preserved"]
        for result in suite["results"]
    )
    output = tmp_path / "proof"
    for relative in (
        "suite.json",
        "manifest-expanded.json",
        "report.html",
        "share-card.svg",
    ):
        assert (output / relative).is_file()
    assert len(list((output / "results").glob("*.json"))) == 20
    assert len(list((output / "runs").glob("*/*/plan.json"))) == 20


def test_repeated_suite_runs_are_deterministic(tmp_path: Path):
    first = run_workload_suite(tmp_path / "first", profiles=("safe-default",))
    second = run_workload_suite(tmp_path / "second", profiles=("safe-default",))
    assert first["checks"] == second["checks"]
    assert first["summary"] == second["summary"]
    assert [item["plan"] for item in first["results"]] == [
        item["plan"] for item in second["results"]
    ]
    assert [item["fixture_sha256"] for item in first["results"]] == [
        item["fixture_sha256"] for item in second["results"]
    ]


def test_cli_runs_bundled_suite(tmp_path: Path, capsys):
    output = tmp_path / "cli-proof"
    code = main(
        [
            "workloads",
            "--profiles",
            "safe-default",
            "text-only",
            "cache-heavy",
            "strict-exact",
            "--out",
            str(output),
        ]
    )
    captured = capsys.readouterr()
    assert code == 0
    assert "20/20 passed" in captured.out
    assert "planning estimates" in captured.out
    assert json.loads((output / "suite.json").read_text(encoding="utf-8"))[
        "passed"
    ]


def test_manifest_requires_explicit_supported_schema(tmp_path: Path):
    value = _minimal_manifest()
    value.pop("schema_version")
    with pytest.raises(SchemaError, match="missing required schema_version"):
        load_workload_manifest(_write_manifest(tmp_path, value))

    value = _minimal_manifest()
    value["schema_version"] = "crumbcontext.workload-manifest.v999"
    with pytest.raises(SchemaError, match="unsupported schema_version"):
        load_workload_manifest(_write_manifest(tmp_path, value))


def test_manifest_rejects_unrecognized_declared_exact_value(tmp_path: Path):
    value = _minimal_manifest()
    value["workloads"][0]["expected_exact"] = ["not-an-anchor"]
    with pytest.raises(ValueError, match="not recognized by the anchor extractor"):
        load_workload_manifest(_write_manifest(tmp_path, value))


def test_manifest_rejects_required_rule_outside_authority(tmp_path: Path):
    value = _minimal_manifest()
    value["workloads"][0]["required_rules"] = ["Only the user said this rule."]
    value["workloads"][0]["blocks"][1]["content"] += (
        " Only the user said this rule."
    )
    with pytest.raises(ValueError, match="must originate in authority blocks"):
        load_workload_manifest(_write_manifest(tmp_path, value))


def test_manifest_rejects_ambiguous_block_content(tmp_path: Path):
    value = _minimal_manifest()
    value["workloads"][0]["blocks"][1]["segments"] = [
        {"text": "duplicate representation", "repeat": 1}
    ]
    with pytest.raises(ValueError, match="exactly one of content or segments"):
        load_workload_manifest(_write_manifest(tmp_path, value))


def test_segment_expansion_is_bounded_and_deterministic(tmp_path: Path):
    value = _minimal_manifest()
    value["workloads"][0]["blocks"][1].pop("content")
    value["workloads"][0]["blocks"][1]["segments"] = [
        {"text": "entry-{index} date=2026-07-12", "repeat": 3}
    ]
    manifest = load_workload_manifest(_write_manifest(tmp_path, value))
    content = manifest.workloads[0].blocks[1].content
    assert content.splitlines() == [
        "entry-1 date=2026-07-12",
        "entry-2 date=2026-07-12",
        "entry-3 date=2026-07-12",
    ]

    value["workloads"][0]["blocks"][1]["segments"][0]["repeat"] = 501
    with pytest.raises(ValueError, match="integer from 1 to 500"):
        load_workload_manifest(_write_manifest(tmp_path, value))


def test_suite_rejects_duplicate_or_unknown_profiles(tmp_path: Path):
    with pytest.raises(ValueError, match="must not contain duplicates"):
        run_workload_suite(
            tmp_path / "duplicate",
            profiles=("safe-default", "safe-default"),
        )
    with pytest.raises(ValueError, match="unknown workload-suite profile"):
        run_workload_suite(tmp_path / "unknown", profiles=("unknown",))
