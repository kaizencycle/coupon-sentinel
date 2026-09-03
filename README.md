# 🛒 Coupon Sentinel

**Consumer-side savings intelligence — evidence before recommendation.**

A grocery optimization engine that finds the cheapest way to fulfill your shopping list by automatically stacking coupons, comparing stores, and tracking rebates. PR-1 adds the canonical deal-intelligence foundation: normalized price observations, evidence types, deal events, and effective-price calculations — without replacing the existing optimizer.

---

## 🎯 What It Does

Coupon Sentinel takes your shopping list and:

1. **Searches** across multiple grocery stores (Target, Walmart, Costco, etc.)
2. **Compares** prices including package sizes and unit costs
3. **Stacks** coupons intelligently:
   - Manufacturer coupons
   - Store coupons
   - Loyalty discounts
   - Rebate apps (Ibotta, Fetch)
4. **Optimizes** for either:
   - Single store convenience
   - Multi-store maximum savings
5. **Generates** a step-by-step shopping plan

**Deal Intelligence (PR-1)** surfaces evidence-backed deal events derived from price observations — receipts, retailer listings, community reports — with provenance, confidence, and inventory uncertainty visible to the consumer.

**Architecture principle (never collapse these layers):**

```
Evidence → PriceObservation → DealEvent → Consumer recommendation
```

Observation ≠ Interpretation ≠ Recommendation. AI-generated recommendations are never the source of truth.

**Example Output:**
```
Shop at Target:
  • Clip digital coupon: $1 off dairy
  • Buy: 1× Good & Gather Milk (1 gallon) = $2.99
  • Buy: 2× Good & Gather Eggs (12 count) = $7.54
  • Submit receipt to Ibotta for $0.75 cashback

Total: $10.53 (saved $3.42 vs full price)
```

---

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone the repo
git clone https://github.com/kaizencycle/coupon-sentinel.git
cd coupon-sentinel

# docker-compose requires JWT_SECRET (no insecure default — see .env.example)
cp .env.example .env
echo "JWT_SECRET=$(openssl rand -base64 32)" >> .env

# Start frontend, backend, Postgres, and Redis
docker-compose up --build

