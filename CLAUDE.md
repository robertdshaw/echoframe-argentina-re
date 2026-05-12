2# EchoFrame Argentina Real Estate Intelligence — Claude Code Build Instructions

## CONTEXT FOR CLAUDE CODE

You are building a working demo of EchoFrame's Argentina Real Estate Intelligence Module. This is a predictive analytics dashboard that forecasts Buenos Aires apartment prices and Argentine agricultural land (campos) prices over 1/2/3 year horizons using Bayesian probability, Hidden Markov Models, and Prospect Theory behavioral adjustments.

**This is a DEMO that must work TODAY.** The architecture uses a hybrid approach:
- **LIVE data** from free public APIs (BCRA, REM survey) — fetched at runtime
- **Seeded realistic data** for sources requiring API keys (NewsData.io, Zonaprop) — based on real 2024-2026 market data researched and hardcoded
- **Real probabilistic models** (PyMC Bayesian, hmmlearn HMM) running actual inference — not mock outputs

The client is Argentine, speaks Spanish, and asked specifically: "Will Buenos Aires apartment prices go up or down? What about campos? At what rate over years 1, 2, and 3?"

---

## REPO STRUCTURE

```
echoframe-argentina-re/
├── CLAUDE.md                    # This file — master instructions
├── README.md                    # Project overview + setup
├── docker-compose.yml           # Full stack orchestration
├── .env.example                 # Environment variables template
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                  # FastAPI application entry point
│   ├── config.py                # Settings + env management
│   │
│   ├── data/
│   │   ├── __init__.py
│   │   ├── bcra_client.py       # LIVE: BCRA API connector (free, no auth needed)
│   │   ├── rem_client.py        # LIVE: REM market expectations API (free, no auth)
│   │   ├── news_seeder.py       # SEEDED: Realistic Argentine RE news articles
│   │   ├── property_seeder.py   # SEEDED: Realistic Zonaprop-style listing data
│   │   ├── commodity_seeder.py  # SEEDED: MATBA-ROFEX soy/wheat/corn prices
│   │   └── seeds/
│   │       ├── news_articles.json        # 200+ realistic articles
│   │       ├── ba_listings.json          # Buenos Aires property listings
│   │       ├── campos_listings.json      # Agricultural land listings
│   │       └── commodity_prices.json     # Historical commodity data
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── bayesian_departamentos.py   # PyMC model for CABA apartments
│   │   ├── bayesian_campos.py          # PyMC model for agricultural land
│   │   ├── hmm_regime.py              # hmmlearn regime detection
│   │   ├── prospect_theory.py         # Behavioral adjustment layer
│   │   ├── ensemble.py               # Model integration + final forecast
│   │   └── calibration_data.py       # Historical data for model training
│   │
│   ├── nlp/
│   │   ├── __init__.py
│   │   ├── signal_classifier.py      # News article → signal category
│   │   ├── sentiment.py              # Spanish sentiment analysis
│   │   └── entity_extractor.py       # Argentine entity recognition
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes_forecast.py        # /forecast endpoints
│   │   ├── routes_signals.py         # /signals endpoints
│   │   ├── routes_market.py          # /market-data endpoints
│   │   ├── routes_scenarios.py       # /scenarios what-if endpoints
│   │   └── schemas.py                # Pydantic response models
│   │
│   └── services/
│       ├── __init__.py
│       ├── data_pipeline.py          # Orchestrates data collection
│       ├── forecast_service.py       # Runs model ensemble
│       └── signal_service.py         # Processes news → signals
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   │
│   ├── public/
│   │   └── echoframe-logo.svg
│   │
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/
│       │   └── client.ts             # Axios client for backend
│       │
│       ├── components/
│       │   ├── layout/
│       │   │   ├── Header.tsx
│       │   │   ├── Sidebar.tsx
│       │   │   └── DashboardLayout.tsx
│       │   │
│       │   ├── forecast/
│       │   │   ├── FanChart.tsx              # Main price trajectory visualization
│       │   │   ├── ProbabilityGauge.tsx       # P(increase), P(decrease) gauges
│       │   │   ├── ForecastCard.tsx           # Combined forecast display
│       │   │   └── HorizonSelector.tsx        # Year 1/2/3 toggle
│       │   │
│       │   ├── regime/
│       │   │   ├── RegimeIndicator.tsx        # Current HMM state display
│       │   │   ├── TransitionMatrix.tsx       # State transition probabilities
│       │   │   └── RegimeTimeline.tsx         # Historical regime overlay
│       │   │
│       │   ├── signals/
│       │   │   ├── SignalFeed.tsx             # Live intelligence feed
│       │   │   ├── SignalCard.tsx             # Individual signal display
│       │   │   └── ImpactBadge.tsx            # Impact magnitude indicator
│       │   │
│       │   ├── scenarios/
│       │   │   ├── ScenarioExplorer.tsx       # What-if scenario tool
│       │   │   └── ScenarioSlider.tsx         # Adjustable parameter inputs
│       │   │
│       │   ├── market/
│       │   │   ├── MacroPanel.tsx             # BCRA data display
│       │   │   ├── BarrioHeatmap.tsx          # Buenos Aires neighborhood map
│       │   │   └── CamposMap.tsx              # Agricultural zones map
│       │   │
│       │   └── common/
│       │       ├── LoadingSpinner.tsx
│       │       ├── ConfidenceInterval.tsx
│       │       └── DisclaimerBanner.tsx
│       │
│       ├── pages/
│       │   ├── DepartamentosPage.tsx          # Buenos Aires apartments view
│       │   ├── CamposPage.tsx                 # Agricultural land view
│       │   ├── SignalsPage.tsx                # Intelligence feed view
│       │   └── ScenarioPage.tsx               # What-if explorer view
│       │
│       ├── hooks/
│       │   ├── useForecast.ts
│       │   ├── useSignals.ts
│       │   └── useMarketData.ts
│       │
│       ├── types/
│       │   └── index.ts                       # TypeScript interfaces
│       │
│       └── utils/
│           ├── formatters.ts                  # Number/currency formatting
│           └── colors.ts                      # EchoFrame brand palette
│
└── scripts/
    ├── seed_data.py                           # Populate seed data
    ├── train_models.py                        # Pre-train HMM on historical data
    └── run_backtest.py                        # Validate model on 2019-2024 data
```

