"""
responsive.py  —  PEAKADS LLP
==============================
Responsive design system for the Revenue Tracker Streamlit app.

HOW IT WORKS
────────────
1. detect_screen()     → injects a zero-height JS iframe that reads window.innerWidth /
                         window.innerHeight and writes them to st.session_state via a
                         hidden Streamlit number_input widget. Triggers one st.rerun()
                         on first load so Python immediately knows the real screen size.

2. get_screen_config() → reads session state, returns a ScreenConfig dataclass with
                         helpers like .grid_height(base), .font_scale, .is_mobile, etc.

3. inject_responsive_css() → injects a complete CSS stylesheet with @media queries and
                              clamp() rules covering all 4 breakpoints.

USAGE (2 lines in app.py)
──────────────────────────
    from responsive import detect_screen, get_screen_config, inject_responsive_css
    detect_screen()
    inject_responsive_css()
    sc = get_screen_config()

    # Then use sc wherever you have a hardcoded height or size:
    AgGrid(..., height=sc.grid_height(650))
    AgGrid(..., height=sc.grid_height(700))

BREAKPOINTS
───────────
    Mobile  : < 768 px   (phones, small tablets in portrait)
    Tablet  : 768–1199   (tablets, 13" laptops, portrait iPads)
    Desktop : 1200–1919  (14"–27" monitors, normal laptops)
    Large   : ≥ 1920 px  (32"+ monitors, external 4K displays)
"""

from __future__ import annotations
import streamlit as st
import streamlit.components.v1 as components
from dataclasses import dataclass


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

BP_MOBILE  = 768
BP_TABLET  = 1200
BP_DESKTOP = 1920

# Grid height multipliers per breakpoint
_GRID_SCALE = {
    "mobile" : 0.55,   # phones — short tables so content fits without scroll wars
    "tablet" : 0.78,   # 13" laptop / tablet
    "desktop": 1.00,   # reference (your current hardcoded values)
    "large"  : 1.18,   # 32"+ monitors — more rows visible
}

# Font scale multipliers (applied to base CSS values via CSS vars)
_FONT_SCALE = {
    "mobile" : 0.88,
    "tablet" : 0.94,
    "desktop": 1.00,
    "large"  : 1.08,
}

# Navbar widths per breakpoint
_NAVBAR = {
    "mobile" : (0,   0),    # hidden collapsed; overlay toggle instead
    "tablet" : (36, 190),   # slightly narrower
    "desktop": (46, 220),   # original values
    "large"  : (52, 240),   # slightly wider for 32"
}


# ─────────────────────────────────────────────────────────────────────────────
# ScreenConfig dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ScreenConfig:
    screen_w   : int
    screen_h   : int
    breakpoint : str      # "mobile" | "tablet" | "desktop" | "large"

    # ── derived helpers ──────────────────────────────────────────────────────

    @property
    def is_mobile(self) -> bool:
        return self.breakpoint == "mobile"

    @property
    def is_tablet(self) -> bool:
        return self.breakpoint == "tablet"

    @property
    def is_desktop(self) -> bool:
        return self.breakpoint == "desktop"

    @property
    def is_large(self) -> bool:
        return self.breakpoint == "large"

    @property
    def font_scale(self) -> float:
        return _FONT_SCALE[self.breakpoint]

    @property
    def navbar_cw(self) -> int:
        """Collapsed navbar width (px)."""
        return _NAVBAR[self.breakpoint][0]

    @property
    def navbar_ew(self) -> int:
        """Expanded navbar width (px)."""
        return _NAVBAR[self.breakpoint][1]

    def grid_height(self, base: int = 650) -> int:
        """
        Scale a base AgGrid height to the current screen size.
        Also caps at a sensible fraction of screen height so the table
        never pushes content off-screen.
        """
        scale   = _GRID_SCALE[self.breakpoint]
        scaled  = int(base * scale)
        # never taller than 72% of viewport height
        max_h   = int(self.screen_h * 0.72) if self.screen_h > 0 else scaled
        return min(scaled, max_h)

    @property
    def block_padding(self) -> str:
        """CSS padding for .block-container left/right."""
        return {
            "mobile" : "6px",
            "tablet" : "10px",
            "desktop": "15px",
            "large"  : "22px",
        }[self.breakpoint]

    @property
    def card_padding(self) -> str:
        """Padding for .kpi-container cards."""
        return {
            "mobile" : "10px",
            "tablet" : "16px",
            "desktop": "25px",
            "large"  : "32px",
        }[self.breakpoint]


