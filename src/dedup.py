"""Conservative local candidate fingerprints for daily semantic comparisons.

English source text remains evidence, not an English product. Historical event
membership is read only to preserve daily deduplication; no event is created.
"""
from __future__ import annotations
import re
import unicodedata
import json
from pathlib import Path
from dataclasses import dataclass,field
from typing import Iterable,Sequence,Optional


_STOPWORDS = {
    "about", "after", "against", "amid", "announce", "announced",
    "announcement", "another", "over", "with", "from", "into", "that",
    "this", "their", "there", "these", "those", "will", "would", "could",
    "have", "has", "been", "being", "more", "most", "than", "then", "they",
    "what", "when", "where", "which", "while", "your", "news", "report",
    "reports", "update", "updates", "says", "said", "new", "now",
    "crypto", "cryptocurrency", "blockchain", "market", "markets",
}

_ACRONYM = re.compile(r"[A-Z]{2,}[0-9]*")

_CAPITALIZED = re.compile(r"[A-Z][A-Za-z0-9]{2,}")

_SENTENCE_SPLIT = re.compile(r"[.!?;:\n。！？；]\s*")

_EDGE_PUNCTUATION = "\"'“”‘’()[]{}<>,、·—–-"

_ANCHOR_STOPWORDS = {
    "after", "amid", "and", "another", "back", "but", "could", "days",
    "first", "for", "from", "has", "have", "how", "into", "its", "last",
    "more", "most", "new", "news", "next", "not", "now", "over", "report",
    "reports", "said", "says", "than", "that", "the", "their", "then",
    "these", "this", "those", "top", "update", "updates", "what", "when",
    "where", "which", "while", "who", "why", "will", "with", "would",
    "your",
    "january", "february", "march", "april", "may", "june", "july",
    "august", "september", "october", "november", "december",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept",
    "oct", "nov", "dec",
    "ai", "altcoin", "altcoins", "bitcoin", "blockchain", "billion",
    "btc", "capital", "ceo", "cfo", "chain", "coin", "coins", "company",
    "crypto", "cryptocurrency", "cto", "dao", "data", "defi", "eth",
    "ether", "ethereum", "etf", "etfs", "exchange", "exchanges",
    "exploit", "exploits", "fund", "funds", "hack", "hacked", "hacker",
    "hackers", "inc", "launch", "launches", "llc", "ltd", "market",
    "markets", "million", "model", "models", "network", "nft", "nfts",
    "onchain", "policy", "price", "prices", "protocol", "regulation",
    "regulator", "regulators", "security", "stablecoin", "stablecoins",
    "team", "technology", "token", "tokens", "trader", "traders",
    "trading", "usd", "usdc", "usdt", "users", "wallet", "wallets",
    "web3",
    "eu", "uk", "us", "usa",
}

_CJK = re.compile(r"[一-鿿㐀-䶿]{2,}")

_WORD = re.compile(r"[a-z0-9]+")

def normalize_tag(tag: str) -> str:
    """Lowercase, ASCII-fold, and hyphenate a tag into a stable slug."""
    text = unicodedata.normalize("NFKC", str(tag or "")).strip().lstrip("#")
    text = text.lower()
    text = re.sub(r"[\s_/]+", "-", text)
    text = re.sub(r"[^a-z0-9一-鿿-]", "", text)
    return re.sub(r"-{2,}", "-", text).strip("-")

def _title_tokens(title: str) -> set[str]:
    tokens = {
        word
        for word in _WORD.findall(title.lower())
        if len(word) >= 4 and word not in _STOPWORDS
    }
    for run in _CJK.findall(title):
        tokens.update(run[i : i + 2] for i in range(len(run) - 1))
    return tokens

def _is_title_case(words: Sequence[str]) -> bool:
    """Whether a run of words is a Title Case headline rather than prose.

    "Bybit Wins US Court Order Freezing Assets" capitalizes everything, so
    capitalization there says nothing about which words are names.
    """
    candidates = [word for word in words if len(word) >= 3 and word[:1].isalpha()]
    if len(candidates) < 4:
        return False
    capitalized = sum(1 for word in candidates if word[:1].isupper())
    return capitalized / len(candidates) >= 0.6

