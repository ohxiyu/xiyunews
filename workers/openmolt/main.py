#!/usr/bin/env python3
"""Moltbook Telegram Bot - Main entry point."""

import logging
import signal
import sys
import time
from pathlib import Path
from typing import Any

import yaml

from datetime import datetime, timedelta

from bot import TelegramBot
from formatter import format_daily_digest
from scraper import MoltbookClient
from storage import Storage

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("moltbook")

# Global flag for graceful shutdown
shutdown_requested = False


def load_config(config_path: str = "config.yaml") -> dict[str, Any]:
    """Load configuration from YAML file."""
    path = Path(config_path)
    if not path.exists():
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)

    with open(path) as f:
        config = yaml.safe_load(f) or {}

    return config


def filter_posts(
    posts: list[dict],
    min_score: int = 0,
    exclude_submolts: list[str] | None = None,
    include_submolts: list[str] | None = None,
) -> list[dict]:
    """Filter posts based on score and submolt rules."""
    exclude_submolts = exclude_submolts or []
    include_submolts = include_submolts or []

    filtered = []
    for post in posts:
        # Get score
        score = post.get("score")
        if score is None:
            upvotes = post.get("upvotes", 0) or 0
            downvotes = post.get("downvotes", 0) or 0
            score = upvotes - downvotes

        # Check minimum score
        if score < min_score:
            continue

        # Get submolt
        submolt = post.get("submolt") or post.get("community") or ""
        submolt_lower = str(submolt).lower()

        # Check exclusions
        if any(ex.lower() == submolt_lower for ex in exclude_submolts):
            continue

        # Check inclusions (if specified)
        if include_submolts:
            if not any(inc.lower() == submolt_lower for inc in include_submolts):
                continue

        filtered.append(post)

    return filtered


def run_cycle(
    scraper: MoltbookClient,
    storage: Storage,
    bot: TelegramBot,
    config: dict[str, Any],
) -> int:
    """Run one fetch-filter-push cycle.

    Returns the number of posts pushed.
    """
    scraper_cfg = config.get("scraper", {})
    storage_cfg = config.get("storage", {})

    # Fetch posts (support mixed strategy like "hot+new")
    sort_raw = scraper_cfg.get("sort", "hot")
    limit = scraper_cfg.get("limit", 25)
    sort_methods = [s.strip() for s in sort_raw.split("+")]

    seen_ids: set[str] = set()
    posts: list[dict] = []
    for method in sort_methods:
        batch = scraper.fetch_posts(sort=method, limit=limit)
        for p in batch:
            pid = str(p.get("id", ""))
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                posts.append(p)
        logger.info(f"Fetched {len(batch)} posts via sort={method}")

    if not posts:
        logger.info("No posts fetched")
        return 0

    logger.info(f"Total unique posts after merge: {len(posts)}")

    # Filter posts
    filtered = filter_posts(
        posts,
        min_score=scraper_cfg.get("min_score", 0),
        exclude_submolts=scraper_cfg.get("exclude_submolts", []),
        include_submolts=scraper_cfg.get("include_submolts", []),
    )

    logger.info(f"Filtered to {len(filtered)}/{len(posts)} posts")

    # Deduplicate
    new_posts = []
    for post in filtered:
        post_id = str(post.get("id", ""))
        if not post_id:
            continue
        if not storage.is_sent(post_id):
            new_posts.append(post)

    # Limit to max_push posts
    max_push = scraper_cfg.get("max_push", 8)
    if len(new_posts) > max_push:
        new_posts = new_posts[:max_push]

    logger.info(f"New posts to send: {len(new_posts)}")

    if not new_posts:
        return 0

    # Format all posts into a single digest message
    digest_message = format_daily_digest(new_posts)
    if not digest_message:
        return 0

    # Send single message
    if bot.send_message(digest_message):
        # Mark all posts as sent
        for post in new_posts:
            post_id = str(post.get("id", ""))
            title = post.get("title", "")
            storage.mark_sent(post_id, title)
        success = len(new_posts)
    else:
        success = 0

    # Cleanup old records
    max_history = storage_cfg.get("max_history", 10000)
    storage.cleanup(max_history)

    return success


