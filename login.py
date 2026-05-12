"""
login.py — PEAKADS LLP

FIX: The left panel is now injected directly into the parent DOM via a
height=0 iframe (same pattern as navbar.py).  This completely bypasses
st.markdown(), whose parser randomly renders complex HTML as raw text.

The right-panel form stays as normal Streamlit content; CSS shifts it
right by LP_WIDTH% so it fills the remaining viewport.
"""

import streamlit as st
import streamlit.components.v1 as components
import base64
import os
from datetime import datetime
import sqlite3
import pandas as pd

DB_PATH = r"D:\Sumit\PY\Tracker Software\New SQL\tracker.db"

# ── Logo loader ────────────────────────────────────────────────────────────────

def _get_logo_b64() -> str:
    logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "peakads_logo.png")
    try:
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return ""

# ===============================
# DEFAULT USERS
# ===============================

DEFAULT_USERS = {
    "Admin":   {"password": "Admin@1808", "role": "Admin"},
    "Sales":   {"password": "Sales@123",  "role": "Sales"},
    "Finance": {"password": "Fin@123",    "role": "Finance"},
    "User":    {"password": "User@123",   "role": "User"},
}

# ===============================
# ROLE TAB ACCESS
# ===============================

ROLE_ACCESS = {
    "Admin": [
        "Dashboard", "Ageing", "Master Data", "DSP (Customers)",
        "Invoice Manager", "SSP (Vendors)", "List of Partners",
        "Costs Centre", "P&L", "Admin Control", "Edit Database",
        "BC Report",
    ],
    "Sales":   ["Dashboard", "Summary", "List of Partners"],
    "Finance": ["Dashboard", "Summary", "DSP (Customers)",
                "SSP (Vendors)", "List of Partners", "Costs Centre"],
    "User":    ["Dashboard", "Summary", "List of Partners"],
}

# ===============================
# DB CONNECTION
# ===============================

def get_db_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

# ===============================
# CREATE LOGIN LOG TABLE
# ===============================

