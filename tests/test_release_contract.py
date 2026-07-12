from __future__ import annotations

import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

import crumbcontext
from crumbcontext.providers import AnthropicProvider, OpenAIProvider, get_provider

ROOT = Path(__file__).resolve().parents[1]


def test_installed_metadata_matches_package_version():
    assert version("crumb-context") == crumbcontext.__version__


def test_provider_registry_exposes_both_network_adapters():
    anthropic = get_provider("anthropic", api_key="test-key")
    openai = get_provider("openai", api_key="test-key")
    assert isinstance(anthropic, AnthropicProvider)
    assert isinstance(openai, OpenAIProvider)
    assert anthropic.name == "anthropic"
    assert openai.name == "openai"


def test_release_contract_script_passes():
    completed = subprocess.run(
        [sys.executable, "scripts/release-check.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
