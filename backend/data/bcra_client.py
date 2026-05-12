"""
BCRA API client for EchoFrame Argentina Real Estate Intelligence.

Async httpx client for the BCRA (Banco Central de la República Argentina)
public statistics API. The API is free and requires no authentication.

Base URL: https://api.bcra.gob.ar/estadisticas/v4.0

v2 and v3 of the API were deprecated by BCRA — they explicitly return
"Método correspondiente a la v2/v3 ha sido deprecado." in the 400 body.
v4 changed both the path (/monetarias/{id}) and the response shape
(observations live under results[0].detalle, not results).

Variables consumed (v4 IDs):
  1   Reservas internacionales            (USD millions)
  4   Tipo de cambio minorista            (ARS per USD, retail sell)
  5   Tipo de cambio mayorista            (ARS per USD, wholesale)
  7   Tasa BADLAR                         (was ID 6 in v2)
  8   Tasa TM20                           (was ID 7 in v2)
  15  Base monetaria                      (ARS millions)
  27  Inflación mensual                   (% monthly)
  28  Inflación interanual                (% yoy)

Each `get_*` method returns a dict shaped like:
    {"valor": float, "fecha": "YYYY-MM-DD"}

Failures raise; callers in services.data_pipeline catch and fall back.
"""

import asyncio
import logging
import ssl
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import httpx

from config import settings


logger = logging.getLogger(__name__)


class BCRAClient:
    """Async client for the BCRA public statistics API."""

    # Variable IDs in the BCRA v4 API.
    VAR_RESERVES = 1
    VAR_EXCHANGE_RATE_RETAIL = 4
    VAR_EXCHANGE_RATE_WHOLESALE = 5
    VAR_BADLAR = 7              # moved from id 6 in v2
    VAR_TM20 = 8                # moved from id 7 in v2
    VAR_MONETARY_BASE = 15
    VAR_INFLATION_MONTHLY = 27
    VAR_INFLATION_YOY = 28

    def __init__(self) -> None:
        self.base_url = settings.bcra_api_base_url.rstrip("/")
        self.timeout = settings.bcra_api_timeout
        self.retries = settings.bcra_api_retries
        # BCRA's TLS chain is occasionally non-standard; allow disabling verify
        # via the existing setting path if it surfaces in the field.
        verify: Any = True
        try:
            if getattr(settings, "bcra_verify_ssl", True) is False:
                verify = False
        except Exception:
            verify = True
        self._verify = verify

    async def get_exchange_rate(self) -> Dict[str, Any]:
        """Most recent wholesale USD/ARS rate (variable 5)."""
        return await self._latest_value(self.VAR_EXCHANGE_RATE_WHOLESALE)

    async def get_reference_rate(self) -> Dict[str, Any]:
        """BADLAR reference rate (variable 6)."""
        return await self._latest_value(self.VAR_BADLAR)

    async def get_inflation_data(self) -> Dict[str, Any]:
        """Most recent monthly CPI (variable 27)."""
        return await self._latest_value(self.VAR_INFLATION_MONTHLY)

    async def get_reserves(self) -> Dict[str, Any]:
        """Most recent international reserves (variable 1, USD millions)."""
        return await self._latest_value(self.VAR_RESERVES)

    async def get_monetary_base(self) -> Dict[str, Any]:
        """Most recent monetary base (variable 15, ARS millions)."""
        return await self._latest_value(self.VAR_MONETARY_BASE)

    async def _latest_value(self, variable_id: int) -> Dict[str, Any]:
        """
        Fetch the most recent observation for a variable.

        Args:
            variable_id: BCRA variable identifier.

        Returns:
            Dict with keys 'valor' (float) and 'fecha' (YYYY-MM-DD string).

        Raises:
            RuntimeError: if the API call fails after all retries or the
                response contains no observations.

        Notes on the v4 response shape:
            {
              "status": 200,
              "metadata": {...},
              "results": [
                {
                  "idVariable": 5,
                  "detalle": [
                    {"fecha": "2026-05-11", "valor": 1399.47},
                    ...
                  ]
                }
              ]
            }
        """
        # Use a generous lookback so we always get something even over
        # long Argentine holidays. Monthly series like inflation only
        # publish on the last day of the month.
        end = datetime.utcnow().date()
        start = end - timedelta(days=90)
        path = (
            f"/monetarias/{variable_id}"
            f"?desde={start.isoformat()}&hasta={end.isoformat()}"
        )
        payload = await self._request_with_retries(path)

        results = payload.get("results") or []
        if not results:
            raise RuntimeError(
                f"BCRA variable {variable_id}: empty results array"
            )

        # In v4 the time series lives under results[0].detalle.
        first = results[0]
        observations = first.get("detalle") or []
        if not observations:
            raise RuntimeError(
                f"BCRA variable {variable_id}: no observations in {start}..{end}"
            )

        latest = max(observations, key=lambda r: r.get("fecha", ""))
        return {
            "valor": float(latest["valor"]),
            "fecha": str(latest["fecha"]),
        }

    async def _request_with_retries(self, path: str) -> Dict[str, Any]:
        """GET `path` with exponential backoff retry on transient errors."""
        url = f"{self.base_url}{path}"
        last_exc: Optional[Exception] = None

        for attempt in range(self.retries):
            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout, verify=self._verify
                ) as client:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    return resp.json()
            except (httpx.HTTPError, ssl.SSLError) as exc:
                last_exc = exc
                wait = 2 ** attempt
                logger.warning(
                    "BCRA request failed (attempt %d/%d) for %s: %s; retrying in %ds",
                    attempt + 1,
                    self.retries,
                    path,
                    exc,
                    wait,
                )
                await asyncio.sleep(wait)

        assert last_exc is not None
        raise RuntimeError(f"BCRA request failed after {self.retries} attempts: {last_exc}")
