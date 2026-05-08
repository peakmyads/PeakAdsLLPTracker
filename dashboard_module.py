"""
Dashboard Module
Author: Sumit
Description:
    Professional Executive Dashboard — Revenue, Costs, Profit,
    AR/AP Cash-Flow and Collection Efficiency for the Revenue Tracker app.
    Drop-in replacement: call render_dashboard_tab(master_df, dsp_df, ssp_df)
"""

import streamlit as st
import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────
# PLOTLY SAFE IMPORT
# ─────────────────────────────────────────────────────────────────────────────
try:
    import plotly.graph_objects as go
    import plotly.express as px
    _PLOTLY = True
except ImportError:
    _PLOTLY = False


# ═════════════════════════════════════════════════════════════════════════════
# INTERNAL HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def _fmt(v, prefix="$"):
    """Format number → $1,234.56"""
    try:
        return f"{prefix}{float(v):,.2f}"
    except Exception:
        return f"{prefix}0.00"


def _pct(v):
    try:
        return f"{float(v):.1f}%"
    except Exception:
        return "0.0%"


# ─────────────────────────────────────────────────────────────────────────────
# KPI CARD  (consistent with existing app style)
# ─────────────────────────────────────────────────────────────────────────────

def _kpi(title, value, subtitle="", icon="", gradient=None, is_pct=False):
    """Render one gradient KPI card."""
    _GRADIENTS = {
        "green":  "linear-gradient(135deg,#0f5132,#198754)",
        "red":    "linear-gradient(135deg,#842029,#dc3545)",
        "blue":   "linear-gradient(135deg,#003366,#0076CE)",
        "purple": "linear-gradient(135deg,#d765c5,#0d6efd)",
        "teal":   "linear-gradient(135deg,#0d6efd,#0dcaf0)",
        "amber":  "linear-gradient(135deg,#856404,#ffc107)",
        "slate":  "linear-gradient(135deg,#343a40,#6c757d)",
        "orange": "linear-gradient(135deg,#a0522d,#e65100)",
    }
    bg = _GRADIENTS.get(gradient or "slate", _GRADIENTS["slate"])

    try:
        num = float(value)
        display = _pct(num) if is_pct else _fmt(num)
    except Exception:
        display = str(value)

    sub_html = (
        f'<div style="font-size:11px;color:rgba(255,255,255,0.75);margin-top:4px;">{subtitle}</div>'
        if subtitle else ""
    )

    st.markdown(f"""
    <div style="
        background:{bg};
        padding:18px 20px;
        border-radius:14px;
        box-shadow:0 6px 20px rgba(0,0,0,0.22);
        margin-bottom:8px;
        min-height:95px;
    ">
        <div style="font-size:12px;font-weight:700;color:#FFEF00;
                    text-transform:uppercase;letter-spacing:.6px;">
            {icon}&nbsp;{title}
        </div>
        <div style="font-size:28px;font-weight:900;color:#fff;margin-top:6px;
                    letter-spacing:-0.5px;">
            {display}
        </div>
        {sub_html}
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION HEADER
# ─────────────────────────────────────────────────────────────────────────────

def _section(title, subtitle=""):
    sub_html = (
        f'<div style="color:#90caf9;font-size:12px;margin-top:3px;">{subtitle}</div>'
        if subtitle else ""
    )
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#003366 0%,#005599 100%);
        border-radius:10px;padding:14px 20px;margin:12px 0 16px;
        box-shadow:0 4px 14px rgba(0,51,102,.22);
        display:flex;align-items:center;gap:12px;">
        <div>
            <div style="color:white;font-size:17px;font-weight:800;">{title}</div>
            {sub_html}
        </div>
    </div>
    """, unsafe_allow_html=True)




# ─────────────────────────────────────────────────────────────────────────────
# ANCHOR MARKER  — invisible div that acts as a scroll target
# ─────────────────────────────────────────────────────────────────────────────

