import json
from types import SimpleNamespace

import pytest

from scripts import configure_edge_deploy_token as setup

TOKEN = "test_token_" + "a" * 40


def test_setup_uses_stdin_and_never_enables_production(monkeypatch):
    calls = []

    def run(args, **kwargs):
        calls.append((args, kwargs))
        if args[0] == "/usr/bin/curl":
            if "user/tokens/verify" in kwargs["input"]:
                result = {"status": "active"}
            else:
                result = {"bindings": [{"name": "GITHUB_REPOSITORY", "type": "plain_text",
                                        "text": setup.REPOSITORY}]}
            return SimpleNamespace(returncode=0, stdout=json.dumps({"success": True, "result": result}))
        output = "CLOUDFLARE_ACCOUNT_ID\nCLOUDFLARE_API_TOKEN\n" if "list" in args else ""
        return SimpleNamespace(returncode=0, stdout=output)

    monkeypatch.setattr(setup.subprocess, "run", run)
    setup.configure(TOKEN)
    assert all(TOKEN not in " ".join(args) for args, _ in calls)
    secret_calls = [(args, kwargs) for args, kwargs in calls if args[1:3] == ["secret", "set"]]
    assert [args[3] for args, _ in secret_calls] == ["CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_API_TOKEN"]
    assert secret_calls[-1][1]["input"] == TOKEN
    assert not any("deploy" in args or "delete" in args or "--method" in args for args, _ in calls)


@pytest.mark.parametrize("token", ["invalid\nheader", 'invalid"config', "", "short"])
def test_rejects_config_injection_before_any_calls(monkeypatch, token):
    monkeypatch.setattr(setup, "command", lambda *a, **k: pytest.fail("must not call"))
    with pytest.raises(setup.SetupError, match="格式"):
        setup.configure(token)


def test_active_production_is_not_mutated(monkeypatch):
    calls = []
    monkeypatch.setattr(setup, "command", lambda args, **k: calls.append(args) or "true")
    with pytest.raises(setup.SetupError, match="已启用"):
        setup.configure(TOKEN)
    assert len(calls) == 1


def test_provider_failure_is_not_printed_or_forwarded(monkeypatch):
    monkeypatch.setattr(setup.subprocess, "run", lambda *a, **k:
                        SimpleNamespace(returncode=1, stdout=TOKEN, stderr=TOKEN))
    with pytest.raises(setup.SetupError) as error:
        setup.cloudflare_get("user/tokens/verify", TOKEN)
    assert TOKEN not in str(error.value)


def test_noninteractive_input_is_refused_before_reading(monkeypatch, capsys):
    monkeypatch.setattr(setup.sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(setup.getpass, "getpass", lambda *a: pytest.fail("must not read"))
    assert setup.main() == 1
    assert "交互终端" in capsys.readouterr().out


def test_missing_path_uses_installed_homebrew_cli(monkeypatch):
    calls = []
    monkeypatch.setattr(setup.shutil, "which", lambda name: None)
    monkeypatch.setattr(setup.subprocess, "run", lambda args, **k:
                        calls.append(args) or SimpleNamespace(returncode=0, stdout=""))
    setup.check_github()
    assert calls[0][0] == "/opt/homebrew/bin/gh"


@pytest.mark.parametrize("provider_error,expected", [
    ("gh auth login " + TOKEN, "未登录"),
    ("HTTP 401 " + TOKEN, "失效"),
    ("HTTP 403 " + TOKEN, "仓库权限"),
    ("HTTP 404 " + TOKEN, "仓库权限"),
    ("connection failed " + TOKEN, "网络"),
    ("rate limit exceeded " + TOKEN, "限额"),
    (TOKEN, "未显示原始输出"),
])
def test_github_diagnostics_are_fixed_and_do_not_expose_output(monkeypatch, provider_error, expected):
    monkeypatch.setattr(setup.subprocess, "run", lambda *a, **k:
                        SimpleNamespace(returncode=1, stdout=TOKEN, stderr=provider_error))
    with pytest.raises(setup.SetupError) as error:
        setup.check_github()
    assert expected in str(error.value)
    assert TOKEN not in str(error.value)


def test_github_failure_is_checked_before_requesting_token(monkeypatch, capsys):
    monkeypatch.setattr(setup.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(setup.getpass, "getpass", lambda *a: pytest.fail("must not read"))
    monkeypatch.setattr(setup.subprocess, "run", lambda *a, **k:
                        SimpleNamespace(returncode=1, stdout="", stderr="gh auth login"))
    assert setup.main() == 1
    assert "未登录" in capsys.readouterr().out


def test_check_only_never_reads_token_or_mutates_secrets(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(setup.getpass, "getpass", lambda *a: pytest.fail("must not read"))
    monkeypatch.setattr(setup.subprocess, "run", lambda args, **k:
                        calls.append(args) or SimpleNamespace(returncode=0, stdout=""))
    assert setup.main(check_only=True) == 0
    assert len(calls) == 1
    assert calls[0][1] == "api"
    assert "预检通过" in capsys.readouterr().out


@pytest.mark.parametrize("exception,expected", [
    (FileNotFoundError, "找不到"), (setup.subprocess.TimeoutExpired, "超时"),
])
def test_github_command_start_errors_are_safe(monkeypatch, exception, expected):
    def fail(*a, **k):
        if exception is setup.subprocess.TimeoutExpired:
            raise exception("gh", 45)
        raise exception(TOKEN)
    monkeypatch.setattr(setup.subprocess, "run", fail)
    with pytest.raises(setup.SetupError) as error:
        setup.check_github()
    assert expected in str(error.value)
    assert TOKEN not in str(error.value)
