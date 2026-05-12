"""
Seeded commodity price provider for EchoFrame Argentina RE Intelligence.

Loads monthly MATBA-ROFEX soybean / wheat / corn prices (USD per ton) from
backend/data/seeds/commodity_prices.json and exposes the long-format
filtering API consumed by services.data_pipeline.DataPipeline.

The seed file is wide-format (one row per month, three commodity columns).
This loader pivots it to the long-format records expected by callers and
the CommodityPrice response schema:

    {"commodity": "soy", "price_usd_ton": 342.50, "date": "2020-01-01",
     "market": "MATBA-ROFEX"}
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)

_SEED_PATH = Path(__file__).parent / "seeds" / "commodity_prices.json"

# Map seed-file column name → canonical commodity name accepted by callers.
_COLUMN_TO_COMMODITY = {
    "soybean_usd_per_ton": "soy",
    "wheat_usd_per_ton": "wheat",
    "corn_usd_per_ton": "corn",
}

# Accept several aliases for the commodity filter argument.
_COMMODITY_ALIASES = {
    "soy": "soy",
    "soja": "soy",
    "soybean": "soy",
    "wheat": "wheat",
    "trigo": "wheat",
    "corn": "corn",
    "maiz": "corn",
    "maíz": "corn",
}


class CommoditySeeder:
    """Seeded monthly commodity price provider (MATBA-ROFEX)."""

    def __init__(self) -> None:
        self._rows_long: List[Dict[str, Any]] = self._load_and_pivot()

    def _load_and_pivot(self) -> List[Dict[str, Any]]:
        if not _SEED_PATH.exists():
            raise FileNotFoundError(f"Commodity seed file not found: {_SEED_PATH}")
        with _SEED_PATH.open("r", encoding="utf-8") as fh:
            wide_rows = json.load(fh)
        if not isinstance(wide_rows, list):
            raise ValueError(f"Commodity seed at {_SEED_PATH} is not a JSON array")

        long_rows: List[Dict[str, Any]] = []
        for row in wide_rows:
            date = row.get("date")
            market = row.get("source", "MATBA-ROFEX")
            for column, commodity in _COLUMN_TO_COMMODITY.items():
                price = row.get(column)
                if price is None:
                    continue
                long_rows.append(
                    {
                        "commodity": commodity,
                        "price_usd_ton": float(price),
                        "date": date,
                        "market": market,
                    }
                )

        logger.info(
            "CommoditySeeder loaded %d wide rows → %d long-format records",
            len(wide_rows),
            len(long_rows),
        )
        return long_rows

    async def get_prices(
        self,
        commodity: Optional[str] = None,
        days_back: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Return commodity price records, optionally filtered.

        Args:
            commodity: 'soy' | 'wheat' | 'corn' (Spanish aliases accepted),
                or None for all.
            days_back: Limit to records within this many days of the most
                recent observation in the seed file. Use 0 to disable.

        Returns:
            List of commodity price dicts sorted by date descending.

        Raises:
            ValueError: if `commodity` is provided but unrecognised.
        """
        rows = self._rows_long

        if commodity:
            key = commodity.strip().lower()
            canonical = _COMMODITY_ALIASES.get(key)
            if canonical is None:
                raise ValueError(
                    f"Unknown commodity '{commodity}'. "
                    f"Expected one of: {sorted(set(_COMMODITY_ALIASES))}"
                )
            rows = [r for r in rows if r["commodity"] == canonical]

        if days_back and days_back > 0 and rows:
            latest = max(self._parse_date(r["date"]) for r in rows if self._parse_date(r["date"]))
            cutoff = latest - timedelta(days=days_back)
            rows = [
                r
                for r in rows
                if (parsed := self._parse_date(r["date"])) is not None and parsed >= cutoff
            ]

        rows.sort(key=lambda r: str(r["date"]), reverse=True)
        return rows

    @staticmethod
    def _parse_date(value: Optional[str]) -> Optional[datetime]:
        if value is None:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
