from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import random

app = FastAPI(
    title="EchoFrame Argentina RE Intelligence API",
    description="Real-time forecasting for Buenos Aires real estate markets",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "echoframe-argentina-re",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/v1/forecast/summary")
async def get_forecast_summary():
    """Get demo forecast summary for dashboard."""
    return {
        "departamentos": {
            "current_price_m2": 2400,
            "year_1": {
                "median_change_pct": 6.2,
                "ci_80": [3.1, 9.8],
                "p_increase": 0.87
            },
            "year_2": {
                "median_change_pct": 5.5,
                "ci_80": [1.8, 9.2],
                "p_increase": 0.83
            },
            "year_3": {
                "median_change_pct": 7.0,
                "ci_80": [-0.5, 14.5],
                "p_increase": 0.79
            }
        },
        "campos": {
            "current_price_ha": 16000,
            "year_1": {
                "median_change_pct": 5.8,
                "ci_80": [2.5, 9.1],
                "p_increase": 0.85
            },
            "year_2": {
                "median_change_pct": 4.9,
                "ci_80": [0.8, 8.9],
                "p_increase": 0.80
            },
            "year_3": {
                "median_change_pct": 6.5,
                "ci_80": [-1.2, 14.2],
                "p_increase": 0.75
            }
        },
        "current_regime": "recovery",
        "regime_confidence": 0.82,
        "last_updated": datetime.utcnow().isoformat()
    }

@app.get("/api/v1/signals/latest")
async def get_latest_signals(limit: int = 10):
    """Get latest market signals."""
    signals = []
    sources = ["Ámbito Financiero", "La Nación", "Clarín", "El Cronista"]
    titles = [
        "BCRA reduce tasa de referencia al 32% anual",
        "Créditos hipotecarios UVA vuelven con fuerza al mercado",
        "Construcción creció 8.5% interanual en marzo",
        "Inversión extranjera en real estate aumenta 45%",
        "Inflación cede al 3.8% mensual, menor en 3 años"
    ]
    
    for i in range(min(limit, 5)):
        signals.append({
            "id": f"signal_{i+1}",
            "title": titles[i % len(titles)],
            "source": sources[i % len(sources)],
            "published_at": datetime.utcnow().isoformat(),
            "impact_direction": "positive" if i % 3 != 0 else "negative",
            "impact_magnitude": round(random.uniform(0.3, 0.9), 2),
            "signal_type": ["credit_policy", "construction", "investment", "inflation"][i % 4],
            "affected_segments": ["departamentos", "campos"] if i % 2 == 0 else ["departamentos"]
        })
    
    return {"signals": signals, "total": len(signals)}

@app.get("/api/v1/market/macro")
async def get_macro_data():
    """Get current macro indicators."""
    return {
        "usd_ars_official": 1050.25,
        "usd_ars_blue": 1180.50,
        "blue_gap_pct": 12.4,
        "inflation_monthly": 3.8,
        "inflation_annual": 52.1,
        "bcra_rate": 32.0,
        "reserves_usd_bn": 28.5,
        "last_updated": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
