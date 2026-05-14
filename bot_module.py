"""
bot_module.py  —  PEAKADS LLP
AI Assistant powered by Groq (FREE tier — Llama 3.3 70B).

LAYOUT
──────
• A dedicated "🤖 Assistant" tab renders the full chat interface.
• A floating 🤖 button (bottom-right, always visible) navigates to that tab
  by clicking the hidden Streamlit tab button — same technique as invoice_subnav.py.

INTEGRATION  (3 steps)
──────────────────────

STEP 1 — app.py: add the tab and FAB

    # Inside the tab rendering section, add:
    with tabs["🤖 Assistant"]:
        render_bot_tab()

    # At the very bottom of app.py (after all tabs):
    render_bot_fab()

    # Import at top of app.py:
    from bot_module import render_bot_tab, render_bot_fab

STEP 2 — login.py: add tab to every role's allowed list
    "🤖 Assistant" to Admin, Finance, and Viewer tab lists

STEP 3 — navbar.py TAB_MAP: add entry
    "🤖 Assistant": ("🤖", "Assistant"),

REQUIREMENTS
────────────
  pip install groq

  API key (FREE — get from https://console.groq.com → API Keys):
  a) GROQ_API_KEY = "gsk_..."   (.streamlit/secrets.toml)
  b) set GROQ_API_KEY=gsk_...   (environment variable)
  c) Enter inside the bot Settings panel in-app (session only)
"""

import os
import streamlit as st
import streamlit.components.v1 as components


