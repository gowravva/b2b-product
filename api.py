"""
CatDog AI — FastAPI Backend
Deploy on Render.com as a Web Service.
"""

from fastapi import FastAPI, UploadFile, File, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import sqlite3
import datetime
import numpy as np
import io
import os
from PIL import Image

# ── Lazy-load Keras model (only once) ────────────────────────────
_model = None

def get_model():
    global _model
    if _model is None:
        from tensorflow.keras.models import load_model
        MODEL_PATH = os.getenv("MODEL_PATH", "cat_dog_classifier_final.keras")
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Model not found at {MODEL_PATH}")
        _model = load_model(MODEL_PATH)
        print("✅ Model loaded:", MODEL_PATH)
    return _model

# ── Constants ────────────────────────────────────────────────────
DB_PATH       = os.getenv("DB_PATH", "users.db")
FREE_LIMIT    = 50
STARTER_LIMIT = 500
IMG_SIZE      = (128, 128)

# ── App setup ────────────────────────────────────────────────────
app = FastAPI(
    title       = "CatDog AI API",
    description = "Classify pet images as cat or dog. Sign up at your Streamlit dashboard to get an API key.",
    version     = "1.0.0",
    docs_url    = "/docs",
    redoc_url   = "/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins  = ["*"],
    allow_methods  = ["*"],
    allow_headers  = ["*"],
)

# ── DB init (runs on startup — creates tables if not exist) ──────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            username   TEXT    NOT NULL,
            email      TEXT    UNIQUE NOT NULL,
            password   TEXT    NOT NULL,
            api_key    TEXT    UNIQUE NOT NULL,
            tier       TEXT    DEFAULT 'free',
            is_active  INTEGER DEFAULT 1,
            created_at TEXT    DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS api_usage (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            month_year TEXT    NOT NULL,
            count      INTEGER DEFAULT 0,
            UNIQUE(user_id, month_year),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            result     TEXT,
            confidence REAL,
            filename   TEXT,
            month_year TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()
    print("✅ Database initialized:", DB_PATH)

# Run DB init at startup
init_db()

# ── DB helpers ───────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def cur_month() -> str:
    return datetime.datetime.now().strftime("%Y-%m")

def get_user_by_key(api_key: str):
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE api_key = ? AND is_active = 1", (api_key,)
    ).fetchone()
    conn.close()
    return dict(user) if user else None

def get_usage(user_id: int) -> int:
    m = cur_month()
    conn = get_db()
    row = conn.execute(
        "SELECT count FROM api_usage WHERE user_id=? AND month_year=?",
        (user_id, m)
    ).fetchone()
    conn.close()
    return row["count"] if row else 0

def increment_usage(user_id: int):
    m = cur_month()
    conn = get_db()
    conn.execute("""
        INSERT INTO api_usage (user_id, month_year, count) VALUES (?, ?, 1)
        ON CONFLICT(user_id, month_year) DO UPDATE SET count = count + 1
    """, (user_id, m))
    conn.commit()
    conn.close()

def save_prediction(user_id: int, result: str, confidence: float, filename: str):
    m = cur_month()
    conn = get_db()
    conn.execute(
        "INSERT INTO predictions (user_id, result, confidence, filename, month_year) VALUES (?,?,?,?,?)",
        (user_id, result, round(confidence, 4), filename, m)
    )
    conn.commit()
    conn.close()

def get_tier_limit(tier: str) -> int:
    return {"free": FREE_LIMIT, "starter": STARTER_LIMIT, "pro": 999999}.get(tier, FREE_LIMIT)

# ── Image preprocessing ──────────────────────────────────────────
def preprocess_image(image_bytes: bytes) -> np.ndarray:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB").resize(IMG_SIZE)
    arr = np.array(img, dtype=np.float32) / 255.0
    return np.expand_dims(arr, axis=0)

def run_prediction(image_bytes: bytes):
    model = get_model()
    pred  = float(model.predict(preprocess_image(image_bytes), verbose=0)[0][0])
    if pred > 0.5:
        return "Dog", pred
    return "Cat", 1.0 - pred

# ══════════════════════════════════════════════════════════════════
#  ROUTES
# ══════════════════════════════════════════════════════════════════

@app.get("/", tags=["Health"])
def root():
    return {
        "status"  : "online",
        "service" : "CatDog AI API",
        "version" : "1.0.0",
        "docs"    : "/docs",
    }

@app.head("/", tags=["Health"])
def root_head():
    """Render health check via HEAD request"""
    return {}

@app.get("/health", tags=["Health"])
def health():
    model_ok = os.path.exists(os.getenv("MODEL_PATH", "cat_dog_classifier_final.keras"))
    db_ok    = os.path.exists(DB_PATH)
    return {
        "status"      : "ok" if (model_ok and db_ok) else "degraded",
        "model_loaded": model_ok,
        "database"    : db_ok,
        "timestamp"   : datetime.datetime.utcnow().isoformat(),
    }

