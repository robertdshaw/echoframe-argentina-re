"""
Natural Language Processing module for EchoFrame Argentina Real Estate Intelligence.

This module provides Spanish language processing capabilities for analyzing
Argentine real estate and agricultural market signals from news sources.
"""

from .signal_classifier import SignalClassifier
from .sentiment import SpanishSentimentAnalyzer
from .entity_extractor import ArgentineEntityExtractor

__all__ = [
    "SignalClassifier",
    "SpanishSentimentAnalyzer", 
    "ArgentineEntityExtractor"
]