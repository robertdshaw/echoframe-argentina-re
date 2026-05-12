"""
Configuration management for EchoFrame Argentina Real Estate Intelligence backend.

Manages environment variables, API settings, and application configuration
with proper validation and defaults for different deployment environments.
"""

import os
import logging
from typing import Optional, List, Dict, Any
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Application settings with environment variable support.
    
    Uses Pydantic BaseSettings for automatic environment variable loading,
    validation, and type conversion with sensible defaults for development.
    """
    
    # Application settings
    app_name: str = Field("EchoFrame Argentina RE Intelligence", description="Application name")
    app_version: str = Field("1.0.0", description="Application version")
    environment: str = Field("demo", description="Environment (demo, development, production)")
    debug: bool = Field(False, description="Enable debug mode")
    
    # API settings
    api_host: str = Field("0.0.0.0", description="API server host")
    api_port: int = Field(8000, description="API server port")
    api_prefix: str = Field("/api/v1", description="API URL prefix")
    cors_origins: List[str] = Field(
        ["http://localhost:3000", "http://localhost:5173"],
        description="CORS allowed origins"
    )
    
    # BCRA API settings (free, no authentication required).
    # v2 and v3 of the endpoint are deprecated as of 2026 — BCRA explicitly
    # returns "Método correspondiente a la v2/v3 ha sido deprecado."
    # v4 is the current public statistics surface.
    bcra_api_base_url: str = Field(
        "https://api.bcra.gob.ar/estadisticas/v4.0",
        description="BCRA API base URL"
    )
    # Per-request timeout AND retry budget kept tight so a flaky BCRA
    # call can't blow past a frontend request budget. The data pipeline
    # falls back to cached/seeded values when this fails.
    bcra_api_timeout: int = Field(6, description="BCRA per-request timeout seconds")
    bcra_api_retries: int = Field(2, description="BCRA retry attempts (each backs off)")
    bcra_cache_ttl_hours: int = Field(1, description="BCRA data cache TTL")
    
    # REM API settings (free, no authentication required)  
    rem_api_base_url: str = Field(
        "https://bcra-rem-api.facujallia.workers.dev",
        description="REM API base URL"
    )
    rem_api_timeout: int = Field(30, description="REM API timeout seconds")
    rem_cache_ttl_hours: int = Field(24, description="REM data cache TTL")
    
    # Optional API keys (for production deployment)
    newsdata_api_key: Optional[str] = Field(None, description="NewsData.io API key (optional)")
    fred_api_key: Optional[str] = Field(None, description="FRED (St. Louis Fed) API key — used as BCRA fallback")
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key (optional)")
    anthropic_api_key: Optional[str] = Field(None, description="Anthropic API key for narrative generation")
    narrative_model: str = Field("claude-sonnet-4-6", description="Claude model used for narrative generation")
    narrative_cache_ttl_minutes: int = Field(20, description="How long generated narratives stay cached")

    # FRED API settings (free, requires key)
    fred_api_base_url: str = Field(
        "https://api.stlouisfed.org/fred",
        description="FRED API base URL",
    )
    fred_api_timeout: int = Field(20, description="FRED API timeout seconds")
    
    # Model settings
    model_cache_ttl_minutes: int = Field(15, description="Model prediction cache TTL")
    enable_behavioral_adjustments: bool = Field(True, description="Enable Prospect Theory adjustments")
    prospect_theory_lambda: float = Field(2.25, description="Loss aversion parameter for Argentina")
    
    # HMM settings
    hmm_n_states: int = Field(3, description="Number of HMM regime states")
    hmm_covariance_type: str = Field("full", description="HMM covariance type")
    hmm_max_iter: int = Field(100, description="HMM max training iterations")
    
    # Bayesian model settings
    bayesian_n_samples: int = Field(2000, description="MCMC samples for Bayesian inference")
    bayesian_chains: int = Field(2, description="Number of MCMC chains")
    bayesian_tune: int = Field(1000, description="MCMC tuning steps")
    
    # Data pipeline settings
    max_concurrent_requests: int = Field(10, description="Max concurrent API requests")
    request_delay_seconds: float = Field(0.1, description="Delay between API requests")
    
    # Cache settings
    cache_enabled: bool = Field(True, description="Enable in-memory caching")
    cache_max_size_mb: int = Field(100, description="Max cache size in MB")
    
    # Seed data settings
    seed_data_path: str = Field("data/seeds", description="Path to seed data files")
    news_articles_count: int = Field(200, description="Number of news articles in seed data")
    property_listings_count: int = Field(500, description="Number of property listings in seed data")
    
    # Logging settings
    log_level: str = Field("INFO", description="Logging level")
    log_format: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string"
    )
    
    # Security settings
    secret_key: str = Field(
        "echoframe-argentina-demo-secret-key-change-in-production",
        description="Secret key for sessions/JWT"
    )
    allowed_hosts: List[str] = Field(["*"], description="Allowed host headers")
    
    # Performance settings
    max_workers: int = Field(4, description="Max worker processes/threads")
    keepalive_timeout: int = Field(65, description="Keep-alive timeout seconds")
    
    # External service timeouts
    external_api_timeout: int = Field(30, description="Default external API timeout")
    external_api_retries: int = Field(3, description="Default external API retries")
    
    # Feature flags
    enable_live_apis: bool = Field(True, description="Enable live BCRA/REM API calls")
    enable_nlp_processing: bool = Field(True, description="Enable NLP signal processing")
    enable_regime_detection: bool = Field(True, description="Enable HMM regime detection")
    enable_scenario_analysis: bool = Field(True, description="Enable scenario endpoints")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "env_prefix": ""
    }
    
    @field_validator("environment")
    def validate_environment(cls, v):
        """Validate environment setting."""
        valid_environments = ["demo", "development", "staging", "production"]
        if v not in valid_environments:
            raise ValueError(f"Environment must be one of {valid_environments}")
        return v
    
    @field_validator("cors_origins")
    def validate_cors_origins(cls, v):
        """Validate CORS origins format."""
        for origin in v:
            if not (origin.startswith("http://") or origin.startswith("https://") or origin == "*"):
                raise ValueError(f"Invalid CORS origin format: {origin}")
        return v
    
    @field_validator("log_level")
    def validate_log_level(cls, v):
        """Validate logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v
    
    @field_validator("prospect_theory_lambda")
    def validate_lambda(cls, v):
        """Validate Prospect Theory lambda parameter."""
        if not (0.5 <= v <= 5.0):
            raise ValueError("Prospect Theory lambda must be between 0.5 and 5.0")
        return v
    
    def get_database_url(self) -> str:
        """
        Get database URL (currently not used as demo uses in-memory storage).
        
        Returns:
            Database connection string (placeholder for future use)
        """
        # For the demo, we use in-memory storage only
        # In production, this would return a proper database URL
        return "sqlite:///:memory:"
    
    def get_redis_url(self) -> Optional[str]:
        """
        Get Redis URL for caching (currently not used in demo).
        
        Returns:
            Redis connection string or None if not configured
        """
        redis_url = os.getenv("REDIS_URL")
        return redis_url
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment in ["demo", "development"]
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"
    
    def get_cors_settings(self) -> Dict[str, Any]:
        """Get CORS configuration for FastAPI."""
        return {
            "allow_origins": self.cors_origins,
            "allow_credentials": True,
            "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["*"],
        }
    
    def get_api_metadata(self) -> Dict[str, Any]:
        """Get API metadata for OpenAPI documentation."""
        return {
            "title": self.app_name,
            "version": self.app_version,
            "description": """
EchoFrame Argentina Real Estate Intelligence API

This API provides probabilistic forecasts for Argentine real estate markets using:
- Bayesian ensemble models for price prediction
- Hidden Markov Models for regime detection  
- Prospect Theory behavioral adjustments
- Spanish NLP for news signal processing
- Live BCRA and REM market data integration

Key features:
- Buenos Aires departamentos (apartment) forecasts
- Agricultural land (campos) price predictions
- What-if scenario analysis
- Market regime detection and transition probabilities
- Real-time news signal classification and sentiment analysis

All forecasts include uncertainty quantification with confidence intervals.
            """.strip(),
            "contact": {
                "name": "EchoFrame Intelligence",
                "url": "https://echoframe.ai",
                "email": "info@echoframe.ai"
            },
            "license_info": {
                "name": "Proprietary",
                "identifier": "LicenseRef-EchoFrame-Commercial"
            },
            "tags_metadata": [
                {
                    "name": "forecast",
                    "description": "Real estate price forecasting endpoints"
                },
                {
                    "name": "signals",
                    "description": "News signal processing and analysis"
                },
                {
                    "name": "market-data",
                    "description": "Live market data and indicators"
                },
                {
                    "name": "scenarios",
                    "description": "What-if scenario analysis tools"
                }
            ]
        }
    
    def setup_logging(self) -> None:
        """Configure application logging."""
        logging.basicConfig(
            level=getattr(logging, self.log_level),
            format=self.log_format,
            handlers=[
                logging.StreamHandler(),
                # In production, add file handler
            ]
        )
        
        # Set external library log levels
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        
        if self.is_development():
            # More verbose logging in development
            logging.getLogger("uvicorn").setLevel(logging.INFO)
        else:
            # Less verbose in production
            logging.getLogger("uvicorn").setLevel(logging.WARNING)


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached application settings.
    
    Uses LRU cache to avoid repeatedly parsing environment variables.
    The cache is invalidated when the process restarts.
    
    Returns:
        Settings instance with current configuration
    """
    return Settings()


# Export settings instance for easy importing
settings = get_settings()

# Configure logging when module is imported
settings.setup_logging()

logger.info(f"EchoFrame Argentina RE Intelligence API - Environment: {settings.environment}")
logger.info(f"BCRA API: {settings.bcra_api_base_url}")
logger.info(f"REM API: {settings.rem_api_base_url}")
logger.info(f"Live APIs enabled: {settings.enable_live_apis}")
logger.info(f"NLP processing enabled: {settings.enable_nlp_processing}")
logger.info(f"Behavioral adjustments enabled: {settings.enable_behavioral_adjustments}")

# Validate critical settings on import
if settings.environment == "production":
    logger.info("Production environment detected - ensure all secrets are configured")
    
if not settings.enable_live_apis:
    logger.warning("Live APIs disabled - using fallback data only")
    
if settings.debug:
    logger.warning("Debug mode enabled - not suitable for production")


# Development helper functions

def print_config_summary():
    """Print configuration summary for debugging."""
    print(f"""
EchoFrame Argentina RE Intelligence Configuration
================================================
Environment: {settings.environment}
Debug Mode: {settings.debug}
API Host: {settings.api_host}:{settings.api_port}
CORS Origins: {', '.join(settings.cors_origins)}

External APIs:
- BCRA: {settings.bcra_api_base_url} (timeout: {settings.bcra_api_timeout}s)
- REM: {settings.rem_api_base_url} (timeout: {settings.rem_api_timeout}s)
- Live APIs Enabled: {settings.enable_live_apis}

Model Settings:
- Behavioral Adjustments: {settings.enable_behavioral_adjustments}
- Prospect Theory Lambda: {settings.prospect_theory_lambda}
- HMM States: {settings.hmm_n_states}
- Cache TTL: {settings.model_cache_ttl_minutes} minutes

Features:
- NLP Processing: {settings.enable_nlp_processing}
- Regime Detection: {settings.enable_regime_detection}
- Scenario Analysis: {settings.enable_scenario_analysis}

Logging: {settings.log_level}
    """)


if __name__ == "__main__":
    print_config_summary()