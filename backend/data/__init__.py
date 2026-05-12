"""Data clients and seeded data providers for EchoFrame Argentina RE."""

from .bcra_client import BCRAClient
from .rem_client import REMClient
from .fred_client import FREDClient
from .news_seeder import NewsSeeder
from .newsdata_client import NewsDataClient
from .property_seeder import PropertySeeder
from .properati_scraper import ProperatiScraper
from .commodity_seeder import CommoditySeeder

__all__ = [
    "BCRAClient",
    "REMClient",
    "FREDClient",
    "NewsSeeder",
    "NewsDataClient",
    "PropertySeeder",
    "ProperatiScraper",
    "CommoditySeeder",
]
