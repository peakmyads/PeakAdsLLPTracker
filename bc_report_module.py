"""
bc_report_module.py  —  PEAKADS LLP
Balance Confirmation (BC) Report Tab

SEND METHOD: Microsoft Graph API → Teams Group Chat
────────────────────────────────────────────────────
Requires:
  • Azure App Registration (admin@peakmyads.com — work/school account)
  • API Permission: Chat.ReadWrite.All  (Application, admin consented)
  • Per-partner: Teams Group Chat ID

Flow:
  Button click in app
      → OAuth2 client_credentials token (Azure)
          → POST /v1.0/chats/{chat_id}/messages (Graph API)
              → Message in partner Teams group chat

FEATURES
────────
• Import BC Report xlsx (Month | Partner Name | DSP $(BC) | SSP $(BC))
• Net $(BC) = DSP - SSP auto-calculated on import
• Editable C DSP $ / C SSP $ inline; C Net $ = C DSP - C SSP live (JS)
• Send Teams per row  → sends numbers message via Graph API → Teams
• Number Confirmation → sends generic deadline reminder (selected rows)
• Confirm             → marks rows Confirmed, turns row green
• Push to Master Data → upserts selected rows into master_data table
• Status lifecycle: Pending → Sent → Confirmed
• Filters: Financial Year, Month, Partner (same style as Dashboard)
• Full Azure setup guide built into the tab

INTEGRATION
───────────
  from bc_report_module import render_bc_report_tab
  with tabs["BC Report"]:
      render_bc_report_tab()
"""

import os
import sys
import sqlite3
from datetime import datetime

import pandas as pd
import requests
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode, DataReturnMode


# ═══════════════════════════════════════════════════════════════════════════
# DB PATH
# ═══════════════════════════════════════════════════════════════════════════

if getattr(sys, "frozen", False):
    _BASE_DIR = os.path.dirname(sys.executable)
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))

_DB_PATH = os.path.join(_BASE_DIR, "tracker.db")


def _conn():
    return sqlite3.connect(_DB_PATH, check_same_thread=False)


# ═══════════════════════════════════════════════════════════════════════════
# DB INIT
# ═══════════════════════════════════════════════════════════════════════════

def init_bc_report_tables():
    """Create all BC Report tables on first run (idempotent)."""
    con = _conn()
    con.executescript("""
        CREATE TABLE IF NOT EXISTS bc_report (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            month         TEXT,
            partner_name  TEXT,
            dsp_bc        REAL DEFAULT 0,
            ssp_bc        REAL DEFAULT 0,
            net_bc        REAL DEFAULT 0,
            c_dsp         REAL DEFAULT 0,
            c_ssp         REAL DEFAULT 0,
            c_net         REAL DEFAULT 0,
            status        TEXT DEFAULT 'Pending',
            sent_at       TEXT,
            UNIQUE(month, partner_name)
        );

        CREATE TABLE IF NOT EXISTS bc_teams_config (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            partner_name  TEXT UNIQUE,
            teams_chat_id TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS bc_azure_config (
            id            INTEGER PRIMARY KEY,
            tenant_id     TEXT DEFAULT '',
            client_id     TEXT DEFAULT '',
            client_secret TEXT DEFAULT '',
            username      TEXT DEFAULT '',
            password      TEXT DEFAULT ''
        );
    """)
    # Migrate existing DBs — add missing columns to all tables
    migrations = [
        ("bc_report",       "sent_at",        "ALTER TABLE bc_report ADD COLUMN sent_at TEXT"),
        ("bc_azure_config", "username",        "ALTER TABLE bc_azure_config ADD COLUMN username TEXT DEFAULT ''"),
        ("bc_azure_config", "password",        "ALTER TABLE bc_azure_config ADD COLUMN password TEXT DEFAULT ''"),
        ("bc_azure_config", "refresh_token",   "ALTER TABLE bc_azure_config ADD COLUMN refresh_token TEXT DEFAULT ''"),
    ]
    for table, col, sql in migrations:
        try:
            cols = [r[1] for r in con.execute(f"PRAGMA table_info({table})").fetchall()]
            if col not in cols:
                con.execute(sql)
        except Exception:
            pass
    con.commit()
    con.close()


# ═══════════════════════════════════════════════════════════════════════════
# DATA ACCESS
# ═══════════════════════════════════════════════════════════════════════════

_COL_RENAME = {
    "month":        "Month",
    "partner_name": "Partner Name",
    "dsp_bc":       "DSP $ (BC)",
    "ssp_bc":       "SSP $ (BC)",
    "net_bc":       "Net $ (BC)",
    "c_dsp":        "C DSP $",
    "c_ssp":        "C SSP $",
    "c_net":        "C Net $",
    "status":       "Status",
    "sent_at":      "sent_at",
}


def _load_bc_report() -> pd.DataFrame:
    con = _conn()
    try:
        df = pd.read_sql(
            "SELECT * FROM bc_report ORDER BY month, partner_name", con
        )
    except Exception:
        df = pd.DataFrame()
    con.close()
    if df.empty:
        return pd.DataFrame(columns=list(_COL_RENAME.values()) + ["id"])
    df.rename(columns=_COL_RENAME, inplace=True)
    for col in ["DSP $ (BC)", "SSP $ (BC)", "Net $ (BC)",
                "C DSP $", "C SSP $", "C Net $"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def _upsert_bc_report(df: pd.DataFrame):
    """Import rows — updates BC amounts, preserves status/C edits."""
    con = _conn()
    for _, row in df.iterrows():
        con.execute("""
            INSERT INTO bc_report
                (month, partner_name, dsp_bc, ssp_bc, net_bc,
                 c_dsp, c_ssp, c_net, status)
            VALUES (?,?,?,?,?,?,?,?,'Pending')
            ON CONFLICT(month, partner_name) DO UPDATE SET
                dsp_bc = excluded.dsp_bc,
                ssp_bc = excluded.ssp_bc,
                net_bc = excluded.net_bc
        """, (
            str(row.get("Month", "")),
            str(row.get("Partner Name", "")),
            float(row.get("DSP $ (BC)", 0) or 0),
            float(row.get("SSP $ (BC)", 0) or 0),
            float(row.get("Net $ (BC)", 0) or 0),
            float(row.get("C DSP $", 0) or 0),
            float(row.get("C SSP $", 0) or 0),
            float(row.get("C Net $", 0) or 0),
        ))
    con.commit()
    con.close()


def _save_c_edits(df: pd.DataFrame):
    con = _conn()
    for _, row in df.iterrows():
        c_dsp = float(row.get("C DSP $", 0) or 0)
        c_ssp = float(row.get("C SSP $", 0) or 0)
        con.execute(
            "UPDATE bc_report SET c_dsp=?, c_ssp=?, c_net=? "
            "WHERE month=? AND partner_name=?",
            (c_dsp, c_ssp, round(c_dsp - c_ssp, 6),
             str(row["Month"]), str(row["Partner Name"])),
        )
    con.commit()
    con.close()


def _set_status(month: str, partner: str, status: str):
    con = _conn()
    if status == "Sent":
        con.execute(
            "UPDATE bc_report SET status=?, sent_at=? "
            "WHERE month=? AND partner_name=?",
            (status, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), month, partner),
        )
    else:
        con.execute(
            "UPDATE bc_report SET status=? WHERE month=? AND partner_name=?",
            (status, month, partner),
        )
    con.commit()
    con.close()


def _push_to_master(rows: list) -> tuple:
    """
    True upsert into master_data — checks existence first to prevent duplicates.
    Returns (inserted_count, updated_count).
    """
    con = _conn()
    inserted, updated = 0, 0
    for row in rows:
        month   = str(row.get("Month", "")        or "").strip()
        partner = str(row.get("Partner Name", "") or "").strip()
        if not month or not partner:
            continue
        dsp  = float(row.get("DSP $ (BC)", 0) or 0)
        ssp  = float(row.get("SSP $ (BC)", 0) or 0)
        net  = round(dsp - ssp, 6)
        cdsp = float(row.get("C DSP $",    0) or 0)
        cssp = float(row.get("C SSP $",    0) or 0)
        cnet = round(cdsp - cssp, 6)
        # Check if row already exists (master_data may not have an id column)
        exists = con.execute(
            'SELECT COUNT(*) FROM master_data WHERE "Month"=? AND "Partner Name"=?',
            (month, partner)
        ).fetchone()[0] > 0
        if exists:
            con.execute("""
                UPDATE master_data
                SET "DSP $ (BC)"=?, "SSP $ (BC)"=?, "Net $ (BC)"=?,
                    "C DSP $"=?,    "C SSP $"=?,    "C Net $"=?
                WHERE "Month"=? AND "Partner Name"=?
            """, (dsp, ssp, net, cdsp, cssp, cnet, month, partner))
            updated += 1
        else:
            con.execute("""
                INSERT INTO master_data
                    ("Month", "Partner Name",
                     "DSP $ (BC)", "SSP $ (BC)", "Net $ (BC)",
                     "C DSP $", "C SSP $", "C Net $")
                VALUES (?,?,?,?,?,?,?,?)
            """, (month, partner, dsp, ssp, net, cdsp, cssp, cnet))
            inserted += 1
    con.commit()
    con.close()
    return inserted, updated


