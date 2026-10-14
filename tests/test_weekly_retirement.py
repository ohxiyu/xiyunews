"""Retired public sections must not be regenerated or advertised."""
from pathlib import Path
import pytest

from src.api_output import render_sitemap
from src.main import main


def test_weekly_is_no_longer_a_runnable_mode(monkeypatch):
    monkeypatch.setattr("sys.argv", ["bmtnews", "--mode", "weekly"])
    with pytest.raises(SystemExit) as result:
        main()
    assert result.value.code == 2


def test_weekly_has_no_scheduled_workflow_or_sitemap_entry():
    assert not Path(".github/workflows/weekly-review.yml").exists()
    assert "/weekly/" not in render_sitemap([], generated_date="2026-10-14")
    for config in [Path("_config.yml"), Path("docs/_config.yml")]:
        text = config.read_text()
        for excluded in ['"weekly"', '"weekly.html"', '"en/weekly"', '"en/weekly.html"']:
            assert f"  - {excluded}" in text
