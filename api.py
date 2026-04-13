"""
CatDog AI — FastAPI Backend
Deploy on Render.com as a Web Service.
"""

from fastapi import FastAPI, UploadFile, File, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import sqlite3, datetime, numpy as np, io, os
from PIL import Image

_model = None

def get_model():
    global _model
    if _model is None:
        from tensorflow.keras.models import load_model
        MODEL_PATH = os.getenv("MODEL_PATH", "cat_dog_classifier_final.keras")
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Model not found at {MODEL_PATH}")
        _model = load_model(MODEL_PATH)
    return _model

DB_PATH       = os.getenv("DB_PATH", "users.db")
FREE_LIMIT    = 50
STARTER_LIMIT = 500
IMG_SIZE      = (128, 128)

app = FastAPI(
    title="CatDog AI API",
    description="Classify pet images as cat or dog.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        api_key TEXT UNIQUE NOT NULL,
        tier TEXT DEFAULT 'free',
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now')))""")
    conn.execute("""CREATE TABLE IF NOT EXISTS api_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        month_year TEXT NOT NULL,
        count INTEGER DEFAULT 0,
        UNIQUE(user_id, month_year),
        FOREIGN KEY (user_id) REFERENCES users(id))""")
    conn.execute("""CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        result TEXT, confidence REAL, filename TEXT, month_year TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id))""")
    conn.commit()
    conn.close()

init_db()

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def cur_month(): return datetime.datetime.now().strftime("%Y-%m")

def get_user_by_key(api_key):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE api_key=? AND is_active=1", (api_key,)).fetchone()
    conn.close()
    return dict(user) if user else None

def get_usage(user_id):
    conn = get_db()
    row = conn.execute("SELECT count FROM api_usage WHERE user_id=? AND month_year=?", (user_id, cur_month())).fetchone()
    conn.close()
    return row["count"] if row else 0

def increment_usage(user_id):
    conn = get_db()
    conn.execute("""INSERT INTO api_usage (user_id, month_year, count) VALUES (?,?,1)
        ON CONFLICT(user_id, month_year) DO UPDATE SET count=count+1""", (user_id, cur_month()))
    conn.commit(); conn.close()

def save_prediction(user_id, result, confidence, filename):
    conn = get_db()
    conn.execute("INSERT INTO predictions (user_id,result,confidence,filename,month_year) VALUES (?,?,?,?,?)",
        (user_id, result, round(confidence,4), filename, cur_month()))
    conn.commit(); conn.close()

def get_tier_limit(tier):
    return {"free": FREE_LIMIT, "starter": STARTER_LIMIT, "pro": 999999}.get(tier, FREE_LIMIT)

def preprocess_image(image_bytes):
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB").resize(IMG_SIZE)
    return np.expand_dims(np.array(img, dtype=np.float32)/255.0, axis=0)

def run_prediction(image_bytes):
    pred = float(get_model().predict(preprocess_image(image_bytes), verbose=0)[0][0])
    return ("Dog", pred) if pred > 0.5 else ("Cat", 1.0 - pred)

# ══ ROUTES ══════════════════════════════════════════

@app.get("/", tags=["Health"])
def root():
    return {"status":"online","service":"CatDog AI API","version":"1.0.0","docs":"/docs"}

@app.head("/", tags=["Health"])
def root_head(): return {}

@app.get("/health", tags=["Health"])
def health():
    model_ok = os.path.exists(os.getenv("MODEL_PATH","cat_dog_classifier_final.keras"))
    return {"status":"ok" if (model_ok and os.path.exists(DB_PATH)) else "degraded",
            "model_loaded":model_ok, "database":os.path.exists(DB_PATH),
            "timestamp":datetime.datetime.utcnow().isoformat()}

# ── ⚡ TEMP ROUTE — visit once to get API key on Render ──────────
@app.get("/setup-testuser", tags=["Setup"])
def setup_test_user():
    """Visit once on Render to create test user. COPY key then DELETE this route!"""
    import uuid, hashlib
    conn = get_db()
    new_key = "cd_" + uuid.uuid4().hex
    conn.execute("INSERT OR IGNORE INTO users (username,email,password,api_key,tier,is_active) VALUES (?,?,?,?,?,?)",
        ("gouri","gouri@test.com", hashlib.sha256(b"pass123").hexdigest(), new_key, "free", 1))
    conn.commit()
    row = conn.execute("SELECT api_key,username,tier FROM users WHERE email='gouri@test.com'").fetchone()
    conn.close()
    return {"status":"✅ User ready!", "username":row["username"],
            "tier":row["tier"], "api_key":row["api_key"],
            "message":"Copy this api_key! DELETE this route after use!"}

@app.post("/register", tags=["Auth"])
def register(data: dict):
    import uuid, hashlib
    username = data.get("username","").strip()
    email    = data.get("email","").strip().lower()
    password = data.get("password","")
    if not all([username, email, password]):
        raise HTTPException(400, {"error":"missing_fields","message":"username, email, password required."})
    conn = get_db()
    if conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone():
        conn.close()
        raise HTTPException(409, {"error":"email_exists","message":"Email already registered."})
    key = "cd_" + uuid.uuid4().hex
    conn.execute("INSERT INTO users (username,email,password,api_key,tier,is_active) VALUES (?,?,?,?,?,?)",
        (username, email, hashlib.sha256(password.encode()).hexdigest(), key, "free", 1))
    conn.commit(); conn.close()
    return {"status":"success","message":f"Welcome {username}!","api_key":key,"tier":"free","limit":FREE_LIMIT}

@app.post("/login", tags=["Auth"])
def login(data: dict):
    import hashlib
    email    = data.get("email","").strip().lower()
    password = data.get("password","")
    if not email or not password:
        raise HTTPException(400, {"error":"missing_fields","message":"email and password required."})
    hashed = hashlib.sha256(password.encode()).hexdigest()
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email=? AND password=? AND is_active=1",(email,hashed)).fetchone()
    conn.close()
    if not user:
        raise HTTPException(401, {"error":"invalid_credentials","message":"Invalid email or password."})
    user = dict(user)
    return {"status":"success","username":user["username"],"api_key":user["api_key"],
            "tier":user["tier"],"limit":get_tier_limit(user["tier"])}

@app.post("/predict", tags=["Prediction"])
async def predict(
    file: UploadFile = File(...),
    x_api_key: str   = Header(..., alias="x-api-key"),
):
    if not x_api_key or not x_api_key.startswith("cd_"):
        raise HTTPException(401, {"error":"invalid_key_format","message":"Key must start with cd_"})
    user = get_user_by_key(x_api_key)
    if not user:
        raise HTTPException(401, {"error":"invalid_key","message":"API key not found 