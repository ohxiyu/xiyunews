"""Cloudflare Web Analytics stays one gated beacon from the official script host."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEAD = (ROOT / "docs/_includes/head-custom.html").read_text(encoding="utf-8")
CONFIG = (ROOT / "docs/_config.yml").read_text(encoding="utf-8")
BEACON = "https://static.cloudflareinsights.com/beacon.min.js"


def test_token_is_empty_or_a_cloudflare_site_token():
    lines = re.findall(r'^cloudflare_web_analytics_token: "([^"]*)"$', CONFIG, re.M)
    assert len(lines) == 1
    token = lines[0]
    assert token == "" or re.fullmatch(r"[0-9a-f]{32}", token)


def test_beacon_is_gated_on_a_non_empty_token_and_skips_the_console():
    block = re.search(r"\{% if site\.cloudflare_web_analytics_token (.*?)%\}(.*?)\{% endif %\}",
                      HEAD, re.S)
    assert block, "beacon must sit inside its own token guard"
    guard, body = block.groups()
    assert 'site.cloudflare_web_analytics_token != ""' in guard
    assert 'page.page_type != "source_console"' in guard
    assert body.count("<script") == 1 and BEACON in body
    assert "| jsonify" in body
    assert HEAD.count("cloudflareinsights") == 1


def test_no_other_third_party_script_source():
    sources = re.findall(r'<script[^>]*\ssrc="([^"]+)"', HEAD)
    external = [s for s in sources if s.startswith("http")]
    assert external == [BEACON]


def test_legal_page_discloses_cookieless_analytics():
    legal = (ROOT / "docs/legal/index.md").read_text(encoding="utf-8")
    assert "Cloudflare Web Analytics" in legal
    assert "不设置 Cookie" in legal and "sets\nno cookies" in legal
