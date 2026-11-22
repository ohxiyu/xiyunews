import pytest

from ops.release import xiyunewsctl as release


def test_status_reads_only_the_daily_site(monkeypatch):
    sources = {
        release.DAILY_HEALTH: (200, {
            "site_source_commit": "a" * 40, "site_artifact_commit": "b" * 40,
            "runner": {"status": "github-hosted"},
        }),
        release.EDITION: (200, {"date": "2026-11-21", "items": [{}]}),
    }
    monkeypatch.setattr(release, "response", sources.__getitem__)

    result = release.status()

    assert result["product"] == "xiyu.news"
    assert result["daily"]["edition"] == "2026-11-21"


def test_daily_dispatch_is_pinned_and_stops_on_different_revision(monkeypatch):
    revision = "a" * 40
    commands = []

    def run(*command, **options):
        commands.append(command)
        if command[:3] == ("gh", "workflow", "run"):
            return b"https://github.com/ohxiyu/xiyunews/actions/runs/123\n"
        if command[:2] == ("gh", "api"):
            return b"not-the-expected-revision\n"
        pytest.fail("unexpected command")

    monkeypatch.setattr(release, "response", lambda url: (200, {"site_source_commit": "old"}))
    monkeypatch.setattr(release, "main_revision", lambda: revision)
    monkeypatch.setattr(release, "run", run)

    with pytest.raises(ValueError, match="different main revision"):
        release.deploy_daily(revision)
    assert f"expected_source={revision}" in commands[0]
