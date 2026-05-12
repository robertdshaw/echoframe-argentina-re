"""
Properati live scraper for EchoFrame Argentina Real Estate Intelligence.

Properati publishes Buenos Aires apartment listings at:
    https://www.properati.com.ar/s/{barrio-slug}/departamento/venta

Their search results page returns server-rendered HTML where each listing
is an <article class="snippet"> with stable, scrapable child classes:

    article.snippet[data-idanuncio][data-url]
      .title       — listing title
      .price       — "USD 197.000"  (Argentine thousands separator)
      .location    — "Caballito, Capital Federal"
      .properties__bedrooms / .properties__bathrooms / amenity spans
      .published-date

Surface (m²) is NOT shown on the search list view — it lives behind the
detail page. This scraper omits it for departamentos rather than firing
N+1 follow-up requests; the seed corpus carries it for offline use.

Properati does not cover agricultural land (campos) at search-page level —
that URL returns 404 — so this client is departamentos-only. Callers fall
back to PropertySeeder for campos.

The scraper is best-effort:
  * Cloudflare may serve 403 if the UA looks bot-like.
  * Page DOM can change.
On any failure the caller is expected to fall back to PropertySeeder.
"""

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import hashlib
import httpx
from bs4 import BeautifulSoup, Tag


logger = logging.getLogger(__name__)

# Barrio centroid coordinates (WGS84) for CABA. Used to approximate
# coordinates for listings scraped from search results — Properati's
# search page doesn't expose precise lat/lon, only the barrio name.
# A small deterministic jitter is added per listing id so multiple
# listings in the same barrio don't all stack on the same pixel.
_BARRIO_CENTROIDS: Dict[str, Tuple[float, float]] = {
    "palermo":               (-34.5875, -58.4240),
    "palermo soho":          (-34.5870, -58.4310),
    "palermo hollywood":     (-34.5790, -58.4350),
    "palermo chico":         (-34.5780, -58.4115),
    "recoleta":              (-34.5875, -58.3970),
    "belgrano":              (-34.5610, -58.4570),
    "belgrano c":            (-34.5610, -58.4540),
    "belgrano r":            (-34.5615, -58.4690),
    "nuñez":                 (-34.5468, -58.4630),
    "núñez":                 (-34.5468, -58.4630),
    "nunez":                 (-34.5468, -58.4630),
    "caballito":             (-34.6189, -58.4400),
    "almagro":               (-34.6105, -58.4220),
    "boedo":                 (-34.6260, -58.4170),
    "balvanera":             (-34.6095, -58.4012),
    "san telmo":             (-34.6210, -58.3735),
    "monserrat":             (-34.6125, -58.3815),
    "puerto madero":         (-34.6118, -58.3650),
    "retiro":                (-34.5905, -58.3760),
    "san nicolás":           (-34.6045, -58.3805),
    "san nicolas":           (-34.6045, -58.3805),
    "villa crespo":          (-34.6005, -58.4395),
    "villa urquiza":         (-34.5740, -58.4895),
    "villa pueyrredón":      (-34.5765, -58.4990),
    "villa pueyrredon":      (-34.5765, -58.4990),
    "villa del parque":      (-34.6080, -58.4870),
    "villa devoto":          (-34.6010, -58.5130),
    "villa lugano":          (-34.6755, -58.4730),
    "villa luro":            (-34.6360, -58.4910),
    "villa ortúzar":         (-34.5810, -58.4640),
    "villa ortuzar":         (-34.5810, -58.4640),
    "saavedra":              (-34.5530, -58.4805),
    "coghlan":               (-34.5630, -58.4810),
    "colegiales":            (-34.5740, -58.4505),
    "chacarita":             (-34.5900, -58.4515),
    "parque chacabuco":      (-34.6320, -58.4350),
    "parque patricios":      (-34.6385, -58.4030),
    "flores":                (-34.6320, -58.4640),
    "floresta":              (-34.6310, -58.4830),
    "agronomía":             (-34.5945, -58.4810),
    "agronomia":             (-34.5945, -58.4810),
    "paternal":              (-34.5945, -58.4640),
    "barracas":              (-34.6450, -58.3795),
    "la boca":               (-34.6350, -58.3625),
    "constitución":          (-34.6260, -58.3835),
    "constitucion":          (-34.6260, -58.3835),
    "boca":                  (-34.6350, -58.3625),
    "mataderos":             (-34.6595, -58.4985),
    "liniers":               (-34.6440, -58.5210),
    "versalles":             (-34.6260, -58.5180),
    "monte castro":          (-34.6175, -58.5060),
    "vélez sársfield":       (-34.6275, -58.5050),
    "velez sarsfield":       (-34.6275, -58.5050),
    "parque avellaneda":     (-34.6485, -58.4790),
    "nueva pompeya":         (-34.6510, -58.4170),
    "san cristóbal":         (-34.6235, -58.4030),
    "san cristobal":         (-34.6235, -58.4030),
    "capital federal":       (-34.6087, -58.4173),  # fallback to city centre
}


