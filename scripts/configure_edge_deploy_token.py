"""Operator-run credential setup; no deployment, traffic or cron changes.

Run only after approving the specific token and GitHub secret configuration.
The Cloudflare token is entered without echo, stays in memory, and is passed
to curl/gh on stdin. Never accept credentials as command-line arguments.
"""
import getpass
import json
import re
import subprocess
import sys
import warnings

REPOSITORY = "ohxiyu/xiyunews"
ACCOUNT_ID = "ba29b4955bae94ec7b14d1c2d187554d"
LEGACY_DISPATCHER = "bmtnews-daily-dispatcher"


class SetupError(Exception):
    """Public, fixed error codes only; never forward provider error bodies."""


def command(args, *, stdin=None):
    try:
        result = subprocess.run(
            args, input=stdin, text=True, capture_output=True,
            timeout=45, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise SetupError("命令不可用或超时，未显示原始输出") from None
    if result.returncode:
        raise SetupError("命令失败，未显示原始输出")
    return result.stdout


def cloudflare_get(path, token):
    # A config on stdin keeps Authorization out of argv and disk files. Do not
    # follow redirects: the token must only reach the intended API origin.
    config = (
        f'url = "https://api.cloudflare.com/client/v4/{path}"\n'
        f'header = "Authorization: Bearer {token}"\n'
        'header = "Accept: application/json"\n'
    )
    try:
        data = json.loads(command([
            "/usr/bin/curl", "--silent", "--show-error", "--fail-with-body",
            "--proto", "=https", "--max-time", "30", "--config", "-",
        ], stdin=config))
    except (ValueError, SetupError):
        raise SetupError("Cloudflare 只读校验失败，没有修改 GitHub Secrets") from None
    if not isinstance(data, dict) or data.get("success") is not True:
        raise SetupError("Cloudflare 只读校验失败，没有修改 GitHub Secrets")
    return data.get("result")


def configure(token):
    if not re.fullmatch(r"[A-Za-z0-9_-]{20,256}", token):
        raise SetupError("输入格式无效，没有修改 Secrets")
    # Do not alter live deployment credentials in an active rollout.
    try:
        enabled = command([
            "gh", "api", f"repos/{REPOSITORY}/actions/variables",
            "--jq", '.variables[] | select(.name=="XIYUNEWS_EDGE_ENABLED") | .value',
        ]).strip()
    except SetupError:
        raise SetupError("GitHub 只读校验失败，没有修改 Secrets") from None
    if enabled == "true":
        raise SetupError("统一自动发布已启用；请由发布负责人另行安排凭据轮换")
    verified = cloudflare_get("user/tokens/verify", token)
    if not isinstance(verified, dict) or verified.get("status") != "active":
        raise SetupError("令牌未激活，没有修改 Secrets")
    settings = cloudflare_get(
        f"accounts/{ACCOUNT_ID}/workers/scripts/{LEGACY_DISPATCHER}/settings", token,
    )
    if not isinstance(settings, dict) or not isinstance(settings.get("bindings"), list):
        raise SetupError("生产账户读取校验失败，没有修改 Secrets")
    bindings = settings["bindings"]
    if not any(b.get("name") == "GITHUB_REPOSITORY" and
               b.get("type") == "plain_text" and b.get("text") == REPOSITORY
               for b in bindings if isinstance(b, dict)):
        raise SetupError("生产项目身份不匹配，没有修改 Secrets")
    # The reviewed browser summary establishes edit scope; read-only checks do
    # not claim to prove write permission by uploading a test deployment.
    for name, value in (("CLOUDFLARE_ACCOUNT_ID", ACCOUNT_ID),
                        ("CLOUDFLARE_API_TOKEN", token)):
        try:
            command(["gh", "secret", "set", name, "--repo", REPOSITORY], stdin=value)
        except SetupError:
            raise SetupError(f"配置 {name} 失败；请核对部分配置，不自动删除或重试") from None
    names = command(["gh", "secret", "list", "--repo", REPOSITORY,
                     "--json", "name", "--jq", '.[].name']).splitlines()
    if not {"CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_API_TOKEN"}.issubset(names):
        raise SetupError("名称回读不完整；请核对部分配置，不自动删除")


def main():
    print(f"仅校验已批准令牌并配置 {REPOSITORY} 的两个部署 Secrets。")
    print("不会启用自动部署、修改运行 Secrets、主域、Cron、状态或删除旧项目。")
    try:
        if not sys.stdin.isatty():
            raise SetupError("请在交互终端运行，禁止管道或无回显保护的输入")
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            token = getpass.getpass("粘贴已批准的 Cloudflare API Token（不回显）：")
        configure(token)
    except (SetupError, EOFError, KeyboardInterrupt, getpass.GetPassWarning) as error:
        print(str(error) if isinstance(error, SetupError) else "输入已取消，没有继续操作")
        return 1
    print("两个部署 Secrets 已配置并回读名称；统一项目仍暂停，运行凭据与生产验收尚待完成。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