def create_login_log_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS login_logs (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            username  TEXT
        )
    """)
    conn.commit()
    conn.close()

create_login_log_table()

# ===============================
# LOGIN LOG
# ===============================

def log_login(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO login_logs (timestamp, username) VALUES (?, ?)",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), username),
    )
    conn.commit()
    conn.close()


def _inject_loading_screen(logo_b64: str, hold_seconds: float = 6.5) -> None:
    """
    Inject a position:fixed dark loading overlay into the parent DOM.

    Key design — self-destruct via <script> in parent <head>:
      The JS inside the iframe appends a <script> element to the parent
      document's <head>.  That script executes IMMEDIATELY in the parent
      window's own context (not the iframe's context), registering a
      setTimeout on the parent window.  When Streamlit tears down the iframe
      on st.rerun(), the timer is already owned by the parent window and
      continues running, guaranteed.  After (hold_seconds + 1.5) seconds the
      overlay fades out and is removed, along with the helper script tag.
    """
    logo_tag = (
        f'<img src="data:image/png;base64,{logo_b64}" '
        f'style="width:84px;height:84px;object-fit:contain;border-radius:16px;'
        f'box-shadow:0 8px 32px rgba(0,118,206,0.45);margin-bottom:22px;" alt="PEAKADS">'
        if logo_b64 else
        '<div style="width:84px;height:84px;'
        'background:linear-gradient(135deg,#0076CE,#38bdf8);border-radius:16px;'
        'display:flex;align-items:center;justify-content:center;'
        'font-size:30px;font-weight:900;color:#fff;margin-bottom:22px;'
        'box-shadow:0 8px 32px rgba(0,118,206,0.45);">PA</div>'
    )

    ld_css = (
        "#pak-loading{position:fixed;inset:0;z-index:99999;"
        "background:linear-gradient(145deg,#060c18 0%,#0b1828 50%,#08121e 100%);"
        "display:flex;flex-direction:column;align-items:center;justify-content:center;"
        "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;"
        "-webkit-font-smoothing:antialiased;"
        "transition:opacity .7s ease;opacity:1;}"
        "#pak-loading::before{content:'';position:absolute;inset:0;"
        "background-image:radial-gradient(rgba(255,255,255,0.028) 1px,transparent 1px);"
        "background-size:30px 30px;pointer-events:none;}"
        ".ld-logo{width:84px;height:84px;object-fit:contain;border-radius:16px;"
        "box-shadow:0 8px 32px rgba(0,118,206,0.45);margin-bottom:22px;}"
        ".ld-brand{font-size:22px;font-weight:800;color:#fff;letter-spacing:2px;margin-bottom:10px;}"
        ".ld-sep{width:48px;height:2px;"
        "background:linear-gradient(90deg,#0076CE,#38bdf8);"
        "border-radius:2px;margin:0 auto 28px;}"
        ".ld-msg{font-size:16px;color:rgba(255,255,255,.80);margin-bottom:6px;letter-spacing:.2px;}"
        ".ld-sub{font-size:13px;color:rgba(255,255,255,.40);margin-bottom:36px;font-style:italic;}"
        "@keyframes ldP{0%,80%,100%{transform:scale(0);opacity:.4}40%{transform:scale(1);opacity:1}}"
        ".ld-dots{display:flex;gap:10px;}"
        ".ld-dots span{width:11px;height:11px;border-radius:50%;background:#38bdf8;"
        "animation:ldP 1.5s ease-in-out infinite;}"
        ".ld-dots span:nth-child(2){animation-delay:.2s;}"
        ".ld-dots span:nth-child(3){animation-delay:.4s;}"
        f"@keyframes ldBar{{0%{{width:0%}}70%{{width:80%}}90%{{width:95%}}100%{{width:100%}}}}"
        f".ld-track{{width:240px;height:3px;background:rgba(255,255,255,.10);"
        "border-radius:2px;overflow:hidden;margin-top:28px;}"
        f".ld-bar{{height:100%;width:0%;border-radius:2px;"
        "background:linear-gradient(90deg,#0076CE,#38bdf8);"
        f"animation:ldBar {hold_seconds}s ease-in-out forwards;}}"
        "#pak-loading{z-index:2147483647!important;}"
        "[data-testid='stApp'],[data-testid='stAppViewContainer'],[data-testid='stMain'],.stApp{visibility:hidden!important;}"
        "#pak-loading,#pak-loading *{visibility:visible!important;}"
    )

    ld_html = (
        '<div id="pak-loading">' + logo_tag +
        '<div class="ld-brand">PEAKADS\u00a0LLP</div>'
        '<div class="ld-sep"></div>'
        '<p class="ld-msg">Software is getting ready for you\u2026</p>'
        '<p class="ld-sub">Please wait while we load your workspace</p>'
        '<div class="ld-dots"><span></span><span></span><span></span></div>'
        '<div class="ld-track"><div class="ld-bar"></div></div>'
        '</div>'
    )

    # Script that runs in parent window context — NOT in the iframe context.
    # It is appended to parent <head> as a <script> element and executes
    # immediately there, registering a setTimeout on the parent window itself.
    remove_ms = int((hold_seconds + 1.5) * 1000)
    remove_js = (
        "setTimeout(function(){"
        "var o=document.getElementById('pak-loading');if(!o)return;"
        "o.style.opacity='0';"
        "setTimeout(function(){"
        "o.remove();"
        "['pak-loading-css','pak-loading-rm'].forEach(function(id){"
        "var e=document.getElementById(id);if(e)e.remove();});"
        "},750);"
        f"}},{remove_ms});"
    )

    inject_js = (
        "(function(){"
        "var P=window.parent.document;if(!P||!P.body)return;"
        # clean stale elements
        "['pak-loading','pak-loading-css','pak-loading-rm'].forEach(function(id){"
        "var e=P.getElementById(id);if(e)e.remove();});"
        # inject CSS
        "var s=P.createElement('style');s.id='pak-loading-css';"
        "s.textContent=" + repr(ld_css) + ";"
        "P.head.appendChild(s);"
        # inject overlay HTML
        "var d=P.createElement('div');"
        "d.innerHTML=" + repr(ld_html) + ";"
        "P.body.appendChild(d.firstChild);"
        # inject self-destruct script into parent HEAD (runs in parent context!)
        "var rm=P.createElement('script');rm.id='pak-loading-rm';"
        "rm.textContent=" + repr(remove_js) + ";"
        "P.head.appendChild(rm);"   # appending executes the script immediately
        "})();"
    )

    components.html(
        "<!DOCTYPE html><html><head><meta charset='utf-8'></head>"
        "<body style='margin:0;padding:0;background:transparent;'>"
        "<script>" + inject_js + "</script>"
        "</body></html>",
        height=0, scrolling=False,
    )


# ===============================
# LOGIN SCREEN  - Option C
# Split Dark / Light Cinematic
# ===============================

_LP = 58   # left panel width in %

def login_screen():

    # ── LOADING SCREEN ───────────────────────────────────────────────────────
    # The overlay is already in the parent DOM — injected by _inject_loading_screen()
    # called RIGHT BEFORE st.rerun() in the Sign-In handler (same render as the
    # button click).  The overlay's self-destruct <script> lives in the parent
    # <head> and runs in the parent window context, surviving all iframe teardowns.
    # Here we just hold 6.5 s then transition to main app.
    if st.session_state.get("app_loading", False):
        st.session_state.logged_in   = True
        st.session_state.user        = st.session_state.pop("pending_user", "")
        st.session_state.role        = st.session_state.pop("pending_role", "")
        st.session_state.app_loading = False
        st.rerun()
        return
    # 2. Load logo
    logo_b64 = _get_logo_b64()
    lp_logo  = (f'<img src="data:image/png;base64,{logo_b64}" class="lp-logo-img" alt="PEAKADS">'
                if logo_b64 else '<div class="lp-logo-fallback">PA</div>')
    rp_logo  = (f'<img src="data:image/png;base64,{logo_b64}" class="rp-logo-img" alt="PEAKADS">'
                if logo_b64 else '')

    lp = str(_LP)
    rp = str(100 - _LP)

    # 3. Right-panel + global CSS via st.markdown (plain CSS only, no complex HTML)
    st.markdown(f"""<style>
    html,body,[data-testid="stAppViewContainer"],[data-testid="stMain"],.main .block-container{{
        background:#ffffff!important;min-height:100vh!important;overflow-x:hidden!important;
    }}
    header,footer,[data-testid="stToolbar"],[data-testid="stDecoration"]{{display:none!important;}}
    .block-container{{padding:0!important;max-width:100%!important;}}

    [data-testid="stMain"]{{
        margin-left:{lp}%!important;width:{rp}%!important;max-width:{rp}%!important;
        min-height:100vh!important;background:#ffffff!important;padding:0!important;
    }}

    .rp-spacer{{min-height:10vh;}}
    .rp-header{{padding:0 52px;margin-bottom:28px;text-align:center;}}
    .rp-logo-mini{{display:flex;justify-content:center;margin-bottom:22px;}}
    .rp-logo-img{{width:200px;height:200px;object-fit:contain;border-radius:14px;
        box-shadow:0 4px 20px rgba(0,118,206,0.18);}}
    .rp-title{{font-size:28px;font-weight:800;color:#0f172a;margin:0 0 8px;text-align:center;
        letter-spacing:-0.4px;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;}}
    .rp-subtitle{{font-size:14px;color:#6b7280;margin:0;text-align:center;font-family:-apple-system,sans-serif;}}
    .rp-field-label{{font-size:11.5px!important;font-weight:700!important;color:#374151!important;
        letter-spacing:0.7px!important;text-transform:uppercase!important;
        margin:0 0 6px!important;display:block!important;
        font-family:-apple-system,sans-serif!important;padding:0 52px!important;}}
    .rp-footer{{margin-top:30px;padding:18px 52px 0;border-top:1px solid #f1f5f9;}}
    .rp-security-row{{display:flex;justify-content:center;gap:20px;margin-bottom:12px;}}
    .rp-sec-item{{font-size:11.5px;color:#9ca3af;font-family:-apple-system,sans-serif;}}
    .rp-copy{{font-size:11px;color:#d1d5db;text-align:center;margin:0;font-family:-apple-system,sans-serif;}}

    [data-testid="stMain"] [data-baseweb="select"]>div:first-child{{
        border-radius:10px!important;border:1.5px solid #e5e7eb!important;
        background:#f9fafb!important;min-height:48px!important;font-size:14px!important;
        transition:border-color .2s,box-shadow .2s!important;}}
    [data-testid="stMain"] [data-baseweb="select"]:focus-within>div:first-child{{
        border-color:#0076CE!important;box-shadow:0 0 0 3px rgba(0,118,206,.12)!important;
        background:#ffffff!important;}}

    /* ── Password / text input: single clean border ──────────────────────────
       Root cause of double-border: Streamlit injects its own theme primaryColor
       onto [data-baseweb="input"] on focus.  We must target that attribute
       directly (higher specificity than >div>div) and zero every child as well.
    ── */
    [data-testid="stMain"] [data-baseweb="input"]{{
        border-radius:10px!important;border:1.5px solid #e5e7eb!important;
        background:#f9fafb!important;min-height:48px!important;
        box-shadow:none!important;outline:none!important;
        transition:border-color .2s,box-shadow .2s!important;}}
    [data-testid="stMain"] [data-baseweb="input"]:focus-within{{
        border-color:#0076CE!important;
        box-shadow:0 0 0 3px rgba(0,118,206,.12)!important;
        background:#ffffff!important;}}
    /* Strip border/outline/shadow from every child inside the BaseWeb container */
    [data-testid="stMain"] [data-baseweb="input"]>div,
    [data-testid="stMain"] [data-baseweb="input"]>div>div{{
        border:none!important;outline:none!important;
        box-shadow:none!important;background:transparent!important;}}
    [data-testid="stMain"] [data-baseweb="input"] input,
    [data-testid="stMain"] [data-baseweb="input"] input:focus,
    [data-testid="stMain"] [data-baseweb="input"] input:focus-visible{{
        font-size:14px!important;color:#111827!important;
        border:none!important;outline:none!important;
        box-shadow:none!important;background:transparent!important;
        -webkit-box-shadow:none!important;}}
    [data-testid="stMain"] [data-baseweb="input"] button,
    [data-testid="stMain"] [data-baseweb="input"] button:focus{{
        border:none!important;outline:none!important;
        box-shadow:none!important;background:transparent!important;}}
    [data-testid="stMain"] [data-baseweb="input"] input::placeholder{{color:#c4c9d4!important;}}

    [data-testid="stMain"] .stSelectbox,[data-testid="stMain"] .stTextInput{{padding:0 52px!important;}}
    [data-testid="stMain"] .stButton{{padding:0 52px!important;}}
    [data-testid="stMain"] .stButton>button{{
        background:linear-gradient(135deg,#0076CE 0%,#0055a3 100%)!important;
        color:#ffffff!important;font-size:15px!important;font-weight:700!important;
        border:none!important;border-radius:10px!important;height:52px!important;
        width:100%!important;letter-spacing:.5px!important;
        box-shadow:0 4px 20px rgba(0,118,206,.36)!important;
        transition:all .22s cubic-bezier(.4,0,.2,1)!important;margin-top:6px!important;}}
    [data-testid="stMain"] .stButton>button:hover{{
        background:linear-gradient(135deg,#0088e8 0%,#0066c0 100%)!important;
        box-shadow:0 8px 32px rgba(0,118,206,.52)!important;transform:translateY(-2px)!important;}}
    [data-testid="stMain"] .stButton>button:active{{
        transform:translateY(0)!important;box-shadow:0 3px 14px rgba(0,118,206,.36)!important;}}
    [data-testid="stMain"] [data-testid="stAlert"],[data-testid="stMain"] .stAlert>div{{
        border-radius:10px!important;font-size:13.5px!important;margin:0 52px!important;}}

    /* hide Streamlit's own spinner while loading screen is active */
    [data-testid="stStatusWidget"]{{display:none!important;}}

    /* ── Mobile overrides (≤ 767px) ── */
    @media(max-width:767px){{

        /* Right panel fills 100% — left panel is hidden via its own CSS */
        [data-testid="stMain"]{{
            margin-left:0!important;
            width:100%!important;
            max-width:100%!important;
            min-height:100vh!important;
        }}

        /* Tighter spacer on mobile */
        .rp-spacer{{min-height:5vh!important;}}

        /* Logo smaller, header padding tighter */
        .rp-header{{padding:0 24px!important;margin-bottom:20px!important;}}
        .rp-logo-img{{width:80px!important;height:80px!important;}}
        .rp-title{{font-size:22px!important;margin:0 0 6px!important;}}
        .rp-subtitle{{font-size:13px!important;}}

        /* Field labels + inputs + button — reduce side padding for phone width */
        .rp-field-label{{padding:0 24px!important;}}
        [data-testid="stMain"] .stSelectbox,
        [data-testid="stMain"] .stTextInput{{padding:0 24px!important;}}
        [data-testid="stMain"] .stButton{{padding:0 24px!important;}}

        /* Alerts / error messages — match reduced padding */
        [data-testid="stMain"] [data-testid="stAlert"],
        [data-testid="stMain"] .stAlert>div{{margin:0 24px!important;}}

        /* Footer — tighter, wrap security badges */
        .rp-footer{{padding:16px 24px 0!important;}}
        .rp-security-row{{
            flex-wrap:wrap!important;
            gap:10px 18px!important;
            justify-content:center!important;
        }}
    }}

    /* ── Loading screen ── */
    #pak-loading{{
        position:fixed;inset:0;z-index:99999;
        background:linear-gradient(145deg,#060c18 0%,#0b1828 50%,#08121e 100%);
        display:flex;flex-direction:column;align-items:center;justify-content:center;
        font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
        -webkit-font-smoothing:antialiased;
    }}
    #pak-loading::before{{
        content:'';position:absolute;inset:0;
        background-image:radial-gradient(rgba(255,255,255,0.028) 1px,transparent 1px);
        background-size:30px 30px;pointer-events:none;
    }}
    .ld-logo{{width:80px;height:80px;object-fit:contain;border-radius:16px;
        box-shadow:0 8px 32px rgba(0,118,206,0.4);margin-bottom:22px;position:relative;}}
    .ld-logo-fb{{width:80px;height:80px;background:linear-gradient(135deg,#0076CE,#38bdf8);
        border-radius:16px;display:flex;align-items:center;justify-content:center;
        font-size:28px;font-weight:900;color:#fff;margin-bottom:22px;position:relative;
        box-shadow:0 8px 32px rgba(0,118,206,0.4);}}
    .ld-brand{{font-size:22px;font-weight:800;color:#ffffff;letter-spacing:2px;
        margin-bottom:10px;position:relative;}}
    .ld-sep{{width:48px;height:2px;background:linear-gradient(90deg,#0076CE,#38bdf8);
        border-radius:2px;margin:0 auto 28px;position:relative;}}
    .ld-msg{{font-size:16px;color:rgba(255,255,255,0.75);margin-bottom:6px;
        position:relative;letter-spacing:0.2px;}}
    .ld-sub{{font-size:13px;color:rgba(255,255,255,0.38);margin-bottom:36px;
        position:relative;font-style:italic;}}
    @keyframes ldPulse{{0%,80%,100%{{transform:scale(0);opacity:0.4}}
        40%{{transform:scale(1);opacity:1}}}}
    .ld-dots{{display:flex;gap:10px;position:relative;}}
    .ld-dots span{{width:11px;height:11px;border-radius:50%;background:#38bdf8;
        animation:ldPulse 1.5s ease-in-out infinite;}}
    .ld-dots span:nth-child(1){{animation-delay:0s;}}
    .ld-dots span:nth-child(2){{animation-delay:0.2s;}}
    .ld-dots span:nth-child(3){{animation-delay:0.4s;}}
    @keyframes ldProgress{{0%{{width:0%}}100%{{width:100%}}}}
    .ld-progress-track{{width:220px;height:3px;background:rgba(255,255,255,0.10);
        border-radius:2px;overflow:hidden;position:relative;margin-top:28px;}}
    .ld-progress-bar{{height:100%;width:0%;border-radius:2px;
        background:linear-gradient(90deg,#0076CE,#38bdf8);
        animation:ldProgress 2.2s cubic-bezier(.4,0,.6,1) forwards;}}
    </style>""", unsafe_allow_html=True)

    # 4. Left-panel CSS string (injected via JS — never passed to st.markdown)
    lp_css = (
        "#pak-login-left{position:fixed;top:0;left:0;bottom:0;width:" + lp + "%;"
        "z-index:9000;"
        "background:linear-gradient(150deg,#060c18 0%,#0b1828 45%,#08121e 100%);"
        "overflow:hidden;display:flex;flex-direction:column;"
        "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;"
        "-webkit-font-smoothing:antialiased;}"

        "#pak-login-left::before{content:'';position:absolute;inset:0;"
        "background-image:radial-gradient(rgba(255,255,255,0.028) 1px,transparent 1px);"
        "background-size:30px 30px;pointer-events:none;z-index:0;}"

        "#pak-login-left::after{content:'';position:absolute;top:0;left:0;right:0;height:3px;"
        "background:linear-gradient(90deg,transparent,#0076CE 35%,#38bdf8 65%,transparent);z-index:3;}"

        "@keyframes lpO1{0%,100%{transform:translate(0,0) scale(1)}"
        "33%{transform:translate(55px,-75px) scale(1.09)}"
        "66%{transform:translate(-35px,35px) scale(0.92)}}"
        "@keyframes lpO2{0%,100%{transform:translate(0,0) scale(1)}"
        "40%{transform:translate(-65px,45px) scale(1.06)}"
        "70%{transform:translate(45px,-30px) scale(0.94)}}"
        "@keyframes lpO3{0%,100%{transform:translate(0,0) scale(1)}"
        "50%{transform:translate(35px,55px) scale(1.12)}}"

        ".lp-orb{position:absolute;border-radius:50%;pointer-events:none;}"
        ".lp-orb1{width:560px;height:560px;"
        "background:radial-gradient(circle,rgba(0,118,206,0.22) 0%,transparent 65%);"
        "top:-190px;left:-160px;animation:lpO1 18s ease-in-out infinite;}"
        ".lp-orb2{width:450px;height:450px;"
        "background:radial-gradient(circle,rgba(56,189,248,0.13) 0%,transparent 65%);"
        "bottom:-130px;right:-90px;animation:lpO2 22s ease-in-out infinite;}"
        ".lp-orb3{width:340px;height:340px;"
        "background:radial-gradient(circle,rgba(99,102,241,0.10) 0%,transparent 65%);"
        "top:40%;left:40%;animation:lpO3 26s ease-in-out infinite;}"

        ".lp-content{position:relative;z-index:2;display:flex;flex-direction:column;"
        "justify-content:space-between;padding:44px 52px 40px;height:100%;box-sizing:border-box;}"

        ".lp-brand{display:flex;align-items:center;gap:13px;}"
        ".lp-logo-img{width:40px;height:40px;object-fit:contain;border-radius:9px;flex-shrink:0;}"
        ".lp-logo-fallback{width:40px;height:40px;"
        "background:linear-gradient(135deg,#0076CE,#38bdf8);border-radius:9px;"
        "display:flex;align-items:center;justify-content:center;"
        "font-size:14px;font-weight:800;color:#fff;flex-shrink:0;}"
        ".lp-brand-name{font-size:15px;font-weight:800;color:#fff;letter-spacing:1.5px;"
        "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;}"

        ".lp-eyebrow{font-size:11px;font-weight:700;color:#38bdf8;letter-spacing:3px;"
        "text-transform:uppercase;margin-bottom:16px;font-family:-apple-system,sans-serif;}"
        ".lp-headline{font-size:46px;font-weight:900;color:#fff;line-height:1.08;"
        "letter-spacing:-1px;margin:0 0 22px;"
        "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;}"
        ".lp-headline span{color:#38bdf8;}"
        ".lp-desc{font-size:14px;color:rgba(255,255,255,0.48);line-height:1.75;"
        "max-width:400px;margin:0;font-family:-apple-system,sans-serif;}"

        ".lp-features{display:flex;flex-direction:column;gap:12px;}"
        ".lp-feat{display:flex;align-items:flex-start;gap:14px;padding:15px 18px;"
        "background:rgba(255,255,255,0.038);border:1px solid rgba(255,255,255,0.07);"
        "border-radius:13px;transition:background .22s,border-color .22s,transform .22s;cursor:default;}"
        ".lp-feat:hover{background:rgba(0,118,206,0.10);"
        "border-color:rgba(0,118,206,0.30);transform:translateX(3px);}"
        ".lp-feat-ico{font-size:20px;flex-shrink:0;margin-top:1px;width:28px;text-align:center;}"
        ".lp-feat-title{font-size:13px;font-weight:700;color:#e2e8f0;margin-bottom:3px;"
        "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;}"
        ".lp-feat-sub{font-size:11.5px;color:rgba(255,255,255,0.38);line-height:1.5;"
        "font-family:-apple-system,sans-serif;}"

        ".lp-footer{display:flex;align-items:center;justify-content:space-between;"
        "padding-top:18px;border-top:1px solid rgba(255,255,255,0.07);}"
        ".lp-footer-copy{font-size:11px;color:rgba(255,255,255,0.25);font-family:-apple-system,sans-serif;}"
        ".lp-version{font-size:10.5px;font-weight:700;color:#38bdf8;"
        "background:rgba(56,189,248,0.10);border:1px solid rgba(56,189,248,0.22);"
        "padding:3px 10px;border-radius:20px;letter-spacing:.5px;font-family:-apple-system,sans-serif;}"

        "@media(max-width:767px){#pak-login-left{display:none!important;}}"
    )

    # 5. Left-panel HTML string
    lp_html = (
        '<div class="lp-orb lp-orb1"></div>'
        '<div class="lp-orb lp-orb2"></div>'
        '<div class="lp-orb lp-orb3"></div>'
        '<div class="lp-content">'
        '<div class="lp-brand">' + lp_logo +
        '<span class="lp-brand-name">PEAKADS\u00a0LLP</span></div>'
        '<div class="lp-tagline-block">'
        '<div class="lp-eyebrow">Revenue Intelligence Platform</div>'
        '<h1 class="lp-headline">Track.<br><span>Manage.</span><br>Grow.</h1>'
        '<p class="lp-desc">Complete financial visibility for your business. '
        'Monitor DSP &amp; SSP revenue, manage invoices, '
        'and track AR/AP ageing \u2014 all in one place.</p>'
        '</div>'
        '<div class="lp-features">'
        '<div class="lp-feat"><div class="lp-feat-ico">\U0001f4ca</div><div>'
        '<div class="lp-feat-title">Real-time Dashboard</div>'
        '<div class="lp-feat-sub">Live P&amp;L, KPIs and partner analytics at a glance</div>'
        '</div></div>'
        '<div class="lp-feat"><div class="lp-feat-ico">\U0001f9fe</div><div>'
        '<div class="lp-feat-title">Invoice Management</div>'
        '<div class="lp-feat-sub">DSP &amp; SSP invoicing with Dropbox cloud sync</div>'
        '</div></div>'
        '<div class="lp-feat"><div class="lp-feat-ico">\U0001f4c8</div><div>'
        '<div class="lp-feat-title">AR/AP Ageing</div>'
        '<div class="lp-feat-sub">Track overdue receivables &amp; payables by partner</div>'
        '</div></div>'
        '</div>'
        '<div class="lp-footer">'
        '<span class="lp-footer-copy">\u00a9 2025 PEAKADS LLP \u00b7 All rights reserved</span>'
        '<span class="lp-version">v 2.0</span>'
        '</div>'
        '</div>'
    )

    # 6. SINGLE iframe: cleanup stale elements → inject left panel → smart retries.
    #    All in one components.html() call so no two iframes can race against
    #    each other.  Retries ONLY re-create the panel if it goes missing;
    #    they never unconditionally remove it.
    def _make_inject_block(css_repr, html_repr):
        return (
            "var P=window.parent.document;"
            "['pak-sb','pak-sb-css','pak-login-left','pak-login-left-css','pak-loading'].forEach("
            "function(id){var e=P.getElementById(id);if(e)e.remove();});"
            "var m=P.querySelector('[data-testid=\"stMain\"]');"
            "if(m){m.style.marginLeft='';m.style.width='';m.style.maxWidth='';}"
            "var s=P.createElement('style');s.id='pak-login-left-css';"
            f"s.textContent={css_repr};"
            "P.head.appendChild(s);"
            "var d=P.createElement('div');d.id='pak-login-left';"
            f"d.innerHTML={html_repr};"
            "P.body.insertBefore(d,P.body.firstChild);"
        )

    def _make_retry_block(css_repr, html_repr):
        """Re-inject only if the panel is missing (never destroy an existing one)."""
        return (
            "var P=window.parent.document;if(!P||!P.body)return;"
            # Remove leftover navbar OR loading overlay in retries, never the login panel
            "['pak-sb','pak-sb-css','pak-loading'].forEach(function(id){var e=P.getElementById(id);if(e)e.remove();});"
            "if(P.getElementById('pak-login-left'))return;"
            "var s=P.createElement('style');s.id='pak-login-left-css';"
            f"s.textContent={css_repr};"
            "P.head.appendChild(s);"
            "var d=P.createElement('div');d.id='pak-login-left';"
            f"d.innerHTML={html_repr};"
            "P.body.insertBefore(d,P.body.firstChild);"
        )

    css_r  = repr(lp_css)
    html_r = repr(lp_html)

    combined_js = (
        # ── immediate boot (runs as soon as iframe loads) ──────────────────
        "(function boot(){"
        "var P=window.parent.document;"
        "if(!P||!P.body){setTimeout(boot,80);return;}"
        + _make_inject_block(css_r, html_r) +
        "})();"

        # ── retry 1 @ 350 ms ──────────────────────────────────────────────
        # (handles slow first renders; panel is re-created only if missing)
        "setTimeout(function(){" + _make_retry_block(css_r, html_r) + "},350);"

        # ── retry 2 @ 900 ms ──────────────────────────────────────────────
        "setTimeout(function(){" + _make_retry_block(css_r, html_r) + "},900);"

        # ── retry 3 @ 2000 ms ─────────────────────────────────────────────
        "setTimeout(function(){" + _make_retry_block(css_r, html_r) + "},2000);"
    )

    components.html(
        "<!DOCTYPE html><html><head><meta charset='utf-8'></head>"
        "<body style='margin:0;padding:0;background:transparent;'>"
        "<script>" + combined_js + "</script>"
        "</body></html>",
        height=0, scrolling=False,
    )

    # 7. Right panel — standard Streamlit widgets
    st.markdown('<div class="rp-spacer"></div>', unsafe_allow_html=True)

    st.markdown(
        f'<div class="rp-header">'
        f'<div class="rp-logo-mini">{rp_logo}</div>'
        f'<h2 class="rp-title">Welcome back</h2>'
        f'<p class="rp-subtitle">Sign in to your account to continue</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<span class="rp-field-label">Select User</span>', unsafe_allow_html=True)
    username = st.selectbox(
        "Select User", ["Admin", "Sales", "Finance", "User"],
        label_visibility="collapsed",
    )

    st.markdown('<div style="height:4px;"></div>', unsafe_allow_html=True)
    st.markdown('<span class="rp-field-label">Password</span>', unsafe_allow_html=True)
    password = st.text_input(
        "Password", type="password",
        placeholder="Enter your password",
        label_visibility="collapsed",
    )

    st.markdown('<div style="height:4px;"></div>', unsafe_allow_html=True)
    login_btn = st.button("Sign In  \u2192", use_container_width=True)

    # ── AUTH LOGIC ────────────────────────────────────────────────────────────
    if login_btn:
        if username in DEFAULT_USERS and password == DEFAULT_USERS[username]["password"]:
            # 1. Inject overlay NOW (same render as the button click).
            #    The overlay and its self-destruct <script> land in the parent
            #    DOM before st.rerun() fires.
            _inject_loading_screen(logo_b64, hold_seconds=6.5)
            # 2. Set state and rerun → app_loading handler just sleeps then flips
            st.session_state.app_loading  = True
            st.session_state.pending_user = username
            st.session_state.pending_role = DEFAULT_USERS[username]["role"]
            log_login(username)
            st.rerun()
        else:
            st.error("Incorrect password. Please try again.")

    st.markdown("""
<div class="rp-footer">
  <div class="rp-security-row">
    <span class="rp-sec-item">\U0001f512 Secure Access</span>
    <span class="rp-sec-item">\U0001f6e1\ufe0f Role-based</span>
    <span class="rp-sec-item">\U0001f4cb Audit Logs</span>
  </div>
  
</div>""", unsafe_allow_html=True)


# ===============================
# PASSWORD CHANGE (ADMIN ONLY)
# ===============================

def admin_change_password():
    st.subheader("\U0001f511 Change User Password")
    if st.session_state.role != "Admin":
        st.warning("Only Admin can change passwords")
        return
    user     = st.selectbox("Select User", ["Admin","Sales","Finance","User"])
    new_pass = st.text_input("New Password", type="password")
    st.divider()
    if st.button("Update Password"):
        DEFAULT_USERS[user]["password"] = new_pass
        st.success("Password Updated")

# ===============================
# ROLE ACCESS FUNCTION
# ===============================

def get_allowed_tabs():
    role = st.session_state.role
    return ROLE_ACCESS.get(role, [])
