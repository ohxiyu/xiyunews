"""Bounded setup for two approved group topics; no realtime configuration writes."""
import argparse
import json
import os
from pathlib import Path
import shlex
import urllib.request

NAMES = ["📰 每日信息流", "🧭 事件追踪"]


def credentials(path):
    values = {}
    for line in Path(path).read_text().splitlines():
        key, separator, raw = line.partition("=")
        if separator and key.strip() in {"TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"}:
            parts = shlex.split(raw, comments=True)
            if len(parts) == 1:
                values[key.strip()] = parts[0]
    return values


def save(path, record):
    # Never store the token; persist the claim BEFORE a create request.
    temporary = path.with_suffix(".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(record, stream, ensure_ascii=False)
    os.replace(temporary, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", default="/etc/fomobtc.env")
    parser.add_argument("--create", action="store_true")
    parser.add_argument("--receipt", default="/tmp/xiyunews-group-topics-20261012.json")
    parser.add_argument("--config", action="store_true", help="Emit non-secret binding JSON to a protected caller")
    args = parser.parse_args()
    values = credentials(args.env)
    token, chat_id = values.get("TELEGRAM_BOT_TOKEN"), values.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print(json.dumps({"token_configured": bool(token), "chat_configured": bool(chat_id)}))
        raise ValueError("missing credentials")

    def api(method, payload):
        request = urllib.request.Request("https://api.telegram.org/bot" + token + "/" + method,
            data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=15) as response:
            result = json.load(response)
        if result.get("ok") is not True:
            raise ValueError("Telegram rejected request")
        return result["result"]

    bot = api("getMe", {})
    chat = api("getChat", {"chat_id": chat_id})
    member = api("getChatMember", {"chat_id": chat_id, "user_id": bot["id"]})
    if not args.config:
        print(json.dumps({"bot_matches": bot.get("username") == "xiyunewsbot",
            "group_name_matches": chat.get("title") == "xiyu.news",
            "forum": bool(chat.get("is_forum")), "administrator": member.get("status") in {"administrator", "creator"},
            "can_manage_topics": bool(member.get("can_manage_topics"))}))
    if (bot.get("username") != "xiyunewsbot" or chat.get("title") != "xiyu.news"
            or chat.get("type") != "supergroup" or not chat.get("is_forum")
            or member.get("status") not in {"administrator", "creator"}
            or (member.get("status") != "creator" and not member.get("can_manage_topics"))):
        raise ValueError("target or existing permissions mismatch")
    receipt = Path(args.receipt)
    if not args.create and not args.config:
        print("Verified @xiyunewsbot; xiyu.news forum; existing topic-management permission. No changes.")
        return
    record = json.loads(receipt.read_text()) if receipt.exists() else {
        "chat_id": str(chat["id"]), "bot_id": bot["id"], "topics": {}}
    if record["chat_id"] != str(chat["id"]) or record["bot_id"] != bot["id"]:
        raise ValueError("receipt target mismatch")
    for name in NAMES:
        previous = record["topics"].get(name)
        if previous and previous.get("status") == "created":
            continue
        if previous or not args.create:
            raise ValueError("unresolved topic creation; do not repeat")
        record["topics"][name] = {"status": "unknown"}
        save(receipt, record)
        topic = api("createForumTopic", {"chat_id": chat["id"], "name": name})
        if topic.get("name") != name or not isinstance(topic.get("message_thread_id"), int):
            raise ValueError("invalid topic receipt")
        record["topics"][name] = {"status": "created", "id": topic["message_thread_id"]}
        save(receipt, record)
    if args.config:
        print(json.dumps({"enabled": True, "chat_id": record["chat_id"],
            "feed_topic": record["topics"][NAMES[0]]["id"],
            "events_topic": record["topics"][NAMES[1]]["id"],
            "start_date": "2026-10-12", "expected_bot": "xiyunewsbot"}))
    else:
        print("Created/reused exactly two approved topics. No messages, no realtime configuration changes.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # URL/exception strings can contain a bot token. Emit type only.
        print("Stopped safely:", type(error).__name__)
        raise SystemExit(1)
