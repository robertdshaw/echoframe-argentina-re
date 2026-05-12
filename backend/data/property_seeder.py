"""
Seeded property listings provider for EchoFrame Argentina RE Intelligence.

Loads Buenos Aires apartment listings (ba_listings.json) and agricultural
land listings (campos_listings.json) from backend/data/seeds/ and exposes
filtering helpers consumed by services.data_pipeline.DataPipeline.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)

_SEEDS_DIR = Path(__file__).parent / "seeds"
_BA_PATH = _SEEDS_DIR / "ba_listings.json"
_CAMPOS_PATH = _SEEDS_DIR / "campos_listings.json"


class PropertySeeder:
    """Seeded property listing provider for departamentos and campos."""

    def __init__(self) -> None:
        self._ba_listings: List[Dict[str, Any]] = self._load(_BA_PATH, "BA")
        self._campos_listings: List[Dict[str, Any]] = self._load(_CAMPOS_PATH, "campos")

    @staticmethod
    def _load(path: Path, label: str) -> List[Dict[str, Any]]:
        if not path.exists():
            raise FileNotFoundError(f"Property seed file not found: {path}")
        with path.open("r", encoding="utf-8") as fh:
            listings = json.load(fh)
        if not isinstance(listings, list):
            raise ValueError(f"{label} seed at {path} is not a JSON array")
        logger.info("PropertySeeder loaded %d %s listings", len(listings), label)
        return listings

    async def get_ba_listings(
        self,
        barrio: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Return Buenos Aires apartment listings.

        Args:
            barrio: Optional barrio filter (case-insensitive exact match).
            limit: Maximum listings to return.

        Returns:
            List of listing dicts.
        """
        listings = self._ba_listings
        if barrio:
            target = barrio.strip().lower()
            listings = [
                l for l in listings if str(l.get("barrio", "")).strip().lower() == target
            ]
        return listings[:limit]

    async def get_campos_listings(
        self,
        zone: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Return agricultural land listings.

        Args:
            zone: Optional zone filter (e.g. 'core_pampa', 'santa_fe').
            limit: Maximum listings to return.

        Returns:
            List of listing dicts.
        """
        listings = self._campos_listings
        if zone:
            target = zone.strip().lower()
            listings = [
                l for l in listings if str(l.get("zone", "")).strip().lower() == target
            ]
        return listings[:limit]