# Open http://localhost:3000
```

### Option 2: Local Development

**Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Visit:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## 📐 Architecture

```
coupon-sentinel/
├── backend/               # FastAPI service
│   ├── app.py            # API endpoints
│   ├── models.py         # Optimizer Pydantic models
│   ├── deal_models.py    # Deal intelligence canonical models (PR-1)
│   ├── engines/
│   │   ├── pricing_engine.py     # Core optimization logic
│   │   ├── stacking_logic.py     # Coupon stacking rules
│   │   └── deal_engine.py        # Effective price + evidence aggregation
│   ├── providers/
│   │   ├── mock_data.py          # Mock store/coupon data
│   │   └── mock_deal_data.py     # Mock observations/deals (fixtures)
│   └── tests/
│
├── frontend/             # React + TypeScript UI
│   ├── src/
│   │   ├── App.tsx              # Main application + nav
│   │   ├── types.ts             # Type definitions
│   │   ├── api/
│   │   │   └── client.ts        # API client
│   │   └── components/
│   │       ├── ShoppingListInput.tsx
│   │       ├── StoreSelector.tsx
│   │       ├── SavingsSummary.tsx
│   │       ├── OptimizedPlan.tsx
│   │       └── DealsView.tsx    # Deal intelligence UI (PR-1)
│   └── package.json
│
├── docker-compose.yml    # Container orchestration
└── README.md
```

---

## 🧮 How the Optimization Works

### 1. **Item Matching**
```python
# User inputs: "milk"
# System finds:
- Target: Good & Gather Milk (1 gal) = $3.99
- Walmart: Great Value Milk (1 gal) = $3.49
- Costco: Kirkland Milk (2 gal) = $6.49 ($3.25/gal)
```

### 2. **Coupon Stacking**
```python
# US grocery rules (implemented in stacking_logic.py):
- 1 manufacturer coupon per item
- Store coupons stack with manufacturer
- Rebates stack with everything
- BOGO has special rules
```

**Example Stack:**
```
Base price: $3.99
- Store coupon: -$1.00
- Manufacturer coupon: -$0.50
- Ibotta rebate: -$0.25
Final: $2.24 (saved $1.75)
```

### 3. **Basket Optimization**
```python
# Single store mode: Pick store with lowest total
# Multi-store mode: Pick cheapest source per item
```

---

## 🛠️ Tech Stack

**Backend:**
- **FastAPI** - Modern Python web framework
- **Pydantic** - Data validation
- **uvicorn** - ASGI server

**Frontend:**
- **React** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool

**Deployment:**
- **Docker** - Containerization
- **Render** / **Railway** / **Fly.io** compatible

---

## 📊 API Endpoints

### `POST /api/optimize`
Main optimization endpoint.

**Request:**
```json
{
  "shopping_list": [
    {"name": "milk", "quantity": 1, "unit": "gallon", "flexible": true},
    {"name": "eggs", "quantity": 12, "unit": "count", "flexible": true}
  ],
  "zip_code": "12345",
  "preferred_stores": ["Target", "Walmart"],
  "allow_multi_store": false,
  "rebate_apps": ["Ibotta"]
}
```

**Response:**
```json
{
  "plans": [
    {
      "store_name": "Target",
      "items": [...],
      "final_total": 10.53,
      "estimated_savings": 3.42
    }
  ],
  "grand_total": 10.53,
  "total_savings": 3.42,
  "savings_percentage": 24.5,
  "action_steps": ["Clip coupon...", "Buy..."]
}
```

### Other Endpoints:
- `GET /api/stores` - List available stores
- `GET /api/items` - List inventory
- `GET /api/coupons` - List available coupons
- `GET /api/deals` - List deal events (mock fixtures, read-only)
- `GET /api/deals/{deal_id}` - Single deal with provenance
- `GET /api/price-observations` - Normalized price observations
- `GET /api/price-memory/{product_id}` - Local median baseline (PR-2)
- `GET /api/anomalies` - Price anomalies and recommendation signals (PR-2)
- `POST /api/optimize/with-deal-context` - Optimize plus optional per-item deal context (PR-3)
- `GET /health` - Health check

**Product identity bridge (PR-3):** Optimizer `StoreItem` rows may carry an optional `product_id` linking to deal-intelligence `ProductIdentity`. After this PR only a few mock catalog overlaps are bridged (Walmart whole milk, 12-count eggs, whole wheat bread). Most catalog rows remain unbridged — `deal_context` is `null`, not an error. Full coverage is a fixture-data follow-up, not a code gap.

---

## 🎨 Features

### V0 (Current)
- ✅ Multi-store price comparison
- ✅ Coupon stacking engine
- ✅ Single vs multi-store optimization
- ✅ Unit price calculation
- ✅ Mock data for testing
- ✅ Clean React UI
- ✅ Canonical deal intelligence models (PR-1)
- ✅ Price observations + deal events API
- ✅ Effective-price engine
- ✅ Minimal Deals UI with provenance display
- ✅ Local price memory + BUY/WAIT signals (PR-2)
- ✅ Product identity bridge + deal-aware optimize endpoint (PR-3, partial catalog)

### Phase 1 MVP progress (Micro-SaaS build)

Milestone 1 (Backend Foundation) is implemented — real Postgres-backed
persistence sits alongside the existing unauthenticated mock-data optimizer,
which is untouched:

- [x] PostgreSQL schema + Alembic migrations (`backend/migrations/`, `DATABASE_URL`; defaults to local SQLite for dev/tests)
- [x] JWT auth: `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/refresh`, `GET /api/user/profile`
- [x] Stripe scaffolding: `POST /api/user/subscription`, `DELETE /api/user/subscription`, `GET /api/subscriptions/plans`, `POST /api/webhooks/stripe` (`backend/engines/subscription_engine.py`) — returns `503` until real Stripe keys are set, by design
- [x] Tier gating dependency (`backend/auth.py:require_tier`) ready for endpoints that should require Pro/Premium
- [x] Unit tests for auth + subscription flows (`backend/tests/test_auth.py`, `backend/tests/test_subscription_api.py`), CI running the full suite on every PR (`.github/workflows/backend-ci.yml`)

Milestone 2 (Kroger Integration) is partially implemented:

- [x] Kroger OAuth2 client-credentials client, product search, price lookup, sliding-window rate limiter (`backend/providers/kroger.py`) — unit-tested against a mocked HTTP transport (`backend/tests/test_kroger_client.py`); **not yet verified against Kroger's live API, since no `KROGER_CLIENT_ID`/`KROGER_CLIENT_SECRET` exist for this project**
- [x] `GET /api/kroger/search`, `GET /api/kroger/products/{id}` — persist results as `price_observations` rows with `source=kroger_api` (`backend/kroger_routes.py`, `backend/engines/kroger_price_engine.py`); return `503` until credentials are set, by design
- [ ] Not done: wiring Kroger data into `/api/optimize` (the mock-data optimizer is untouched), store-location lookup, digital coupon endpoint, frontend store selector using real data

**Not yet built** (needs real accounts/credentials + further sessions, roughly Milestones 3-7 of the phase-1 plan):
deal-inference engine wired to live data, email verification, frontend auth/billing/dashboard pages, Mixpanel/Sentry, and production deployment of this new surface. The mock-data optimizer (`/api/optimize`, `/api/deals`, etc.) and its frontend remain fully functional and are not gated by auth.

### V1 (Roadmap)
- [ ] Real store API integrations (public data only)
- [ ] Rebate app APIs (Ibotta, Fetch)
- [ ] Local/community observation aggregation by ZIP/store/SKU
- [ ] Observation independence modeling (source identity)
- [ ] Price history tracking
- [ ] Receipt ingestion (normalized, privacy-minimized)
- [ ] BUY / WAIT recommendations (interpretation layer)

### V2 (Future)
- [ ] User accounts & saved lists (optional, privacy-first)
- [ ] Mobile app (React Native)
- [ ] Push notifications for verified deals only
- [ ] Meal planning integration

---

## 🧪 Development

### Running Tests
```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm test
```

### Code Structure

**Adding a New Store:**
```python
# backend/providers/your_store.py
def get_store_items() -> List[StoreItem]:
    return [
        StoreItem(
            store_name="NewStore",
            item_name="Product Name",
            # ... etc
        )
    ]
