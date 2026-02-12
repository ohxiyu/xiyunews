#!/usr/bin/env python3
"""Manual test script to push daily digest."""

import yaml
from bot import TelegramBot
from formatter import format_daily_digest
from scraper import MoltbookClient
from storage import Storage


def main():
    # Load config
    with open("config.yaml") as f:
        config = yaml.safe_load(f)

    moltbook_cfg = config.get("moltbook", {})
    telegram_cfg = config.get("telegram", {})
    scraper_cfg = config.get("scraper", {})

    # Initialize
    scraper = MoltbookClient(
        api_base=moltbook_cfg.get("api_base", "https://www.moltbook.com/api/v1"),
        api_key=moltbook_cfg.get("api_key", ""),
    )

    bot = TelegramBot(
        bot_token=telegram_cfg.get("bot_token"),
        channel_id=telegram_cfg.get("channel_id"),
    )

    # Fetch posts
    posts = scraper.fetch_posts(
        sort=scraper_cfg.get("sort", "hot"),
        limit=scraper_cfg.get("limit", 10),
    )

    print(f"Fetched {len(posts)} posts")

    # Format digest
    digest = format_daily_digest(posts)
    print(f"\nDigest message:\n{digest}\n")

    # Send
    if bot.send_message(digest):
        print("Message sent successfully!")
    else:
        print("Failed to send message")

    scraper.close()
    bot.close()


if __name__ == "__main__":
    main()