_SYSTEM = """You are PeakBot, the built-in AI assistant for PEAKADS LLP Revenue Intelligence Platform.
You are friendly, concise, and expert in every feature of this software.
Use bullet points for step-by-step answers. Keep responses focused and practical.
Never invent features that do not exist. If unsure, say so honestly.

SOFTWARE OVERVIEW
PEAKADS LLP Revenue Intelligence Platform manages finances for a digital advertising
company. It tracks DSP (Demand-Side Platform = Customers / Receivables) and SSP
(Supply-Side Platform = Vendors / Payables), invoicing, ageing, and partner relations.

User Roles:
Admin   - full access to all tabs including Admin Control Panel and Edit Database
Finance - all tabs except Admin Control Panel and Edit Database
Viewer  - read-only: Dashboard, AR/AP Ageing, Master Data only

TABS AND FEATURES

1. DASHBOARD
   KPI cards: Total Revenue, DSP Revenue, SSP Revenue, Net Revenue, Margins
   Monthly/yearly revenue charts, partner-wise breakdown tables
   Filters: Financial Year (Apr-Mar Indian FY), Month, Partner
   Right-side hover sub-nav for quick section jumping within the tab

2. AR/AP AGEING
   Accounts Receivable (DSP) and Accounts Payable (SSP) ageing buckets
   Buckets: Current, 30 days, 60 days, 90 days, 90+ days overdue
   Due dates calculated from NET Terms set per partner
   Export to Excel

3. MASTER DATA
   Central revenue table: Month | Partner Name | DSP $ | SSP $ | C DSP $ | C SSP $
   Add rows, edit inline, delete, or import from Excel (.xlsx)
   Source data for Dashboard, DSP, SSP, and Ageing tabs

4. DSP (CUSTOMERS)
   Customer revenue and payment tracking
   Invoice status: Pending, Sent, Paid
   NET Terms: Net 30 / 45 / 60 / 90 - due dates auto-calculated
   Currency: USD or INR based on partner country
   Edit payment amounts inline, send reminders

5. INVOICE MANAGER  (5 sub-tabs via right-side sub-nav)
   Create Invoice  - generate professional invoices for DSP/SSP partners
   Invoice History - view all past invoices with status tracking
   Send Reminder   - send reminders to overdue partners
   DSP Statement   - monthly DSP revenue statement
   GST Report      - GST-compliant report for Indian partners

6. SSP (VENDORS)
   Vendor payable tracking (amounts we owe to vendors)
   Same structure as DSP but for payables

7. LIST OF PARTNERS
   Master partner directory: Name, Short Name, Country, Currency, Payment Terms
   Partners feed all dropdowns in DSP, SSP, Invoice, and BC Report tabs
   Short Name must match the name used in BC Report Excel imports

8. COSTS CENTRE
   Track operating costs by category and month
   Data feeds into P&L tab

9. P&L (PROFIT AND LOSS)
   Monthly and annual P&L: Revenue minus Costs
   Gross margin and net margin calculations

10. BC REPORT (BALANCE CONFIRMATION)
    Send balance confirmation messages to partners via Microsoft Teams group chats
    Import Excel with columns: Month, Partner Name, DSP $(BC), SSP $(BC)
    Edit confirmed amounts (C DSP $, C SSP $) inline in the grid
    Actions: Send Teams, Number Confirmation, Confirm, Push to Master Data
    Status lifecycle: Pending, Sent, Confirmed
    Azure/Teams Configuration requires: Tenant ID, Client ID, Client Secret
    Authentication: Device Code Flow - one-time MFA browser sign-in, then silent forever
    Activity log shows all messages sent with timestamps

11. ADMIN CONTROL PANEL  (Admin only)
    User management: add, edit, delete users, assign roles
    Password management for all users

12. EDIT DATABASE  (Admin only)
    Direct view and edit of underlying SQLite database tables
    Use with caution - changes are immediate and permanent

COMMON WORKFLOWS

HOW TO ADD MONTHLY REVENUE:
  1. Go to Master Data tab
  2. Click Add Row or click Import Excel to upload a spreadsheet
  3. Fill in Month (format: Jan-2025), Partner Name, DSP $, SSP $
  4. Save - Dashboard and all other tabs update automatically

HOW TO CREATE AN INVOICE:
  1. Go to Invoice Manager tab
  2. Click Create Invoice sub-tab (use right-side sub-nav if needed)
  3. Select partner, month, and invoice type (DSP or SSP)
  4. Fill in amounts and click Generate
  5. Download PDF or send directly from the app

HOW TO TRACK OVERDUE PAYMENTS:
  1. Go to AR/AP Ageing tab
  2. Red rows are overdue, orange rows are due soon
  3. Use the Financial Year or Partner filter to narrow down
  4. Click on a row to see invoice details

HOW TO SEND BC REPORT TO TEAMS:
  1. Go to BC Report tab
  2. Click Import BC Report and upload Excel file
  3. Edit C DSP $ and C SSP $ columns if confirmed amounts differ
  4. Select the rows you want to send
  5. Click Send Teams - message appears in the partner Teams group chat

HOW TO ADD A NEW PARTNER:
  1. Go to List of Partners tab
  2. Click Add Partner
  3. Fill Name, Short Name (used for BC import matching), Country, Payment Terms
  4. Save - partner appears in all dropdowns immediately

HOW TO SET UP AZURE FOR BC REPORT:
  1. Go to BC Report tab, open Azure / Teams Configuration
  2. Fill in Tenant ID, Client ID, Client Secret, then click Save All
  3. Click Authenticate with Microsoft
  4. Open the URL shown in your browser, enter the code displayed, sign in with MFA
  5. Return to the app and click I have signed in - save my token
  6. Done - all future sends work silently without any MFA prompts

KEY TERMS
DSP $    = revenue billed to customers (Accounts Receivable / AR)
SSP $    = revenue owed to vendors (Accounts Payable / AP)
C DSP $  = confirmed/actual DSP amount (may differ from billed)
C SSP $  = confirmed/actual SSP amount
Net $    = DSP minus SSP (gross profit per deal)
NET Term = payment terms, e.g. Net 30 means payment due 30 days after invoice
FY       = Financial Year, April to March (Indian FY convention)
BC       = Balance Confirmation, sent to verify outstanding amounts with partners
"""