def _anchor(section_id: str):
    """Invisible scroll-target anchor placed just before each section."""
    st.markdown(
        f'<div id="{section_id}" style="position:relative;top:-70px;"></div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# SIDE NAV  (hover-reveal vertical strip on the right edge)
# ─────────────────────────────────────────────────────────────────────────────

_NAV_SECTIONS = [
    ("sec-overview",   "\U0001f4a1", "Overview"),
    ("sec-monthly",    "\U0001f4c5", "Monthly"),
    ("sec-cashflow",   "\U0001f4b0", "Cash Flow"),
    ("sec-partners",   "\U0001f91d", "Partners"),
    ("sec-onboarding", "\U0001f5d3", "Onboarding"),
    ("sec-summary",    "\U0001f50d", "Py Summary"),
    ("sec-table",      "\U0001f4cb", "Data Table"),
]


def _render_nav_bar():
    """
    Vertical side-nav fixed to the RIGHT edge of the viewport.

    Collapsed : an 8 px glowing blue strip with one small dot per section.
    Hovered   : smoothly slides left, revealing labelled pill buttons.
    Pure CSS  : no <script> — Streamlit strips those.
    """
    links_html = ""
    dots_html  = ""
    for sec_id, icon, label in _NAV_SECTIONS:
        links_html += (
            f'<a href="#{sec_id}" class="snav-btn">'
            f'<span class="snav-icon">{icon}</span>'
            f'<span class="snav-label">{label}</span>'
            f'</a>'
        )
        dots_html += f'<a href="#{sec_id}" class="snav-dot" title="{label}"></a>'

    st.markdown(f"""
    <style>
    html {{ scroll-behavior: smooth !important; }}

    #dash-sidenav {{
        position : fixed;
        right    : 0;
        top      : 50%;
        transform: translateY(-50%);
        z-index  : 99999;
        display  : flex;
        flex-direction: row;
        align-items   : center;
    }}

    .snav-handle {{
        width         : 10px;
        min-height    : 180px;
        background    : linear-gradient(180deg,
                            rgba(0,100,200,0)  0%,
                            #0076CE           40%,
                            #003a80           60%,
                            rgba(0,20,80,0)  100%);
        border-radius : 8px 0 0 8px;
        display       : flex;
        flex-direction: column;
        align-items   : center;
        justify-content: center;
        gap           : 9px;
        padding       : 14px 0;
        cursor        : pointer;
        flex-shrink   : 0;
        box-shadow    : -3px 0 16px rgba(0,118,206,0.55),
                         0   0  8px rgba(0,118,206,0.30);
        transition    : width 0.30s cubic-bezier(.4,0,.2,1),
                        opacity 0.25s ease,
                        border-radius 0.30s;
    }}

    .snav-dot {{
        width         : 5px;
        height        : 5px;
        border-radius : 50%;
        background    : rgba(255,255,255,0.55);
        flex-shrink   : 0;
        display       : block;
        transition    : background 0.2s, transform 0.2s;
        text-decoration: none !important;
    }}
    .snav-dot:hover {{
        background : #fff;
        transform  : scale(1.5);
    }}

    .snav-panel {{
        display        : flex;
        flex-direction : column;
        gap            : 7px;
        background     : linear-gradient(160deg, #010f2e 0%, #002a6e 100%);
        border-radius  : 14px 0 0 14px;
        max-width      : 0;
        overflow       : hidden;
        padding        : 0;
        box-shadow     : -8px 0 28px rgba(0,0,0,0.55),
                          0   0 0 1px rgba(0,118,206,0.25);
        transition     : max-width 0.32s cubic-bezier(.4,0,.2,1),
                         padding   0.30s cubic-bezier(.4,0,.2,1);
        white-space    : nowrap;
    }}

    #dash-sidenav:hover .snav-panel {{
        max-width : 185px;
        padding   : 14px 10px;
    }}
    #dash-sidenav:hover .snav-handle {{
        width   : 0;
        opacity : 0;
    }}

    .snav-title {{
        font-size     : 9px;
        font-weight   : 800;
        letter-spacing: 1.2px;
        color         : rgba(255,255,255,0.35);
        text-transform: uppercase;
        padding       : 0 4px 4px;
        border-bottom : 1px solid rgba(255,255,255,0.08);
        margin-bottom : 2px;
        user-select   : none;
        font-family   : -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}

    .snav-btn {{
        display        : flex;
        align-items    : center;
        gap            : 9px;
        padding        : 8px 14px;
        border         : 1.5px solid rgba(255,255,255,0.12);
        border-radius  : 22px;
        background     : rgba(255,255,255,0.06);
        color          : #c8dfff !important;
        font-size      : 12.5px;
        font-weight    : 600;
        text-decoration: none !important;
        letter-spacing : 0.25px;
        font-family    : -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        transition     : background 0.18s ease, border-color 0.18s ease,
                         transform 0.14s ease, box-shadow 0.18s ease;
        white-space    : nowrap;
    }}
    .snav-btn:hover {{
        background  : rgba(0,118,206,0.55) !important;
        border-color: #4dabf7              !important;
        color       : #fff                 !important;
        transform   : translateX(-4px);
        box-shadow  : -3px 0 12px rgba(0,118,206,0.4);
    }}
    .snav-btn:active {{
        background: #0076CE !important;
        transform : translateX(-1px);
    }}
    .snav-icon  {{ font-size: 15px; line-height: 1; flex-shrink: 0; }}
    .snav-label {{ font-size: 12px; }}
    </style>

    <div id="dash-sidenav">
        <div class="snav-panel">
            <div class="snav-title">Navigate</div>
            {links_html}
        </div>
        <div class="snav-handle">{dots_html}</div>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# FINANCIAL YEAR HELPERS  (same logic as ageing_module)
# ─────────────────────────────────────────────────────────────────────────────

def _month_to_fy(dt):
    """Map a Timestamp to its FY label (Apr-Mar cycle)."""
    y = dt.year if dt.month >= 4 else dt.year - 1
    return f"FY {y}-{str(y + 1)[2:]}"


def _current_fy_label():
    today = pd.Timestamp.today()
    y = today.year if today.month >= 4 else today.year - 1
    return f"FY {y}-{str(y + 1)[2:]}"


def _fy_range(fy_str):
    y = int(fy_str.replace("FY ", "").split("-")[0])
    return pd.Timestamp(year=y, month=4, day=1), pd.Timestamp(year=y + 1, month=3, day=31)


# ═════════════════════════════════════════════════════════════════════════════
# DATA PREP
# ═════════════════════════════════════════════════════════════════════════════

def _prep_master(master_df):
    """Normalise master_df columns → numeric, derive Net."""
    df = master_df.copy()
    for col in ["DSP $ (BC)", "SSP $ (BC)", "C DSP $", "C SSP $"]:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["Net $ (BC)"] = df["DSP $ (BC)"] - df["SSP $ (BC)"]
    df["C Net $"]    = df["C DSP $"]    - df["C SSP $"]
    df["Month"]      = pd.to_datetime(df["Month"], errors="coerce")
    return df.dropna(subset=["Month"])


def _prep_cashflow(dsp_df, ssp_df):
    """Compute AR/AP outstanding & overdue from dsp_df / ssp_df."""
    today = pd.Timestamp.today()
    result = {
        "ar_total": 0, "ar_outstanding": 0, "ar_overdue": 0,
        "ap_total": 0, "ap_outstanding": 0, "ap_overdue": 0,
        "ar_collected": 0, "ap_paid": 0,
    }

    if dsp_df is not None and not dsp_df.empty:
        d = dsp_df.copy()
        d["Receivable $"]      = pd.to_numeric(d.get("Receivable $", 0), errors="coerce").fillna(0)
        d["Received Amount $"] = pd.to_numeric(d.get("Received Amount $", 0), errors="coerce").fillna(0)
        d["Due Date"]          = pd.to_datetime(d.get("Due Date"), errors="coerce")
        d["_os"]               = d["Receivable $"] - d["Received Amount $"]
        result["ar_total"]     = d["Receivable $"].sum()
        result["ar_collected"] = d["Received Amount $"].sum()
        result["ar_outstanding"] = d["_os"].sum()
        result["ar_overdue"]   = d.loc[(d["_os"] > 0) & (d["Due Date"] < today), "_os"].sum()

    if ssp_df is not None and not ssp_df.empty:
        s = ssp_df.copy()
        s["Payable $"]      = pd.to_numeric(s.get("Payable $", 0), errors="coerce").fillna(0)
        s["Paid Amount $"]  = pd.to_numeric(s.get("Paid Amount $", 0), errors="coerce").fillna(0)
        s["Due Date"]       = pd.to_datetime(s.get("Due Date"), errors="coerce")
        s["_os"]            = s["Payable $"] - s["Paid Amount $"]
        result["ap_total"]  = s["Payable $"].sum()
        result["ap_paid"]   = s["Paid Amount $"].sum()
        result["ap_outstanding"] = s["_os"].sum()
        result["ap_overdue"]= s.loc[(s["_os"] > 0) & (s["Due Date"] < today), "_os"].sum()

    return result


# ═════════════════════════════════════════════════════════════════════════════
# CHART HELPERS
# ═════════════════════════════════════════════════════════════════════════════

_CHART_BG = dict(plot_bgcolor="white", paper_bgcolor="white",
                 margin=dict(l=10, r=10, t=50, b=10))

_AXIS_STYLE = dict(showgrid=True, gridcolor="#f0f0f0", tickformat=",.0f",
                   tickprefix="$")
                   
# ─────────────────────────────────────────────────────────────────────────────
# LOCKED PLOTLY CONFIG
# Hover allowed, editing disabled
# ─────────────────────────────────────────────────────────────────────────────

_PLOTLY_LOCK_CONFIG = {
    "displayModeBar": False,
    "scrollZoom": False,
    "doubleClick": False,
    "editable": False,
    "responsive": True,
    "showAxisDragHandles": False,
}

def _chart_monthly_revenue(df_month):
    """Grouped bar: Revenue vs Cost vs Profit per month."""
    if not _PLOTLY or df_month.empty:
        return

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Revenue (DSP)",
        x=df_month["Label"], y=df_month["DSP $ (BC)"],
        marker_color="#0076CE",
        hovertemplate="<b>%{x}</b><br>Revenue: $%{y:,.2f}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Cost (SSP)",
        x=df_month["Label"], y=df_month["SSP $ (BC)"],
        marker_color="#dc3545",
        hovertemplate="<b>%{x}</b><br>Cost: $%{y:,.2f}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Gross Profit",
        x=df_month["Label"], y=df_month["Net $ (BC)"],
        marker_color="#198754",
        hovertemplate="<b>%{x}</b><br>Profit: $%{y:,.2f}<extra></extra>",
    ))
    fig.update_layout(
        dragmode=False,
        barmode="group",
        title=dict(text="📅 Monthly Revenue vs Cost vs Profit",
                   font=dict(size=13, color="#003366")),
        xaxis=dict(tickangle=-30, tickfont=dict(size=10)),
        yaxis=_AXIS_STYLE,
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1),
        height=320,
        **_CHART_BG,
    )
    st.plotly_chart(
        fig,
        use_container_width=True,
        config=_PLOTLY_LOCK_CONFIG
    )


def _chart_profit_trend(df_month):
    """Line chart: Cumulative / Monthly profit trend."""
    if not _PLOTLY or df_month.empty:
        return
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        name="Monthly Profit",
        x=df_month["Label"], y=df_month["Net $ (BC)"],
        mode="lines+markers",
        line=dict(color="#0d6efd", width=2.5),
        marker=dict(size=7),
        hovertemplate="<b>%{x}</b><br>Profit: $%{y:,.2f}<extra></extra>",
        fill="tozeroy", fillcolor="rgba(13,110,253,0.08)",
    ))
    df_month = df_month.copy()
    df_month["Cumulative"] = df_month["Net $ (BC)"].cumsum()
    fig.add_trace(go.Scatter(
        name="Cumulative Profit",
        x=df_month["Label"], y=df_month["Cumulative"],
        mode="lines",
        line=dict(color="#198754", width=2, dash="dot"),
        hovertemplate="<b>%{x}</b><br>Cumulative: $%{y:,.2f}<extra></extra>",
    ))
    fig.update_layout(
        dragmode=False,
        title=dict(text="📈 Profit Trend", font=dict(size=13, color="#003366")),
        xaxis=dict(tickangle=-30, tickfont=dict(size=10)),
        yaxis=_AXIS_STYLE,
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1),
        height=300,
        **_CHART_BG,
    )
    st.plotly_chart(fig, use_container_width=True,
                    config=_PLOTLY_LOCK_CONFIG)


def _chart_ar_ap_bar(cf):
    """Horizontal bar: AR vs AP outstanding."""
    if not _PLOTLY:
        return
    labels  = ["AR Outstanding", "AP Outstanding", "AR Overdue", "AP Overdue"]
    values  = [cf["ar_outstanding"], cf["ap_outstanding"],
               cf["ar_overdue"],      cf["ap_overdue"]]
    colors  = ["#0076CE", "#dc3545", "#e65100", "#b71c1c"]
    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h",
        marker_color=colors,
        hovertemplate="%{y}: $%{x:,.2f}<extra></extra>",
        text=[f"${v:,.0f}" for v in values],
        textposition="outside",
    ))
    fig.update_layout(
        dragmode=False,
        title=dict(text="💰 Cash-Flow Snapshot — AR vs AP",
                   font=dict(size=13, color="#003366")),
        xaxis=dict(tickprefix="$", tickformat=",.0f",
                   showgrid=True, gridcolor="#f0f0f0"),
        height=260,
        **_CHART_BG,
    )
    st.plotly_chart(fig, use_container_width=True,
                    config=_PLOTLY_LOCK_CONFIG)


def _chart_collection_donut(cf):
    """Two small donuts: AR collection % and AP payment %."""
    if not _PLOTLY:
        return

    ar_pct = (cf["ar_collected"] / cf["ar_total"] * 100) if cf["ar_total"] else 0
    ap_pct = (cf["ap_paid"]      / cf["ap_total"] * 100) if cf["ap_total"] else 0

    def _donut(pct, title, color):
        fig = go.Figure(go.Pie(
            values=[pct, max(0, 100 - pct)],
            labels=["Done", "Pending"],
            hole=0.62,
            marker=dict(colors=[color, "#e9ecef"],
                        line=dict(color="white", width=2)),
            textinfo="none",
            hovertemplate="%{label}: %{value:.1f}%<extra></extra>",
            sort=False,
        ))
        fig.add_annotation(
            text=f"<b>{pct:.1f}%</b>",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color=color), xanchor="center",
        )
        fig.update_layout(
            dragmode=False,
            title=dict(text=title, font=dict(size=12, color="#003366")),
            showlegend=False,
            margin=dict(l=5, r=5, t=40, b=5),
            height=200,
            plot_bgcolor="white",
            paper_bgcolor="white",
        )
        return fig

    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(_donut(ar_pct, "AR Collection Rate", "#0076CE"),
                        use_container_width=True,
                        config=_PLOTLY_LOCK_CONFIG)
    with c2:
        st.plotly_chart(_donut(ap_pct, "AP Payment Rate", "#198754"),
                        use_container_width=True,
                        config=_PLOTLY_LOCK_CONFIG)


def _chart_partner_revenue(df, top_n=10):
    """Horizontal bar: Top N partners by revenue."""
    if not _PLOTLY or df.empty or "Partner Name" not in df.columns:
        return
    grp = (
        df.groupby("Partner Name")["DSP $ (BC)"].sum()
          .sort_values(ascending=False)
          .head(top_n)
          .reset_index()
    )
    if grp.empty:
        return
    fig = go.Figure(go.Bar(
        x=grp["DSP $ (BC)"],
        y=grp["Partner Name"],
        orientation="h",
        marker=dict(
            color=grp["DSP $ (BC)"],
            colorscale=[[0, "#0059b3"], [1, "#00c6ff"]],
            showscale=False,
        ),
        hovertemplate="<b>%{y}</b><br>Revenue: $%{x:,.2f}<extra></extra>",
        text=[f"${v:,.0f}" for v in grp["DSP $ (BC)"]],
        textposition="outside",
    ))
    fig.update_layout(
        dragmode=False,
        title=dict(text=f"🏆 Top {top_n} Partners by Revenue",
                   font=dict(size=13, color="#003366")),
        xaxis=dict(tickprefix="$", tickformat=",.0f",
                   showgrid=True, gridcolor="#f0f0f0"),
        yaxis=dict(autorange="reversed"),
        height=max(260, top_n * 28),
        **_CHART_BG,
    )
    st.plotly_chart(fig, use_container_width=True,
                    config=_PLOTLY_LOCK_CONFIG)


def _chart_revenue_mix(df):
    """Donut: DSP revenue share by partner."""
    if not _PLOTLY or df.empty or "Partner Name" not in df.columns:
        return
    grp = (
        df.groupby("Partner Name")["DSP $ (BC)"].sum()
          .sort_values(ascending=False)
    )
    if grp.empty:
        return
    # Collapse small partners into "Others"
    threshold = grp.sum() * 0.02
    major = grp[grp >= threshold]
    minor = grp[grp <  threshold]
    if not minor.empty:
        major = pd.concat([major, pd.Series({"Others": minor.sum()})])

    fig = go.Figure(go.Pie(
        labels=major.index, values=major.values,
        hole=0.50,
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>$%{value:,.2f}<extra></extra>",
    ))
    fig.update_layout(
        dragmode=False,
        title=dict(text="🥧 Revenue Mix by Partner",
                   font=dict(size=13, color="#003366")),
        legend=dict(orientation="h", yanchor="bottom", y=-0.3,
                    xanchor="center", x=0.5),
        margin=dict(l=10, r=10, t=50, b=30),
        height=320,
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    st.plotly_chart(fig, use_container_width=True,
                    config=_PLOTLY_LOCK_CONFIG)



# ═════════════════════════════════════════════════════════════════════════════
# PARTNER ONBOARDING  CHART
# ═════════════════════════════════════════════════════════════════════════════

def _render_partner_onboarding(partner_df):
    """Bar chart + table: partners onboarded per month from List of Partners."""
    if partner_df is None or partner_df.empty:
        st.info("No partner data available.")
        return

    df = partner_df.copy()

    # Detect the date column — handle both old and new DB schemas
    date_col = None
    for candidate in ["agreement_date", "Agreement Start Date", "Agreement Date"]:
        if candidate in df.columns:
            date_col = candidate
            break
    if date_col is None:
        st.info("Agreement date column not found in partner data.")
        return

    df["_adate"] = pd.to_datetime(df[date_col], errors="coerce", dayfirst=True)
    df = df.dropna(subset=["_adate"])
    if df.empty:
        st.info("No valid agreement dates found.")
        return

    df["_month"] = df["_adate"].dt.to_period("M").dt.to_timestamp()
    df["_label"] = df["_adate"].dt.strftime("%b-%Y")

    # Detect name column
    name_col = next(
        (c for c in ["short_name", "Short Name using in Bidscube", "Short Name", "legal_name", "Legal Entity Name"]
         if c in df.columns), None
    )

    monthly = (
        df.groupby(["_month"])
          .agg(_count=pd.NamedAgg(column="_label", aggfunc="count"),
               _names=pd.NamedAgg(
                   column=(name_col if name_col else "_label"),
                   aggfunc=lambda x: ", ".join(x.dropna().astype(str).tolist())
               ))
          .reset_index()
          .sort_values("_month")          # sort by true datetime — guaranteed order
    )
    # Derive display label AFTER sort so order is locked
    monthly["_label"] = monthly["_month"].dt.strftime("%b-%Y")

    if not _PLOTLY or monthly.empty:
        return

    fig = go.Figure(go.Bar(
        # Use datetime on x-axis → Plotly time axis always renders chronologically
        x=monthly["_month"],
        y=monthly["_count"],
        text=monthly["_count"],
        textposition="outside",
        marker=dict(
            color=monthly["_count"],
            colorscale=[[0, "#0059b3"], [1, "#00c6ff"]],
            showscale=False,
        ),
        customdata=monthly["_names"],
        hovertemplate=(
            "<b>%{x|%b-%Y}</b><br>"
            "Partners Onboarded: <b>%{y}</b><br>"
            "%{customdata}<extra></extra>"
        ),
    ))
    fig.update_layout(
        dragmode=False,
        title=dict(text="🤝 Partners Onboarded by Month",
                   font=dict(size=13, color="#003366")),
        xaxis=dict(
            tickangle=-30,
            tickfont=dict(size=10),
            showgrid=False,
            type="date",                       # ← enforce date axis
            tickformat="%b-%Y",                # ← display as Apr-2025
            dtick="M1",                        # one tick per month
        ),
        yaxis=dict(showgrid=True, gridcolor="#f0f0f0", tickformat="d", dtick=1),
        height=310,
        **_CHART_BG,
    )
    st.plotly_chart(fig, use_container_width=True,
                    config=_PLOTLY_LOCK_CONFIG)

    # Expandable detail table — rows already sorted by _month above
    with st.expander("📋 Partner Onboarding Detail", expanded=False):
        _rows2 = [
            {
                "Month":              r["_label"],
                "Partners Onboarded": int(r["_count"]),
                "Partner Names":      r["_names"],
            }
            for _, r in monthly.iterrows()   # monthly already sorted chronologically
        ]
        st.dataframe(pd.DataFrame(_rows2), use_container_width=True, hide_index=True)


# ═════════════════════════════════════════════════════════════════════════════
# PARTNER MONTHWISE SUMMARY  (from Summary tab — AgGrid style)
# ═════════════════════════════════════════════════════════════════════════════

def _render_partner_summary(master_df, dsp_df, ssp_df):
    """Partner-level month-wise C DSP / C SSP / Offset summary with AgGrid."""
    from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode

    if master_df is None or master_df.empty:
        st.info("No master data available.")
        return

    df_master = master_df.copy()
    df_master["Month"] = pd.to_datetime(df_master["Month"], errors="coerce")
    df_master["C DSP $"] = pd.to_numeric(df_master["C DSP $"], errors="coerce").fillna(0)
    df_master["C SSP $"] = pd.to_numeric(df_master["C SSP $"], errors="coerce").fillna(0)

    partner_list = sorted(df_master["Partner Name"].dropna().unique().tolist())
    partner_options = ["— Select Partner —"] + partner_list

    max_len = max((len(str(n)) for n in partner_list), default=20)
    dyn_w   = max(280, min(900, max_len * 10))

    st.markdown(f"""
    <style>
    div[data-testid="stSelectbox"][data-key="dash_ps_partner"] > div {{
        width: {dyn_w}px !important;
    }}
    </style>""", unsafe_allow_html=True)

    selected = st.selectbox(
        "Select Partner",
        partner_options,
        index=0,
        key="dash_ps_partner"
    )

    if selected == "— Select Partner —":
        st.info("Select a partner above to view their month-wise breakdown.")
        return

    # ── Filter master ─────────────────────────────────────────────────────
    df_p = df_master[df_master["Partner Name"] == selected].copy()

    # ── Exclusion logic (months already green/yellow in DSP or SSP) ───────
    excluded_dsp, excluded_ssp = set(), set()

    _dsp = (dsp_df.copy() if dsp_df is not None and not dsp_df.empty
            else pd.DataFrame())
    _ssp = (ssp_df.copy() if ssp_df is not None and not ssp_df.empty
            else pd.DataFrame())

    def _to_monthstr(df, col="Month"):
        df[col] = pd.to_datetime(df[col], errors="coerce")
        return df[col].dt.strftime("%b-%Y").fillna(df[col].astype(str))

    if not _dsp.empty and "DSP Name" in _dsp.columns:
        d = _dsp[_dsp["DSP Name"] == selected].copy()
        d["_ms"] = _to_monthstr(d)
        d["Receivable $"]      = pd.to_numeric(d.get("Receivable $", 0),      errors="coerce").fillna(0)
        d["Received Amount $"] = pd.to_numeric(d.get("Received Amount $", 0), errors="coerce").fillna(0)
        excluded_dsp = set(
            pd.concat([
                d[d["Received Amount $"] == d["Receivable $"]],
                d[(d["Received Amount $"] != 0) & (d["Received Amount $"] != d["Receivable $"])]
            ])["_ms"]
        )

    if not _ssp.empty and "SSP Name" in _ssp.columns:
        s = _ssp[_ssp["SSP Name"] == selected].copy()
        s["_ms"] = _to_monthstr(s)
        s["Payable $"]     = pd.to_numeric(s.get("Payable $", 0),     errors="coerce").fillna(0)
        s["Paid Amount $"] = pd.to_numeric(s.get("Paid Amount $", 0), errors="coerce").fillna(0)
        excluded_ssp = set(
            pd.concat([
                s[s["Paid Amount $"] == s["Payable $"]],
                s[(s["Paid Amount $"] != 0) & (s["Paid Amount $"] != s["Payable $"])]
            ])["_ms"]
        )

    excluded = excluded_dsp | excluded_ssp
    df_p["_ms"] = df_p["Month"].dt.strftime("%b-%Y")
    df_p = df_p[~df_p["_ms"].isin(excluded)].drop(columns=["_ms"])

    if df_p.empty:
        st.success("✅ All months settled — nothing outstanding for this partner.")
        return

    # ── Build summary ─────────────────────────────────────────────────────
    df_sum = (
        df_p.groupby("Month", as_index=False)
            .agg({"C DSP $": "sum", "C SSP $": "sum"})
    )
    df_sum["Offset $ USD"] = df_sum["C DSP $"] - df_sum["C SSP $"]

    # ── Due Date lookup ───────────────────────────────────────────────────
    _dsp2 = _dsp.copy()
    _ssp2 = _ssp.copy()
    if not _dsp2.empty:
        _dsp2["Month"] = pd.to_datetime(_dsp2["Month"], errors="coerce")
    if not _ssp2.empty:
        _ssp2["Month"] = pd.to_datetime(_ssp2["Month"], errors="coerce")

    due_dates = []
    for _, row in df_sum.iterrows():
        m = row["Month"]
        dd = None
        if not _dsp2.empty and "DSP Name" in _dsp2.columns:
            hit = _dsp2[(_dsp2["DSP Name"] == selected) & (_dsp2["Month"] == m)]
            if not hit.empty:
                dd = hit.iloc[0].get("Due Date")
        if dd is None and not _ssp2.empty and "SSP Name" in _ssp2.columns:
            hit = _ssp2[(_ssp2["SSP Name"] == selected) & (_ssp2["Month"] == m)]
            if not hit.empty:
                dd = hit.iloc[0].get("Due Date")
        due_dates.append(dd)

    df_sum["Due Date"] = pd.to_datetime(due_dates, errors="coerce").strftime("%d-%b-%Y")
    df_sum["Month"]    = df_sum["Month"].dt.strftime("%b-%Y")
    df_sum.rename(columns={"C DSP $": "As DSP", "C SSP $": "As SSP"}, inplace=True)

    # ── Total row ─────────────────────────────────────────────────────────
    total_row = {
        "Month": "TOTAL",
        "As DSP": df_sum["As DSP"].sum(),
        "As SSP": df_sum["As SSP"].sum(),
        "Offset $ USD": df_sum["Offset $ USD"].sum(),
        "Due Date": "",
    }
    df_sum = pd.DataFrame(
        [{k: r.get(k, "") for k in ["Month","As DSP","As SSP","Offset $ USD","Due Date"]}
         for r in df_sum.to_dict("records")] + [total_row]
    )

    # ── AgGrid ───────────────────────────────────────────────────────────
    cur_fmt = JsCode("""
        function(params) {
            if (params.value == null || params.value === '') return '';
            return '$' + parseFloat(params.value).toLocaleString(undefined,
                {minimumFractionDigits: 2, maximumFractionDigits: 2});
        }
    """)
    total_style = JsCode("""
        function(params) {
            if (params.data && params.data.Month === 'TOTAL')
                return {backgroundColor:'#003366', color:'white', fontWeight:'bold'};
            return {fontWeight:'600'};
        }
    """)
    offset_style = JsCode("""
        function(params) {
            if (params.data && params.data.Month === 'TOTAL')
                return {backgroundColor:'#003366', color:'white', fontWeight:'bold'};
            let s = {backgroundColor:'#E8F5E9', fontWeight:'bold'};
            if (params.value < 0) s.color = '#dc3545';
            return s;
        }
    """)

    gb = GridOptionsBuilder.from_dataframe(df_sum)
    gb.configure_column("Month",    minWidth=100, flex=1)
    gb.configure_column("Due Date", minWidth=110, flex=1)
    gb.configure_column("As DSP",   type=["numericColumn"],
                        valueFormatter=cur_fmt, cellStyle=total_style, flex=1)
    gb.configure_column("As SSP",   type=["numericColumn"],
                        valueFormatter=cur_fmt, cellStyle=total_style, flex=1)
    gb.configure_column("Offset $ USD", type=["numericColumn"],
                        valueFormatter=cur_fmt, cellStyle=offset_style, flex=1)
    gb.configure_default_column(resizable=True, sortable=True, filter=False)
    opts = gb.build()
    opts["getRowStyle"] = JsCode("""
        function(p) {
            if (p.data && p.data.Month === 'TOTAL')
                return {backgroundColor:'#003366', color:'white', fontWeight:'bold',
                        fontSize:'13px'};
        }
    """)
    AgGrid(
        df_sum,
        gridOptions=opts,
        allow_unsafe_jscode=True,
        fit_columns_on_grid_load=True,
        height=min(80 + len(df_sum) * 42, 420),
        custom_css={
            ".ag-header": {
                "background-color": "#003366 !important",
                "color": "white !important",
                "font-weight": "bold !important",
                "font-size": "13px !important",
            },
            ".ag-header-cell-label": {
                "color": "white !important",
                "font-weight": "bold !important",
            },
        },
        update_mode=GridUpdateMode.NO_UPDATE,
    )


# ═════════════════════════════════════════════════════════════════════════════
# P&L  SECTION  HELPER
# ═════════════════════════════════════════════════════════════════════════════

def _strip_fy(fy_label):
    """'FY 2025-26' → '2025-26'  (handles both formats)."""
    return fy_label.replace("FY ", "").strip()


def _col(df, *candidates):
    """Return first matching column name (case-insensitive, snake or title)."""
    lower_map = {c.lower().replace(" ", "_").replace("-", "_"): c for c in df.columns}
    for cand in candidates:
        key = cand.lower().replace(" ", "_").replace("-", "_")
        if key in lower_map:
            return lower_map[key]
    return None


def _get_avg_fx(cost_df, months_in_scope, sel_fy="All"):
    """Return average FX rate for given months from cost_df."""
    if cost_df is None or cost_df.empty:
        return 0.0
    _c = cost_df.copy()
    _c.columns = _c.columns.str.strip()

    fx_col    = _col(_c, "FX Rate", "fx_rate")
    fy_col    = _col(_c, "Financial Year", "financial_year")
    month_col = _col(_c, "Month", "month")

    if not fx_col or not month_col:
        return 0.0

    _c[fx_col] = pd.to_numeric(_c[fx_col], errors="coerce").fillna(0)

    if sel_fy != "All" and fy_col:
        _c = _c[_c[fy_col].astype(str).str.strip() == _strip_fy(sel_fy)]

    mask = _c[month_col].astype(str).str.strip().isin(months_in_scope) & (_c[fx_col] > 0)
    vals = _c.loc[mask, fx_col].tolist()
    return (sum(vals) / len(vals)) if vals else 0.0


def _render_pnl_section(master_df, cost_df, sel_fy, sel_month):
    """Render the P&L section inside the dashboard."""

    if sel_fy == "All":
        st.info("📅 Select a specific Financial Year above to view the P&L statement.")
        return

    if cost_df is None or cost_df.empty:
        st.warning("No Cost Centre data found. Please load it via the Costs Centre tab.")
        return

    # ── Prep master ──────────────────────────────────────────────────────────
    df = master_df.copy()
    df["Month"]   = pd.to_datetime(df["Month"], errors="coerce")
    df["C Net $"] = pd.to_numeric(df.get("C Net $", 0), errors="coerce").fillna(0)

    s, e = _fy_range(sel_fy)
    df = df[(df["Month"] >= s) & (df["Month"] <= e)]
    if sel_month != "All":
        sel_dt = pd.to_datetime(sel_month, format="%b-%Y", errors="coerce")
        df = df[df["Month"] == sel_dt]

    if df.empty:
        st.info("No master data for the selected period.")
        return

    active_months = df["Month"].dt.strftime("%b-%Y").unique().tolist()

    # ── FX rate ─────────────────────────────────────────────────────────────
    fx_rate = _get_avg_fx(cost_df, active_months, sel_fy)
    if fx_rate == 0:
        fx_rate = 84.0   # fallback

    revenue_usd = df["C Net $"].sum()
    revenue_inr = revenue_usd * fx_rate

    # ── Prep cost centre — handle BOTH snake_case and Title Case column names ─
    _c = cost_df.copy()
    _c.columns = _c.columns.str.strip()

    # Detect every relevant column regardless of naming convention
    fy_col      = _col(_c, "Financial Year", "financial_year")
    month_col   = _col(_c, "Month", "month")
    cat_col     = _col(_c, "Category", "category")
    cur_col     = _col(_c, "Currency", "currency")
    usd_col     = _col(_c, "Amount USD", "amount_usd")
    inr_col     = _col(_c, "Amount INR", "amount_inr")
    fx_col      = _col(_c, "FX Rate", "fx_rate")

    # Numeric conversions
    for c in [usd_col, inr_col, fx_col]:
        if c:
            _c[c] = pd.to_numeric(_c[c], errors="coerce").fillna(0)

    # Build _final_inr: start from INR amount, override USD rows
    _c["_final_inr"] = _c[inr_col].copy() if inr_col else 0.0
    if cur_col and usd_col and fx_col:
        usd_mask = _c[cur_col].astype(str).str.strip().str.upper() == "USD"
        _c.loc[usd_mask, "_final_inr"] = _c.loc[usd_mask, usd_col] * _c.loc[usd_mask, fx_col]

    # FY filter  ("FY 2025-26" → "2025-26" to match DB storage)
    if fy_col:
        _c = _c[_c[fy_col].astype(str).str.strip() == _strip_fy(sel_fy)]

    # Month filter
    if sel_month != "All" and month_col:
        _c = _c[_c[month_col].astype(str).str.strip() == sel_month.strip()]

    # Aggregate
    if cat_col and not _c.empty:
        direct_cost   = _c.loc[_c[cat_col].astype(str).str.strip() == "Direct",   "_final_inr"].sum()
        indirect_cost = _c.loc[_c[cat_col].astype(str).str.strip() == "Indirect", "_final_inr"].sum()
    else:
        direct_cost = indirect_cost = 0.0

    # ── Calculations ─────────────────────────────────────────────────────────
    gross_profit = revenue_inr - direct_cost
    net_profit   = gross_profit - indirect_cost
    gp_pct       = (gross_profit / revenue_inr * 100) if revenue_inr else 0
    np_pct       = (net_profit   / revenue_inr * 100) if revenue_inr else 0

    period_label = sel_fy + (f" — {sel_month}" if sel_month != "All" else "")

    # ── KPI strip ────────────────────────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)

    def _ikpi(col, title, val, grad, icon=""):
        try:
            num = float(val)
            display = f"\u20b9{num:,.0f}"
        except Exception:
            display = str(val)
        bg_map = {
            "blue":   "linear-gradient(135deg,#003366,#0076CE)",
            "red":    "linear-gradient(135deg,#842029,#dc3545)",
            "green":  "linear-gradient(135deg,#0f5132,#198754)",
            "purple": "linear-gradient(135deg,#d765c5,#0d6efd)",
            "orange": "linear-gradient(135deg,#a0522d,#e65100)",
        }
        bg = bg_map.get(grad, bg_map["blue"])
        with col:
            st.markdown(f"""
            <div style="background:{bg};padding:18px 16px;border-radius:14px;
                        box-shadow:0 6px 20px rgba(0,0,0,.22);margin-bottom:8px;">
                <div style="font-size:11px;font-weight:700;color:#FFEF00;
                            text-transform:uppercase;letter-spacing:.6px;">
                    {icon}&nbsp;{title}</div>
                <div style="font-size:24px;font-weight:900;color:#fff;margin-top:6px;">
                    {display}</div>
            </div>""", unsafe_allow_html=True)

    _ikpi(k1, "Revenue (INR)",  revenue_inr,  "blue",   "💵")
    _ikpi(k2, "Direct Cost",    direct_cost,  "red",    "💸")
    _ikpi(k3, "Gross Profit",   gross_profit, "green",  "📈")
    _ikpi(k4, "Indirect Cost",  indirect_cost,"orange", "🏢")
    _ikpi(k5, "Net Profit",     net_profit,   "purple", "💰")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── P&L Table + FX info ──────────────────────────────────────────────────
    tbl_col, fx_col_ui = st.columns([2, 1])

    with tbl_col:
        gp_bg  = "#E8F5E9" if gross_profit >= 0 else "#FFEBEE"
        np_bg  = "#E3F2FD" if net_profit   >= 0 else "#FFEBEE"
        np_col = "#0d47a1" if net_profit   >= 0 else "#b71c1c"
        st.markdown(f"""
        <table style="width:100%;border-collapse:collapse;font-size:14px;
                      border-radius:10px;overflow:hidden;
                      box-shadow:0 4px 14px rgba(0,0,0,.12);">
          <thead>
            <tr style="background:#003366;color:white;">
              <th style="padding:10px 14px;text-align:left;">Particulars</th>
              <th style="padding:10px 14px;text-align:right;">Amount (INR)</th>
            </tr>
          </thead>
          <tbody>
            <tr style="background:#f9f9f9;">
              <td style="padding:9px 14px;font-weight:600;">Revenue</td>
              <td style="padding:9px 14px;text-align:right;font-weight:700;">
                  \u20b9{revenue_inr:,.0f}</td>
            </tr>
            <tr>
              <td style="padding:9px 14px;">Less: Direct Cost</td>
              <td style="padding:9px 14px;text-align:right;color:#D32F2F;font-weight:600;">
                  (\u20b9{direct_cost:,.0f})</td>
            </tr>
            <tr style="background:{gp_bg};">
              <td style="padding:10px 14px;font-weight:700;color:#1b5e20;">Gross Profit</td>
              <td style="padding:10px 14px;text-align:right;font-weight:800;color:#1b5e20;">
                  \u20b9{gross_profit:,.0f}</td>
            </tr>
            <tr style="background:#fafafa;">
              <td style="padding:7px 14px;color:#555;">GP %</td>
              <td style="padding:7px 14px;text-align:right;font-weight:700;color:#2e7d32;">
                  {gp_pct:.2f}%</td>
            </tr>
            <tr>
              <td style="padding:9px 14px;">Less: Indirect Cost</td>
              <td style="padding:9px 14px;text-align:right;color:#D32F2F;font-weight:600;">
                  (\u20b9{indirect_cost:,.0f})</td>
            </tr>
            <tr style="background:{np_bg};border-top:2px solid #003366;">
              <td style="padding:12px 14px;font-size:16px;font-weight:800;color:{np_col};">
                  Net Profit</td>
              <td style="padding:12px 14px;text-align:right;font-size:16px;
                         font-weight:900;color:{np_col};">
                  \u20b9{net_profit:,.0f}</td>
            </tr>
            <tr style="background:#fafafa;">
              <td style="padding:7px 14px;color:#555;">NP %</td>
              <td style="padding:7px 14px;text-align:right;font-weight:800;color:{np_col};">
                  {np_pct:.2f}%</td>
            </tr>
          </tbody>
        </table>
        """, unsafe_allow_html=True)

    with fx_col_ui:
        months_str = ", ".join(active_months) if active_months else "—"
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#003366,#005599);
            border-radius:12px;padding:20px;color:white;
            box-shadow:0 6px 18px rgba(0,51,102,.25);">
            <div style="font-size:13px;font-weight:800;color:#FFEF00;
                        text-transform:uppercase;letter-spacing:.5px;margin-bottom:14px;">
                \U0001f4ca FX &amp; USD Summary
            </div>
            <div style="margin-bottom:10px;">
                <div style="font-size:11px;color:#90caf9;">Revenue (USD)</div>
                <div style="font-size:22px;font-weight:900;">${revenue_usd:,.2f}</div>
            </div>
            <div style="margin-bottom:10px;">
                <div style="font-size:11px;color:#90caf9;">Avg FX Rate Used</div>
                <div style="font-size:22px;font-weight:900;">\u20b9{fx_rate:,.2f}</div>
            </div>
            <div style="background:rgba(255,255,255,.1);border-radius:8px;
                        padding:10px;margin-top:12px;">
                <div style="font-size:11px;color:#90caf9;">Period</div>
                <div style="font-size:13px;font-weight:700;">{period_label}</div>
            </div>
            <div style="background:rgba(255,255,255,.1);border-radius:8px;
                        padding:10px;margin-top:10px;">
                <div style="font-size:11px;color:#90caf9;">Cost Centre Months</div>
                <div style="font-size:13px;font-weight:700;">
                    {months_str}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── PDF Export ───────────────────────────────────────────────────────
        pdf_bytes = _pnl_pdf(
            revenue_usd, fx_rate, revenue_inr,
            direct_cost, gross_profit, gp_pct,
            indirect_cost, net_profit, np_pct,
            period_label,
        )
        if pdf_bytes:
            safe = period_label.replace(" ","_").replace("/","-").replace("\u2014","").replace(" ","")
            st.download_button(
                label="\u2b07\ufe0f Export P&L as PDF",
                data=pdf_bytes,
                file_name=f"PnL_{safe}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.warning("PDF generation requires reportlab. Run: pip install reportlab")



# ═════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═════════════════════════════════════════════════════════════════════════════

def render_dashboard_tab(master_df, dsp_df=None, ssp_df=None, partner_df=None, cost_df=None):
    """
    Render the full Executive Dashboard.

    Parameters
    ----------
    master_df : pd.DataFrame   — from load_master_data()
    dsp_df      : pd.DataFrame   — from load_dsp_final()   (optional)
    ssp_df      : pd.DataFrame   — from load_ssp_final()   (optional)
    partner_df  : pd.DataFrame   — from load_partner_list() (optional)
    cost_df     : pd.DataFrame   — from load_cost_centre()  (optional)
    """
    
    st.markdown('''
            <div style="background:linear-gradient(135deg,#003366 0%,#005599 100%);
            border-radius:10px;padding:18px 24px;margin-bottom:20px;
            box-shadow:0 4px 16px rgba(0,51,102,.2);
            display:flex;align-items:center;height:4px;gap:14px;">
            <div style="font-size:32px;">📊</div>
            <div>
                <div style="color:white;font-size:20px;font-weight:800;">
                    Dashboard</div>
            </div></div>
        ''', unsafe_allow_html=True)
    
    try:
        # ── GUARD: no data ───────────────────────────────────────────────────
        if master_df is None or master_df.empty:
            st.info("📭 No Master Data loaded yet. Please upload data via the "
                    "**Master Data** tab first.")
            return

        # ── PREP DATA ────────────────────────────────────────────────────────
        df = _prep_master(master_df)
        cf = _prep_cashflow(dsp_df, ssp_df)

        # ── STICKY SIDE NAV ──────────────────────────────────────────────────
        _render_nav_bar()

        # ── FILTER ROW ───────────────────────────────────────────────────────
        # Build FY list only from months present in the data
        df["_fy"] = df["Month"].apply(_month_to_fy)
        fy_list   = sorted(df["_fy"].dropna().unique().tolist(), reverse=True)
        cur_fy    = _current_fy_label()
        fy_default = cur_fy if cur_fy in fy_list else (fy_list[0] if fy_list else "All")
        fy_opts   = ["All"] + fy_list
        f1, f2, f3 = st.columns([1.5, 1.5, 3])

        with f1:
            sel_fy = st.selectbox("📅 Financial Year",
                                  fy_opts,
                                  index=fy_opts.index(fy_default) if fy_default in fy_opts else 0,
                                  key="dash_fy")
        with f2:
            all_months = (
                ["All"] +
                sorted(df["Month"].dropna().dt.strftime("%b-%Y").unique().tolist(),
                       key=lambda m: pd.to_datetime(m, format="%b-%Y",
                                                    errors="coerce"))
            )
            sel_month = st.selectbox("🗓️ Month", all_months, key="dash_month")

        with f3:
            partner_opts = (
                ["All"] +
                sorted(df["Partner Name"].dropna().unique().tolist())
                if "Partner Name" in df.columns else ["All"]
            )
            sel_partner = st.selectbox("🤝 Partner", partner_opts,
                                       key="dash_partner")

        # Apply filters
        filtered = df.copy()
        if sel_fy != "All":
            s, e = _fy_range(sel_fy)
            filtered = filtered[(filtered["Month"] >= s) & (filtered["Month"] <= e)]
        if sel_month != "All":
            filtered = filtered[
                filtered["Month"].dt.strftime("%b-%Y") == sel_month
            ]
        if sel_partner != "All" and "Partner Name" in filtered.columns:
            filtered = filtered[filtered["Partner Name"] == sel_partner]

        if filtered.empty:
            st.warning("⚠️ No data matches the selected filters.")
            return

        # ── TOP-LEVEL KPIs ───────────────────────────────────────────────────
        _anchor("sec-overview")
        
        st.divider()

        total_dsp   = filtered["DSP $ (BC)"].sum()
        total_ssp   = filtered["SSP $ (BC)"].sum()
        total_net   = filtered["Net $ (BC)"].sum()
        total_c_dsp = filtered["C DSP $"].sum()
        total_c_ssp = filtered["C SSP $"].sum()
        total_c_net = filtered["C Net $"].sum()
        ivt         = total_net - total_c_net
        ivt_pct     = (ivt / total_net * 100) if total_net else 0
        margin_pct  = (total_c_net / total_c_dsp * 100) if total_c_dsp else 0

        r1 = st.columns(6)
        with r1[0]: _kpi("Confirmed Revenue",  total_c_dsp, gradient="teal",   icon="✅")
        with r1[1]: _kpi("Confirmed Cost",     total_c_ssp, gradient="orange", icon="🧾")
        with r1[2]: _kpi("Confirmed Profit",   total_c_net, gradient="green",  icon="💰")
        with r1[3]: _kpi("Profit Margin %",    margin_pct,  gradient="purple", icon="📐", is_pct=True)
        with r1[4]: _kpi("IVT (Unconfirmed)",  ivt,         gradient="slate",  icon="⏳")
        with r1[5]: _kpi("IVT %",              ivt_pct,     gradient="blue",   icon="📊", is_pct=True)

        st.divider()

        # ── MONTHLY CHARTS ───────────────────────────────────────────────────
        _anchor("sec-monthly")
        _section("📅 Monthly Performance",
                 "Trend of Revenue, Cost and Profit by month")

        df_month = (
            filtered.groupby("Month")
                    .agg({"DSP $ (BC)": "sum",
                          "SSP $ (BC)": "sum",
                          "Net $ (BC)": "sum",
                          "C DSP $":    "sum",
                          "C SSP $":    "sum",
                          "C Net $":    "sum"})
                    .sort_index()
                    .reset_index()
        )
        df_month["Label"] = df_month["Month"].dt.strftime("%b-%Y")

        ch_col1, ch_col2 = st.columns([3, 2])
        with ch_col1:
            _chart_monthly_revenue(df_month)
        with ch_col2:
            _chart_profit_trend(df_month)

        st.divider()

        # ── CASH FLOW / AR-AP ────────────────────────────────────────────────
        _anchor("sec-cashflow")
        _section("💰 Cash Flow — AR & AP Overview",
                 "Accounts Receivable (DSP) and Accounts Payable (SSP)")
        st.divider()
        ar_pct = (cf["ar_collected"] / cf["ar_total"] * 100) if cf["ar_total"] else 0
        ap_pct = (cf["ap_paid"]      / cf["ap_total"] * 100) if cf["ap_total"] else 0

        cf_cols = st.columns(4)
        with cf_cols[0]:
            _kpi("AR Outstanding", cf["ar_outstanding"],
                 subtitle=f"Collected: {_fmt(cf['ar_collected'])}",
                 gradient="blue", icon="🏦")
        with cf_cols[1]:
            _kpi("AR Overdue", cf["ar_overdue"],
                 subtitle="Past due date",
                 gradient="orange", icon="⚠️")
        with cf_cols[2]:
            _kpi("AP Outstanding", cf["ap_outstanding"],
                 subtitle=f"Paid: {_fmt(cf['ap_paid'])}",
                 gradient="red", icon="📤")
        with cf_cols[3]:
            _kpi("AP Overdue", cf["ap_overdue"],
                 subtitle="Past due date",
                 gradient="orange", icon="🔴")

        st.markdown("<br>", unsafe_allow_html=True)
        cf_chart_col, cf_donut_col = st.columns([3, 2])
        with cf_chart_col:
            _chart_ar_ap_bar(cf)
        with cf_donut_col:
            _section("📊 Efficiency Rates", "Collection vs Payment")
            _chart_collection_donut(cf)

        # Efficiency bar
        eff_c1, eff_c2 = st.columns(2)
        with eff_c1:
            st.metric(
                label="Collection Efficiency (AR)",
                value=f"{ar_pct:.1f}%",
                delta=f"{ar_pct - 80:.1f}% vs 80% target",
                delta_color="normal"
            )
        with eff_c2:
            st.metric(
                label="Payment Rate (AP)",
                value=f"{ap_pct:.1f}%",
                delta=f"{ap_pct - 80:.1f}% vs 80% target",
                delta_color="normal"
            )

        st.divider()

        # ── PARTNER ANALYSIS ─────────────────────────────────────────────────
        _anchor("sec-partners")
        _section("🤝 Partner Revenue Analysis",
                 "Revenue contribution by partner")

        pa_col1, pa_col2 = st.columns([3, 2])
        with pa_col1:
            _chart_partner_revenue(filtered)
        with pa_col2:
            _chart_revenue_mix(filtered)

        st.divider()

        # ── PARTNER ONBOARDING CHART ─────────────────────────────────────────
        _anchor("sec-onboarding")
        _section("📅 Partner Onboarding Timeline",
                 "Number of partners onboarded each month (from List of Partners)")

        _render_partner_onboarding(partner_df)

        st.divider()

        # ── PARTNER MONTHWISE SUMMARY ────────────────────────────────────────
        _anchor("sec-summary")
        _section("🔍 Partner Month-wise Summary",
                 "Outstanding C DSP / C SSP / Offset per month for selected partner")

        _render_partner_summary(master_df, dsp_df, ssp_df)

        st.divider()

        # ── QUICK DATA TABLE
        _anchor("sec-table")


# ─────────────────────────────────────────────────────────────────────────────
        with st.expander("📋 Month-wise Summary Table", expanded=False):
            _rows = []
            for _, r in df_month.iterrows():
                _rows.append({
                    "Month":      r.get("Label", ""),
                    "C DSP $":    float(r.get("C DSP $", 0)),
                    "C SSP $":    float(r.get("C SSP $", 0)),
                    "C Net $":    float(r.get("C Net $", 0)),
                })
            _tot = {
                "Month":   "TOTAL",
                "C DSP $": sum(x["C DSP $"] for x in _rows),
                "C SSP $": sum(x["C SSP $"] for x in _rows),
                "C Net $": sum(x["C Net $"] for x in _rows),
            }
            _rows.append(_tot)
            show_df = pd.DataFrame(_rows)

            for c in ["C DSP $", "C SSP $", "C Net $"]:
                show_df[c] = show_df[c].apply(lambda v: f"${v:,.2f}")

            st.dataframe(show_df, use_container_width=True, hide_index=True)

        st.divider()

        
    except Exception as exc:
        import traceback
        st.error(f"Dashboard render error: {exc}")
        st.code(traceback.format_exc())
