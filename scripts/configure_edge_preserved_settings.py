"""Preserve existing Access/Telegram settings on the paused unified Worker.

Uses official Wrangler configuration download and the original server sources,
never Cloudflare secret extraction or model-visible credential output. Does not
activate production. Recovery uses a new, separately staged shared key.
"""
import base64
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import subprocess
import sys
import tempfile
import tomllib

if __package__:
    from . import configure_edge_runtime_token as runtime
else:
    import configure_edge_runtime_token as runtime

base = runtime.base
SetupError = base.SetupError
ACCESS_NAMES = {"ADMIN_ACCESS_ISSUER", "ADMIN_ACCESS_AUD", "ADMIN_ALLOWED_EMAIL"}
NEW_NAMES = ACCESS_NAMES | {"TELEGRAM_BOT_TOKEN", "ALERT_CHAT_ID", "RECOVERY_CHECK_TOKEN"}
RECOVERY_NAME = "XIYUNEWS_RECOVERY_CHECK_TOKEN"
SSH = ["/usr/bin/ssh", "-o", "BatchMode=yes", "-F",
       "/Users/minutesdr/.ssh/xiyunews_tokyo_config", "xiyunews-tokyo"]
REMOTE = r'''
import json, os, re, subprocess, sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode
class Stop(Exception): pass
def run(*args):
    r = subprocess.run(args, capture_output=True, timeout=30)
    if r.returncode: raise Stop()
    return r.stdout.decode().strip()
def cfg(path):
    s = path.stat()
    if s.st_uid != 0 or s.st_mode & 0o077: raise Stop()
    pairs = {}
    for line in path.read_text().splitlines():
        if line.strip() and not line.lstrip().startswith('#') and '=' in line:
            k,v = line.split('=',1)
            k = k.strip()
            if k in pairs: raise Stop()
            pairs[k] = v.strip().strip('"').strip("'")
    return pairs
def api(token, method, **params):
    q = Request('https://api.telegram.org/bot'+token+'/'+method,
                data=urlencode(params).encode(), method='POST')
    with urlopen(q, timeout=20) as response: value = json.load(response)
    if not value.get('ok'): raise Stop()
    return value['result']
try:
    if run('systemctl','is-active','fomobtc') != 'active': raise Stop()
    c = cfg(Path('/etc/fomobtc.env'))
    pid = run('systemctl','show','fomobtc','-p','MainPID','--value')
    if not pid.isdigit() or int(pid)==0: raise Stop()
    p = dict(x.split('=',1) for x in Path('/proc/'+pid+'/environ').read_bytes().decode().split('\0') if '=' in x)
    required = {'SOURCE_COMMIT':'d6a9d3f29ef93c138842342c973b3049fb7bc252',
                'TELEGRAM_ENABLED':'true','TELEGRAM_TOPIC_MARKET':'3',
                'TELEGRAM_TOPIC_ANNOUNCEMENT':'5','TELEGRAM_TOPIC_FLOW':'7'}
    if any(c.get(k)!=v or p.get(k)!=v for k,v in required.items()): raise Stop()
    token = c.get('TELEGRAM_BOT_TOKEN','')
    if not re.fullmatch(r'[0-9]+:[A-Za-z0-9_-]{30,}',token) or p.get('TELEGRAM_BOT_TOKEN')!=token: raise Stop()
    private_ids = set()
    for path in sorted(Path('/etc').glob('fomobtc.env.bak-*')):
        value = cfg(path).get('TELEGRAM_CHAT_ID','')
        if re.fullmatch(r'[1-9][0-9]*',value): private_ids.add(value)
    if len(private_ids)!=1: raise Stop()
    private_id = private_ids.pop()
    if api(token,'getMe').get('username','').lower() != 'xiyunewsbot': raise Stop()
    chat = api(token,'getChat',chat_id=private_id)
    if chat.get('type')!='private' or str(chat.get('id'))!=private_id: raise Stop()
    if sys.argv[1] == 'inspect':
        print(json.dumps({'ok':True,'private_backup_unique':True,'private_chat_readable':True,
                          'bot':'xiyunewsbot','service_preserved':True}))
    elif sys.argv[1] == 'inject':
        print(json.dumps({'TELEGRAM_BOT_TOKEN':token,'ALERT_CHAT_ID':private_id}))
    else: raise Stop()
except Exception:
    print('server_source_check_failed', file=sys.stderr)
    sys.exit(1)
'''