def signal_handler(signum: int, frame: Any) -> None:
    """Handle shutdown signals."""
    global shutdown_requested
    logger.info(f"Received signal {signum}, shutting down...")
    shutdown_requested = True


def main() -> None:
    """Main entry point."""
    global shutdown_requested

    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Load config
    config_path = "config.yaml"
    config = load_config(config_path)

    logger.info("=" * 50)
    logger.info("  Moltbook Telegram Bot Starting")
    logger.info("=" * 50)

    # Extract configs
    moltbook_cfg = config.get("moltbook", {})
    telegram_cfg = config.get("telegram", {})
    scraper_cfg = config.get("scraper", {})
    storage_cfg = config.get("storage", {})

    # Validate required configs
    bot_token = telegram_cfg.get("bot_token", "")
    if not bot_token or bot_token == "YOUR_BOT_TOKEN":
        logger.error("Telegram bot_token not configured in config.yaml")
        sys.exit(1)

    channel_id = telegram_cfg.get("channel_id", "")
    if not channel_id or channel_id == "@your_channel":
        logger.error("Telegram channel_id not configured in config.yaml")
        sys.exit(1)

    # Initialize components
    storage = Storage(db_path=storage_cfg.get("db_path", "data/sent_posts.db"))
    storage.init_db()

    scraper = MoltbookClient(
        api_base=moltbook_cfg.get("api_base", "https://www.moltbook.com/api/v1"),
        api_key=moltbook_cfg.get("api_key", ""),
        agent_name=moltbook_cfg.get("agent_name", "TelegramBot"),
        agent_description=moltbook_cfg.get("agent_description", "Moltbook hot posts curator"),
        config_path=config_path,
    )

    bot = TelegramBot(bot_token=bot_token, channel_id=channel_id)

    # Verify bot connection
    bot_info = bot.get_me()
    if not bot_info:
        logger.error("Failed to verify Telegram bot connection")
        sys.exit(1)

    # Send startup message
    logger.info("Sending startup test message...")
    if bot.send_startup_message():
        logger.info("Startup message sent successfully")
    else:
        logger.warning("Failed to send startup message")

    # Main loop - run daily at 21:00
    schedule_hour = scraper_cfg.get("schedule_hour", 21)
    schedule_minute = scraper_cfg.get("schedule_minute", 0)

    logger.info(f"Starting main loop (daily at {schedule_hour:02d}:{schedule_minute:02d})")
    logger.info(f"Watching channel: {channel_id}")

    while not shutdown_requested:
        now = datetime.now()
        target_time = now.replace(hour=schedule_hour, minute=schedule_minute, second=0, microsecond=0)

        # If target time already passed today, schedule for tomorrow
        if now >= target_time:
            target_time = target_time + timedelta(days=1)

        wait_seconds = (target_time - now).total_seconds()
        logger.info(f"Next push scheduled at {target_time.strftime('%Y-%m-%d %H:%M:%S')} (in {wait_seconds/3600:.1f} hours)")

        # Wait until target time
        while wait_seconds > 0 and not shutdown_requested:
            sleep_time = min(wait_seconds, 60)  # Check every minute
            time.sleep(sleep_time)
            wait_seconds -= sleep_time

        if shutdown_requested:
            break

        try:
            # Run fetch-filter-push cycle
            pushed = run_cycle(scraper, storage, bot, config)
            logger.info(f"Daily digest complete: pushed {pushed} posts")

        except Exception as e:
            logger.exception(f"Error in main loop: {e}")

    # Cleanup
    logger.info("Shutting down...")
    scraper.close()
    bot.close()
    storage.close()
    logger.info("Goodbye!")


if __name__ == "__main__":
    main()