# ── Azure / Teams config ───────────────────────────────────────────────────

def _load_azure_cfg() -> dict:
    con = _conn()
    try:
        # Migrate: ensure username + password columns exist
        # (handles old DBs that may have ms_password or missing columns)
        cols = [r[1] for r in con.execute(
            "PRAGMA table_info(bc_azure_config)"
        ).fetchall()]
        if "username" not in cols:
            con.execute(
                "ALTER TABLE bc_azure_config ADD COLUMN username TEXT DEFAULT ''"
            )
        if "password" not in cols:
            con.execute(
                "ALTER TABLE bc_azure_config ADD COLUMN password TEXT DEFAULT ''"
            )
        con.commit()
        row = con.execute(
            "SELECT tenant_id, client_id, client_secret, username, password, refresh_token "
            "FROM bc_azure_config WHERE id=1"
        ).fetchone()
    except Exception:
        row = None
    con.close()
    if row:
        return {
            "tenant_id":     row[0] or "", "client_id":     row[1] or "",
            "client_secret": row[2] or "", "username":      row[3] or "",
            "password":      row[4] or "", "refresh_token": row[5] or "",
        }
    return {}


def _save_azure_cfg(tid: str, cid: str, csec: str,
                    username: str = "", password: str = ""):
    """Save credentials — does NOT touch refresh_token (preserved separately)."""
    con = _conn()
    con.execute("""
        INSERT INTO bc_azure_config
            (id, tenant_id, client_id, client_secret, username, password)
        VALUES (1,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET
            tenant_id=excluded.tenant_id,
            client_id=excluded.client_id,
            client_secret=excluded.client_secret,
            username=excluded.username,
            password=excluded.password
    """, (tid, cid, csec, username, password))
    con.commit()
    con.close()


def _save_refresh_token(token: str):
    """Store (or clear) the refresh token obtained from Device Code Flow."""
    con = _conn()
    try:
        con.execute(
            "UPDATE bc_azure_config SET refresh_token=? WHERE id=1",
            (token,)
        )
        con.commit()
    except Exception:
        pass
    con.close()


def _load_teams_cfg() -> dict:
    """Returns {partner_name: chat_id}"""
    con = _conn()
    try:
        rows = con.execute(
            "SELECT partner_name, teams_chat_id FROM bc_teams_config"
        ).fetchall()
    except Exception:
        rows = []
    con.close()
    return {r[0]: r[1] for r in rows if r[1]}


def _save_teams_cfg(partner: str, chat_id: str):
    con = _conn()
    con.execute("""
        INSERT INTO bc_teams_config (partner_name, teams_chat_id) VALUES (?,?)
        ON CONFLICT(partner_name) DO UPDATE SET
            teams_chat_id=excluded.teams_chat_id
    """, (partner, chat_id.strip()))
    con.commit()
    con.close()


# ── Activity Log ──────────────────────────────────────────────────────────

def _ensure_log_table(con):
    """Create bc_activity_log if it doesn't exist — called before every write."""
    con.execute("""
        CREATE TABLE IF NOT EXISTS bc_activity_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            logged_at    TEXT,
            partner_name TEXT,
            month        TEXT,
            action       TEXT,
            status       TEXT DEFAULT 'Success'
        )
    """)
    con.commit()


def _log_action(partner: str, month: str, action: str, status: str = "Success"):
    """Append one row to bc_activity_log. Creates table first if missing."""
    con = _conn()
    _ensure_log_table(con)
    con.execute(
        "INSERT INTO bc_activity_log (logged_at, partner_name, month, action, status) "
        "VALUES (?,?,?,?,?)",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
         partner, month, action, status),
    )
    con.commit()
    con.close()


def _load_activity_log(limit: int = 100) -> pd.DataFrame:
    con = _conn()
    _ensure_log_table(con)
    try:
        df = pd.read_sql(
            "SELECT logged_at, partner_name, month, action, status "
            "FROM bc_activity_log ORDER BY id DESC LIMIT ?",
            con, params=(limit,)
        )
    except Exception:
        df = pd.DataFrame(
            columns=["logged_at", "partner_name", "month", "action", "status"]
        )
    con.close()
    df.rename(columns={
        "logged_at":    "Date & Time",
        "partner_name": "Partner",
        "month":        "Month",
        "action":       "Action",
        "status":       "Status",
    }, inplace=True)
    return df


def _build_welcome_msg() -> str:
    """HTML welcome message sent when a Chat ID is first configured."""
    return (
        "<p>Hi Team,</p>"
        "<p>This is the <strong>PeakAds LLP Number Confirmation Bot</strong>, "
        "set up to streamline our monthly reconciliation process.</p>"
        "<p>Going forward, you will receive two types of messages from me here:</p>"
        "<ol>"
        "<li><strong>Reminder for Number Confirmation Request</strong> — sent at the beginning of each month, "
        "asking you to confirm the previous month's activity numbers before the 10th.</li>"
        "<li><strong>Number Confirmation</strong> — a detailed breakdown of the monthly figures "
        "(DSP, SSP, and Net amounts) for your review and sign-off.</li>"
        "</ol>"
        "<p>Please respond promptly so we can close the month efficiently. "
        "If you have any queries, please reach out to "
        "<a href='mailto:finance@peakmyads.com'>finance@peakmyads.com</a>.</p>"
        "<p>Thank you for your cooperation!</p>"
        "<p><strong>PeakAds LLP Finance Team</strong></p>"
    )


# ═══════════════════════════════════════════════════════════════════════════
# GRAPH API
# ═══════════════════════════════════════════════════════════════════════════

def _azure_error(r) -> str:
    """Parse Azure error response into a human-readable string."""
    try:
        b = r.json()
        desc = b.get("error_description", r.text)
        import re as _re
        m = _re.search(r"AADSTS\d+", desc)
        code = m.group(0) if m else b.get("error", "error")
        return f"{code}: {desc}"
    except Exception:
        return r.text


def _start_device_code_flow(cfg: dict) -> dict:
    """
    Phase 1 — request a device code.
    Returns Azure response: {device_code, user_code, verification_uri,
                              expires_in, interval, message}
    """
    url = (
        f"https://login.microsoftonline.com/{cfg['tenant_id']}"
        "/oauth2/v2.0/devicecode"
    )
    r = requests.post(url, data={
        "client_id":     cfg["client_id"],
        "client_secret": cfg["client_secret"],   # required for confidential clients
        "scope":         "https://graph.microsoft.com/.default offline_access",
    }, timeout=20)
    if not r.ok:
        raise RuntimeError(f"Device code request failed: {_azure_error(r)}")
    return r.json()


def _poll_device_code(cfg: dict, device_code: str, interval: int = 5) -> dict:
    """
    Phase 2 — poll until the user completes sign-in in the browser.
    Returns full token response (includes access_token + refresh_token).
    Raises RuntimeError on permanent failure or timeout (5 min).
    """
    import time
    url = (
        f"https://login.microsoftonline.com/{cfg['tenant_id']}"
        "/oauth2/v2.0/token"
    )
    deadline = time.time() + 300
    while time.time() < deadline:
        time.sleep(interval)
        r = requests.post(url, data={
            "grant_type":  "urn:ietf:params:oauth:grant-type:device_code",
            "client_id":   cfg["client_id"],
            "device_code": device_code,
        }, timeout=20)
        body = r.json()
        if "access_token" in body:
            return body
        err = body.get("error", "")
        if err == "authorization_pending":
            continue
        if err == "slow_down":
            interval = min(interval + 5, 30)
            continue
        raise RuntimeError(body.get("error_description", err))
    raise RuntimeError("Authentication timed out (5 min). Please try again.")


