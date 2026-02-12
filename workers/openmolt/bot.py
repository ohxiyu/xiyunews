"""Telegram bot for sending messages."""

import logging
import time
from typing import Any

import httpx

logger = logging.getLogger("moltbook.bot")


class TelegramBot:
    def __init__(self, bot_token: str, channel_id: str):
        self.bot_token = bot_token
        self.channel_id = channel_id
        self.api_base = f"https://api.telegram.org/bot{bot_token}"
        self.client = httpx.Client(timeout=30.0)

    def send_message(
        self,
        text: str,
        chat_id: str | None = None,
        parse_mode: str = "HTML",
        disable_web_page_preview: bool = False,
        max_retries: int = 3,
    ) -> bool:
        """Send a message to Telegram.

        Args:
            text: Message text (HTML formatted)
            chat_id: Target chat ID (defaults to configured channel)
            parse_mode: Parse mode (HTML or Markdown)
            disable_web_page_preview: Disable link previews
            max_retries: Maximum retry attempts

        Returns:
            True if message was sent successfully
        """
        if not self.bot_token:
            logger.warning("Bot token not configured")
            return False

        target = chat_id or self.channel_id
        if not target:
            logger.warning("No target chat ID specified")
            return False

        url = f"{self.api_base}/sendMessage"
        payload = {
            "chat_id": target,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview,
        }

        for attempt in range(max_retries):
            try:
                resp = self.client.post(url, json=payload)
                data = resp.json()

                if resp.status_code == 200 and data.get("ok"):
                    logger.debug(f"Message sent to {target}")
                    return True

                elif resp.status_code == 429:
                    # Rate limited
                    retry_after = data.get("parameters", {}).get("retry_after", 30)
                    logger.warning(f"Rate limited - waiting {retry_after}s")
                    time.sleep(retry_after)
                    continue

                elif resp.status_code == 400:
                    # Bad request - likely message format issue
                    error_desc = data.get("description", "Unknown error")
                    logger.error(f"Bad request: {error_desc}")
                    # Try sending without parse_mode
                    if parse_mode and attempt == 0:
                        logger.info("Retrying without parse mode")
                        payload["parse_mode"] = ""
                        continue
                    return False

                else:
                    error_desc = data.get("description", "Unknown error")
                    logger.error(f"Send failed ({resp.status_code}): {error_desc}")
                    return False

            except httpx.TimeoutException:
                logger.error(f"Timeout sending message (attempt {attempt + 1})")
                if attempt < max_retries - 1:
                    time.sleep(5)
                    continue
            except Exception as e:
                logger.error(f"Error sending message: {e}")
                return False

        return False

    def send_posts(
        self,
        formatted_messages: list[str],
        delay: float = 1.5,
    ) -> tuple[int, int]:
        """Send multiple formatted post messages.

        Args:
            formatted_messages: List of formatted HTML messages
            delay: Delay between messages in seconds

        Returns:
            Tuple of (successful_count, failed_count)
        """
        success = 0
        failed = 0

        for i, msg in enumerate(formatted_messages):
            if self.send_message(msg):
                success += 1
            else:
                failed += 1

            # Delay between messages (except after last)
            if i < len(formatted_messages) - 1:
                time.sleep(delay)

        logger.info(f"Sent {success}/{success + failed} messages")
        return success, failed

    def send_startup_message(self) -> bool:
        """Send a test message to verify bot is working."""
        from formatter import format_startup_message

        msg = format_startup_message()
        return self.send_message(msg)

    def get_me(self) -> dict[str, Any] | None:
        """Get bot info to verify token is valid."""
        url = f"{self.api_base}/getMe"
        try:
            resp = self.client.get(url)
            data = resp.json()
            if data.get("ok"):
                bot_info = data.get("result", {})
                logger.info(f"Bot verified: @{bot_info.get('username', 'unknown')}")
                return bot_info
        except Exception as e:
            logger.error(f"Failed to verify bot: {e}")
        return None

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()