_QUICK = [
    "How do I add monthly revenue data?",
    "How do I create an invoice?",
    "How do I send a BC Report via Teams?",
    "What is the difference between DSP and SSP?",
    "How do I track overdue payments?",
    "How do I add a new partner?",
    "What are the user roles and their permissions?",
    "How do I set up Azure for BC Report?",
]


def _get_key() -> str:
    try:
        return st.secrets["GROQ_API_KEY"]
    except Exception:
        pass
    k = os.environ.get("GROQ_API_KEY", "")
    if k:
        return k
    return st.session_state.get("_bot_api_key", "")


def _stream_reply(history: list, api_key: str) -> str:
    try:
        from groq import Groq
    except ImportError:
        st.error("groq package not installed. Run: pip install groq")
        return "Please install the groq package."
    try:
        client = Groq(api_key=api_key)

        messages = [{"role": "system", "content": _SYSTEM}]
        for m in history:
            messages.append({"role": m["role"], "content": m["content"]})

        full = ""
        box = st.empty()

        stream = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=1024,
            temperature=0.7,
            stream=True,
        )

        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            full += delta
            box.markdown(full + "▌")

        box.markdown(full)
        return full
    except Exception as e:
        msg = f"API error: {e}"
        st.error(msg)
        return msg


def render_bot_tab():
    """Render the full chat UI. Call inside with tabs['🤖 Assistant']: in app.py."""

    st.markdown("""
    <div style="background:linear-gradient(135deg,#003366 0%,#0076CE 100%);
        border-radius:12px;padding:18px 24px;margin-bottom:20px;
        box-shadow:0 4px 16px rgba(0,51,102,.2);
        display:flex;align-items:center;gap:14px;">
        <div style="font-size:36px;">🤖</div>
        <div>
            <div style="color:white;font-size:20px;font-weight:800;">
                PeakBot — AI Assistant
            </div>
            <div style="color:#90caf9;font-size:12px;margin-top:2px;">
                Ask me anything about how to use PEAKADS Revenue Intelligence Platform
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    key = _get_key()

    if not key:
        st.warning("⚠️ Groq API key not configured.")
        with st.expander("⚙️ How to set up the FREE Groq API key", expanded=True):
            st.markdown("""
**Get your FREE key** at 👉 [console.groq.com](https://console.groq.com)
*(Sign up free → API Keys → Create API Key → Copy it)*

**Option A — Streamlit secrets file** (`.streamlit/secrets.toml`):
```toml
GROQ_API_KEY = "gsk_..."
```
Restart Streamlit after saving.

**Option B — Environment variable**:
```
set GROQ_API_KEY=gsk_...
```

**Option C — Enter below** *(session only, cleared on restart)*:
""")
            c1, c2 = st.columns([4, 1])
            with c1:
                entered = st.text_input(
                    "API Key", type="password", key="bot_key_input",
                    placeholder="gsk_...", label_visibility="collapsed"
                )
            with c2:
                if st.button("Save", key="bot_key_btn", use_container_width=True):
                    if entered.strip().startswith("gsk_"):
                        st.session_state["_bot_api_key"] = entered.strip()
                        st.success("Saved for this session.")
                        st.rerun()
                    else:
                        st.error("Key must start with gsk_...")
        return

    if "bot_history" not in st.session_state:
        st.session_state.bot_history = []

    if not st.session_state.bot_history:
        st.markdown("""
        <div style="background:#f0f7ff;border-left:4px solid #0076CE;
             padding:14px 18px;border-radius:8px;margin-bottom:16px;font-size:14px;color:#003366;">
            👋 <b>Hi! I am PeakBot.</b> I know every feature of this software.
            Pick a quick question or type your own below.
        </div>
        """, unsafe_allow_html=True)
        st.markdown("**Quick questions — click to ask:**")
        cols = st.columns(2)
        for i, q in enumerate(_QUICK):
            with cols[i % 2]:
                if st.button(q, key=f"bot_q_{i}", use_container_width=True):
                    st.session_state.bot_history.append({"role": "user", "content": q})
                    st.rerun()
        st.markdown("---")

    for msg in st.session_state.bot_history:
        with st.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else "👤"):
            st.markdown(msg["content"])

    last = st.session_state.bot_history[-1] if st.session_state.bot_history else None
    if last and last["role"] == "user":
        with st.chat_message("assistant", avatar="🤖"):
            reply = _stream_reply(st.session_state.bot_history, key)
        st.session_state.bot_history.append({"role": "assistant", "content": reply})

    if prompt := st.chat_input("Ask PeakBot anything about the software…"):
        st.session_state.bot_history.append({"role": "user", "content": prompt})
        st.rerun()

    if st.session_state.bot_history:
        if st.button("🗑 Clear chat", key="bot_clear"):
            st.session_state.bot_history = []
            st.rerun()


def render_bot_fab():
    """
    Inject a fixed floating 🤖 button (bottom-right corner).
    Clicking it switches to the Assistant tab by programmatically clicking the
    hidden Streamlit stTab button — same pattern as invoice_subnav.py.
    Call once at the very bottom of app.py after all tabs are rendered.
    """
    st.markdown("""
    <style>
    #peakbot-fab {
        position       : fixed;
        bottom         : 28px;
        right          : 28px;
        z-index        : 99997;
        width          : 52px;
        height         : 52px;
        border-radius  : 50%;
        background     : linear-gradient(135deg, #0076CE 0%, #003a80 100%);
        color          : white;
        font-size      : 22px;
        border         : 2px solid rgba(255,255,255,0.25);
        cursor         : pointer;
        box-shadow     : 0 4px 18px rgba(0,118,206,0.55);
        display        : flex;
        align-items    : center;
        justify-content: center;
        transition     : transform 0.18s ease, box-shadow 0.18s ease;
    }
    #peakbot-fab:hover {
        transform  : scale(1.12);
        box-shadow : 0 6px 28px rgba(0,118,206,0.75);
    }
    #peakbot-fab-label {
        position      : fixed;
        bottom        : 88px;
        right         : 18px;
        z-index       : 99997;
        background    : #003366;
        color         : white;
        font-size     : 11px;
        font-weight   : 600;
        padding       : 5px 10px;
        border-radius : 8px;
        white-space   : nowrap;
        opacity       : 0;
        pointer-events: none;
        transition    : opacity 0.2s;
        font-family   : -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        box-shadow    : 0 2px 8px rgba(0,0,0,0.2);
    }
    #peakbot-fab:hover ~ #peakbot-fab-label { opacity: 1; }
    @media (max-width: 768px) {
        #peakbot-fab { bottom:16px; right:16px; width:44px; height:44px; font-size:18px; }
        #peakbot-fab-label { display: none; }
    }
    </style>
    <button id="peakbot-fab" title="Open PeakBot AI Assistant">🤖</button>
    <div id="peakbot-fab-label">PeakBot — AI Assistant</div>
    """, unsafe_allow_html=True)

    components.html("""<!DOCTYPE html><html><body style="margin:0;background:transparent;">
    <script>
    (function bindFab(){
        var P   = window.parent.document;
        var fab = P.getElementById('peakbot-fab');
        if (!fab || fab._pbBound) return;
        fab._pbBound = true;
        fab.addEventListener('click', function(){
            // Find the stTab button whose text contains "Assistant"
            var tabs = P.querySelectorAll('button[data-testid="stTab"]');
            for (var i = 0; i < tabs.length; i++){
                if ((tabs[i].textContent || '').trim().indexOf('Assistant') !== -1){
                    tabs[i].click();
                    return;
                }
            }
        });
    })();
    // Retry binding a few times in case DOM not ready
    var _t = [100, 500, 1500];
    _t.forEach(function(d){ setTimeout(bindFab, d); });
    </script>
    </body></html>""", height=0, scrolling=False)