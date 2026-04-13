# 📋 DEPLOYMENT GUIDE — Read This First

## Files Overview
```
catdog-saas/
├── app.py                           ← Streamlit Dashboard (deploy on Streamlit Cloud)
├── api.py                           ← FastAPI Backend     (deploy on Render.com)
├── requirements.txt                 ← For Streamlit Cloud
├── requirements-api.txt             ← For Render.com (lighter)
├── cat_dog_classifier_final.keras   ← Your model (YOU must add this file)
├── .gitignore                       ← Excludes users.db and secrets
├── .streamlit/
│   ├── config.toml                  ← Dark theme
│   └── secrets.toml.template        ← Add API_BASE_URL here (rename to secrets.toml locally)
└── README.md
```

## ⚠️ BEFORE YOU PUSH TO GITHUB
1. Copy your model file to this folder:
   cat_dog_classifier_final.keras

2. If model > 100MB:
   git lfs install
   git lfs track "*.keras"
   git add .gitattributes

3. NEVER push:
   - users.db
   - .streamlit/secrets.toml
   - .env

## LOCAL TESTING
```bash
# Terminal 1 — run FastAPI
pip install -r requirements-api.txt
uvicorn api:app --reload --port 8000
# Visit: http://localhost:8000/docs

# Terminal 2 — run Streamlit
pip install streamlit requests
API_BASE_URL=http://localhost:8000 streamlit run app.py
# Visit: http://localhost:8501
```

## PRODUCTION FLOW
1. User signs up on Streamlit dashboard
2. Gets API key (e.g. cd_abc123...)
3. Calls FastAPI /predict with key + image
4. FastAPI validates key from shared users.db
5. Keras model runs inference
6. Returns JSON with result + confidence
7. Usage counter increments in DB

## SHARED DATABASE
Both app.py and api.py read/write the SAME users.db file.
- On Streamlit Cloud: users.db lives in the Streamlit container
- On Render: users.db lives in the Render container
⚠️ They are SEPARATE files on different servers!

SOLUTION — Use one of:
Option A: Render hosts users.db, Streamlit calls FastAPI for ALL DB operations
Option B: Move to PostgreSQL on Supabase (free) — one shared DB for both

For MVP: run BOTH app.py and api.py on Render as two separate services
pointing to the same Render disk / PostgreSQL database.
