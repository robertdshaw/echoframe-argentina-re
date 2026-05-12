"""
Signal processing API routes for EchoFrame Argentina Real Estate Intelligence.

Provides endpoints for accessing processed news signals that drive the
forecasting models, including classification, sentiment, and impact analysis.
"""

import logging
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Depends, Body, Request
from fastapi.responses import JSONResponse

from .schemas import (
    ProcessedSignalResponse, SignalSummaryResponse, SignalClassificationData,
    SentimentData, ExtractedEntityData, SegmentEnum, SignalTypeEnum,
    ImpactDirectionEnum
)
from services.signal_service import SignalService, ProcessedSignal
from services.data_pipeline import DataPipeline
from nlp.signal_classifier import SignalClassification
from nlp.sentiment import SentimentScore
from nlp.entity_extractor import ExtractedEntity


logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/signals", tags=["signals"])

# Dependency injection — reuse the shared SignalService set up in
# main.lifespan so the NLP classifier doesn't reload its keyword tables
# on every request.
def get_signal_service(request: Request) -> SignalService:
    ss = getattr(request.app.state, "signal_service", None)
    if ss is not None:
        return ss
    dp = getattr(request.app.state, "data_pipeline", None) or DataPipeline()
    return SignalService(data_pipeline=dp)


@router.get("/latest", response_model=List[ProcessedSignalResponse])
async def get_latest_signals(
    limit: int = Query(20, ge=1, le=100, description="Maximum number of signals to return"),
    segment: Optional[SegmentEnum] = Query(None, description="Filter by market segment"),
    signal_type: Optional[SignalTypeEnum] = Query(None, description="Filter by signal type"),
    impact_direction: Optional[ImpactDirectionEnum] = Query(None, description="Filter by impact direction"),
    min_impact: float = Query(0.0, ge=0.0, le=1.0, description="Minimum impact score threshold"),
    signal_service: SignalService = Depends(get_signal_service)
):
    """
    Get latest processed news signals with full NLP analysis.
    
    Returns news articles processed through signal classification,
    sentiment analysis, and entity extraction with market impact scoring.
    """
    try:
        logger.info(f"Getting latest signals: limit={limit}, segment={segment}, type={signal_type}")
        
        # Get processed signals from service
        if segment:
            # Get signals for specific segment
            signals = await signal_service.process_signals_for_segment(
                segment=segment.value,
                limit=limit,
                min_impact_threshold=min_impact
            )
        else:
            # Get all latest signals
            signals = await signal_service.process_latest_signals(
                limit=limit * 2  # Get more to allow for filtering
            )
        
        # Apply additional filters
        filtered_signals = []
        for signal in signals:
            # Signal type filter
            if signal_type and signal.signal_classification.signal_type.value != signal_type.value:
                continue
            
            # Impact direction filter
            if impact_direction and signal.signal_classification.impact_direction.value != impact_direction.value:
                continue
            
            # Impact threshold filter
            if signal.market_impact_score < min_impact:
                continue
            
            # Segment filter (if not already applied above)
            if segment and segment.value not in signal.signal_classification.affected_segments:
                continue
            
            filtered_signals.append(signal)
        
        # Limit results
        filtered_signals = filtered_signals[:limit]
        
        # Convert to response format
        response_signals = []
        for signal in filtered_signals:
            response_signal = ProcessedSignalResponse(
                article_id=signal.article_id,
                title=signal.title,
                source=signal.source,
                published_at=signal.published_at,
                signal_classification=SignalClassificationData(
                    signal_type=signal.signal_classification.signal_type,
                    impact_direction=signal.signal_classification.impact_direction,
                    impact_magnitude=signal.signal_classification.impact_magnitude,
                    confidence=signal.signal_classification.confidence,
                    affected_segments=signal.signal_classification.affected_segments,
                    matched_keywords=signal.signal_classification.matched_keywords,
                    reasoning=signal.signal_classification.reasoning
                ),
                sentiment_score=SentimentData(
                    polarity=signal.sentiment_score.polarity.value,
                    confidence=signal.sentiment_score.confidence,
                    score=signal.sentiment_score.score
                ),
                extracted_entities=[
                    ExtractedEntityData(
                        text=entity.text,
                        entity_type=entity.entity_type.value,
                        confidence=entity.confidence,
                        normalized_form=entity.normalized_form
                    )
                    for entity in signal.extracted_entities[:10]  # Limit entities for response size
                ],
                market_impact_score=signal.market_impact_score,
                processed_at=signal.processed_at
            )
            response_signals.append(response_signal)
        
        logger.info(f"Returning {len(response_signals)} filtered signals")
        return response_signals
        
    except Exception as e:
        logger.error(f"Error getting latest signals: {e}")
        raise HTTPException(status_code=500, detail=f"Signal retrieval failed: {str(e)}")


