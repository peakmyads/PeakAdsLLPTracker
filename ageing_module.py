"""
AR / AP Ageing Module
Author: Sumit
Description: Accounts Receivable (DSP) and Accounts Payable (SSP) Ageing Analysis
"""

import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode

BUCKET_COLS   = ["Current", "1-30 Days", "31-60 Days", "61-90 Days", ">90 Days"]
BUCKET_COLORS = ["#4CAF50", "#FFC107", "#FF9800", "#F44336", "#B71C1C"]
BUCKET_BG = {
    "Current":           "#E8F5E9",
    "1-30 Days":         "#FFF8E1",
    "31-60 Days":        "#FFF3E0",
    "61-90 Days":        "#FFEBEE",
    ">90 Days":          "#FFCDD2",
    "Total Outstanding": "#E3F2FD",
}
HEADER_CSS = {
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
}
CURRENCY_JS = JsCode("""
function(params) {
    if (params.value == null || params.value === \'\') return \'-\';
    return \'$\' + parseFloat(params.value).toLocaleString(\'en-US\',
        {minimumFractionDigits:2, maximumFractionDigits:2});
}
""")


def _bucket(age, outstanding):
    if outstanding <= 0: return None
    if age <= 0:   return "Current"
    if age <= 30:  return "1-30 Days"
    if age <= 60:  return "31-60 Days"
    if age <= 90:  return "61-90 Days"
    return ">90 Days"


def _build_ageing(df, name_col, amount_col, paid_col, due_col):
    df = df.copy()
    df[amount_col] = pd.to_numeric(df[amount_col], errors="coerce").fillna(0)
    df[paid_col]   = pd.to_numeric(df[paid_col],   errors="coerce").fillna(0)
    df[due_col]    = pd.to_datetime(df[due_col],   errors="coerce")
    today = pd.Timestamp.today().normalize()
    df["Outstanding"]  = (df[amount_col] - df[paid_col]).round(2)
    df["Age (Days)"]   = (today - df[due_col]).dt.days.fillna(0).astype(int)
    df["Bucket"]       = df.apply(lambda r: _bucket(r["Age (Days)"], r["Outstanding"]), axis=1)
    detail = df[df["Outstanding"] > 0].copy()
    rows = []
    for partner, grp in detail.groupby(name_col):
        row = {name_col: partner, "Total Outstanding": round(grp["Outstanding"].sum(), 2)}
        for b in BUCKET_COLS:
            row[b] = round(grp.loc[grp["Bucket"] == b, "Outstanding"].sum(), 2)
        rows.append(row)
    summary = pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=[name_col, "Total Outstanding"] + BUCKET_COLS)
    if not summary.empty:
        summary = summary.sort_values(">90 Days", ascending=False).reset_index(drop=True)
    return detail, summary


def _kpi_row(data):
    cols = st.columns(len(data))
    for col, (label, value, color) in zip(cols, data):
        with col:
            if isinstance(value, float) and value == int(value) and "Partners" in label or "Vendors" in label:
                display = str(int(value))
            elif isinstance(value, (int, float)):
                display = f"${value:,.2f}"
            else:
                display = str(value)
            st.markdown(
                f'''<div style="background:linear-gradient(135deg,{color}f0,{color}bb);
                border-radius:10px;padding:16px 18px;text-align:center;color:white;
                box-shadow:0 3px 10px rgba(0,0,0,.15);min-height:80px;
                display:flex;flex-direction:column;justify-content:center;">
                <div style="font-size:11px;font-weight:600;opacity:.85;text-transform:uppercase;
                            letter-spacing:.5px;margin-bottom:6px;">{label}</div>
                <div style="font-size:20px;font-weight:800;letter-spacing:-.5px;">{display}</div>
                </div>''', unsafe_allow_html=True)