def _proper_nouns(text: str, *, skip_sentence_initial: bool) -> set[str]:
    """Capitalized words that plausibly name something.

    English prose capitalizes the first word of every sentence, so those are
    skipped there — that is where "According", "Following" and friends come
    from. Chinese copy has no such rule and routinely opens with the brand
    ("Bybit 遭盗窃"), so the first word counts there.

    Title Case sentences contribute only their acronyms; the names in a
    headline are recovered from the sentence-case summary instead.
    """
    names: set[str] = set()
    for sentence in _SENTENCE_SPLIT.split(text or ""):
        words = [
            word
            for word in (
                raw.strip(_EDGE_PUNCTUATION) for raw in sentence.split()
            )
            if word
        ]
        title_case = _is_title_case(words)
        for index, word in enumerate(words):
            for possessive in ("'s", "’s"):
                if word.endswith(possessive):
                    word = word[: -len(possessive)]
            if _ACRONYM.fullmatch(word):
                names.add(word.lower())
                continue
            if title_case:
                continue
            if skip_sentence_initial and index == 0:
                continue
            if _CAPITALIZED.fullmatch(word):
                names.add(word.lower())
    return names

def _anchor_names(text_en: str, text_zh: str, tags: set[str]) -> set[str]:
    """Named actors in a story: companies, protocols, regulators, people.

    Anchors are what makes "Bybit hacked" and "Bybit sues Lazarus" the same
    thread. Token overlap alone cannot see it — one shared brand name is
    diluted to nothing by a dozen unrelated tokens — so the names are pulled
    out and compared separately.
    """
    anchors = _proper_nouns(text_en, skip_sentence_initial=True)
    anchors |= _proper_nouns(text_zh, skip_sentence_initial=False)
    anchors = {
        word for word in anchors if word not in _ANCHOR_STOPWORDS and len(word) >= 2
    }

    # A tag counts as an anchor only when a headline actually names it, which
    # separates entity tags ("coldcard") from descriptive ones ("market-
    # shakeout") without needing a curated list of either.
    compact_zh = re.sub(r"\s+", "", text_zh or "")
    for slug in tags:
        if _CJK.search(slug):
            # A Chinese-named entity ("美联储") has no Latin form to match, so
            # it is confirmed against the Chinese text directly.
            if slug in compact_zh:
                anchors.add(slug)
            continue
        parts = [part for part in slug.split("-") if len(part) >= 3]
        if parts and all(part in anchors for part in parts):
            anchors.add(slug)
    return anchors

@dataclass
class StoryFingerprint:
    """Comparable token sets for one story."""

    tags: set[str] = field(default_factory=set)
    tokens: set[str] = field(default_factory=set)
    anchors: set[str] = field(default_factory=set)
    #: Anchors named in the headline. A story that is genuinely about an
    #: actor says so in the title; an actor mentioned only in passing in the
    #: body ("... much like Hyperliquid") is not what the story is about.
    lead_anchors: set[str] = field(default_factory=set)

    @property
    def is_empty(self) -> bool:
        return not (self.tags or self.tokens)

def fingerprint(
    *,
    title_zh: str = "",
    title_en: str = "",
    summary_zh: str = "",
    summary_en: str = "",
    tags: Iterable[str] = (),
) -> StoryFingerprint:
    """Build the comparable token sets for one story.

    Summaries are folded in alongside titles because a headline alone is too
    thin to link continuing coverage: day two of an event is usually written
    with an entirely different headline, and only the summary still mentions
    what happened on day one.
    """
    normalized_tags = {
        slug for slug in (normalize_tag(tag) for tag in tags) if slug
    }
    text_en = " ".join(filter(None, (title_en, summary_en)))
    text_zh = " ".join(filter(None, (title_zh, summary_zh)))
    tokens = set(normalized_tags)
    tokens |= _title_tokens(text_en)
    tokens |= _title_tokens(text_zh)
    anchors = _anchor_names(text_en, text_zh, normalized_tags)
    return StoryFingerprint(
        tags=normalized_tags,
        tokens=tokens,
        anchors=anchors,
        lead_anchors=_anchor_names(title_en, title_zh, normalized_tags) & anchors,
    )