---

## BUILD SEQUENCE — FOLLOW THIS ORDER

### Phase 1: Backend Foundation (do this first)

#### Step 1.1: Project scaffolding + dependencies

```
# requirements.txt must include:
fastapi==0.115.0
uvicorn[standard]==0.30.0
pydantic==2.9.0
httpx==0.27.0          # for async API calls
numpy==1.26.4
pandas==2.2.0
scipy==1.13.0
pymc==5.16.0           # Bayesian inference
arviz==0.19.0          # Bayesian diagnostics
hmmlearn==0.3.2        # Hidden Markov Models
scikit-learn==1.5.0
python-dotenv==1.0.0
```

**CRITICAL**: PyMC requires JAX or C backend. For the demo, use `pymc` with the default NumPyro/JAX backend. If JAX install is problematic in Docker, fall back to `scipy.stats` for Bayesian posteriors using conjugate priors — this is simpler but produces identical demo output for the forecast distributions. The demo doesn't need MCMC convergence diagnostics; it needs plausible posterior distributions.

**FALLBACK STRATEGY**: If PyMC/JAX dependency hell blocks progress, implement the Bayesian model using `scipy.stats` directly:
- Use Beta distributions for probability estimates
- Use Normal distributions for price change posteriors
- Update priors with observed data using conjugate updating
- This produces identical visual output for the dashboard and is what a pragmatic data scientist would ship for a demo

#### Step 1.2: BCRA Live Data Client

```python
# backend/data/bcra_client.py
# 
# The BCRA API is FREE, requires NO authentication, and returns JSON.
# Base URL: https://api.bcra.gob.ar/estadisticas/v2.0
# 
# Key endpoints to implement:
# - GET /principalesvariables → list all available variables with latest values
# - GET /datosvariable/{idVariable}/{desde}/{hasta} → time series data
#
# Critical variable IDs to fetch:
#   - Variable 1: Reservas Internacionales del BCRA
#   - Variable 4: Tipo de Cambio Minorista (USD sell)
#   - Variable 5: Tipo de Cambio Mayorista (USD wholesale)  
#   - Variable 6: Tasa BADLAR
#   - Variable 7: Tasa TM20
#   - Variable 15: Base Monetaria
#   - Variable 27: Inflación mensual (CPI)
#   - Variable 28: Inflación interanual
#   - Variable 29: Inflación esperada (expected)
#
# Date format: YYYY-MM-DD
# Response format: { "results": [{ "fecha": "2025-01-15", "valor": 1234.56 }] }
#
# IMPORTANT: This API sometimes returns 500 errors. Implement retry with 
# exponential backoff (3 retries, 1s/2s/4s delays). Cache responses for 1 hour.
# If API is down during demo, fall back to seeded data.
#
# Also implement the REM (Market Expectations) client:
# Base URL: https://bcra-rem-api.facujallia.workers.dev
# - GET /api/ipc_general → inflation forecasts (median, mean, min, max)
# - GET /api/tipo_cambio → exchange rate forecasts
# - GET /api/pib → GDP growth forecasts
# No auth required. Returns { "datos": [...], "metadata": {...} }
```

