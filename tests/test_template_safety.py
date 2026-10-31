"""Safety contracts for Liquid templates consuming source/AI text."""
import re
from pathlib import Path


def test_archive_index_escapes_every_dynamic_output():
    template = Path("docs/_includes/archive-index.html").read_text() + Path("docs/_includes/event-reading-context.html").read_text()
    expressions = re.findall(r"\{\{(.*?)\}\}", template, re.S)
    assert expressions
    assert all(re.search(r"\|\s*escape\b", item) for item in expressions)


def test_event_references_use_protocol_validating_include():
    template = Path("docs/_includes/event-reading-context.html").read_text()
    assert 'href="{{ reference.url' not in template
    assert template.count('include external-reference.html') == 2
    reference = Path("docs/_includes/external-reference.html").read_text()
    assert "reference_scheme == 'https://'" in reference
    assert "reference_http == 'http://'" in reference
    assert '{{ reference_url | escape }}' in reference
    assert '{{ include.title | escape }}' in reference


def test_home_spotlight_is_escaped_and_driven_by_event_data():
    template = Path("docs/_includes/feed-home.html").read_text()
    block = template.split("site.data.threads.spotlight", 1)[1].split("</section>", 1)[0]
    assert "spotlight.event_id | escape" in block
    assert "spotlight_title | escape" in block
    assert "for step in spotlight.timeline limit: 3" in block
    assert "step_text | escape" in block
    assert "step.update_id | escape" in block
    assert "step.date | escape" in block
