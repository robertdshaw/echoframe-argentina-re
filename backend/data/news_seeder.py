"""
Seeded news article provider for EchoFrame Argentina Real Estate Intelligence.

Loads pre-curated Spanish-language news articles from
backend/data/seeds/news_articles.json and exposes a filtering API consumed
by services.data_pipeline.DataPipeline.

Articles are pre-classified (signal_type, impact_direction, impact_magnitude,
affected_segments, keywords) so they can flow straight into the NLP and
forecasting pipelines without requiring a live news provider.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)

_SEED_PATH = Path(__file__).parent / "seeds" / "news_articles.json"


class NewsSeeder:
    """Seeded news article provider backed by a static JSON corpus."""

    def __init__(self) -> None:
        self._articles: List[Dict[str, Any]] = self._load()

    def _load(self) -> List[Dict[str, Any]]:
        if not _SEED_PATH.exists():
            raise FileNotFoundError(f"News seed file not found: {_SEED_PATH}")
        with _SEED_PATH.open("r", encoding="utf-8") as fh:
            articles = json.load(fh)
        if not isinstance(articles, list):
            raise ValueError(f"News seed at {_SEED_PATH} is not a JSON array")
        logger.info("NewsSeeder loaded %d articles from %s", len(articles), _SEED_PATH)
        return articles

    async def get_articles(
        self,
        limit: int = 50,
        category: Optional[str] = None,
        date_from: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return seeded articles, optionally filtered and capped at `limit`.

        Args:
            limit: Maximum number of articles to return.
            category: Filter by article category (e.g. 'economic_policy').
            date_from: Only return articles published on/after this UTC datetime.

        Returns:
            List of article dicts sorted by published_at descending.
        """
        filtered: List[Dict[str, Any]] = []
        for article in self._articles:
            if category is not None and article.get("category") != category:
                continue
            if date_from is not None:
                published = self._parse_published(article.get("published_at"))
                if published is None or published < date_from:
                    continue
            filtered.append(article)

        filtered.sort(key=lambda a: str(a.get("published_at", "")), reverse=True)
        return filtered[:limit]

    @staticmethod
    def _parse_published(value: Optional[str]) -> Optional[datetime]:
        if value is None:
            return None
        try:
            cleaned = value.replace("Z", "+00:00")
            return datetime.fromisoformat(cleaned).replace(tzinfo=None)
        except ValueError:
            return None