#### Step 1.3: Seed Data Files

Create JSON seed files with realistic data. This is NOT mock data — it's based on actual 2024-2026 Argentine market research:

```python
# backend/data/seeds/news_articles.json
#
# Generate 200+ articles structured as:
# {
#   "id": "art_001",
#   "title": "BCRA reduce tasa de referencia al 32%",
#   "source": "Ámbito Financiero",
#   "published_at": "2025-11-15T08:30:00Z",
#   "category": "economic_policy",
#   "summary": "El Banco Central recortó la tasa de política monetaria...",
#   "signal_type": "credit_policy",
#   "impact_direction": "positive",    # for RE prices
#   "impact_magnitude": 0.7,           # 0-1 scale
#   "affected_segments": ["departamentos", "campos"],
#   "keywords": ["tasa", "BCRA", "crédito", "hipotecario"]
# }
#
# Article categories should cover:
# - Monetary policy (BCRA rate decisions, reserve changes)
# - Mortgage/credit (new hipotecario programs, UVA credits)
# - Exchange rate (blue dollar, cepo, devaluation risk)
# - Construction (permits, costs, INDEC ICC)
# - Political (government policy, regulation changes)
# - Agricultural (commodity prices, retenciones, drought/weather)
# - Foreign investment (FDI flows, capital controls)
# - Urban development (infrastructure, subte expansion, zoning)
#
# Mix positive and negative signals realistically. Current period
# (late 2024-2026) should lean ~60% positive reflecting recovery.
# Include some high-magnitude negative signals (cepo reimposition risk,
# drought warnings) to show the system handles downside scenarios.
#
# SOURCES TO USE (real Argentine outlets):
# Ámbito Financiero, La Nación, Clarín, Infobae, BAE Negocios,
# El Cronista, iProfesional, Página/12, Cronista Comercial

# backend/data/seeds/ba_listings.json  
#
# Generate ~500 property listings matching real Zonaprop data structure:
# {
#   "id": "prop_001",
#   "barrio": "Palermo",
#   "type": "departamento",
#   "price_usd": 185000,
#   "surface_m2": 65,
#   "price_per_m2": 2846,
#   "rooms": 3,
#   "bedrooms": 2,
#   "bathrooms": 1,
#   "latitude": -34.5875,
#   "longitude": -58.4240,
#   "listing_date": "2026-03-15",
#   "is_new_construction": false,
#   "building_age_years": 25
# }
#
# Use REAL price ranges by barrio (as of early 2026):
# Puerto Madero: $5,500-6,500/m2
# Palermo: $2,800-3,500/m2
# Recoleta: $2,600-3,200/m2
# Belgrano: $2,400-3,000/m2
# Caballito: $1,800-2,200/m2
# Villa Urquiza: $2,000-2,500/m2
# Villa Crespo: $2,100-2,600/m2
# La Boca: $1,200-1,600/m2
# Villa Lugano: $1,000-1,300/m2
# Distribute across 15+ barrios with realistic variation.

# backend/data/seeds/campos_listings.json
#
# Agricultural land data by zone:
# {
#   "id": "campo_001",  
#   "zone": "core_pampa",
#   "province": "Buenos Aires",
#   "partido": "Pergamino",
#   "price_usd_per_ha": 15500,
#   "hectares": 280,
#   "use_type": "agricultural",     # agricultural | livestock | mixed
#   "soil_quality": "premium",      # premium | good | marginal
#   "has_irrigation": false,
#   "latitude": -33.8899,
#   "longitude": -60.5735
# }
#
# Price ranges by zone:
# Core Pampa (Pergamino, Junín, Rojas): $12,000-18,000/ha
# Buenos Aires peri-urban: up to $35,000/ha
# Santa Fe: $4,000-12,000/ha  
# Córdoba: $8,000-14,000/ha
# Santiago del Estero frontier: $3,000-6,000/ha
# Andean/Western: $700-2,000/ha

# backend/data/seeds/commodity_prices.json
#
# Monthly soybean, wheat, corn prices (USD/ton) from 2020-2026
# Based on real MATBA-ROFEX/CBOT historical data.
# Soybean: range $320-580/ton over period
# Wheat: range $180-400/ton
# Corn: range $140-280/ton
```

#### Step 1.4: Historical Calibration Data