def _bar_chart(summary_df, name_col, title):
    try:
        import plotly.graph_objects as go
    except ImportError:
        st.info("Install plotly to see charts: pip install plotly")
        return
    if summary_df.empty: return
    fig = go.Figure()
    for bucket, color in zip(BUCKET_COLS, BUCKET_COLORS):
        if bucket not in summary_df.columns: continue
        fig.add_trace(go.Bar(
            name=bucket, x=summary_df[name_col], y=summary_df[bucket],
            marker_color=color,
            hovertemplate=f"<b>%{{x}}</b><br>{bucket}: $%{{y:,.2f}}<extra></extra>",
        ))
    fig.update_layout(
        barmode="stack",
        title=dict(text=title, font=dict(size=13, color="#003366")),
        xaxis=dict(tickangle=-35, tickfont=dict(size=10)),
        yaxis=dict(tickprefix="$", tickformat=",.0f"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=10, r=10, t=60, b=90), height=330,
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
    st.plotly_chart(fig, use_container_width=True,
                    config={"displayModeBar": False})


def _donut(summary_df, title):
    try:
        import plotly.graph_objects as go
    except ImportError:
        return
    if summary_df.empty: return
    pairs = [(b, summary_df[b].sum()) for b in BUCKET_COLS
             if b in summary_df.columns and summary_df[b].sum() > 0]
    if not pairs: return
    labels, values = zip(*pairs)
    colors = [BUCKET_COLORS[BUCKET_COLS.index(l)] for l in labels]
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.55,
        marker=dict(colors=colors, line=dict(color="white", width=2)),
        textinfo="percent",
        hovertemplate="<b>%{label}</b><br>$%{value:,.2f}<extra></extra>",
    ))
    fig.add_annotation(
        text=f"<b>${sum(values):,.0f}</b>",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=12, color="#003366"), xanchor="center"
    )
    fig.update_layout(
        title=dict(text=title, font=dict(size=13, color="#003366")),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
        margin=dict(l=10, r=10, t=50, b=10),
        height=295, plot_bgcolor="white", paper_bgcolor="white",
    )
    st.plotly_chart(fig, use_container_width=True,
                    config={"displayModeBar": False})


def _summary_grid(df, name_col, height=380):
    if df.empty:
        st.info("No outstanding balances found.")
        return None
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_column(name_col, pinned="left", flex=1.6, minWidth=130)
    for col in ["Total Outstanding"] + BUCKET_COLS:
        if col not in df.columns: continue
        bg = BUCKET_BG.get(col, "")
        gb.configure_column(
            col, type=["numericColumn"], valueFormatter=CURRENCY_JS,
            flex=1, minWidth=95,
            cellStyle=JsCode(f"""
                function(p) {{
                    if (p.node.rowPinned)
                        return {{backgroundColor:"#003366",color:"white",fontWeight:"bold"}};
                    var s = {{backgroundColor:"{bg}", fontWeight:"600"}};
                    if (p.colDef.field === ">90 Days" && p.value > 0) s.color = "#B71C1C";
                    return s;
                }}
            """)
        )
    gb.configure_default_column(resizable=True, sortable=True, filter=False)
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    total_row = {name_col: "Grand Total"}
    for col in ["Total Outstanding"] + BUCKET_COLS:
        if col in df.columns:
            total_row[col] = round(df[col].sum(), 2)
    opts = gb.build()
    opts["pinnedBottomRowData"] = [total_row]
    opts["getRowStyle"] = JsCode("""
        function(p) {
            if (p.node.rowPinned)
                return {backgroundColor:"#003366",color:"white",fontWeight:"bold",fontSize:"13px"};
        }
    """)
    opts["onGridReady"] = JsCode("function(p){p.api.sizeColumnsToFit();}")
    return AgGrid(
        df, gridOptions=opts, allow_unsafe_jscode=True,
        fit_columns_on_grid_load=True, height=height,
        custom_css=HEADER_CSS, update_mode=GridUpdateMode.SELECTION_CHANGED,
        enable_enterprise_modules=False,
    )


