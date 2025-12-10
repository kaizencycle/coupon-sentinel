# 🛒 Coupon Sentinel

**Extreme couponing, automated.**

A grocery optimization engine that finds the cheapest way to fulfill your shopping list by automatically stacking coupons, comparing stores, and tracking rebates.

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

# Start both frontend and backend
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
│   ├── models.py         # Pydantic data models
│   ├── engines/
│   │   ├── pricing_engine.py     # Core optimization logic
│   │   └── stacking_logic.py     # Coupon stacking rules
│   └── providers/
│       └── mock_data.py           # Mock store/coupon data
│
├── frontend/             # React + TypeScript UI
│   ├── src/
│   │   ├── App.tsx              # Main application
│   │   ├── types.ts             # Type definitions
│   │   ├── api/
│   │   │   └── client.ts        # API client
│   │   └── components/
│   │       ├── ShoppingListInput.tsx
│   │       ├── StoreSelector.tsx
│   │       ├── SavingsSummary.tsx
│   │       └── OptimizedPlan.tsx
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
- `GET /health` - Health check

---

## 🎨 Features

### V0 (Current)
- ✅ Multi-store price comparison
- ✅ Coupon stacking engine
- ✅ Single vs multi-store optimization
- ✅ Unit price calculation
- ✅ Mock data for testing
- ✅ Clean React UI

### V1 (Roadmap)
- [ ] Real store API integrations
- [ ] Rebate app APIs (Ibotta, Fetch)
- [ ] Price history tracking
- [ ] User accounts & saved lists
- [ ] Receipt OCR
- [ ] Price predictions ("Wait 3 days")

### V2 (Future)
- [ ] Mobile app (React Native)
- [ ] Push notifications for deals
- [ ] Community price submissions
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

**Design Philosophy:** This is a **financial literacy tool**, not a loophole exploit.

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
