import json
from types import SimpleNamespace

import pytest

from scripts import configure_edge_preserved_settings as setup

ACCESS = {"ADMIN_ACCESS_ISSUER": "https://example.cloudflareaccess.com",
          "ADMIN_ACCESS_AUD": "a" * 64, "ADMIN_ALLOWED_EMAIL": "operator@example.com"}
TELEGRAM = {"TELEGRAM_BOT_TOKEN": "123:" + "a" * 40, "ALERT_CHAT_ID": "123456"}
RECOVERY = "a_fake_recovery_value_never_log"


def patch_sources(monkeypatch):
    monkeypatch.setattr(setup, "paused_preflight", lambda: None)
    monkeypatch.setattr(setup, "access_config", lambda: dict(ACCESS))
    monkeypatch.setattr(setup, "server_settings", lambda **kwargs:
                        {"ok": True} if kwargs else dict(TELEGRAM))
    monkeypatch.setattr(setup.secrets, "token_urlsafe", lambda size: RECOVERY)


def test_preserves_selected_sources_and_stages_new_recovery_only(monkeypatch, capsys):
    patch_sources(monkeypatch)
    writes = []
    monkeypatch.setattr(setup.runtime, "wrangler", lambda *a, **k: writes.append((a, k)))
    monkeypatch.setattr(setup.runtime, "secret_names", lambda: setup.NEW_NAMES | setup.runtime.SECRET_NAMES)
    calls = []

    def command(args, **kwargs):
        calls.append((args, kwargs))
        return setup.RECOVERY_NAME if "list" in args else ""

    monkeypatch.setattr(setup.base, "command", command)
    assert setup.main() == 0
    assert writes[0][0] == ("secret", "bulk")
    assert json.loads(writes[0][1]["stdin"]) == ACCESS | TELEGRAM | {"RECOVERY_CHECK_TOKEN": RECOVERY}
    assert calls[0][0][1:4] == ["secret", "set", setup.RECOVERY_NAME]
    assert calls[0][1]["stdin"] == RECOVERY
    output = capsys.readouterr().out
    assert RECOVERY not in output
    assert all(value not in output for value in ACCESS.values())
    assert all(value not in output for value in TELEGRAM.values())
    assert all(RECOVERY not in " ".join(args) for args, _ in calls)
    assert all("RECOVERY_CHECK_TOKEN" != args[3] for args, _ in calls if "set" in args)
    assert not any("deploy" in args or "variable" in args or "delete" in args for args, _ in calls)


def test_inspection_never_exports_server_token_or_writes(monkeypatch, capsys):
    patch_sources(monkeypatch)
    monkeypatch.setattr(setup.runtime, "wrangler", lambda *a, **k: pytest.fail("no writes"))
    assert setup.main(inspect_only=True) == 0
    output = capsys.readouterr().out
    assert all(value not in output for value in ACCESS.values())
    assert all(value not in output for value in TELEGRAM.values())


def test_partial_write_failure_is_not_retried_and_never_leaks(monkeypatch, capsys):
    patch_sources(monkeypatch)
    calls = []
    monkeypatch.setattr(setup.runtime, "wrangler", lambda *a, **k: calls.append(a))

    def fail(*a, **k):
        raise setup.SetupError("写入失败")
    monkeypatch.setattr(setup.base, "command", fail)
    assert setup.main() == 1
    assert len(calls) == 1
    record = json.loads(capsys.readouterr().out)
    assert record["stage"] == "github_staged_recovery"
    assert record["no_automatic_retry"] is True
    assert RECOVERY not in str(record)


def test_unexpected_provider_exception_is_sanitized(monkeypatch, capsys):
    patch_sources(monkeypatch)

    def fail(*a, **k):
        raise RuntimeError(TELEGRAM["TELEGRAM_BOT_TOKEN"])
    monkeypatch.setattr(setup.runtime, "wrangler", fail)
    assert setup.main() == 1
    assert TELEGRAM["TELEGRAM_BOT_TOKEN"] not in capsys.readouterr().out


