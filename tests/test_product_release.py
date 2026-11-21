from pathlib import Path

import pytest

from ops.release import xiyunewsctl as release


def test_status_keeps_realtime_degradation_visible(monkeypatch):
    sources = {
        release.DAILY_HEALTH: (200, {
            "site_source_commit": "a" * 40, "site_artifact_commit": "b" * 40,
            "runner": {"status": "github-hosted"},
        }),
        release.EDITION: (200, {"date": "2026-11-21", "items": [{}]}),
        release.REALTIME_READY: (503, {
            "source_commit": "c" * 40, "ready": False, "telegram_enabled": True,
            "sources": {"spot": {"state": "live"}, "one": {"state": "degraded"}},
        }),
    }
    monkeypatch.setattr(release, "response", sources.__getitem__)

    result = release.status()

    assert result["product"] == "xiyu.news"
    assert result["daily"]["edition"] == "2026-11-21"
    assert result["realtime"]["ready"] is False
    assert result["realtime"]["sources_requiring_attention"] == {"one": "degraded"}


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


def test_realtime_already_at_revision_never_uses_ssh(monkeypatch):
    revision = "a" * 40
    monkeypatch.setattr(release, "response", lambda url: (200, {"source_commit": revision}))
    monkeypatch.setattr(release, "run", lambda *args, **kwargs: pytest.fail("unexpected SSH"))
    release.deploy_realtime(revision, Path("/unused-config"), "xiyunews-tokyo")
