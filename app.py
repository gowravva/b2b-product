"""
CatDog AI — Streamlit Dashboard
This is the USER-FACING product:
  - Signup / Login
  - Get API key
  - Try prediction (calls FastAPI backend)
  - Check usage / history
  - Upgrade plan

Deploy on: share.streamlit.io
The FastAPI backend runs separately on Render.com
"""

import streamlit as st
import sqlite3
import hashlib
import uuid
import datetime
import os
import requests as http_requests   # to call FastAPI

st.set_page_config(
    page_title = "CatDog AI — Dashboard",
    page_icon  = "🐾",
    layout     = "wide",
    initial_sidebar_state = "collapsed",
)

# ── CONFIG: point this to your deployed FastAPI URL ─────────────
# After deploying api.py on Render, replace this URL:
API_BASE_URL = os.getenv("API_BASE_URL", "https://b2b-product-cs3h.onrender.com")


DB_PATH       = "users.db"
FREE_LIMIT    = 50
STARTER_LIMIT = 500

# ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
#MainMenu,footer,header{visibility:hidden;}
.block-container{padding-top:2rem;padding-bottom:2rem;max-width:1100px;}
.stButton>button{background:#01696f!important;color:white!important;border:none!important;
  border-radius:8px!important;padding:.55rem 1.5rem!important;font-weight:600!important;
  font-size:.9rem!important;width:100%;transition:background .18s;}