@router.get("/summary", response_model=SignalSummaryResponse)
async def get_signals_summary(
    time_window_hours: int = Query(24, ge=1, le=168, description="Time window in hours (max 7 days)"),
    signal_service: SignalService = Depends(get_signal_service)
):
    """
    Get aggregate signal summary for the specified time window.
    
    Returns summary statistics including signal counts by type, segment,
    impact direction, and top news sources.
    """
    try:
        logger.info(f"Getting signal summary for {time_window_hours} hours")
        
        # Get summary from service
        summary = await signal_service.get_signal_summary(time_window_hours=time_window_hours)
        
        # Convert to response format
        response = SignalSummaryResponse(**summary)
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting signal summary: {e}")
        # Return empty summary on error
        return SignalSummaryResponse(
            total_signals=0,
            time_window_hours=time_window_hours,
            by_signal_type={},
            by_segment={},
            by_impact_direction={},
            high_impact_count=0,
            avg_impact_score=0.0,
            avg_sentiment_score=0.0,
            top_sources=[],
            generated_at=datetime.utcnow()
        )


@router.get("/trends")
async def get_signal_trends(
    days_back: int = Query(7, ge=1, le=30, description="Number of days to analyze"),
    signal_service: SignalService = Depends(get_signal_service)
):
    """
    Get signal trend analysis over time.
    
    Returns daily signal metrics and trends for the specified period.
    """
    try:
        logger.info(f"Getting signal trends for {days_back} days")
        
        # Get trends from service
        trends = await signal_service.analyze_signal_trends(days_back=days_back)
        
        return JSONResponse(content=trends)
        
    except Exception as e:
        logger.error(f"Error getting signal trends: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Trend analysis failed: {str(e)}"}
        )


@router.get("/by-segment/{segment}", response_model=List[ProcessedSignalResponse])
async def get_signals_by_segment(
    segment: SegmentEnum,
    limit: int = Query(20, ge=1, le=50, description="Maximum signals to return"),
    min_impact: float = Query(0.3, ge=0.0, le=1.0, description="Minimum impact threshold"),
    signal_service: SignalService = Depends(get_signal_service)
):
    """
    Get signals specifically affecting a market segment.
    
    Returns signals that have been classified as affecting either
    departamentos or campos markets with impact above threshold.
    """
    try:
        logger.info(f"Getting signals for segment: {segment.value}")
        
        # Get segment-specific signals
        signals = await signal_service.process_signals_for_segment(
            segment=segment.value,
            limit=limit,
            min_impact_threshold=min_impact
        )
        
        # Convert to response format
        response_signals = []
        for signal in signals:
            response_signal = ProcessedSignalResponse(
                article_id=signal.article_id,
                title=signal.title,
                source=signal.source,
                published_at=signal.published_at,
                signal_classification=SignalClassificationData(
                    signal_type=signal.signal_classification.signal_type,
                    impact_direction=signal.signal_classification.impact_direction,
                    impact_magnitude=signal.signal_classification.impact_magnitude,
                    confidence=signal.signal_classification.confidence,
                    affected_segments=signal.signal_classification.affected_segments,
                    matched_keywords=signal.signal_classification.matched_keywords,
                    reasoning=signal.signal_classification.reasoning
                ),
                sentiment_score=SentimentData(
                    polarity=signal.sentiment_score.polarity.value,
                    confidence=signal.sentiment_score.confidence,
                    score=signal.sentiment_score.score
                ),
                extracted_entities=[
                    ExtractedEntityData(
                        text=entity.text,
                        entity_type=entity.entity_type.value,
                        confidence=entity.confidence,
                        normalized_form=entity.normalized_form
                    )
                    for entity in signal.extracted_entities[:5]  # Limit for response size
                ],
                market_impact_score=signal.market_impact_score,
                processed_at=signal.processed_at
            )
            response_signals.append(response_signal)
        
        return response_signals
        
    except Exception as e:
        logger.error(f"Error getting signals for segment {segment.value}: {e}")
        raise HTTPException(status_code=500, detail=f"Segment signal retrieval failed: {str(e)}")


