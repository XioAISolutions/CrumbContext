#!/usr/bin/env python3
"""Build and validate the CrumbContext static documentation site."""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

try:
    import markdown
except ModuleNotFoundError as exc:  # pragma: no cover - operator guidance
    raise SystemExit(
        "Documentation build dependency missing. Install with: "
        "python -m pip install -e '.[docs]'"
    ) from exc

ROOT = Path(__file__).resolve().parents[1]
GITHUB_BLOB = "https://github.com/XioAISolutions/CrumbContext/blob/main/"
DEFAULT_SITE_URL = "https://xioaisolutions.github.io"


@dataclass(frozen=True)
class Page:
    title: str
    source: str
    slug: str
    section: str
    description: str


PAGES: tuple[Page, ...] = (
    Page(
        "Documentation home",
        "docs/README.md",
        "",
        "Overview",
        "Start here for CrumbContext architecture, APIs, providers, evidence, and operations.",
    ),
    Page(
        "Getting started",
        "README.md",
        "getting-started",
        "Overview",
        "Install CrumbContext, run the proof, and understand the five routing lanes.",
    ),
    Page(
        "Python integration API",
        "docs/PYTHON_API.md",
        "python-api",
        "Build",
        "Use the supported provider-neutral Python API and native payload builders.",
    ),
    Page(
        "Routing profiles and schemas",
        "docs/ROUTING_PROFILES.md",
        "routing-profiles",
        "Build",
        "Choose named routing policies, inspect resolved configuration, and read versioned evidence.",
    ),
    Page(
        "Architecture",
        "docs/ARCHITECTURE.md",
        "architecture",
        "Concepts",
        "Understand the router, lanes, exact-anchor sidecars, artifacts, and trust boundaries.",
    ),
    Page(
        "Counterfactual measurement",
        "docs/COUNTERFACTUAL.md",
        "counterfactual",
        "Evidence",
        "Run the same task against baseline and routed context under one evaluation contract.",
    ),
    Page(
        "Provider-measured benchmarks",
        "docs/PROVIDER_BENCHMARKS.md",
        "provider-benchmarks",
        "Evidence",
        "Generate guarded, reproducible Anthropic and OpenAI evidence without overstating claims.",
    ),
    Page(
        "Anthropic Messages adapter",
        "docs/ANTHROPIC.md",
        "anthropic",
        "Providers",
        "Preserve authority, exact values, images, caching, usage, and privacy with Anthropic Messages.",
    ),
    Page(
        "OpenAI Responses adapter",
        "docs/OPENAI.md",
        "openai",
        "Providers",
        "Preserve native roles, assistant phases, exact values, images, storage controls, and usage.",
    ),
    Page(
        "Security",
        "SECURITY.md",
        "security",
        "Operations",
        "Review the threat model, sensitive artifacts, provider boundaries, and reporting process.",
    ),
    Page(
        "Release process",
        "docs/RELEASE.md",
        "release",
        "Operations",
        "Build, attest, publish, and independently verify a CrumbContext release.",
    ),
    Page(
        "Roadmap",
        "ROADMAP.md",
        "roadmap",
        "Project",
        "Track measured evidence, integrations, policies, and workload-evaluation priorities.",
    ),
    Page(
        "Contributing",
        "CONTRIBUTING.md",
        "contributing",
        "Project",
        "Contribute small, tested, security-conscious changes to CrumbContext.",
    ),
)

PAGE_BY_SOURCE = {(ROOT / page.source).resolve(): page for page in PAGES}

MARKDOWN_LINK = re.compile(r"(?P<prefix>\]\()(?P<target>[^)]+)(?P<suffix>\))")
HTML_ATTRIBUTE = re.compile(
    r"(?P<prefix>\b(?:href|src)\s*=\s*[\"'])(?P<target>[^\"']+)(?P<suffix>[\"'])",
    flags=re.IGNORECASE,
)


class SearchParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.text: list[str] = []
        self.headings: list[str] = []
        self._heading_depth = 0
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style", "nav"}:
            self._ignored_depth += 1
        if tag in {"h1", "h2", "h3"}:
            self._heading_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"h1", "h2", "h3"} and self._heading_depth:
            self._heading_depth -= 1
        if tag in {"script", "style", "nav"} and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        value = " ".join(data.split())
        if not value:
            return
        self.text.append(value)
        if self._heading_depth:
            self.headings.append(value)


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.targets: list[tuple[str, str]] = []
        self.ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs) -> None:
        values = dict(attrs)
        if "id" in values and values["id"]:
            self.ids.add(values["id"])
        for attribute in ("href", "src"):
            value = values.get(attribute)
            if value:
                self.targets.append((attribute, value))


def normalize_base_path(value: str) -> str:
    stripped = value.strip()
    if not stripped or stripped == "/":
        return "/"
    return "/" + stripped.strip("/") + "/"


def page_url(page: Page, base_path: str) -> str:
    if not page.slug:
        return base_path
    return f"{base_path}{page.slug}/"


def _split_target(value: str) -> tuple[str, str, str]:
    parsed = urlsplit(value)
    suffix = ""
    if parsed.query:
        suffix += f"?{parsed.query}"
    if parsed.fragment:
        suffix += f"#{parsed.fragment}"
    return unquote(parsed.path), suffix, parsed.scheme


def rewrite_target(value: str, source: Path, base_path: str) -> str:
    stripped = value.strip()
    if not stripped or stripped.startswith("#"):
        return stripped
    path_text, suffix, scheme = _split_target(stripped)
    if scheme or stripped.startswith("//") or stripped.startswith(("mailto:", "tel:", "data:")):
        return stripped
    if path_text.startswith("/"):
        return stripped

    target = (source.parent / path_text).resolve()
    page = PAGE_BY_SOURCE.get(target)
    if page:
        return page_url(page, base_path) + suffix

    assets_root = (ROOT / "docs" / "assets").resolve()
    try:
        relative_asset = target.relative_to(assets_root)
    except ValueError:
        relative_asset = None
    if relative_asset is not None and target.is_file():
        return f"{base_path}assets/media/{relative_asset.as_posix()}{suffix}"

    if target.is_file():
        try:
            relative = target.relative_to(ROOT).as_posix()
        except ValueError:
            return stripped
        return f"{GITHUB_BLOB}{relative}{suffix}"
    return stripped


def rewrite_markdown_links(text: str, source: Path, base_path: str) -> str:
    def markdown_replacement(match: re.Match[str]) -> str:
        raw = match.group("target")
        target = raw
        title = ""
        if " " in raw and not raw.startswith("<"):
            candidate, remainder = raw.split(" ", 1)
            if remainder.lstrip().startswith(('"', "'")):
                target, title = candidate, " " + remainder
        rewritten = rewrite_target(target.strip("<>"), source, base_path)
        if target.startswith("<") and target.endswith(">"):
            rewritten = f"<{rewritten}>"
        return f"{match.group('prefix')}{rewritten}{title}{match.group('suffix')}"

    text = MARKDOWN_LINK.sub(markdown_replacement, text)

    def attribute_replacement(match: re.Match[str]) -> str:
        rewritten = rewrite_target(match.group("target"), source, base_path)
        return f"{match.group('prefix')}{rewritten}{match.group('suffix')}"

    return HTML_ATTRIBUTE.sub(attribute_replacement, text)


def render_markdown(source: Path, base_path: str) -> str:
    raw = source.read_text(encoding="utf-8")
    rewritten = rewrite_markdown_links(raw, source, base_path)
    return markdown.markdown(
        rewritten,
        extensions=("fenced_code", "tables", "toc", "sane_lists", "attr_list"),
        extension_configs={
            "toc": {
                "permalink": True,
                "permalink_class": "heading-anchor",
            }
        },
        output_format="html5",
    )


def navigation(active: Page, base_path: str) -> str:
    sections: list[str] = []
    current = None
    for page in PAGES:
        if page.section != current:
            if current is not None:
                sections.append("</ul></section>")
            current = page.section
            sections.append(
                f'<section class="nav-section"><h2>{html.escape(current)}</h2><ul>'
            )
        selected = ' aria-current="page" class="active"' if page == active else ""
        sections.append(
            f'<li><a{selected} href="{page_url(page, base_path)}">'
            f"{html.escape(page.title)}</a></li>"
        )
    sections.append("</ul></section>")
    return "".join(sections)


