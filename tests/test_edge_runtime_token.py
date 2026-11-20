import json
from types import SimpleNamespace

import pytest

from scripts import configure_edge_runtime_token as setup

TOKEN = "github_pat_" + "a" * 70
HEALTH = {"project": "xiyunews", "repository": "ohxiyu/xiyunews",
          "dispatcher_enabled": False, "realtime_watchdog_enabled": False,
          "site_source_commit": "a" * 40, "site_artifact_commit": "b" * 40}


def test_runtime_token_only_goes_to_stdin_and_two_reviewed_secrets(monkeypatch):
    calls = []
    monkeypatch.setattr(setup, "preflight", lambda: None)

    def command(args, *, stdin=None):
        calls.append((args, stdin))
        if "/actions/workflows" in stdin:
            return json.dumps({"workflows": []})
        return json.dumps({"full_name": "ohxiyu/xiyunews", "private": True})

    writes = []
    monkeypatch.setattr(setup.base, "command", command)
    monkeypatch.setattr(setup, "wrangler", lambda *args, **kwargs: writes.append((args, kwargs)))
    monkeypatch.setattr(setup, "secret_names", lambda: setup.SECRET_NAMES)
    setup.configure(TOKEN)
    assert all(TOKEN not in " ".join(args) for args, _ in calls)
    assert all("--config" in args and "-" in args for args, _ in calls)
    assert all("Authorization: Bearer " + TOKEN in stdin for _, stdin in calls)
    assert len(writes) == 1 and writes[0][0] == ("secret", "bulk")
    assert json.loads(writes[0][1]["stdin"]) == {name: TOKEN for name in setup.SECRET_NAMES}
    assert not any("--location" in args or "-L" in args for args, _ in calls)


@pytest.mark.parametrize("token", ["", "github_pat_short", TOKEN + "\nheader", TOKEN + '"'])
def test_invalid_token_never_requests_or_writes(monkeypatch, token):
    monkeypatch.setattr(setup.base, "command", lambda *a, **k: pytest.fail("no requests"))
    with pytest.raises(setup.SetupError, match="格式"):
        setup.configure(token)


@pytest.mark.parametrize("change", [
    {"project": "old"}, {"repository": "other/repo"},
    {"dispatcher_enabled": True}, {"realtime_watchdog_enabled": True},
    {"site_source_commit": None}, {"site_artifact_commit": "short"},
])
def test_preflight_rejects_wrong_or_active_worker(monkeypatch, change):
    monkeypatch.setattr(setup.base, "check_github", lambda: None)
    monkeypatch.setattr(setup.base, "command", lambda *a, **k: json.dumps(HEALTH | change))
    monkeypatch.setattr(setup, "secret_names", lambda: pytest.fail("must stop"))
    with pytest.raises(setup.SetupError, match="目标"):
        setup.preflight()


def test_existing_secrets_are_never_overwritten(monkeypatch):
    monkeypatch.setattr(setup.base, "check_github", lambda: None)
    monkeypatch.setattr(setup.base, "command", lambda *a, **k: json.dumps(HEALTH))
    monkeypatch.setattr(setup, "secret_names", lambda: {"ADMIN_GITHUB_TOKEN"})
    with pytest.raises(setup.SetupError, match="拒绝覆盖"):
        setup.preflight()


def test_noninteractive_input_does_not_read_a_token(monkeypatch, capsys):
    monkeypatch.setattr(setup.sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(setup.getpass, "getpass", lambda *a: pytest.fail("must not read"))
    assert setup.main() == 1
    assert "交互终端" in capsys.readouterr().out


def test_check_only_and_preflight_failure_never_read_token(monkeypatch):
    monkeypatch.setattr(setup.getpass, "getpass", lambda *a: pytest.fail("must not read"))
    monkeypatch.setattr(setup, "preflight", lambda: None)
    assert setup.main(check_only=True) == 0
    monkeypatch.setattr(setup.sys.stdin, "isatty", lambda: True)

    def fail():
        raise setup.SetupError("预检失败")
    monkeypatch.setattr(setup, "preflight", fail)
    assert setup.main() == 1


def test_wrangler_uses_fixed_account_and_disables_logs(monkeypatch):
    calls = []
    monkeypatch.setattr(setup.subprocess, "run", lambda args, **kwargs:
                        calls.append((args, kwargs)) or SimpleNamespace(returncode=0, stdout="[]"))
    setup.wrangler("secret", "bulk", stdin=json.dumps({"ADMIN_GITHUB_TOKEN": TOKEN}))
    args, kwargs = calls[0]
    assert TOKEN not in " ".join(args)
    assert args[args.index("--name") + 1] == "xiyunews"
    assert kwargs["env"]["CLOUDFLARE_ACCOUNT_ID"] == setup.base.ACCOUNT_ID
    assert kwargs["env"]["WRANGLER_WRITE_LOGS"] == "false"
    assert kwargs["env"]["WRANGLER_LOG_SANITIZE"] == "true"
    assert kwargs["cwd"] == setup.EDGE


def test_provider_output_is_not_forwarded(monkeypatch):
    monkeypatch.setattr(setup.subprocess, "run", lambda *a, **k:
                        SimpleNamespace(returncode=1, stdout=TOKEN, stderr=TOKEN))
    with pytest.raises(setup.SetupError) as error:
        setup.wrangler("secret", "bulk", stdin=TOKEN)
    assert TOKEN not in str(error.value)


def test_partial_write_is_not_automatically_retried(monkeypatch):
    writes = []
    monkeypatch.setattr(setup, "validate_token", lambda token: None)
    monkeypatch.setattr(setup, "preflight", lambda: None)
    monkeypatch.setattr(setup, "wrangler", lambda *a, **k: writes.append(a))
    monkeypatch.setattr(setup, "secret_names", lambda: {"ADMIN_GITHUB_TOKEN"})
    with pytest.raises(setup.SetupError, match="不自动重试"):
        setup.configure(TOKEN)
    assert len(writes) == 1


@pytest.mark.parametrize("data", [{"full_name": "other/repo", "private": True},
                                 {"full_name": "ohxiyu/xiyunews", "private": False}])
def test_repository_mismatch_rejected_before_mutation(monkeypatch, data):
    monkeypatch.setattr(setup.base, "command", lambda *a, **k: json.dumps(data))
    monkeypatch.setattr(setup, "preflight", lambda: pytest.fail("must not write"))
    with pytest.raises(setup.SetupError, match="不匹配"):
        setup.configure(TOKEN)
