"""
Data orchestration pipeline for EchoFrame Argentina Real Estate Intelligence.

Coordinates data collection from live APIs and seeded sources, manages caching,
and provides unified data access for the forecasting models.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import json

from data.bcra_client import BCRAClient
from data.rem_client import REMClient
from data.fred_client import FREDClient
from data.news_seeder import NewsSeeder
from data.newsdata_client import NewsDataClient
from data.property_seeder import PropertySeeder
from data.properati_scraper import ProperatiScraper
from data.commodity_seeder import CommoditySeeder


logger = logging.getLogger(__name__)


@dataclass
class DataFreshness:
    """Track data freshness for different sources."""
    source: str
    last_updated: datetime
    is_stale: bool
    staleness_threshold_hours: int


class DataPipeline:
    """
    Orchestrates data collection from all sources for the forecasting pipeline.
    
    Manages live API calls (BCRA, REM), seeded data access, and caching
    to provide consistent data to the forecasting models with proper
    error handling and fallback mechanisms.
    """
    
    def __init__(self):
        """Initialize data pipeline with all client instances."""
        # Live API clients
        self.bcra_client = BCRAClient()
        self.rem_client = REMClient()
        self.fred_client = FREDClient()
        self.newsdata_client = NewsDataClient()
        self.properati_scraper = ProperatiScraper()

        # Seeded data providers (used as fallback when live sources fail)
        self.news_seeder = NewsSeeder()
        self.property_seeder = PropertySeeder()
        self.commodity_seeder = CommoditySeeder()
        
        # In-memory cache with timestamps
        self._cache = {}
        self._cache_timestamps = {}
        
        # Cache TTL settings (hours)
        self.cache_ttl = {
            "bcra_data": 1,        # BCRA updates daily, cache 1 hour
            "rem_data": 24,        # REM updates weekly, cache 24 hours
            "news_articles": 6,    # News articles, refresh every 6 hours
            "property_listings": 12, # Property data, refresh twice daily
            "commodity_prices": 2,   # Commodity prices, refresh every 2 hours
            "macro_indicators": 1,   # Combined macro data, cache 1 hour
        }

    async def get_macro_indicators(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get comprehensive macro indicators from BCRA and REM APIs.
        
        Args:
            force_refresh: Skip cache and fetch fresh data
            
        Returns:
            Dict with current macro indicators including exchange rates,
            inflation, interest rates, and market expectations
        """
        cache_key = "macro_indicators"
        
        if not force_refresh and self._is_cache_valid(cache_key):
            logger.info("Returning cached macro indicators")
            return self._cache[cache_key]
        
        logger.info("Fetching fresh macro indicators")
        
        try:
            # Fetch BCRA and REM data in parallel
            bcra_task = asyncio.create_task(self._fetch_bcra_data())
            rem_task = asyncio.create_task(self._fetch_rem_data())
            
            bcra_data, rem_data = await asyncio.gather(
                bcra_task, rem_task, return_exceptions=True
            )
            
            # Handle potential exceptions
            if isinstance(bcra_data, Exception):
                logger.error(f"BCRA API error: {bcra_data}")
                bcra_data = self._get_fallback_bcra_data()
            
            if isinstance(rem_data, Exception):
                logger.error(f"REM API error: {rem_data}")
                rem_data = self._get_fallback_rem_data()
            
            # Combine and structure the data
            macro_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "bcra": bcra_data,
                "rem": rem_data,
                "sources": {
                    "bcra_status": "live" if not isinstance(bcra_data, Exception) else "fallback",
                    "rem_status": "live" if not isinstance(rem_data, Exception) else "fallback"
                }
            }
            
            # Cache the result
            self._cache[cache_key] = macro_data
            self._cache_timestamps[cache_key] = datetime.utcnow()
            
            return macro_data
            
        except Exception as e:
            logger.error(f"Error in get_macro_indicators: {e}")
            # Return cached data if available, otherwise fallback data
            if cache_key in self._cache:
                logger.warning("Returning stale cached macro data due to API errors")
                return self._cache[cache_key]
            else:
                logger.warning("Returning fallback macro data")
                return self._get_fallback_macro_data()

    async def get_news_signals(
        self, 
        limit: int = 50, 
        category: Optional[str] = None,
        date_from: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get news articles with signal classification.
        
        Args:
            limit: Maximum number of articles to return
            category: Filter by article category (optional)
            date_from: Only return articles after this date (optional)
            
        Returns:
            List of news articles with signal metadata
        """
        cache_key = f"news_signals_{limit}_{category}_{date_from}"
        
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]
        
        articles: List[Dict[str, Any]] = []
        live_used = False

        # Try live NewsData.io first when an API key is configured.
        if self.newsdata_client.is_configured:
            try:
                live = await self.newsdata_client.get_articles(limit=limit)
                if live:
                    articles = live
                    live_used = True
                    logger.info("News signals: %d live articles from NewsData.io", len(live))
            except Exception as exc:
                logger.warning(
                    "NewsData.io live fetch failed (%s); falling back to seed corpus", exc
                )

        if not articles:
            try:
                articles = await self.news_seeder.get_articles(
                    limit=limit, category=category, date_from=date_from
                )
                logger.info("News signals: %d seeded articles", len(articles))
            except Exception as exc:
                logger.error("News seed fallback failed: %s", exc)
                return []

        # Tag freshness so downstream consumers can render a "live" badge.
        enriched = [
            {
                **a,
                "data_source": a.get("data_source", "seeded"),
                "freshness": "live" if live_used else "static_seed",
            }
            for a in articles
        ]

        self._cache[cache_key] = enriched
        self._cache_timestamps[cache_key] = datetime.utcnow()
        return enriched

    async def get_property_listings(
        self,
        segment: str = "departamentos",
        barrio: Optional[str] = None,
        limit: int = 100,
        live: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Get property listings for market analysis.

        Args:
            segment: "departamentos" or "campos"
            barrio: Filter by neighborhood (for departamentos)
            limit: Maximum listings to return
            live: If True (default), try the live Properati scrape first
                  for departamentos. If False, skip the network call and
                  return seeded data immediately — used by the forecast
                  service so the forecast critical path doesn't block on
                  a slow scrape. The map widget calls with live=True.

        Returns:
            List of property listings with metadata
        """
        cache_key = f"property_listings_{segment}_{barrio}_{limit}_{live}"

        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        if segment not in ("departamentos", "campos"):
            raise ValueError(f"Invalid segment: {segment}")

        listings: List[Dict[str, Any]] = []
        live_used = False

        # Live path: Properati covers departamentos only. Campos always seeded.
        if live and segment == "departamentos":
            try:
                # Hard cap on how long the scrape can block the caller —
                # if Properati is slow we'd rather degrade to seed than
                # blow past a frontend timeout.
                scraped = await asyncio.wait_for(
                    self.properati_scraper.get_listings(
                        barrio=barrio, limit=limit, max_pages=2
                    ),
                    timeout=8.0,
                )
                if scraped:
                    listings = scraped
                    live_used = True
                    logger.info(
                        "Property listings (departamentos): %d live from Properati",
                        len(scraped),
                    )
            except asyncio.TimeoutError:
                logger.warning(
                    "Properati live scrape exceeded 8s budget; using seed corpus"
                )
            except Exception as exc:
                logger.warning(
                    "Properati live scrape failed (%s); falling back to seed corpus",
                    exc,
                )

        if not listings:
            try:
                if segment == "departamentos":
                    listings = await self.property_seeder.get_ba_listings(
                        barrio=barrio, limit=limit
                    )
                else:
                    listings = await self.property_seeder.get_campos_listings(
                        zone=barrio, limit=limit
                    )
                logger.info("Property listings (%s): %d seeded", segment, len(listings))
            except Exception as exc:
                logger.error("Property seed fallback failed: %s", exc)
                return []

        enriched = [
            {
                **l,
                "data_source": l.get("data_source", "seeded"),
                "segment": segment,
                "freshness": "live" if live_used else "static_seed",
            }
            for l in listings
        ]

        self._cache[cache_key] = enriched
        self._cache_timestamps[cache_key] = datetime.utcnow()
        return enriched

    async def get_commodity_prices(
        self,
        commodity: Optional[str] = None,
        days_back: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get commodity price data for agricultural analysis.
        
        Args:
            commodity: "soy", "wheat", "corn", or None for all
            days_back: Number of days of historical data
            
        Returns:
            List of commodity price records
        """
        cache_key = f"commodity_prices_{commodity}_{days_back}"
        
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]
        
        try:
            prices = await self.commodity_seeder.get_prices(
                commodity=commodity,
                days_back=days_back
            )
            
            # Add metadata
            enriched_prices = []
            for price_record in prices:
                enriched_record = {
                    **price_record,
                    "data_source": "seeded",
                    "market": "matba_rofex"
                }
                enriched_prices.append(enriched_record)
            
            # Cache result
            self._cache[cache_key] = enriched_prices
            self._cache_timestamps[cache_key] = datetime.utcnow()
            
            return enriched_prices
            
        except Exception as e:
            logger.error(f"Error getting commodity prices: {e}")
            return []

    async def get_data_freshness_status(self) -> Dict[str, DataFreshness]:
        """
        Get freshness status for all data sources.
        
        Returns:
            Dict mapping source names to DataFreshness objects
        """
        freshness_status = {}
        current_time = datetime.utcnow()
        
        for cache_key, ttl_hours in self.cache_ttl.items():
            if cache_key in self._cache_timestamps:
                last_updated = self._cache_timestamps[cache_key]
                age_hours = (current_time - last_updated).total_seconds() / 3600
                is_stale = age_hours > ttl_hours
            else:
                last_updated = datetime.min
                is_stale = True
                
            freshness_status[cache_key] = DataFreshness(
                source=cache_key,
                last_updated=last_updated,
                is_stale=is_stale,
                staleness_threshold_hours=ttl_hours
            )
        
        return freshness_status

    async def refresh_all_data(self) -> Dict[str, bool]:
        """
        Force refresh of all data sources.
        
        Returns:
            Dict mapping source names to success status
        """
        logger.info("Starting full data refresh")
        results = {}
        
        try:
            # Refresh macro indicators
            await self.get_macro_indicators(force_refresh=True)
            results["macro_indicators"] = True
        except Exception as e:
            logger.error(f"Failed to refresh macro indicators: {e}")
            results["macro_indicators"] = False
        
        try:
            # Refresh news data
            await self.get_news_signals(limit=100)
            results["news_signals"] = True
        except Exception as e:
            logger.error(f"Failed to refresh news signals: {e}")
            results["news_signals"] = False
        
        try:
            # Refresh property data
            await self.get_property_listings(segment="departamentos", limit=200)
            await self.get_property_listings(segment="campos", limit=100)
            results["property_listings"] = True
        except Exception as e:
            logger.error(f"Failed to refresh property listings: {e}")
            results["property_listings"] = False
        
        try:
            # Refresh commodity data
            await self.get_commodity_prices(days_back=90)
            results["commodity_prices"] = True
        except Exception as e:
            logger.error(f"Failed to refresh commodity prices: {e}")
            results["commodity_prices"] = False
        
        logger.info(f"Data refresh completed: {results}")
        return results

    # Private helper methods
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid based on TTL."""
        if cache_key not in self._cache or cache_key not in self._cache_timestamps:
            return False
            
        ttl_hours = self.cache_ttl.get(cache_key, 1)
        cache_age = datetime.utcnow() - self._cache_timestamps[cache_key]
        
        return cache_age.total_seconds() < ttl_hours * 3600

    async def _fetch_bcra_data(self) -> Dict[str, Any]:
        """
        Fetch live data from BCRA API, with optional FRED fallback per-field.

        Each BCRA indicator is tried first against BCRA v4. If a specific
        indicator fails and FRED has an equivalent series, we transparently
        fill that single slot from FRED so a partial BCRA outage doesn't
        collapse the whole macro response.
        """
        tasks = [
            self.bcra_client.get_exchange_rate(),
            self.bcra_client.get_reference_rate(),
            self.bcra_client.get_inflation_data(),
            self.bcra_client.get_reserves(),
            self.bcra_client.get_monetary_base(),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        exchange_rate = await self._resolve_bcra_field(
            "exchange_rate", results[0], fred_call=self.fred_client.get_exchange_rate
        )
        reference_rate = self._unwrap(results[1])
        inflation = await self._resolve_bcra_field(
            "inflation", results[2], fred_call=self.fred_client.get_inflation_annual
        )
        reserves = self._unwrap(results[3])
        monetary_base = self._unwrap(results[4])

        return {
            "exchange_rate": exchange_rate,
            "reference_rate": reference_rate,
            "inflation": inflation,
            "reserves": reserves,
            "monetary_base": monetary_base,
            "timestamp": datetime.utcnow().isoformat(),
        }

    @staticmethod
    def _unwrap(result: Any) -> Optional[Any]:
        """Return the value when the gathered task succeeded, else None."""
        return result if not isinstance(result, Exception) else None

    async def _resolve_bcra_field(
        self,
        field: str,
        bcra_result: Any,
        fred_call: Any,
    ) -> Optional[Dict[str, Any]]:
        """
        Resolve a single BCRA field, falling back to FRED on BCRA failure.

        Args:
            field: Logical field name used only for log context.
            bcra_result: The result from asyncio.gather for the BCRA call.
            fred_call: Async FRED method to call when BCRA failed.

        Returns:
            A dict {"valor", "fecha", optional "source"} or None when both
            sources are unavailable.
        """
        if not isinstance(bcra_result, Exception):
            return bcra_result

        if not self.fred_client.is_configured:
            return None

        try:
            fred_value = await fred_call()
            if fred_value is not None:
                logger.info("BCRA %s failed; filled from FRED instead", field)
                fred_value["source"] = "fred"
            return fred_value
        except Exception as exc:
            logger.warning("FRED fallback for %s also failed: %s", field, exc)
            return None

    async def _fetch_rem_data(self) -> Dict[str, Any]:
        """Fetch live data from REM API."""
        tasks = [
            self.rem_client.get_inflation_forecast(),
            self.rem_client.get_exchange_rate_forecast(),
            self.rem_client.get_gdp_forecast()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            "inflation_forecast": results[0] if not isinstance(results[0], Exception) else None,
            "exchange_rate_forecast": results[1] if not isinstance(results[1], Exception) else None,
            "gdp_forecast": results[2] if not isinstance(results[2], Exception) else None,
            "timestamp": datetime.utcnow().isoformat()
        }

    def _get_fallback_bcra_data(self) -> Dict[str, Any]:
        """Return fallback BCRA data when API is unavailable."""
        logger.warning("Using fallback BCRA data")
        return {
            "exchange_rate": {"valor": 1045.50, "fecha": "2026-01-15"},
            "reference_rate": {"valor": 32.0, "fecha": "2026-01-15"}, 
            "inflation": {"valor": 2.1, "fecha": "2025-12-31"},
            "reserves": {"valor": 27850.0, "fecha": "2026-01-15"},
            "monetary_base": {"valor": 15847000, "fecha": "2026-01-15"},
            "timestamp": datetime.utcnow().isoformat(),
            "source": "fallback"
        }

    def _get_fallback_rem_data(self) -> Dict[str, Any]:
        """Return fallback REM data when API is unavailable."""
        logger.warning("Using fallback REM data")
        return {
            "inflation_forecast": {
                "median": 15.2,
                "mean": 15.8,
                "period": "2026"
            },
            "exchange_rate_forecast": {
                "median": 1180.0,
                "mean": 1220.0,
                "period": "2026-12-31"
            },
            "gdp_forecast": {
                "median": 4.2,
                "mean": 4.5,
                "period": "2026"
            },
            "timestamp": datetime.utcnow().isoformat(),
            "source": "fallback"
        }

    def _get_fallback_macro_data(self) -> Dict[str, Any]:
        """Return minimal fallback macro data when all APIs fail."""
        logger.warning("Using minimal fallback macro data")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "bcra": self._get_fallback_bcra_data(),
            "rem": self._get_fallback_rem_data(),
            "sources": {
                "bcra_status": "fallback",
                "rem_status": "fallback",
                "warning": "All APIs unavailable, using static fallback data"
            }
        }