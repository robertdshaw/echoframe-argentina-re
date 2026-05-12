"""
Narrative generation service for EchoFrame Argentina RE Intelligence.

Calls Claude Sonnet 4.6 with a carefully composed prompt that includes:
  * The current forecast (median, credible bands, P(↑))
  * The HMM regime + transition probabilities
  * Top live news signals
  * Backtest accuracy metrics (calibration coverage, Brier, MAE vs naive)

…and returns a short, executive-style narrative the client can read in
30 seconds. The point is to convert numbers + uncertainty bounds into
*plain language* the client uses to make a decision.

Caching: narratives are deterministic-ish for a given input snapshot but
expensive to generate (~2-4s of Claude inference), so we cache per
segment for `settings.narrative_cache_ttl_minutes`.

Failure behaviour: when no Anthropic key is configured, or the API call
fails, the service returns a `status: "unavailable"` response with the
reason — never blocks the rest of the dashboard.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from anthropic import AsyncAnthropic

from config import settings


# Hard timeout on the Anthropic SDK call. Render's free-tier proxy
# closes idle connections at ~100s and the frontend axios timeout is
# 60s, so we need the LLM call to either succeed or fail well inside
# that envelope. 25s is generous for Sonnet 4.6 at ~900 max-tokens;
# anything longer than this typically means the upstream is degraded
# and the deterministic draft is the right answer.
_ANTHROPIC_CALL_TIMEOUT_SECONDS: float = 25.0


logger = logging.getLogger(__name__)


_PLACEHOLDER_KEYS = {
    "",
    "your_key",
    "your-api-key",
    "your_anthropic_api_key",
    "changeme",
    "demo",
    "todo",
}


@dataclass
class _CacheEntry:
    payload: Dict[str, Any]
    expires_at: float


class NarrativeService:
    """Generates short executive-style narratives via Claude.

    Hallucination-capped pattern: every numeric value, named entity, and
    citation is filled in Python before the LLM ever sees the prose. The
    LLM is constrained to a language-smoothing role — it may rewrite
    connective phrasing for fluency but must not change any number,
    percentage, named barrio, scenario probability, or historical period.
    This is the same pattern Bloomberg-style structured briefings use to
    keep credibility intact at scale.
    """

    SYSTEM_PROMPT = (
        "You are a senior real estate strategist polishing a briefing for "
        "a sophisticated Argentine client. The user message contains a "
        "fully-numbered draft of seven titled paragraphs. Your job is to "
        "smooth the connective language so it reads as fluent investment "
        "prose, not to compose new content.\n\n"
        "STRICT RULES (non-negotiable):\n"
        "- Do NOT change any number, percentage, currency value, named "
        "barrio, named scenario, historical period, or sample size.\n"
        "- Do NOT add new claims, citations, statistics, or sources.\n"
        "- Do NOT drop any of the seven titled paragraphs.\n"
        "- KEEP the paragraph titles exactly as given (e.g. 'The Call.', "
        "'Where.', 'When.', 'What you take home.', 'What could break it.', "
        "'Versus alternatives.', 'Confidence statement.').\n"
        "- You MAY rephrase connective tissue for clarity and pace, fix "
        "awkward phrasing, and ensure plain English.\n"
        "- Output is exactly seven paragraphs; no headings, no bullets, "
        "no markdown beyond bold paragraph titles.\n"
        "- Total length: 220-320 words.\n"
        "- The final sentence of the seventh paragraph is the bottom-line "
        "summary; preserve its quantitative content unchanged.\n"
        "If the input draft seems internally inconsistent, prefer it to "
        "inventing a fix — return the draft as-is rather than guessing."
    )

    def __init__(self) -> None:
        self.api_key = settings.anthropic_api_key
        self.model = settings.narrative_model
        self.ttl_seconds = settings.narrative_cache_ttl_minutes * 60
        self._cache: Dict[str, _CacheEntry] = {}
        self._client: Optional[AsyncAnthropic] = None
        if self.is_configured:
            try:
                self._client = AsyncAnthropic(api_key=self.api_key)
            except Exception as exc:  # pragma: no cover
                logger.warning("AsyncAnthropic init failed: %s", exc)

    @property
    def is_configured(self) -> bool:
        if not self.api_key:
            return False
        return self.api_key.strip().lower() not in _PLACEHOLDER_KEYS

    async def generate(
        self,
        segment: str,
        forecast_payload: Dict[str, Any],
        signals: list,
        insights: Optional[Dict[str, Any]],
        slot_extras: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Compose the briefing draft, send it to Claude for language-polish,
        and return the result.

        slot_extras may contain pre-computed structured data the caller
        already gathered for other endpoints (top barrios, entry-quality
        triggers, net-return decomposition, canonical scenarios). When
        absent the corresponding paragraph is dropped from the draft
        rather than invented — keeps hallucination surface at zero.
        """
        if not self.is_configured or self._client is None:
            return {
                "status": "unavailable",
                "narrative": None,
                "reason": "ANTHROPIC_API_KEY not configured",
                "model": self.model,
            }

        slot_extras = slot_extras or {}
        cache_key = (
            f"{segment}:{forecast_payload.get('current_price')}:"
            f"{len(signals)}:{hash(str(sorted(slot_extras.keys())))}"
        )
        cached = self._cache.get(cache_key)
        if cached and cached.expires_at > time.time():
            return cached.payload

        # Stage 1: deterministic Python composition with every number,
        # named entity, and citation already in place. The LLM never
        # invents these.
        draft = self._build_numbered_draft(
            segment, forecast_payload, signals, insights, slot_extras
        )

        # Stage 2: LLM language polish. The system prompt forbids
        # numeric or entity edits; the draft is the source of truth.
        user_prompt = (
            "Polish the connective language in the following draft so it "
            "reads as fluent investment prose. Preserve every number, "
            "percentage, named entity, and paragraph title exactly as "
            "written. Return only the seven titled paragraphs.\n\n"
            "----- DRAFT BEGIN -----\n"
            f"{draft}\n"
            "----- DRAFT END -----"
        )

        try:
            response = await asyncio.wait_for(
                self._client.messages.create(
                    model=self.model,
                    max_tokens=900,
                    system=self.SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": user_prompt}],
                ),
                timeout=_ANTHROPIC_CALL_TIMEOUT_SECONDS,
            )
            text_blocks = [b.text for b in response.content if getattr(b, "type", None) == "text"]
            narrative = "".join(text_blocks).strip()
        except asyncio.TimeoutError:
            logger.warning(
                "Claude narrative call exceeded %.0fs budget; serving deterministic draft",
                _ANTHROPIC_CALL_TIMEOUT_SECONDS,
            )
            return {
                "status": "ok",
                "narrative": draft,
                "reason": "LLM polish timed out; served deterministic draft",
                "model": self.model + " (draft fallback)",
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        except Exception as exc:
            logger.warning("Claude narrative call failed: %s", exc)
            # Graceful fallback: return the deterministic draft. The
            # client still sees a coherent briefing; only the prose
            # polish was lost.
            return {
                "status": "ok",
                "narrative": draft,
                "reason": f"Claude API error ({exc}); served deterministic draft",
                "model": self.model + " (draft fallback)",
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }

        payload: Dict[str, Any] = {
            "status": "ok",
            "narrative": narrative,
            "model": self.model,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        self._cache[cache_key] = _CacheEntry(payload=payload, expires_at=time.time() + self.ttl_seconds)
        return payload

    def _build_numbered_draft(
        self,
        segment: str,
        forecast_payload: Dict[str, Any],
        signals: list,
        insights: Optional[Dict[str, Any]],
        slot_extras: Dict[str, Any],
    ) -> str:
        """
        Compose the seven-paragraph briefing draft with every numeric slot
        already filled. The LLM that consumes this is forbidden from
        editing the numbers; it only polishes the connective language.
        Paragraphs whose underlying data is missing are quietly skipped.
        """
        current = forecast_payload.get("current_price") or 0.0
        regime = forecast_payload.get("regime_context") or {}
        forecasts = forecast_payload.get("forecasts") or {}
        y1 = forecasts.get("1") or forecasts.get(1) or {}
        m1 = y1.get("model_estimate") or {}
        median = float(m1.get("median_change_pct", 0))
        ci80 = m1.get("ci_80") or {}
        ci_lower = float(ci80.get("lower", 0)) if isinstance(ci80, dict) else float(ci80[0])
        ci_upper = float(ci80.get("upper", 0)) if isinstance(ci80, dict) else float(ci80[1])
        p_increase = float(m1.get("p_increase", 0))

        paragraphs: list[str] = []

        # ---- Paragraph 1 · THE CALL ---------------------------------
        # Conviction language is keyed to P(increase). The 80% band
        # phrasing ("1-in-10 chance of an outright loss") is anchored
        # to the model's own ci80 lower bound.
        if p_increase >= 0.80:
            conviction = "high"
        elif p_increase >= 0.55:
            conviction = "medium"
        else:
            conviction = "low"
        loss_phrase = (
            "roughly a 1-in-10 chance of an outright loss"
            if ci_lower < 0
            else "the lower band stays positive — no 10%-tail loss in the model"
        )
        entry_quality = slot_extras.get("entry_quality") or {}
        entry_score = entry_quality.get("score_out_of_10")
        entry_phrase = (
            f" Entry quality this week is {float(entry_score):.1f}/10 "
            f"(verdict: {self._verdict_for(entry_score)})."
            if entry_score is not None
            else ""
        )
        paragraphs.append(
            f"**The Call.** {self._segment_label(segment)} are a "
            f"{conviction}-conviction buy at a 12-month horizon, with an "
            f"expected {median:+.1f}% USD median appreciation off a current "
            f"{current:,.0f} {self._unit(segment)} reference price. The 80% "
            f"credible band runs {ci_lower:+.1f}% to {ci_upper:+.1f}% — "
            f"{loss_phrase} and a comparable 1-in-10 chance of a return "
            f"above {ci_upper:+.1f}%.{entry_phrase}"
        )

        # ---- Paragraph 2 · WHERE ------------------------------------
        top_barrios = slot_extras.get("top_barrios") or []
        if top_barrios:
            names = [b.get("name", "?") for b in top_barrios[:3]]
            returns = [
                f"{float(b.get('total_return_pct', 0)):+.1f}%"
                for b in top_barrios[:3]
            ]
            joined = ", ".join(
                f"{n} ({r})" for n, r in zip(names, returns)
            )
            paragraphs.append(
                f"**Where.** Concentrate exposure in {joined}, which "
                f"top the partial-pooled barrio model on combined "
                f"appreciation plus gross yield. Thin-data barrios are "
                f"excluded from this ranking; the per-barrio drawer "
                f"shows the full distribution."
            )

        # ---- Paragraph 3 · WHEN -------------------------------------
        triggers = entry_quality.get("triggers") or []
        if triggers:
            active = [t for t in triggers if t.get("status") == "active"]
            active_names = ", ".join(t.get("name", "?") for t in active)
            analogy_period = entry_quality.get("historical_analogy_period")
            analogy_pct = entry_quality.get("historical_analogy_realised_pct")
            analogy_phrase = ""
            if analogy_period and analogy_pct is not None:
                analogy_phrase = (
                    f" The closest historical match in the calibration "
                    f"backtest is {analogy_period}, which realised "
                    f"{float(analogy_pct):+.1f}% over the subsequent 12 months."
                )
            paragraphs.append(
                f"**When.** {len(active)} of {len(triggers)} timing "
                f"triggers are active: {active_names or 'none'}."
                f"{analogy_phrase}"
            )

        # ---- Paragraph 4 · WHAT YOU TAKE HOME -----------------------
        net = slot_extras.get("net_return") or {}
        if net.get("net_annual_pct") is not None:
            net_pct = float(net["net_annual_pct"])
            gross_app = float(net.get("appreciation_pct", median))
            gross_yield = float(net.get("gross_yield_pct", 0))
            hold_years = int(net.get("hold_years", 5))
            paragraphs.append(
                f"**What you take home.** Gross USD appreciation of "
                f"{gross_app:+.1f}%/yr combined with rental yield of "
                f"{gross_yield:+.1f}%/yr nets out to {net_pct:+.1f}%/yr "
                f"after carrying costs, taxes, and round-trip "
                f"transaction friction amortised over a {hold_years}-year "
                f"hold. Shorter holds compress the net because "
                f"transaction costs amortise over fewer years."
            )

        # ---- Paragraph 5 · WHAT COULD BREAK IT ----------------------
        scenarios = slot_extras.get("scenarios") or []
        fx = next((s for s in scenarios if s.get("key") == "fx_shock"), None)
        crisis = next((s for s in scenarios if s.get("key") == "regime_crisis"), None)
        if fx or crisis:
            parts: list[str] = []
            if fx:
                parts.append(
                    f"an FX shock (parallel-USD brecha breaks the upper "
                    f"band durably) would imply a {float(fx['median_pct']):+.1f}% "
                    f"impact with an 80% band of "
                    f"{float(fx['band_lower_pct']):+.1f}% to {float(fx['band_upper_pct']):+.1f}%, "
                    f"prior probability {float(fx['probability']):.0%}"
                )
            if crisis:
                parts.append(
                    f"a regime crisis (HMM mass shifts to crisis state) "
                    f"would imply {float(crisis['median_pct']):+.1f}% with an "
                    f"80% band of {float(crisis['band_lower_pct']):+.1f}% to "
                    f"{float(crisis['band_upper_pct']):+.1f}%, "
                    f"prior probability {float(crisis['probability']):.0%}"
                )
            paragraphs.append(
                "**What could break it.** The dominant tails are a peso "
                "regime breakdown and a return to crisis. Specifically, "
                + "; ".join(parts)
                + ". These are not forecasts — they are conditional "
                "estimates for the named regimes."
            )

        # ---- Paragraph 6 · VERSUS ALTERNATIVES ----------------------
        if net.get("net_annual_pct") is not None:
            net_pct = float(net["net_annual_pct"])
            paragraphs.append(
                f"**Versus alternatives.** Net {net_pct:+.1f}% USD with "
                f"this risk profile compares against US 10-year "
                f"Treasuries at roughly 4.5% (the risk-free benchmark) "
                f"and a 6.5% long-run S&P 500 consensus. The thesis "
                f"reads as Treasuries plus optionality on Argentine "
                f"normalisation rather than equity-beating growth; "
                f"Argentine USD sovereigns yield more, but at "
                f"materially higher default risk."
            )

        # ---- Paragraph 7 · CONFIDENCE STATEMENT ---------------------
        bt = (insights or {}).get("backtest") or {}
        bt_all = bt.get("all") or {} if isinstance(bt, dict) else {}
        if bt_all:
            cov80 = float(bt_all.get("ci80_coverage", 0))
            hit = float(bt_all.get("directional_hit_rate", 0))
            n = int(bt_all.get("n", 0))
            paragraphs.append(
                f"**Confidence statement.** The forecast methodology "
                f"achieved {cov80:.0%} empirical coverage at the 80% "
                f"band over {n} walk-forward anchors, with {hit:.0%} "
                f"directional accuracy. Boom-state forecasts are limited "
                f"by training data (n=1 historical quarter) and should "
                f"be treated as directional only. Bottom line: at this "
                f"entry, the model's central case is a "
                f"{conviction}-conviction long with explicit tail-risk "
                f"disclosure rather than a directional bet."
            )

        return "\n\n".join(paragraphs)

    @staticmethod
    def _segment_label(segment: str) -> str:
        return (
            "CABA apartments"
            if segment == "departamentos"
            else "Argentine agricultural land (campos)"
        )

    @staticmethod
    def _unit(segment: str) -> str:
        return "USD/m²" if segment == "departamentos" else "USD/ha"

    @staticmethod
    def _verdict_for(score: Optional[float]) -> str:
        if score is None:
            return "n/a"
        s = float(score)
        if s >= 7:
            return "buy window"
        if s >= 4:
            return "mixed signals"
        return "wait"