```python
# backend/models/calibration_data.py
#
# This file contains the REAL historical data for model training.
# All figures sourced from IDECBA, Colegio de Escribanos, BCRA.
#
# CABA apartment price index (USD/m2, quarterly, used 2BR apartments):
# Q1 2018: 2,800 (pre-crisis peak)
# Q2 2018: 2,750
# Q3 2018: 2,600  (Macri crisis begins)
# Q4 2018: 2,450
# Q1 2019: 2,380
# Q2 2019: 2,300  (prolonged decline begins — 18 quarters of YoY drops)
# ... declining through ...
# Q4 2023: 2,150  (trough)
# Q1 2024: 2,170  (first recovery quarter)
# Q2 2024: 2,195
# Q3 2024: 2,220
# Q4 2024: 2,260
# Q1 2025: 2,290
# Q2 2025: 2,310  (+5.27% YoY — confirmed IDECBA)
# Q3 2025: 2,340 (est.)
# Q4 2025: 2,370 (est.)
# Q1 2026: 2,400 (est. — ~5.6% YoY appreciation continuing)
#
# Transaction volumes (annual, Buenos Aires):
# 2018: ~42,000 (healthy)
# 2019: ~32,000 (crisis)
# 2020: ~22,000 (COVID + crisis)
# 2021: ~28,000 (partial recovery)
# 2022: ~35,000 (improving)
# 2023: ~40,500 (returning to normal)
# 2024: 54,761 (+35.1% YoY — confirmed Colegio de Escribanos)
# 2025 H1: 36,179 (+45.3% YoY pace)
#
# Monthly USD-ARS rate, inflation rate, BCRA reference rate
# — use actual BCRA data via the live API for recent periods,
# seeded historical data for pre-2024 calibration
#
# Agricultural land values (USD/ha, core Pampa, annual):
# 2015: ~8,000
# 2016: ~8,500
# 2017: ~9,500
# 2018: ~10,500
# 2019: ~10,000 (crisis dip)
# 2020: ~10,500
# 2021: ~12,000 (commodity boom)
# 2022: ~13,500
# 2023: ~14,000 (drought impact)
# 2024: ~15,000
# 2025: ~16,000 (est.)
```

### Phase 2: Probabilistic Models

#### Step 2.1: Bayesian Departamentos Model

```python
# backend/models/bayesian_departamentos.py
#
# PURPOSE: Generate posterior probability distributions for CABA apartment
# price changes at Year 1, 2, and 3 horizons.
#
# APPROACH: Use conjugate Bayesian updating with Normal-Normal model.
# The beauty of this for a demo is it's analytically tractable —
# no MCMC needed, instant computation, real math.
#
# PRIOR SPECIFICATION:
# Use REM survey consensus as informative priors:
# - Inflation prior: Normal(μ=15%, σ=5%) for 2026 (REM median ~15%)
# - USD-ARS rate prior: derived from REM tipo_cambio forecast
# - GDP growth prior: Normal(μ=4.5%, σ=1.5%) for 2026
#
# LIKELIHOOD MODEL:
# price_change ~ Normal(μ_posterior, σ_posterior)
# where μ_posterior is a weighted combination of:
#   0.30 × credit_expansion_effect
#   0.25 × inflation_adjusted_demand
#   0.20 × transaction_volume_momentum
#   0.10 × construction_cost_pressure
#   0.10 × foreign_investment_flow
#   0.05 × news_sentiment_aggregate
#
# POSTERIOR COMPUTATION (conjugate Normal-Normal):
# μ_posterior = (μ_prior/σ²_prior + Σ(x_i)/σ²_likelihood) / (1/σ²_prior + n/σ²_likelihood)
# σ²_posterior = 1 / (1/σ²_prior + n/σ²_likelihood)
#
# OUTPUT for each year horizon:
# {
#   "year": 1,
#   "median_change_pct": 6.2,
#   "mean_change_pct": 6.5,
#   "credible_interval_80": [3.1, 9.8],
#   "credible_interval_95": [0.5, 12.4],
#   "p_increase": 0.87,           # P(change > 0)
#   "p_increase_5pct": 0.62,      # P(change > 5%)
#   "p_increase_10pct": 0.28,     # P(change > 10%)
#   "p_decrease": 0.13,           # P(change < 0)
#   "p_decrease_5pct": 0.04,      # P(change < -5%)
#   "distribution": {              # For fan chart rendering
#     "type": "normal",
#     "mu": 6.5,
#     "sigma": 3.2
#   }
# }
#
# IMPORTANT: Given the current market context (recovery phase, 
# reintroduction of mortgages, inflation declining, transaction volumes 
# surging 45% YoY), the model SHOULD output positive expected returns 
# in nominal USD terms for Year 1-2, with widening uncertainty at Year 3.
# This matches the client's intuition ("estoy seguro que te va a decir 
# que es muy probable que aumenten") — and it should, because the 
# evidence genuinely supports it. But the uncertainty bounds must be 
# honest: Year 3 should have wide intervals reflecting genuine 
# Argentine macro uncertainty.
#
# Expected output ranges (sanity check):
# Year 1: +5% to +8% median (narrow CI, strong evidence)
# Year 2: +4% to +9% median (wider CI)
# Year 3: +3% to +12% median (wide CI, regime uncertainty)
```

