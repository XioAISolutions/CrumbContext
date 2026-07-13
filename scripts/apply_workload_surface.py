#!/usr/bin/env python3
"""Apply the reviewed workload/async documentation and release-contract surface.

This is a one-time branch migration helper. It is removed before merge.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(path: str, old: str, new: str, *, sentinel: str | None = None) -> None:
    text = read(path)
    if sentinel and sentinel in text:
        return
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one target, found {count}: {old[:80]!r}")
    write(path, text.replace(old, new, 1))


def complete_readme() -> None:
    replace_once(
        "README.md",
        '  <a href="#30-second-proof"><strong>Run the proof</strong></a>\n'
        "  ·\n"
        '  <a href="#provider-measured-counterfactuals"><strong>Measure a provider</strong></a>',
        '  <a href="#30-second-proof"><strong>Run the proof</strong></a>\n'
        "  ·\n"
        '  <a href="#public-workload-suite"><strong>Run workloads</strong></a>\n'
        "  ·\n"
        '  <a href="#provider-measured-counterfactuals"><strong>Measure a provider</strong></a>',
        sentinel='href="#public-workload-suite"',
    )
    section = """## 🌐 Public workload suite

One demo transcript is not enough evidence. Run five public synthetic context shapes through all four named routing profiles:

```bash
crumbcontext workloads --out workload-proof --open
```

```text
5 workloads × 4 profiles = 20 deterministic runs
```

The suite covers coding, research, operations, tool-heavy agents, and mixed-authority conversations. Every run checks exact anchors, authority, required rules, recency, image policy, strict-exact behavior, deterministic plans, and referenced artifacts.

Outputs include aggregate and per-run JSON, full routing bundles, an HTML report, fixture and manifest SHA-256 hashes, and a share card. See [`docs/WORKLOADS.md`](docs/WORKLOADS.md) for the fixture protocol and claims boundary.

> **Claims boundary:** workload token reductions are deterministic planning estimates. They are not provider billing, answer-quality scores, or universal savings claims.

"""
    replace_once(
        "README.md",
        "## 🧠 The rule that matters",
        section + "## 🧠 The rule that matters",
        sentinel="## 🌐 Public workload suite",
    )


def complete_docs_site() -> None:
    async_page = """    Page(
        "Async and streaming API",
        "docs/ASYNC_STREAMING.md",
        "async-streaming",
        "Build",
        "Run providers without blocking and collect normalized streaming evidence.",
    ),
"""
    replace_once(
        "scripts/build_docs.py",
        '    Page(\n        "Routing profiles and schemas",',
        async_page + '    Page(\n        "Routing profiles and schemas",',
        sentinel='"docs/ASYNC_STREAMING.md"',
    )
    workload_page = """    Page(
        "Public workload suite",
        "docs/WORKLOADS.md",
        "workloads",
        "Evidence",
        "Evaluate five public context shapes across four deterministic routing profiles.",
    ),
