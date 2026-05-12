"""
LLM dual-scoring for news relevance (Stage 2 of the denoise pipeline).

Stage 1 (relevance_filter.py) drops obviously off-topic headlines with
a positive-allowlist of Argentine domestic tokens. The survivors come
here for two model-graded scores, both in [0, 1]:

  * arg_relevance — does this materially concern Argentina's economy?
  * re_relevance — does this concern real estate, mortgage credit, FX,
                    BCRA policy, or Buenos Aires economic activity?

The displayed magnitude becomes raw × arg_relevance × re_relevance, and
items below 0.4 on the product are dropped from the surfaced feed.

Cost controls (matches CLAUDE.md $50/month ceiling):
  * Single Haiku batch per refresh; up to ~30 headlines per call.
  * URL-hash LRU cache so the same headline isn't re-scored.
  * Cost ledger check before every call; fails closed when budget
    is exhausted (caller falls back to Stage-1-only output).
  * Estimated cost: ~$0.001 per refresh, ~$0.10/month at hourly cadence,
    well under the $50 ceiling.

If the ANTHROPIC_API_KEY is not configured the scorer returns the
input list unchanged with a status of 'no_llm' — Stage 1 is the
backstop and the pipeline never blocks on Stage 2.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from anthropic import AsyncAnthropic

from config import settings
from services.cost_ledger import get_cost_ledger


logger = logging.getLogger(__name__)


# Haiku 4.5 pricing (per 1M tokens, as of late 2025): $1 input / $5 output.
# A 30-headline batch is ~1500 input tokens and ~600 output tokens, so
# ~$0.0015 + $0.003 = $0.0045 per batch. Cap projected cost at this for
# the budget check; if the budget can't absorb that we don't call.
_PROJECTED_BATCH_COST_USD: float = 0.005
_HAIKU_MODEL: str = "claude-haiku-4-5-20251001"

# Threshold below which the headline is dropped from the surfaced feed.
_DROP_THRESHOLD: float = 0.4

# Max headlines per Haiku batch. More than this and we either truncate
# or skip — we don't fan out into multiple parallel calls.
_MAX_BATCH: int = 30


_PLACEHOLDER_KEYS = {"", "your_key", "your-api-key", "changeme", "demo", "todo"}


@dataclass(frozen=True)
class RelevanceScore:
    """Per-article dual-relevance scores."""
    arg_relevance: float
    re_relevance: float

    @property
    def product(self) -> float:
        return self.arg_relevance * self.re_relevance


class LLMRelevanceScorer:
    """
    Async Haiku-based dual-relevance scorer with cost gating.

    Public API:
      * is_configured       — True iff API key + budget headroom both OK
      * score_articles(...) — returns (kept_articles, dropped_count,
                                       status_dict)

    The status dict surfaces useful telemetry (n_cached, n_scored,
    n_dropped, projected_cost_usd) so the calling pipeline can log
    or render it.
    """

    def __init__(self) -> None:
        self.api_key = getattr(settings, "anthropic_api_key", None)
        self._client: Optional[AsyncAnthropic] = None
        # URL-hash → RelevanceScore. Trimmed when it grows past 5000
        # entries (LRU-ish via dict insertion order).
        self._cache: Dict[str, RelevanceScore] = {}
        if self.is_api_key_configured:
            try:
                self._client = AsyncAnthropic(api_key=self.api_key)
            except Exception as exc:  # pragma: no cover
                logger.warning("AsyncAnthropic init failed: %s", exc)

    @property
    def is_api_key_configured(self) -> bool:
        if not self.api_key:
            return False
        return self.api_key.strip().lower() not in _PLACEHOLDER_KEYS

    def is_configured(self) -> bool:
        """API key set AND current budget can absorb at least one batch."""
        if not self.is_api_key_configured or self._client is None:
            return False
        return get_cost_ledger().can_spend(_PROJECTED_BATCH_COST_USD)

    @staticmethod
    def _key_for(article: Dict[str, Any]) -> str:
        """URL-hash cache key (falls back to title hash when no URL)."""
        url = (article.get("url") or "").strip()
        if url:
            return hashlib.sha1(url.encode("utf-8")).hexdigest()
        title = (article.get("title") or "").strip()
        return hashlib.sha1(title.encode("utf-8")).hexdigest()

    def _trim_cache(self) -> None:
        if len(self._cache) <= 5000:
            return
        # Drop oldest insertions; dict preserves order in Python 3.7+.
        excess = len(self._cache) - 4000
        for k in list(self._cache.keys())[:excess]:
            self._cache.pop(k, None)

    async def score_articles(
        self,
        articles: Sequence[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], int, Dict[str, Any]]:
        """
        Score and filter articles via Haiku dual-relevance.

        Returns:
            (kept_articles, n_dropped, status_dict)

        Each kept article gains:
            - `arg_relevance`, `re_relevance`, `relevance_product` floats
            - `market_impact_score` rescaled to `raw × product`
              (only when an impact score was present in the input)
        """
        if not articles:
            return [], 0, {"status": "empty"}

        # Stage A: separate cache hits from misses.
        hits: List[Tuple[Dict[str, Any], RelevanceScore]] = []
        misses: List[Dict[str, Any]] = []
        for art in articles:
            key = self._key_for(art)
            cached = self._cache.get(key)
            if cached is not None:
                hits.append((art, cached))
            else:
                misses.append(art)

        status: Dict[str, Any] = {
            "status": "ok",
            "n_total": len(articles),
            "n_cached": len(hits),
            "n_scored_live": 0,
            "n_dropped": 0,
            "projected_cost_usd": 0.0,
            "budget_remaining_usd": get_cost_ledger().headroom_usd(),
        }

        # Stage B: optionally call Haiku for the misses, budget-gated.
        if misses and self.is_configured():
            misses_to_score = misses[:_MAX_BATCH]
            scored = await self._haiku_batch(misses_to_score)
            for art, sc in scored.items():
                self._cache[art] = sc
            status["n_scored_live"] = len(scored)
            status["projected_cost_usd"] = _PROJECTED_BATCH_COST_USD
            # Re-collect after population.
            for art in misses:
                key = self._key_for(art)
                if key in self._cache:
                    hits.append((art, self._cache[key]))
                else:
                    # Couldn't score this one (e.g. dropped from batch
                    # cap). Assign a neutral 1.0/1.0 so we don't punish
                    # an article we never measured.
                    hits.append((art, RelevanceScore(1.0, 1.0)))
        else:
            # No LLM available — pass misses through as neutral. Stage 1
            # is the backstop.
            for art in misses:
                hits.append((art, RelevanceScore(1.0, 1.0)))
            if misses and not self.is_api_key_configured:
                status["status"] = "no_llm"
            elif misses:
                status["status"] = "budget_exhausted"

        # Stage C: apply threshold and rescale magnitudes.
        kept: List[Dict[str, Any]] = []
        dropped = 0
        for art, sc in hits:
            product = sc.product
            if product < _DROP_THRESHOLD:
                dropped += 1
                continue
            enriched = dict(art)
            enriched["arg_relevance"] = round(sc.arg_relevance, 3)
            enriched["re_relevance"] = round(sc.re_relevance, 3)
            enriched["relevance_product"] = round(product, 3)
            raw_impact = enriched.get("market_impact_score")
            if isinstance(raw_impact, (int, float)) and raw_impact > 0:
                enriched["market_impact_score"] = round(float(raw_impact) * product, 4)
            kept.append(enriched)

        status["n_dropped"] = dropped
        self._trim_cache()
        return kept, dropped, status

    async def _haiku_batch(
        self,
        articles: Sequence[Dict[str, Any]],
    ) -> Dict[str, RelevanceScore]:
        """
        Single Haiku call scoring up to `_MAX_BATCH` headlines.

        Returns a dict keyed by article URL-hash. Articles the model
        fails to score (parse error, unexpected response shape) are
        absent from the result — the caller treats them as neutral.
        """
        if self._client is None:
            return {}

        ledger = get_cost_ledger()
        if not ledger.can_spend(_PROJECTED_BATCH_COST_USD):
            logger.info("LLM relevance: monthly budget exhausted; skipping")
            return {}

        prompt = self._build_batch_prompt(articles)
        try:
            response = await asyncio.wait_for(
                self._client.messages.create(
                    model=_HAIKU_MODEL,
                    max_tokens=1024,
                    system=(
                        "You are a news triage classifier for an Argentine "
                        "real-estate intelligence platform. For each headline "
                        "you return two floats in [0,1]: arg_relevance (does "
                        "this materially concern Argentina's economy?) and "
                        "re_relevance (does this concern Argentine real "
                        "estate, mortgage credit, FX policy, BCRA policy, or "
                        "Buenos Aires economic activity?). Reply with a JSON "
                        "array only. Each element has integer 'id' and two "
                        "floats 'arg' and 're'. No prose."
                    ),
                    messages=[{"role": "user", "content": prompt}],
                ),
                timeout=15.0,
            )
        except (asyncio.TimeoutError, Exception) as exc:
            logger.warning("Haiku batch failed: %s", exc)
            return {}

        # Record the projected cost optimistically — we'd rather
        # over-count and stay under budget than under-count and burst.
        ledger.record_spend(_PROJECTED_BATCH_COST_USD)

        text_blocks = [b.text for b in response.content if getattr(b, "type", None) == "text"]
        raw = "".join(text_blocks).strip()
        return self._parse_batch_response(raw, articles)

    @staticmethod
    def _build_batch_prompt(articles: Sequence[Dict[str, Any]]) -> str:
        lines = []
        for i, a in enumerate(articles):
            title = (a.get("title") or "").replace("\n", " ").strip()[:240]
            summary = (a.get("summary") or "").replace("\n", " ").strip()[:240]
            lines.append(f"  {{\"id\": {i}, \"title\": {json.dumps(title)}, \"summary\": {json.dumps(summary)}}}")
        return (
            "Score the following headlines. Return a JSON array, one entry per "
            "headline, with the same 'id'. Floats only.\n\n[\n"
            + ",\n".join(lines)
            + "\n]"
        )

    @staticmethod
    def _parse_batch_response(
        raw: str,
        articles: Sequence[Dict[str, Any]],
    ) -> Dict[str, RelevanceScore]:
        # Haiku usually wraps JSON cleanly; tolerate code-fence wrappers.
        cleaned = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()
        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.warning("Haiku response not valid JSON (%s): %s", exc, raw[:200])
            return {}

        out: Dict[str, RelevanceScore] = {}
        for entry in payload if isinstance(payload, list) else []:
            try:
                idx = int(entry.get("id"))
                arg = float(entry.get("arg", entry.get("arg_relevance", 0)))
                re_ = float(entry.get("re", entry.get("re_relevance", 0)))
            except (TypeError, ValueError):
                continue
            if idx < 0 or idx >= len(articles):
                continue
            key = LLMRelevanceScorer._key_for(articles[idx])
            out[key] = RelevanceScore(
                arg_relevance=max(0.0, min(1.0, arg)),
                re_relevance=max(0.0, min(1.0, re_)),
            )
        return out


# Process-wide singleton.
_default: Optional[LLMRelevanceScorer] = None


def get_llm_relevance_scorer() -> LLMRelevanceScorer:
    global _default
    if _default is None:
        _default = LLMRelevanceScorer()
    return _default
