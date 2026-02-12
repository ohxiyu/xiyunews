"""Translate text to Chinese using Google Translate."""

import logging
import re
import urllib.parse

import httpx

logger = logging.getLogger("moltbook.translator")


def translate_to_chinese(text: str) -> str:
    """Translate text to Chinese using Google Translate.

    Args:
        text: Text to translate

    Returns:
        Translated text, or original text if translation fails
    """
    if not text or not text.strip():
        return text

    # Skip if already contains Chinese characters
    if re.search(r'[\u4e00-\u9fff]', text):
        return text

    try:
        # Use Google Translate's internal API
        encoded_text = urllib.parse.quote(text)
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=zh-CN&dt=t&q={encoded_text}"

        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                # Extract translated text from response
                if data and isinstance(data, list) and data[0]:
                    translated = "".join(
                        part[0] for part in data[0] if part and part[0]
                    )
                    if translated:
                        logger.debug(f"Translated: {text[:50]}... -> {translated[:50]}...")
                        return translated

    except Exception as e:
        logger.warning(f"Translation failed: {e}")

    return text
