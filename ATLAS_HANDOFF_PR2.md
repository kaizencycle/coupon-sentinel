# ATLAS Handoff — PR-2: Local Price Memory + Deal Intelligence

**Cycle:** C-396  
**Prior state:** PR-1 merged to `main` @ `90f24eedaee423b950bd433b222be14ae843b7ca`  
**Scope tier:** EP-2 (new schema + deterministic engine, additive only)

## Objective

Turn the PR-1 evidence substrate into local market memory:

```
Individual observations
        ↓
ZIP / retailer / SKU grouping
        ↓
all-time price history (median-based, no decay)
        ↓
local baseline
        ↓
anomaly detection (deviation off baseline)
        ↓
BUY / WAIT / NORMAL signal
```

## Ratified design decisions (do not relitigate)

- Baseline window = **all-time, no decay**
- Baseline statistic = **median**, not mean
- Baseline and confidence are **separate** — freshness only in PR-1 `aggregate_observation_confidence()`
- Below `MIN_BASELINE_SAMPLES` (3) → `INSUFFICIENT_DATA`, not a false-confident signal

## Implementation contract

| Module | Responsibility |
|--------|----------------|
| `backend/price_memory_models.py` | `LocalPriceBaseline`, `RecommendationSignal`, `PriceAnomaly`, `MIN_BASELINE_SAMPLES` |
| `backend/engines/price_memory_engine.py` | `group_observations_by_market`, `compute_local_baseline`, `compute_deviation_pct`, `derive_recommendation_signal`, `build_price_anomaly` |
| `backend/providers/mock_deal_data.py` | Multi-week Tide history, thin-sample yogurt, flat milk |
| `backend/app.py` | `GET /api/price-memory/{product_id}`, `GET /api/anomalies` |

## Threshold constants (engine module top)

- `_STRONG_DEAL_THRESHOLD_PCT = 40.0` — clearance/penny-pull territory, not routine noise
- `_GOOD_DEAL_THRESHOLD_PCT = 15.0` — actionable sale band
- `_NORMAL_BAND_PCT = 15.0` — week-to-week noise band

## Non-goals

No LLM, scraping, OCR UI, `/api/optimize` fusion, inventory inference, or mutations to PR-1 canonical fields.

## Validation

```bash
cd backend && pytest   # full suite including PR-1 regression
cd frontend && npm run build
```

## Witness table (on completion)

| Claim | Evidence |
|-------|----------|
| Baseline median, all-time, no decay | `compute_local_baseline` |
| Confidence independent of baseline | no freshness in `price_memory_engine.py` baseline path |
| `INSUFFICIENT_DATA` below min samples | `derive_recommendation_signal` + tests |
| PR-1 unaffected | `test_optimizer_regression`, `test_deal_api` |