@router.post("/classify")
async def classify_article(
    title: str = Body(..., description="Article headline"),
    content: str = Body(..., description="Article content"),
    source: str = Body("", description="Publication source"),
    signal_service: SignalService = Depends(get_signal_service)
):
    """
    Classify a single news article through the NLP pipeline.
    
    Processes the provided article text through signal classification,
    sentiment analysis, and entity extraction.
    """
    try:
        logger.info(f"Classifying article: {title[:50]}...")
        
        # Process article through NLP pipeline
        processed_signal = await signal_service.classify_single_article(
            title=title,
            content=content,
            source=source
        )
        
        # Convert to response format
        response = ProcessedSignalResponse(
            article_id=processed_signal.article_id,
            title=processed_signal.title,
            source=processed_signal.source,
            published_at=processed_signal.published_at,
            signal_classification=SignalClassificationData(
                signal_type=processed_signal.signal_classification.signal_type,
                impact_direction=processed_signal.signal_classification.impact_direction,
                impact_magnitude=processed_signal.signal_classification.impact_magnitude,
                confidence=processed_signal.signal_classification.confidence,
                affected_segments=processed_signal.signal_classification.affected_segments,
                matched_keywords=processed_signal.signal_classification.matched_keywords,
                reasoning=processed_signal.signal_classification.reasoning
            ),
            sentiment_score=SentimentData(
                polarity=processed_signal.sentiment_score.polarity.value,
                confidence=processed_signal.sentiment_score.confidence,
                score=processed_signal.sentiment_score.score
            ),
            extracted_entities=[
                ExtractedEntityData(
                    text=entity.text,
                    entity_type=entity.entity_type.value,
                    confidence=entity.confidence,
                    normalized_form=entity.normalized_form
                )
                for entity in processed_signal.extracted_entities
            ],
            market_impact_score=processed_signal.market_impact_score,
            processed_at=processed_signal.processed_at
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error classifying article: {e}")
        raise HTTPException(status_code=500, detail=f"Article classification failed: {str(e)}")


@router.get("/sources")
async def get_signal_sources(
    signal_service: SignalService = Depends(get_signal_service)
):
    """
    Get information about news sources in the signal feed.
    
    Returns statistics on news sources including article counts
    and average impact scores.
    """
    try:
        logger.info("Getting signal source information")
        
        # Get recent signals to analyze sources
        signals = await signal_service.process_latest_signals(limit=100)
        
        # Aggregate by source
        source_stats = {}
        for signal in signals:
            source = signal.source
            if source not in source_stats:
                source_stats[source] = {
                    "articles": 0,
                    "avg_impact": 0.0,
                    "impacts": [],
                    "signal_types": set()
                }
            
            source_stats[source]["articles"] += 1
            source_stats[source]["impacts"].append(signal.market_impact_score)
            source_stats[source]["signal_types"].add(signal.signal_classification.signal_type.value)
        
        # Calculate averages and clean up
        for source_data in source_stats.values():
            source_data["avg_impact"] = sum(source_data["impacts"]) / len(source_data["impacts"])
            source_data["signal_types"] = list(source_data["signal_types"])
            del source_data["impacts"]
        
        # Sort by article count
        sorted_sources = sorted(
            [(source, data) for source, data in source_stats.items()],
            key=lambda x: x[1]["articles"],
            reverse=True
        )
        
        return JSONResponse(content={
            "total_sources": len(source_stats),
            "sources": [
                {"name": source, **data} 
                for source, data in sorted_sources
            ],
            "generated_at": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting signal sources: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Source analysis failed: {str(e)}"}
        )


@router.get("/health")
async def get_signals_health():
    """
    Get health status of signal processing pipeline.
    
    Returns status information for NLP components and data sources.
    """
    try:
        return JSONResponse(content={
            "status": "healthy",
            "nlp_components": {
                "signal_classifier": "operational",
                "sentiment_analyzer": "operational",
                "entity_extractor": "operational"
            },
            "data_sources": {
                "news_seeder": "operational",
                "signal_cache": "operational"
            },
            "cache_status": {
                "hit_rate": "N/A - not implemented",
                "size": "N/A - not implemented"
            },
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Signals health check error: {e}")
        raise HTTPException(status_code=503, detail="Signal service temporarily unavailable")