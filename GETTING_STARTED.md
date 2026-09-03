# 🚀 Getting Started with Coupon Sentinel

This guide will get you up and running in 5 minutes.

---

## Prerequisites

- **Python 3.10+** (for backend)
- **Node.js 18+** (for frontend)
- **npm** or **yarn**

---

## Quick Start

### 1. Start the Backend

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv .venv

# Activate it
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn backend.app:app --reload --port 8000
```

**Backend is now running at:** http://localhost:8000

**API docs available at:** http://localhost:8000/docs

By default the backend uses a local SQLite file (`backend/coupon_sentinel.db`,
auto-created on startup) for the auth/billing/evidence tables — no Postgres
setup needed for local dev. Set `DATABASE_URL` (see `.env.example`) to point
at Postgres instead; then run migrations explicitly with:

```bash
cd backend
alembic upgrade head
```

### Try the real auth + billing endpoints

```bash
# Register (returns access_token + refresh_token)
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "password123"}'

# Use the access_token to fetch your profile
curl http://localhost:8000/api/user/profile \
  -H "Authorization: Bearer <access_token>"

# List subscription plans (free/pro/premium tier matrix)
curl http://localhost:8000/api/subscriptions/plans
```

`POST /api/user/subscription` and the Stripe webhook return `503` until
`STRIPE_SECRET_KEY` (and `STRIPE_PRICE_ID_PRO` / `STRIPE_PRICE_ID_PREMIUM`)
are set — that's intentional: it fails loudly instead of pretending to bill
someone with no real Stripe account behind it. Same pattern for
`POST /api/auth/resend-verification`, which needs `RESEND_API_KEY` or
`SENDGRID_API_KEY`.

### Try the auth + subscription UI

With both the backend (above) and frontend (`cd frontend && npm run dev`)
running, open http://localhost:5173 and click the **Account** tab: register,
view your profile, list plans, and try subscribing/verifying — both will
show a clean "not configured" error rather than fail silently, since this
project has no real Stripe or email-provider credentials yet. Set
`VITE_STRIPE_PUBLIC_KEY` (`frontend/.env.example`) to render an actual
Stripe payment form instead of that message.

### 2. Start the Frontend

In a new terminal:

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

**Frontend is now running at:** http://localhost:5173

---

## Test It Out

1. Open http://localhost:5173 in your browser
2. Add some items to your shopping list:
   - "milk"
   - "eggs"
   - "bread"
   - "chicken"
3. Select stores (Target, Walmart, Costco)
4. Toggle "Allow multi-store shopping" if you want
5. Click **"Find Best Deals"**
6. See your optimized shopping plan! 🎉

---

## Test the API Directly

### Health Check

```bash
curl http://localhost:8000/health
```

### List Stores

```bash
curl http://localhost:8000/api/stores
```

### List Available Items

```bash
curl http://localhost:8000/api/items
```

### Optimize Shopping List

```bash
curl -X POST http://localhost:8000/api/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "shopping_list": [
      {"name": "milk", "quantity": 1, "unit": "gallon", "flexible": true},
      {"name": "eggs", "quantity": 12, "unit": "count", "flexible": true},
      {"name": "bread", "quantity": 1, "unit": "count", "flexible": true}
    ],
    "zip_code": "11566",
    "preferred_stores": ["Target", "Walmart"],
    "allow_multi_store": false,
    "rebate_apps": ["Ibotta"]
  }'
```

---

## Project Structure

```
coupon-sentinel/
├── backend/                  # Python FastAPI backend
│   ├── app.py               # Main API
│   ├── models.py            # Data models
│   ├── requirements.txt     # Python dependencies
│   ├── engines/             # Optimization logic
│   │   ├── pricing_engine.py
│   │   └── stacking_logic.py
│   └── providers/           # Data sources
│       └── mock_data.py
│
├── frontend/                # React + TypeScript frontend
│   ├── src/
│   │   ├── App.tsx          # Main component
│   │   ├── types.ts         # TypeScript types
│   │   ├── api/client.ts    # API client
│   │   └── components/      # React components
│   ├── package.json
│   └── vite.config.ts
│
├── README.md                # Project overview
├── GETTING_STARTED.md       # This file
└── docker-compose.yml       # Docker config
```

---

## Common Issues

### Backend won't start

**Error:** `ModuleNotFoundError: No module named 'fastapi'`

**Fix:** Make sure you activated the virtual environment and installed dependencies:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### Frontend can't reach backend

**Error:** "Failed to fetch" or network errors

**Fix:** Make sure the backend is running on port 8000. The Vite proxy is configured to forward `/api` requests automatically.

### No items found

The mock data includes common grocery items. Try searching for:
- milk, eggs, bread
- chicken, beef
- pasta, sauce
- chips, tortilla
- coffee, juice

---

## Next Steps

1. **Customize mock data:** Edit `backend/providers/mock_data.py` to add your local stores and prices

2. **Deploy:** Follow [DEPLOYMENT.md](DEPLOYMENT.md) to deploy to Render, Vercel, etc.

3. **Add real data sources:** Create provider files in `backend/providers/` for real store APIs

4. **Extend the UI:** Add new features like:
   - Price history charts
   - Saved shopping lists
   - Receipt scanning

---

## Need Help?

- Check the API docs at http://localhost:8000/docs
- Open an issue on GitHub
- Read the main [README.md](README.md)

---

**Happy couponing! 🛒💰**
