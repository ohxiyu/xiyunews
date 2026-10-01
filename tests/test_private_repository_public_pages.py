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
        "docs/about/index.md", "docs/contact/index.md", "docs/legal/index.md",
        "docs/llms.txt", "docs/legal/content-rights.txt",
    ):
        text = (ROOT / relative).read_text()
        assert "https://github.com/ohxiyu/xiyunews" not in text
    about = (ROOT / "docs/about/index.md").read_text()
    assert "operational repository is private" in about
    contact = (ROOT / "docs/contact/index.md").read_text()
    assert "https://x.com/ohxiyu" in contact
    assert "没有站内提交表单" in contact
    assert "Direct messages depend" in contact


def test_legal_links_have_public_static_targets() -> None:
    legal = (ROOT / "docs/legal/index.md").read_text()
    llms = (ROOT / "docs/llms.txt").read_text()
    for notice in ("software-license", "content-rights", "third-party-notices"):
        url = f"/legal/{notice}.txt"
        assert f"]({url})" in legal
        assert f"](https://xiyu.news{url})" in llms
        assert (ROOT / "docs" / url.lstrip("/")).is_file()


def test_structured_identity_does_not_advertise_inaccessible_repository() -> None:
    soup = BeautifulSoup((ROOT / "docs/_includes/head-custom.html").read_text(), "html.parser")
    data = json.loads(soup.find("script", {"type": "application/ld+json"}).string)
    organization = next(node for node in data["@graph"] if node["@type"] == "Organization")
    assert organization["url"] == "https://xiyu.news/"
    assert "https://github.com/ohxiyu/xiyunews" not in organization.get("sameAs", [])


def test_crawler_identity_points_to_public_site() -> None:
    from src.scrapers.rss import RSSScraper
    from src.scrapers.telegram import USER_AGENT

    assert "+https://xiyu.news/)" in USER_AGENT
    assert "github.com" not in USER_AGENT
    # Read the module rather than construct a scraper or contact a live feed.
    text = (ROOT / "src/scrapers/rss.py").read_text()
    assert "+https://xiyu.news/)" in text
    assert RSSScraper is not None
