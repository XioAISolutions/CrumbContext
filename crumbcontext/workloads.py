from __future__ import annotations

import hashlib
import html
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from xml.sax.saxutils import escape

from .anchors import extract_anchors, unique_anchors
from .bundle import route_to_directory
from .models import ContextBlock, Lane, RoutePlan
from .profiles import available_profiles, resolve_profile
from .router import route_blocks
from .schemas import (
    WORKLOAD_MANIFEST_SCHEMA,
    WORKLOAD_RESULT_SCHEMA,
    WORKLOAD_SUITE_RESULT_SCHEMA,
    require_schema,
)

DEFAULT_PROFILES = available_profiles()
DEFAULT_MANIFEST = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "workloads"
    / "v1"
    / "manifest.json"
)
_ID = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_MAX_WORKLOADS = 100
_MAX_BLOCKS_PER_WORKLOAD = 500
_MAX_EXPANDED_BLOCK_CHARS = 2_000_000
DISCLAIMER = (
    "Token figures are deterministic routing estimates for these public synthetic "
    "fixtures. They are not provider billing records, model-quality scores, or "
    "universal savings claims."
)


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _required_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    return value.strip()


def _string_list(value: Any, label: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be an array of strings")
    result: list[str] = []
    for index, item in enumerate(value):
        result.append(_required_text(item, f"{label}[{index}]"))
    if not allow_empty and not result:
        raise ValueError(f"{label} must not be empty")
    if len(set(result)) != len(result):
        raise ValueError(f"{label} must not contain duplicates")
    return tuple(result)


def _expand_segments(value: Any, label: str) -> str:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} must be a non-empty array")
    chunks: list[str] = []
    for index, segment in enumerate(value):
        if not isinstance(segment, dict):
            raise ValueError(f"{label}[{index}] must be an object")
        text = _required_text(segment.get("text"), f"{label}[{index}].text")
        repeat = segment.get("repeat", 1)
        if not isinstance(repeat, int) or isinstance(repeat, bool) or not 1 <= repeat <= 500:
            raise ValueError(f"{label}[{index}].repeat must be an integer from 1 to 500")
        for occurrence in range(1, repeat + 1):
            chunks.append(text.replace("{index}", str(occurrence)))
    expanded = "\n".join(chunks)
    if len(expanded) > _MAX_EXPANDED_BLOCK_CHARS:
        raise ValueError(
            f"{label} expands beyond {_MAX_EXPANDED_BLOCK_CHARS:,} characters"
        )
    return expanded


def _expand_block(value: Any, index: int, workload_id: str) -> ContextBlock:
    if not isinstance(value, dict):
        raise ValueError(f"workload {workload_id!r} block {index} must be an object")
    has_content = "content" in value
    has_segments = "segments" in value
    if has_content == has_segments:
        raise ValueError(
            f"workload {workload_id!r} block {index} must declare exactly one of "
            "content or segments"
        )
    content = (
        _required_text(value.get("content"), f"workload {workload_id} block {index}.content")
        if has_content
        else _expand_segments(
            value.get("segments"),
            f"workload {workload_id} block {index}.segments",
        )
    )
    normalized = dict(value)
    normalized.pop("segments", None)
    normalized["content"] = content
    block = ContextBlock.from_dict(normalized, index=index)
    if not _ID.fullmatch(block.id):
        raise ValueError(
            f"workload {workload_id!r} block id {block.id!r} must match {_ID.pattern}"
        )
    return block


def _block_to_dict(block: ContextBlock) -> dict[str, Any]:
    value = asdict(block)
    if not value["metadata"]:
        value.pop("metadata")
    return value