@app.post("/predict", tags=["Prediction"])
async def predict(
    file      : UploadFile = File(..., description="Pet image — JPG, PNG, or WEBP"),
    x_api_key : str        = Header(..., alias="x-api-key", description="Your API key from the dashboard"),
):
    """
    ## Classify a pet image as Cat or Dog

    ### Request
    - **Header:** `x-api-key: cd_your_key_here`
    - **Body (form-data):** `file` = image file (JPG / PNG / WEBP)

    ### Response
    ```json
    {
      "result": "Cat",
      "confidence": 0.97,
      "predictions_used": 12,
      "predictions_limit": 50,
      "tier": "free"
    }
    ```
    """
    # 1. Validate API key
    if not x_api_key or not x_api_key.startswith("cd_"):
        raise HTTPException(status_code=401, detail={
            "error": "invalid_key_format",
            "message": "API key must start with 'cd_'. Get yours at the dashboard."
        })

    user = get_user_by_key(x_api_key)
    if not user:
        raise HTTPException(status_code=401, detail={
            "error": "invalid_key",
            "message": "API key not found or account is inactive."
        })

    # 2. Check usage limit
    usage = get_usage(user["id"])
    limit = get_tier_limit(user["tier"])

    if usage >= limit:
        raise HTTPException(status_code=429, detail={
            "error"            : "limit_exceeded",
            "message"          : f"Monthly limit of {limit} predictions reached for '{user['tier']}' plan.",
            "predictions_used" : usage,
            "predictions_limit": limit,
            "tier"             : user["tier"],
            "upgrade_message"  : "Upgrade your plan at the dashboard.",
        })

    # 3. Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail={"error": "no_file", "message": "No image file provided."})

    allowed = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
    if file.content_type and file.content_type.lower() not in allowed:
        raise HTTPException(status_code=415, detail={
            "error": "invalid_file_type",
            "message": f"Unsupported file type '{file.content_type}'. Use JPG, PNG, or WEBP."
        })

    # 4. Read image bytes
    image_bytes = await file.read()
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail={"error": "empty_file", "message": "Uploaded file is empty."})

    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail={"error": "file_too_large", "message": "File size must be under 10 MB."})

    # 5. Run prediction
    try:
        label, confidence = run_prediction(image_bytes)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail={"error": "model_not_found", "message": str(e)})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "prediction_failed", "message": f"Prediction error: {str(e)}"})

    # 6. Save & increment
    save_prediction(user["id"], label, round(confidence, 4), file.filename)
    increment_usage(user["id"])

    # 7. Return result
    return {
        "result"            : label,
        "confidence"        : round(confidence, 4),
        "confidence_percent": f"{round(confidence * 100, 1)}%",
        "predictions_used"  : usage + 1,
        "predictions_limit" : limit,
        "tier"              : user["tier"],
        "filename"          : file.filename,
    }

@app.get("/usage", tags=["Account"])
def check_usage(x_api_key: str = Header(..., alias="x-api-key")):
    """Check your current month usage."""
    user = get_user_by_key(x_api_key)
    if not user:
        raise HTTPException(status_code=401, detail={"error": "invalid_key", "message": "API key not found."})

    usage = get_usage(user["id"])
    limit = get_tier_limit(user["tier"])

    return {
        "username"             : user["username"],
        "tier"                 : user["tier"],
        "month"                : cur_month(),
        "predictions_used"     : usage,
        "predictions_limit"    : limit,
        "predictions_remaining": max(limit - usage, 0),
        "usage_percent"        : f"{min(round(usage/limit*100, 1), 100)}%",
    }

@app.get("/plans", tags=["Account"])
def list_plans():
    """List all available subscription plans."""
    return {
        "plans": [
            {"name":"free",    "price":"₹0/month",    "predictions_per_month": 50,          "features":["50 predictions","Email support","Dashboard access"]},
            {"name":"starter", "price":"₹499/month",  "predictions_per_month": 500,         "features":["500 predictions","Priority support","Full history","Batch upload"]},
            {"name":"pro",     "price":"₹1499/month", "predictions_per_month": "unlimited", "features":["Unlimited predictions","24/7 support","SLA guarantee","Custom domain"]},
        ]
    }

# ── Global error handlers ────────────────────────────────────────
@app.exception_handler(404)
async def not_found(request: Request, exc):
    return JSONResponse(status_code=404, content={
        "error": "not_found",
        "message": f"Route '{request.url.path}' does not exist.",
        "docs": "/docs",
    })

@app.exception_handler(422)
async def validation_error(request: Request, exc):
    return JSONResponse(status_code=422, content={
        "error": "validation_error",
        "message": "Missing required fields. Check /docs for usage.",
        "docs": "/docs",
    })

# ── Run locally ──────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