def _use_refresh_token(cfg: dict) -> str:
    """
    Exchange stored refresh token for a fresh access token.
    Raises RuntimeError if refresh token is expired/revoked.
    """
    url = (
        f"https://login.microsoftonline.com/{cfg['tenant_id']}"
        "/oauth2/v2.0/token"
    )
    r = requests.post(url, data={
        "grant_type":    "refresh_token",
        "client_id":     cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "refresh_token": cfg["refresh_token"],
        "scope":         "https://graph.microsoft.com/.default offline_access",
    }, timeout=20)
    if not r.ok:
        raise RuntimeError(f"Refresh token failed: {_azure_error(r)}")
    body = r.json()
    # Azure may issue a new refresh token — store it
    if body.get("refresh_token"):
        _save_refresh_token(body["refresh_token"])
    return body["access_token"]


def _get_token(cfg: dict) -> str:
    """
    Token acquisition priority:
      1. Refresh token  (Device Code Flow result — MFA-safe, recommended)
      2. ROPC password  (legacy, fails if MFA is ON)
      3. client_credentials (application flow, no user context)

    Raises a descriptive RuntimeError with Azure's AADSTS code so the user
    knows exactly what to fix instead of a raw HTTP 400.
    """
    tenant_id     = (cfg.get("tenant_id")     or "").strip()
    client_id     = (cfg.get("client_id")     or "").strip()
    client_secret = (cfg.get("client_secret") or "").strip()
    refresh_token = (cfg.get("refresh_token") or "").strip()
    username      = (cfg.get("username")      or "").strip()
    password      = (cfg.get("password")      or "").strip()

    if not tenant_id or not client_id or not client_secret:
        raise RuntimeError(
            "Missing credentials — Tenant ID, Client ID and Client Secret are all required."
        )

    # ── Priority 1: Refresh token from Device Code Flow (MFA-safe) ───────────
    if refresh_token:
        try:
            return _use_refresh_token(cfg)
        except Exception as e:
            # Expired/revoked — clear it and fall through
            _save_refresh_token("")
            # Re-raise with clear message so user knows to re-authenticate
            raise RuntimeError(
                f"Refresh token expired or revoked. "
                f"Please use 'Authenticate with Microsoft' again. Detail: {e}"
            )

    # ── Priority 2: ROPC password flow (fails when MFA is ON) ────────────────
    if username and password:
        url = (
            f"https://login.microsoftonline.com/{tenant_id}"
            "/oauth2/v2.0/token"
        )
        r = requests.post(url, data={
            "grant_type":    "password",
            "client_id":     client_id,
            "client_secret": client_secret,
            "username":      username,
            "password":      password,
            "scope":         "https://graph.microsoft.com/.default offline_access",
        }, timeout=20)
        if not r.ok:
            raise RuntimeError(f"Azure token error [ROPC (delegated)] {_azure_error(r)}")
        body = r.json()
        if "access_token" not in body:
            raise RuntimeError(f"No access_token in Azure ROPC response: {body}")
        return body["access_token"]

    # ── Priority 3: client_credentials (application, no user context) ─────────
    url = (
        f"https://login.microsoftonline.com/{tenant_id}"
        "/oauth2/v2.0/token"
    )
    r = requests.post(url, data={
        "grant_type":    "client_credentials",
        "client_id":     client_id,
        "client_secret": client_secret,
        "scope":         "https://graph.microsoft.com/.default",
    }, timeout=20)
    if not r.ok:
        raise RuntimeError(f"Azure token error [client_credentials] {_azure_error(r)}")
    body = r.json()
    if "access_token" not in body:
        raise RuntimeError(f"No access_token in Azure response: {body}")
    return body["access_token"]


def _send_graph_message(token: str, chat_id: str, html_body: str):
    r = requests.post(
        f"https://graph.microsoft.com/v1.0/chats/{chat_id}/messages",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        },
        json={"body": {"contentType": "html", "content": html_body}},
        timeout=20,
    )
    if not r.ok:
        try:
            err = r.json()
            code    = err.get("error", {}).get("code", "")
            message = err.get("error", {}).get("message", r.text)
            raise RuntimeError(f"Graph API error [{r.status_code}] {code}: {message}")
        except RuntimeError:
            raise
        except Exception:
            r.raise_for_status()


# ═══════════════════════════════════════════════════════════════════════════
# MESSAGE BUILDERS
# ═══════════════════════════════════════════════════════════════════════════

def _following_10th(month_str: str) -> str:
    """'Apr-2026' → '10th May 2026'"""
    try:
        dt = pd.to_datetime(month_str, format="%b-%Y")
        nxt = (dt.replace(month=1, year=dt.year + 1)
               if dt.month == 12 else dt.replace(month=dt.month + 1))
        return nxt.strftime("10th %B %Y")
    except Exception:
        return "10th of the following month"


def _month_upper(month_str: str) -> str:
    """'Apr-2026' → 'APRIL 2026'"""
    try:
        return pd.to_datetime(month_str, format="%b-%Y").strftime("%B %Y").upper()
    except Exception:
        return month_str.upper()


def _build_number_msg(month_str: str) -> str:
    mu   = _month_upper(month_str)
    dead = _following_10th(month_str)
    return (
        f"<p>Hi Team,</p>"
        f"<p>Please confirm the activity numbers for <strong>{mu}</strong> "
        f"on or before <strong>{dead}</strong>.</p>"
        f"<p>In case we do not receive your confirmation by the above deadline, "
        f"we will proceed with our numbers and close the month accordingly.</p>"
        f"<p>Thank you in advance for your cooperation.</p>"
    )


def _build_send_teams_msg(row: dict) -> str:
    month    = str(row.get("Month", ""))
    dsp      = float(row.get("DSP $ (BC)", 0) or 0)
    ssp      = float(row.get("SSP $ (BC)", 0) or 0)
    net      = float(row.get("Net $ (BC)", 0) or 0)
    deadline = _following_10th(month)
    # Net label: negative = we owe partner, positive = partner owes us
    if net < 0:
        net_label = "We owe you"
    elif net > 0:
        net_label = "You owe us"
    else:
        net_label = "Settled"
    return (
        f"<p>Hi Team, please confirm below numbers for the month of "
        f"<strong>{month}</strong> before <strong>{deadline}</strong>.</p>"
        f"<ul>"
        f"<li>You owe us &nbsp;&mdash;&nbsp; <strong>${dsp:,.2f}</strong></li>"
        f"<li>We owe you &nbsp;&mdash;&nbsp; <strong>${ssp:,.2f}</strong></li>"
        f"<li>Netted &nbsp;&mdash;&nbsp; <strong>${net:,.2f}</strong>"
        f" &nbsp;({net_label})</li>"
        f"</ul>"
    )


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _gen_fy_list():
    y, m = datetime.today().year, datetime.today().month
    s = y if m >= 4 else y - 1
    return [f"{s-1}-{str(s)[-2:]}", f"{s}-{str(s+1)[-2:]}"]


def _fy_range(fy: str):
    sy = int(fy.split("-")[0])
    return pd.to_datetime(f"{sy}-04-01"), pd.to_datetime(f"{sy+1}-03-31")


def _require_azure(cfg: dict) -> bool:
    missing = [k for k in ["tenant_id","client_id","client_secret","username","password"]
               if not cfg.get(k)]
    if missing:
        st.error(
            "⚠️ Azure configuration incomplete. "
            "Open **⚙️ Azure / Teams Configuration** and fill in all 5 fields: "
            "Tenant ID, Client ID, Client Secret, Email and Password."
        )
        return False
    return True


# ═══════════════════════════════════════════════════════════════════════════
# AGGRID CONFIG
# ═══════════════════════════════════════════════════════════════════════════

_GRID_CSS = {
    ".ag-header": {
        "background-color": "#003366 !important",
        "color":            "white !important",
        "font-weight":      "bold !important",
    },
    ".ag-header-cell-label": {
        "color": "white !important",
    },
    ".ag-row-even": {
        "background-color": "#f8faff !important",
    },
    ".ag-row-odd": {
        "background-color": "#eef3fc !important",
    },
    ".ag-row-hover": {
        "background-color": "#dce8ff !important",
    },
    ".ag-cell": {
        "font-size":   "12.5px !important",
        "font-family": "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important",
    },
    ".ag-pinned-bottom-container .ag-row": {
        "background-color": "#003366 !important",
        "color":            "white !important",
        "font-weight":      "bold !important",
        "font-size":        "13px !important",
    },
}

_FMT_CURRENCY = JsCode("""
function(p) {
    if (p.value == null || p.value === '') return '';
    return '$' + parseFloat(p.value).toLocaleString(undefined,
        {minimumFractionDigits:2, maximumFractionDigits:2});
}""")

