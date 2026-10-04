"""Recovery never calls AI or retries ambiguous Telegram delivery."""
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from scripts.recover_telegram_edition import (
    RecoveryBlocked, preflight, recover, validate_evidence, validate_history,
    validate_invocation,
)
from src.daily_feed import DailyFeedState
from src.models import ContentItem, SourceType, TelegramDeliveryConfig
from src.services.telegram_delivery import TelegramEditionPublisher


def evidence():
    stamp = datetime(2026, 10, 4, 3, 41, tzinfo=timezone.utc)
    state = DailyFeedState(date="2026-10-04", timezone="Asia/Shanghai", updated_at=stamp,
                          items=[ContentItem(id="one", source_type=SourceType.RSS,
                                             title="测试新闻", url="https://example.com/news",
                                             published_at=stamp, ai_score=8)])
    report = {"date": state.date, "kind": "daily_publish", "started_at": stamp.isoformat(),
              "metrics": {"displayed_today": 1}, "alerts": [{"code": "telegram_delivery_failed",
              "message": "Telegram API error 403: Forbidden: bot is not a member of the channel chat"}]}
    return state, report


def invocation(send="true"):
    return {"RECOVERY_EDITION": "2026-10-04", "SOURCE_RUN_ID": "123",
            "RECOVERY_SEND": send, "GITHUB_REF": "refs/heads/main",
            "GITHUB_REPOSITORY": "ohxiyu/xiyunews", "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_RUN_ATTEMPT": "1", "GITHUB_RUN_ID": "456", "GH_TOKEN": "test-github"}


@pytest.mark.parametrize("key,value", [
    ("RECOVERY_EDITION", "20261004"), ("RECOVERY_EDITION", "2026-02-30"),
    ("SOURCE_RUN_ID", "0"), ("SOURCE_RUN_ID", "$(echo bad)"),
    ("GITHUB_REF", "refs/heads/agent/test"), ("GITHUB_REPOSITORY", "other/repo"),
    ("GITHUB_EVENT_NAME", "push"), ("GITHUB_RUN_ATTEMPT", "2"),
])
def test_invocation_refuses_untrusted_or_repeated_send(key, value):
    env = invocation()
    env[key] = value
    with pytest.raises(RecoveryBlocked):
        validate_invocation(env)


def test_evidence_requires_exact_definite_failure_and_unchanged_edition():
    state, report = evidence()
    validate_evidence(report, state, state.date)
    for message in ["Telegram request failed: ReadTimeout", "Telegram API error 429: retry"]:
        report["alerts"][0]["message"] = message
        with pytest.raises(RecoveryBlocked):
            validate_evidence(report, state, state.date)
    state, report = evidence()
    report["metrics"]["telegram_messages_sent"] = 1
    with pytest.raises(RecoveryBlocked):
        validate_evidence(report, state, state.date)
    state, report = evidence()
    state.updated_at = datetime.now(timezone.utc)
    with pytest.raises(RecoveryBlocked):
        validate_evidence(report, state, state.date)
    state, report = evidence()
    with pytest.raises(RecoveryBlocked):
        validate_evidence(report, state, "2026-10-03")


def test_history_checks_later_pages_and_refuses_even_failed_send():
    pages = []
    def handler(request):
        page = int(request.url.params["page"])
        pages.append(page)
        rows = ([{"id": n, "display_title": "another day"} for n in range(100)]
                if page == 1 else [{"id": 77, "display_title": "Telegram recovery 2026-10-04 send",
                                   "conclusion": "failure"}])
        return httpx.Response(200, json={"workflow_runs": rows})
    async def run():
        async with httpx.AsyncClient(base_url="https://api.github.com/",
                                    transport=httpx.MockTransport(handler)) as client:
            await validate_history(client, "ohxiyu/xiyunews", "2026-10-04", 456)
    with pytest.raises(RecoveryBlocked):
        asyncio.run(run())
    assert pages == [1, 2]