@dataclass(frozen=True)
class WorkloadSpec:
    id: str
    title: str
    description: str
    tags: tuple[str, ...]
    license: str
    provenance: str
    task: str
    expected_exact: tuple[str, ...]
    required_rules: tuple[str, ...]
    blocks: tuple[ContextBlock, ...]
    fixture_sha256: str

    @classmethod
    def from_dict(cls, value: Mapping[str, Any], index: int) -> "WorkloadSpec":
        workload_id = _required_text(value.get("id"), f"workloads[{index}].id")
        if not _ID.fullmatch(workload_id):
            raise ValueError(f"workload id {workload_id!r} must match {_ID.pattern}")
        raw_blocks = value.get("blocks")
        if not isinstance(raw_blocks, list) or not raw_blocks:
            raise ValueError(f"workload {workload_id!r} blocks must be a non-empty array")
        if len(raw_blocks) > _MAX_BLOCKS_PER_WORKLOAD:
            raise ValueError(
                f"workload {workload_id!r} exceeds {_MAX_BLOCKS_PER_WORKLOAD} blocks"
            )
        blocks = tuple(
            _expand_block(item, block_index, workload_id)
            for block_index, item in enumerate(raw_blocks)
        )
        ids = [block.id for block in blocks]
        if len(set(ids)) != len(ids):
            raise ValueError(f"workload {workload_id!r} has duplicate block IDs")

        expected_exact = _string_list(
            value.get("expected_exact"),
            f"workload {workload_id}.expected_exact",
        )
        required_rules = _string_list(
            value.get("required_rules"),
            f"workload {workload_id}.required_rules",
        )
        extracted = {
            anchor.value
            for block in blocks
            for anchor in unique_anchors(extract_anchors(block.content))
        }
        missing_exact = sorted(set(expected_exact) - extracted)
        if missing_exact:
            raise ValueError(
                f"workload {workload_id!r} declares exact values not recognized by the "
                f"anchor extractor: {', '.join(missing_exact)}"
            )
        authority_text = "\n".join(
            block.content
            for block in blocks
            if block.authoritative or block.role.lower() in {"system", "developer"}
        )
        missing_rules = [rule for rule in required_rules if rule not in authority_text]
        if missing_rules:
            raise ValueError(
                f"workload {workload_id!r} required rules must originate in authority "
                f"blocks: {', '.join(missing_rules)}"
            )

        normalized = {
            "id": workload_id,
            "title": _required_text(value.get("title"), f"workload {workload_id}.title"),
            "description": _required_text(
                value.get("description"), f"workload {workload_id}.description"
            ),
            "tags": list(_string_list(value.get("tags"), f"workload {workload_id}.tags")),
            "license": _required_text(
                value.get("license"), f"workload {workload_id}.license"
            ),
            "provenance": _required_text(
                value.get("provenance"), f"workload {workload_id}.provenance"
            ),
            "task": _required_text(value.get("task"), f"workload {workload_id}.task"),
            "expected_exact": list(expected_exact),
            "required_rules": list(required_rules),
            "blocks": [_block_to_dict(block) for block in blocks],
        }
        return cls(
            id=workload_id,
            title=normalized["title"],
            description=normalized["description"],
            tags=tuple(normalized["tags"]),
            license=normalized["license"],
            provenance=normalized["provenance"],
            task=normalized["task"],
            expected_exact=expected_exact,
            required_rules=required_rules,
            blocks=blocks,
            fixture_sha256=_sha256_json(normalized),
        )

    def to_dict(self, *, include_blocks: bool = True) -> dict[str, Any]:
        value: dict[str, Any] = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "tags": list(self.tags),
            "license": self.license,
            "provenance": self.provenance,
            "task": self.task,
            "expected_exact": list(self.expected_exact),
            "required_rules": list(self.required_rules),
            "fixture_sha256": self.fixture_sha256,
        }
        if include_blocks:
            value["blocks"] = [_block_to_dict(block) for block in self.blocks]
        return value


@dataclass(frozen=True)
class WorkloadManifest:
    suite_id: str
    version: str
    title: str
    license: str
    provenance: str
    workloads: tuple[WorkloadSpec, ...]
    source_sha256: str
    schema_version: str = WORKLOAD_MANIFEST_SCHEMA

    def to_dict(self, *, include_blocks: bool = False) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "suite_id": self.suite_id,
            "version": self.version,
            "title": self.title,
            "license": self.license,
            "provenance": self.provenance,
            "source_sha256": self.source_sha256,
            "workloads": [
                workload.to_dict(include_blocks=include_blocks)
                for workload in self.workloads
            ],
        }


