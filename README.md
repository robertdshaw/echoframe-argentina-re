# EchoFrame · Argentina Real Estate Intelligence

A narrative-first probabilistic forecasting dashboard for two Argentine
real-estate segments — Buenos Aires apartments (CABA *departamentos*) and
Argentine farmland (*campos*).

The page leads with the investment call. Model machinery (Bayesian
posteriors, HMM regime detection, calibration backtest) lives in a
collapsible **Evidence drawer** at the bottom so the headline reads as
"buy / hold / wait" rather than as an academic paper.

```
┌───────────────────────────────────────────────────────────────┐
│  THE CALL                                                     │
│  +6.2% expected · 80% band 3.1% to 9.8% · 87% prob of gain    │
│  Polished briefing (Claude Sonnet, slot-driven, no fabrication) │
├───────────────────────────────────────────────────────────────┤
│  §01  Where to buy        — per-neighborhood / per-zone       │
│  §02  When to act         — 4 timing triggers + 0–10 gauge    │
│  §03  What you'll earn    — net-return waterfall + hold slider│
│  §04  Versus alternatives — vs Treasuries / S&P / Bonar 30    │
│  §05  Geography           — sampled listings map              │
│  §06  Signals             — denoised news + provenance tags   │
│  ▸ Evidence drawer (collapsed): trajectory, distribution,     │
│    regime, tail-risk scenarios, calibration backtest, HMM     │
└───────────────────────────────────────────────────────────────┘
```

---

## Architecture

```
echoframe-argentina-re/
├── backend/                       FastAPI · Python 3.11
│   ├── main.py                    App entry, lifespan prefetch, CORS
│   ├── config.py                  Settings + env validation
│   ├── api/                       Route handlers + Pydantic schemas
│   ├── models/                    Bayesian (dept / campos) + HMM + Prospect
│   │   ├── bayesian_departamentos.py
│   │   ├── bayesian_campos.py
│   │   ├── bayesian_barrios.py    Hierarchical partial-pooling per-barrio
│   │   ├── hmm_regime.py          HMMLearn 3-state regime detector
│   │   ├── prospect_theory.py     Kahneman-Tversky behavioural overlay
│   │   ├── ensemble.py            Regime-conditional mixture forecaster
│   │   └── calibration_data.py    Historical CABA / campos series
│   ├── nlp/                       Spanish signal classifier + relevance
│   │   ├── signal_classifier.py   Keyword + weight rule-based classifier
│   │   ├── sentiment.py           Spanish sentiment lexicon
│   │   ├── entity_extractor.py    Argentine named-entity recognition
│   │   ├── relevance_filter.py    Stage 1 · domestic-token allowlist
│   │   └── llm_relevance.py       Stage 2 · Haiku dual-scoring + cache
│   ├── services/
│   │   ├── data_pipeline.py       BCRA / REM / FRED / news / listings
│   │   ├── forecast_service.py    Task-coalescing cache + scenario apply
│   │   ├── signal_service.py      NLP pipeline orchestration
│   │   ├── narrative_service.py   Slot-driven LLM briefing (Claude Sonnet)
│   │   ├── timing_signals.py      4-trigger entry-quality gauge
│   │   └── cost_ledger.py         Monthly LLM-spend gatekeeper ($50 cap)
│   └── data/                      Seed corpora + live API clients
│       ├── bcra_client.py         BCRA monetary / macro (live)
│       ├── rem_client.py          BCRA-REM expectations (live)
│       ├── fred_client.py         FRED fallback (live)
│       ├── newsdata_client.py     NewsData.io (live, optional key)
│       ├── properati_scraper.py   CABA listings (live scrape)
│       ├── property_seeder.py     ba_listings + campos seed corpora
│       └── seeds/*.json           ~500 BA + 44 campos + 200 news items
│
├── frontend/                      React 18 · Vite · TypeScript
│   └── src/
│       ├── pages/                 DepartamentosPage / CamposPage / etc.
│       ├── components/
│       │   ├── forecast/          ExecutiveCard, NarrativeCard,
│       │   │                      NetReturnWaterfall, HurdleRateBar,
│       │   │                      BarrioForecastPanel, TimingTriggerPanel,
│       │   │                      ScenarioImpactPanel, CamposPanels…
│       │   ├── maps/              PropertyMap, CamposMap (Leaflet)
│       │   ├── regime/            RegimeIndicator + history strip
│       │   ├── model/             HmmPanel, ModelAccuracyPanel
│       │   ├── signals/           SignalFeed + cards with provenance
│       │   └── common/            EvidenceDrawer, ErrorBoundary, etc.
│       ├── hooks/                 useForecast / useNetReturn / …
│       ├── api/client.ts          Axios client w/ 60s timeout
│       ├── utils/                 colors, formatters, boomAdjust
│       └── index.css              Design tokens (navy / orange / purple)
│
├── scripts/
│   ├── run_backtest.py            29-anchor walk-forward LOO backtest
│   ├── train_models.py            Pre-fit HMM + Bayesian priors
│   └── seed_data.py               (Re)generate seed JSON
│
├── render.yaml                    Render Blueprint (backend + static site)
├── DEPLOY.md                      Deploy notes
├── CLAUDE.md                      Build instructions (Claude Code)
└── README.md                      You are here
```

