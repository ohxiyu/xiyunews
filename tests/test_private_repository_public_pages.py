"""Public-site regressions for a private operational repository; fully offline."""
import json
from pathlib import Path

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]


def test_public_notices_match_canonical_rights_files() -> None:
    for canonical, published in (
        ("LICENSE", "software-license.txt"),
        ("CONTENT-LICENSE.md", "content-rights.txt"),
        ("THIRD_PARTY_NOTICES.md", "third-party-notices.txt"),
    ):
        assert (ROOT / canonical).read_bytes() == (
            ROOT / "docs/legal" / published
        ).read_bytes()


def test_public_policy_surfaces_do_not_require_private_repo_access() -> None:
    for relative in (
        "docs/contact/index.md", "docs/legal/index.md",
        "docs/legal/content-rights.txt",
    ):
        text = (ROOT / relative).read_text()
        assert "https://github.com/ohxiyu/xiyunews" not in text
    assert "https://x.com/ohxiyu" in (ROOT / "docs/_includes/author-links.html").read_text()
    contact = (ROOT / "docs/contact/index.md").read_text()
    assert "https://x.com/ohxiyu" in contact
    assert "没有站内提交表单" in contact
    assert "Direct messages depend" in contact


def test_legal_links_have_public_static_targets() -> None:
    legal = (ROOT / "docs/legal/index.md").read_text()
    for notice in ("software-license", "content-rights", "third-party-notices"):
        url = f"/legal/{notice}.txt"
        assert f"](https://xiyu.news{url})" in legal
        assert (ROOT / "docs" / url.lstrip("/")).is_file()




def test_crawler_identity_points_to_public_site() -> None:
    from src.scrapers.rss import RSSScraper
    from src.scrapers.telegram import USER_AGENT

    assert "+https://xiyu.news/)" in USER_AGENT
    assert "github.com" not in USER_AGENT
    # Read the module rather than construct a scraper or contact a live feed.
    text = (ROOT / "src/scrapers/rss.py").read_text()
    assert "+https://xiyu.news/)" in text
    assert RSSScraper is not None
