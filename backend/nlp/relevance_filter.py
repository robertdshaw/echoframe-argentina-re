"""
Argentina-relevance filter for the news intelligence pipeline.

Stage 1 of the denoise spec: a cheap keyword allowlist that drops obvious
off-topic headlines (foreign celebrity, foreign politics, global sports)
before they reach the more expensive classifier + sentiment + entity
pipeline. Stage 2 (LLM dual-scoring with Haiku) is intentionally not
implemented here — that has its own cost-tracking infrastructure and
ships as a separate change.

The filter uses positive matching: an article must contain at least one
token from the Argentina-domestic vocabulary to pass. This catches the
common failure mode (a Messi business headline, a Brazilian election
piece, a US Fed meeting summary) without trying to enumerate every
possible foreign topic — it's the inverse of a denylist and is more
precise.

A second helper attaches a provenance tag to each surviving signal,
naming the dashboard section it influences. This is the trust-builder
the redesign spec calls out: the user sees not just THAT a headline
matters, but WHERE on the page it shifts the recommendation.
"""

from __future__ import annotations

import re
from typing import Iterable, Optional


# Lowercase tokens that mark an article as plausibly Argentina-relevant.
# Mix of country names, major cities, Argentine institutions, political
# figures who only matter for Argentine policy, and currency indicators.
# Keep this list disciplined — adding "peso" alone would re-admit Mexican
# peso headlines; the qualifier "peso argentino" / "argentino" is safer.
_AR_DOMESTIC_TOKENS: frozenset[str] = frozenset(
    {
        # Country and demonym
        "argentina",
        "argentino",
        "argentinas",
        "argentinos",
        # Major cities, provinces, and the federal capital
        "buenos aires",
        "caba",
        "capital federal",
        "córdoba",
        "cordoba",
        "rosario",
        "mendoza",
        "la plata",
        "mar del plata",
        "neuquén",
        "neuquen",
        "tucumán",
        "tucuman",
        "salta",
        "santa fe",
        "entre ríos",
        "entre rios",
        "patagonia",
        "pampa",
        # Public institutions and acronyms unique to Argentina
        "bcra",
        "indec",
        "afip",
        "anses",
        "anmat",
        "cnv",
        "byma",
        "matba",
        "rofex",
        # Government and major political figures
        "milei",
        "macri",
        "kicillof",
        "massa",
        "caputo",
        "sturzenegger",
        "villarruel",
        # Currency / market shorthand
        "peso argentino",
        "blue dollar",
        "dólar blue",
        "dolar blue",
        "dólar mep",
        "dolar mep",
        "dólar ccl",
        "dolar ccl",
        "cepo cambiario",
        "brecha cambiaria",
        # RE-specific Argentine sources / instruments
        "uva",
        "zonaprop",
        "argenprop",
        "reporte inmobiliario",
        "colegio de escribanos",
    }
)

# A small list of high-volume off-topic tokens we treat as REJECTING
# *even when* one of the allowlist tokens also appears — this catches
# the "Messi visits Argentina" celebrity-tourism class of headline.
# Order matters less than precision; keep these tight.
_HARD_REJECT_TOKENS: frozenset[str] = frozenset(
    {
        "messi",
        "champions league",
        "premier league",
        "copa libertadores",
        "boca juniors",
        "river plate",
        "wimbledon",
        "roland garros",
        "marcha del orgullo",
        "gran hermano",
        "bailando por un sueño",
        "masterchef",
    }
)

# Map each SignalType to the dashboard section it influences. The tag
# format is "§NN <Section Title>" so the frontend can render it as a
# discrete chip alongside the headline. Adjust the section numbers when
# the page restructure ships (Fix #9).
_SIGNAL_PROVENANCE: dict[str, str] = {
    "credit_policy": "§03 Timing · credit availability trigger",
    "exchange_rate": "§05 What could go wrong · FX shock scenario",
    "inflation": "§01 The Call · real-return adjustment",
    "construction": "§04 What you'll earn · cost pressure",
    "regulation": "§01 The Call · regulatory regime",
    "agricultural": "§01 The Call · campos thesis (cross-segment)",
    "investment": "§03 Timing · capital flows trigger",
    "infrastructure": "§02 Where · barrio-level demand",
}


# Compile once. Word-boundary anchored to avoid substring matches like
# "córdoba" tripping on "récord obama" (contrived but illustrates why
# substring containment is the wrong tool).
def _make_token_regex(tokens: Iterable[str]) -> re.Pattern[str]:
    sorted_tokens = sorted({t.lower() for t in tokens}, key=len, reverse=True)
    escaped = [re.escape(t) for t in sorted_tokens]
    return re.compile(r"(?<!\w)(?:" + "|".join(escaped) + r")(?!\w)", re.IGNORECASE)


_AR_REGEX = _make_token_regex(_AR_DOMESTIC_TOKENS)
_REJECT_REGEX = _make_token_regex(_HARD_REJECT_TOKENS)


def is_argentina_relevant(title: str, summary: Optional[str] = None) -> bool:
    """
    Return True if the article looks like Argentine domestic news.

    Decision logic:
      1. If any hard-reject token appears → False (Messi, sports, reality TV).
      2. Else if any Argentina-domestic token appears → True.
      3. Else → False (foreign / generic / off-topic).

    Args:
        title: Article headline (Spanish, mixed-case OK).
        summary: Optional body or summary text; checked together with the title.

    Returns:
        True when the article should proceed to the classifier; False to drop.
    """
    haystack = f"{title or ''} {summary or ''}".strip()
    if not haystack:
        return False
    if _REJECT_REGEX.search(haystack):
        return False
    return bool(_AR_REGEX.search(haystack))


def provenance_tag(signal_type: str) -> Optional[str]:
    """
    Return the "§NN section · driver" provenance tag for a signal type.

    Returns None when the signal type isn't mapped — callers should skip
    the chip rather than render a blank.
    """
    return _SIGNAL_PROVENANCE.get(signal_type)


def filter_argentina_relevant(
    articles: list[dict],
    title_key: str = "title",
    summary_key: str = "summary",
) -> tuple[list[dict], int]:
    """
    Apply the relevance filter to a list of article dicts.

    Args:
        articles: Article dicts as returned by news_seeder / NewsDataClient.
        title_key: Key to read the headline from.
        summary_key: Key to read the article summary from.

    Returns:
        Tuple of (surviving_articles, n_dropped). The dropped count is
        surfaced so the API can report it transparently in the dashboard.
    """
    kept: list[dict] = []
    dropped = 0
    for a in articles:
        if is_argentina_relevant(a.get(title_key, ""), a.get(summary_key, "")):
            kept.append(a)
        else:
            dropped += 1
    return kept, dropped
