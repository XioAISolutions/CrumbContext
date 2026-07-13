from pathlib import Path

from crumbcontext.cli import build_parser, cmd_workloads


def test_workloads_cli_preserves_the_bundled_four_profile_default(
    tmp_path: Path,
    monkeypatch,
) -> None:
    captured = {}

    def fake_run_workload_suite(**kwargs):
        captured.update(kwargs)
        return {
            "passed": True,
            "summary": {
                "passed_runs": 20,
                "runs": 20,
                "workloads": 5,
                "profiles": 4,
                "exact_anchors_preserved": 1,
                "exact_anchors_expected": 1,
                "lane_counts": {},
            },
        }

    monkeypatch.setattr("crumbcontext.cli.run_workload_suite", fake_run_workload_suite)
    args = build_parser().parse_args(["workloads", "--out", str(tmp_path)])

    assert args.profiles is None
    assert cmd_workloads(args) == 0
    assert captured == {
        "output_dir": tmp_path,
        "manifest_path": None,
        "profiles": None,
    }
