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

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from anthropic import AsyncAnthropic

from config import settings


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
    """Generates short executive-style narratives via Claude."""

    SYSTEM_PROMPT = (
        "You are a senior real estate strategist briefing a sophisticated "
        "Argentine client. Output is read by an investor making a real "
        "allocation decision; they are numerate but time-poor.\n\n"
        "Rules:\n"
        "- Be direct. Lead with the bottom line in the first sentence.\n"
        "- Use plain English, not jargon. Spanish-language data labels "
        "may appear in the input; quote them in Spanish but explain in "
        "English.\n"
        "- Quote at least one credible-interval bound to anchor uncertainty.\n"
        "- Reference the model's track record when relevant (calibration "
        "coverage, MAE vs naive) — investors trust validated forecasts.\n"
        "- Acknowledge tail risk when the model's downside band is wide.\n"
        "- Never invent numbers. Only use figures present in the input.\n"
        "- 4 short paragraphs, max 180 words total.\n"
        "- No headings, no bullet lists, no markdown. Flowing prose.\n"
        "- Final sentence: 'Bottom line: …' summarising the trade.\n"
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
    ) -> Dict[str, Any]:
        """
        Compose the narrative prompt and call Claude.

        Returns a dict shaped:
            {"status": "ok" | "unavailable",
             "narrative": str | None,
             "model": str,
             "generated_at": iso-string,
             "reason": str | None}
        """
        if not self.is_configured or self._client is None:
            return {
                "status": "unavailable",
                "narrative": None,
                "reason": "ANTHROPIC_API_KEY not configured",
                "model": self.model,
            }

        cache_key = f"{segment}:{forecast_payload.get('current_price')}:{len(signals)}"
        cached = self._cache.get(cache_key)
        if cached and cached.expires_at > time.time():
            return cached.payload

        user_prompt = self._build_prompt(segment, forecast_payload, signals, insights)

        try:
            response = await self._client.messages.create(
                model=self.model,
                max_tokens=512,
                system=self.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            text_blocks = [b.text for b in response.content if getattr(b, "type", None) == "text"]
            narrative = "".join(text_blocks).strip()
        except Exception as exc:
            logger.warning("Claude narrative call failed: %s", exc)
            return {
                "status": "unavailable",
                "narrative": None,
                "reason": f"Claude API error: {exc}",
                "model": self.model,
            }

        payload: Dict[str, Any] = {
            "status": "ok",
            "narrative": narrative,
            "model": self.model,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        self._cache[cache_key] = _CacheEntry(payload=payload, expires_at=time.time() + self.ttl_seconds)
        return payload

    @staticmethod
    def _build_prompt(
        segment: str,
        forecast_payload: Dict[str, Any],
        signals: list,
        insights: Optional[Dict[str, Any]],
    ) -> str:
        """Render the prompt the strategist will react to."""
        unit = "USD/m²" if segment == "departamentos" else "USD/ha"
        current = forecast_payload.get("current_price", 0)
        regime = forecast_payload.get("regime_context", {})
        forecasts = forecast_payload.get("forecasts", {})

        # Pull Y1/Y2/Y3 model estimates compactly.
        horizon_lines = []
        for year_key in ("1", "2", "3"):
            f = forecasts.get(year_key) or forecasts.get(int(year_key))
            if not f:
                continue
            m = f.get("model_estimate", {})
            ci80 = m.get("ci_80", {})
            horizon_lines.append(
                f"  Year {year_key}: median {m.get('median_change_pct', 0):+.1f}%; "
                f"80% CI {ci80.get('lower', 0):+.1f}% to {ci80.get('upper', 0):+.1f}%; "
                f"P(↑) {m.get('p_increase', 0):.0%}; "
                f"P(decrease > 5%) {m.get('p_decrease_5pct', 0):.0%}"
            )

        # Signals (top 5 by impact).
        sorted_signals = sorted(
            signals, key=lambda s: s.get("market_impact_score", 0), reverse=True
        )[:5]
        signal_lines = []
        for s in sorted_signals:
            cls = s.get("signal_classification", {})
            signal_lines.append(
                f"  - [{cls.get('impact_direction', '?')}/{cls.get('impact_magnitude', 0):.2f}] "
                f"{s.get('title', '')[:120]}"
            )

        # Backtest accuracy block.
        bt = (insights or {}).get("backtest", {})
        bt_all = bt.get("all", {}) if isinstance(bt, dict) else {}
        accuracy_block = ""
        if bt_all:
            accuracy_block = (
                f"\nModel track record (29 walk-forward LOO anchors, 2018-2025):\n"
                f"  - 80% CI coverage: {bt_all.get('ci80_coverage', 0):.0%} (target 80%)\n"
                f"  - Directional hit rate: {bt_all.get('directional_hit_rate', 0):.0%}\n"
                f"  - Brier score: {bt_all.get('brier_score', 0):.3f} (vs 0.25 coin-flip)\n"
                f"  - MAE: {bt_all.get('mae_pct', 0):.2f} pp · naive baseline: "
                f"{bt_all.get('naive_baseline_mae_pct', 0):.2f} pp\n"
            )

        return (
            f"Segment: {segment.upper()} · current price {current:.0f} {unit}\n"
            f"HMM regime: {regime.get('current', 'unknown')} "
            f"({regime.get('confidence', 0):.0%} confidence)\n"
            f"Regime transitions next quarter: "
            f"{regime.get('transition_probabilities', {})}\n\n"
            f"Forecast horizons (Student-t df=4 posterior):\n"
            + "\n".join(horizon_lines)
            + accuracy_block
            + "\n\nTop live news signals affecting this segment:\n"
            + ("\n".join(signal_lines) if signal_lines else "  (none above threshold)")
            + "\n\nWrite the briefing per the system instructions."
        )