```

**Adding a New Feature:**
1. Update `models.py` with new data structures
2. Implement logic in `engines/`
3. Add API endpoint in `app.py`
4. Create React component in `frontend/src/components/`

---

## 🤝 Contributing

This is a side project, but contributions welcome!

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push (`git push origin feature/amazing`)
5. Open a Pull Request

---

## ⚖️ Legal & Ethics

### What This Bot Does:
- ✅ Uses publicly available prices
- ✅ Respects store Terms of Service
- ✅ Recommends legal coupon stacking
- ✅ Helps consumers save money

### What This Bot Does NOT Do:
- ❌ Scrape behind login walls
- ❌ Auto-redeem coupons without consent
- ❌ Exploit system vulnerabilities
- ❌ Use insider pricing data
- ❌ Build behavioral surveillance profiles from receipts
- ❌ Rank deals by affiliate commission
- ❌ Claim inventory without evidence
- ❌ Present AI output as source of truth

**Consumer protection guardrails (PR-1):**
1. Public or user-contributed information only.
2. No unauthorized access to retailer systems.
3. No bypassing login/access controls.
4. No claims of inventory without evidence.
5. No claiming personalized pricing from one observation.
6. Price anomalies are observations, not accusations.
7. No ranking by affiliate commission.
8. Consumer privacy takes priority over behavioral monetization.
9. Receipt data minimized after extracting market facts.
10. Every displayed deal traceable to provenance.

**Design Philosophy:** This is a **financial literacy tool**, not a loophole exploit. A receipt is evidence of a transaction, not permission to profile the consumer.

---

## 📄 License

MIT License - see [LICENSE](LICENSE)

---

## 🙏 Acknowledgments

Built by [kaizencycle](https://github.com/kaizencycle)

Part of a larger vision: returning economic surplus directly to people.

---

## 💬 Support

- **Issues:** [GitHub Issues](https://github.com/kaizencycle/coupon-sentinel/issues)
- **Discussions:** [GitHub Discussions](https://github.com/kaizencycle/coupon-sentinel/discussions)

---

**"Sometimes the most radical thing an AI can do is help someone afford groceries." 🧾**