---

## What it does

### Forecasts
- **Bayesian ensemble** with Student-t (df=4) posterior bands at year 1 / 2 / 3.
- **Hierarchical barrio model** — each CABA neighbourhood gets its own
  forecast via partial-pooling toward the city posterior. Thin-data
  barrios are flagged and excluded from ranked tables.
- **HMM regime detector** (Crisis / Recovery / Boom) with transition
  probabilities. Boom-state σ is widened 1.4× when P(transition → boom)
  exceeds 15% because boom was fitted on n = 1 quarter.
- **Prospect Theory** behavioural overlay applies Kahneman-Tversky
  loss aversion (λ = 2.25 for Argentina) on top of the raw posterior.

### Six narrative panels per segment
1. **Where to buy** — heat map + ranked tables (by total return, yield,
   stability score).
2. **When to act** — 4 named triggers (brecha compression, inventory,
   reserves, mortgage availability) rolled into a 0–10 entry-quality gauge
   with the closest historical analogy from the backtest.
3. **What you'll earn** — net-return waterfall with a hold-period slider.
   Departamentos: gross yield − vacancy − ABL − expensas − FX − amortised
   transactions. Campos: lease yield − inputs − retenciones − tax − FX −
   amortised transactions.
4. **Versus alternatives** — hurdle-rate comparison vs US 10Y, S&P
   long-run, Bonar 30, gross yield only. Frames the thesis as
   "Treasuries plus optionality" rather than "equity-beating growth".
5. **Geography** — Leaflet listings map with price-band colour, size ∝
   surface.
6. **Signals** — denoised Spanish-language news. Stage 1 keyword
   allowlist drops obvious noise; Stage 2 Haiku dual-scoring rescales
   the impact magnitude. Each surviving headline carries a provenance
   tag naming the dashboard section it influences.

### Evidence drawer (collapsed)
Forecast trajectory (FanChart with 80% / 95% bands), 5-bucket outcome
distribution, three canonical tail-risk scenarios (base / FX-shock /
crisis), HMM diagnostics, calibration backtest (29 walk-forward LOO
anchors).

### Anti-hallucination LLM briefing
The "Bottom line" briefing card is composed in **two stages**:

1. **Deterministic Python draft** — every number, percentage, named
   barrio, scenario probability, historical period, and backtest
   statistic is filled in Python from current model state.
2. **LLM language polish** — Claude Sonnet smooths connective tissue.
   The system prompt forbids numeric edits, entity edits, paragraph
   drops, or new citations. If the LLM call fails or times out (25s
   hard cap), the deterministic draft ships as-is.

Result: the briefing inherits the model's claims verbatim and reads
as fluent investment prose, with zero room for the LLM to invent a
neighbourhood that doesn't exist.

### Cost controls
A `CostLedger` gates every LLM call against a $50/month ceiling
(configurable via `LLM_COST_CEILING_USD`). Fails closed when the
budget is exhausted — Stage 1 keyword filter remains as a backstop;
the deterministic draft remains as a backstop for the briefing.

---

## Running locally

