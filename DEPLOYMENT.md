# Cloud Deployment Guide

## Quick Deploy to Railway.app

### Step 1: Create Railway Account
1. Go to https://railway.app
2. Sign up (GitHub login recommended)

### Step 2: Deploy Your Bot
1. Click **"New Project"**
2. Choose **"Deploy from GitHub repo"** (push code to GitHub first) OR **"Empty Project"** to upload files manually
3. If using Empty Project:
   - Click on your project
   - Click **"New"** → **"GitHub Repo"** (to connect GitHub) OR upload files via CLI

### Step 3: Set Environment Variables
In Railway dashboard, go to **Variables** tab and add:

**Required:**
- `BYBIT_API_KEY` = `IQLf80eQtGNRghf7ux`
- `BYBIT_API_SECRET` = `6qcz3FE9j2cXr8afh2JLSAwA4AD5qHSXi7VC`

**Optional (defaults in code):**
- `SYMBOL_LONG` = `1000000BABYDOGEUSDT`
- `SYMBOL_SHORT` = `DOGUSDT`
- `USD_POSITION_SIZE` = `1500`
- `MAX_USD_POSITION` = `1500`
- `TRIGGER_DROP_PCT` = `8`
- `ENABLE_SCALE_IN` = `False`
- `SCALE_IN_LEGS` = `3`
- `SCALE_IN_DROP_STEP` = `2`

### Step 4: Deploy
Railway will automatically:
- Detect Python
- Install dependencies from `requirements.txt`
- Run using `Procfile`

### Step 5: Monitor
- View logs in Railway dashboard
- Bot runs 24/7 automatically
- Free tier: $5 credit/month (usually enough for this bot)

## Test Locally First
```bash
./test_local.sh
```

## Alternative: Deploy to Render.com

### Step 1: Create Render Account
1. Go to https://render.com
2. Sign up with GitHub (recommended - it will automatically connect your repo)

### Step 2: Deploy Your Bot
1. Click **"New +"** → **"Web Service"**
2. Connect your GitHub account if not already connected
3. Select repository: `gbrack7/heeed`
4. Configure the service:
   - **Name**: `heeed-bot` (or any name)
   - **Region**: Choose closest to you
   - **Branch**: `main`
   - **Root Directory**: Leave empty (or `./`)
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python hedge_server.py`

### Step 3: Set Environment Variables
Scroll to "Environment Variables" section and add:

**Required:**
- `BYBIT_API_KEY` = `IQLf80eQtGNRghf7ux`
- `BYBIT_API_SECRET` = `6qcz3FE9j2cXr8afh2JLSAwA4AD5qHSXi7VC`

**Optional (defaults in code):**
- `SYMBOL_LONG` = `HYPEUSDT`
- `SYMBOL_SHORT` = `JASMYUSDT`
- `USD_POSITION_SIZE` = `1500`
- `TRIGGER_DROP_PCT` = `12`

### Step 4: Deploy
1. Click **"Create Web Service"**
2. Render will build and deploy your bot automatically
3. Check logs - your bot should start running!

**Note:** Render's free tier spins down after 15 minutes of inactivity, but since your bot polls every 30 seconds, it should stay active.

## Alternative Platforms
- **DigitalOcean App Platform**: $5/month, simple setup, static IPs available
- **Fly.io**: Good for small apps, free tier, containerized
- **Railway.app**: $5/month (what we tried first - IPs might be blocked by Bybit)
