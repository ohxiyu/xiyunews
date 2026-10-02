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
