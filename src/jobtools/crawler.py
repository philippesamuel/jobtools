from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import html2text
from playwright.sync_api import sync_playwright


def fetch_page(url: str, output_dir: Path) -> tuple[Path, Path]:
    """
    Fetch *url* with a headless browser, save:
      - output_dir/job-post-raw.html
      - output_dir/job-post-raw.md

    Returns (html_path, md_path).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    html_path = output_dir / "job-post-raw.html"
    md_path = output_dir / "job-post-raw.md"

    html_content = _fetch_body_html(url)
    html_path.write_text(html_content, encoding="utf-8")

    md_content = _html_to_md(html_content, url)
    md_path.write_text(md_content, encoding="utf-8")

    return html_path, md_path


def _fetch_body_html(url: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Block images, fonts, media — we only need text
        page.route(
            "**/*",
            lambda route: route.abort()
            if route.request.resource_type in {"image", "media", "font"}
            else route.continue_(),
        )

        page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        # Wait for body to be present
        page.wait_for_selector("body", timeout=10_000)

        body_html: str = page.evaluate("() => document.body.innerHTML")
        browser.close()

    return body_html


def _html_to_md(html: str, source_url: str) -> str:
    converter = html2text.HTML2Text()
    converter.ignore_links = False
    converter.ignore_images = True
    converter.ignore_tables = False
    converter.body_width = 0  # no line wrapping

    header = (
        f"<!-- source: {source_url} -->\n"
        f"<!-- scraped_at: {datetime.now(timezone.utc).isoformat()} -->\n\n"
    )
    return header + converter.handle(html)
