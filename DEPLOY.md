# Primeline Position Sizer — Deployment Guide

## Run Locally (instant)

```bash
cd /Users/aleexorlov/Documents/Claude/Projects/Primeline/position-sizer-app
pip install -r requirements.txt
streamlit run app.py
```

App opens at http://localhost:8501

---

## Deploy to Streamlit Cloud (free, shareable URL)

Anyone with the link can use the tool — no install, no Python, just a browser.

### Step 1 — Push to GitHub

```bash
cd /Users/aleexorlov/Documents/Claude/Projects/Primeline/position-sizer-app
git init
git add app.py requirements.txt .streamlit/config.toml
git commit -m "feat: Primeline Position Sizer v2.0"
git remote add origin https://github.com/YOUR_USERNAME/primeline-position-sizer.git
git push -u origin main
```

> ⚠️ Do NOT commit credentials.json, token.json, or config.json — those stay local.

### Step 2 — Connect to Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. Click **New app**
4. Select your repo → branch `main` → file `app.py`
5. Click **Deploy**

Streamlit gives you a URL like:  
`https://your-username-primeline-position-sizer-app-xxxx.streamlit.app`

Share that URL with anyone — they just need an Alpha Vantage API key.

### Step 3 — Optional: Pre-fill the API key via Streamlit Secrets

In Streamlit Cloud → **Settings → Secrets**, add:
```toml
AV_API_KEY = "QYW38J8TNDWPHAD4"
```

Then in `app.py` sidebar, replace the default value line with:
```python
import os
value=st.session_state.get("av_api_key", os.environ.get("AV_API_KEY", "")),
```

This pre-fills the key so users don't need to enter it.

---

## Files

```
position-sizer-app/
├── app.py                  ← Main Streamlit app
├── requirements.txt        ← Python deps (streamlit, requests, pandas)
└── .streamlit/
    └── config.toml         ← Dark theme, Primeline gold accent
```

## Alpha Vantage API Limits (free tier)

- 25 requests/day
- 5 requests/minute  
- Each Fetch = 2 requests (price history + company overview)
- ~12 position sizing runs per day on the free tier
- Premium key ($50/mo): unlimited requests
