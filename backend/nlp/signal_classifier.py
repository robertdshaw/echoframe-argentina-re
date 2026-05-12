"""
Signal classifier for Argentine real estate news using Spanish keyword matching.

This module implements a rule-based classifier that categorizes Spanish news articles
into market signal types that feed the Bayesian forecasting models.
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class SignalType(Enum):
    """Market signal categories for Argentine real estate intelligence."""
    CREDIT_POLICY = "credit_policy"
    EXCHANGE_RATE = "exchange_rate" 
    INFLATION = "inflation"
    CONSTRUCTION = "construction"
    REGULATION = "regulation"
    AGRICULTURAL = "agricultural"
    INVESTMENT = "investment"
    INFRASTRUCTURE = "infrastructure"


class ImpactDirection(Enum):
    """Impact direction on real estate prices."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


@dataclass
class SignalClassification:
    """Classification result for a news article."""
    signal_type: SignalType
    impact_direction: ImpactDirection
    impact_magnitude: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    affected_segments: List[str]  # ["departamentos", "campos"] 
    matched_keywords: List[str]
    reasoning: str


class SignalClassifier:
    """
    Rule-based classifier for Argentine real estate market signals.
    
    Uses Spanish keyword matching with weighted scoring to determine
    signal type, impact direction, and magnitude from news articles.
    """
    
    def __init__(self):
        """Initialize classifier with Spanish keyword dictionaries."""
        # Signal type keywords with weights
        self.signal_keywords = {
            SignalType.CREDIT_POLICY: {
                "high": ["tasa de referencia", "política monetaria", "créditos hipotecarios", "líneas UVA"],
                "medium": ["tasa", "BCRA", "hipotecario", "crédito", "UVA", "préstamo", "financiamiento"],
                "low": ["banco", "financiero", "interés"]
            },
            SignalType.EXCHANGE_RATE: {
                "high": ["tipo de cambio oficial", "dólar blue", "brecha cambiaria", "devaluación", "cepo cambiario"],
                "medium": ["dólar", "tipo de cambio", "devaluación", "cepo", "blue", "peso", "divisa"],
                "low": ["USD", "ARS", "moneda", "cambio"]
            },
            SignalType.INFLATION: {
                "high": ["índice de precios al consumidor", "inflación mensual", "inflación interanual"],
                "medium": ["inflación", "IPC", "precios", "costo de vida", "canasta básica"],
                "low": ["precio", "costo", "valor", "aumento"]
            },
            SignalType.CONSTRUCTION: {
                "high": ["permisos de construcción", "índice del costo de la construcción", "ICC"],
                "medium": ["construcción", "permisos", "obras", "INDEC ICC", "cemento", "ladrillo"],
                "low": ["construir", "obra", "material", "edificio"]
            },
            SignalType.REGULATION: {
                "high": ["blanqueo de capitales", "régimen de regularización", "DNU inmobiliario"],
                "medium": ["regulación", "ley", "normativa", "blanqueo", "DNU", "decreto", "impuesto"],
                "low": ["legal", "jurídico", "norma", "reglamento"]
            },
            SignalType.AGRICULTURAL: {
                "high": ["derechos de exportación", "retenciones agrícolas", "precio de la soja"],
                "medium": ["campo", "soja", "trigo", "retenciones", "sequía", "cosecha", "agro", "MATBA"],
                "low": ["agricultura", "rural", "hectárea", "producción"]
            },
            SignalType.INVESTMENT: {
                "high": ["inversión extranjera directa", "flujos de capital", "RIGI"],
                "medium": ["inversión", "FDI", "capital", "flujos", "extranjero", "fondos"],
                "low": ["invertir", "inversor", "financiero"]
            },
            SignalType.INFRASTRUCTURE: {
                "high": ["extensión de subte", "autopista ribereña", "tren San Martín"],
                "medium": ["subte", "autopista", "infraestructura", "desarrollo", "transporte", "conectividad"],
                "low": ["obra pública", "proyecto", "urbano"]
            }
        }
        
        # Positive impact indicators
        self.positive_keywords = {
            "strong": ["aumenta", "sube", "incrementa", "mejora", "crece", "expande", "potencia", "impulsa"],
            "medium": ["favorable", "positivo", "bueno", "beneficia", "estimula", "promueve", "facilita"],
            "mild": ["estable", "mantiene", "sostiene", "consolida"]
        }
        
        # Negative impact indicators  
        self.negative_keywords = {
            "strong": ["cae", "baja", "reduce", "colapsa", "crisis", "deteriora", "plomea", "frena"],
            "medium": ["negativo", "malo", "perjudica", "obstaculiza", "limita", "restringe", "complica"],
            "mild": ["incertidumbre", "cautela", "preocupación", "riesgo"]
        }
        
        # Source credibility weights
        self.source_weights = {
            # Tier 1 - High credibility financial outlets
            "ámbito financiero": 1.0,
            "bae negocios": 1.0,
            "el cronista": 1.0,
            "cronista comercial": 1.0,
            "iprofesional": 0.9,
            
            # Tier 2 - Major newspapers with economic sections
            "la nación": 0.8,
            "clarín": 0.8,
            "infobae": 0.7,
            "perfil": 0.7,
            
            # Tier 3 - Other sources
            "página/12": 0.6,
            "default": 0.5
        }
        
        # Segment relevance patterns
        self.segment_patterns = {
            "departamentos": [
                "departamento", "vivienda", "inmueble", "propiedad", "caba", "buenos aires",
                "palermo", "recoleta", "belgrano", "caballito", "barrio", "m2", "metro cuadrado"
            ],
            "campos": [
                "campo", "hectárea", "rural", "agro", "agricultural", "tierra", "estancia",
                "producción", "cosecha", "sembrado", "ganadería", "pampa húmeda"
            ]
        }

    def classify_article(
        self, 
        title: str, 
        content: str, 
        source: str = "",
        category: Optional[str] = None
    ) -> SignalClassification:
        """
        Classify a news article into market signal type and impact assessment.
        
        Args:
            title: Article headline in Spanish
            content: Article body text in Spanish  
            source: Publication source name
            category: Pre-assigned category if available
            
        Returns:
            SignalClassification with type, direction, magnitude, and reasoning
        """
        # Combine title and content, weight title 2x
        full_text = f"{title} {title} {content}".lower()
        
        # Determine signal type
        signal_type, type_confidence, matched_keywords = self._classify_signal_type(full_text)
        
        # Determine impact direction and magnitude
        impact_direction, impact_magnitude = self._assess_impact(full_text, signal_type)
        
        # Determine affected segments
        affected_segments = self._identify_segments(full_text)
        
        # Apply source credibility adjustment
        source_weight = self._get_source_weight(source.lower())
        final_magnitude = min(1.0, impact_magnitude * source_weight)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(
            signal_type, impact_direction, matched_keywords, source, affected_segments
        )
        
        return SignalClassification(
            signal_type=signal_type,
            impact_direction=impact_direction,
            impact_magnitude=final_magnitude,
            confidence=type_confidence,
            affected_segments=affected_segments,
            matched_keywords=matched_keywords,
            reasoning=reasoning
        )

    def _classify_signal_type(self, text: str) -> Tuple[SignalType, float, List[str]]:
        """Classify signal type using weighted keyword matching."""
        scores = {}
        all_matches = {}
        
        for signal_type, keyword_groups in self.signal_keywords.items():
            score = 0
            matches = []
            
            # High importance keywords (weight = 3)
            for keyword in keyword_groups["high"]:
                count = len(re.findall(re.escape(keyword), text))
                if count > 0:
                    score += count * 3
                    matches.extend([keyword] * count)
            
            # Medium importance keywords (weight = 2)  
            for keyword in keyword_groups["medium"]:
                count = len(re.findall(re.escape(keyword), text))
                if count > 0:
                    score += count * 2
                    matches.extend([keyword] * count)
                    
            # Low importance keywords (weight = 1)
            for keyword in keyword_groups["low"]:
                count = len(re.findall(re.escape(keyword), text))
                if count > 0:
                    score += count * 1
                    matches.extend([keyword] * count)
            
            scores[signal_type] = score
            all_matches[signal_type] = matches
        
        # Find best match
        if not scores or max(scores.values()) == 0:
            # Default to investment if no clear signals
            return SignalType.INVESTMENT, 0.1, []
            
        best_type = max(scores.keys(), key=lambda k: scores[k])
        best_score = scores[best_type]
        total_score = sum(scores.values())
        confidence = best_score / total_score if total_score > 0 else 0.1
        
        return best_type, min(confidence, 1.0), list(set(all_matches[best_type]))

    def _assess_impact(self, text: str, signal_type: SignalType) -> Tuple[ImpactDirection, float]:
        """Assess impact direction and magnitude from text sentiment."""
        positive_score = 0
        negative_score = 0
        
        # Score positive indicators
        for weight_category, keywords in self.positive_keywords.items():
            multiplier = {"strong": 3, "medium": 2, "mild": 1}[weight_category]
            for keyword in keywords:
                count = len(re.findall(re.escape(keyword), text))
                positive_score += count * multiplier
        
        # Score negative indicators
        for weight_category, keywords in self.negative_keywords.items():
            multiplier = {"strong": 3, "medium": 2, "mild": 1}[weight_category]
            for keyword in keywords:
                count = len(re.findall(re.escape(keyword), text))
                negative_score += count * multiplier
        
        # Determine direction
        if positive_score > negative_score * 1.2:  # Slight bias toward positive
            direction = ImpactDirection.POSITIVE
            magnitude = min(1.0, positive_score / 10.0)  # Normalize to 0-1
        elif negative_score > positive_score * 1.2:
            direction = ImpactDirection.NEGATIVE
            magnitude = min(1.0, negative_score / 10.0)
        else:
            direction = ImpactDirection.NEUTRAL
            magnitude = 0.2  # Low but non-zero for neutral signals
            
        # Signal-specific magnitude adjustments
        if signal_type in [SignalType.CREDIT_POLICY, SignalType.EXCHANGE_RATE]:
            magnitude *= 1.2  # These have higher impact on real estate
        elif signal_type == SignalType.INFRASTRUCTURE:
            magnitude *= 0.8   # More gradual impact
            
        return direction, min(1.0, magnitude)

    def _identify_segments(self, text: str) -> List[str]:
        """Identify which real estate segments are affected."""
        segments = []
        
        for segment, keywords in self.segment_patterns.items():
            for keyword in keywords:
                if keyword in text:
                    segments.append(segment)
                    break  # Don't double-count segment
        
        # Default to both if no specific segments identified
        if not segments:
            segments = ["departamentos", "campos"]
            
        return list(set(segments))  # Remove duplicates

    def _get_source_weight(self, source_lower: str) -> float:
        """Get credibility weight for news source."""
        for source_key, weight in self.source_weights.items():
            if source_key in source_lower:
                return weight
        return self.source_weights["default"]

    def _generate_reasoning(
        self, 
        signal_type: SignalType, 
        impact_direction: ImpactDirection,
        matched_keywords: List[str],
        source: str,
        affected_segments: List[str]
    ) -> str:
        """Generate human-readable reasoning for the classification."""
        direction_text = {
            ImpactDirection.POSITIVE: "positivo",
            ImpactDirection.NEGATIVE: "negativo", 
            ImpactDirection.NEUTRAL: "neutral"
        }[impact_direction]
        
        segment_text = ", ".join(affected_segments)
        keywords_text = ", ".join(matched_keywords[:3])  # Show top 3 keywords
        
        return (f"Clasificado como {signal_type.value} con impacto {direction_text} "
                f"en {segment_text}. Palabras clave: {keywords_text}. "
                f"Fuente: {source}")

    def batch_classify(self, articles: List[Dict]) -> List[SignalClassification]:
        """
        Classify multiple articles in batch.
        
        Args:
            articles: List of article dicts with 'title', 'content', 'source' keys
            
        Returns:
            List of SignalClassification objects
        """
        return [
            self.classify_article(
                title=article.get("title", ""),
                content=article.get("content", ""),
                source=article.get("source", ""),
                category=article.get("category")
            )
            for article in articles
        ]