# 🚀 Deployment Guide

Deploy Coupon Sentinel to production in minutes.

---

## Quick Deploy Options

| Platform | Backend | Frontend | Cost |
|----------|---------|----------|------|
| **Render + Vercel** | ✅ | ✅ | Free tier |
| **Railway** | ✅ | ✅ | $5/month |
| **Docker (self-hosted)** | ✅ | ✅ | Varies |

---

## Option 1: Render (Recommended - Easiest)

### Deploy with render.yaml (Automatic Configuration)

1. **Create Render account** at [render.com](https://render.com)

2. **Connect your GitHub repo**

3. **Render will automatically detect `render.yaml`** and create both services:
   - Backend API: `coupon-sentinel-api`
   - Frontend: `coupon-sentinel-frontend`

4. **After backend deploys**, set the `VITE_API_URL` environment variable in the frontend service:
   - Go to Render Dashboard → Frontend Service → Environment
   - Add: `VITE_API_URL` = `https://coupon-sentinel-api.onrender.com`
   - Redeploy the frontend

5. **Done!** Both services will auto-deploy on every push.

### Manual Deploy (Alternative)

If you prefer manual configuration:

1. **Create Render account** at [render.com](https://render.com)

2. **Connect your GitHub repo**

3. **Create a new Web Service:**
   - Name: `coupon-sentinel-api`
   - Root Directory: *(leave empty - use repo root)*
   - Runtime: Python 3
   - Build Command: `pip install -r backend/requirements.txt`
   - Start Command — **use one of these** (do **not** use bare `uvicorn backend.app:app` without `PYTHONPATH`):
     - **Option 1 (Recommended):** `python3 backend/run.py`
     - **Option 2:** `./start.sh`
     - **Option 3:** `python -m uvicorn wsgi:app --host 0.0.0.0 --port $PORT`
     - **Option 4:** `PYTHONPATH=. uvicorn backend.app:app --host 0.0.0.0 --port $PORT`

4. **Deploy!** Your API will be at: `https://coupon-sentinel-api.onrender.com`

### Deploy Frontend to Vercel (recommended for UI)

The receipt-themed UI lives in `frontend/` (`index.html`, `src/index.css`, `src/App.css`, `src/App.tsx`, `src/components/*`).

1. **Vercel Dashboard → Project → Settings → General**
   - **Root Directory:** `frontend` (required — app is not at repo root)
   - Framework Preset: Vite (or use `frontend/vercel.json`)

2. **Environment Variables** (Production):
   - `VITE_API_URL` = `https://coupon-sentinel-api.onrender.com` (your Render API URL)

3. **Redeploy** production after env changes (Vite bakes `VITE_API_URL` at build time).

4. **CLI alternative:**
   ```bash
   npm i -g vercel
   cd frontend
   vercel link
   vercel --prod
   ```

Production URL (if linked to this repo): [https://coupon-sentinel.vercel.app](https://coupon-sentinel.vercel.app)

### Vercel stuck on an old PR branch (e.g. PR #10 / December 2025)

**Do not use "Redeploy" on an old Production row** (e.g. merge PR #10 / `d2fea3a` from 12/17/25). That re-runs the *old* build config and often fails. Production is still serving that December build until you deploy **current `main`**.

If the dashboard only lists old branches:

1. **Settings → Git → Production Branch** → `main` (reconnect Git if `main` is missing).
2. **Settings → General → Root Directory** → leave **empty** (repo root; `vercel.json` builds `frontend/`) **or** set `frontend` (uses `frontend/vercel.json`).
3. **Deployments → Create Deployment** → Branch **`main`** → Deploy (not Redeploy of an old ID).

**GitHub Actions** (after PR #20): add secrets `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`. Check **Actions** tab — failed runs mean secrets are missing or CLI version was wrong.

**CLI one-off deploy:**

```bash
git checkout main
cd frontend
npm i -g vercel
vercel login
vercel link    # pick the coupon-sentinel project
vercel --prod  # deploys current main to production
```

**CI fix (recommended):** merge `.github/workflows/vercel-frontend-production.yml` and add GitHub Actions secrets:

| Secret | Where to find it |
|--------|------------------|
| `VERCEL_TOKEN` | [vercel.com/account/tokens](https://vercel.com/account/tokens) |
| `VERCEL_ORG_ID` | Team Settings → General, or `frontend/.vercel/project.json` after `vercel link` |
| `VERCEL_PROJECT_ID` | Project → Settings → General → Project ID |
| `VITE_API_URL` | Optional if already set in Vercel env — `https://coupon-sentinel-api.onrender.com` |

Every push to `main` that touches `frontend/` will then deploy production without relying on the Vercel branch picker.

---

## Option 2: Docker Compose (Self-Hosted)

### Local Docker

```bash
# Build and start both services
docker-compose up --build

# Access:
# - Frontend: http://localhost:3000
# - Backend: http://localhost:8000
```

### Production Docker

1. **Update `docker-compose.yml`** for production:
   - Change ports if needed
   - Add SSL termination (nginx reverse proxy or load balancer)
   - Configure environment variables

2. **Deploy to any Docker host:**
   ```bash
   docker-compose -f docker-compose.yml up -d
   ```

---

## Option 3: Railway

1. **Create Railway account** at [railway.app](https://railway.app)

2. **Create new project from GitHub**

3. **Add two services:**
   - **Backend:** Use repo root, start command: `PYTHONPATH=. uvicorn backend.app:app --host 0.0.0.0 --port $PORT`
   - **Frontend:** Set root to `frontend`, Railway auto-detects Vite

4. **Add environment variable** to frontend:
   - `VITE_API_URL` = Railway backend URL

---

## Environment Variables

### Backend

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PORT` | Yes | `8000` | Server port (set by platform) |
| `ENVIRONMENT` | No | `development` | `development` or `production` |
| `LOG_LEVEL` | No | `INFO` | Logging level |

### Frontend

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_API_URL` | Yes* | (empty) | Backend API URL |

*Required in production. In development, Vite proxy handles it.

---

## Production Checklist

- [ ] Backend deployed and accessible
- [ ] Frontend deployed and accessible
- [ ] `VITE_API_URL` set correctly
- [ ] CORS configured in backend (update `allow_origins`)
- [ ] Health check endpoint working (`/health`)
- [ ] HTTPS enabled (most platforms do this automatically)
- [ ] Test end-to-end flow

---

## Monitoring

### Health Check

```bash
curl https://your-backend-url.onrender.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "database": "mock_data",
  "features": {
    "multi_store": true,
    "coupon_stacking": true,
    "rebate_tracking": true
  }
}
```

### Render Logs

View in Render dashboard or use CLI:
```bash
render logs -s coupon-sentinel-api
```

---

## Cost Estimates

| Platform | Free Tier | Paid |
|----------|-----------|------|
| Render | 750 hrs/month | $7/month |
| Vercel | 100GB bandwidth | $20/month |
| Railway | $5 credit/month | ~$5-10/month |

**Hobby project:** $0/month on free tiers

---

## Troubleshooting

### Build fails: `No such file or directory: 'requirements.txt'`

Render is running `pip install -r requirements.txt` from the **repo root**, but deps are under `backend/`. Fix either:

1. **Dashboard → Build Command:** `pip install -r backend/requirements.txt` (Root Directory empty)
2. **Or** use the repo root `requirements.txt` (includes `-r backend/requirements.txt`) with build command `pip install -r requirements.txt`

After PR merge, both paths work from repo root.

### Backend won't start on Render

- Check Python version (needs 3.10+)
- Verify `requirements.txt` includes all dependencies
- Check build logs for errors
- **ModuleNotFoundError: No module named 'backend'** — Render is starting with `uvicorn backend.app:app` without the repo root on `PYTHONPATH`. **Fix:** In Render Dashboard → your API service → **Settings** → **Start Command**, set:
  ```bash
  python3 backend/run.py
  ```
  Then **Manual Deploy** → Deploy latest commit. Also confirm **Root Directory** is empty (repo root), not `backend`.

### Frontend can't reach backend

- Verify `VITE_API_URL` is set correctly
- Check for mixed content issues (https → http)
- Test backend directly with curl

### CORS errors

Update `backend/app.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend.vercel.app"],
    # ... rest of config
)
```

---

## Custom Domain

### Render
1. Dashboard → Settings → Custom Domains
2. Add your domain
3. Configure DNS (CNAME)

### Vercel
1. Dashboard → Settings → Domains
2. Add your domain
3. Configure DNS (Vercel provides instructions)

---

**Questions?** Check the main [README.md](README.md) or open an issue.