def load_workload_manifest(path: str | Path | None = None) -> WorkloadManifest:
    source = Path(path) if path is not None else DEFAULT_MANIFEST
    raw = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("workload manifest must be a JSON object")
    require_schema(raw, WORKLOAD_MANIFEST_SCHEMA, allow_legacy_missing=False)
    raw_workloads = raw.get("workloads")
    if not isinstance(raw_workloads, list) or not raw_workloads:
        raise ValueError("workload manifest workloads must be a non-empty array")
    if len(raw_workloads) > _MAX_WORKLOADS:
        raise ValueError(f"workload manifest exceeds {_MAX_WORKLOADS} workloads")
    workloads = tuple(
        WorkloadSpec.from_dict(item, index)
        for index, item in enumerate(raw_workloads)
        if isinstance(item, dict)
    )
    if len(workloads) != len(raw_workloads):
        raise ValueError("every workload manifest entry must be an object")
    ids = [workload.id for workload in workloads]
    if len(set(ids)) != len(ids):
        raise ValueError("workload manifest contains duplicate workload IDs")
    return WorkloadManifest(
        suite_id=_required_text(raw.get("suite_id"), "suite_id"),
        version=_required_text(raw.get("version"), "version"),
        title=_required_text(raw.get("title"), "title"),
        license=_required_text(raw.get("license"), "license"),
        provenance=_required_text(raw.get("provenance"), "provenance"),
        workloads=workloads,
        source_sha256=_sha256_json(raw),
    )


def _all_anchor_values(blocks: Iterable[ContextBlock]) -> tuple[str, ...]:
    seen: set[tuple[str, str]] = set()
    values: list[str] = []
    for block in blocks:
        for anchor in unique_anchors(extract_anchors(block.content)):
            key = (anchor.kind, anchor.value)
            if key not in seen:
                seen.add(key)
                values.append(anchor.value)
    return tuple(values)


def _artifacts_exist(plan: RoutePlan, root: Path) -> bool:
    for routed in plan.blocks:
        if routed.lane in {Lane.IMAGE, Lane.CRUMB, Lane.SUMMARY}:
            if not routed.artifact:
                return False
            for relative in routed.artifact.split(","):
                if not (root / relative).is_file():
                    return False
    return all(
        (root / name).is_file()
        for name in ("plan.json", "report.html", "anchors-all.txt")
    )