.stButton>button:hover{background:#0c4e54!important;}
.kpi-box{background:#1c1b19;border:1px solid #393836;border-radius:10px;padding:1.2rem 1.4rem;text-align:center;}
.kpi-val{font-family:'JetBrains Mono',monospace;font-size:2rem;font-weight:700;color:#4f98a3;}
.kpi-label{font-size:.75rem;color:#797876;text-transform:uppercase;letter-spacing:.07em;margin-top:.3rem;}
.apikey-box{background:#171614;border:1px solid #393836;border-radius:8px;padding:.9rem 1.2rem;
  font-family:'JetBrains Mono',monospace;font-size:.82rem;color:#4f98a3;word-break:break-all;margin:.75rem 0;}
.badge-free{background:#313b3b;color:#4f98a3;padding:3px 10px;border-radius:20px;font-size:.72rem;font-weight:700;}
.badge-starter{background:#4d4332;color:#e8af34;padding:3px 10px;border-radius:20px;font-size:.72rem;font-weight:700;}
.badge-pro{background:#3a4435;color:#6daa45;padding:3px 10px;border-radius:20px;font-size:.72rem;font-weight:700;}
.prog-wrap{background:#262523;border-radius:20px;height:8px;overflow:hidden;margin:.5rem 0;}
.prog-fill{height:100%;background:#4f98a3;border-radius:20px;}
.stTabs [data-baseweb="tab-list"]{gap:4px;background:#1c1b19;border-radius:10px;padding:4px;border:1px solid #393836;}
.stTabs [data-baseweb="tab"]{border-radius:7px;padding:.5rem 1.2rem;font-size:.88rem;font-weight:500;color:#797876;}
.stTabs [aria-selected="true"]{background:#4f98a3!important;color:white!important;}
.alert-success{background:#1e2e1a;border-left:3px solid #6daa45;border-radius:8px;padding:.8rem 1rem;color:#6daa45;font-size:.88rem;margin:.5rem 0;}
.alert-error{background:#2a1a1a;border-left:3px solid #d163a7;border-radius:8px;padding:.8rem 1rem;color:#d163a7;font-size:.88rem;margin:.5rem 0;}
.alert-warn{background:#2a2010;border-left:3px solid #e8af34;border-radius:8px;padding:.8rem 1rem;color:#e8af34;font-size:.88rem;margin:.5rem 0;}
.alert-info{background:#101f22;border-left:3px solid #4f98a3;border-radius:8px;padding:.8rem 1rem;color:#4f98a3;font-size:.88rem;margin:.5rem 0;}
.result-box{border-radius:12px;padding:1.5rem;text-align:center;margin:1rem 0;}
.result-cat{background:linear-gradient(135deg,#1a1f3a,#1c1b19);border:1px solid #3b82f6;}
.result-dog{background:linear-gradient(135deg,#1f2e1a,#1c1b19);border:1px solid #6daa45;}
.hero-title{font-size:2.4rem;font-weight:800;letter-spacing:-.04em;color:#cdccca;line-height:1.15;}
.hero-sub{font-size:1.05rem;color:#797876;margin-top:.75rem;max-width:520px;}
.divider{border-top:1px solid #393836;margin:1.5rem 0;}
.hist-row{display:flex;align-items:center;gap:1rem;padding:.65rem .9rem;border-bottom:1px solid #262523;font-size:.82rem;color:#797876;}
.hist-row:last-child{border-bottom:none;}
.hist-cat{color:#60a5fa;font-weight:700;}
.hist-dog{color:#6daa45;font-weight:700;}
.code-block{background:#171614;border:1px solid #393836;border-radius:8px;padding:1rem 1.2rem;
  font-family:'JetBrains Mono',monospace;font-size:.78rem;color:#4f98a3;
  overflow-x:auto;white-space:pre;margin:.5rem 0 1rem 0;}
.arch-box{background:#1c1b19;border:1px solid #393836;border-radius:10px;padding:1.2rem;}
</style>
""", unsafe_allow_html=True)


# ── DB helpers (same users.db) ───────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            username   TEXT UNIQUE NOT NULL,
            email      TEXT UNIQUE NOT NULL,
            password   TEXT NOT NULL,
            api_key    TEXT UNIQUE,
            tier       TEXT DEFAULT 'free',
            created_at TEXT DEFAULT (datetime('now')),
            is_active  INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS predictions (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            result     TEXT NOT NULL,
            confidence REAL NOT NULL,
            filename   TEXT,
            month_year TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS api_usage (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            month_year TEXT NOT NULL,
            count      INTEGER DEFAULT 0,
            UNIQUE(user_id, month_year),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    conn.commit()
    conn.close()

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def gen_key():
    return "cd_" + uuid.uuid4().hex + uuid.uuid4().hex[:8]

def create_user(username, email, password):
    conn = get_db()
    try:
        key = gen_key()
        conn.execute(
            "INSERT INTO users (username,email,password,api_key) VALUES (?,?,?,?)",
            (username.strip(), email.strip().lower(), hash_pw(password), key)
        )
        conn.commit()
        return True, "Account created! Please login."
    except sqlite3.IntegrityError as e:
        err = str(e)
        if "username" in err: return False, "Username already taken."
        if "email" in err:    return False, "Email already registered."
        return False, "Registration failed."
    finally:
        conn.close()

def login_user(identifier, password):
    conn = get_db()
    u = conn.execute(
        "SELECT * FROM users WHERE (username=? OR email=?) AND password=? AND is_active=1",
        (identifier, identifier.lower(), hash_pw(password))
    ).fetchone()
    conn.close()
    return dict(u) if u else None

def get_user_by_id(uid):
    conn = get_db()
    u = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    conn.close()
    return dict(u) if u else None

def regenerate_key(uid):
    k = gen_key()
    conn = get_db()
    conn.execute("UPDATE users SET api_key=? WHERE id=?", (k, uid))
    conn.commit()
    conn.close()
    return k

def cur_month():
    return datetime.datetime.now().strftime("%Y-%m")

def get_usage(uid):
    conn = get_db()
    r = conn.execute(
        "SELECT count FROM api_usage WHERE user_id=? AND month_year=?",
        (uid, cur_month())
    ).fetchone()
    conn.close()
    return r["count"] if r else 0

def tier_limit(tier):
    return {"free": FREE_LIMIT, "starter": STARTER_LIMIT, "pro": 999999}.get(tier, FREE_LIMIT)

def get_history(uid, n=10):
    conn = get_db()
    rows = conn.execute(
        "SELECT result,confidence,filename,created_at FROM predictions "
        "WHERE user_id=? ORDER BY created_at DESC LIMIT ?", (uid, n)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Call FastAPI /predict ────────────────────────────────────────
def call_fastapi_predict(api_key: str, image_bytes: bytes, filename: str):
    """
    Calls the FastAPI /predict endpoint.
    Returns (success: bool, data: dict)
    """
    try:
        resp = http_requests.post(
            f"{API_BASE_URL}/predict",
            headers={"x-api-key": api_key},
            files={"file": (filename, image_bytes, "image/jpeg")},
            timeout=30,
        )
        return resp.status_code == 200, resp.json()
    except http_requests.exceptions.ConnectionError:
        return False, {"error": "api_offline",
                       "message": f"Cannot reach FastAPI at {API_BASE_URL}. Is it deployed?"}
    except http_requests.exceptions.Timeout:
        return False, {"error": "timeout", "message": "API request timed out (30s). Try again."}
    except Exception as e:
        return False, {"error": "request_failed", "message": str(e)}

def call_fastapi_usage(api_key: str):
    """Check usage via FastAPI /usage endpoint"""
    try:
        resp = http_requests.get(
            f"{API_BASE_URL}/usage",
            headers={"x-api-key": api_key},
            timeout=10,
        )
        return resp.status_code == 200, resp.json()
    except Exception as e:
        return False, {}


# ════════════════════════════════════════════════════════════════
#  PAGES
# ════════════════════════════════════════════════════════════════

def page_landing():
    c1, c2 = st.columns([1.15, 0.85], gap="large")
    with c1:
        st.markdown(f"""
        <div style="padding-top:2rem">
            <div class="hero-title">CatDog AI<br><span style="color:#4f98a3">Image API</span></div>
            <div class="hero-sub">
                A real B2B REST API powered by FastAPI + Keras.<br>
                Classify pet images as <strong style="color:#60a5fa">cat</strong> or
                <strong style="color:#6daa45">dog</strong> from any app, anywhere in the world.
                <br>50 free predictions/month.
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)
        st.markdown("""
        <div style="display:flex;gap:.75rem;flex-wrap:wrap;margin-bottom:1.5rem">
            <span class="badge-free">✓ Free 50/month</span>
            <span class="badge-starter">⚡ FastAPI Backend</span>
            <span class="badge-pro">🌍 Global REST API</span>
        </div>
        """, unsafe_allow_html=True)

        # Architecture diagram
        st.markdown("""
        <div class="arch-box">
            <div style="font-size:.72rem;text-transform:uppercase;letter-spacing:.08em;color:#797876;margin-bottom:.75rem;font-weight:700">Architecture</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:.75rem;color:#cdccca;line-height:2">
                Your App (curl/Python/JS)<br>
                &nbsp;&nbsp;&nbsp;&nbsp;↓ POST /predict + x-api-key<br>
                <span style="color:#4f98a3">FastAPI (Render.com)</span><br>
                &nbsp;&nbsp;&nbsp;&nbsp;↓ validate key + check limit<br>
                <span style="color:#e8af34">SQLite users.db</span> &nbsp;+&nbsp; <span style="color:#6daa45">Keras Model</span><br>
                &nbsp;&nbsp;&nbsp;&nbsp;↓ run inference<br>
                <span style="color:#4f98a3">{"result":"Cat","confidence":0.97}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        t_login, t_signup = st.tabs(["🔑  Login", "✨  Sign Up"])
        with t_login:
            st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)
            with st.form("login_f"):
                st.markdown("##### Welcome back")
                ident = st.text_input("Username or Email")
                pw    = st.text_input("Password", type="password")
                sub   = st.form_submit_button("Login →")
                if sub:
                    if not ident or not pw:
                        st.markdown('<div class="alert-error">Fill in all fields.</div>', unsafe_allow_html=True)
                    else:
                        u = login_user(ident, pw)
                        if u:
                            st.session_state.user = u
                            st.session_state.page = "dashboard"
                            st.rerun()
                        else:
                            st.markdown('<div class="alert-error">❌ Invalid credentials.</div>', unsafe_allow_html=True)

        with t_signup:
            st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)
            with st.form("signup_f", clear_on_submit=True):
                st.markdown("##### Create account")
                uname = st.text_input("Username", placeholder="johnsmith")
                email = st.text_input("Email",    placeholder="john@company.com")
                pw1   = st.text_input("Password", type="password", placeholder="Min 8 characters")
                pw2   = st.text_input("Confirm Password", type="password")
                sub   = st.form_submit_button("Create Account →")
                if sub:
                    if not all([uname, email, pw1, pw2]):
                        st.markdown('<div class="alert-error">Fill in all fields.</div>', unsafe_allow_html=True)
                    elif len(pw1) < 8:
                        st.markdown('<div class="alert-error">Password min 8 chars.</div>', unsafe_allow_html=True)
                    elif pw1 != pw2:
                        st.markdown('<div class="alert-error">Passwords do not match.</div>', unsafe_allow_html=True)
                    elif "@" not in email:
                        st.markdown('<div class="alert-error">Enter valid email.</div>', unsafe_allow_html=True)
                    else:
                        ok, msg = create_user(uname, email, pw1)
                        cls  = "alert-success" if ok else "alert-error"
                        icon = "✅" if ok else "❌"
                        st.markdown(f'<div class="{cls}">{icon} {msg}</div>', unsafe_allow_html=True)


def page_dashboard():
    user  = get_user_by_id(st.session_state.user["id"])
    st.session_state.user = user
    usage = get_usage(user["id"])
    limit = tier_limit(user["tier"])
    pct   = min(int(usage / limit * 100), 100)
    tier  = user["tier"]
    badge = {"free":"badge-free","starter":"badge-starter","pro":"badge-pro"}.get(tier,"badge-free")

    # Nav
    n1, n2 = st.columns([0.85, 0.15])
    with n1:
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:1rem;padding-bottom:1rem;
             border-bottom:1px solid #393836;flex-wrap:wrap">
            <div style="font-size:1.15rem;font-weight:800;letter-spacing:-.03em;color:#cdccca">🐾 CatDog AI</div>
            <span class="{badge}">{tier.upper()}</span>
            <div style="font-size:.78rem;color:#5a5957;margin-left:.5rem">
                API: <span style="color:#4f98a3">{API_BASE_URL}</span>
            </div>
            <div style="margin-left:auto;font-size:.82rem;color:#797876">👤 {user['username']}</div>
        </div>""", unsafe_allow_html=True)
    with n2:
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # KPIs
    k1,k2,k3,k4 = st.columns(4)
    month_label  = datetime.datetime.now().strftime("%b %Y")
    for col, val, label in [
        (k1, usage, "Used This Month"),
        (k2, max(limit-usage,0), "Remaining"),
        (k3, limit if limit < 999999 else "∞", "Monthly Limit"),
        (k4, month_label, "Billing Period"),
    ]:
        with col:
            fsize = "2rem" if isinstance(val, int) or val=="∞" else "1.3rem"
            st.markdown(f"""<div class="kpi-box">
                <div class="kpi-val" style="font-size:{fsize}">{val}</div>
                <div class="kpi-label">{label}</div>
            </div>""", unsafe_allow_html=True)

    bar_color = "#ef4444" if pct>=90 else "#e8af34" if pct>=70 else "#4f98a3"
    st.markdown(f"""
    <div style="margin:1rem 0 .3rem;font-size:.78rem;color:#797876">
        API Usage — {pct}% of monthly limit
    </div>
    <div class="prog-wrap">
        <div class="prog-fill" style="width:{pct}%;background:{bar_color}"></div>
    </div>""", unsafe_allow_html=True)

    if pct >= 100:
        st.markdown('<div class="alert-warn">🚫 Limit reached. Go to Upgrade tab.</div>', unsafe_allow_html=True)
    elif pct >= 80:
        st.markdown(f'<div class="alert-warn">⚠️ {pct}% used. Consider upgrading soon.</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # Tabs
    t_pred, t_key, t_hist, t_up, t_docs = st.tabs(
        ["🔮 Try API", "🔑 API Key", "📜 History", "⬆️ Upgrade", "📖 API Docs"]
    )

    # ── TRY API (calls FastAPI /predict) ─────────────────────────
    with t_pred:
        st.markdown("#### Try the API — Upload a Pet Image")
        st.markdown(f"""
        <div class="alert-info">
            🚀 This calls your <strong>FastAPI backend</strong> at
            <code>{API_BASE_URL}/predict</code> using your API key.
            Exactly what any developer would do from their code.
        </div>
        """, unsafe_allow_html=True)

        uploaded = st.file_uploader(
            "Choose image", type=["jpg","jpeg","png","webp"],
            label_visibility="collapsed"
        )

        if uploaded:
            ci, cr = st.columns(2, gap="large")
            with ci:
                st.image(uploaded, caption=uploaded.name, use_container_width=True)
            with cr:
                if st.button("🔮 Classify via FastAPI"):
                    with st.spinner(f"Calling {API_BASE_URL}/predict ..."):
                        img_bytes = uploaded.read()
                        ok, data  = call_fastapi_predict(
                            user["api_key"], img_bytes, uploaded.name
                        )

                    if ok:
                        label     = data.get("result", "Unknown")
                        conf      = data.get("confidence", 0)
                        used      = data.get("predictions_used", 0)
                        lim       = data.get("predictions_limit", limit)
                        is_cat    = label == "Cat"
                        res_cls   = "result-cat" if is_cat else "result-dog"
                        color     = "#60a5fa" if is_cat else "#6daa45"
                        conf_pct  = round(conf * 100, 1)

                        st.markdown(f"""
                        <div class="result-box {res_cls}">
                            <div style="font-size:3rem">{"🐱" if is_cat else "🐶"}</div>
                            <div style="font-size:1.8rem;font-weight:800;color:{color};margin:.5rem 0">
                                {label}
                            </div>
                            <div style="font-size:1rem;color:#cdccca">
                                Confidence: <strong style="color:{color}">{conf_pct}%</strong>
                            </div>
                        </div>
                        <div style="font-size:.78rem;color:#797876;text-align:center">
                            Prediction #{used} of {lim} used this month
                        </div>""", unsafe_allow_html=True)

                        # Show raw API response
                        with st.expander("📦 Raw API Response (JSON)"):
                            st.json(data)
                    else:
                        err_code = data.get("error","unknown")
                        err_msg  = data.get("message", str(data))

                        if err_code == "limit_exceeded":
                            st.markdown(f'<div class="alert-warn">🚫 {err_msg}</div>', unsafe_allow_html=True)
                        elif err_code == "api_offline":
                            st.markdown(f"""
                            <div class="alert-error">
                                ❌ <strong>FastAPI backend is offline!</strong><br>
                                {err_msg}<br><br>
                                <strong>To fix:</strong> Deploy api.py on Render.com and update
                                <code>API_BASE_URL</code> in your Streamlit secrets.
                            </div>""", unsafe_allow_html=True)
                        else:
                            st.markdown(f'<div class="alert-error">❌ Error ({err_code}): {err_msg}</div>', unsafe_allow_html=True)

    # ── API KEY ───────────────────────────────────────────────────
    with t_key:
        st.markdown("#### Your API Key")
        st.markdown('<div class="alert-info">🔒 This key is validated by FastAPI on every request.</div>', unsafe_allow_html=True)

        show = st.checkbox("👁 Show full API key")
        display_key = user["api_key"] if show else "cd_" + "•"*40
        st.markdown(f'<div class="apikey-box">{display_key}</div>', unsafe_allow_html=True)

        ca, cb = st.columns(2)
        with ca:
            st.code(user["api_key"], language=None)
        with cb:
            if st.button("🔄 Regenerate Key"):
                new_key = regenerate_key(user["id"])
                user["api_key"] = new_key
                st.session_state.user = user
                st.markdown('<div class="alert-success">✅ New API key generated!</div>', unsafe_allow_html=True)
                st.rerun()

        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
        st.markdown(f"#### Test Your Key Live — FastAPI at `{API_BASE_URL}`")

        if st.button("📡 Check My Usage via API"):
            ok, data = call_fastapi_usage(user["api_key"])
            if ok:
                st.json(data)
            else:
                st.markdown('<div class="alert-error">❌ Could not reach FastAPI. Is it deployed?</div>', unsafe_allow_html=True)

    # ── HISTORY ───────────────────────────────────────────────────
    with t_hist:
        st.markdown("#### Recent Predictions (last 10)")
        history = get_history(user["id"])
        if not history:
            st.markdown("""<div style="text-align:center;padding:3rem;color:#5a5957">
                <div style="font-size:3rem">📭</div>
                <div style="margin-top:.75rem">No predictions yet. Try the API tab above.</div>
            </div>""", unsafe_allow_html=True)
        else:
            for row in history:
                is_cat   = "Cat" in row["result"]
                cls      = "hist-cat" if is_cat else "hist-dog"
                conf_pct = round(row["confidence"]*100, 1)
                ts       = row["created_at"][:16].replace("T"," ")
                fname    = (row["filename"] or "unknown")[:35]
                st.markdown(f"""
                <div class="hist-row">
                    <span>{"🐱" if is_cat else "🐶"}</span>
                    <span class="{cls}">{row['result'].split()[0]}</span>
                    <span style="color:#cdccca;font-weight:600">{conf_pct}%</span>
                    <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#5a5957">{fname}</span>
                    <span style="font-family:'JetBrains Mono',monospace;font-size:.72rem">{ts}</span>
                </div>""", unsafe_allow_html=True)

    # ── UPGRADE ───────────────────────────────────────────────────
    with t_up:
        st.markdown("#### Choose Your Plan")
        plans = [
            ("Free",    "₹0/month",    50,    "badge-free",
             ["50 API calls/month","Dashboard access","API key access","Email support"]),
            ("Starter", "₹499/month",  500,   "badge-starter",
             ["500 API calls/month","Priority support","Full history","Batch upload"]),
            ("Pro",     "₹1499/month", "∞",   "badge-pro",
             ["Unlimited API calls","24/7 support","SLA guarantee","Custom domain"]),
        ]
        for col, (name, price, lim, badge_cls, feats) in zip(st.columns(3), plans):
            current = tier == name.lower()
            bc = "#4f98a3" if current else "#393836"
            with col:
                st.markdown(f"""
                <div style="background:#1c1b19;border:2px solid {bc};border-radius:12px;
                     padding:1.4rem;min-height:260px">
                    <span class="{badge_cls}">{name}</span>
                    <div style="font-size:1.4rem;font-weight:800;color:#cdccca;margin:.75rem 0 .2rem">{price}</div>
                    <div style="font-size:.82rem;color:#797876;margin-bottom:1rem">{lim} predictions/month</div>
                    <hr style="border-color:#393836;margin:.75rem 0">
                    <ul style="list-style:none;padding:0">
                        {"".join(f'<li style="font-size:.8rem;color:#797876;padding:.2rem 0">✓ {f}</li>' for f in feats)}
                    </ul>
                </div>""", unsafe_allow_html=True)
                if current:
                    st.markdown('<div class="alert-success" style="text-align:center;margin-top:.5rem">✓ Active Plan</div>', unsafe_allow_html=True)
                else:
                    if st.button(f"Upgrade to {name}", key=f"up_{name}"):
                        st.markdown(f'<div class="alert-info">💳 Integrate Razorpay/Stripe to automate. For now email: admin@catdogai.com with your username to upgrade to <strong>{name}</strong>.</div>', unsafe_allow_html=True)

    # ── API DOCS ──────────────────────────────────────────────────
    with t_docs:
        st.markdown("#### Complete API Reference")

        st.markdown(f"**Base URL (FastAPI on Render):**")
        st.code(f"{API_BASE_URL}", language=None)

        st.markdown("**Authentication header (required on all requests):**")
        st.code("x-api-key: cd_your_api_key_here", language=None)

        st.markdown("---")
        st.markdown("##### 🔮 POST /predict — Classify an image")
        st.markdown("""
        | Parameter | Location | Type | Required |
        |---|---|---|---|
        | `file` | form-data | image (JPG/PNG/WEBP) | ✅ |
        | `x-api-key` | header | string | ✅ |
        """)

        st.markdown("**✅ Success (200):**")
        st.code("""{
  "result": "Cat",
  "confidence": 0.9712,
  "confidence_percent": "97.1%",
  "predictions_used": 12,
  "predictions_limit": 50,
  "tier": "free",
  "filename": "photo.jpg"
}""", language="json")

        st.markdown("**❌ Error responses:**")
        st.code("""{
  "error": "invalid_key",
  "message": "API key not found or account is inactive."
}
{
  "error": "limit_exceeded",
  "message": "Monthly limit of 50 predictions reached for 'free' plan.",
  "predictions_used": 50,
  "predictions_limit": 50,
  "upgrade_message": "Upgrade your plan at the dashboard to continue."
}
{
  "error": "invalid_file_type",
  "message": "Use JPG, PNG, or WEBP."
}""", language="json")

        st.markdown("---")
        st.markdown("##### 📊 GET /usage — Check your usage")
        st.code(f"""curl {API_BASE_URL}/usage \
  -H "x-api-key: {user['api_key']}" """, language="bash")

        st.markdown("---")
        st.markdown("##### Code Examples")
        lang = st.selectbox("Language", ["Python","cURL","JavaScript (Node.js)","PHP"])

        if lang == "Python":
            st.code(f"""import requests

API_KEY = "{user['api_key']}"
API_URL = "{API_BASE_URL}"

# ── Predict ──────────────────────────────────────────
with open("photo.jpg", "rb") as img:
    response = requests.post(
        f"{{API_URL}}/predict",
        headers={{"x-api-key": API_KEY}},
        files={{"file": img}}
    )

data = response.json()

if response.status_code == 200:
    print(f"Result: {{data['result']}}")
    print(f"Confidence: {{data['confidence_percent']}}")
    print(f"Used: {{data['predictions_used']}} / {{data['predictions_limit']}}")
elif data.get("error") == "limit_exceeded":
    print("Limit reached — upgrade your plan!")
else:
    print("Error:", data.get("message"))

# ── Check usage ───────────────────────────────────────
r = requests.get(f"{{API_URL}}/usage", headers={{"x-api-key": API_KEY}})
print(r.json())
""", language="python")

        elif lang == "cURL":
            st.code(f"""# Predict
curl -X POST {API_BASE_URL}/predict \
  -H "x-api-key: {user['api_key']}" \
  -F "file=@photo.jpg"

# Check usage
curl {API_BASE_URL}/usage \
  -H "x-api-key: {user['api_key']}"

# View API docs in browser
open {API_BASE_URL}/docs
""", language="bash")

        elif lang == "JavaScript (Node.js)":
            st.code(f"""const FormData = require('form-data');
const fs       = require('fs');
const fetch    = require('node-fetch');

const API_KEY = "{user['api_key']}";
const API_URL = "{API_BASE_URL}";

async function classifyPet(imagePath) {{
  const form = new FormData();
  form.append('file', fs.createReadStream(imagePath));

  const res  = await fetch(`${{API_URL}}/predict`, {{
    method : 'POST',
    headers: {{ 'x-api-key': API_KEY, ...form.getHeaders() }},
    body   : form,
  }});

  const data = await res.json();

  if (res.ok) {{
    console.log(`Result: ${{data.result}} (${{data.confidence_percent}})`);
    console.log(`Used: ${{data.predictions_used}} / ${{data.predictions_limit}}`);
  }} else {{
    console.error('Error:', data.message);
  }}
}}

classifyPet('photo.jpg');
""", language="javascript")

        else:  # PHP
            st.code(f"""<?php
$API_KEY = "{user['api_key']}";
$API_URL = "{API_BASE_URL}";

$ch = curl_init("$API_URL/predict");
curl_setopt_array($ch, [
  CURLOPT_POST           => true,
  CURLOPT_POSTFIELDS     => ["file" => new CURLFile("photo.jpg")],
  CURLOPT_HTTPHEADER     => ["x-api-key: $API_KEY"],
  CURLOPT_RETURNTRANSFER => true,
]);

$res  = json_decode(curl_exec($ch), true);
$code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if ($code === 200) {{
    echo $res["result"] . " — " . $res["confidence_percent"];
}} else {{
    echo "Error: " . $res["message"];
}}
?>
""", language="php")


# ── Entry point ──────────────────────────────────────────────────
def main():
    init_db()
    if "page" not in st.session_state: st.session_state.page = "landing"
    if "user" not in st.session_state: st.session_state.user = None
    if st.session_state.user and st.session_state.page == "landing":
        st.session_state.page = "dashboard"
    if st.session_state.page == "dashboard" and st.session_state.user:
        page_dashboard()
    else:
        page_landing()

if __name__ == "__main__":
    main()
