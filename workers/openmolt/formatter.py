"""Format Moltbook posts for Telegram messages."""

import html
import re
from typing import Any

from translator import translate_to_chinese


def escape_html(text: str) -> str:
    """Escape HTML special characters for Telegram."""
    if not text:
        return ""
    return html.escape(str(text))


def truncate_content(content: str, max_len: int = 500) -> str:
    """Truncate content to max length, preserving word boundaries."""
    if not content:
        return ""

    content = content.strip()
    if len(content) <= max_len:
        return content

    # Try to break at word boundary
    truncated = content[:max_len]
    last_space = truncated.rfind(" ")
    if last_space > max_len * 0.7:  # Don't cut too early
        truncated = truncated[:last_space]

    return truncated.rstrip() + "..."


def strip_markdown(text: str) -> str:
    """Convert markdown to plain text."""
    if not text:
        return ""

    # Remove images
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    # Remove links but keep text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Remove bold/italic
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    text = re.sub(r"_([^_]+)_", r"\1", text)
    # Remove code blocks
    text = re.sub(r"```[^`]*```", "", text, flags=re.DOTALL)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # Remove headers
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    # Remove blockquotes
    text = re.sub(r"^>\s*", "", text, flags=re.MULTILINE)
    # Normalize whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def format_post(post: dict[str, Any]) -> str:
    """Format a Moltbook post for Telegram.

    简洁格式：标题 + 链接

    Returns:
        Formatted HTML message for Telegram
    """
    # Extract fields
    post_id = post.get("id", "")
    title = post.get("title", "Untitled")
    submolt = post.get("submolt") or post.get("community") or "unknown"

    # Build URL - correct format is /post/{id}
    url = post.get("url")
    if not url and post_id:
        url = f"https://www.moltbook.com/post/{post_id}"

    # Translate title to Chinese
    translated_title = translate_to_chinese(title)

    # Escape title
    safe_title = escape_html(translated_title)

    # Simple format: title + link
    if url:
        return f'🦞 <a href="{url}">{safe_title}</a>'
    else:
        return f"🦞 {safe_title}"


def format_startup_message() -> str:
    """Format startup test message."""
    return (
        " <b>Moltbook Bot </b>\n"
        "\n"
        "Bot is now running and will push hot posts to this channel.\n"
        " Powered by Moltbook API"
    )


def format_error_message(error: str) -> str:
    """Format error notification message."""
    safe_error = escape_html(error)
    return f" <b>Moltbook Bot Error</b>\n\n{safe_error}"


def format_daily_digest(posts: list[dict[str, Any]]) -> str:
    """Format multiple posts into a single daily digest message.

    Args:
        posts: List of post dictionaries

    Returns:
        Formatted HTML message with all posts
    """
    if not posts:
        return ""

    lines = ["🦞 <b>Moltbook 今日热门</b>\n"]

    for i, post in enumerate(posts, 1):
        post_id = post.get("id", "")
        title = post.get("title", "Untitled")

        # Build URL
        url = f"https://www.moltbook.com/post/{post_id}" if post_id else ""

        # Translate title
        translated_title = translate_to_chinese(title)
        safe_title = escape_html(translated_title)

        # Format as numbered list item with link
        if url:
            lines.append(f'{i}. <a href="{url}">{safe_title}</a>')
        else:
            lines.append(f"{i}. {safe_title}")

    return "\n".join(lines)