def _run_workload(
    manifest: WorkloadManifest,
    workload: WorkloadSpec,
    profile_name: str,
    output_dir: Path,
) -> dict[str, Any]:
    policy = resolve_profile(profile_name)
    blocks = list(workload.blocks)
    first = route_blocks(blocks, policy.config, profile_name=policy.name)
    second = route_blocks(blocks, policy.config, profile_name=policy.name)
    deterministic_plan = first.to_dict() == second.to_dict()

    run_root = output_dir / "runs" / workload.id / profile_name
    plan = route_to_directory(
        blocks,
        run_root,
        policy.config,
        profile_name=policy.name,
    )
    by_id = {item.block_id: item for item in plan.blocks}
    exact_values = _all_anchor_values(blocks)
    sidecars = (run_root / "anchors-all.txt").read_text(encoding="utf-8")
    exact_found = sum(1 for value in exact_values if value in sidecars)

    authority_blocks = [
        block
        for block in blocks
        if block.authoritative or block.role.lower() in {"system", "developer"}
    ]
    recent_blocks = [
        block for block in blocks if block.age_turns <= policy.config.recent_turns
    ]
    rule_blocks_exact = all(
        any(
            rule in block.content and by_id[block.id].lane is Lane.EXACT
            for block in authority_blocks
        )
        for rule in workload.required_rules
    )
    image_routes = [item for item in plan.blocks if item.lane is Lane.IMAGE]
    image_policy_honored = (
        not image_routes if not policy.config.vision_allowed else True
    ) and all(item.artifact for item in image_routes)
    checks = {
        "all_exact_anchors_preserved": exact_found == len(exact_values),
        "declared_exact_values_preserved": all(
            value in sidecars for value in workload.expected_exact
        ),
        "authority_blocks_stay_exact": all(
            by_id[block.id].lane is Lane.EXACT for block in authority_blocks
        ),
        "required_rules_stay_exact": rule_blocks_exact,
        "recent_context_stays_exact": all(
            by_id[block.id].lane is Lane.EXACT for block in recent_blocks
        ),
        "image_policy_honored": image_policy_honored,
        "strict_exact_routes_every_block_exact": (
            profile_name != "strict-exact"
            or all(item.lane is Lane.EXACT for item in plan.blocks)
        ),
        "deterministic_plan": deterministic_plan,
        "routing_artifacts_created": _artifacts_exist(plan, run_root),
    }
    lanes = Counter(item.lane.value for item in plan.blocks)
    result = {
        "schema_version": WORKLOAD_RESULT_SCHEMA,
        "suite_id": manifest.suite_id,
        "suite_version": manifest.version,
        "manifest_sha256": manifest.source_sha256,
        "workload_id": workload.id,
        "workload_title": workload.title,
        "fixture_sha256": workload.fixture_sha256,
        "tags": list(workload.tags),
        "license": workload.license,
        "provenance": workload.provenance,
        "profile": profile_name,
        "resolved_profile": policy.to_dict(),
        "passed": all(checks.values()),
        "checks": checks,
        "metrics": {
            "block_count": len(blocks),
            "original_chars": plan.original_chars,
            "estimated_text_tokens": plan.estimated_text_tokens,
            "estimated_routed_tokens": plan.estimated_routed_tokens,
            "estimated_reduction_percent": plan.reduction_percent,
            "exact_anchors_expected": len(exact_values),
            "exact_anchors_preserved": exact_found,
            "lane_counts": dict(sorted(lanes.items())),
        },
        "plan": plan.to_dict(),
        "artifact_root": str(run_root.relative_to(output_dir)),
        "disclaimer": DISCLAIMER,
    }
    result_path = output_dir / "results" / f"{workload.id}--{profile_name}.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def _aggregate_by_profile(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for profile in sorted({str(item["profile"]) for item in results}):
        selected = [item for item in results if item["profile"] == profile]
        reductions = [
            float(item["metrics"]["estimated_reduction_percent"])
            for item in selected
        ]
        output[profile] = {
            "runs": len(selected),
            "passed": sum(bool(item["passed"]) for item in selected),
            "average_estimated_reduction_percent": round(
                sum(reductions) / max(1, len(reductions)), 1
            ),
            "minimum_estimated_reduction_percent": min(reductions, default=0.0),
            "maximum_estimated_reduction_percent": max(reductions, default=0.0),
        }
    return output