_GET_NET_BC = JsCode("""
function(p) {
    return Math.round(((parseFloat(p.data['DSP $ (BC)'])||0)
                     - (parseFloat(p.data['SSP $ (BC)'])||0)) * 100) / 100;
}""")

_GET_C_NET = JsCode("""
function(p) {
    return Math.round(((parseFloat(p.data['C DSP $'])||0)
                     - (parseFloat(p.data['C SSP $'])||0)) * 100) / 100;
}""")

_STYLE_STATUS = JsCode("""
function(p) {
    if (p.node && p.node.rowPinned) return {};
    var v = (p.value||'').toLowerCase();
    if (v==='confirmed') return {color:'#155724',backgroundColor:'#d4edda',fontWeight:'bold'};
    if (v==='sent')      return {color:'#004085',backgroundColor:'#cce5ff',fontWeight:'bold'};
    if (!v) return {};
    return {color:'#856404',backgroundColor:'#fff3cd',fontWeight:'bold'};
}""")

_STYLE_ROW = JsCode("""
function(p) {
    if (p.node && p.node.rowPinned) {
        return {backgroundColor:'#dce6f1', color:'#003366',
                fontWeight:'bold', fontSize:'13px', borderTop:'2px solid #0076CE'};
    }
    if (!p.data) return {};
    var s = (p.data['Status']||'').toLowerCase();
    if (s==='confirmed') return {backgroundColor:'#c6efce', color:'#155724', fontWeight:'bold'};
    if (s==='sent')      return {backgroundColor:'#dbeafe', color:'#004085', fontWeight:'bold'};
    return {};
}""")

_RENDER_SEND_BTN = JsCode("""
function(p) {
    return '<span style="display:inline-block;padding:3px 12px;border-radius:12px;'
         + 'border:1px solid #0076CE;background:rgba(0,118,206,0.12);'
         + 'color:#0076CE;font-size:11.5px;font-weight:600;cursor:pointer;'
         + 'white-space:nowrap;line-height:1.6;user-select:none;">&#128228; Send</span>';
}""")

_ON_CELL_CLICK = JsCode("""
function(p) {
    if (p.column && p.column.colId === 'Send Teams') {
        p.api.deselectAll();
        p.node.setSelected(true);
    }
}""")

_GRAND_TOTAL = JsCode("""
function(api) {
    var d=0,s=0,n=0,cd=0,cs=0,cn=0;
    api.forEachNodeAfterFilter(function(nd) {
        if (!nd.data) return;
        d  += parseFloat(nd.data['DSP $ (BC)'])||0;
        s  += parseFloat(nd.data['SSP $ (BC)'])||0;
        n  += parseFloat(nd.data['Net $ (BC)'])||0;
        cd += parseFloat(nd.data['C DSP $'])||0;
        cs += parseFloat(nd.data['C SSP $'])||0;
        cn += parseFloat(nd.data['C Net $'])||0;
    });
    api.setPinnedBottomRowData([{
        'Partner Name':'Grand Total',
        'DSP $ (BC)':d,'SSP $ (BC)':s,'Net $ (BC)':n,
        'C DSP $':cd,'C SSP $':cs,'C Net $':cn
    }]);
}""")


def _build_grid_opts(df: pd.DataFrame) -> dict:
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_selection("multiple", use_checkbox=True,
                           suppressRowClickSelection=True)
    gb.configure_default_column(resizable=True, sortable=True,
                                filter=True, editable=False)

    gb.configure_column("Month", pinned="left", flex=1, minWidth=85,
                        headerCheckboxSelection=True, checkboxSelection=True)
    gb.configure_column("Partner Name", pinned="left", flex=1.6, minWidth=130)

    for col in ["DSP $ (BC)", "SSP $ (BC)"]:
        gb.configure_column(col, type=["numericColumn"],
                            valueFormatter=_FMT_CURRENCY, flex=1.2, minWidth=100)

    gb.configure_column("Net $ (BC)", type=["numericColumn"],
                        valueGetter=_GET_NET_BC, valueFormatter=_FMT_CURRENCY,
                        editable=False, flex=1.2, minWidth=100)

    _edit_cell = {"backgroundColor": "#f0f8ff", "border": "1px solid #90caf9"}
    gb.configure_column("C DSP $", type=["numericColumn"],
                        valueFormatter=_FMT_CURRENCY, editable=True,
                        cellStyle=_edit_cell, flex=1.2, minWidth=100)
    gb.configure_column("C SSP $", type=["numericColumn"],
                        valueFormatter=_FMT_CURRENCY, editable=True,
                        cellStyle=_edit_cell, flex=1.2, minWidth=100)
    gb.configure_column("C Net $", type=["numericColumn"],
                        valueGetter=_GET_C_NET, valueFormatter=_FMT_CURRENCY,
                        editable=False, flex=1.2, minWidth=100)

    gb.configure_column("Send Teams", cellRenderer=_RENDER_SEND_BTN,
                        editable=False, sortable=False, filter=False,
                        flex=0.9, minWidth=95, headerName="Send Teams")
    gb.configure_column("Status", cellStyle=_STYLE_STATUS,
                        editable=False, flex=1, minWidth=95)

    for col in ["id", "sent_at", "teams_sent_at"]:
        if col in df.columns:
            gb.configure_column(col, hide=True)

    opts = gb.build()
    opts["getRowStyle"]                   = _STYLE_ROW
    opts["stopEditingWhenCellsLoseFocus"] = True
    opts["stopEditingWhenGridLosesFocus"] = True
    opts["onFirstDataRendered"]           = _GRAND_TOTAL
    opts["onCellValueChanged"]            = _GRAND_TOTAL
    opts["onFilterChanged"]               = _GRAND_TOTAL
    opts["onGridReady"] = JsCode("function(p){ p.api.sizeColumnsToFit(); }")
    opts["onCellClicked"]                 = _ON_CELL_CLICK
    return opts


# ═══════════════════════════════════════════════════════════════════════════
# UI — AZURE CONFIG SECTION
# ═══════════════════════════════════════════════════════════════════════════