def page_template(page: Page, body: str, base_path: str, site_url: str) -> str:
    canonical = site_url.rstrip("/") + page_url(page, base_path)
    description = html.escape(page.description, quote=True)
    title = html.escape(page.title)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="description" content="{description}">
  <meta name="theme-color" content="#070b13">
  <meta property="og:title" content="{title} · CrumbContext">
  <meta property="og:description" content="{description}">
  <meta property="og:type" content="website">
  <meta property="og:image" content="{site_url.rstrip('/')}{base_path}assets/media/social-preview.png">
  <link rel="canonical" href="{canonical}">
  <link rel="icon" href="{base_path}assets/media/logo.svg" type="image/svg+xml">
  <link rel="stylesheet" href="{base_path}assets/site.css">
  <title>{title} · CrumbContext</title>
</head>
<body data-base-path="{base_path}">
  <a class="skip-link" href="#content">Skip to content</a>
  <header class="topbar">
    <a class="brand" href="{base_path}" aria-label="CrumbContext documentation home">
      <img src="{base_path}assets/media/logo.svg" width="36" height="36" alt="">
      <span>CrumbContext</span>
    </a>
    <div class="top-actions">
      <button id="search-toggle" class="search-toggle" type="button" aria-expanded="false" aria-controls="search-panel">Search <kbd>/</kbd></button>
      <a href="https://github.com/XioAISolutions/CrumbContext">GitHub</a>
      <a href="https://pypi.org/project/crumb-context/">PyPI</a>
    </div>
  </header>
  <div class="layout">
    <aside class="sidebar" aria-label="Documentation navigation">
      {navigation(page, base_path)}
    </aside>
    <main id="content" class="content">
      <div class="page-meta"><span>{html.escape(page.section)}</span><a href="{GITHUB_BLOB}{page.source}">Edit source</a></div>
      <article>{body}</article>
      <footer class="page-footer">
        <p>Exact facts never depend on pixels.</p>
        <p>CrumbContext is released under the MIT License.</p>
      </footer>
    </main>
  </div>
  <dialog id="search-panel" class="search-panel" aria-labelledby="search-title">
    <form method="dialog" class="search-head">
      <label id="search-title" for="search-input">Search documentation</label>
      <button value="cancel" aria-label="Close search">Close</button>
    </form>
    <input id="search-input" type="search" autocomplete="off" placeholder="Try “exact anchors” or “redact responses”">
    <p id="search-status" class="search-status" aria-live="polite"></p>
    <ol id="search-results" class="search-results"></ol>
  </dialog>
  <script src="{base_path}assets/site.js" defer></script>