def _write_html(suite: Mapping[str, Any], path: Path) -> None:
    rows: list[str] = []
    for result in suite["results"]:
        metrics = result["metrics"]
        status = "PASS" if result["passed"] else "FAIL"
        status_class = "pass" if result["passed"] else "fail"
        rows.append(
            "<tr>"
            f"<td>{html.escape(result['workload_id'])}</td>"
            f"<td>{html.escape(result['profile'])}</td>"
            f"<td class='{status_class}'>{status}</td>"
            f"<td>{metrics['estimated_text_tokens']:,}</td>"
            f"<td>{metrics['estimated_routed_tokens']:,}</td>"
            f"<td>{metrics['estimated_reduction_percent']:.1f}%</td>"
            f"<td>{metrics['exact_anchors_preserved']}/{metrics['exact_anchors_expected']}</td>"
            f"<td><code>{html.escape(result['fixture_sha256'][:12])}</code></td>"
            "</tr>"
        )
    checks = "".join(
        f"<li><strong>{html.escape(name.replace('_', ' '))}</strong>: "
        f"{'PASS' if passed else 'FAIL'}</li>"
        for name, passed in suite["checks"].items()
    )
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CrumbContext workload suite</title>
<style>
:root{{color-scheme:dark}}body{{margin:0;background:#070b13;color:#e8eef9;font:16px/1.55 Inter,system-ui,sans-serif}}main{{max-width:1180px;margin:auto;padding:44px 24px}}h1{{font-size:42px;margin-bottom:8px}}p{{color:#aab8cf}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px;margin:28px 0}}.card{{background:#101827;border:1px solid #29344a;border-radius:18px;padding:20px}}.value{{font-size:30px;font-weight:800}}table{{width:100%;border-collapse:collapse;background:#0d1523;border-radius:16px;overflow:hidden}}th,td{{padding:12px;border-bottom:1px solid #243149;text-align:left}}th{{color:#91a4c2}}.pass{{color:#53f2a3;font-weight:800}}.fail{{color:#ff7185;font-weight:800}}code{{color:#9bdcf0}}li{{margin:6px 0}}a{{color:#71dcff}}@media(max-width:760px){{table{{display:block;overflow:auto}}h1{{font-size:32px}}}}
</style></head><body><main>
<p>CRUMBCONTEXT PUBLIC EVIDENCE</p><h1>Multi-workload routing suite</h1>
<p>{html.escape(suite['disclaimer'])}</p>
<div class="grid"><div class="card"><div>Workloads</div><div class="value">{suite['summary']['workloads']}</div></div><div class="card"><div>Profiles</div><div class="value">{suite['summary']['profiles']}</div></div><div class="card"><div>Passing runs</div><div class="value">{suite['summary']['passed_runs']}/{suite['summary']['runs']}</div></div><div class="card"><div>Exact anchors</div><div class="value">{suite['summary']['exact_anchors_preserved']}/{suite['summary']['exact_anchors_expected']}</div></div></div>
<h2>Suite checks</h2><ul>{checks}</ul>
<h2>Run matrix</h2><table><thead><tr><th>Workload</th><th>Profile</th><th>Status</th><th>Text estimate</th><th>Routed estimate</th><th>Reduction</th><th>Exact anchors</th><th>Fixture hash</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
<p>Manifest SHA-256: <code>{html.escape(suite['manifest']['source_sha256'])}</code></p>
</main></body></html>"""
    path.write_text(document, encoding="utf-8")


def _write_share_card(suite: Mapping[str, Any], path: Path) -> None:
    summary = suite["summary"]
    status = "PASS" if suite["passed"] else "CHECK FAILED"
    status_fill = "#53f2a3" if suite["passed"] else "#ff7185"
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
<defs><linearGradient id="bg" x1="0" x2="1" y1="0" y2="1"><stop offset="0" stop-color="#070b13"/><stop offset="1" stop-color="#14233b"/></linearGradient><linearGradient id="glow" x1="0" x2="1"><stop offset="0" stop-color="#7c5cff"/><stop offset="1" stop-color="#27d9ff"/></linearGradient></defs>
<rect width="1200" height="630" rx="34" fill="url(#bg)"/><circle cx="1080" cy="60" r="220" fill="#7c5cff" opacity=".12"/><circle cx="80" cy="610" r="240" fill="#27d9ff" opacity=".08"/>
<text x="72" y="92" fill="#94a3bd" font-family="Inter,Arial,sans-serif" font-size="24" letter-spacing="4">CRUMBCONTEXT WORKLOAD SUITE</text>
<text x="72" y="165" fill="#ffffff" font-family="Inter,Arial,sans-serif" font-weight="800" font-size="58">Evidence beyond one transcript.</text>
<text x="72" y="215" fill="#aab6cc" font-family="Inter,Arial,sans-serif" font-size="25">Five public workloads. Four routing profiles. Exact facts stay exact.</text>
<g transform="translate(72 276)"><rect width="315" height="174" rx="22" fill="#101827" stroke="#29344a"/><text x="28" y="46" fill="#8fa0ba" font-family="Inter,Arial,sans-serif" font-size="18">RUN MATRIX</text><text x="28" y="120" fill="url(#glow)" font-family="Inter,Arial,sans-serif" font-size="66" font-weight="800">{summary['passed_runs']}/{summary['runs']}</text></g>
<g transform="translate(414 276)"><rect width="315" height="174" rx="22" fill="#101827" stroke="#29344a"/><text x="28" y="46" fill="#8fa0ba" font-family="Inter,Arial,sans-serif" font-size="18">EXACT ANCHORS</text><text x="28" y="120" fill="#ffffff" font-family="Inter,Arial,sans-serif" font-size="54" font-weight="800">{summary['exact_anchors_preserved']}/{summary['exact_anchors_expected']}</text></g>
<g transform="translate(756 276)"><rect width="372" height="174" rx="22" fill="#101827" stroke="#29344a"/><text x="28" y="46" fill="#8fa0ba" font-family="Inter,Arial,sans-serif" font-size="18">SELF-CHECK</text><text x="28" y="120" fill="{status_fill}" font-family="Inter,Arial,sans-serif" font-size="54" font-weight="800">{escape(status)}</text></g>
<text x="72" y="526" fill="#8fa0ba" font-family="ui-monospace,Menlo,monospace" font-size="20">crumbcontext workloads --out workload-proof</text>
<text x="72" y="572" fill="#65738b" font-family="Inter,Arial,sans-serif" font-size="17">Planning estimates, not provider billing claims • github.com/XioAISolutions/CrumbContext</text>
</svg>"""
    path.write_text(svg, encoding="utf-8")


def run_workload_suite(
    output_dir: str | Path,
    *,
    manifest_path: str | Path | None = None,
    profiles: Sequence[str] | None = None,
) -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    manifest = load_workload_manifest(manifest_path)
    selected = tuple(profiles or DEFAULT_PROFILES)
    if not selected:
        raise ValueError("at least one routing profile is required")
    if len(set(selected)) != len(selected):
        raise ValueError("routing profiles must not contain duplicates")
    supported = set(available_profiles())
    unknown = sorted(set(selected) - supported)
    if unknown:
        raise ValueError(f"unknown workload-suite profile(s): {', '.join(unknown)}")

    results = [
        _run_workload(manifest, workload, profile, output)
        for workload in manifest.workloads
        for profile in selected
    ]
    lane_totals: Counter[str] = Counter()
    for result in results:
        lane_totals.update(result["metrics"]["lane_counts"])
    expected_runs = len(manifest.workloads) * len(selected)
    exact_expected = sum(
        int(result["metrics"]["exact_anchors_expected"]) for result in results
    )
    exact_preserved = sum(
        int(result["metrics"]["exact_anchors_preserved"]) for result in results
    )
    required_lanes = {"exact", "cache", "crumb", "summary"}
    if "safe-default" in selected:
        required_lanes.add("image")
    suite_checks = {
        "run_matrix_complete": len(results) == expected_runs,
        "all_runs_pass": all(bool(result["passed"]) for result in results),
        "all_exact_anchors_preserved": exact_preserved == exact_expected,
        "required_lane_coverage": required_lanes <= set(lane_totals),
        "manifest_and_fixture_hashes_present": (
            len(manifest.source_sha256) == 64
            and all(len(result["fixture_sha256"]) == 64 for result in results)
        ),
    }
    suite = {
        "schema_version": WORKLOAD_SUITE_RESULT_SCHEMA,
        "passed": all(suite_checks.values()),
        "checks": suite_checks,
        "manifest": manifest.to_dict(include_blocks=False),
        "profiles": list(selected),
        "summary": {
            "workloads": len(manifest.workloads),
            "profiles": len(selected),
            "runs": len(results),
            "passed_runs": sum(bool(result["passed"]) for result in results),
            "exact_anchors_expected": exact_expected,
            "exact_anchors_preserved": exact_preserved,
            "lane_counts": dict(sorted(lane_totals.items())),
            "by_profile": _aggregate_by_profile(results),
        },
        "results": results,
        "disclaimer": DISCLAIMER,
    }
    (output / "suite.json").write_text(
        json.dumps(suite, indent=2),
        encoding="utf-8",
    )
    (output / "manifest-expanded.json").write_text(
        json.dumps(manifest.to_dict(include_blocks=True), indent=2),
        encoding="utf-8",
    )
    _write_html(suite, output / "report.html")
    _write_share_card(suite, output / "share-card.svg")
    return suite


__all__ = [
    "DEFAULT_MANIFEST",
    "DEFAULT_PROFILES",
    "DISCLAIMER",
    "WorkloadManifest",
    "WorkloadSpec",
    "load_workload_manifest",
    "run_workload_suite",
]