#### Step 2.2: Bayesian Campos Model

```python
# backend/models/bayesian_campos.py
#
# Same conjugate Bayesian structure but different input weights:
#   0.35 × commodity_price_trajectory (soy/wheat/corn futures)
#   0.20 × export_tax_policy (retenciones — binary/categorical)
#   0.15 × usd_ars_trajectory
#   0.15 × agricultural_profitability_index
#   0.10 × news_sentiment_agricultural
#   0.05 × frontier_expansion_pressure
#
# Regional sub-models with separate priors:
# - Core Pampa: μ_prior = +6%, σ_prior = 3% (stable, commodity-driven)
# - Santa Fe: μ_prior = +5%, σ_prior = 4%
# - Frontier: μ_prior = +8%, σ_prior = 7% (higher return, higher risk)
# - Peri-urban: μ_prior = +10%, σ_prior = 8% (development optionality)
#
# Commodity price correlation: When soybean > $450/ton, agricultural
# land appreciates faster. Below $350/ton, appreciation stalls.
# This creates natural nonlinearity in the forecast.
```

#### Step 2.3: HMM Regime Detection

```python
# backend/models/hmm_regime.py
#
# PURPOSE: Detect the current market regime and forecast regime 
# transition probabilities over the forecast horizon.
#
# IMPLEMENTATION: Use hmmlearn GaussianHMM with 3 hidden states.
#
# States:
#   0 = "Crisis" (capital flight, cepo, transaction collapse)
#   1 = "Recovery" (credit restoration, volume surge, stabilization)
#   2 = "Boom" (speculative excess, rapid appreciation)
#
# Observable features (multivariate Gaussian emission):
#   - transaction_volume_yoy_change (normalized)
#   - price_change_rate (quarterly, normalized)
#   - news_sentiment_score (aggregated, normalized)
#   - credit_growth_rate (normalized)
#   - usd_premium_gap (blue dollar vs official, normalized)
#
# TRAINING: Fit on the historical calibration data (2018-2026).
# The model should learn:
#   - 2018-2019: Crisis state
#   - 2020-2021: Deep crisis / COVID overlay
#   - 2022-2023: Late crisis / transition
#   - 2024-2026: Recovery state
#
# TRANSITION MATRIX (expected after training):
#   From\To    Crisis  Recovery  Boom
#   Crisis     0.70    0.25      0.05
#   Recovery   0.10    0.72      0.18
#   Boom       0.15    0.25      0.60
#
# CURRENT STATE PREDICTION: Use forward algorithm to compute
# P(state | all observations). Expected: P(Recovery) ≈ 0.80+
#
# OUTPUT:
# {
#   "current_regime": "recovery",
#   "regime_probability": 0.82,
#   "transition_probabilities": {
#     "remain_recovery": 0.72,
#     "transition_to_boom": 0.18,
#     "transition_to_crisis": 0.10
#   },
#   "regime_history": [
#     {"period": "Q1 2018", "regime": "crisis", "probability": 0.85},
#     ...
#   ]
# }
```

#### Step 2.4: Prospect Theory Behavioral Layer

```python
# backend/models/prospect_theory.py
#
# PURPOSE: Apply Kahneman-Tversky behavioral distortions to the raw 
# Bayesian posteriors to account for Argentine-specific market psychology.
#
# IMPLEMENTATION:
#
# Value function: V(x) = x^α for gains, V(x) = -λ(-x)^β for losses
#   α = 0.88 (standard K-T)
#   β = 0.88 (standard K-T)
#   λ = 2.25 (Argentine calibration — higher than standard 2.0 due 
#             to decades of crisis memory amplifying loss aversion)
#
# Probability weighting: π(p) = p^γ / (p^γ + (1-p)^γ)^(1/γ)
#   γ = 0.61 (standard K-T) for gains
#   γ = 0.69 (standard K-T) for losses
#
# What this does to the forecast:
# 1. The raw Bayesian posterior says P(decrease>5%) = 0.04
# 2. Prospect Theory probability weighting OVERWEIGHTS this small probability
#    because people (especially Argentines with crisis memory) pay 
#    disproportionate attention to tail risks
# 3. The behavioral-adjusted output shows the same median but with 
#    ASYMMETRIC confidence intervals — wider on the downside
# 4. This is displayed in the dashboard as "behaviorally-adjusted risk"
#    vs "model-estimated risk" — showing the client BOTH views
#
# OUTPUT: Takes a Bayesian posterior distribution and returns a 
# modified distribution with asymmetric tails.
#
# def adjust_posterior(posterior_mu, posterior_sigma, lambda_loss=2.25):
#     """
#     Returns:
#       - adjusted_mu: slightly lower (loss aversion drags expected value)
#       - adjusted_ci_80: asymmetric [wider_lower, narrower_upper]
#       - adjusted_ci_95: asymmetric [much_wider_lower, slightly_narrower_upper]
#       - behavioral_p_decrease: higher than raw (probability overweighting)
#     """
```