def _coords_for_barrio(barrio: Optional[str], listing_id: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Resolve approximate (lat, lon) for a listing.

    Falls back gracefully:
      1. Exact-match the barrio in the centroid table.
      2. Try the first word of the barrio (e.g. 'Palermo Hollywood' → 'palermo').
      3. Return (None, None) if no match — the map will skip the marker.

    Jitter is deterministic per listing id (hash → ±0.004°, ~400m) so
    repeated requests place the same listing in the same spot.
    """
    if not barrio:
        return None, None
    key = barrio.strip().lower()
    coords = _BARRIO_CENTROIDS.get(key)
    if coords is None:
        first_word = key.split()[0] if key.split() else ""
        coords = _BARRIO_CENTROIDS.get(first_word)
    if coords is None:
        return None, None
    lat, lon = coords
    h = hashlib.md5(listing_id.encode("utf-8")).digest()
    # Map two bytes to [-0.004, +0.004] each → ~440m max offset.
    lat_jitter = ((h[0] - 128) / 128.0) * 0.004
    lon_jitter = ((h[1] - 128) / 128.0) * 0.004
    return round(lat + lat_jitter, 6), round(lon + lon_jitter, 6)

# Realistic desktop UA so Cloudflare's edge doesn't 403 us. The short-UA
# variant was blocked during probing.
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/127.0 Safari/537.36"
)

_BARRIO_SLUG_OVERRIDES = {
    "puerto madero": "puerto-madero",
    "villa urquiza": "villa-urquiza",
    "villa crespo": "villa-crespo",
    "la boca": "la-boca",
    "villa lugano": "villa-lugano",
}

_PRICE_RX = re.compile(r"USD\s*([\d.]+)", re.IGNORECASE)
_INT_RX = re.compile(r"(\d+(?:[.,]\d+)?)")


class ProperatiScraper:
    """Async scraper for Properati Argentina departamento search results."""

    BASE_URL = "https://www.properati.com.ar"

    def __init__(
        self,
        timeout: float = 15.0,
        polite_delay_seconds: float = 0.6,
    ) -> None:
        self.timeout = timeout
        self.polite_delay = polite_delay_seconds

    async def get_listings(
        self,
        barrio: Optional[str] = None,
        limit: int = 30,
        max_pages: int = 2,
    ) -> List[Dict[str, Any]]:
        """
        Fetch CABA apartment listings from Properati search pages.

        Args:
            barrio: Neighborhood filter; if None, the CABA-wide search is used.
            limit: Soft cap on returned listings.
            max_pages: How many search pages to walk (≈30 listings per page).

        Returns:
            List of listing dicts shaped like PropertySeeder output:
            id, barrio, type, price_usd, price_per_m2, listing_date, ...
            with `surface_m2` and `rooms` left as None when absent.

        Raises:
            RuntimeError: on any network or parse failure. Callers catch
                and fall back to PropertySeeder.
        """
        slug = self._barrio_slug(barrio)
        url_base = f"{self.BASE_URL}/s/{slug}/departamento/venta"
        collected: List[Dict[str, Any]] = []

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                headers={"User-Agent": _USER_AGENT},
                follow_redirects=True,
            ) as client:
                for page in range(1, max_pages + 1):
                    url = url_base if page == 1 else f"{url_base}?pagina={page}"
                    resp = await client.get(url)
                    if resp.status_code == 404:
                        # Barrio doesn't exist on Properati; bail rather
                        # than retry.
                        raise RuntimeError(f"Properati: 404 for slug '{slug}'")
                    resp.raise_for_status()

                    page_listings = self._parse_listings(resp.text)
                    if not page_listings:
                        # No more listings — stop paginating.
                        break
                    collected.extend(page_listings)

                    if len(collected) >= limit:
                        break

                    # Be polite to their edge so we don't get rate-limited.
                    await asyncio.sleep(self.polite_delay)
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Properati HTTP error: {exc}") from exc

        return collected[:limit]

    @staticmethod
    def _barrio_slug(barrio: Optional[str]) -> str:
        if not barrio:
            return "capital-federal"
        key = barrio.strip().lower()
        if key in _BARRIO_SLUG_OVERRIDES:
            return _BARRIO_SLUG_OVERRIDES[key]
        return key.replace(" ", "-")

    @staticmethod
    def _parse_listings(html: str) -> List[Dict[str, Any]]:
        """Extract listing dicts from a search-results page."""
        soup = BeautifulSoup(html, "lxml")
        articles = soup.find_all("article", class_="snippet")
        if not articles:
            return []

        results: List[Dict[str, Any]] = []
        for article in articles:
            listing = ProperatiScraper._parse_one(article)
            if listing is not None:
                results.append(listing)
        return results

    @staticmethod
    def _parse_one(article: Tag) -> Optional[Dict[str, Any]]:
        listing_id = article.get("data-idanuncio")
        listing_url = article.get("data-url")
        if not listing_id:
            return None

        price_usd = ProperatiScraper._extract_price(article)
        location_text = ProperatiScraper._text_of(article, ".location")
        barrio = location_text.split(",")[0].strip() if location_text else None

        title = ProperatiScraper._text_of(article, "a.title, .title")
        bedrooms = ProperatiScraper._extract_int(
            ProperatiScraper._text_of(article, ".properties__bedrooms")
        )
        bathrooms = ProperatiScraper._extract_float(
            ProperatiScraper._text_of(article, ".properties__bathrooms")
        )
        listing_date = ProperatiScraper._text_of(article, ".published-date")

        # Properati's search page doesn't expose precise coordinates, but
        # the barrio name is reliable. Resolve to a centroid (+ small
        # deterministic jitter) so the listing has a map position.
        lat, lon = _coords_for_barrio(barrio, str(listing_id))

        return {
            "id": f"properati_{listing_id}",
            "barrio": barrio,
            "type": "departamento",
            "price_usd": price_usd,
            "surface_m2": None,
            "price_per_m2": None,
            "rooms": bedrooms,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "latitude": lat,
            "longitude": lon,
            "listing_date": listing_date,
            "is_new_construction": None,
            "building_age_years": None,
            "title": title,
            "url": listing_url,
            "data_source": "properati.com.ar",
        }

    @staticmethod
    def _text_of(article: Tag, selector: str) -> Optional[str]:
        el = article.select_one(selector)
        return el.get_text(strip=True) if el else None

    @staticmethod
    def _extract_price(article: Tag) -> Optional[float]:
        text = ProperatiScraper._text_of(article, ".price")
        if not text:
            return None
        match = _PRICE_RX.search(text)
        if not match:
            return None
        # Properati formats USD with periods as thousands separator
        # (e.g. "USD 197.000" = 197000). No decimals on listing prices.
        digits = match.group(1).replace(".", "").replace(",", "")
        try:
            return float(digits)
        except ValueError:
            return None

    @staticmethod
    def _extract_int(text: Optional[str]) -> Optional[int]:
        if not text:
            return None
        match = _INT_RX.search(text)
        return int(match.group(1).split(",")[0].split(".")[0]) if match else None

    @staticmethod
    def _extract_float(text: Optional[str]) -> Optional[float]:
        if not text:
            return None
        match = _INT_RX.search(text)
        if not match:
            return None
        return float(match.group(1).replace(",", "."))