@pytest.mark.parametrize("kind,status,can_post,valid", [
    ("channel", "administrator", True, True), ("channel", "administrator", False, False),
    ("channel", "member", True, False), ("supergroup", "administrator", True, False),
])
def test_permission_preflight_never_posts(monkeypatch, kind, status, can_post, valid):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHANNEL_ID", "@testchannel")
    calls = []
    def handler(request):
        method = request.url.path.rsplit("/", 1)[-1]
        calls.append(method)
        data = {"getMe": {"id": 11, "is_bot": True}, "getChat": {"type": kind},
                "getChatMember": {"status": status, "can_post_messages": can_post,
                                  "user": {"id": 11}}}[method]
        return httpx.Response(200, json={"ok": True, "result": data})
    publisher = TelegramEditionPublisher(TelegramDeliveryConfig(enabled=True),
                                         transport=httpx.MockTransport(handler))
    if valid:
        asyncio.run(preflight(publisher))
    else:
        with pytest.raises(RecoveryBlocked):
            asyncio.run(preflight(publisher))
    assert "sendMessage" not in calls


@pytest.mark.parametrize("send,mode", [("false", "success"), ("true", "success"),
                                     ("true", "timeout"), ("true", "no_receipt")])
def test_recovery_full_path_with_mock_apis(monkeypatch, tmp_path, send, mode):
    import scripts.recover_telegram_edition as module
    state, report = evidence()
    state_path = tmp_path / "state.json"
    state_path.write_text(state.model_dump_json())
    receipt_path = tmp_path / "receipt.json"
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "never-log-token")
    monkeypatch.setenv("TELEGRAM_CHANNEL_ID", "@never_log_channel")
    calls = []
    def handler(request):
        method = request.url.path.rsplit("/", 1)[-1]
        calls.append(method)
        if request.url.host == "api.github.com":
            assert request.headers["authorization"] == "Bearer test-github"
            data = ({"workflow_runs": []} if method == "runs" else {
                "path": ".github/workflows/daily-summary.yml", "head_branch": "main",
                "status": "completed", "run_attempt": 1})
            return httpx.Response(200, json=data)
        assert "authorization" not in request.headers
        if method == "sendMessage" and mode == "timeout":
            raise httpx.ReadTimeout("secret URL never-log-token @never_log_channel")
        data = {"getMe": {"id": 11, "is_bot": True}, "getChat": {"type": "channel"},
                "getChatMember": {"status": "administrator", "can_post_messages": True,
                                  "user": {"id": 11}},
                "sendMessage": {} if mode == "no_receipt" else {"message_id": 99}}[method]
        return httpx.Response(200, json={"ok": True, "result": data})
    client = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: client(
        **(kwargs | {"transport": httpx.MockTransport(handler)})))
    def download(args, **kwargs):
        (Path(args[-1]) / "run-report.json").write_text(json.dumps(report))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(module.subprocess, "run", download)
    if send == "true" and mode != "success":
        with pytest.raises(RecoveryBlocked, match="no confirmed receipt"):
            asyncio.run(recover(invocation(send), state_path=state_path, receipt_path=receipt_path))
    else:
        asyncio.run(recover(invocation(send), state_path=state_path, receipt_path=receipt_path))
    receipt = json.loads(receipt_path.read_text())
    assert calls.count("sendMessage") == (1 if send == "true" else 0)
    assert receipt["status"] == ("permission_verified" if send == "false" else
                                "sent" if mode == "success" else "send_attempted_outcome_unknown")
    if send == "true" and mode == "success":
        assert receipt["message_id"] == 99
    assert "never-log-token" not in receipt_path.read_text()
    assert "never_log_channel" not in receipt_path.read_text()


def test_workflow_has_no_ai_credentials_or_writes():
    workflow = Path(".github/workflows/telegram-recovery.yml").read_text()
    assert "contents: read" in workflow and "actions: read" in workflow
    assert "github.ref == 'refs/heads/main'" in workflow
    assert "DEEPSEEK" not in workflow and "CLOUDFLARE" not in workflow
    assert "force_publish" not in workflow and "git push" not in workflow
