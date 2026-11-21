import json
import xml.etree.ElementTree as ET

import pytest

from src.brand_republish import migrate, republish


def test_self_links_only_and_original_news_state_preserved():
    original = {"site": "https://bmt.news", "items": [{"url": "https://www.bmt.news/x?y=1#u", "source": "https://example.com/bmt.news", "title": "A report", "id": "existing", "delivery": {"message_id": 12}}], "other": "https://bmt.news.example/a"}
    result = migrate(original)
    assert result["site"] == "https://xiyu.news"
    assert result["items"][0]["url"] == "https://xiyu.news/x?y=1#u"
    assert result["items"][0]["source"] == original["items"][0]["source"]
    assert result["items"][0]["delivery"] == {"message_id": 12}
    assert result["other"] == original["other"]
    assert original["site"] == "https://bmt.news"


def test_republish_is_idempotent_and_does_not_touch_queues(tmp_path):
    path = tmp_path / "api/latest.json"
    path.parent.mkdir()
    path.write_text(json.dumps({"site": "https://bmt.news"}))
    queue = tmp_path / "x-queue.json"
    queue.write_text('{"url":"https://bmt.news"}')
    assert republish(tmp_path) == 1
    assert republish(tmp_path) == 0
    assert json.loads(path.read_text())["site"] == "https://xiyu.news"
    assert queue.read_text() == '{"url":"https://bmt.news"}'


def test_xml_self_links_and_channel_title_only(tmp_path):
    feeds = tmp_path / "feeds"
    feeds.mkdir()
    atom = feeds / "crypto-zh.xml"
    atom.write_text('''<feed xmlns="http://www.w3.org/2005/Atom">
<title>BMTNews · Crypto</title><link href="https://bmt.news/feeds/crypto-zh.xml"/>
<id>https://bmt.news/feeds/crypto-zh.xml</id><entry><title>BMTNews · Original report</title>
<link href="https://bmt.news.example/report"/><summary>Original summary</summary></entry></feed>''')
    sitemap = tmp_path / "sitemap.xml"
    sitemap.write_text('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url>'
                       '<loc>https://www.bmt.news/x?y=1&amp;z=2</loc><lastmod>2026-10-01</lastmod>'
                       '</url></urlset>')
    assert republish(tmp_path) == 2
    assert republish(tmp_path) == 0
    document = ET.fromstring(atom.read_text())
    ns = {"a": "http://www.w3.org/2005/Atom"}
    assert document.find("a:title", ns).text == "xiyu.news · Crypto"
    assert document.find("a:entry/a:title", ns).text == "BMTNews · Original report"
    assert document.find("a:entry/a:link", ns).attrib["href"] == "https://bmt.news.example/report"
    assert document.find("a:entry/a:summary", ns).text == "Original summary"
    assert "https://xiyu.news/x?y=1&amp;z=2" in sitemap.read_text()
    assert "2026-10-01" in sitemap.read_text()


def test_invalid_xml_fails_without_overwriting(tmp_path):
    sitemap = tmp_path / "sitemap.xml"
    sitemap.write_text("<invalid>")
    with pytest.raises(ET.ParseError):
        republish(tmp_path)
    assert sitemap.read_text() == "<invalid>"


def test_republish_removes_only_retired_owned_weekly_sitemap_entries(tmp_path):
    sitemap = tmp_path / "sitemap.xml"
    sitemap.write_text('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join(
        f'<url><loc>{url}</loc><lastmod>2026-10-14</lastmod></url>' for url in [
            'https://bmt.news/weekly/', 'https://xiyu.news/en/weekly/2026-10-11/',
            'https://xiyu.news/threads/', 'https://example.org/weekly/',
            'https://xiyu.news/weekly-market/'
        ]) + '</urlset>')
    assert republish(tmp_path) == 1
    assert republish(tmp_path) == 0
    result = sitemap.read_text()
    assert 'https://xiyu.news/weekly/' not in result
    assert 'https://xiyu.news/en/weekly/' not in result
    assert 'https://xiyu.news/threads/' in result
    assert 'https://example.org/weekly/' in result
    assert 'https://xiyu.news/weekly-market/' in result
