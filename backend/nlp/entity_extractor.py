"""
Argentine entity extraction for real estate intelligence.

Identifies and extracts Argentine-specific entities from Spanish text including
neighborhoods, institutions, economic indicators, and real estate terms.
"""

import re
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class EntityType(Enum):
    """Types of entities relevant to Argentine real estate analysis."""
    NEIGHBORHOOD = "neighborhood"
    INSTITUTION = "institution" 
    ECONOMIC_INDICATOR = "economic_indicator"
    CURRENCY = "currency"
    REAL_ESTATE_TYPE = "real_estate_type"
    LOCATION = "location"
    PERSON = "person"
    ORGANIZATION = "organization"
    AGRICULTURAL_TERM = "agricultural_term"


@dataclass
class ExtractedEntity:
    """An extracted entity with metadata."""
    text: str
    entity_type: EntityType
    confidence: float
    start_position: int
    end_position: int
    normalized_form: str  # Standardized version of the entity
    context: str  # Surrounding text for disambiguation


class ArgentineEntityExtractor:
    """
    Named entity recognition for Argentine real estate and financial content.
    
    Uses rule-based pattern matching with comprehensive dictionaries of
    Argentine-specific terms, places, and institutions.
    """
    
    def __init__(self):
        """Initialize extractor with Argentine entity dictionaries."""
        
        # Buenos Aires neighborhoods (CABA)
        self.neighborhoods = {
            # Central/Premium areas
            "puerto madero": "Puerto Madero",
            "recoleta": "Recoleta", 
            "palermo": "Palermo",
            "belgrano": "Belgrano",
            "núñez": "Núñez",
            "retiro": "Retiro",
            "san telmo": "San Telmo",
            "la boca": "La Boca",
            "montserrat": "Montserrat",
            "san nicolás": "San Nicolás",
            
            # Mid-tier areas
            "caballito": "Caballito",
            "villa crespo": "Villa Crespo", 
            "almagro": "Almagro",
            "balvanera": "Balvanera",
            "barracas": "Barracas",
            "villa urquiza": "Villa Urquiza",
            "coghlan": "Coghlan",
            "saavedra": "Saavedra",
            "colegiales": "Colegiales",
            "chacarita": "Chacarita",
            
            # Outer areas
            "villa lugano": "Villa Lugano",
            "villa soldati": "Villa Soldati", 
            "nueva pompeya": "Nueva Pompeya",
            "parque avellaneda": "Parque Avellaneda",
            "flores": "Flores",
            "floresta": "Floresta",
            "liniers": "Liniers",
            "mataderos": "Mataderos",
            "parque chacabuco": "Parque Chacabuco",
            
            # Additional variants
            "palermo soho": "Palermo Soho",
            "palermo hollywood": "Palermo Hollywood",
            "villa del parque": "Villa del Parque",
            "puerto madero este": "Puerto Madero Este",
            "puerto madero oeste": "Puerto Madero Oeste",
        }
        
        # Argentine institutions and organizations
        self.institutions = {
            # Central Bank and Government
            "bcra": "Banco Central de la República Argentina",
            "banco central": "Banco Central de la República Argentina",
            "banco central de la república argentina": "Banco Central de la República Argentina",
            "ministerio de economía": "Ministerio de Economía",
            "indec": "Instituto Nacional de Estadística y Censos",
            "anses": "Administración Nacional de la Seguridad Social",
            "afip": "Administración Federal de Ingresos Públicos",
            
            # Real Estate and Construction
            "colegio de escribanos": "Colegio de Escribanos",
            "cámara argentina de la construcción": "Cámara Argentina de la Construcción",
            "uocra": "Unión Obrera de la Construcción de la República Argentina",
            
            # Financial Markets
            "byma": "Bolsas y Mercados Argentinos",
            "rofex": "Rosario Futures Exchange",
            "matba": "Mercado a Término de Buenos Aires",
            "matba-rofex": "MATBA-ROFEX",
            
            # Development Finance
            "procrear": "Programa Crédito Argentino del Bicentenario",
            "fondo nacional de habitación": "FONAVI",
            "instituto de la vivienda": "Instituto Provincial de Vivienda",
            
            # Transportation
            "subte": "Subterráneos de Buenos Aires",
            "metrobus": "Metrobus",
            "ffcc": "Ferrocarriles Argentinos",
        }
        
        # Economic indicators and financial terms
        self.economic_indicators = {
            "ipc": "Índice de Precios al Consumidor",
            "índice de precios al consumidor": "Índice de Precios al Consumidor", 
            "inflación": "Inflación",
            "tasa de interés": "Tasa de Interés",
            "tasa de política monetaria": "Tasa de Política Monetaria",
            "tipo de cambio": "Tipo de Cambio",
            "reservas internacionales": "Reservas Internacionales",
            "base monetaria": "Base Monetaria",
            "agregados monetarios": "Agregados Monetarios",
            "leliq": "Letras de Liquidez",
            "lebac": "Letras del Banco Central",
            "badlar": "Buenos Aires Deposits of Large Amount Rate",
            "tm20": "Tasa de Depósitos a Plazo Fijo",
            "uva": "Unidad de Valor Adquisitivo",
            "uvi": "Unidad de Vivienda",
            "cer": "Coeficiente de Estabilización de Referencia",
            "cvs": "Coeficiente de Variación Salarial",
            "icc": "Índice del Costo de la Construcción",
            "emae": "Estimador Mensual de Actividad Económica",
            "rigi": "Régimen de Incentivo para Grandes Inversiones",
        }
        
        # Currency terms
        self.currencies = {
            "peso": "Peso Argentino",
            "pesos": "Peso Argentino",
            "ars": "Peso Argentino", 
            "dólar": "Dólar Estadounidense",
            "dólares": "Dólar Estadounidense",
            "usd": "Dólar Estadounidense",
            "dólar blue": "Dólar Blue",
            "dólar oficial": "Dólar Oficial",
            "dólar mep": "Dólar MEP",
            "dólar ccl": "Dólar Contado con Liquidación",
            "dólar tarjeta": "Dólar Tarjeta",
            "euro": "Euro",
            "real": "Real Brasileño",
        }
        
        # Real estate property types
        self.real_estate_types = {
            "departamento": "Departamento",
            "casa": "Casa",
            "ph": "Propiedad Horizontal",
            "loft": "Loft",
            "duplex": "Duplex",
            "triplex": "Triplex",
            "monoambiente": "Monoambiente",
            "dos ambientes": "Dos Ambientes",
            "tres ambientes": "Tres Ambientes",
            "cuatro ambientes": "Cuatro Ambientes",
            "cochera": "Cochera",
            "baulera": "Baulera",
            "local comercial": "Local Comercial",
            "oficina": "Oficina",
            "galpón": "Galpón",
            "terreno": "Terreno",
            "lote": "Lote",
        }
        
        # Agricultural and campos terms
        self.agricultural_terms = {
            "campo": "Campo",
            "hectárea": "Hectárea",
            "hectáreas": "Hectárea",
            "ha": "Hectárea",
            "estancia": "Estancia",
            "establecimiento": "Establecimiento Rural",
            "soja": "Soja",
            "trigo": "Trigo", 
            "maíz": "Maíz",
            "girasol": "Girasol",
            "sorgo": "Sorgo",
            "retenciones": "Derechos de Exportación",
            "derechos de exportación": "Derechos de Exportación",
            "cosecha": "Cosecha",
            "siembra": "Siembra",
            "rindes": "Rendimiento por Hectárea",
            "ganadería": "Ganadería",
            "feedlot": "Feedlot",
            "hacienda": "Hacienda",
            "tambo": "Tambo",
            "pampa húmeda": "Pampa Húmeda",
            "núcleo maicero": "Núcleo Maicero",
        }
        
        # Argentine provinces and key cities
        self.locations = {
            "caba": "Ciudad Autónoma de Buenos Aires",
            "ciudad autónoma de buenos aires": "Ciudad Autónoma de Buenos Aires",
            "buenos aires": "Provincia de Buenos Aires",  
            "provincia de buenos aires": "Provincia de Buenos Aires",
            "córdoba": "Córdoba",
            "santa fe": "Santa Fe",
            "mendoza": "Mendoza",
            "tucumán": "Tucumán",
            "entre ríos": "Entre Ríos",
            "salta": "Salta",
            "corrientes": "Corrientes",
            "misiones": "Misiones",
            "santiago del estero": "Santiago del Estero",
            "chaco": "Chaco",
            "formosa": "Formosa",
            "la pampa": "La Pampa",
            "neuquén": "Neuquén",
            "río negro": "Río Negro",
            "chubut": "Chubut",
            "santa cruz": "Santa Cruz",
            "tierra del fuego": "Tierra del Fuego",
            "catamarca": "Catamarca",
            "la rioja": "La Rioja",
            "san juan": "San Juan",
            "san luis": "San Luis",
            "jujuy": "Jujuy",
            
            # Key agricultural regions
            "pergamino": "Pergamino",
            "junín": "Junín", 
            "rojas": "Rojas",
            "9 de julio": "9 de Julio",
            "marcos juárez": "Marcos Juárez",
            "río cuarto": "Río Cuarto",
            "venado tuerto": "Venado Tuerto",
            "rufino": "Rufino",
        }

    def extract_entities(self, text: str, context_window: int = 50) -> List[ExtractedEntity]:
        """
        Extract all entities from Spanish text.
        
        Args:
            text: Input text to analyze
            context_window: Characters of context to include around entities
            
        Returns:
            List of ExtractedEntity objects sorted by position
        """
        entities = []
        text_lower = text.lower()
        
        # Extract each entity type
        entities.extend(self._extract_by_dictionary(text, text_lower, self.neighborhoods, EntityType.NEIGHBORHOOD, context_window))
        entities.extend(self._extract_by_dictionary(text, text_lower, self.institutions, EntityType.INSTITUTION, context_window))
        entities.extend(self._extract_by_dictionary(text, text_lower, self.economic_indicators, EntityType.ECONOMIC_INDICATOR, context_window))
        entities.extend(self._extract_by_dictionary(text, text_lower, self.currencies, EntityType.CURRENCY, context_window))
        entities.extend(self._extract_by_dictionary(text, text_lower, self.real_estate_types, EntityType.REAL_ESTATE_TYPE, context_window))
        entities.extend(self._extract_by_dictionary(text, text_lower, self.locations, EntityType.LOCATION, context_window))
        entities.extend(self._extract_by_dictionary(text, text_lower, self.agricultural_terms, EntityType.AGRICULTURAL_TERM, context_window))
        
        # Extract numeric patterns (prices, percentages, etc.)
        entities.extend(self._extract_numeric_patterns(text, context_window))
        
        # Remove overlapping entities (keep highest confidence)
        entities = self._remove_overlaps(entities)
        
        # Sort by position
        entities.sort(key=lambda e: e.start_position)
        
        return entities

    def _extract_by_dictionary(
        self, 
        original_text: str, 
        text_lower: str, 
        entity_dict: Dict[str, str], 
        entity_type: EntityType,
        context_window: int
    ) -> List[ExtractedEntity]:
        """Extract entities using dictionary lookup with fuzzy matching."""
        entities = []
        
        for term_lower, normalized_form in entity_dict.items():
            # Find all occurrences of this term
            pattern = re.compile(re.escape(term_lower), re.IGNORECASE)
            
            for match in pattern.finditer(text_lower):
                start_pos = match.start()
                end_pos = match.end()
                
                # Get original case text
                original_text_span = original_text[start_pos:end_pos]
                
                # Extract context
                context_start = max(0, start_pos - context_window)
                context_end = min(len(original_text), end_pos + context_window)
                context = original_text[context_start:context_end]
                
                # Calculate confidence based on exact match vs fuzzy
                if original_text_span.lower() == term_lower:
                    confidence = 1.0
                else:
                    confidence = 0.85  # Slightly lower for case differences
                
                # Boost confidence for well-known terms
                if entity_type in [EntityType.INSTITUTION, EntityType.ECONOMIC_INDICATOR]:
                    confidence = min(1.0, confidence * 1.1)
                
                entities.append(ExtractedEntity(
                    text=original_text_span,
                    entity_type=entity_type,
                    confidence=confidence,
                    start_position=start_pos,
                    end_position=end_pos,
                    normalized_form=normalized_form,
                    context=context.strip()
                ))
        
        return entities

    def _extract_numeric_patterns(self, text: str, context_window: int) -> List[ExtractedEntity]:
        """Extract numeric patterns relevant to real estate (prices, percentages, etc.)."""
        entities = []
        
        # Price patterns (pesos and dollars)
        price_patterns = [
            (r'\$\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)', "price_ars"),
            (r'USD?\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)', "price_usd"),
            (r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*dólares?', "price_usd"),
            (r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*pesos?', "price_ars"),
        ]
        
        for pattern, price_type in price_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                start_pos = match.start()
                end_pos = match.end()
                
                context_start = max(0, start_pos - context_window)
                context_end = min(len(text), end_pos + context_window)
                context = text[context_start:context_end]
                
                entities.append(ExtractedEntity(
                    text=match.group(0),
                    entity_type=EntityType.CURRENCY,
                    confidence=0.9,
                    start_position=start_pos,
                    end_position=end_pos,
                    normalized_form=f"{price_type}:{match.group(1)}",
                    context=context.strip()
                ))
        
        # Percentage patterns
        percentage_pattern = r'(\d{1,2}(?:[.,]\d{1,2})?)\s*%'
        for match in re.finditer(percentage_pattern, text):
            start_pos = match.start()
            end_pos = match.end()
            
            context_start = max(0, start_pos - context_window)
            context_end = min(len(text), end_pos + context_window)
            context = text[context_start:context_end]
            
            entities.append(ExtractedEntity(
                text=match.group(0),
                entity_type=EntityType.ECONOMIC_INDICATOR,
                confidence=0.8,
                start_position=start_pos,
                end_position=end_pos,
                normalized_form=f"percentage:{match.group(1)}",
                context=context.strip()
            ))
        
        return entities

    def _remove_overlaps(self, entities: List[ExtractedEntity]) -> List[ExtractedEntity]:
        """Remove overlapping entities, keeping the one with highest confidence."""
        if len(entities) <= 1:
            return entities
        
        # Sort by start position
        entities.sort(key=lambda e: e.start_position)
        
        filtered = []
        for entity in entities:
            # Check if this entity overlaps with any already accepted
            overlaps = False
            for accepted in filtered:
                if (entity.start_position < accepted.end_position and 
                    entity.end_position > accepted.start_position):
                    # There's an overlap - keep the higher confidence one
                    if entity.confidence > accepted.confidence:
                        filtered.remove(accepted)
                        break
                    else:
                        overlaps = True
                        break
            
            if not overlaps:
                filtered.append(entity)
        
        return filtered

    def get_entity_summary(self, entities: List[ExtractedEntity]) -> Dict:
        """Get summary statistics for extracted entities."""
        if not entities:
            return {"total": 0, "by_type": {}, "high_confidence": 0}
        
        by_type = {}
        high_confidence = 0
        
        for entity in entities:
            entity_type = entity.entity_type.value
            by_type[entity_type] = by_type.get(entity_type, 0) + 1
            
            if entity.confidence >= 0.8:
                high_confidence += 1
        
        return {
            "total": len(entities),
            "by_type": by_type,
            "high_confidence": high_confidence,
            "confidence_rate": high_confidence / len(entities)
        }

    def filter_entities(
        self, 
        entities: List[ExtractedEntity], 
        entity_types: Optional[List[EntityType]] = None,
        min_confidence: float = 0.0
    ) -> List[ExtractedEntity]:
        """Filter entities by type and confidence threshold."""
        filtered = entities
        
        if entity_types:
            filtered = [e for e in filtered if e.entity_type in entity_types]
        
        if min_confidence > 0.0:
            filtered = [e for e in filtered if e.confidence >= min_confidence]
        
        return filtered