@pytest.mark.parametrize("health", [[], {}, {"project": "old"},
    {"project": "xiyunews", "repository": setup.base.REPOSITORY, "dispatcher_enabled": True,
     "realtime_watchdog_enabled": False}])
def test_paused_preflight_rejects_wrong_or_enabled_target(monkeypatch, health):
    monkeypatch.setattr(setup.base, "check_github", lambda: None)
    monkeypatch.setattr(setup.base, "command", lambda *a, **k: json.dumps(health))
    with pytest.raises(setup.SetupError, match="指定暂停"):
        setup.paused_preflight()


@pytest.mark.parametrize("names", [set(), setup.runtime.SECRET_NAMES | {"ALERT_CHAT_ID"}])
def test_missing_or_existing_runtime_keys_are_not_overwritten(monkeypatch, names):
    monkeypatch.setattr(setup.base, "check_github", lambda: None)
    health = {"project": "xiyunews", "repository": setup.base.REPOSITORY,
              "dispatcher_enabled": False, "realtime_watchdog_enabled": False}
    monkeypatch.setattr(setup.base, "command", lambda *a, **k: json.dumps(health))
    monkeypatch.setattr(setup.runtime, "secret_names", lambda: names)
    with pytest.raises(setup.SetupError, match="拒绝覆盖"):
        setup.paused_preflight()


@pytest.mark.parametrize("data", [{}, {"ALERT_CHAT_ID": "-100123", "TELEGRAM_BOT_TOKEN": TELEGRAM["TELEGRAM_BOT_TOKEN"]},
                                 {"ALERT_CHAT_ID": 123, "TELEGRAM_BOT_TOKEN": TELEGRAM["TELEGRAM_BOT_TOKEN"]}])
def test_server_group_or_malformed_settings_are_rejected(monkeypatch, data):
    monkeypatch.setattr(setup, "source_command", lambda *a, **k: json.dumps(data))
    with pytest.raises(setup.SetupError):
        setup.server_settings()


def test_server_export_only_targets_verified_ssh_and_read_only_remote(monkeypatch):
    calls = []
    monkeypatch.setattr(setup, "source_command", lambda args, **k:
                        calls.append(args) or json.dumps(TELEGRAM))
    assert setup.server_settings() == TELEGRAM
    assert calls[0][:len(setup.SSH)] == setup.SSH
    assert "setChat" not in setup.REMOTE and "sendMessage" not in setup.REMOTE
    assert "systemctl','stop" not in setup.REMOTE
    assert "len(private_ids)!=1" in setup.REMOTE


def test_plaintext_pages_download_has_private_directory_and_selected_keys(monkeypatch, tmp_path):
    config = ('name = "bmtnews"\n[vars]\n' +
              "\n".join(f'{key} = "{value}"' for key, value in ACCESS.items()) +
              '\nOTHER = "do not migrate"\n')
    (tmp_path / "wrangler.toml").write_text(config)
    monkeypatch.setattr(setup.tempfile, "mkdtemp", lambda **k: str(tmp_path))
    calls = []
    monkeypatch.setattr(setup, "source_command", lambda args, **k: calls.append((args, k)))
    assert setup.access_config() == ACCESS
    assert (tmp_path / "wrangler.toml").stat().st_mode & 0o077 == 0
    assert calls[0][1]["env"]["CLOUDFLARE_ACCOUNT_ID"] == setup.base.ACCOUNT_ID
    assert calls[0][1]["env"]["WRANGLER_WRITE_LOGS"] == "false"


@pytest.mark.parametrize("value", ["", "two@example.com,three@example.com", "not-an-email"])
def test_access_whitelist_is_not_guessed_or_expanded(monkeypatch, tmp_path, value):
    data = ACCESS | {"ADMIN_ALLOWED_EMAIL": value}
    (tmp_path / "wrangler.toml").write_text('name = "bmtnews"\n[vars]\n' +
        "\n".join(f'{key} = "{entry}"' for key, entry in data.items()))
    monkeypatch.setattr(setup.tempfile, "mkdtemp", lambda **k: str(tmp_path))
    monkeypatch.setattr(setup, "source_command", lambda *a, **k: "")
    with pytest.raises(setup.SetupError):
        setup.access_config()