def _drilldown(detail_df, partner, name_col, amount_col, paid_col, due_col):
    rows = detail_df[detail_df[name_col] == partner].copy()
    if rows.empty: return
    show_cols = [c for c in ["Month", due_col, amount_col, paid_col,
                              "Outstanding", "Age (Days)", "Bucket"] if c in rows.columns]
    show = rows[show_cols].copy()
    if "Month" in show.columns:
        show["Month"] = pd.to_datetime(show["Month"], errors="coerce").dt.strftime("%b-%Y")
    if due_col in show.columns:
        show[due_col] = pd.to_datetime(show[due_col], errors="coerce").dt.strftime("%d-%b-%Y")
    gb = GridOptionsBuilder.from_dataframe(show)
    for col in [amount_col, paid_col, "Outstanding"]:
        if col in show.columns:
            gb.configure_column(col, type=["numericColumn"],
                                valueFormatter=CURRENCY_JS, flex=1, minWidth=110)
    if "Bucket" in show.columns:
        gb.configure_column("Bucket", flex=1, minWidth=95, cellStyle=JsCode("""
            function(p) {
                var m = {"Current":"#E8F5E9","1-30 Days":"#FFF8E1",
                         "31-60 Days":"#FFF3E0","61-90 Days":"#FFEBEE",">90 Days":"#FFCDD2"};
                return {backgroundColor:m[p.value]||"",fontWeight:"600"};
            }
        """))
    gb.configure_column("Age (Days)", flex=0.7, minWidth=80)
    gb.configure_default_column(resizable=True, sortable=True, flex=1, minWidth=90)
    opts = gb.build()
    opts["onGridReady"] = JsCode("function(p){p.api.sizeColumnsToFit();}")
    AgGrid(show, gridOptions=opts, allow_unsafe_jscode=True,
           fit_columns_on_grid_load=True,
           height=min(60 + len(show) * 42, 360),
           custom_css=HEADER_CSS, enable_enterprise_modules=False)


def _gen_fy_list():
    today = pd.Timestamp.today()
    start = today.year if today.month >= 4 else today.year - 1
    return [f"FY {y}-{str(y+1)[2:]}" for y in range(start, start - 5, -1)]


def _fy_range(fy_str):
    y = int(fy_str.replace("FY ", "").split("-")[0])
    return pd.Timestamp(year=y, month=4, day=1), pd.Timestamp(year=y+1, month=3, day=31)


def _render_ar(dsp_df):
    if dsp_df is None or dsp_df.empty:
        st.warning("No DSP data available. Please load Master Data first.")
        return
    try:
        detail, summary = _build_ageing(
            dsp_df, "DSP Name", "Receivable $", "Received Amount $", "Due Date")
    except Exception as e:
        st.error(f"Error building AR ageing: {e}")
        return
    if summary.empty:
        st.success("All DSP receivables collected — no outstanding AR!")
        return
    total_os = summary["Total Outstanding"].sum()
    current  = summary["Current"].sum()
    overdue  = total_os - current
    worst    = summary[">90 Days"].sum()
    partners = int(summary["DSP Name"].nunique())
    _kpi_row([
        ("Total AR Outstanding",  total_os,  "#003366"),
        ("Current (Not Yet Due)", current,   "#2e7d32"),
        ("Total Overdue",         overdue,   "#e65100"),
        (">90 Days Critical",     worst,     "#b71c1c"),
        ("Partners with Balance", partners,  "#1565c0"),
    ])
    st.markdown("<br>", unsafe_allow_html=True)
    ch1, ch2 = st.columns([2, 1])
    with ch1:
        _bar_chart(summary, "DSP Name", "AR Outstanding by Partner & Ageing Bucket")
    with ch2:
        _donut(summary, "AR Bucket Distribution")
    st.divider()
    st.markdown("#### AR Ageing Summary by Partner")
    st.caption("Click any row to see month-level breakdown below.")
    resp = _summary_grid(summary, "DSP Name")
    if resp is not None:
        sel = resp.get("selected_rows")
        if sel is not None and len(sel) > 0:
            if isinstance(sel, pd.DataFrame):
                sel = sel.to_dict("records")
            partner = sel[0].get("DSP Name", "")
            if partner and partner != "Grand Total":
                st.markdown(f"---\n#### Month Detail — {partner}")
                _drilldown(detail, partner, "DSP Name",
                           "Receivable $", "Received Amount $", "Due Date")