#### Step 2.5: Ensemble Integration

```python
# backend/models/ensemble.py
#
# PURPOSE: Combine Bayesian + HMM + Prospect Theory into final output.
#
# FLOW:
# 1. HMM → current regime + transition probabilities
# 2. Bayesian → regime-CONDITIONAL posteriors
#    (if HMM says P(crisis)=0.10, weight the crisis-conditional 
#     Bayesian posterior by 0.10 in the mixture)
# 3. Prospect Theory → behavioral adjustment of the mixture posterior
#
# FINAL OUTPUT (per segment, per year):
# {
#   "segment": "departamentos_caba",
#   "year": 1,
#   "current_price_m2": 2400,           # current USD/m2
#   "forecast": {
#     "model_estimate": {                 # Raw Bayesian-HMM
#       "median_change_pct": 6.2,
#       "mean_change_pct": 6.5,
#       "ci_80": [3.1, 9.8],
#       "ci_95": [0.5, 12.4],
#       "p_increase": 0.87,
#       "projected_price_m2": 2549      # 2400 × 1.062
#     },
#     "behavioral_adjusted": {           # After Prospect Theory
#       "median_change_pct": 5.8,
#       "ci_80": [1.5, 9.2],            # Note: asymmetric, wider downside
#       "ci_95": [-2.0, 11.8],
#       "p_increase": 0.82,
#       "p_decrease_narrative": "Argentine market psychology suggests investors 
#         weight downside scenarios ~2.25x more heavily than rational models predict"
#     }
#   },
#   "regime_context": {
#     "current": "recovery",
#     "confidence": 0.82,
#     "key_driver": "Transaction volumes +45% YoY signal sustained recovery momentum"
#   },
#   "top_signals": [
#     { "title": "...", "impact": 0.7, "direction": "positive" },
#     ...
#   ]
# }
```

### Phase 3: NLP Signal Pipeline

```python
# backend/nlp/signal_classifier.py
#
# Classify news articles into signal categories that feed the Bayesian network.
#
# APPROACH: Rule-based classifier using Spanish keyword matching.
# NOT a trained ML model — for demo purposes, keyword matching is 
# deterministic, fast, and produces consistent results.
#
# Signal categories:
# "credit_policy" → keywords: ["tasa", "BCRA", "hipotecario", "crédito", "UVA", "prestamo"]
# "exchange_rate" → keywords: ["dólar", "tipo de cambio", "devaluación", "cepo", "blue"]
# "inflation" → keywords: ["inflación", "IPC", "precios", "costo de vida"]
# "construction" → keywords: ["construcción", "permisos", "obras", "INDEC ICC"]
# "regulation" → keywords: ["regulación", "ley", "normativa", "blanqueo", "DNU"]
# "agricultural" → keywords: ["campo", "soja", "trigo", "retenciones", "sequía", "cosecha"]
# "investment" → keywords: ["inversión", "FDI", "capital", "flujos"]
# "infrastructure" → keywords: ["subte", "autopista", "infraestructura", "desarrollo"]
#
# Impact magnitude: based on source credibility + keyword density
# Impact direction: based on positive/negative word lists in Spanish
#
# This is a legitimate NLP approach — The Economist Intelligence Unit uses 
# similar keyword-based signal detection for their country risk ratings.
# The sophistication is in the signal dictionary design, not ML complexity.
```

### Phase 4: API Endpoints

```python
# backend/api/routes_forecast.py
#
# FastAPI routes:
#
# GET /api/v1/forecast/departamentos
#   Query params: barrio (optional), year_horizon (1|2|3, default all)
#   Returns: ForecastResponse with model + behavioral estimates
#
# GET /api/v1/forecast/campos  
#   Query params: zone (core_pampa|santa_fe|frontier|periurban), year_horizon
#   Returns: ForecastResponse with regional sub-model
#
# GET /api/v1/forecast/summary
#   Returns: Both segments, all horizons, compact format for dashboard header
#
# GET /api/v1/regime/current
#   Returns: HMM regime state, transition matrix, regime history
#
# GET /api/v1/signals/latest
#   Query params: limit (default 20), segment (departamentos|campos|all)
#   Returns: Latest classified news signals with impact scores
#
# GET /api/v1/market/macro
#   Returns: Latest BCRA data (live), REM consensus (live), key indicators
#
# GET /api/v1/market/listings-summary
#   Query params: segment
#   Returns: Aggregated listing stats by barrio/zone
#
# POST /api/v1/scenarios/simulate
#   Body: { "inflation_target": 15, "usd_ars_target": 1800, "retenciones_change": 0 }
#   Returns: Modified forecast given scenario parameters
#
# GET /api/v1/health
#   Returns: API status + data freshness timestamps
```