def source_command(args, *, cwd=None, env=None):
    try:
        result = subprocess.run(args, cwd=cwd, env=env, text=True,
                                capture_output=True, timeout=120, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise SetupError("原配置读取不可用或超时；没有显示秘密值") from None
    if result.returncode:
        raise SetupError("原配置安全核验失败；没有显示原始输出")
    return result.stdout


def access_config():
    # Only plaintext Pages vars are downloaded by official Wrangler. No secrets
    # are exported. The CLI-created file stays in a private temporary directory.
    directory = tempfile.mkdtemp(prefix="xiyunews-pages-settings-")
    env = os.environ.copy()
    env.update(CLOUDFLARE_ACCOUNT_ID=base.ACCOUNT_ID, WRANGLER_WRITE_LOGS="false",
               WRANGLER_LOG_SANITIZE="true", WRANGLER_SEND_METRICS="false", CI="true")
    source_command([
        "/opt/homebrew/bin/node", str(runtime.EDGE / "node_modules/wrangler/wrangler-dist/cli.js"),
        "pages", "download", "config", "bmtnews",
    ], cwd=directory, env=env)
    path = Path(directory) / "wrangler.toml"
    os.chmod(path, 0o600)
    try:
        data = tomllib.loads(path.read_text())
        if data.get("name") != "bmtnews":
            raise SetupError("Pages 项目身份不匹配")
        values = data.get("env", {}).get("production", {}).get("vars", data.get("vars", {}))
        selected = {name: values.get(name) for name in ACCESS_NAMES}
        if not all(isinstance(value, str) and value for value in selected.values()):
            raise SetupError("原 Pages 的 Access 配置不完整，不能推断或扩大白名单")
        if not re.fullmatch(r"https://[a-z0-9-]+\.cloudflareaccess\.com", selected["ADMIN_ACCESS_ISSUER"]):
            raise SetupError("原 Access issuer 无效")
        if not re.fullmatch(r"[0-9a-f]{64}", selected["ADMIN_ACCESS_AUD"]):
            raise SetupError("原 Access AUD 无效")
        if not re.fullmatch(r"[^\s@,;]+@[^\s@,;]+", selected["ADMIN_ALLOWED_EMAIL"]):
            raise SetupError("原单账号白名单无效")
        return selected
    except (ValueError, TypeError, OSError):
        raise SetupError("原 Pages 配置解析失败；未输出原值") from None


def server_settings(*, inspect_only=False):
    encoded = base64.b64encode(REMOTE.encode()).decode()
    remote = shlex.join(["sudo", "-n", "python3", "-c",
                        "import base64;exec(base64.b64decode(" + repr(encoded) + "))",
                        "inspect" if inspect_only else "inject"])
    try:
        values = json.loads(source_command(SSH + [remote]))
    except (ValueError, TypeError):
        raise SetupError("服务器源配置核验失败；没有显示原始输出") from None
    if inspect_only:
        if values.get("ok") is not True:
            raise SetupError("服务器源配置核验失败")
        return values
    if not isinstance(values, dict) or set(values) != {"TELEGRAM_BOT_TOKEN", "ALERT_CHAT_ID"}:
        raise SetupError("服务器返回的配置字段不匹配")
    if not all(isinstance(value, str) for value in values.values()) or not re.fullmatch(r"[0-9]+:[A-Za-z0-9_-]{30,}", values["TELEGRAM_BOT_TOKEN"]) or not re.fullmatch(r"[1-9][0-9]*", values["ALERT_CHAT_ID"]):
        raise SetupError("服务器返回配置格式无效")
    return values


def paused_preflight():
    base.check_github()
    try:
        health = json.loads(base.command([
            "/usr/bin/curl", "--silent", "--show-error", "--fail-with-body",
            "--proto", "=https", "--max-time", "30", runtime.HEALTH_URL,
        ]))
    except (ValueError, SetupError):
        raise SetupError("暂停项目预检失败") from None
    if not isinstance(health, dict) or not (health.get("project") == "xiyunews" and health.get("repository") == base.REPOSITORY
            and health.get("dispatcher_enabled") is False and health.get("realtime_watchdog_enabled") is False):
        raise SetupError("目标不是指定暂停项目")
    names = runtime.secret_names()
    if not runtime.SECRET_NAMES.issubset(names) or NEW_NAMES & names:
        raise SetupError("运行配置缺失或已存在；拒绝覆盖初始配置")
    names = base.command(["gh", "secret", "list", "--repo", base.REPOSITORY,
                          "--json", "name", "--jq", ".[].name"]).splitlines()
    if RECOVERY_NAME in names:
        raise SetupError("暂存恢复 Secret 已存在；先核对部分配置，拒绝重新轮换")


def main(*, inspect_only=False):
    stage = "preflight"
    try:
        paused_preflight()
        access = access_config()
        facts = server_settings(inspect_only=True)
        if inspect_only:
            print(json.dumps({"ok": True, "access_keys": sorted(access), "single_account_preserved": True,
                              "server": facts, "runtime_secrets_unchanged": True}))
            return 0
        telegram = server_settings()
        paused_preflight()
        recovery = secrets.token_urlsafe(48)
        stage = "cloudflare_secrets"
        runtime.wrangler("secret", "bulk", stdin=json.dumps(access | telegram | {"RECOVERY_CHECK_TOKEN": recovery}))
        stage = "github_staged_recovery"
        base.command(["gh", "secret", "set", RECOVERY_NAME, "--repo", base.REPOSITORY], stdin=recovery)
        stage = "readback"
        if not (NEW_NAMES | runtime.SECRET_NAMES).issubset(runtime.secret_names()):
            raise SetupError("运行 Secret 名称回读不完整")
        names = base.command(["gh", "secret", "list", "--repo", base.REPOSITORY,
                              "--json", "name", "--jq", ".[].name"]).splitlines()
        if RECOVERY_NAME not in names:
            raise SetupError("暂存恢复 Secret 名称回读不完整")
    except SetupError as error:
        print(json.dumps({"ok": False, "stage": stage, "reason": str(error), "no_automatic_retry": True}))
        return 1
    except Exception:
        print(json.dumps({"ok": False, "stage": stage, "reason": "controlled_failure",
                          "no_automatic_retry": True}))
        return 1
    print(json.dumps({"ok": True, "runtime_secret_names": sorted(NEW_NAMES | runtime.SECRET_NAMES),
                      "github_staged_secret": RECOVERY_NAME, "production_still_paused": True,
                      "old_recovery_secret_unchanged": True, "messages_sent": False}))
    return 0


if __name__ == "__main__":
    if sys.argv[1:] not in ([], ["--inspect-only"]):
        print("仅接受 --inspect-only；不接受凭据参数。")
        raise SystemExit(2)
    raise SystemExit(main(inspect_only=bool(sys.argv[1:])))
