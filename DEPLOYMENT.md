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

## Option 1: Render + Vercel (Recommended)

### Deploy Backend to Render

1. **Create Render account** at [render.com](https://render.com)

2. **Connect your GitHub repo**

3. **Create a new Web Service:**
   - Name: `coupon-sentinel-api`
   - Root Directory: *(leave empty - use repo root)*
   - Runtime: Python 3
   - Build Command: `pip install -r backend/requirements.txt`
   - Start Command: `uvicorn backend.app:app --host 0.0.0.0 --port $PORT`

4. **Deploy!** Your API will be at: `https://coupon-sentinel-api.onrender.com`

### Deploy Frontend to Vercel

1. **Install Vercel CLI:**
   ```bash
   npm i -g vercel
   ```

2. **Deploy:**
   ```bash
   cd frontend
   vercel
   ```

3. **Set environment variable** in Vercel dashboard:
   - `VITE_API_URL` = `https://coupon-sentinel-api.onrender.com`

4. **Redeploy** to apply the environment variable.

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
   - **Backend:** Use repo root, start command: `uvicorn backend.app:app --host 0.0.0.0 --port $PORT`
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

### Backend won't start on Render

- Check Python version (needs 3.10+)
- Verify `requirements.txt` includes all dependencies
- Check build logs for errors
- **ModuleNotFoundError: No module named 'backend'** - Make sure you're using the start command `uvicorn backend.app:app --host 0.0.0.0 --port $PORT` from the repo root (not from the `backend/` subdirectory)

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