</body>
</html>
"""


def output_path(output: Path, page: Page) -> Path:
    if not page.slug:
        return output / "index.html"
    return output / page.slug / "index.html"


def build_search_entry(page: Page, rendered_page: str, base_path: str) -> dict[str, object]:
    parser = SearchParser()
    parser.feed(rendered_page)
    text = " ".join(parser.text)
    return {
        "title": page.title,
        "section": page.section,
        "description": page.description,
        "url": page_url(page, base_path),
        "headings": parser.headings[:40],
        "text": text[:50000],
    }


def copy_assets(output: Path) -> None:
    assets = output / "assets"
    media = assets / "media"
    assets.mkdir(parents=True, exist_ok=True)
    media.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "docs" / "site-assets" / "site.css", assets / "site.css")
    shutil.copy2(ROOT / "docs" / "site-assets" / "site.js", assets / "site.js")
    source_media = ROOT / "docs" / "assets"
    for path in source_media.rglob("*"):
        if path.is_file():
            destination = media / path.relative_to(source_media)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)


def _local_target(value: str, base_path: str) -> tuple[str, str] | None:
    parsed = urlsplit(value)
    if parsed.scheme or value.startswith(("//", "mailto:", "tel:", "data:")):
        return None
    if value.startswith("#"):
        return "", parsed.fragment
    path = unquote(parsed.path)
    if path.startswith(base_path):
        path = path[len(base_path) :]
    elif path.startswith("/"):
        raise ValueError(f"local URL escapes configured base path {base_path!r}: {value}")
    normalized = PurePosixPath(path).as_posix().lstrip("./")
    return normalized, parsed.fragment


def check_site(output: Path, base_path: str) -> None:
    output = output.resolve()
    html_files = sorted(output.rglob("*.html"))
    if not html_files:
        raise ValueError("documentation build produced no HTML files")
    parsed_pages: dict[Path, LinkParser] = {}
    for path in html_files:
        parser = LinkParser()
        parser.feed(path.read_text(encoding="utf-8"))
        parsed_pages[path.resolve()] = parser

    errors: list[str] = []
    for source, parser in tuple(parsed_pages.items()):
        for attribute, value in parser.targets:
            try:
                local = _local_target(value, base_path)
            except ValueError as exc:
                errors.append(f"{source.relative_to(output)}: {exc}")
                continue
            if local is None:
                continue
            relative, fragment = local
            if not relative:
                target = source if value.startswith("#") else output / "index.html"
            else:
                target = output / relative
                if value.endswith("/") or target.is_dir() or not target.suffix:
                    target = target / "index.html"
            if not target.is_file():
                errors.append(
                    f"{source.relative_to(output)}: broken {attribute} {value!r}"
                )
                continue
            if fragment and target.suffix == ".html":
                target_parser = parsed_pages.get(target.resolve())
                if target_parser is None:
                    target_parser = LinkParser()
                    target_parser.feed(target.read_text(encoding="utf-8"))
                    parsed_pages[target.resolve()] = target_parser
                if fragment not in target_parser.ids:
                    errors.append(
                        f"{source.relative_to(output)}: missing anchor #{fragment} in "
                        f"{target.relative_to(output)}"
                    )
    if errors:
        raise ValueError("documentation link check failed:\n" + "\n".join(errors))

    script_sources = [
        value
        for parser in parsed_pages.values()
        for attribute, value in parser.targets
        if attribute == "src" and value.endswith(".js")
    ]
    expected_script = f"{base_path}assets/site.js"
    if set(script_sources) != {expected_script}:
        raise ValueError(
            "documentation pages may load only the local site.js asset; found "
            f"{sorted(set(script_sources))}"
        )


def build_site(
    output: Path,
    *,
    base_path: str = "/CrumbContext/",
    site_url: str = DEFAULT_SITE_URL,
) -> None:
    output = output.resolve()
    base_path = normalize_base_path(base_path)
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    copy_assets(output)

    search_entries: list[dict[str, object]] = []
    for page in PAGES:
        source = ROOT / page.source
        if not source.is_file():
            raise FileNotFoundError(f"documentation source is missing: {page.source}")
        body = render_markdown(source, base_path)
        rendered = page_template(page, body, base_path, site_url)
        destination = output_path(output, page)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered, encoding="utf-8")
        search_entries.append(build_search_entry(page, rendered, base_path))

    (output / "search.json").write_text(
        json.dumps(search_entries, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (output / ".nojekyll").write_text("", encoding="utf-8")
    (output / "robots.txt").write_text("User-agent: *\nAllow: /\n", encoding="utf-8")
    sitemap = "\n".join(
        f"  <url><loc>{html.escape(site_url.rstrip('/') + page_url(page, base_path))}</loc></url>"
        for page in PAGES
    )
    (output / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{sitemap}\n</urlset>\n',
        encoding="utf-8",
    )
    (output / "404.html").write_text(
        page_template(
            PAGES[0],
            f'<h1>Page not found</h1><p>Return to the <a href="{base_path}">documentation home</a>.</p>',
            base_path,
            site_url,
        ),
        encoding="utf-8",
    )
    check_site(output, base_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("_site"))
    parser.add_argument("--base-path", default="/CrumbContext/")
    parser.add_argument("--site-url", default=DEFAULT_SITE_URL)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        build_site(args.out, base_path=args.base_path, site_url=args.site_url)
    except (OSError, ValueError) as exc:
        print(f"documentation build failed: {exc}", file=sys.stderr)
        return 1
    print(f"CrumbContext documentation: PASS ({args.out.resolve()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
