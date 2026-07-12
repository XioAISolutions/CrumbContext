from __future__ import annotations

import json
from pathlib import Path

from crumbcontext.cli import main


def write_input(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "blocks": [
                    {
                        "id": "system",
                        "role": "system",
                        "kind": "instruction",
                        "content": "Never change exact values.",
                        "authoritative": True,
                    },
                    {
                        "id": "old",
                        "role": "user",
                        "kind": "docs",
                        "content": "key=value\n" * 900,
                        "age_turns": 20,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )


def test_analyze_strict_exact_prints_versioned_resolved_policy(
    tmp_path: Path, capsys
):
    source = tmp_path / "input.json"
    write_input(source)
    assert main(["analyze", str(source), "--profile", "strict-exact"]) == 0
    value = json.loads(capsys.readouterr().out)
    assert value["schema_version"] == "crumbcontext.route-plan.v1"
    assert value["routing"]["profile"] == "strict-exact"
    assert all(item["lane"] == "exact" for item in value["blocks"])


def test_route_records_profile_overrides(tmp_path: Path):
    source = tmp_path / "input.json"
    out = tmp_path / "out"
    write_input(source)
    assert (
        main(
            [
                "route",
                str(source),
                "--profile",
                "safe-default",
                "--no-images",
                "--recent-turns",
                "4",
                "--out",
                str(out),
            ]
        )
        == 0
    )
    plan = json.loads((out / "plan.json").read_text(encoding="utf-8"))
    assert plan["routing"]["profile"] == "safe-default+overrides"
    assert plan["routing"]["config"]["vision_allowed"] is False
    assert plan["routing"]["config"]["recent_turns"] == 4


def test_counterfactual_redacts_saved_response_bodies(tmp_path: Path):
    out = tmp_path / "proof"
    assert (
        main(
            [
                "counterfactual",
                "--provider",
                "mock",
                "--profile",
                "text-only",
                "--redact-responses",
                "--out",
                str(out),
            ]
        )
        == 0
    )
    report = json.loads((out / "counterfactual.json").read_text(encoding="utf-8"))
    assert report["plan"]["routing"]["profile"] == "text-only"
    assert report["redaction"]["response_bodies"] is True
    assert report["baseline"]["response"]["text_redacted"] is True
    assert report["routed"]["response"]["text_redacted"] is True


def test_negative_recent_turn_override_fails_cleanly(tmp_path: Path, capsys):
    source = tmp_path / "input.json"
    write_input(source)
    assert main(["analyze", str(source), "--recent-turns", "-1"]) == 1
    assert "recent_turns" in capsys.readouterr().err
