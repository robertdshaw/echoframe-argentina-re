"""
NewsData.io live client for EchoFrame Argentina Real Estate Intelligence.

When `settings.newsdata_api_key` is set, fetches Spanish-language Argentine
real-estate and macro news from NewsData.io and adapts the response into
the same shape produced by NewsSeeder so the rest of the pipeline does not
need to care which source the article came from.

NewsData.io free tier: 200 requests/day, 10 articles per page, no
backfill beyond 48h. We page through `nextPage` tokens up to a small cap.

Notes on classification: NewsData.io does not classify into our
signal_type / impact_direction / affected_segments vocabularies. We leave
those fields unset on the returned dict — `services.signal_service`
re-classifies through the NLP pipeline (SignalClassifier, SentimentAnalyzer,
EntityExtractor) before the article hits the forecasting models, so the
downstream contract holds regardless of source.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from config import settings


logger = logging.getLogger(__name__)


class NewsDataClient:
    """Async client for the NewsData.io REST API."""

    DEFAULT_ENDPOINT = "https://newsdata.io/api/1/news"

    # Real-estate / macro keywords that filter the query at source so we
    # don't burn our quota on entertainment / sport. NewsData.io's free
    # tier rejects queries longer than ~5 terms with 422 Unprocessable
    # Entity, so we pick the five highest-coverage keywords. Quotes are
    # omitted because they also trigger 422 above ~3 terms.
    DEFAULT_QUERY = "BCRA OR inmobiliario OR dolar OR inflacion OR hipotecario"

    def __init__(self, endpoint: Optional[str] = None) -> None:
        self.api_key = settings.newsdata_api_key
        self.endpoint = endpoint or self.DEFAULT_ENDPOINT
        self.timeout = 20

    # Common placeholder values shipped in .env.example files. Treating
    # these as "no key" prevents needless 401s during demos.
    _PLACEHOLDER_KEYS = {
        "",
        "your_key",
        "your-key",
        "your_api_key",
        "your-api-key",
        "changeme",
        "todo",
        "demo",
        "none",
        "null",
        "placeholder",
    }

    @property
    def is_configured(self) -> bool:
        """True when a non-placeholder API key is available."""
        if not self.api_key:
            return False
        return self.api_key.strip().lower() not in self._PLACEHOLDER_KEYS

    async def get_articles(
        self,
        limit: int = 20,
        max_pages: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Fetch recent Argentine real-estate / macro articles.

        Args:
            limit: Soft cap on returned articles.
            max_pages: How many pages of nextPage tokens to walk (free tier
                returns 10 per page; 3 pages = up to 30 articles).

        Returns:
            List of article dicts normalized to the NewsSeeder schema:
            id, title, source, published_at, category, summary, keywords.

        Raises:
            RuntimeError: when the key is missing or every request fails.
        """
        if not self.is_configured:
            raise RuntimeError(
                "NEWSDATA_API_KEY is not configured; live news fetch unavailable"
            )

        params: Dict[str, Any] = {
            "apikey": self.api_key,
            "country": "ar",
            "language": "es",
            "q": self.DEFAULT_QUERY,
        }

        collected: List[Dict[str, Any]] = []
        next_page: Optional[str] = None

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                for _ in range(max_pages):
                    if next_page:
                        params["page"] = next_page
                    resp = await client.get(self.endpoint, params=params)
                    resp.raise_for_status()
                    payload = resp.json()

                    if payload.get("status") != "success":
                        raise RuntimeError(
                            f"NewsData.io error: {payload.get('message', payload)}"
                        )

                    for raw in payload.get("results", []):
                        normalized = self._normalize(raw)
                        if normalized is not None:
                            collected.append(normalized)

                    next_page = payload.get("nextPage")
                    if not next_page or len(collected) >= limit:
                        break
        except httpx.HTTPError as exc:
            raise RuntimeError(f"NewsData.io HTTP error: {exc}") from exc

        # Sort by published_at descending so the freshest hits come first.
        collected.sort(key=lambda a: a.get("published_at", ""), reverse=True)
        return collected[:limit]

    @staticmethod
    def _normalize(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Adapt a NewsData.io record into the NewsSeeder schema."""
        article_id = raw.get("article_id") or raw.get("link")
        title = raw.get("title")
        if not article_id or not title:
            return None

        # NewsData.io pubDate is 'YYYY-MM-DD HH:MM:SS' in UTC; normalize.
        published_raw = raw.get("pubDate", "")
        published_iso = published_raw.replace(" ", "T")
        if published_iso and not published_iso.endswith("Z"):
            published_iso += "Z"

        keywords = raw.get("keywords") or []
        if isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split(",") if k.strip()]

        return {
            "id": str(article_id),
            "title": title,
            "source": raw.get("source_id") or raw.get("source_name") or "newsdata.io",
            "published_at": published_iso or datetime.utcnow().isoformat() + "Z",
            "category": (raw.get("category") or ["news"])[0]
            if isinstance(raw.get("category"), list)
            else (raw.get("category") or "news"),
            "summary": raw.get("description") or raw.get("content", "")[:500],
            "keywords": keywords,
            "affected_segments": [],  # Re-classified downstream by NLP
            "data_source": "newsdata.io",
        }
