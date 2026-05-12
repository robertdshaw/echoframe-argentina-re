"""
Signal processing service for news classification and impact analysis.

Processes news articles through NLP pipeline to extract market signals
that feed into the Bayesian forecasting models.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import asyncio

from nlp.signal_classifier import SignalClassifier, SignalClassification
from nlp.sentiment import SpanishSentimentAnalyzer, SentimentScore
from nlp.entity_extractor import ArgentineEntityExtractor, ExtractedEntity
from nlp.relevance_filter import filter_argentina_relevant
from .data_pipeline import DataPipeline


logger = logging.getLogger(__name__)


@dataclass
class ProcessedSignal:
    """A news article processed through the full NLP pipeline."""
    article_id: str
    title: str
    source: str
    published_at: str
    signal_classification: SignalClassification
    sentiment_score: SentimentScore
    extracted_entities: List[ExtractedEntity]
    market_impact_score: float
    processed_at: datetime


class SignalService:
    """
    Service for processing news articles into actionable market signals.
    
    Coordinates the NLP pipeline to classify signals, analyze sentiment,
    extract entities, and calculate market impact scores for forecasting models.
    """
    
    def __init__(self, data_pipeline: Optional[DataPipeline] = None):
        """Initialize signal service with NLP components."""
        self.data_pipeline = data_pipeline or DataPipeline()
        
        # NLP components
        self.signal_classifier = SignalClassifier()
        self.sentiment_analyzer = SpanishSentimentAnalyzer()
        self.entity_extractor = ArgentineEntityExtractor()
        
        # Processing cache
        self._signal_cache = {}
        self._cache_timestamps = {}
        self.cache_ttl_hours = 2  # Cache processed signals for 2 hours

    async def process_latest_signals(
        self,
        limit: int = 50,
        category_filter: Optional[str] = None,
        force_refresh: bool = False
    ) -> List[ProcessedSignal]:
        """
        Process latest news articles into market signals.
        
        Args:
            limit: Maximum number of articles to process
            category_filter: Filter by article category
            force_refresh: Skip cache and reprocess articles
            
        Returns:
            List of ProcessedSignal objects sorted by impact score
        """
        cache_key = f"latest_signals_{limit}_{category_filter}"
        
        if not force_refresh and self._is_cache_valid(cache_key):
            logger.info("Returning cached processed signals")
            return self._signal_cache[cache_key]
        
        logger.info(f"Processing {limit} latest news signals")
        
        try:
            # Pull a wider raw pool than `limit` because the relevance
            # filter typically drops ~30–50% of the live news feed (foreign
            # celebrity, sports, generic global macro). Without the
            # over-fetch the dashboard would render thin after denoise.
            articles = await self.data_pipeline.get_news_signals(
                limit=max(limit * 2, 60),
                category=category_filter,
            )

            # Stage 1 of the denoise pipeline: positive-allowlist filter
            # that keeps only Argentina-domestic headlines before we burn
            # cycles on classification + sentiment + entity extraction.
            # Stage 2 (LLM dual-scoring) ships separately to keep cost
            # tracking infrastructure isolated.
            relevant, dropped = filter_argentina_relevant(articles)
            if dropped:
                logger.info(
                    "Relevance filter dropped %d/%d off-topic articles",
                    dropped,
                    len(articles),
                )
            articles = relevant[:limit]

            # Process articles through NLP pipeline
            processed_signals = await self._process_articles_batch(articles)
            
            # Sort by market impact score (descending)
            processed_signals.sort(key=lambda s: s.market_impact_score, reverse=True)
            
            # Cache results
            self._signal_cache[cache_key] = processed_signals
            self._cache_timestamps[cache_key] = datetime.utcnow()
            
            logger.info(f"Processed {len(processed_signals)} signals, top impact: {processed_signals[0].market_impact_score:.3f}")
            
            return processed_signals
            
        except Exception as e:
            logger.error(f"Error processing latest signals: {e}")
            return []

    async def process_signals_for_segment(
        self,
        segment: str,
        limit: int = 20,
        min_impact_threshold: float = 0.3
    ) -> List[ProcessedSignal]:
        """
        Get processed signals specifically affecting a market segment.
        
        Args:
            segment: "departamentos" or "campos"
            limit: Maximum signals to return
            min_impact_threshold: Minimum impact score threshold
            
        Returns:
            List of ProcessedSignal objects for the segment
        """
        cache_key = f"segment_signals_{segment}_{limit}_{min_impact_threshold}"
        
        if self._is_cache_valid(cache_key):
            return self._signal_cache[cache_key]
        
        try:
            # Get all latest signals
            all_signals = await self.process_latest_signals(limit=100)
            
            # Filter for segment and impact threshold
            segment_signals = []
            for signal in all_signals:
                if (segment in signal.signal_classification.affected_segments and
                    signal.market_impact_score >= min_impact_threshold):
                    segment_signals.append(signal)
            
            # Limit results
            segment_signals = segment_signals[:limit]
            
            # Cache results
            self._signal_cache[cache_key] = segment_signals
            self._cache_timestamps[cache_key] = datetime.utcnow()
            
            return segment_signals
            
        except Exception as e:
            logger.error(f"Error processing signals for {segment}: {e}")
            return []

    async def get_signal_summary(
        self,
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get aggregate signal summary for the specified time window.
        
        Args:
            time_window_hours: Time window for signal aggregation
            
        Returns:
            Dict with signal summary statistics
        """
        try:
            # Process recent signals
            signals = await self.process_latest_signals(limit=100)
            
            # Filter by time window
            cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
            recent_signals = [
                s for s in signals 
                if s.processed_at >= cutoff_time
            ]
            
            if not recent_signals:
                return self._get_empty_summary()
            
            # Calculate aggregate metrics
            summary = {
                "total_signals": len(recent_signals),
                "time_window_hours": time_window_hours,
                
                # By signal type
                "by_signal_type": self._aggregate_by_signal_type(recent_signals),
                
                # By market segment
                "by_segment": self._aggregate_by_segment(recent_signals),
                
                # By impact direction
                "by_impact_direction": self._aggregate_by_impact_direction(recent_signals),
                
                # High impact signals (>0.7)
                "high_impact_count": len([s for s in recent_signals if s.market_impact_score > 0.7]),
                
                # Average scores
                "avg_impact_score": sum(s.market_impact_score for s in recent_signals) / len(recent_signals),
                "avg_sentiment_score": sum(s.sentiment_score.score for s in recent_signals) / len(recent_signals),
                
                # Top sources
                "top_sources": self._get_top_sources(recent_signals, limit=5),
                
                # Generated timestamp
                "generated_at": datetime.utcnow().isoformat()
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating signal summary: {e}")
            return self._get_empty_summary()

    async def analyze_signal_trends(
        self,
        days_back: int = 7
    ) -> Dict[str, Any]:
        """
        Analyze signal trends over time.
        
        Args:
            days_back: Number of days to analyze
            
        Returns:
            Dict with trend analysis
        """
        try:
            # Get extended signal history (this would ideally come from a database)
            signals = await self.process_latest_signals(limit=200)
            
            # Group signals by day
            daily_groups = {}
            for signal in signals:
                date_key = signal.processed_at.date().isoformat()
                if date_key not in daily_groups:
                    daily_groups[date_key] = []
                daily_groups[date_key].append(signal)
            
            # Calculate daily metrics
            daily_trends = {}
            for date_key, day_signals in daily_groups.items():
                daily_trends[date_key] = {
                    "total_signals": len(day_signals),
                    "avg_impact": sum(s.market_impact_score for s in day_signals) / len(day_signals),
                    "avg_sentiment": sum(s.sentiment_score.score for s in day_signals) / len(day_signals),
                    "positive_signals": len([s for s in day_signals if s.signal_classification.impact_direction.value == "positive"]),
                    "negative_signals": len([s for s in day_signals if s.signal_classification.impact_direction.value == "negative"])
                }
            
            return {
                "period_days": days_back,
                "daily_trends": daily_trends,
                "total_days_analyzed": len(daily_trends),
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing signal trends: {e}")
            return {"error": str(e)}

    async def classify_single_article(
        self,
        title: str,
        content: str,
        source: str = "",
        article_id: Optional[str] = None
    ) -> ProcessedSignal:
        """
        Process a single article through the full NLP pipeline.
        
        Args:
            title: Article headline
            content: Article body text
            source: Publication source
            article_id: Optional article identifier
            
        Returns:
            ProcessedSignal object
        """
        try:
            # Run NLP components in parallel
            classification_task = asyncio.create_task(
                self._classify_article_async(title, content, source)
            )
            sentiment_task = asyncio.create_task(
                self._analyze_sentiment_async(title, content)
            )
            entities_task = asyncio.create_task(
                self._extract_entities_async(f"{title} {content}")
            )
            
            classification, sentiment, entities = await asyncio.gather(
                classification_task, sentiment_task, entities_task
            )
            
            # Calculate market impact score
            market_impact_score = self._calculate_market_impact(
                classification, sentiment, entities
            )
            
            # Create processed signal
            processed_signal = ProcessedSignal(
                article_id=article_id or f"manual_{datetime.utcnow().timestamp()}",
                title=title,
                source=source,
                published_at=datetime.utcnow().isoformat(),
                signal_classification=classification,
                sentiment_score=sentiment,
                extracted_entities=entities,
                market_impact_score=market_impact_score,
                processed_at=datetime.utcnow()
            )
            
            return processed_signal
            
        except Exception as e:
            logger.error(f"Error processing single article: {e}")
            raise

    # Private helper methods
    
    async def _process_articles_batch(self, articles: List[Dict]) -> List[ProcessedSignal]:
        """Process multiple articles through NLP pipeline."""
        processed_signals = []
        
        # Process in batches to avoid overwhelming the system
        batch_size = 10
        for i in range(0, len(articles), batch_size):
            batch = articles[i:i + batch_size]
            
            # Process batch in parallel
            tasks = []
            for article in batch:
                task = self._process_single_article(article)
                tasks.append(task)
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Collect successful results
            for result in batch_results:
                if isinstance(result, ProcessedSignal):
                    processed_signals.append(result)
                elif isinstance(result, Exception):
                    logger.error(f"Error processing article: {result}")
        
        return processed_signals

    async def _process_single_article(self, article: Dict) -> ProcessedSignal:
        """Process a single article through the NLP pipeline."""
        title = article.get("title", "")
        content = article.get("summary", article.get("content", ""))
        source = article.get("source", "")
        
        # Run NLP components
        classification = self.signal_classifier.classify_article(title, content, source)
        sentiment = self.sentiment_analyzer.analyze_sentiment(content, title)
        entities = self.entity_extractor.extract_entities(f"{title} {content}")
        
        # Calculate market impact
        market_impact_score = self._calculate_market_impact(classification, sentiment, entities)
        
        return ProcessedSignal(
            article_id=article.get("id", f"unknown_{datetime.utcnow().timestamp()}"),
            title=title,
            source=source,
            published_at=article.get("published_at", datetime.utcnow().isoformat()),
            signal_classification=classification,
            sentiment_score=sentiment,
            extracted_entities=entities,
            market_impact_score=market_impact_score,
            processed_at=datetime.utcnow()
        )

    async def _classify_article_async(self, title: str, content: str, source: str) -> SignalClassification:
        """Async wrapper for signal classification."""
        return self.signal_classifier.classify_article(title, content, source)

    async def _analyze_sentiment_async(self, title: str, content: str) -> SentimentScore:
        """Async wrapper for sentiment analysis."""
        return self.sentiment_analyzer.analyze_sentiment(content, title)

    async def _extract_entities_async(self, text: str) -> List[ExtractedEntity]:
        """Async wrapper for entity extraction."""
        return self.entity_extractor.extract_entities(text)

    def _calculate_market_impact(
        self,
        classification: SignalClassification,
        sentiment: SentimentScore,
        entities: List[ExtractedEntity]
    ) -> float:
        """Calculate overall market impact score from NLP components."""
        # Base impact from signal classification
        base_impact = classification.impact_magnitude * classification.confidence
        
        # Sentiment adjustment
        sentiment_multiplier = 1.0 + (abs(sentiment.score) * sentiment.confidence)
        
        # Entity relevance bonus
        entity_bonus = 0.0
        relevant_entity_types = ["institution", "economic_indicator", "currency", "neighborhood"]
        relevant_entities = [
            e for e in entities 
            if e.entity_type.value in relevant_entity_types and e.confidence > 0.8
        ]
        entity_bonus = min(0.3, len(relevant_entities) * 0.05)  # Up to 30% bonus
        
        # Signal type importance weights
        signal_weights = {
            "credit_policy": 1.2,
            "exchange_rate": 1.1,
            "inflation": 1.0,
            "construction": 0.9,
            "regulation": 1.1,
            "agricultural": 1.0,
            "investment": 1.0,
            "infrastructure": 0.8
        }
        signal_weight = signal_weights.get(classification.signal_type.value, 1.0)
        
        # Calculate final score
        final_score = (base_impact * sentiment_multiplier + entity_bonus) * signal_weight
        
        # Clamp to [0, 1] range
        return min(1.0, max(0.0, final_score))

    def _aggregate_by_signal_type(self, signals: List[ProcessedSignal]) -> Dict[str, int]:
        """Aggregate signals by signal type."""
        type_counts = {}
        for signal in signals:
            signal_type = signal.signal_classification.signal_type.value
            type_counts[signal_type] = type_counts.get(signal_type, 0) + 1
        return type_counts

    def _aggregate_by_segment(self, signals: List[ProcessedSignal]) -> Dict[str, int]:
        """Aggregate signals by affected market segment."""
        segment_counts = {}
        for signal in signals:
            for segment in signal.signal_classification.affected_segments:
                segment_counts[segment] = segment_counts.get(segment, 0) + 1
        return segment_counts

    def _aggregate_by_impact_direction(self, signals: List[ProcessedSignal]) -> Dict[str, int]:
        """Aggregate signals by impact direction."""
        direction_counts = {}
        for signal in signals:
            direction = signal.signal_classification.impact_direction.value
            direction_counts[direction] = direction_counts.get(direction, 0) + 1
        return direction_counts

    def _get_top_sources(self, signals: List[ProcessedSignal], limit: int = 5) -> List[Dict[str, Any]]:
        """Get top news sources by signal count."""
        source_counts = {}
        for signal in signals:
            source = signal.source
            if source not in source_counts:
                source_counts[source] = {"count": 0, "avg_impact": 0.0, "impacts": []}
            source_counts[source]["count"] += 1
            source_counts[source]["impacts"].append(signal.market_impact_score)
        
        # Calculate average impact per source
        for source_data in source_counts.values():
            source_data["avg_impact"] = sum(source_data["impacts"]) / len(source_data["impacts"])
            del source_data["impacts"]  # Remove raw impacts to clean up response
        
        # Sort by signal count and return top sources
        top_sources = sorted(
            [(source, data) for source, data in source_counts.items()],
            key=lambda x: x[1]["count"],
            reverse=True
        )
        
        return [
            {"source": source, **data} 
            for source, data in top_sources[:limit]
        ]

    def _get_empty_summary(self) -> Dict[str, Any]:
        """Return empty summary structure."""
        return {
            "total_signals": 0,
            "by_signal_type": {},
            "by_segment": {},
            "by_impact_direction": {},
            "high_impact_count": 0,
            "avg_impact_score": 0.0,
            "avg_sentiment_score": 0.0,
            "top_sources": [],
            "generated_at": datetime.utcnow().isoformat()
        }

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid."""
        if cache_key not in self._cache_timestamps:
            return False
        
        cache_age = datetime.utcnow() - self._cache_timestamps[cache_key]
        return cache_age.total_seconds() < self.cache_ttl_hours * 3600