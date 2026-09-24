"""Language detection and extractive summary/key points. No translation, no inference."""
# ruff: noqa: RUF001, RUF003

import re

# Latin sentences end with punctuation plus a space; CJK sentences need no space.
SPLIT = re.compile(r"(?<=[\u3002\uff01\uff1f])\s*|(?<=[.!?])\s+|\n+")
EXCLUDED = re.compile(
    r"general update|please check|not an endorsement|past performance|not financial advice|"
    r"exercise control|unfamiliar|disclaimer|user agreement|terms of|thank you for your support|"
    r"regional|risk warning|this announcement|for more information|"
    r"一般性公告|地区而异|免责声明|风险提示|感谢您|更多信息|条款与条件|不构成",
    re.I,
)
# A key point states when or what exactly: dates, clock times, UTC, pairs, amounts, leverage.
POINT = re.compile(
    r"\d{4}[-/.\u5e74]\s?\d{1,2}[-/.\u6708]\s?\d{1,2}|\d{1,2}:\d{2}|\bUTC\b|"
    r"\b[A-Z0-9]{2,}\s?/\s?(?:USDT|USDC|USD|KRW|BTC|ETH|TRY|EUR)\b|"
    r"\d+(?:\.\d+)?\s?(?:%|x\b|\u500d)",
    re.I,
)
# Salutations such as "尊敬的欧易用户：" or "Dear users," precede the actual text.
GREETING = re.compile(
    r"^(?:(?:尊敬的|亲爱的)[^\s，,：:]{0,8}用户[：:，,]?|Dear (?:valued )?\w* ?users?,)\s*", re.I
)
LIMITS = {"zh": (160, 120), "ko": (160, 120)}


def language(text: str) -> str:
    if re.search(r"[一-鿿]", text):
        return "zh"
    if re.search(r"[가-힣]", text):
        return "ko"
    return "en"


def clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def summarize(title: str, body: str, lang: str) -> tuple[str, str]:
    """Return (summary, key points) as verbatim sentences from the official text.

    The summary is the lead of the notice; key points are later sentences that state a
    time, pair or amount, so the two never repeat each other.
    """
    summary_limit, point_limit = LIMITS.get(lang, (320, 220))
    shortest = 12 if lang == "en" else 6
    seen = {title.strip()}
    sentences = []
    for raw in SPLIT.split(body or ""):
        sentence = GREETING.sub("", " ".join(raw.split()))
        if len(sentence) > shortest and sentence not in seen and not EXCLUDED.search(sentence):
            seen.add(sentence)
            sentences.append(sentence)
    lead: list[str] = []
    used = 0
    for sentence in sentences:
        if lead and used + len(sentence) > summary_limit:
            break
        lead.append(sentence)
        used += len(sentence)
        if len(lead) == 2:
            break
    points = [s for s in sentences[len(lead) :] if POINT.search(s)][:2]
    return clip(join(lead, lang), summary_limit), clip(join(points, lang), point_limit)


def join(parts: list[str], lang: str) -> str:
    if lang == "en":
        return " ".join(parts)
    # CJK sentences carry their own full stop; bare lines (table rows) get a separator.
    text = ""
    for part in parts:
        if text and not text.endswith(("。", "！", "？", "；", ".", "!", "?")):
            text += "；"
        text += part
    return text
