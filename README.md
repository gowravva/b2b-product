# 🐾 CatDog AI — B2B Image Classification API

A real B2B SaaS product: **FastAPI backend** + **Streamlit dashboard**.

| Component | Purpose | Deploy On |
|---|---|---|
| `api.py` | REST API — `/predict`, `/usage`, `/plans` | Render.com |
| `app.py` | Dashboard — signup, API key, usage, docs | Streamlit Cloud |

---

## 🏗️ Architecture

```
B2B Developer / Their App
        ↓
POST https://catdog-api.onrender.com/predict
Header: x-api-key: cd_xxxxx
Body:   file=photo.jpg
        ↓
FastAPI (api.py) on Render
        ↓ validate key
SQLite users.db   +   Keras Model (.keras)
        ↓ inference
{"result":"Cat","confidence":0.97,"used":12,"limit":50}
        ↓
B2B Developer gets JSON — integrates into their pet app
```

---

## 🚀 Deploy Step by Step

### Step 1 — Push to GitHub
```bash
git init
git add app.py api.py requirements.txt requirements-api.txt \
        cat_dog_classifier_final.keras .gitignore README.md
git commit -m "CatDog SaaS — FastAPI + Streamlit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/catdog-saas.git
git push -u origin main
```
⚠️ If .keras file > 100MB: `git lfs track "*.keras"` first.

---

### Step 2 — Deploy FastAPI on Render (FREE)
1. Go to [render.com](https://render.com) → New Web Service
2. Connect your GitHub repo
3. Settings:
   - **Build Command:** `pip install -r requirements-api.txt`
   - **Start Command:** `uvicorn api:app --host 0.0.0.0 --port $PORT`
   - **Environment:** Python 3
4. Click Deploy
5. Your API URL: `https://catdog-api.onrender.com`
6. Test: visit `https://catdog-api.onrender.com/docs`

---

### Step 3 — Deploy Streamlit Dashboard (FREE)
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. New App → select repo → select `app.py`
4. Add Secret: `API_BASE_URL = "https://catdog-api.onrender.com"`
5. Click Deploy
6. Dashboard URL: `https://catdog-classifier.streamlit.app`

---

## 📡 API Reference

### POST /predict
```bash
curl -X POST https://catdog-api.onrender.com/predict \
  -H "x-api-key: cd_your_key" \
  -F "file=@photo.jpg"
```
```json
{
  "result": "Cat",
  "confidence": 0.9712,
  "confidence_percent": "97.1%",
  "predictions_used": 12,
  "predictions_limit": 50,
  "tier": "free"
}
```

### GET /usage
```bash
curl https://catdog-api.onrender.com/usage \
  -H "x-api-key: cd_your_key"
```

### GET /plans — No auth needed
```bash
curl https://catdog-api.onrender.com/plans
```

### GET /docs — Interactive docs (browser)
```
https://catdog-api.onrender.com/docs
```

---

## 💰 Pricing
| Plan | Price | Predictions/Month |
|---|---|---|
| Free | ₹0 | 50 |
| Starter | ₹499/mo | 500 |
| Pro | ₹1499/mo | Unlimited |

---

## 🌍 Who Can Use This?
Anyone, anywhere — India, USA, UK, Singapore.
Any language — Python, JS, PHP, Ruby, curl.
Any platform — mobile apps, web apps, backend services.

---


