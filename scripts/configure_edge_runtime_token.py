"""Hidden-input setup for two GitHub runtime secrets on the paused Worker.

No token files, command-line credentials, production activation or test writes.
Run only after approving the exact GitHub token and Cloudflare destination.
"""
import getpass
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import warnings

if __package__:
    from . import configure_edge_deploy_token as base
else:
    import configure_edge_deploy_token as base

SetupError = base.SetupError
ROOT = Path(__file__).resolve().parents[1]
EDGE = ROOT / "ops/daily-dispatcher"
HEALTH_URL = "https://xiyunews.drminutes.workers.dev/health"
SECRET_NAMES = {"ADMIN_GITHUB_TOKEN", "GITHUB_DISPATCH_TOKEN"}


def wrangler(*args, stdin=None):
    env = os.environ.copy()
    env.update(CLOUDFLARE_ACCOUNT_ID=base.ACCOUNT_ID, WRANGLER_WRITE_LOGS="false",
               WRANGLER_LOG_SANITIZE="true", WRANGLER_SEND_METRICS="false",
               CI="true", FORCE_COLOR="0")
    try:
        result = subprocess.run(
            ["/opt/homebrew/bin/node", str(EDGE / "node_modules/wrangler/wrangler-dist/cli.js"),
             *args, "--name", "xiyunews", "--config", str(EDGE / "wrangler.unified.jsonc")],
            cwd=EDGE, env=env, input=stdin, text=True, capture_output=True,
            timeout=120, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise SetupError("Cloudflare 命令不可用或超时；不显示原始输出") from None
    if result.returncode:
        raise SetupError("Cloudflare 操作失败；请核对部分配置，不自动重试")
    return result.stdout


def secret_names():
    try:
        entries = json.loads(wrangler("secret", "list"))
        return {entry["name"] for entry in entries}
    except (ValueError, KeyError, TypeError):
        raise SetupError("Cloudflare Secret 名称回读无效") from None


def preflight():
    base.check_github()
    try:
        health = json.loads(base.command([
            "/usr/bin/curl", "--silent", "--show-error", "--fail-with-body",
            "--proto", "=https", "--max-time", "30", HEALTH_URL,
        ]))
    except (ValueError, SetupError):
        raise SetupError("统一 Worker 健康读取失败；没有请求或保存令牌") from None
    if not isinstance(health, dict) or not (
        health.get("project") == "xiyunews"
        and health.get("repository") == base.REPOSITORY
        and health.get("dispatcher_enabled") is False
        and health.get("realtime_watchdog_enabled") is False
        and re.fullmatch(r"[0-9a-f]{40}", health.get("site_source_commit") or "")
        and re.fullmatch(r"[0-9a-f]{40}", health.get("site_artifact_commit") or "")
    ):
        raise SetupError("目标不是已核验的暂停 xiyunews 项目；没有保存令牌")
    if SECRET_NAMES & secret_names():
        raise SetupError("运行 Secret 已存在；初始配置拒绝覆盖，请先核对")


def validate_token(token):
    if not re.fullmatch(r"github_pat_[A-Za-z0-9_]{30,240}", token):
        raise SetupError("GitHub 令牌格式无效；没有修改 Secrets")
    for path in (f"repos/{base.REPOSITORY}", f"repos/{base.REPOSITORY}/actions/workflows"):
        config = (
            f'url = "https://api.github.com/{path}"\n'
            f'header = "Authorization: Bearer {token}"\n'
            'header = "Accept: application/vnd.github+json"\n'
            'header = "X-GitHub-Api-Version: 2022-11-28"\n'
        )
        try:
            data = json.loads(base.command([
                "/usr/bin/curl", "--silent", "--show-error", "--fail-with-body",
                "--proto", "=https", "--max-time", "30", "--config", "-",
            ], stdin=config))
        except (ValueError, SetupError):
            raise SetupError("GitHub 运行令牌只读校验失败；没有修改 Secrets") from None
        if not isinstance(data, dict) or (
            path.endswith("/actions/workflows") and not isinstance(data.get("workflows"), list)
        ) or (not path.endswith("/actions/workflows") and not (
            data.get("full_name") == base.REPOSITORY and data.get("private") is True
        )):
            raise SetupError("GitHub 仓库或 Actions 身份不匹配；没有修改 Secrets")
    # Write permission was reviewed on GitHub, not probed with real content or dispatch.


def configure(token):
    validate_token(token)
    preflight()  # Recheck pause/existing keys immediately before the encrypted write.
    wrangler("secret", "bulk", stdin=json.dumps({name: token for name in sorted(SECRET_NAMES)}))
    if not SECRET_NAMES.issubset(secret_names()):
        raise SetupError("运行 Secret 名称回读不完整；请核对部分配置，不自动重试")


def main(*, check_only=False):
    print("仅配置暂停 xiyunews Worker 的 ADMIN_GITHUB_TOKEN 和 GITHUB_DISPATCH_TOKEN。")
    print("不改旧项目、主域、Cron、Access、状态或自动发布，不发送消息或测试新闻。")
    try:
        if not check_only and not sys.stdin.isatty():
            raise SetupError("请在交互终端运行；禁止管道及无回显保护的输入")
        preflight()
        if check_only:
            print("运行配置只读预检通过；没有读取或保存令牌。")
            return 0
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            token = getpass.getpass("粘贴刚创建的 GitHub 运行令牌（不回显）：")
        configure(token)
    except (SetupError, EOFError, KeyboardInterrupt, getpass.GetPassWarning) as error:
        print(str(error) if isinstance(error, SetupError) else "输入已取消，没有继续操作")
        return 1
    print("两个运行 Secrets 已保存并回读名称；项目仍暂停，尚未接管生产。")
    return 0


if __name__ == "__main__":
    if sys.argv[1:] not in ([], ["--check-only"]):
        print("仅接受 --check-only；禁止通过参数传入凭据。")
        raise SystemExit(2)
    raise SystemExit(main(check_only=bool(sys.argv[1:])))
