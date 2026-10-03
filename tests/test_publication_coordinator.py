import io
import json
from urllib.error import HTTPError, URLError
from unittest.mock import Mock

import pytest

from src import schedule_watchdog as watchdog


@pytest.fixture(autouse=True)
def isolate_edge_cutover(monkeypatch):
    monkeypatch.delenv("XIYUNEWS_EDGE_ENABLED", raising=False)
    monkeypatch.delenv("XIYUNEWS_RECOVERY_CHECK_TOKEN", raising=False)


def response(status, state):
    body = io.BytesIO(json.dumps({"status": state}).encode())
    body.code = status
    return body


@pytest.mark.parametrize("code,state,success,expected", [
    (200, "healthy", False, 0),
    (200, "not_due", False, 0),
    (200, "daily_dispatched", False, 1),
    (202, "daily_dispatched", True, 0),
    (202, "publication_active", False, 1),
    (503, "daily_retry_limit", True, 1),
    (503, "publication_stuck", True, 1),
])
def test_shared_coordinator(monkeypatch, code, state, success, expected):
    monkeypatch.setenv("RECOVERY_CHECK_TOKEN", "test-secret")
    opener = Mock(return_value=response(code, state))
    monkeypatch.setattr(watchdog, "urlopen", opener)
    direct = Mock()
    monkeypatch.setattr(watchdog, "dispatch_workflow", direct)
    args = ["--coordinator"] + (["--success-on-recovery"] if success else [])
    assert watchdog.main(args) == expected
    request = opener.call_args.args[0]
    assert request.method == "POST"
    assert request.get_header("Authorization") == "Bearer test-secret"
    assert request.get_header("User-agent") == "bmtnews-schedule-watchdog"
    assert "test-secret" not in request.full_url
    direct.assert_not_called()


@pytest.mark.parametrize("error", [
    URLError("unreachable"),
    HTTPError("https://example.test", 401, "Unauthorized", {}, io.BytesIO()),
    HTTPError("https://example.test", 503, "Unavailable", {},
              io.BytesIO(b'{"status":"check_failed"}')),
])
def test_coordinator_errors_never_fall_back_to_duplicate_dispatch(monkeypatch, error, capsys):
    monkeypatch.setenv("RECOVERY_CHECK_TOKEN", "test-secret")
    monkeypatch.setattr(watchdog, "urlopen", Mock(side_effect=error))
    direct = Mock()
    monkeypatch.setattr(watchdog, "dispatch_workflow", direct)
    assert watchdog.main(["--coordinator", "--success-on-recovery"]) == 1
    direct.assert_not_called()
    assert "test-secret" not in capsys.readouterr().out


def test_missing_coordinator_secret_is_fail_closed(monkeypatch):
    monkeypatch.delenv("RECOVERY_CHECK_TOKEN", raising=False)
    opener = Mock()
    monkeypatch.setattr(watchdog, "urlopen", opener)
    assert watchdog.main(["--coordinator"]) == 1
    opener.assert_not_called()


@pytest.mark.parametrize("enabled,origin", [
    ("true", "https://xiyu.news"),
    ("false", "https://bmtnews-daily-dispatcher.drminutes.workers.dev"),
    ("TRUE", "https://bmtnews-daily-dispatcher.drminutes.workers.dev"),
    ("", "https://bmtnews-daily-dispatcher.drminutes.workers.dev"),
])
def test_coordinator_switch_requires_exact_opt_in(monkeypatch, enabled, origin):
    monkeypatch.setenv("RECOVERY_CHECK_TOKEN", "test-secret")
    monkeypatch.setenv("XIYUNEWS_RECOVERY_CHECK_TOKEN", "new-test-secret")
    monkeypatch.setenv("XIYUNEWS_EDGE_ENABLED", enabled)
    opener = Mock(return_value=response(200, "healthy"))
    monkeypatch.setattr(watchdog, "urlopen", opener)
    assert watchdog.check_coordinator() == 0
    assert opener.call_args.args[0].full_url == origin + "/publication/check"
    expected = "new-test-secret" if enabled == "true" else "test-secret"
    assert opener.call_args.args[0].get_header("Authorization") == "Bearer " + expected
    assert opener.call_count == 1


def test_new_coordinator_failure_never_falls_back_to_legacy(monkeypatch):
    monkeypatch.setenv("RECOVERY_CHECK_TOKEN", "test-secret")
    monkeypatch.setenv("XIYUNEWS_RECOVERY_CHECK_TOKEN", "new-test-secret")
    monkeypatch.setenv("XIYUNEWS_EDGE_ENABLED", "true")
    opener = Mock(side_effect=URLError("unreachable"))
    monkeypatch.setattr(watchdog, "urlopen", opener)
    direct = Mock()
    monkeypatch.setattr(watchdog, "dispatch_workflow", direct)
    assert watchdog.check_coordinator(success_on_recovery=True) == 1
    assert opener.call_count == 1
    assert opener.call_args.args[0].full_url == "https://xiyu.news/publication/check"
    direct.assert_not_called()


def test_both_automatic_callers_pass_the_same_cutover_flag():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    for name in ("schedule-watchdog.yml", "feed-collection.yml"):
        content = (root / ".github/workflows" / name).read_text()
        assert "XIYUNEWS_EDGE_ENABLED: ${{ vars.XIYUNEWS_EDGE_ENABLED }}" in content
        assert "XIYUNEWS_RECOVERY_CHECK_TOKEN: ${{ secrets.XIYUNEWS_RECOVERY_CHECK_TOKEN }}" in content


def test_enabled_edge_without_new_key_does_not_reuse_legacy_key(monkeypatch):
    monkeypatch.setenv("XIYUNEWS_EDGE_ENABLED", "true")
    monkeypatch.setenv("RECOVERY_CHECK_TOKEN", "old-test-secret")
    opener = Mock()
    monkeypatch.setattr(watchdog, "urlopen", opener)
    assert watchdog.check_coordinator() == 1
    opener.assert_not_called()
