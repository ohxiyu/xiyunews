import json

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
