# Deploying to Render

End-to-end: GitHub repo → two Render services (backend + frontend) →
public URL you can share. Free tier on both. ~10 minutes.

---

## 1. Push the repo to GitHub

From the repo root in PowerShell:

```powershell
git init                          # if not already a git repo
git add .
git commit -m "Initial commit"

# Create the repo on GitHub first (any name), then:
git branch -M main
git remote add origin https://github.com/<your-handle>/echoframe-argentina-re.git
git push -u origin main
```

`.gitignore` already excludes `.env`, `node_modules`, `__pycache__`,
`dist`, etc. Confirm with `git status` before committing if you want.

---

## 2. Create a Render account

Go to [render.com](https://render.com) → sign up with GitHub. Grant
Render read access to the repo.

---

## 3. Use the blueprint

In the Render dashboard:

1. Click **New** → **Blueprint**.
2. Pick the GitHub repo you just pushed.
3. Render reads [`render.yaml`](render.yaml) and shows two services:
   - `echoframe-argentina-api` (FastAPI backend)
   - `echoframe-argentina-web` (static React frontend)
4. Click **Apply**.

Render will create both services but will pause for missing secrets.

---

## 4. Fill in the env vars

The blueprint marks four secrets as `sync: false` — they're not in the
repo and you set them per-service in the dashboard.

### `echoframe-argentina-api` (backend)
Under **Environment** add:

| Key | Value |
|---|---|
| `NEWSDATA_API_KEY` | your NewsData.io key |
| `FRED_API_KEY` | your FRED key |
| `ANTHROPIC_API_KEY` | your Claude key (`sk-ant-api03-…`) |

### `echoframe-argentina-web` (frontend)
Under **Environment** add:

| Key | Value |
|---|---|
| `VITE_API_URL` | the backend URL Render assigned, e.g. `https://echoframe-argentina-api.onrender.com` |

`VITE_API_URL` is baked into the static bundle at build time — you must
trigger a manual redeploy of the frontend after setting this value
(Dashboard → frontend service → **Manual Deploy → Deploy latest commit**).

---

## 5. First deploy

The backend build will:
1. Install Python deps (`requirements.txt`)
2. Run `scripts/run_backtest.py` to generate model diagnostics
3. Start `uvicorn main:app`

Expect ~3 minutes for the first build (PyMC, NumPy, scipy, hmmlearn all
take time to wheel). The free instance sleeps after 15 minutes of
inactivity, so the first request after a quiet period will take ~20s
to warm up — subsequent requests are fast.

The frontend is a 1-minute static build; once deployed it's served
from Render's CDN globally, no cold starts.

---

## 6. Test the live deploy

Backend health (replace with your URL):

```
https://echoframe-argentina-api.onrender.com/health
```

Should return `{"status": "healthy", …}`.

Frontend:

```
https://echoframe-argentina-web.onrender.com
```

Open it in a browser. The dashboard should render with the status bar
at the top, the navy executive card, the section grid, and the maps.

---

## 7. Tighten CORS (recommended)

`render.yaml` sets `CORS_ORIGINS=["*"]` for the first deploy so nothing
breaks. Once both services are up, swap to the real frontend URL:

In the backend service's Environment tab, edit `CORS_ORIGINS` to:

```
["https://echoframe-argentina-web.onrender.com"]
```

Save → Render redeploys automatically.

---

## 8. Sharing

Send the frontend URL to your client. That's it.

If you want a custom domain (`re.echoframe.io` or similar):
1. In the frontend service → **Settings** → **Custom Domain** → Add.
2. Render gives you a CNAME target — set it in your DNS provider.
3. Render auto-issues a Let's Encrypt certificate.

Same flow for the backend if you want a clean API hostname.

---

## Local development still works

`.env` and `node_modules` stay gitignored. To run locally exactly like
production:

```powershell
# Terminal 1
cd backend
uvicorn main:app --reload

# Terminal 2
cd frontend
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

---

## Costs

Free tier covers:
- 1 web service (the backend) — 512MB, 0.5 vCPU, sleeps after 15 min idle
- 1 static site (the frontend) — unlimited bandwidth on CDN
- 750 build minutes/month

If your client uses the dashboard frequently and the cold-start delay
is a problem, upgrade the backend to the **Starter** plan ($7/month)
which removes sleep. Frontend stays free.

Anthropic / NewsData / FRED bill separately on their own metering. The
narrative service caches each briefing for 20 minutes server-side, so
typical usage is ≤ 1 Claude call per page view.