### Phase 5: Frontend Dashboard

#### Design Principles

```
BRAND: EchoFrame Intelligence
- Primary: #1B2A4A (navy)
- Secondary: #E85D26 (orange) 
- Accent: #4A3B8F (purple)
- Background: #F8F9FB (light gray)
- Cards: #FFFFFF with subtle shadow
- Font: Inter for body, JetBrains Mono for numbers/data

LANGUAGE: Dashboard UI in English, but all Argentine data labels 
and news articles remain in Spanish (the client is bilingual).
Financial terminology should use standard international conventions.

TONE: Professional, analytical, intelligence-grade. NOT a consumer 
real estate app. Think Bloomberg Terminal meets The Economist.
```

#### Key Component Specifications

```typescript
// FanChart.tsx — THE most important visualization
//
// A D3.js or Recharts time-series chart showing:
// 1. Historical price line (solid, navy) — 2018 to present
// 2. Current price marker (vertical line, orange)
// 3. Forward projection as a "fan" of confidence intervals:
//    - Median forecast line (dashed, navy)
//    - 80% CI band (light purple fill, semi-transparent)
//    - 95% CI band (lighter purple fill, more transparent)
// 4. Year markers at Y1, Y2, Y3 on the x-axis
//
// Must support both departamentos (USD/m2) and campos (USD/ha) modes.
// Y-axis: price level, X-axis: time (quarters)
// Include behavioral-adjusted overlay toggle (dashed orange band 
// showing the asymmetric Prospect Theory intervals)
//
// INTERACTIONS:
// - Hover on any point: tooltip showing exact values
// - Click on Y1/Y2/Y3: expand to show full probability breakdown
// - Toggle "Model estimate" vs "Behavioral adjusted" overlay

// ProbabilityGauge.tsx
//
// Circular or semicircular gauge showing probability percentages:
// - P(increase) as the primary display (green fill)
// - P(decrease) as the complementary (red fill)
// - Center text: "87% likely to increase"
// - Below: "Year 1 — Buenos Aires Departamentos"
// - Additional detail on hover: P(>5%), P(>10%), P(decrease>5%)

// RegimeIndicator.tsx
//
// A prominent status indicator showing:
// - Large text: "RECOVERY" (or "CRISIS" / "BOOM")
// - Color-coded: green for Recovery, red for Crisis, amber for Boom
// - Confidence percentage: "82% confidence"
// - Small transition arrows: "18% → Boom | 10% → Crisis"
// - Historical timeline strip below showing past regimes as colored bars

// ScenarioExplorer.tsx
//
// Interactive what-if panel with sliders:
// - Inflation target (5% — 40%, default at REM consensus)
// - USD-ARS exchange rate (800 — 3000, default at REM consensus)
// - Mortgage rate adjustment (-5% to +10%)
// - Retenciones change (-10pp to +10pp, for campos)
// - News sentiment override (very negative to very positive)
//
// Each slider adjustment triggers a POST to /scenarios/simulate
// and the FanChart + ProbabilityGauges update in real-time.
// Include a "Reset to base case" button.

// SignalFeed.tsx
//
// Scrollable feed of news signals, each card showing:
// - Source name + publication date (in Spanish)
// - Article title (Spanish)
// - Impact badge: green↑ or red↓ with magnitude (0.1-1.0)
// - Affected variable tag: "credit_policy", "exchange_rate", etc.
// - Which segment affected: 🏢 departamentos, 🌾 campos, or both
//
// Filter controls: by segment, by signal type, by impact direction
// Sort: by date (default) or by impact magnitude

// DisclaimerBanner.tsx
//
// ALWAYS visible at the bottom of every page:
// "Las proyecciones presentadas son estimaciones probabilísticas basadas 
// en modelos cuantitativos y no constituyen asesoramiento financiero o 
// de inversión. Los intervalos de confianza reflejan incertidumbre 
// inherente. Rendimientos pasados no garantizan resultados futuros.
// EchoFrame Intelligence — Análisis ético basado en fuentes licenciadas."
```

### Phase 6: Docker Compose

