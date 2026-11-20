"""Conservative, operator-invoked recovery of a definitively unsent daily edition.

No collection, AI, rendering, queues or publication writes. A send invocation
consumes its edition's one-shot allowance even if it times out: Telegram does
not provide an idempotency key, so ambiguous outcomes require human inspection.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

import httpx

from src.daily_feed import DailyFeedState
from src.models import TelegramDeliveryConfig
from src.services.telegram_delivery import TelegramDeliveryStatus, TelegramEditionPublisher


class RecoveryBlocked(ValueError):
    """Only fixed, credential-free reasons may escape to the operator."""


def validate_evidence(report: dict, state: DailyFeedState, edition: str) -> None:
    if (state.date != edition or state.timezone != "Asia/Shanghai" or not state.items
            or report.get("date") != edition or report.get("kind") != "daily_publish"):
        raise RecoveryBlocked("Published edition and original report do not match")
    metrics = report.get("metrics", {})
    if (metrics.get("telegram_messages_sent", 0) != 0
            or metrics.get("displayed_today") != len(state.items)
            or state.updated_at != datetime.fromisoformat(report["started_at"])):
        raise RecoveryBlocked("Delivery or edition contents have changed; inspect manually")
    failures = [row for row in report.get("alerts", [])
                if row.get("code") == "telegram_delivery_failed"]
    if len(failures) != 1 or failures[0].get("message") != (
        "Telegram API error 403: Forbidden: bot is not a member of the channel chat"
    ):
        raise RecoveryBlocked("Only a confirmed bot-not-member 403 is recoverable")


def validate_invocation(env: dict[str, str]) -> tuple[str, str, int, bool]:
    edition = env.get("RECOVERY_EDITION", "")
    try:
        valid_date = date.fromisoformat(edition)
        source_id = int(env.get("SOURCE_RUN_ID", ""))
    except ValueError:
        raise RecoveryBlocked("Invalid edition date or source run ID") from None
    if (valid_date.isoformat() != edition or source_id <= 0
            or env.get("GITHUB_REF") != "refs/heads/main"
            or env.get("GITHUB_REPOSITORY") != "ohxiyu/xiyunews"
            or env.get("GITHUB_EVENT_NAME") != "workflow_dispatch"):
        raise RecoveryBlocked("Recovery requires an explicit dispatch on trusted main")
    send = env.get("RECOVERY_SEND") == "true"
    if send and env.get("GITHUB_RUN_ATTEMPT") != "1":
        raise RecoveryBlocked("No rerun after a send attempt; inspect the channel first")
    return env["GITHUB_REPOSITORY"], edition, source_id, send


async def validate_history(client: httpx.AsyncClient, repo: str, edition: str,
                           run_id: int) -> None:
    # Scan all pages, not just the latest 100 runs. Fail closed on API errors.
    page = 1
    while True:
        response = await client.get(
            f"repos/{repo}/actions/workflows/telegram-recovery.yml/runs",
            params={"per_page": 100, "page": page},
        )
        response.raise_for_status()
        runs = response.json()["workflow_runs"]
        if any(row["id"] != run_id and row.get("display_title") == (
            f"Telegram recovery {edition} send"
        ) for row in runs):
            raise RecoveryBlocked("This edition already had a send invocation; inspect manually")
        if len(runs) < 100:
            return
        page += 1


async def preflight(publisher: TelegramEditionPublisher) -> None:
    token, channel = publisher._credentials()
    if not token or not channel:
        raise RecoveryBlocked("Daily Telegram credentials are missing")
    async with httpx.AsyncClient(timeout=30, transport=publisher.transport) as client:
        async def call(method: str, payload: dict) -> dict:
            response = await client.post(f"https://api.telegram.org/bot{token}/{method}", json=payload)
            body = response.json()
            if not response.is_success or body.get("ok") is not True:
                raise RecoveryBlocked(f"Telegram permission check failed at {method}; no message sent")
            return body["result"]

        bot = await call("getMe", {})
        chat = await call("getChat", {"chat_id": channel})
        if bot.get("is_bot") is not True or chat.get("type") != "channel":
            raise RecoveryBlocked("Destination is not the daily channel; no message sent")
        member = await call("getChatMember", {"chat_id": channel, "user_id": bot["id"]})
        if (member.get("status") != "administrator"
                or member.get("can_post_messages") is not True
                or member.get("user", {}).get("id") != bot["id"]):
            raise RecoveryBlocked("Daily bot needs channel administrator posting permission")


async def recover(env: dict[str, str], *, state_path: Path,
                  receipt_path: Path) -> None:
    repo, edition, source_id, send = validate_invocation(env)
    receipt = {"edition": edition, "source_run_id": source_id,
               "recovery_run_id": env["GITHUB_RUN_ID"], "send": send,
               "status": "blocked", "checked_at": datetime.now(timezone.utc).isoformat()}
    receipt_path.parent.mkdir(parents=True, exist_ok=True)

    def save() -> None:
        receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")

    save()
    try:
        async with httpx.AsyncClient(
            base_url="https://api.github.com/", timeout=30,
            headers={"Authorization": f"Bearer {env.get('GH_TOKEN', '')}",
                     "Accept": "application/vnd.github+json"},
        ) as github:
            response = await github.get(f"repos/{repo}/actions/runs/{source_id}")
            response.raise_for_status()
            source = response.json()
            if (source.get("path") != ".github/workflows/daily-summary.yml"
                    or source.get("head_branch") != "main"
                    or source.get("status") != "completed"):
                raise RecoveryBlocked("Source must be a completed trusted daily workflow")
            if send:
                await validate_history(github, repo, edition, int(env["GITHUB_RUN_ID"]))
        with tempfile.TemporaryDirectory(prefix="telegram-source-report-") as folder:
            downloaded = subprocess.run(
                ["gh", "run", "download", str(source_id), "--repo", repo,
                 "--name", f"run-report-{source_id}-{int(source['run_attempt'])}", "--dir", folder],
                env=env, capture_output=True, check=False,
            )
            if downloaded.returncode:
                raise RecoveryBlocked("Cannot read original report artifact; no message sent")
            report = json.loads((Path(folder) / "run-report.json").read_text())
        state = DailyFeedState.model_validate_json(state_path.read_text())
        validate_evidence(report, state, edition)
        config = TelegramDeliveryConfig.model_validate(
            json.loads(Path("data/config.github.json").read_text())["telegram_delivery"]
        )
        if not config.enabled or config.languages != ["zh"]:
            raise RecoveryBlocked("Recovery requires enabled single-language daily delivery")
        publisher = TelegramEditionPublisher(config)
        await preflight(publisher)
        receipt.update(status="permission_verified", items=len(state.items))
        save()
        if send:
            # Persist before POST. No retries, including timeouts or missing receipts.
            receipt["status"] = "send_attempted_outcome_unknown"
            save()
            result = await publisher.send_daily_edition(
                state.items, date=edition,
                total_candidates=report["metrics"].get("edition_candidates", len(state.items)),
                language="zh",
            )
            if result.status != TelegramDeliveryStatus.SUCCESS or result.message_id is None:
                raise RecoveryBlocked("Send has no confirmed receipt; inspect channel before any retry")
            receipt.update(status="sent", message_id=result.message_id,
                           message_length=result.message_length)
            save()
        print(json.dumps(receipt, ensure_ascii=False))
    except Exception as exc:
        # Never print HTTP exception URLs, provider payloads, tokens or chat IDs.
        receipt["reason"] = str(exc) if isinstance(exc, RecoveryBlocked) else type(exc).__name__
        save()
        raise RecoveryBlocked(receipt["reason"]) from None


def main() -> None:
    try:
        asyncio.run(recover(dict(os.environ), state_path=Path("published/_data/bmtnews_state.json"),
                            receipt_path=Path("recovery/telegram-receipt.json")))
    except RecoveryBlocked as exc:
        print(f"Telegram recovery blocked: {exc}")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