def _render_azure_config():
    st.markdown(
        "<div style='color:#90caf9;font-size:13px;margin-bottom:10px;'>"
        "Enter your Azure App credentials and Microsoft account details below. "
        "Use <b>finance@peakmyads.onmicrosoft.com</b> as the sending account — "
        "it must be a member of all partner group chats."
        "</div>",
        unsafe_allow_html=True,
    )

    cfg = _load_azure_cfg()

    st.markdown(
        "<div style='background:rgba(0,118,206,0.08);border-left:3px solid #0076CE;"
        "padding:8px 12px;border-radius:4px;font-size:12.5px;color:#90caf9;"
        "margin-bottom:10px;'>"
        "⚠️ <b>Important:</b> Use <b>Delegated</b> permission "
        "(<code>Chat.ReadWrite</code>) and fill in <b>Username + Password</b> below. "
        "The app will send messages as <b>admin@peakmyads.com</b> — "
        "that account must be a <b>member</b> of each partner's Teams group chat."
        "</div>",
        unsafe_allow_html=True,
    )

    # Row 1 — App credentials
    a1, a2, a3 = st.columns([1, 1, 1])
    with a1:
        tid = st.text_input(
            "Tenant ID",
            value=cfg.get("tenant_id", ""),
            key="bc_az_tid",
            placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        )
    with a2:
        cid = st.text_input(
            "Client (App) ID",
            value=cfg.get("client_id", ""),
            key="bc_az_cid",
            placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        )
    with a3:
        csec = st.text_input(
            "Client Secret",
            value=cfg.get("client_secret", ""),
            key="bc_az_csec",
            type="password",
            placeholder="Your app secret value",
        )

    # Row 2 — Delegated user credentials
    b1, b2, b3 = st.columns([1, 1, 1])
    with b1:
        uname = st.text_input(
            "Microsoft Account Email",
            value=cfg.get("username", ""),
            key="bc_az_uname",
            placeholder="finance@peakmyads.onmicrosoft.com",
            help="Use finance@peakmyads.onmicrosoft.com — this account sends the Teams messages and must be a member of all partner group chats.",
        )
    with b2:
        passwd = st.text_input(
            "Password",
            value=cfg.get("password", ""),
            key="bc_az_pass",
            type="password",
            placeholder="Account password",
            help="Used only for Microsoft Graph API authentication (ROPC flow). Stored locally.",
        )
    with b3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💾 Save All", key="bc_az_save"):
            if tid.strip() and cid.strip() and csec.strip() and uname.strip() and passwd.strip():
                _save_azure_cfg(tid.strip(), cid.strip(), csec.strip(),
                                uname.strip(), passwd.strip())
                st.success("✅ Azure configuration saved.")
            else:
                st.error("All 5 fields are required (Tenant ID, Client ID, "
                         "Client Secret, Username, Password).")

    # ── Device Code Flow (MFA-safe, recommended) ─────────────────────────────
    st.markdown(
        "<div style='background:rgba(0,118,206,0.10);border-left:4px solid #0076CE;"
        "padding:10px 14px;border-radius:6px;margin:10px 0;font-size:13px;color:#003a6e;'>"
        "🔑 <b>MFA accounts:</b> Use <b>Authenticate with Microsoft</b> below instead of "
        "Username/Password. You sign in once in your browser (MFA included) and a refresh "
        "token is stored — all future sends work silently without MFA prompts."
        "</div>",
        unsafe_allow_html=True,
    )

    auth_cfg = _load_azure_cfg()
    has_refresh = bool(auth_cfg.get("refresh_token", "").strip())
    dc_flow = st.session_state.get("bc_dc_flow")  # holds phase-1 response

    auth_c1, auth_c2 = st.columns([1, 3])
    with auth_c1:
        if has_refresh:
            if st.button("🔄 Re-authenticate Microsoft", key="bc_dc_start"):
                _save_refresh_token("")
                st.session_state.pop("bc_dc_flow", None)
                st.rerun()
        else:
            if st.button("🔑 Authenticate with Microsoft", key="bc_dc_start"):
                cfg_now = _load_azure_cfg()
                missing_now = [k for k in ("tenant_id", "client_id", "client_secret")
                               if not (cfg_now.get(k) or "").strip()]
                if missing_now:
                    st.error(f"❌ Save these fields first before authenticating: **{', '.join(missing_now)}**")
                else:
                    try:
                        flow = _start_device_code_flow(cfg_now)
                        st.session_state["bc_dc_flow"] = flow
                        st.rerun()
                    except Exception as ex:
                        st.error(f"❌ Failed to start authentication: {ex}")

    with auth_c2:
        if has_refresh:
            st.success("✅ Microsoft account authenticated — refresh token stored. All sends use this.")
        elif dc_flow:
            user_code = dc_flow.get("user_code", "")
            verify_url = dc_flow.get("verification_uri", "https://microsoft.com/devicelogin")
            st.info(f"Open {verify_url} and enter code: {user_code} — then sign in with MFA, then click the button below.")
            if st.button("✅ I've signed in — save my token", key="bc_dc_confirm"):
                try:
                    with st.spinner("Checking authentication…"):
                        token_resp = _poll_device_code(
                            _load_azure_cfg(),
                            dc_flow["device_code"],
                            interval=dc_flow.get("interval", 5),
                        )
                    if token_resp.get("refresh_token"):
                        _save_refresh_token(token_resp["refresh_token"])
                        st.session_state.pop("bc_dc_flow", None)
                        st.success("✅ Authenticated! Refresh token saved — future sends are automatic.")
                        st.rerun()
                    else:
                        st.error("No refresh token returned. Ensure 'offline_access' scope is allowed.")
                except Exception as ex:
                    st.error(f"❌ Authentication failed: {ex}")

    # ── Test connection ───────────────────────────────────────────────────────
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    test_col, _ = st.columns([1, 4])
    with test_col:
        if st.button("🔗 Test Azure Connection", key="bc_az_test"):
            test_cfg = _load_azure_cfg()
            missing = [k for k in ("tenant_id","client_id","client_secret")
                       if not test_cfg.get(k,"").strip()]
            if missing:
                st.error(f"Save credentials first. Missing: {', '.join(missing)}")
            else:
                has_rt    = bool(test_cfg.get("refresh_token","").strip())
                has_ropc  = bool(test_cfg.get("username","").strip()
                                 and test_cfg.get("password","").strip())
                flow_label = ("Device Code / Refresh Token" if has_rt
                              else "ROPC (delegated)" if has_ropc
                              else "client_credentials")
                try:
                    with st.spinner(f"Testing via {flow_label}…"):
                        token = _get_token(test_cfg)
                    st.success(f"✅ Connected! Token obtained via **{flow_label}**.")
                except Exception as ex:
                    st.error(f"❌ Connection failed: {ex}")
                    if "AADSTS50076" in str(ex) or "AADSTS50079" in str(ex):
                        st.info(
                            "💡 MFA is required on this account. "
                            "Use **Authenticate with Microsoft** above — "
                            "it handles MFA and stores a refresh token for silent future use."
                        )

    st.markdown("---")

    # Per-partner Teams Chat ID
    st.markdown(
        "<div style='color:#90caf9;font-size:13px;margin-bottom:6px;'>"
        "<b>Per-Partner Teams Chat ID</b> — the Group Chat ID where each "
        "partner's Teams messages will be sent. "
        "Format: <code>19:xxxxxxxxxxxxx@thread.v2</code> "
        "(see guide below on how to find it)."
        "</div>",
        unsafe_allow_html=True,
    )

    con = _conn()
    try:
        partners = [r[0] for r in con.execute(
            "SELECT DISTINCT partner_name FROM bc_report ORDER BY partner_name"
        ).fetchall()]
    except Exception:
        partners = []
    con.close()

    if not partners:
        st.info("📭 Import a BC Report first — partner names will appear here.")
        return

    existing = _load_teams_cfg()

    b1, b2, b3 = st.columns([1, 2, 0.4])
    with b1:
        sel = st.selectbox("Partner Name", partners, key="bc_cfg_partner")
    with b2:
        chat_in = st.text_input(
            "Teams Chat ID",
            value=existing.get(sel, ""),
            key="bc_cfg_chat_id",
            placeholder="19:AbCdEfGhIjKl@thread.v2",
            help="Open teams.microsoft.com → click the group chat → copy from URL bar",
        )
    with b3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💾 Save & Send Welcome", key="bc_cfg_save"):
            if chat_in.strip():
                _save_teams_cfg(sel, chat_in.strip())
                # Auto-send welcome message
                az_cfg = _load_azure_cfg()
                if all([az_cfg.get("tenant_id"), az_cfg.get("client_id"),
                        az_cfg.get("client_secret"), az_cfg.get("username"),
                        az_cfg.get("password")]):
                    try:
                        token = _get_token(az_cfg)
                        _send_graph_message(token, chat_in.strip(), _build_welcome_msg())
                        st.success(
                            f"✅ Chat ID saved for **{sel}** and welcome message sent to Teams."
                        )
                        _log_action(sel, "", "Welcome Message Sent")
                    except Exception as ex:
                        st.success(f"✅ Chat ID saved for **{sel}**.")
                        st.warning(f"Welcome message could not be sent: {ex}")
                else:
                    st.success(
                        f"✅ Chat ID saved for **{sel}**. "
                        "(Fill in Azure credentials above to enable auto-welcome message.)"
                    )
            else:
                st.error("Chat ID cannot be empty.")

    # Status table
    if existing:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        rows = []
        for p in partners:
            cid_val = existing.get(p, "")
            rows.append({
                "Partner":  p,
                "Status":   "✅ Configured" if cid_val else "❌ Not set",
                "Chat ID":  cid_val,
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════
# UI — AZURE SETUP GUIDE
# ═══════════════════════════════════════════════════════════════════════════

def _render_azure_guide():
    st.markdown("""
### Azure App Registration — Step-by-Step Guide
*(Use admin@peakmyads.com — your work/school Microsoft account)*

---

#### Step 1 — Register an Application
1. Go to **[portal.azure.com](https://portal.azure.com)** → sign in with `admin@peakmyads.com`
2. Search **"App registrations"** → click **New registration**
3. Name: `PEAKADS BC Report`
4. Supported account type: **Single tenant**
5. Redirect URI: leave blank → click **Register**
6. Copy **Application (client) ID** and **Directory (tenant) ID** — paste above

---

#### Step 2 — Create a Client Secret
1. In your app → **Certificates & secrets** → **New client secret**
2. Description: `bc-report`, Expiry: **24 months**
3. Click **Add** → **immediately copy the Value** (hidden after leaving this page)
4. Paste as **Client Secret** above → Save

---

#### Step 3 — Grant API Permissions  ⚠️ IMPORTANT — use Delegated, not Application
1. In your app → **API permissions** → **Add a permission** → **Microsoft Graph**
2. Choose **Delegated permissions** *(not Application — Application gives 403 on chat messages)*
3. Search and add: **`Chat.ReadWrite`**
4. Also add: **`User.Read`**
5. Click **Grant admin consent for peakmyads** → Confirm

> **Why Delegated?** Microsoft does not allow Application permissions to send messages
> to existing group chats unless the app is installed as a bot (very complex).
> Delegated permissions send *on behalf of the user* (finance@peakmyads.onmicrosoft.com)
> which works immediately since that user is already in the chats.

#### Step 3b — Allow Public Client / ROPC Flow
1. In your app → **Authentication** tab
2. Scroll to **Advanced settings**
3. Set **Allow public client flows** → **Yes**
4. Click **Save**

> This allows the app to get tokens using username + password (ROPC flow),
> which is how the BC Report sends messages without requiring a browser login.

---

#### Step 4 — Find the Teams Chat ID
**Method A — Teams web app (easiest)**
1. Open **[teams.microsoft.com](https://teams.microsoft.com)** in Chrome/Edge
2. Sign in with `admin@peakmyads.com`
3. Click on the partner group chat
4. Copy the Chat ID from the URL bar:
   ```
   https://teams.microsoft.com/l/chat/19:AbCd1234@thread.v2/0?...
                                        ↑ copy this part ↑
   ```

**Method B — Graph Explorer**
1. Go to **[developer.microsoft.com/graph/graph-explorer](https://developer.microsoft.com/en-us/graph/graph-explorer)**
2. Sign in with `admin@peakmyads.com` (work account — top right)
3. Consent to `Chat.Read` in Modify Permissions tab
4. Run: `GET https://graph.microsoft.com/v1.0/me/chats?$expand=members`
5. Find your partner's chat by topic name → copy the `id` field

---

#### Step 5 — Test the Connection
1. Fill in Tenant ID, Client ID, Client Secret above → Save
2. Click **🔗 Test Azure Connection** — should show "Token obtained"
3. Add a Chat ID for one partner → click **📤 Send Teams** on any row
4. Check the partner's Teams group chat for the message

---

#### Troubleshooting

| Error | Likely cause |
|---|---|
| `401 Unauthorized` | Wrong Client ID or Secret, or secret expired |
| `403 Forbidden` | Admin consent not granted for Chat.ReadWrite.All |
| `404 Not Found` | Chat ID is wrong |
| Token endpoint failed | Wrong Tenant ID |
| `Chat.ReadWrite.All not visible` | Search exactly as shown — case sensitive |
    """)


# ═══════════════════════════════════════════════════════════════════════════
# UI — UPLOAD
# ═══════════════════════════════════════════════════════════════════════════

def _render_upload():
    st.markdown(
        "<div style='color:#90caf9;font-size:13px;margin-bottom:8px;'>"
        "Upload <b>.xlsx</b> with columns: "
        "<b>Month | Partner Name | DSP $ (BC) | SSP $ (BC)</b>. "
        "Net $ (BC) is auto-calculated. "
        "Re-importing the same Month + Partner refreshes BC amounts only — "
        "C DSP $, C SSP $ and Status are preserved."
        "</div>",
        unsafe_allow_html=True,
    )
    uploaded = st.file_uploader(
        "Choose BC Report Excel file", type=["xlsx"], key="bc_uploader"
    )
    if not uploaded:
        return

    try:
        raw = pd.read_excel(uploaded)
        raw.columns = raw.columns.str.strip()

        col_map = {}
        for c in raw.columns:
            cl = (c.lower().replace(" ", "").replace("$", "")
                    .replace("(bc)", "").replace("_", ""))
            if   "month"   in cl:      col_map[c] = "Month"
            elif "partner" in cl:      col_map[c] = "Partner Name"
            elif cl.startswith("dsp"): col_map[c] = "DSP $ (BC)"
            elif cl.startswith("ssp"): col_map[c] = "SSP $ (BC)"
        raw.rename(columns=col_map, inplace=True)

        missing = [c for c in ["Month", "Partner Name",
                                "DSP $ (BC)", "SSP $ (BC)"]
                   if c not in raw.columns]
        if missing:
            st.error(f"Missing columns: {missing}")
            return

        raw["Month"]      = (pd.to_datetime(raw["Month"], errors="coerce")
                               .dt.strftime("%b-%Y"))
        raw["DSP $ (BC)"] = pd.to_numeric(raw["DSP $ (BC)"], errors="coerce").fillna(0)
        raw["SSP $ (BC)"] = pd.to_numeric(raw["SSP $ (BC)"], errors="coerce").fillna(0)
        raw["Net $ (BC)"] = raw["DSP $ (BC)"] - raw["SSP $ (BC)"]
        raw = raw.dropna(subset=["Month", "Partner Name"]).reset_index(drop=True)

        st.dataframe(
            raw[["Month", "Partner Name",
                 "DSP $ (BC)", "SSP $ (BC)", "Net $ (BC)"]],
            use_container_width=True, hide_index=True,
        )
        st.caption(f"{len(raw)} row(s) ready to import")

        if st.button("⬆ Import to BC Report", key="bc_import_btn"):
            _upsert_bc_report(raw)
            st.cache_data.clear()
            st.success(f"✅ {len(raw)} row(s) imported.")
            st.rerun()
    except Exception as ex:
        st.error(f"Import failed: {ex}")


# ═══════════════════════════════════════════════════════════════════════════
# UI — FILTERS
# ═══════════════════════════════════════════════════════════════════════════

def _render_filters(df: pd.DataFrame) -> pd.DataFrame:
    fy_list = _gen_fy_list()

    month_opts = ["All"]
    if not df.empty:
        try:
            tmp = pd.to_datetime(df["Month"], format="%b-%Y", errors="coerce").dropna()
            month_opts += sorted(
                tmp.dt.strftime("%b-%Y").unique().tolist(),
                key=lambda x: pd.to_datetime(x, format="%b-%Y"),
            )
        except Exception:
            pass

    partner_opts = ["All"] + (
        sorted(df["Partner Name"].dropna().unique().tolist())
        if not df.empty else []
    )

    f1, f2, f3, f4 = st.columns([0.3, 0.3, 0.5, 0.5])
    with f1:
        sel_fy = st.selectbox("Financial Year", ["All"] + fy_list, key="bc_fy")
    with f2:
        sel_month = st.selectbox("Month", month_opts, key="bc_month")
    with f3:
        sel_partner = st.selectbox("Partner Name", partner_opts, key="bc_partner")
    with f4:
        search_q = st.text_input(
            "🔍 Search", placeholder="Global search…", key="bc_search"
        )

    if df.empty:
        return df

    fdf = df.copy()
    fdf["_dt"] = pd.to_datetime(fdf["Month"], format="%b-%Y", errors="coerce")

    if sel_fy != "All":
        s, e = _fy_range(sel_fy)
        fdf = fdf[(fdf["_dt"] >= s) & (fdf["_dt"] <= e)]
    if sel_month != "All":
        fdf = fdf[fdf["Month"] == sel_month]
    if sel_partner != "All":
        fdf = fdf[fdf["Partner Name"] == sel_partner]
    if search_q:
        mask = fdf.apply(
            lambda r: r.astype(str).str.contains(search_q, case=False).any(),
            axis=1,
        )
        fdf = fdf[mask]

    fdf.drop(columns=["_dt"], inplace=True, errors="ignore")
    return fdf.reset_index(drop=True)


# ═══════════════════════════════════════════════════════════════════════════
# UI — TABLE + ACTIONS
# ═══════════════════════════════════════════════════════════════════════════

def _render_table_and_actions(df: pd.DataFrame):
    azure_cfg = _load_azure_cfg()
    teams_cfg = _load_teams_cfg()

    df_grid = df.copy()
    df_grid["Send Teams"] = ""
    for col in df_grid.select_dtypes(include="number").columns:
        df_grid[col] = df_grid[col].apply(
            lambda x: float(x) if pd.notna(x) else None
        )
    df_grid = df_grid.where(pd.notna(df_grid), None)

    pinned = [{
        "Partner Name": "Grand Total",
        "DSP $ (BC)":   float(df["DSP $ (BC)"].sum()),
        "SSP $ (BC)":   float(df["SSP $ (BC)"].sum()),
        "Net $ (BC)":   float(df["Net $ (BC)"].sum()),
        "C DSP $":      float(df["C DSP $"].sum()),
        "C SSP $":      float(df["C SSP $"].sum()),
        "C Net $":      float(df["C Net $"].sum()),
    }]

    opts = _build_grid_opts(df_grid)
    opts["pinnedBottomRowData"] = pinned

    grid_resp = AgGrid(
        df_grid,
        gridOptions=opts,
        height=480,
        update_mode=GridUpdateMode.SELECTION_CHANGED | GridUpdateMode.VALUE_CHANGED,
        data_return_mode=DataReturnMode.AS_INPUT,
        allow_unsafe_jscode=True,
        custom_css=_GRID_CSS,
        fit_columns_on_grid_load=True,
        enable_enterprise_modules=False,
        key=f"bc_aggrid_{st.session_state.get('bc_grid_key', 0)}",
    )

    # Normalise selected rows
    _raw = grid_resp.get("selected_rows")
    if _raw is None:
        selected = []
    elif isinstance(_raw, pd.DataFrame):
        selected = _raw.to_dict("records") if not _raw.empty else []
    else:
        selected = list(_raw)

    edited_df = (
        pd.DataFrame(grid_resp["data"])
        if grid_resp.get("data") is not None
        else df.copy()
    )

    # ── Action bar ──────────────────────────────────────────────────────
    st.markdown("""
    <style>
    /* BC Report action buttons — uniform style matching app theme */
    div[data-testid="stHorizontalBlock"] button[kind="secondary"] {
        border: 1.5px solid #0076CE !important;
        color: #ffffff !important;
        background: #cc0000 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: background 0.18s, color 0.18s;
    }
    div[data-testid="stHorizontalBlock"] button[kind="secondary"]:hover {
        background: #0076CE !important;
        color: #fff !important;
    }
    div[data-testid="stHorizontalBlock"] button[kind="secondary"]:disabled {
        border-color: #ccc !important;
        color: #aaa !important;
        background: transparent !important;
    }
    </style>
    <div style="background:rgba(0,51,102,0.06);border:1px solid rgba(0,51,102,0.12);
        border-radius:8px;padding:8px 16px;margin:10px 0 4px 0;
        display:flex;align-items:center;gap:8px;">
        <span style="font-size:12px;font-weight:700;color:#003366;
            letter-spacing:0.5px;text-transform:uppercase;">Actions</span>
        <span style="font-size:11px;color:#666;margin-left:4px;">
            — select row(s) via checkbox, then click an action</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()

    n = len(selected)
    if n == 0:
        send_label = "📤 Send Teams"
    elif n == 1:
        send_label = f"📤 Send Teams → {selected[0].get('Partner Name', '')}"
    else:
        send_label = f"📤 Send Teams ({n} partners)"

    b1, b2, b3, b4, _ = st.columns([1.8, 1.6, 0.9, 1.2, 1.2])
    with b1:
        send_clicked = st.button(
            send_label, disabled=(n < 1), key="bc_send_btn",
            type="secondary",
            help="Select one or more rows via checkbox, then click to send numbers to all selected partners",
        )
    with b2:
        numconf_clicked = st.button(
            "📬 Number Confirmation", disabled=(n < 1), key="bc_numconf_btn",
            type="secondary",
            help="Sends generic deadline reminder to all selected partners",
        )
    with b3:
        confirm_clicked = st.button(
            "✅ Confirm", disabled=(n < 1), key="bc_confirm_btn",
            type="secondary",
            help="Mark selected rows Confirmed (row turns green)",
        )
    with b4:
        save_clicked = st.button(
            "💾 Save C Edits", key="bc_save_btn",
            type="secondary",
            help="Save C DSP $ / C SSP $ edits to database",
        )

    # ── Send Teams (multi-row) ───────────────────────────────────────────
    if send_clicked and selected:
        if _require_azure(azure_cfg):
            token = None
            try:
                token = _get_token(azure_cfg)
            except Exception as ex:
                st.error(f"❌ Azure token error: {ex}")

            if token:
                ok_rows, errs = [], []
                for row in selected:
                    partner = str(row.get("Partner Name") or row.get("partner_name") or "").strip()
                    month   = str(row.get("Month") or row.get("month") or "").strip()
                    if not partner or partner.lower() == "none":
                        continue
                    chat_id = teams_cfg.get(partner, "")
                    if not chat_id:
                        errs.append(f"**{partner}** — No Chat ID configured")
                        continue
                    try:
                        html = _build_send_teams_msg(row)
                        _send_graph_message(token, chat_id, html)
                        _set_status(month, partner, "Sent")
                        _log_action(partner, month, "Send Teams")
                        ok_rows.append(partner)
                    except Exception as ex:
                        _log_action(partner, month, "Send Teams", f"Failed: {ex}")
                        errs.append(f"**{partner}** — {ex}")

                if ok_rows:
                    st.session_state["bc_log_open"] = True
                    st.session_state["bc_grid_key"] = st.session_state.get("bc_grid_key", 0) + 1
                    st.cache_data.clear()
                    st.success(
                        f"✅ Teams message sent to {len(ok_rows)} partner(s): "
                        + ", ".join(ok_rows)
                    )
                    st.rerun()
                for e in errs:
                    st.warning(e)

    # ── Number Confirmation (multi-row) ──────────────────────────────────
    if numconf_clicked and selected:
        if _require_azure(azure_cfg):
            token = None
            try:
                token = _get_token(azure_cfg)
            except Exception as ex:
                st.error(f"❌ Azure token error: {ex}")

            if token:
                ok, errs = 0, []
                for row in selected:
                    partner = str(row.get("Partner Name") or row.get("partner_name") or "").strip()
                    month   = str(row.get("Month") or row.get("month") or "").strip()
                    if not partner or partner.lower() == "none":
                        continue
                    chat_id = teams_cfg.get(partner, "")
                    if not chat_id:
                        errs.append(f"**{partner}** — No Chat ID configured")
                        continue
                    try:
                        html = _build_number_msg(month)
                        _send_graph_message(token, chat_id, html)
                        _log_action(partner, month, "Number Confirmation")
                        ok += 1
                    except Exception as ex:
                        _log_action(partner, month, "Number Confirmation", f"Failed: {ex}")
                        errs.append(f"**{partner}** — {ex}")
                if ok:
                    st.session_state["bc_log_open"] = True
                    st.success(
                        f"✅ Number Confirmation sent to {ok} partner(s)."
                    )
                    st.cache_data.clear()
                    st.rerun()
                for e in errs:
                    st.warning(e)

    # ── Confirm ──────────────────────────────────────────────────────────
    if confirm_clicked and selected:
        updated, skipped = 0, []
        for row in selected:
            month   = (row.get("Month")        or row.get("month")        or "")
            partner = (row.get("Partner Name") or row.get("partner_name") or "")
            month   = str(month).strip()
            partner = str(partner).strip()
            if not month or month.lower() == "none":
                skipped.append(partner or "?")
                continue
            if not partner or partner.lower() == "none":
                skipped.append(month or "?")
                continue
            try:
                _set_status(month, partner, "Confirmed")
                updated += 1
            except Exception as ex:
                skipped.append(f"{partner} — DB error: {ex}")
        if updated:
            # Bump grid key so AgGrid fully re-renders with fresh DB data
            st.session_state["bc_grid_key"] = st.session_state.get("bc_grid_key", 0) + 1
            st.success(f"✅ {updated} row(s) marked **Confirmed** (rows turn green).")
            st.rerun()
        if skipped:
            st.warning("Could not update: " + ", ".join(skipped))

    # ── Save C Edits ─────────────────────────────────────────────────────
    if save_clicked and not edited_df.empty:
        try:
            save_df = edited_df[
                [c for c in ["Month", "Partner Name", "C DSP $", "C SSP $"]
                 if c in edited_df.columns]
            ].copy()
            save_df["C DSP $"] = pd.to_numeric(
                save_df["C DSP $"], errors="coerce"
            ).fillna(0)
            save_df["C SSP $"] = pd.to_numeric(
                save_df["C SSP $"], errors="coerce"
            ).fillna(0)
            _save_c_edits(save_df)
            st.cache_data.clear()
            st.success("💾 C DSP $ / C SSP $ edits saved.")
            st.rerun()
        except Exception as ex:
            st.error(f"Save failed: {ex}")

    # ── Push to Master Data ──────────────────────────────────────────────
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    def _check_duplicates(rows):
        """Return list of (month, partner) tuples that already exist in master_data."""
        con = _conn()
        dups = []
        for row in rows:
            m = str(row.get("Month","") or "").strip()
            p = str(row.get("Partner Name","") or "").strip()
            if not m or not p: continue
            try:
                cnt = con.execute(
                    'SELECT COUNT(*) FROM master_data WHERE "Month"=? AND "Partner Name"=?',
                    (m, p)
                ).fetchone()[0]
                if cnt > 0: dups.append((m, p))
            except Exception: pass
        con.close()
        return dups

    def _do_push(rows, skip_existing=False):
        """Execute push, return (inserted, updated)."""
        filtered = rows
        if skip_existing:
            dups = {(str(r.get("Month","")).strip(), str(r.get("Partner Name","")).strip())
                    for r in rows}
            con2 = _conn()
            existing = set()
            for m, p in dups:
                try:
                    if con2.execute(
                        'SELECT COUNT(*) FROM master_data WHERE "Month"=? AND "Partner Name"=?',
                        (m, p)
                    ).fetchone()[0] > 0:
                        existing.add((m, p))
                except Exception: pass
            con2.close()
            filtered = [r for r in rows
                        if (str(r.get("Month","")).strip(),
                            str(r.get("Partner Name","")).strip()) not in existing]
        return _push_to_master(filtered)

    push_col, _ = st.columns([1.5, 4])
    with push_col:
        push_clicked = st.button(
            "⬆ Push to Master Data", disabled=(n < 1), key="bc_push_btn",
            type="secondary",
            help="Upserts selected rows into the Master Data table",
        )

    if push_clicked and selected:
        dups = _check_duplicates(selected)
        if dups:
            # Has duplicates — ask user what to do
            st.session_state["bc_push_pending"] = selected
            st.session_state["bc_push_dups"] = dups
            st.rerun()
        else:
            # No duplicates — push directly without asking
            try:
                _ins, _upd = _push_to_master(selected)
                for _k in ["master_df","dsp_df","ssp_df",
                           "dsp_edit_df","ssp_edit_df","data_initialized"]:
                    if _k in st.session_state:
                        del st.session_state[_k]
                st.cache_data.clear()
                _msg = []
                if _ins: _msg.append(f"{_ins} new row(s) inserted")
                if _upd: _msg.append(f"{_upd} existing row(s) updated")
                if not _msg: _msg = ["no changes — already up to date"]
                st.success("✅ Push complete: " + ", ".join(_msg) +
                           ". Master Data, DSP and SSP tabs will reload automatically.")
                st.rerun()
            except Exception as ex:
                st.error(f"Push failed: {ex}")

    # Duplicate confirmation dialog
    if st.session_state.get("bc_push_pending") and st.session_state.get("bc_push_dups"):
        _dups = st.session_state["bc_push_dups"]
        _pending = st.session_state["bc_push_pending"]
        _dup_lines = "\n".join([f"- {m} | {p}" for m, p in _dups])
        st.warning(
            f"⚠️ **{len(_dups)} row(s) already exist** in Master Data:\n\n"
            + _dup_lines
            + "\n\nHow would you like to proceed?"
        )
        _wa, _wb, _wc = st.columns([1, 1, 1])
        with _wa:
            if st.button("♻️ Replace Existing", key="bc_push_replace"):
                try:
                    _ins, _upd = _do_push(_pending, skip_existing=False)
                    for _k in ["master_df","dsp_df","ssp_df","dsp_edit_df","ssp_edit_df","data_initialized"]:
                        if _k in st.session_state: del st.session_state[_k]
                    st.session_state.pop("bc_push_pending", None)
                    st.session_state.pop("bc_push_dups", None)
                    st.cache_data.clear()
                    st.success(f"✅ Push complete: {_ins} inserted, {_upd} updated.")
                    st.rerun()
                except Exception as ex:
                    st.error(f"Push failed: {ex}")
        with _wb:
            if st.button("⏭ Skip Existing", key="bc_push_skip"):
                try:
                    _ins, _upd = _do_push(_pending, skip_existing=True)
                    for _k in ["master_df","dsp_df","ssp_df","dsp_edit_df","ssp_edit_df","data_initialized"]:
                        if _k in st.session_state: del st.session_state[_k]
                    st.session_state.pop("bc_push_pending", None)
                    st.session_state.pop("bc_push_dups", None)
                    st.cache_data.clear()
                    st.success(f"✅ Push complete: {_ins} new row(s) inserted. Existing rows skipped.")
                    st.rerun()
                except Exception as ex:
                    st.error(f"Push failed: {ex}")
        with _wc:
            if st.button("✖ Cancel", key="bc_push_cancel"):
                st.session_state.pop("bc_push_pending", None)
                st.session_state.pop("bc_push_dups", None)
                st.rerun()
    
    st.divider()

    # ── Activity Log ─────────────────────────────────────────────────────
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    with st.expander("📋 Activity Log — Teams Messages Sent", expanded=False):
        # Always reload from DB fresh (no caching)
        log_df = _load_activity_log(limit=100)

        _lc1, _lc2, _lc3, _lc4 = st.columns([1, 1, 0.6, 2.4])
        with _lc1:
            _filter_partner = st.selectbox(
                "Filter by Partner",
                ["All"] + sorted(log_df["Partner"].dropna().unique().tolist())
                if not log_df.empty else ["All"],
                key="bc_log_partner_filter",
            )
        with _lc2:
            _filter_action = st.selectbox(
                "Filter by Action",
                ["All"] + sorted(log_df["Action"].dropna().unique().tolist())
                if not log_df.empty else ["All"],
                key="bc_log_action_filter",
            )
        with _lc3:
            if st.button("🔄 Refresh", key="bc_log_refresh", help="Refresh log"):
                st.rerun()
        with _lc4:
            st.markdown(
                "<div style='font-size:11px;color:#888;padding-top:8px;'>"
                "🔵 Number Confirmation &nbsp;|&nbsp; 🟢 Send Teams "
                "&nbsp;|&nbsp; 🟡 Welcome &nbsp;|&nbsp; 🔴 Failed"
                "</div>",
                unsafe_allow_html=True,
            )

        if log_df.empty:
            st.info("No messages sent yet — log will appear here after first send.")
        else:
            disp_df = log_df.copy()
            if _filter_partner != "All":
                disp_df = disp_df[disp_df["Partner"] == _filter_partner]
            if _filter_action != "All":
                disp_df = disp_df[disp_df["Action"] == _filter_action]

            def _log_style(row):
                action = str(row.get("Action",""))
                status = str(row.get("Status",""))
                if "Failed" in status:
                    return ["background-color:#ffe8e8;color:#721c24"] * len(row)
                if "Number Confirmation" in action:
                    return ["background-color:#e8f4ff;color:#004085"] * len(row)
                if "Send Teams" in action:
                    return ["background-color:#e8fff0;color:#155724"] * len(row)
                if "Welcome" in action:
                    return ["background-color:#fff8e8;color:#856404"] * len(row)
                return [""] * len(row)

            st.dataframe(
                disp_df.style.apply(_log_style, axis=1),
                use_container_width=True,
                hide_index=True,
                height=min(400, 38 + len(disp_df) * 35),
            )
            st.caption(f"Total: {len(log_df)} entries | Showing: {len(disp_df)}")

    return selected, edited_df
    

# ═══════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

def render_bc_report_tab():
    init_bc_report_tables()

    st.markdown("""
    <div style="background:linear-gradient(135deg,#003366 0%,#005599 100%);
        border-radius:10px;padding:18px 24px;margin-bottom:20px;
        box-shadow:0 4px 16px rgba(0,51,102,.2);
        display:flex;align-items:center;height:55px;gap:14px;">
        <div style="font-size:32px;">📋</div>
        <div>
            <div style="color:white;font-size:20px;font-weight:800;">
                BC Report — Balance Confirmation
            </div>
            <div style="color:#90caf9;font-size:12px;margin-top:2px;">
                Sends via Microsoft Graph API → Teams Group Chat
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander("⚙️ Azure / Teams Configuration", expanded=False):
        _render_azure_config()

    with st.expander("📂 Import BC Report (.xlsx)", expanded=False):
        _render_upload()

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    df_all = _load_bc_report()

    if df_all.empty:
        st.info(
            "📭 No data yet. Use **📂 Import BC Report** above to get started."
        )
        with st.expander("📖 Azure App Registration — Step-by-Step Guide",
                         expanded=True):
            _render_azure_guide()
        return

    df_filtered = _render_filters(df_all)

    st.divider()

    if df_filtered.empty:
        st.warning("No rows match the selected filters.")
    else:
        _render_table_and_actions(df_filtered)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    with st.expander("📖 Azure App Registration — Step-by-Step Guide",
                     expanded=False):
        _render_azure_guide()