```yaml
# docker-compose.yml
#
# Services:
#   backend:
#     build: ./backend
#     ports: ["8000:8000"]
#     environment:
#       - NEWSDATA_API_KEY=${NEWSDATA_API_KEY:-demo}  # Optional
#       - BCRA_TOKEN=${BCRA_TOKEN:-}                  # Optional (BCRA is free)
#       - ENVIRONMENT=demo
#     command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
#
#   frontend:
#     build: ./frontend
#     ports: ["3000:3000"]
#     environment:
#       - VITE_API_URL=http://localhost:8000
#     depends_on: [backend]
#
# NO database container needed for demo — everything runs in-memory
# with seeded data + live API calls to BCRA/REM.
# This keeps startup instant and eliminates dependency headaches.
```

---

## CRITICAL IMPLEMENTATION NOTES

### What MUST be live (free APIs, no keys needed):
1. **BCRA API** — `https://api.bcra.gob.ar/estadisticas/v2.0` — exchange rates, inflation, reserves, monetary base
2. **REM API** — `https://bcra-rem-api.facujallia.workers.dev` — economist consensus forecasts

### What is seeded (realistic, based on real data):
1. **News articles** — 200+ articles with real Argentine outlet names, real-world events, proper Spanish
2. **Property listings** — 500+ listings with real barrio names, real price ranges per neighborhood
3. **Campos data** — Regional agricultural land with accurate zone pricing
4. **Commodity prices** — Historical soy/wheat/corn monthly series

### What runs real computation (not mocked):
1. **Bayesian posteriors** — Real conjugate Normal-Normal updating producing genuine probability distributions
2. **HMM** — Real hmmlearn model trained on historical regime data
3. **Prospect Theory** — Real Kahneman-Tversky value/weighting functions applied to posteriors
4. **Ensemble** — Real weighted combination with regime-conditional mixing

### What should gracefully degrade:
- If BCRA API is down → fall back to seeded macro data with "last updated" timestamp
- If PyMC dependency fails → fall back to scipy.stats conjugate updating (same output, simpler math)
- If Docker is problematic → everything should also run with `pip install -r requirements.txt && uvicorn main:app` + `npm run dev`

### Performance targets:
- Backend startup: < 10 seconds (model pre-training on historical data happens at startup)
- Forecast endpoint response: < 2 seconds
- Full page load: < 3 seconds
- Scenario simulation: < 1 second (just re-running conjugate update with modified priors)

---

## WHAT "DONE" LOOKS LIKE

The client opens the dashboard and immediately sees:

1. **Header**: "EchoFrame Intelligence — Argentina Real Estate Forecast" with live BCRA data (USD rate, inflation, reference rate)

2. **Main panel — two fan charts side by side**:
   - Left: Buenos Aires departamentos price trajectory (historical + 3-year forecast with confidence bands)
   - Right: Campos price trajectory (with zone selector)

3. **Below each chart — probability gauges**: "87% probability of price increase in Year 1" with 80/95% credible intervals

4. **Regime indicator**: "RECOVERY — 82% confidence" with transition probabilities

5. **Signal feed**: Latest 20 news signals driving the model, in Spanish, with impact scoring

6. **Scenario explorer**: Sliders to modify assumptions and see forecast update live

7. **Disclaimer**: Always visible, in Spanish, emphasizing this is probabilistic analysis not investment advice

The client can ask "¿cuánto van a subir los departamentos?" and the answer is right there: "Year 1: +6.2% median (80% CI: 3.1% to 9.8%), Year 2: +5.5% median (80% CI: 1.8% to 9.2%), Year 3: +7.0% median (80% CI: -0.5% to 14.5%)" — with full uncertainty quantification and the behavioral-adjusted view showing why Argentine market psychology suggests the downside tail is fatter than pure math indicates.

---

## FOR CLAUDE CODE: EXECUTION ORDER

1. Create repo structure (all folders, empty files)
2. Write backend/requirements.txt
3. Write all seed data JSON files (this is the foundation)
4. Write calibration_data.py (historical data)
5. Write bcra_client.py and rem_client.py (live API clients)
6. Write all model files (bayesian, hmm, prospect_theory, ensemble)
7. Write NLP signal classifier
8. Write FastAPI main.py + all route files
9. Write config.py and schemas.py
10. Test backend: `uvicorn main:app` should start and /health should return OK
11. Create frontend with Vite + React + TypeScript
12. Write all frontend components
13. Write docker-compose.yml
14. Test full stack end-to-end
15. Write README.md with setup instructions

**Do NOT skip seed data generation.** The seed data IS the demo. Without realistic, well-structured seed data grounded in actual Argentine market figures, the entire dashboard is hollow.