# ─────────────────────────────────────────────────────────────────────────────
# Screen detection (JS → session_state bridge)
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# Screen detection (JS → st.query_params bridge — ZERO visible widgets)
# ─────────────────────────────────────────────────────────────────────────────

def detect_screen() -> None:
    """
    Call once near the top of app.py (after st.set_page_config).

    Strategy: JS reads window.innerWidth / innerHeight from the parent
    frame and writes them as URL query params (?_sw=1280&_sh=800) via
    history.replaceState — invisible to the user, no browser history entry.
    Python reads them from st.query_params on every run.

    On the very first run (params not set yet) a st.rerun() is queued
    so Python immediately knows real dimensions before rendering content.
    No number_input, no visible widgets, no layout artifacts.
    """

    # Read current values from query params (set by JS on previous run)
    try:
        sw_qp = int(st.query_params.get("_sw", 0))
        sh_qp = int(st.query_params.get("_sh", 0))
    except Exception:
        sw_qp, sh_qp = 0, 0

    # Persist into session_state so the rest of the app can read them
    if sw_qp > 0:
        st.session_state["_pak_screen_w"] = sw_qp
        st.session_state["_pak_screen_h"] = sh_qp

    # JS bridge — reads viewport size and writes to URL query params
    # Uses history.replaceState so no browser history entry is created
    bridge_js = """
<html><head><meta charset='utf-8'></head>
<body style='margin:0;padding:0;overflow:hidden;'>
<script>
(function(){
  try {
    var P  = window.parent;
    var w  = P.innerWidth  || P.document.documentElement.clientWidth  || 1280;
    var h  = P.innerHeight || P.document.documentElement.clientHeight || 800;
    var qs = P.location.search;

    /* Parse existing params so we don't clobber unrelated ones */
    var params = new URLSearchParams(qs);
    var oldW   = params.get('_sw');
    var oldH   = params.get('_sh');

    /* Only update + trigger rerun if values have changed */
    if(String(oldW) !== String(w) || String(oldH) !== String(h)){
      params.set('_sw', w);
      params.set('_sh', h);
      var newSearch = '?' + params.toString();
      P.history.replaceState(null, '', newSearch);

      /* Trigger Streamlit rerun by dispatching a popstate-like event.
         Streamlit listens to URL changes via its own router. */
      setTimeout(function(){
        P.dispatchEvent(new PopStateEvent('popstate', { state: null }));
      }, 60);
    }
  } catch(e) { /* cross-origin guard */ }
})();
</script>
</body></html>"""

    components.html(bridge_js, height=0, scrolling=False)

    # First run: query params haven't been set yet — force a rerun
    sw_ss = st.session_state.get("_pak_screen_w", 0)
    if sw_ss == 0 and not st.session_state.get("_pak_detect_done"):
        st.session_state["_pak_detect_done"] = True
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# get_screen_config
# ─────────────────────────────────────────────────────────────────────────────

def get_screen_config() -> ScreenConfig:
    """
    Returns a ScreenConfig based on the detected (or default) screen size.
    Safe to call multiple times — reads from session_state.
    """
    sw = int(st.session_state.get("_pak_screen_w") or 0)
    sh = int(st.session_state.get("_pak_screen_h") or 0)

    # Fallback if detection hasn't fired yet
    if sw == 0:
        sw, sh = 1280, 800

    if sw < BP_MOBILE:
        bp = "mobile"
    elif sw < BP_TABLET:
        bp = "tablet"
    elif sw < BP_DESKTOP:
        bp = "desktop"
    else:
        bp = "large"

    return ScreenConfig(screen_w=sw, screen_h=sh, breakpoint=bp)


# ─────────────────────────────────────────────────────────────────────────────
# inject_responsive_css
# ─────────────────────────────────────────────────────────────────────────────