"""
    replace_once(
        "scripts/build_docs.py",
        '    Page(\n        "Provider-measured benchmarks",',
        workload_page + '    Page(\n        "Provider-measured benchmarks",',
        sentinel='"docs/WORKLOADS.md"',
    )

    replace_once(
        "tests/test_docs_site.py",
        '    assert (output / "python-api" / "index.html").is_file()\n',
        '    assert (output / "python-api" / "index.html").is_file()\n'
        '    assert (output / "async-streaming" / "index.html").is_file()\n'
        '    assert (output / "workloads" / "index.html").is_file()\n',
        sentinel='output / "workloads" / "index.html"',
    )
    replace_once(
        "tests/test_docs_site.py",
        '        "/CrumbContext/provider-benchmarks/",\n',
        '        "/CrumbContext/async-streaming/",\n'
        '        "/CrumbContext/workloads/",\n'
        '        "/CrumbContext/provider-benchmarks/",\n',
        sentinel='"/CrumbContext/workloads/"',
    )


def complete_pypi_verification() -> None:
    replace_once(
        ".github/workflows/verify-pypi.yml",
        "          crumbcontext counterfactual --provider mock --out crumbcontext-pypi-counterfactual\n",
        "          crumbcontext counterfactual --provider mock --out crumbcontext-pypi-counterfactual\n"
        "          crumbcontext workloads --out crumbcontext-pypi-workloads\n",
        sentinel="crumbcontext workloads --out crumbcontext-pypi-workloads",
    )
    replace_once(
        ".github/workflows/verify-pypi.yml",
        "          python -c \"import json; assert json.load(open('/tmp/crumbcontext-pypi-counterfactual/counterfactual.json'))['passed']\"\n",
        "          python -c \"import json; assert json.load(open('/tmp/crumbcontext-pypi-counterfactual/counterfactual.json'))['passed']\"\n"
        "          python -c \"import json; s=json.load(open('/tmp/crumbcontext-pypi-workloads/suite.json')); assert s['passed'] and s['summary']['runs'] == 20\"\n",
        sentinel="s['summary']['runs'] == 20",
    )
    replace_once(
        ".github/workflows/verify-pypi.yml",
        "            /tmp/crumbcontext-pypi-counterfactual/\n",
        "            /tmp/crumbcontext-pypi-counterfactual/\n"
        "            /tmp/crumbcontext-pypi-workloads/\n",
        sentinel="/tmp/crumbcontext-pypi-workloads/",
    )


def complete_release_contract() -> None:
    path = "scripts/release-check.py"
    replace_once(
        path,
        '    python_api_workflow = read(".github/workflows/python-api.yml")\n',
        '    python_api_workflow = read(".github/workflows/python-api.yml")\n'
        '    async_workflow = read(".github/workflows/async-streaming.yml")\n'
        '    workload_workflow = read(".github/workflows/workloads.yml")\n',
        sentinel="workload_workflow = read",
    )
    replace_once(
        path,
        '    python_api = read("crumbcontext/api.py")\n',
        '    python_api = read("crumbcontext/api.py")\n'
        '    async_api = read("crumbcontext/async_api.py")\n'
        '    workloads = read("crumbcontext/workloads.py")\n',
        sentinel='workloads = read("crumbcontext/workloads.py")',
    )
    replace_once(
        path,
        '        "crumbcontext/schemas.py",\n',
        '        "crumbcontext/schemas.py",\n'
        '        "crumbcontext/workloads.py",\n'
        '        "crumbcontext/fixtures/workloads/v1/manifest.json",\n'
        '        "crumbcontext/async_api.py",\n'
        '        "crumbcontext/providers/async_base.py",\n'
        '        "crumbcontext/providers/async_registry.py",\n'
        '        "crumbcontext/providers/sse.py",\n'
        '        "crumbcontext/providers/streaming_adapters.py",\n',
        sentinel='"crumbcontext/fixtures/workloads/v1/manifest.json"',
    )
    replace_once(
        path,
        '        "docs/PROVIDER_BENCHMARKS.md",\n',
        '        "docs/PROVIDER_BENCHMARKS.md",\n'
        '        "docs/WORKLOADS.md",\n'
        '        "docs/ASYNC_STREAMING.md",\n',
        sentinel='"docs/WORKLOADS.md",',
    )
    replace_once(
        path,
        '        "tests/test_public_api.py",\n',
        '        "tests/test_public_api.py",\n'
        '        "tests/test_async_streaming.py",\n'
        '        "tests/test_workloads.py",\n',
        sentinel='"tests/test_workloads.py",',
    )
    replace_once(
        path,
        '        ".github/workflows/docs.yml",\n',
        '        ".github/workflows/docs.yml",\n'
        '        ".github/workflows/async-streaming.yml",\n'
        '        ".github/workflows/workloads.yml",\n',
        sentinel='".github/workflows/workloads.yml",',
    )
    replace_once(
        path,
        '            "Exact facts never depend on pixels.",\n',
        '            "Exact facts never depend on pixels.",\n'
        '            "crumbcontext workloads",\n'
        '            "docs/WORKLOADS.md",\n'
        '            "20 deterministic runs",\n',
        sentinel='"20 deterministic runs",',
    )
    replace_once(
        path,
        '            read("docs/PYTHON_API.md"),\n',
        '            read("docs/PYTHON_API.md"),\n'
        '            read("docs/ASYNC_STREAMING.md"),\n'
        '            read("docs/WORKLOADS.md"),\n',
        sentinel='read("docs/WORKLOADS.md")',
    )
    replace_once(
        path,
        '            "crumbcontext counterfactual --provider mock",\n',
        '            "crumbcontext counterfactual --provider mock",\n'
        '            "crumbcontext workloads",\n'
        '            "crumbcontext-pypi-workloads",\n',
        sentinel='"crumbcontext-pypi-workloads",',
    )

    workflow_contract = '''    require_fragments(
        async_workflow,
        (
            'python-version: ["3.10", "3.11", "3.12"]',
            "Build and install the wheel",
            "Verify the installed async surface outside the source tree",
            "Run keyless async examples against the installed wheel",
            "tests/test_async_streaming.py",
        ),
        "async streaming workflow",
    )

    require_fragments(
        workload_workflow,
        (
            'python-version: ["3.10", "3.11", "3.12"]',
            "Run the bundled suite outside the source tree",
            "Verify the installed workload contract",
            "crumbcontext workloads",
            "tests/test_workloads.py",
            "actions/upload-artifact@v7",
        ),
        "workload suite workflow",
    )

'''
    replace_once(
        path,
        "    require_fragments(\n        docs_workflow,\n",
        workflow_contract + "    require_fragments(\n        docs_workflow,\n",
        sentinel='"workload suite workflow"',
    )
    replace_once(
        path,
        '            \'ROOT / "docs" / "site-assets" / "site.js"\',\n',
        '            \'ROOT / "docs" / "site-assets" / "site.js"\',\n'
        '            \'"docs/ASYNC_STREAMING.md"\',\n'
        '            \'"docs/WORKLOADS.md"\',\n',
        sentinel='\'"docs/WORKLOADS.md"\'',
    )
    replace_once(
        path,
        '            \'Documentation = "https://xioaisolutions.github.io/CrumbContext/"\',\n',
        '            \'Documentation = "https://xioaisolutions.github.io/CrumbContext/"\',\n'
        '            \'"fixtures/workloads/v1/*.json"\',\n',
        sentinel='\'"fixtures/workloads/v1/*.json"\'',
    )
    replace_once(
        path,
        '            \'PROVIDER_REQUEST_SCHEMA = "crumbcontext.provider-request.v1"\',\n',
        '            \'PROVIDER_REQUEST_SCHEMA = "crumbcontext.provider-request.v1"\',\n'
        '            \'WORKLOAD_MANIFEST_SCHEMA = "crumbcontext.workload-manifest.v1"\',\n'
        '            \'WORKLOAD_RESULT_SCHEMA = "crumbcontext.workload-result.v1"\',\n'
        '            \'WORKLOAD_SUITE_RESULT_SCHEMA = "crumbcontext.workload-suite-result.v1"\',\n',
        sentinel="WORKLOAD_SUITE_RESULT_SCHEMA",
    )

    module_contract = '''    require_fragments(
        async_api,
        (
            "AnthropicStreamingProvider",
            "OpenAIStreamingProvider",
            "ProviderStreamCancelled",
            "execute_provider_stream",
        ),
        "async public API",
    )

    require_fragments(
        workloads,
        (
            "DEFAULT_MANIFEST",
            "load_workload_manifest",
            "run_workload_suite",
            "all_exact_anchors_preserved",
            "required_lane_coverage",
            "deterministic_plan",
            "Token figures are deterministic routing estimates",
        ),
        "workload suite implementation",
    )

'''
    replace_once(
        path,
        "    require_fragments(\n        release_agent_script,\n",
        module_contract + "    require_fragments(\n        release_agent_script,\n",
        sentinel='"workload suite implementation"',
    )


def main() -> None:
    complete_readme()
    complete_docs_site()
    complete_pypi_verification()
    complete_release_contract()
    print("workload/async project surface completed")


if __name__ == "__main__":
    main()