def _render_ap(ssp_df):
    if ssp_df is None or ssp_df.empty:
        st.warning("No SSP data available. Please load Master Data first.")
        return
    try:
        detail, summary = _build_ageing(
            ssp_df, "SSP Name", "Payable $", "Paid Amount $", "Due Date")
    except Exception as e:
        st.error(f"Error building AP ageing: {e}")
        return
    if summary.empty:
        st.success("All SSP payables paid — no outstanding AP!")
        return
    total_os = summary["Total Outstanding"].sum()
    current  = summary["Current"].sum()
    overdue  = total_os - current
    worst    = summary[">90 Days"].sum()
    vendors  = int(summary["SSP Name"].nunique())
    _kpi_row([
        ("Total AP Outstanding",  total_os, "#003366"),
        ("Current (Not Yet Due)", current,  "#2e7d32"),
        ("Total Overdue",         overdue,  "#e65100"),
        (">90 Days Critical",     worst,    "#b71c1c"),
        ("Vendors with Balance",  vendors,  "#1565c0"),
    ])
    st.markdown("<br>", unsafe_allow_html=True)
    ch1, ch2 = st.columns([2, 1])
    with ch1:
        _bar_chart(summary, "SSP Name", "AP Outstanding by Vendor & Ageing Bucket")
    with ch2:
        _donut(summary, "AP Bucket Distribution")
    st.divider()
    st.markdown("#### AP Ageing Summary by Vendor")
    st.caption("Click any row to see month-level breakdown below.")
    resp = _summary_grid(summary, "SSP Name")
    if resp is not None:
        sel = resp.get("selected_rows")
        if sel is not None and len(sel) > 0:
            if isinstance(sel, pd.DataFrame):
                sel = sel.to_dict("records")
            vendor = sel[0].get("SSP Name", "")
            if vendor and vendor != "Grand Total":
                st.markdown(f"---\n#### Month Detail — {vendor}")
                _drilldown(detail, vendor, "SSP Name",
                           "Payable $", "Paid Amount $", "Due Date")


def render_ageing_tab(dsp_df, ssp_df):
    try:
        st.markdown('''
            <div style="background:linear-gradient(135deg,#003366 0%,#005599 100%);
            border-radius:10px;padding:18px 24px;margin-bottom:20px;
            box-shadow:0 4px 16px rgba(0,51,102,.2);
            display:flex;align-items:center;height:55px;gap:14px;">
            <div style="font-size:32px;">📈</div>
            <div>
                <div style="color:white;font-size:20px;font-weight:800;">
                    AR / AP Ageing Analysis</div>
                <div style="color:#90caf9;font-size:12px;margin-top:3px;">
                    Accounts Receivable — DSP Customers &nbsp;|&nbsp;
                    Accounts Payable — SSP Vendors</div>
            </div></div>
        ''', unsafe_allow_html=True)
        
        view = st.radio(
            "view", ["AR Ageing — DSP (Customers)", "AP Ageing — SSP (Vendors)"],
            horizontal=True, label_visibility="collapsed", key="ageing_view_radio",
        )

        fy_list = _gen_fy_list()
        fc1, fc2, fc3, fc4 = st.columns([1.2, 1, 1, 1.5])

        is_ar = "AR" in view
        src = (dsp_df if is_ar else ssp_df)
        if src is None: src = pd.DataFrame()
        src = src.copy()
        name_col = "DSP Name" if is_ar else "SSP Name"

        src["_mdt"] = pd.to_datetime(
            src["Month"] if "Month" in src.columns else pd.Series(dtype=str),
            errors="coerce")

        with fc1:
            sel_fy = st.selectbox("Financial Year", ["All"] + fy_list, key="age_fy")
        with fc2:
            month_opts = ["All"] + sorted(
                src["_mdt"].dropna().dt.strftime("%b-%Y").unique().tolist(),
                key=lambda m: pd.to_datetime(m, format="%b-%Y", errors="coerce"))
            sel_month = st.selectbox("Month", month_opts, key="age_month")
        with fc3:
            p_opts = ["All"] + sorted(src[name_col].dropna().unique().tolist()) \
                if name_col in src.columns else ["All"]
            sel_partner = st.selectbox(name_col, p_opts, key="age_partner")
        with fc4:
            search = st.text_input("Search", placeholder="Filter...", key="age_search")

        filtered = src.copy()
        if sel_fy != "All":
            s, e = _fy_range(sel_fy)
            filtered = filtered[(filtered["_mdt"] >= s) & (filtered["_mdt"] <= e)]
        if sel_month != "All":
            filtered = filtered[filtered["_mdt"].dt.strftime("%b-%Y") == sel_month]
        if sel_partner != "All" and name_col in filtered.columns:
            filtered = filtered[filtered[name_col] == sel_partner]
        if search and not filtered.empty:
            mask = filtered.apply(
                lambda r: search.lower() in " ".join(r.astype(str).str.lower()), axis=1)
            filtered = filtered[mask]
        filtered = filtered.drop(columns=["_mdt"], errors="ignore")

        st.divider()

        if is_ar:
            _render_ar(filtered)
        else:
            _render_ap(filtered)

    except Exception as exc:
        import traceback
        st.error(f"Ageing tab error: {exc}")
        st.code(traceback.format_exc())