def _overlap(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / min(len(left), len(right))

def thread_affinity(
    left: StoryFingerprint,
    right: StoryFingerprint,
    *,
    strong_tag_matches: int = 2,
    strong_threshold: float = 0.30,
    loose_threshold: float = 0.55,
    pair_context: int = 2,
    single_context: int = 6,
    ignore: Optional[set[str]] = None,
) -> float:
    """Score how strongly two stories continue the same event; 0 means no.

    Four independent signals, any one of which links the stories: two shared
    named actors plus a little shared context, one shared named actor plus
    substantial shared context, several shared tags with moderate token
    overlap, or high token overlap on its own. Only actors named in *both*
    headlines count, because an actor mentioned once in a body paragraph is
    not what either story is about. ``ignore`` carries the corpus
    tokens from :func:`common_tokens`, without which "shared context" is
    mostly boilerplate every crypto story has in common.

    The anchor rules exist because the ratio-based rules never fire on real
    continuing coverage: day two is worded differently, so a headline pair
    shares little beyond the name, and the ratio is dominated by the tokens
    that differ. Counting *shared context* — tokens in common that are not
    themselves the shared name — separates "Bybit hacked → Bybit recovers
    funds" (same event, much shared detail) from "Coinbase revenue →
    Coinbase listings" (same company, nothing else in common), which no
    threshold on a ratio can do.

    The returned score only ranks candidates against each other; the
    thresholds, not the score, decide whether there is a link at all.
    """
    if left.is_empty or right.is_empty:
        return 0.0
    # At least one shared actor has to be named in both headlines; once that
    # holds, actors named anywhere in either story count towards the total.
    # Without the headline gate, one passing mention in a body paragraph
    # ("... much like Hyperliquid") links two unrelated stories; with it as
    # the only rule, a second-day headline that drops a name loses evidence
    # the summary still carries.
    shared_anchors = (
        len(left.anchors & right.anchors)
        if left.lead_anchors & right.lead_anchors
        else 0
    )
    shared_tags = len(left.tags & right.tags)
    overlap = _overlap(left.tokens, right.tokens)
    context = (left.tokens & right.tokens) - left.anchors - right.anchors
    if ignore:
        context -= ignore
    context_size = len(context)

    linked = (
        (shared_anchors >= 2 and context_size >= pair_context)
        or (shared_anchors >= 1 and context_size >= single_context)
        or (shared_tags >= strong_tag_matches and overlap >= strong_threshold)
        or overlap >= loose_threshold
    )
    if not linked:
        return 0.0
    return shared_anchors + 0.5 * shared_tags + overlap

def same_thread(
    left: StoryFingerprint,
    right: StoryFingerprint,
    **thresholds: float,
) -> bool:
    """Whether two stories continue the same event.

    Deliberately conservative on every signal: a missed link only costs a
    badge, while a wrong link merges two unrelated stories into one page.
    """
    return thread_affinity(left, right, **thresholds) > 0.0

def legacy_story_assignments(path=Path('docs/_data/events.json')):
    """Read immutable legacy memberships without retaining event generation."""
    if not path.exists():return {},{}
    value=json.loads(path.read_text())
    assignments={};counts={}
    for event in value.get('events',[]):
        event_id=event['event_id'];updates=event.get('updates',[])
        counts[event_id]=sum(bool(u.get('material_change',True)) for u in updates)
        for update in updates:
            current=(event_id,update['update_id'])
            for story_id in update.get('story_ids',[]):
                if story_id in assignments and assignments[story_id]!=current:
                    raise ValueError('legacy story belongs to multiple updates')
                assignments[story_id]=current
    return assignments,counts