### Backend
```bash
cd backend
python -m venv .venv
.venv/Scripts/activate          # Windows · or `source .venv/bin/activate` on POSIX
pip install -r requirements.txt
python ../scripts/run_backtest.py    # populates models/diagnostics/*.json
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The lifespan prefetches both segment forecasts in the background, so
the first user request returns from cache. Without API keys configured
the app degrades gracefully: live BCRA / REM / FRED feeds become
fallback constants; the news feed falls back to the seed corpus;
narrative card renders the deterministic draft without LLM polish.

### Frontend
```bash
cd frontend
npm ci
npm run dev                     # http://localhost:5173
```

Vite reads `VITE_API_URL` from `.env` (defaults to `http://localhost:8000`).

---

## Deploying to Render

`render.yaml` is a Render Blueprint that provisions both services in
one go: a Python web service for the API and a static site for the
frontend bundle.

```bash
git push origin main
# Render dashboard → New → Blueprint → point at this repo
```

Secrets to set in the Render dashboard (each marked `sync: false` in
the Blueprint so they never land in git):

| Secret | Where it's used | Required? |
|---|---|---|
| `ANTHROPIC_API_KEY` | LLM briefing + Stage 2 news scoring | optional — falls back to deterministic draft |
| `NEWSDATA_API_KEY` | Live news feed | optional — falls back to seed corpus |
| `FRED_API_KEY` | US macro fallback for BCRA outages | optional — falls back to BCRA only |
| `VITE_API_URL` (frontend) | Backend origin for axios | required — e.g. `https://echoframe-argentina-api.onrender.com` |

CORS is locked in `render.yaml` to the Render static-site origin plus
the two common localhost ports for dev. Add custom domains as
additional entries in the `CORS_ORIGINS` array.

See `DEPLOY.md` for the per-deploy checklist.

---

## Data sources

| Source | Live or seeded | Used for |
|---|---|---|
| BCRA `principalesvariables` | Live | Exchange rate, reference rate, inflation, reserves, monetary base |
| BCRA-REM API | Live | Inflation / FX / GDP economist consensus |
| FRED | Live (key optional) | Fallback for individual BCRA fields when the API errors |
| NewsData.io | Live (key optional) | Spanish-language news headlines |
| Properati | Live scrape | CABA apartment listings (search results page only) |
| MATBA-ROFEX / CBOT | Seeded historical | Commodity prices 2020–2026 (soy / wheat / corn) |
| IDECBA + Colegio de Escribanos | Seeded calibration | CABA apartment price index 2018–2026 |
| INTA / Reporte Inmobiliario | Seeded constants | Campos lease yield, input-cost ratios, retenciones rates |

All seeded values are documented in-source with the survey or report
they come from. Synthetic numbers are flagged as such; nothing is
quoted to clients without a citation in the code.

---

## Anti-hallucination principles (enforced in code)

1. **Never fabricate specific facts.** Every quoted number,
   neighbourhood, scenario probability, or historical period must come
   from a service call or a documented constant. Synthetic numbers are
   clearly marked.
2. **Confidence reflects source quality, not plausibility.** HIGH = 3+
   corroborating sources. MODERATE = 1–2. LOW = inference. UNSOURCED is
   tagged in the signal pipeline as `data_source: "seeded"`.
3. **LLM is constrained to language polish.** The briefing template is
   slot-driven; numbers are filled in Python before the LLM ever sees
   the prose. The system prompt forbids numeric edits, entity edits,
   paragraph drops, or invented citations.
4. **Sources contradict ⇒ flag, don't pick.** When BCRA and FRED
   disagree on a macro reading, the response includes both and labels
   which one the model is using.
5. **Brevity over fabrication.** A short briefing grounded in real
   sources beats a long one with invented citations. Paragraphs whose
   underlying data is missing are dropped, not invented.

---

## Tech stack at a glance

**Backend** · FastAPI · Pydantic v2 · NumPy · SciPy · hmmlearn ·
scikit-learn · BeautifulSoup · Anthropic SDK · httpx · Tenacity

**Frontend** · React 18 · Vite · TypeScript · Recharts ·
React-Leaflet · Axios · Poppins (Google Fonts) · JetBrains Mono for numbers

**Infra** · Render (web service + static site) · GitHub
(repo + Render auto-deploy on push)

---

## License & disclaimers

Internal EchoFrame Intelligence demo. The projections shown are
probabilistic estimates produced by quantitative models and do not
constitute financial or investment advice. Confidence intervals
reflect inherent uncertainty. Past performance does not guarantee
future results.
