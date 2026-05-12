"""
Spanish sentiment analysis for Argentine financial news.

Provides sentiment scoring capabilities tailored to Spanish language
financial and real estate content with Argentine-specific terminology.
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class SentimentPolarity(Enum):
    """Sentiment polarity categories."""
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


@dataclass
class SentimentScore:
    """Sentiment analysis result."""
    polarity: SentimentPolarity
    confidence: float  # 0.0 to 1.0
    score: float  # -1.0 to +1.0
    positive_signals: List[str]
    negative_signals: List[str]
    context_modifiers: List[str]


class SpanishSentimentAnalyzer:
    """
    Spanish sentiment analyzer optimized for Argentine financial news.
    
    Uses lexicon-based approach with context-aware modifiers and
    financial domain-specific terminology.
    """
    
    def __init__(self):
        """Initialize analyzer with Spanish financial sentiment lexicons."""
        
        # Positive sentiment words for financial/real estate context
        self.positive_words = {
            # Strong positive (weight = 2.0)
            "excelente": 2.0, "extraordinario": 2.0, "excepcional": 2.0,
            "récord": 2.0, "histórico": 2.0, "boom": 2.0, "éxito": 2.0,
            "crecimiento": 1.8, "expansión": 1.8, "impulso": 1.8,
            
            # Medium positive (weight = 1.0-1.5)
            "positivo": 1.5, "favorable": 1.5, "bueno": 1.2, "mejora": 1.5,
            "aumenta": 1.3, "sube": 1.3, "crece": 1.5, "avanza": 1.3,
            "beneficio": 1.4, "ganancia": 1.4, "recuperación": 1.6,
            "estabilidad": 1.2, "confianza": 1.4, "optimismo": 1.5,
            "oportunidad": 1.3, "potencial": 1.2, "desarrollo": 1.3,
            "inversión": 1.2, "modernización": 1.3, "innovación": 1.4,
            
            # Mild positive (weight = 0.5-1.0)  
            "bien": 0.8, "estable": 0.7, "sólido": 1.0, "firme": 0.9,
            "sostenido": 0.8, "gradual": 0.6, "moderado": 0.5,
        }
        
        # Negative sentiment words
        self.negative_words = {
            # Strong negative (weight = -2.0)
            "crisis": -2.0, "colapso": -2.0, "caída": -1.8, "desplome": -2.0,
            "devastador": -2.0, "catastrófico": -2.0, "pésimo": -2.0,
            "horrible": -2.0, "terrible": -1.8, "dramático": -1.6,
            
            # Medium negative (weight = -1.0 to -1.5)
            "negativo": -1.5, "malo": -1.2, "preocupante": -1.3,
            "deterioro": -1.5, "baja": -1.3, "cae": -1.4, "reduce": -1.3,
            "pérdida": -1.4, "déficit": -1.3, "recesión": -1.8,
            "incertidumbre": -1.2, "riesgo": -1.1, "problema": -1.2,
            "dificultad": -1.1, "obstáculo": -1.2, "freno": -1.3,
            "limitación": -1.1, "restricción": -1.2, "complicación": -1.1,
            
            # Mild negative (weight = -0.5 to -1.0)
            "lento": -0.8, "débil": -0.9, "menor": -0.5, "bajo": -0.7,
            "cauteloso": -0.6, "prudente": -0.4, "conservador": -0.3,
        }
        
        # Context modifiers that change sentiment intensity
        self.intensifiers = {
            "muy": 1.5, "mucho": 1.4, "bastante": 1.3, "algo": 1.1,
            "sumamente": 1.8, "extremadamente": 2.0, "considerablemente": 1.6,
            "significativamente": 1.5, "notablemente": 1.4, "claramente": 1.3,
            "fuertemente": 1.6, "ampliamente": 1.4, "totalmente": 1.7,
        }
        
        self.diminishers = {
            "poco": 0.5, "apenas": 0.4, "ligeramente": 0.6,
            "levemente": 0.5, "parcialmente": 0.7, "relativamente": 0.8,
            "moderadamente": 0.7, "sutilmente": 0.5,
        }
        
        # Negation words that flip polarity
        self.negation_words = {
            "no", "sin", "nada", "nunca", "tampoco", "ni", "ningún", "ninguna",
            "nadie", "jamás", "carece", "falta", "ausencia"
        }
        
        # Financial domain boosters - words that increase importance in financial context
        self.financial_boosters = {
            "mercado": 1.2, "precio": 1.3, "inversión": 1.2, "economía": 1.1,
            "financiero": 1.1, "inmobiliario": 1.3, "hipotecario": 1.3,
            "crédito": 1.2, "tasa": 1.2, "inflación": 1.2, "dólar": 1.1,
            "peso": 1.1, "BCRA": 1.2, "gobierno": 1.1, "política": 1.1,
        }

    def analyze_sentiment(self, text: str, title: str = "") -> SentimentScore:
        """
        Analyze sentiment of Spanish financial text.
        
        Args:
            text: Main content to analyze
            title: Optional title (given higher weight)
            
        Returns:
            SentimentScore with polarity, confidence, and detected signals
        """
        # Combine title and text, weight title 1.5x
        if title:
            full_text = f"{title} {text}"
            title_weight = 1.5
        else:
            full_text = text
            title_weight = 1.0
            
        # Clean and tokenize text
        tokens = self._tokenize_text(full_text.lower())
        
        # Calculate sentiment scores
        scores, positive_signals, negative_signals, context_modifiers = self._calculate_scores(
            tokens, title_weight
        )
        
        # Aggregate final score
        final_score = sum(scores) / len(scores) if scores else 0.0
        final_score = max(-1.0, min(1.0, final_score))  # Clamp to [-1, 1]
        
        # Determine polarity and confidence
        polarity = self._determine_polarity(final_score)
        confidence = self._calculate_confidence(scores, len(tokens))
        
        return SentimentScore(
            polarity=polarity,
            confidence=confidence,
            score=final_score,
            positive_signals=positive_signals,
            negative_signals=negative_signals,
            context_modifiers=context_modifiers
        )

    def _tokenize_text(self, text: str) -> List[str]:
        """Clean and tokenize Spanish text."""
        # Remove punctuation but keep Spanish accents
        text = re.sub(r'[^\w\sáéíóúüñ]', ' ', text)
        # Split on whitespace and filter empty
        return [token.strip() for token in text.split() if token.strip()]

    def _calculate_scores(self, tokens: List[str], title_weight: float) -> Tuple[List[float], List[str], List[str], List[str]]:
        """Calculate sentiment scores with context awareness."""
        scores = []
        positive_signals = []
        negative_signals = []
        context_modifiers = []
        
        i = 0
        while i < len(tokens):
            token = tokens[i]
            context_multiplier = 1.0
            negated = False
            
            # Look for negation in previous 3 tokens
            for j in range(max(0, i-3), i):
                if tokens[j] in self.negation_words:
                    negated = True
                    context_modifiers.append(f"negación: {tokens[j]}")
                    break
            
            # Look for intensifiers/diminishers in next 2 tokens or previous 2
            for j in range(max(0, i-2), min(len(tokens), i+3)):
                if j != i:
                    if tokens[j] in self.intensifiers:
                        context_multiplier *= self.intensifiers[tokens[j]]
                        context_modifiers.append(f"intensificador: {tokens[j]}")
                    elif tokens[j] in self.diminishers:
                        context_multiplier *= self.diminishers[tokens[j]]
                        context_modifiers.append(f"atenuador: {tokens[j]}")
            
            # Look for financial domain boosters
            financial_boost = 1.0
            for j in range(max(0, i-2), min(len(tokens), i+3)):
                if tokens[j] in self.financial_boosters:
                    financial_boost *= self.financial_boosters[tokens[j]]
                    break
            
            # Calculate token score
            base_score = 0.0
            if token in self.positive_words:
                base_score = self.positive_words[token]
                positive_signals.append(token)
            elif token in self.negative_words:
                base_score = self.negative_words[token]
                negative_signals.append(token)
            
            if base_score != 0.0:
                # Apply context modifications
                final_score = base_score * context_multiplier * financial_boost * title_weight
                
                # Apply negation (flip polarity but maintain intensity)
                if negated:
                    final_score *= -1
                    
                scores.append(final_score)
            
            i += 1
        
        return scores, positive_signals, negative_signals, context_modifiers

    def _determine_polarity(self, score: float) -> SentimentPolarity:
        """Map continuous score to discrete polarity categories."""
        if score >= 0.6:
            return SentimentPolarity.VERY_POSITIVE
        elif score >= 0.2:
            return SentimentPolarity.POSITIVE
        elif score <= -0.6:
            return SentimentPolarity.VERY_NEGATIVE
        elif score <= -0.2:
            return SentimentPolarity.NEGATIVE
        else:
            return SentimentPolarity.NEUTRAL

    def _calculate_confidence(self, scores: List[float], text_length: int) -> float:
        """Calculate confidence based on signal strength and consistency."""
        if not scores:
            return 0.1  # Low confidence for no sentiment signals
        
        # Signal strength (number of sentiment words relative to text length)
        signal_density = len(scores) / max(text_length, 1)
        
        # Signal consistency (how much scores agree in direction)
        if len(scores) == 1:
            consistency = 1.0
        else:
            positive_count = sum(1 for s in scores if s > 0)
            negative_count = sum(1 for s in scores if s < 0)
            total_count = len(scores)
            
            # Higher consistency when signals point in same direction
            majority_count = max(positive_count, negative_count)
            consistency = majority_count / total_count
        
        # Combine factors
        confidence = min(1.0, signal_density * 3 + consistency * 0.5)
        return max(0.1, confidence)  # Minimum 10% confidence

    def batch_analyze(self, texts: List[str], titles: List[str] = None) -> List[SentimentScore]:
        """
        Analyze sentiment for multiple texts.
        
        Args:
            texts: List of content strings
            titles: Optional list of title strings (same length as texts)
            
        Returns:
            List of SentimentScore objects
        """
        if titles is None:
            titles = [""] * len(texts)
        
        return [
            self.analyze_sentiment(text, title)
            for text, title in zip(texts, titles)
        ]

    def get_sentiment_summary(self, articles: List[Dict]) -> Dict:
        """
        Get aggregate sentiment summary for a collection of articles.
        
        Args:
            articles: List of dicts with 'title' and 'content' keys
            
        Returns:
            Dict with aggregate sentiment metrics
        """
        if not articles:
            return {"average_score": 0.0, "distribution": {}, "total_articles": 0}
        
        scores = self.batch_analyze(
            [a.get("content", "") for a in articles],
            [a.get("title", "") for a in articles]
        )
        
        # Calculate aggregate metrics
        average_score = sum(s.score for s in scores) / len(scores)
        
        # Polarity distribution
        distribution = {}
        for polarity in SentimentPolarity:
            distribution[polarity.value] = sum(
                1 for s in scores if s.polarity == polarity
            ) / len(scores)
        
        return {
            "average_score": round(average_score, 3),
            "distribution": distribution,
            "total_articles": len(articles),
            "confidence": round(sum(s.confidence for s in scores) / len(scores), 3)
        }