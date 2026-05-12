"""
REM API client for EchoFrame Argentina Real Estate Intelligence.

The REM (Relevamiento de Expectativas de Mercado) is the BCRA's monthly
survey of economist consensus forecasts. Served through a free Cloudflare
Workers proxy that requires no authentication.

Base URL: https://bcra-rem-api.facujallia.workers.dev

Endpoints consumed:
  /api/ipc_general    inflation forecasts
  /api/tipo_cambio    USD/ARS exchange rate forecasts
  /api/pib            GDP growth forecasts

Each `get_*` method returns a dict shaped like:
    {"median": float, "mean": float, "period": "YYYY-MM-DD" or "YYYY"}
"""

import logging
from typing import Any, Dict, Optional

import httpx

from config import settings


logger = logging.getLogger(__name__)


class REMClient:
    """Async client for the REM consensus survey API."""

    PATH_INFLATION = "/api/ipc_general"
    PATH_EXCHANGE_RATE = "/api/tipo_cambio"
    PATH_GDP = "/api/pib"

    def __init__(self) -> None:
        self.base_url = settings.rem_api_base_url.rstrip("/")
        self.timeout = settings.rem_api_timeout

    async def get_inflation_forecast(self) -> Dict[str, Any]:
        """Latest median/mean monthly inflation forecast from economists."""
        return await self._latest_forecast(self.PATH_INFLATION)

    async def get_exchange_rate_forecast(self) -> Dict[str, Any]:
        """Latest median/mean USD/ARS forecast from economists."""
        return await self._latest_forecast(self.PATH_EXCHANGE_RATE)

    async def get_gdp_forecast(self) -> Dict[str, Any]:
        """Latest median/mean annual GDP growth forecast from economists."""
        return await self._latest_forecast(self.PATH_GDP)

    async def _latest_forecast(self, path: str) -> Dict[str, Any]:
        """
        Fetch the most recent forecast observation from a REM endpoint.

        Args:
            path: API path, e.g. '/api/ipc_general'.

        Returns:
            Dict with 'median', 'mean', and 'period' keys.

        Raises:
            RuntimeError: on HTTP failure or empty response.
        """
        payload = await self._request(path)
        rows = payload.get("datos") or payload.get("results") or []
        if not rows:
            raise RuntimeError(f"REM endpoint {path}: empty response")

        # Sort by fecha (publication date of the survey) descending.
        rows_sorted = sorted(
            rows, key=lambda r: str(r.get("fecha") or r.get("date") or ""), reverse=True
        )
        latest = rows_sorted[0]

        median = self._coerce_float(
            latest.get("mediana")
            or latest.get("median")
            or latest.get("valor")
            or latest.get("value")
        )
        mean = self._coerce_float(
            latest.get("media")
            or latest.get("mean")
            or latest.get("promedio")
            or median  # fall back to median when only one stat is provided
        )
        period = str(
            latest.get("periodo")
            or latest.get("period")
            or latest.get("fecha")
            or latest.get("date")
            or ""
        )

        return {"median": median, "mean": mean, "period": period}

    async def _request(self, path: str) -> Dict[str, Any]:
        """GET `path` once (no retries — the proxy is small, fast)."""
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"REM request failed for {path}: {exc}") from exc

    @staticmethod
    def _coerce_float(value: Optional[Any]) -> float:
        """Best-effort float coercion; raises on non-numeric input."""
        if value is None:
            raise RuntimeError("REM response is missing required numeric field")
        return float(value)
