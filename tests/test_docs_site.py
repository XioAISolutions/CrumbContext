from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "crumbcontext_build_docs",
    ROOT / "scripts" / "build_docs.py",
)
assert SPEC and SPEC.loader
build_docs = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build_docs)


def test_builds_all_pages_search_assets_and_metadata(tmp_path: Path):
    output = tmp_path / "site"
    build_docs.build_site(
        output,
        base_path="/CrumbContext/",
        site_url="https://xioaisolutions.github.io",
    )

    assert (output / "index.html").is_file()
    assert (output / "getting-started" / "index.html").is_file()
    assert (output / "python-api" / "index.html").is_file()
    assert (output / "routing-profiles" / "index.html").is_file()
    assert (output / "security" / "index.html").is_file()
    assert (output / "assets" / "site.css").is_file()
    assert (output / "assets" / "site.js").is_file()
    assert (output / "assets" / "media" / "logo.svg").is_file()
    assert (output / "assets" / "media" / "social-preview.png").is_file()
    assert (output / ".nojekyll").is_file()
    assert (output / "404.html").is_file()
    assert (output / "sitemap.xml").is_file()

    search = json.loads((output / "search.json").read_text(encoding="utf-8"))
    assert len(search) == len(build_docs.PAGES)
    assert {entry["url"] for entry in search} >= {
        "/CrumbContext/",
        "/CrumbContext/python-api/",
        "/CrumbContext/provider-benchmarks/",
    }
    assert any("exact anchors" in entry["text"].lower() for entry in search)


def test_generated_site_uses_only_local_runtime_assets(tmp_path: Path):
    output = tmp_path / "site"
    build_docs.build_site(
        output,
        base_path="/CrumbContext/",
        site_url="https://xioaisolutions.github.io",
    )
    for path in output.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        assert '<script src="/CrumbContext/assets/site.js" defer></script>' in text
        assert "googletagmanager" not in text.lower()
        assert "google-analytics" not in text.lower()
        assert "plausible.io" not in text.lower()
        assert "cdn.jsdelivr" not in text.lower()
        assert "unpkg.com" not in text.lower()


def test_canonical_urls_and_media_are_repository_scoped(tmp_path: Path):
    output = tmp_path / "site"
    build_docs.build_site(
        output,
        base_path="/CrumbContext/",
        site_url="https://xioaisolutions.github.io",
    )
    home = (output / "index.html").read_text(encoding="utf-8")
    getting_started = (
        output / "getting-started" / "index.html"
    ).read_text(encoding="utf-8")
    assert (
        '<link rel="canonical" href="https://xioaisolutions.github.io/CrumbContext/">'
        in home
    )
    assert (
        'href="https://xioaisolutions.github.io/CrumbContext/getting-started/"'
        in getting_started
    )
    assert '/CrumbContext/assets/media/hero.svg' in getting_started
    assert '/CrumbContext/python-api/' in home


def test_link_checker_rejects_broken_local_target(tmp_path: Path):
    output = tmp_path / "site"
    build_docs.build_site(
        output,
        base_path="/CrumbContext/",
        site_url="https://xioaisolutions.github.io",
    )
    home = output / "index.html"
    home.write_text(
        home.read_text(encoding="utf-8").replace(
            "</article>",
            '<a href="/CrumbContext/does-not-exist/">broken</a></article>',
        ),
        encoding="utf-8",
    )
    try:
        build_docs.check_site(output, "/CrumbContext/")
    except ValueError as exc:
        assert "broken href" in str(exc)
    else:
        raise AssertionError("broken documentation link was not rejected")


def test_base_path_normalization():
    assert build_docs.normalize_base_path("") == "/"
    assert build_docs.normalize_base_path("/") == "/"
    assert build_docs.normalize_base_path("CrumbContext") == "/CrumbContext/"
    assert build_docs.normalize_base_path("/CrumbContext/") == "/CrumbContext/"