def inject_responsive_css(sc: ScreenConfig | None = None) -> None:
    """
    Injects a comprehensive responsive CSS stylesheet.
    Combines @media queries (for pure CSS properties) with Python-computed
    values (from sc) so both static and dynamic sizes are handled.

    Call after st.set_page_config(), ideally right after detect_screen().
    """
    if sc is None:
        sc = get_screen_config()

    cw = sc.navbar_cw
    ew = sc.navbar_ew

    # Python-computed values injected directly into :root CSS variables
    root_vars = f"""
:root {{
  --pak-nav-cw         : {cw}px;
  --pak-nav-ew         : {ew}px;
  --pak-block-pad      : {sc.block_padding};
  --pak-card-pad       : {sc.card_padding};
  --pak-font-scale     : {sc.font_scale};
  --pak-base-font      : {round(12.5 * sc.font_scale, 1)}px;
  --pak-tab-font       : {round(12.5 * sc.font_scale, 1)}px;
  --pak-btn-font       : {round(12.5 * sc.font_scale, 1)}px;
  --pak-label-font     : {round(13.0 * sc.font_scale, 1)}px;
  --pak-header-font    : {round(13.5 * sc.font_scale, 1)}px;
  --pak-btn-pad-v      : {round(6  * sc.font_scale, 1)}px;
  --pak-btn-pad-h      : {round(15 * sc.font_scale, 1)}px;
  --pak-tab-pad-v      : {round(6  * sc.font_scale, 1)}px;
  --pak-tab-pad-h      : {round(13 * sc.font_scale, 1)}px;
}}"""

    # Full responsive stylesheet
    css = root_vars + """

/* ═══════════════════════════════════════════════════════════════
   RESPONSIVE LAYOUT — content area adapts to navbar width
   ═══════════════════════════════════════════════════════════════ */

[data-testid='stMain'] {
    margin-left  : var(--pak-nav-cw)  !important;
    width        : calc(100vw - var(--pak-nav-cw))  !important;
    max-width    : calc(100vw - var(--pak-nav-cw))  !important;
    min-width    : 0 !important;
    box-sizing   : border-box !important;
    transition   : margin-left .28s cubic-bezier(.4,0,.2,1),
                   width       .28s cubic-bezier(.4,0,.2,1);
}
body:has(#pak-sb:hover) [data-testid='stMain'] {
    margin-left  : var(--pak-nav-ew)  !important;
    width        : calc(100vw - var(--pak-nav-ew))  !important;
    max-width    : calc(100vw - var(--pak-nav-ew))  !important;
}
[data-testid='stMain'] .block-container {
    max-width    : 100% !important;
    padding-left : var(--pak-block-pad) !important;
    padding-right: var(--pak-block-pad) !important;
    box-sizing   : border-box !important;
}

/* ═══════════════════════════════════════════════════════════════
   RESPONSIVE TYPOGRAPHY — tabs, buttons, labels
   ═══════════════════════════════════════════════════════════════ */

/* Tab bar */
div[data-testid="stTabs"] button[role="tab"] {
    font-size : var(--pak-tab-font)   !important;
    padding   : var(--pak-tab-pad-v) var(--pak-tab-pad-h) !important;
}
div[data-testid="stTabs"] button[role="tab"] p {
    font-size : var(--pak-header-font) !important;
}

/* All Streamlit buttons */
div.stButton > button,
div.stDownloadButton > button {
    font-size : var(--pak-btn-font)   !important;
    padding   : var(--pak-btn-pad-v) var(--pak-btn-pad-h) !important;
}
div.stButton > button p,
div.stDownloadButton > button p {
    font-size : inherit !important;
}

/* Selectbox, text inputs, labels */
div[data-testid="stSelectbox"] label,
div[data-testid="stTextInput"] label,
div[data-testid="stDateInput"] label,
div[data-testid="stMultiSelect"] label,
div[data-testid="stNumberInput"] label {
    font-size : var(--pak-label-font) !important;
}
div[data-testid="stSelectbox"] > div > div,
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input {
    font-size : var(--pak-base-font) !important;
}

/* Metric values */
div[data-testid="stMetric"] label {
    font-size : var(--pak-base-font) !important;
}
div[data-testid="stMetricValue"] {
    font-size : clamp(14px, 1.4vw, 28px) !important;
}

/* ═══════════════════════════════════════════════════════════════
   KPI CARDS — uniform height, responsive font
   ═══════════════════════════════════════════════════════════════ */

/* Force all KPI columns in a row to stretch to equal height */
[data-testid="stHorizontalBlock"]:has(.pak-kpi-card) {
    align-items: stretch !important;
}
[data-testid="stHorizontalBlock"]:has(.pak-kpi-card)
    > [data-testid="stVerticalBlockBorderWrapper"] {
    display       : flex !important;
    flex-direction: column !important;
}
[data-testid="stHorizontalBlock"]:has(.pak-kpi-card)
    > [data-testid="stVerticalBlockBorderWrapper"]
    > div {
    flex: 1 !important;
    display: flex !important;
    flex-direction: column !important;
}

.pak-kpi-card {
    padding       : clamp(10px, 1.2vw, 20px) clamp(10px, 1.4vw, 20px);
    border-radius : 14px;
    box-shadow    : 0 6px 20px rgba(0,0,0,0.22);
    margin-bottom : 8px;
    height        : 100%;
    min-height    : 88px;
    display       : flex;
    flex-direction: column;
    justify-content: center;
    box-sizing    : border-box;
}
.pak-kpi-title {
    font-size     : clamp(9px, 0.75vw, 12px);
    font-weight   : 700;
    color         : #FFEF00;
    text-transform: uppercase;
    letter-spacing: .6px;
    line-height   : 1.3;
}
.pak-kpi-value {
    font-size     : clamp(15px, 1.6vw, 28px);
    font-weight   : 900;
    color         : #fff;
    margin-top    : 4px;
    letter-spacing: -0.5px;
    line-height   : 1.15;
    word-break    : break-all;
}



/* AgGrid cell text — scales with viewport */
.ag-cell, .ag-header-cell-text {
    font-size : clamp(10px, 0.75vw, 13px) !important;
}

/* ═══════════════════════════════════════════════════════════════
   MOBILE  (< 768px) — compact everything
   ═══════════════════════════════════════════════════════════════ */
@media (max-width: 767px) {

    /* Navbar collapses to zero width — tap icon to open */
    [data-testid='stMain'] {
        margin-left  : 0 !important;
        width        : 100vw !important;
        max-width    : 100vw !important;
    }
    body:has(#pak-sb:hover) [data-testid='stMain'] {
        margin-left  : 190px !important;
        width        : calc(100vw - 190px) !important;
        max-width    : calc(100vw - 190px) !important;
    }

    /* Touch-friendly buttons — min 44px tap target */
    div.stButton > button,
    div.stDownloadButton > button {
        min-height    : 44px !important;
        padding       : 10px 12px !important;
        font-size     : 11px !important;
        border-radius : 8px  !important;
        width         : 100% !important;
        white-space   : normal !important;
        word-break    : break-word !important;
        line-height   : 1.3 !important;
    }

    /* Tabs — smaller, scrollable */
    div[data-testid="stTabs"] button[role="tab"] {
        font-size : 10px !important;
        padding   : 5px 7px !important;
        min-width : 0 !important;
        white-space: nowrap !important;
    }
    div[data-baseweb="tab-list"] {
        gap         : 2px !important;
        padding     : 4px 4px !important;
        overflow-x  : auto !important;
        flex-wrap   : nowrap !important;
        -webkit-overflow-scrolling: touch !important;
    }

    /* KPI cards — 2 per row on mobile */
    [data-testid="stHorizontalBlock"]:has(.pak-kpi-card) {
        flex-wrap : wrap !important;
    }
    [data-testid="stHorizontalBlock"]:has(.pak-kpi-card)
        > [data-testid="stVerticalBlockBorderWrapper"] {
        width   : calc(50% - 4px) !important;
        flex    : none !important;
        min-width: 0 !important;
    }
    .pak-kpi-card {
        min-height : 70px !important;
    }
    .pak-kpi-value {
        font-size  : clamp(14px, 4.5vw, 20px) !important;
    }
    .pak-kpi-title {
        font-size  : 9px !important;
    }

    /* Stack ALL other columns vertically */
    [data-testid="stHorizontalBlock"]:not(:has(.pak-kpi-card)) {
        flex-direction: column !important;
    }
    [data-testid="stHorizontalBlock"]:not(:has(.pak-kpi-card))
        > [data-testid="stVerticalBlockBorderWrapper"] {
        width   : 100% !important;
        flex    : none !important;
    }

    /* Hide invoice subnav on mobile — too small to use */
    #inv-sidenav {
        display: none !important;
    }

    /* Metric value — smaller on phones */
    div[data-testid="stMetricValue"] {
        font-size : 16px !important;
    }

    /* Block container padding */
    .block-container {
        padding-left : 6px  !important;
        padding-right: 6px  !important;
        padding-top  : 4px  !important;
    }

    /* AgGrid — allow horizontal scroll on mobile */
    .ag-root-wrapper {
        overflow-x : auto !important;
        -webkit-overflow-scrolling: touch !important;
    }

    /* ── Wide multi-column tables (P&L, Costs Centre) — horizontal scroll ── */
    /* Wrap the stMarkdown/block-container so the TABLE can be wider than viewport */
    .block-container [data-testid="stMarkdownContainer"],
    [data-testid="stMarkdownContainer"] {
        overflow-x : auto !important;
        -webkit-overflow-scrolling: touch !important;
        max-width  : calc(100vw - 12px) !important;
    }
    /* HTML tables inside markdown: don't squish, let them scroll */
    .stMarkdown table,
    [data-testid="stMarkdownContainer"] table {
        width      : max-content !important;
        min-width  : 100% !important;
        font-size  : 10px !important;
    }
    .stMarkdown table th,
    .stMarkdown table td,
    [data-testid="stMarkdownContainer"] table th,
    [data-testid="stMarkdownContainer"] table td {
        min-width  : 52px !important;
        max-width  : 110px !important;
        white-space: nowrap !important;
        padding    : 3px 5px !important;
        font-size  : 10px !important;
        overflow   : hidden !important;
        text-overflow: ellipsis !important;
    }
    /* AgGrid: enforce minimum column width so text isn't squished to 2 chars */
    .ag-header-cell {
        min-width  : 65px !important;
    }
    .ag-cell {
        min-width  : 55px !important;
        font-size  : 10.5px !important;
    }
    /* AgGrid iframe wrapper — allow horizontal scroll */
    [data-testid="stCustomComponentV1"],
    iframe[title*="st_aggrid"],
    iframe[title*="AgGrid"] {
        overflow-x : auto !important;
        width      : 100% !important;
        max-width  : calc(100vw - 12px) !important;
    }

    /* Selectbox & multiselect full width */
    div[data-testid="stSelectbox"],
    div[data-testid="stMultiSelect"],
    div[data-testid="stDateInput"],
    div[data-testid="stTextInput"] {
        width: 100% !important;
    }
}

/* ═══════════════════════════════════════════════════════════════
   TABLET  (768px – 1199px) — balanced scaling
   ═══════════════════════════════════════════════════════════════ */
@media (min-width: 768px) and (max-width: 1199px) {

    div.stButton > button,
    div.stDownloadButton > button {
        min-height    : 38px !important;
        font-size     : 11px !important;
        padding       : 6px 10px !important;
        white-space   : normal !important;
        word-break    : break-word !important;
        line-height   : 1.3 !important;
    }

    div[data-testid="stTabs"] button[role="tab"] {
        font-size : 11px !important;
        padding   : 5px 9px !important;
    }

    div[data-testid="stMetricValue"] {
        font-size : clamp(14px, 1.6vw, 22px) !important;
    }

    .block-container {
        padding-left : 10px !important;
        padding-right: 10px !important;
    }

    /* KPI cards — 3 per row on tablet (6-col row wraps to 2 rows of 3) */
    [data-testid="stHorizontalBlock"]:has(.pak-kpi-card)
        > [data-testid="stVerticalBlockBorderWrapper"] {
        min-width : calc(33.33% - 8px) !important;
        flex      : 1 1 calc(33.33% - 8px) !important;
    }
    .pak-kpi-value {
        font-size : clamp(13px, 1.5vw, 22px) !important;
    }
    .pak-kpi-title {
        font-size : clamp(8px, 0.8vw, 11px) !important;
    }

    /* Invoice subnav — slightly smaller on tablet */
    .inv-snav-btn {
        font-size  : 11px !important;
        padding    : 6px 10px !important;
    }
    .inv-snav-handle {
        width      : 8px !important;
        min-height : 140px !important;
    }
}

/* ═══════════════════════════════════════════════════════════════
   DESKTOP  (1200px – 1919px) — original / reference sizes
   ═══════════════════════════════════════════════════════════════ */
@media (min-width: 1200px) and (max-width: 1919px) {
    div[data-testid="stMetricValue"] {
        font-size : clamp(18px, 1.4vw, 28px) !important;
    }

    /* On smaller desktop monitors, buttons may wrap — allow graceful wrap */
    div.stButton > button,
    div.stDownloadButton > button {
        white-space   : normal !important;
        word-break    : break-word !important;
        line-height   : 1.3 !important;
        min-height    : 36px !important;
    }

    /* KPI value clips on narrow columns — let it shrink */
    .pak-kpi-value {
        font-size : clamp(14px, 1.5vw, 28px) !important;
    }
    .pak-kpi-title {
        font-size : clamp(9px, 0.7vw, 12px) !important;
    }
}

/* ═══════════════════════════════════════════════════════════════
   LARGE  (≥ 1920px) — 32"+ monitors, scale UP
   ═══════════════════════════════════════════════════════════════ */
@media (min-width: 1920px) {

    div.stButton > button,
    div.stDownloadButton > button {
        font-size  : 14px   !important;
        padding    : 8px 18px !important;
    }

    div[data-testid="stTabs"] button[role="tab"] {
        font-size : 14px   !important;
        padding   : 8px 16px !important;
    }
    div[data-testid="stTabs"] button[role="tab"] p {
        font-size : 15px !important;
    }

    div[data-testid="stSelectbox"] label,
    div[data-testid="stTextInput"] label,
    div[data-testid="stDateInput"] label,
    div[data-testid="stMultiSelect"] label {
        font-size : 14px !important;
    }

    div[data-testid="stMetricValue"] {
        font-size : clamp(22px, 1.6vw, 36px) !important;
    }

    .block-container {
        padding-left : 22px !important;
        padding-right: 22px !important;
    }

    .ag-cell, .ag-header-cell-text {
        font-size : 13.5px !important;
    }

    /* Subnav bigger on 32" */
    .inv-snav-btn {
        font-size  : 14px !important;
        padding    : 10px 18px !important;
    }
    #inv-sidenav {
        font-size  : 14px !important;
    }
}

/* ═══════════════════════════════════════════════════════════════
   UNIVERSAL QUALITY-OF-LIFE FIXES
   ═══════════════════════════════════════════════════════════════ */

/* Prevent tables from looking broken on any screen */
.ag-root-wrapper {
    border-radius : 8px !important;
    overflow      : hidden !important;
}

/* Horizontal scroll container for wide tables on small screens */
.ag-body-horizontal-scroll {
    display : block !important;
}

/* Smooth font rendering */
html {
    -webkit-font-smoothing : antialiased !important;
    text-rendering         : optimizeLegibility !important;
}

/* Streamlit columns — let them wrap on narrow screens */
[data-testid="stHorizontalBlock"] {
    flex-wrap : wrap !important;
    gap       : 0.5rem !important;
}

/* Plotly charts — always fill container width */
.js-plotly-plot, .plotly, .stPlotlyChart {
    width      : 100% !important;
    max-width  : 100% !important;
}
.stPlotlyChart > div {
    width      : 100% !important;
}

/* Dataframe — horizontal scroll */
[data-testid="stDataFrame"] {
    width      : 100% !important;
    overflow-x : auto !important;
}
"""

    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Convenience: one-call setup
# ─────────────────────────────────────────────────────────────────────────────

def setup_responsive() -> ScreenConfig:
    """
    Call once after st.set_page_config().
    Runs detection + injects CSS + returns ScreenConfig.

    Usage:
        sc = setup_responsive()
        AgGrid(..., height=sc.grid_height(650))
    """
    detect_screen()
    sc = get_screen_config()
    inject_responsive_css(sc)
    return sc
