"""
FRED (St. Louis Fed) API client for EchoFrame Argentina RE Intelligence.

Used as a secondary source / fallback when BCRA's API is unavailable.
FRED carries a small set of Argentine macro series sourced from the IMF,
World Bank, and OECD. Coverage is thinner and lower-frequency than BCRA,
but the API is highly reliable.

Useful Argentine series (verified live against FRED 2026):
    ARGCCUSMA02STM       USD/ARS monthly average (OECD, monthly)
    ARGCCUSMA02STQ       USD/ARS quarterly average (OECD, quarterly)
    FPCPITOTLZGARG       Argentina CPI inflation, annual % (World Bank)
    RBARBIS              Real broad effective exchange rate for Argentina
    NBARBIS              Broad effective exchange rate for Argentina
    FXRATEARA618NUPN     Exchange rate to USD for Argentina (annual)

API docs: https://fred.stlouisfed.org/docs/api/fred/

Each `get_*` / `get_observation` method returns:
    {"value": float, "date": "YYYY-MM-DD", "series_id": str}
"""

import logging
from typing import Any, Dict, Optional

import httpx

from config import settings


logger = logging.getLogger(__name__)


class FREDClient:
    """Async client for the FRED public statistics API."""

    # Argentina-relevant series the data_pipeline may consult.
    # IDs verified live against the FRED catalog in 2026 — DEXARUS and the
    # CCUSMA02ARM618N variant from earlier doc generations both 404 now.
    SERIES_USD_ARS_MONTHLY = "ARGCCUSMA02STM"
    SERIES_INFLATION_ANNUAL = "FPCPITOTLZGARG"
    SERIES_REAL_EFFECTIVE_FX = "RBARBIS"

    # Placeholders we should never treat as real keys.
    _PLACEHOLDER_KEYS = {"", "your_key", "your-api-key", "demo", "changeme", "todo"}

    def __init__(self) -> None:
        self.api_key = settings.fred_api_key
        self.base_url = settings.fred_api_base_url.rstrip("/")
        self.timeout = settings.fred_api_timeout

    @property
    def is_configured(self) -> bool:
        """True when a real (non-placeholder) API key is available."""
        if not self.api_key:
            return False
        return self.api_key.strip().lower() not in self._PLACEHOLDER_KEYS

    async def get_observation(self, series_id: str) -> Dict[str, Any]:
        """
        Fetch the most recent observation for a FRED series.

        Args:
            series_id: FRED series identifier (e.g. 'CCUSMA02ARM618N').

        Returns:
            Dict with 'value', 'date', and 'series_id'.

        Raises:
            RuntimeError: when the key is missing, the request fails, or
                the series has no usable observations.
        """
        if not self.is_configured:
            raise RuntimeError(
                "FRED_API_KEY is not configured; FRED fallback unavailable"
            )

        params = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 5,
        }
        url = f"{self.base_url}/series/observations"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                payload = resp.json()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"FRED request failed for {series_id}: {exc}") from exc

        observations = payload.get("observations") or []
        # FRED returns '.' for missing values; walk down until we find a real one.
        for obs in observations:
            raw_value = obs.get("value", ".")
            if raw_value == ".":
                continue
            try:
                value = float(raw_value)
            except ValueError:
                continue
            return {
                "value": value,
                "date": obs.get("date", ""),
                "series_id": series_id,
            }

        raise RuntimeError(
            f"FRED series {series_id}: no usable observations in latest 5"
        )

    async def get_exchange_rate(self) -> Optional[Dict[str, Any]]:
        """Most recent USD/ARS monthly observation as a BCRA-shaped dict."""
        obs = await self.get_observation(self.SERIES_USD_ARS_MONTHLY)
        return {"valor": obs["value"], "fecha": obs["date"]}

    async def get_inflation_annual(self) -> Optional[Dict[str, Any]]:
        """Annual CPI inflation as a BCRA-shaped dict."""
        obs = await self.get_observation(self.SERIES_INFLATION_ANNUAL)
        return {"valor": obs["value"], "fecha": obs["date"]}
