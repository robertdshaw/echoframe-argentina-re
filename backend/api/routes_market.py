"""
Market data API routes for EchoFrame Argentina Real Estate Intelligence.

Provides endpoints for accessing live macro indicators, property listings,
and commodity prices that inform the forecasting models.
"""

import logging
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Depends, Request
from fastapi.responses import JSONResponse

from .schemas import (
    MacroIndicatorsResponse, PropertyListingsResponse, CommodityPricesResponse,
    BCRADataResponse, REMDataResponse, PropertyListing, CommodityPrice,
    MacroIndicator, REMForecast, SegmentEnum, DataFreshnessStatus
)
from services.data_pipeline import DataPipeline


logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/market", tags=["market-data"])

def get_data_pipeline(request: Request) -> DataPipeline:
    """Reuse the shared DataPipeline so its in-memory cache works."""
    dp = getattr(request.app.state, "data_pipeline", None)
    return dp if dp is not None else DataPipeline()


@router.get("/macro", response_model=MacroIndicatorsResponse)
async def get_macro_indicators(
    force_refresh: bool = Query(False, description="Force refresh of cached data"),
    data_pipeline: DataPipeline = Depends(get_data_pipeline)
):
    """
    Get comprehensive macro economic indicators.
    
    Returns live BCRA data (exchange rates, inflation, interest rates) and
    REM market expectations (inflation, exchange rate, GDP forecasts).
    """
    try:
        logger.info(f"Getting macro indicators (force_refresh: {force_refresh})")
        
        # Get macro data from pipeline
        macro_data = await data_pipeline.get_macro_indicators(force_refresh=force_refresh)
        
        # Extract BCRA data
        bcra_raw = macro_data.get("bcra", {})
        bcra_data = BCRADataResponse(
            exchange_rate=MacroIndicator(
                value=bcra_raw.get("exchange_rate", {}).get("valor", 0),
                date=bcra_raw.get("exchange_rate", {}).get("fecha", ""),
                unit="ARS per USD"
            ) if bcra_raw.get("exchange_rate") else None,
            reference_rate=MacroIndicator(
                value=bcra_raw.get("reference_rate", {}).get("valor", 0),
                date=bcra_raw.get("reference_rate", {}).get("fecha", ""),
                unit="% annual"
            ) if bcra_raw.get("reference_rate") else None,
            inflation=MacroIndicator(
                value=bcra_raw.get("inflation", {}).get("valor", 0),
                date=bcra_raw.get("inflation", {}).get("fecha", ""),
                unit="% monthly"
            ) if bcra_raw.get("inflation") else None,
            reserves=MacroIndicator(
                value=bcra_raw.get("reserves", {}).get("valor", 0),
                date=bcra_raw.get("reserves", {}).get("fecha", ""),
                unit="USD millions"
            ) if bcra_raw.get("reserves") else None,
            monetary_base=MacroIndicator(
                value=bcra_raw.get("monetary_base", {}).get("valor", 0),
                date=bcra_raw.get("monetary_base", {}).get("fecha", ""),
                unit="ARS millions"
            ) if bcra_raw.get("monetary_base") else None,
            timestamp=macro_data.get("timestamp", datetime.utcnow().isoformat()),
            source=bcra_raw.get("source", "live")
        )
        
        # Extract REM data
        rem_raw = macro_data.get("rem", {})
        rem_data = REMDataResponse(
            inflation_forecast=REMForecast(
                median=rem_raw.get("inflation_forecast", {}).get("median", 0),
                mean=rem_raw.get("inflation_forecast", {}).get("mean", 0),
                period=rem_raw.get("inflation_forecast", {}).get("period", "")
            ) if rem_raw.get("inflation_forecast") else None,
            exchange_rate_forecast=REMForecast(
                median=rem_raw.get("exchange_rate_forecast", {}).get("median", 0),
                mean=rem_raw.get("exchange_rate_forecast", {}).get("mean", 0),
                period=rem_raw.get("exchange_rate_forecast", {}).get("period", "")
            ) if rem_raw.get("exchange_rate_forecast") else None,
            gdp_forecast=REMForecast(
                median=rem_raw.get("gdp_forecast", {}).get("median", 0),
                mean=rem_raw.get("gdp_forecast", {}).get("mean", 0),
                period=rem_raw.get("gdp_forecast", {}).get("period", "")
            ) if rem_raw.get("gdp_forecast") else None,
            timestamp=macro_data.get("timestamp", datetime.utcnow().isoformat()),
            source=rem_raw.get("source", "live")
        )
        
        # Build response
        response = MacroIndicatorsResponse(
            bcra=bcra_data,
            rem=rem_data,
            sources=macro_data.get("sources", {"bcra_status": "unknown", "rem_status": "unknown"}),
            timestamp=macro_data.get("timestamp", datetime.utcnow().isoformat())
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting macro indicators: {e}")
        raise HTTPException(status_code=500, detail=f"Macro data retrieval failed: {str(e)}")


@router.get("/listings/{segment}", response_model=PropertyListingsResponse)
async def get_property_listings(
    segment: SegmentEnum,
    location: Optional[str] = Query(None, description="Filter by location (barrio for departamentos, zone for campos)"),
    limit: int = Query(50, ge=1, le=200, description="Maximum listings to return"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price filter"),
    data_pipeline: DataPipeline = Depends(get_data_pipeline)
):
    """
    Get property listings for market analysis.
    
    Returns property listings for either departamentos (Buenos Aires apartments)
    or campos (agricultural land) with optional location and price filtering.
    """
    try:
        logger.info(f"Getting {segment.value} listings (location: {location}, limit: {limit})")
        
        # Get listings from pipeline
        listings_data = await data_pipeline.get_property_listings(
            segment=segment.value,
            barrio=location,
            limit=limit * 2  # Get more to allow for price filtering
        )
        
        # Apply price filters
        filtered_listings = []
        total_prices = []
        
        for listing_raw in listings_data:
            # Extract price based on segment. Live Properati listings often
            # omit price_per_m2 (search-results page doesn't expose surface),
            # so price can legitimately be None — skip rather than crash.
            if segment == SegmentEnum.DEPARTAMENTOS:
                price = listing_raw.get("price_per_m2")
            else:
                price = listing_raw.get("price_usd_per_ha")

            if price is None or not isinstance(price, (int, float)) or price <= 0:
                # Don't apply min/max filters when there's nothing to compare.
                if min_price or max_price:
                    continue
                # But still let the listing through for the map (which uses
                # lat/lon, not price filtering) when no filter was requested.
                price_for_avg: float = 0.0
            else:
                if min_price and price < min_price:
                    continue
                if max_price and price > max_price:
                    continue
                price_for_avg = float(price)
                total_prices.append(price_for_avg)
            
            # Derive the right total / type keys per segment. Campos
            # seed entries don't carry a `price_usd` field (only
            # `price_usd_per_ha`) and use `use_type` instead of `type`,
            # which is why earlier popups showed Total $0 and Type
            # Unknown on every campos parcel.
            if segment == SegmentEnum.CAMPOS:
                hectares = float(listing_raw.get("hectares") or 0)
                per_ha = float(listing_raw.get("price_usd_per_ha") or 0)
                total_usd = (
                    listing_raw.get("price_usd")
                    if listing_raw.get("price_usd")
                    else (per_ha * hectares if per_ha and hectares else None)
                )
                property_type = (
                    listing_raw.get("use_type")
                    or listing_raw.get("type")
                    or "Unknown"
                )
            else:
                total_usd = listing_raw.get("price_usd")
                property_type = listing_raw.get("type", "Unknown")

            listing = PropertyListing(
                id=listing_raw.get("id", "unknown"),
                price_usd=total_usd,
                price_per_m2=listing_raw.get("price_per_m2") if segment == SegmentEnum.DEPARTAMENTOS else None,
                price_usd_per_ha=listing_raw.get("price_usd_per_ha") if segment == SegmentEnum.CAMPOS else None,
                location=listing_raw.get("barrio") or listing_raw.get("zone", "Unknown"),
                property_type=property_type,
                size=listing_raw.get("surface_m2") or listing_raw.get("hectares", 0),
                segment=segment,
                latitude=listing_raw.get("latitude"),
                longitude=listing_raw.get("longitude"),
                province=listing_raw.get("province"),
                partido=listing_raw.get("partido"),
            )
            filtered_listings.append(listing)
        
        # Limit final results
        filtered_listings = filtered_listings[:limit]
        
        # Calculate average price
        avg_price = sum(total_prices) / len(total_prices) if total_prices else 0.0
        
        # Build response
        response = PropertyListingsResponse(
            listings=filtered_listings,
            total_count=len(listings_data),
            segment=segment,
            location_filter=location,
            avg_price=avg_price,
            timestamp=datetime.utcnow()
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting {segment.value} listings: {e}")
        raise HTTPException(status_code=500, detail=f"Listings retrieval failed: {str(e)}")


@router.get("/commodities", response_model=CommodityPricesResponse)
async def get_commodity_prices(
    commodity: Optional[str] = Query(None, description="Filter by commodity (soy, wheat, corn)"),
    days_back: int = Query(30, ge=1, le=365, description="Number of days of historical data"),
    data_pipeline: DataPipeline = Depends(get_data_pipeline)
):
    """
    Get commodity price data for agricultural analysis.
    
    Returns MATBA-ROFEX commodity prices (soy, wheat, corn) that drive
    agricultural land value forecasts.
    """
    try:
        logger.info(f"Getting commodity prices (commodity: {commodity}, days: {days_back})")
        
        # Get commodity data from pipeline
        commodity_data = await data_pipeline.get_commodity_prices(
            commodity=commodity,
            days_back=days_back
        )
        
        # Convert to response format
        prices = []
        commodities_found = set()
        date_range = {"earliest": None, "latest": None}
        
        for price_raw in commodity_data:
            price = CommodityPrice(
                commodity=price_raw.get("commodity", "unknown"),
                price_usd_ton=price_raw.get("price_usd_ton", 0.0),
                date=price_raw.get("date", ""),
                market=price_raw.get("market", "MATBA-ROFEX")
            )
            prices.append(price)
            
            # Track commodities and date range
            commodities_found.add(price.commodity)
            
            if date_range["earliest"] is None or price.date < date_range["earliest"]:
                date_range["earliest"] = price.date
            if date_range["latest"] is None or price.date > date_range["latest"]:
                date_range["latest"] = price.date
        
        # Build response
        response = CommodityPricesResponse(
            prices=prices,
            commodities=sorted(list(commodities_found)),
            date_range={
                "earliest": date_range["earliest"] or "",
                "latest": date_range["latest"] or ""
            },
            timestamp=datetime.utcnow()
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting commodity prices: {e}")
        raise HTTPException(status_code=500, detail=f"Commodity data retrieval failed: {str(e)}")


@router.get("/freshness")
async def get_data_freshness(
    data_pipeline: DataPipeline = Depends(get_data_pipeline)
):
    """
    Get data freshness status for all market data sources.
    
    Returns information about when each data source was last updated
    and whether the data is considered stale.
    """
    try:
        logger.info("Getting data freshness status")
        
        # Get freshness status from pipeline
        freshness_data = await data_pipeline.get_data_freshness_status()
        
        # Convert to response format
        freshness_status = {}
        for source_name, freshness_info in freshness_data.items():
            freshness_status[source_name] = DataFreshnessStatus(
                source=freshness_info.source,
                last_updated=freshness_info.last_updated,
                is_stale=freshness_info.is_stale,
                staleness_threshold_hours=freshness_info.staleness_threshold_hours
            )
        
        return JSONResponse(content={
            "data_sources": {
                source: {
                    "source": status.source,
                    "last_updated": status.last_updated.isoformat(),
                    "is_stale": status.is_stale,
                    "staleness_threshold_hours": status.staleness_threshold_hours
                }
                for source, status in freshness_status.items()
            },
            "overall_status": "stale" if any(s.is_stale for s in freshness_status.values()) else "fresh",
            "checked_at": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting data freshness: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Freshness check failed: {str(e)}"}
        )


@router.post("/refresh")
async def refresh_market_data(
    data_pipeline: DataPipeline = Depends(get_data_pipeline)
):
    """
    Force refresh of all market data sources.
    
    Triggers fresh data collection from BCRA API, REM API, and
    refreshes cached property and commodity data.
    """
    try:
        logger.info("Refreshing all market data")
        
        # Trigger data refresh
        refresh_results = await data_pipeline.refresh_all_data()
        
        # Count successful refreshes
        successful_refreshes = sum(1 for success in refresh_results.values() if success)
        total_sources = len(refresh_results)
        
        return JSONResponse(content={
            "status": "completed",
            "successful_refreshes": successful_refreshes,
            "total_sources": total_sources,
            "source_results": refresh_results,
            "refresh_timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error refreshing market data: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Data refresh failed: {str(e)}"}
        )


@router.get("/bcra/variables")
async def get_bcra_variables():
    """
    Get available BCRA variables and their current values.
    
    Returns metadata about BCRA API variables that can be accessed
    for macro economic analysis.
    """
    try:
        return JSONResponse(content={
            "variables": [
                {
                    "id": 1,
                    "name": "Reservas Internacionales del BCRA",
                    "unit": "USD millions",
                    "description": "International reserves held by the central bank"
                },
                {
                    "id": 4,
                    "name": "Tipo de Cambio Minorista",
                    "unit": "ARS per USD",
                    "description": "Retail exchange rate (bank sell rate)"
                },
                {
                    "id": 5,
                    "name": "Tipo de Cambio Mayorista",
                    "unit": "ARS per USD", 
                    "description": "Wholesale exchange rate"
                },
                {
                    "id": 6,
                    "name": "Tasa BADLAR",
                    "unit": "% annual",
                    "description": "Buenos Aires Deposits of Large Amount Rate"
                },
                {
                    "id": 7,
                    "name": "Tasa TM20",
                    "unit": "% annual",
                    "description": "20-day term deposit rate"
                },
                {
                    "id": 15,
                    "name": "Base Monetaria",
                    "unit": "ARS millions",
                    "description": "Monetary base"
                },
                {
                    "id": 27,
                    "name": "Inflación mensual",
                    "unit": "% monthly",
                    "description": "Monthly consumer price inflation"
                },
                {
                    "id": 28,
                    "name": "Inflación interanual",
                    "unit": "% annual",
                    "description": "Year-over-year consumer price inflation"
                }
            ],
            "api_info": {
                "base_url": "https://api.bcra.gob.ar/estadisticas/v2.0",
                "authentication": "None required",
                "rate_limits": "Unknown - use responsibly"
            },
            "generated_at": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting BCRA variables: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve BCRA variable information")


@router.get("/health")
async def get_market_data_health():
    """
    Get health status of market data pipeline.
    
    Returns status information for API connections and data freshness.
    """
    try:
        return JSONResponse(content={
            "status": "healthy",
            "apis": {
                "bcra_api": "operational - https://api.bcra.gob.ar",
                "rem_api": "operational - https://bcra-rem-api.facujallia.workers.dev"
            },
            "data_sources": {
                "macro_indicators": "cached",
                "property_listings": "seeded",
                "commodity_prices": "seeded"
            },
            "cache_status": {
                "enabled": True,
                "ttl_hours": {
                    "bcra_data": 1,
                    "rem_data": 24,
                    "property_listings": 12,
                    "commodity_prices": 2
                }
            },
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Market data health check error: {e}")
        raise HTTPException(status_code=503, detail="Market data service temporarily unavailable")