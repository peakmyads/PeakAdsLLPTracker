"""
navbar.py  —  PEAKADS LLP
Vertical hover-expand LEFT sidebar navbar for Streamlit.

LAYOUT
──────
• Collapsed (46px) : overlays left edge, content = full 100vw - 46px, scrollbar visible
• Hovered  (220px) : content shifts right, width = 100vw - 220px
• Tab icons shown only when collapsed, hidden when expanded
• Native horizontal tab bar fully hidden (CSS + JS double-kill)

INTEGRATION
───────────
  from navbar import render_navbar
  render_navbar()          ← just before st.tabs(...)

CHANGELOG
─────────
• Logout fix  : A real Streamlit "Logout" button is placed inside st.sidebar
                (already hidden by CSS). JS finds it by text and clicks it,
                which triggers the Python session-clear + st.rerun().
• Logo        : peakads_logo.png loaded as base64 and shown in the header.
                Collapsed → logo icon only.  Expanded → logo + "PEAKADS LLP" text.
"""

import base64
import os
import streamlit as st
import streamlit.components.v1 as components
from login import get_allowed_tabs

# ── Logo loader ──────────────────────────────────────────────────────────────

def _get_logo_b64() -> str:
    """Return base64-encoded peakads_logo.png, or empty string if not found."""
    logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "peakads_logo.png")
    try:
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return ""


# ── Tab maps ─────────────────────────────────────────────────────────────────

TAB_MAP = {
    "Dashboard"       : "📊 Dashboard",
    "Ageing"          : "📈 AR/AP Ageing",
    "Master Data"     : "📁 Master Data",
    "DSP (Customers)" : "🧑 DSP (Customers)",
    "Invoice Manager" : "🧾 Invoice Manager",
    "SSP (Vendors)"   : "📤 SSP (Vendors)",
    "List of Partners": "🤝 List of Partners",
    "Costs Centre"    : "💰 Costs Centre",
    "P&L"             : "📉 P&L",
    "Admin Control"   : "⚙️ Admin Control Panel",
    "Edit Database"   : "🛠️ Edit Database",
}

TAB_ICONS = {
    "Dashboard"       : "📊",
    "Ageing"          : "📈",
    "Master Data"     : "📁",
    "DSP (Customers)" : "🧑",
    "Invoice Manager" : "🧾",
    "SSP (Vendors)"   : "📤",
    "List of Partners": "🤝",
    "Costs Centre"    : "💰",
    "P&L"             : "📉",
    "Admin Control"   : "⚙️",
    "Edit Database"   : "🛠️",
}

CW = 46   # collapsed width  (px)
EW = 220  # expanded width   (px)


def render_navbar() -> None:

    # ── 1. LOGOUT HOOK ───────────────────────────────────────────────────────
    # A real Streamlit "Logout" button is placed inside st.sidebar.
    # The sidebar div is hidden by the injected CSS, so users never see it,
    # but the button IS present in the DOM.  The JS sidebar logout button
    # searches `querySelectorAll('button')` for text "Logout" and clicks it,
    # which fires this Python handler → clears session → st.rerun().
    with st.sidebar:
        if st.button("Logout", key="_nb_sidebar_logout"):
            st.session_state.clear()
            st.rerun()

    # ── 2. BUILD DATA ────────────────────────────────────────────────────────
    allowed_tabs = get_allowed_tabs()
    if "Ageing" not in allowed_tabs:
        idx = (allowed_tabs.index("Dashboard") + 1
               if "Dashboard" in allowed_tabs else 1)
        allowed_tabs.insert(idx, "Ageing")

    username = st.session_state.get("user", "")
    role     = st.session_state.get("role", "")
    logo_b64 = _get_logo_b64()

    tab_js = ", ".join(
        '{{key:"{k}",label:"{l}",icon:"{i}"}}'.format(
            k=k.replace('"', '\\"'),
            l=TAB_MAP.get(k, k).replace('"', '\\"'),
            i=TAB_ICONS.get(k, "▸")
        )
        for k in allowed_tabs
    )
    user_str  = (username + " · " + role).replace('"', '\\"')
    logo_src  = ("data:image/png;base64," + logo_b64) if logo_b64 else ""
    cw, ew    = str(CW), str(EW)

    # ── 3. CSS ───────────────────────────────────────────────────────────────
    css = (
        # content area — collapsed
        "[data-testid='stMain']{"
        "margin-left:" + cw + "px!important;"
        "width:calc(100vw - " + cw + "px)!important;"
        "max-width:calc(100vw - " + cw + "px)!important;"
        "min-width:0!important;"
        "box-sizing:border-box!important;"
        "transition:margin-left .28s cubic-bezier(.4,0,.2,1),"
        "width .28s cubic-bezier(.4,0,.2,1);}"

        # content area — expanded
        "body:has(#pak-sb:hover) [data-testid='stMain']{"
        "margin-left:" + ew + "px!important;"
        "width:calc(100vw - " + ew + "px)!important;"
        "max-width:calc(100vw - " + ew + "px)!important;}"

        # inner block container
        "[data-testid='stMain'] .block-container{"
        "max-width:100%!important;"
        "padding-left:1rem!important;"
        "padding-right:1rem!important;"
        "box-sizing:border-box!important;}"

        # hide Streamlit chrome
        "header[data-testid='stHeader'],"
        "[data-testid='stToolbar'],"
        "[data-testid='stDecoration']{"
        "display:none!important;}"

        # hide sidebar visually but keep it in the DOM
        # (so the hidden Logout button JS can click it)
        "[data-testid='stSidebar']{"
        "display:none!important;"
        "visibility:hidden!important;"
        "pointer-events:none!important;"
        "position:absolute!important;"
        "left:-9999px!important;}"

        # hide native tab bar — every possible selector
        "[data-testid='stTabBar'],"
        "div[data-testid='stTabBar'],"
        ".stTabs [data-testid='stTabBar'],"
        "[data-baseweb='tab-list']{"
        "display:none!important;"
        "visibility:hidden!important;"
        "opacity:0!important;"
        "height:0!important;"
        "max-height:0!important;"
        "min-height:0!important;"
        "overflow:hidden!important;"
        "margin:0!important;"
        "padding:0!important;"
        "pointer-events:none!important;"
        "position:absolute!important;"
        "top:-9999px!important;}"

        # sidebar shell
        "#pak-sb{"
        "position:fixed;top:0;left:0;bottom:0;z-index:99999;"
        "width:" + cw + "px;overflow:hidden;"
        "background:linear-gradient(180deg,#0b1120 0%,#0e1a30 55%,#0a1422 100%);"
        "box-shadow:3px 0 24px rgba(0,0,0,.50);"
        "transition:width .28s cubic-bezier(.4,0,.2,1);"
        "display:flex;flex-direction:column;"
        "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;"
        "-webkit-font-smoothing:antialiased;}"
        "#pak-sb:hover{width:" + ew + "px;}"

        # logo area — vertical stack: logo on top, brand name below
        ".psb-logo{display:flex;flex-direction:column;align-items:center;"
        "justify-content:center;gap:5px;"
        "padding:14px 0 12px;"
        "border-bottom:1px solid rgba(255,255,255,.06);"
        "flex-shrink:0;min-width:" + ew + "px;}"

        # company logo image — always visible (collapsed + expanded), centred
        ".psb-logo-img{"
        "width:40px;height:40px;"
        "border-radius:8px;"
        "object-fit:contain;"
        "display:block;}"

        # fallback hamburger (shown only when no logo image)
        ".psb-ham{font-size:22px;color:#4a5e7a;cursor:default;"
        "user-select:none;"
        "transition:color .22s,transform .30s cubic-bezier(.4,0,.2,1);}"
        "#pak-sb:hover .psb-ham{color:#94a3b8;transform:rotate(90deg);}"

        # brand text — collapses to height 0 when sidebar is narrow, fades in below logo on expand
        ".psb-brand{font-size:14.5px;font-weight:800;color:#0076CE;letter-spacing:.9px;"
        "white-space:nowrap;text-align:center;"
        "opacity:0;max-height:0;overflow:hidden;"
        "transition:opacity .20s ease .06s,max-height .22s ease .06s;}"
        "#pak-sb:hover .psb-brand{opacity:1;max-height:24px;}"

        # nav list
        ".psb-nav{flex:1;overflow-y:auto;overflow-x:hidden;padding:10px 6px;"
        "scrollbar-width:thin;scrollbar-color:rgba(255,255,255,.08) transparent;"
        "min-width:" + ew + "px;}"
        ".psb-nav::-webkit-scrollbar{width:4px;}"
        ".psb-nav::-webkit-scrollbar-thumb{"
        "background:rgba(255,255,255,.08);border-radius:4px;}"

        # nav item
        ".psb-item{display:flex;align-items:center;gap:10px;"
        "padding:8px 8px 8px 9px;border-radius:8px;cursor:pointer;"
        "white-space:nowrap;user-select:none;margin-bottom:2px;"
        "transition:background .14s;}"
        ".psb-item:hover{background:rgba(255,255,255,.06);}"
        ".psb-item.psb-active{background:rgba(0,118,206,.22);}"

        # icon — visible collapsed, hidden expanded
        ".psb-icon{font-size:15px;flex-shrink:0;width:22px;text-align:center;"
        "opacity:.70;"
        "transition:opacity .14s,width .20s,font-size .20s;}"
        ".psb-item:hover .psb-icon,"
        ".psb-item.psb-active .psb-icon{opacity:1;}"
        "#pak-sb:hover .psb-icon{"
        "opacity:0!important;width:0!important;"
        "font-size:0!important;overflow:hidden!important;}"

        # label — hidden collapsed, visible expanded
        ".psb-lbl{font-size:12.5px;font-weight:500;color:#6b7fa0;"
        "opacity:0;transform:translateX(-6px);pointer-events:none;"
        "transition:opacity .20s ease .05s,transform .20s ease .05s,color .14s;}"
        "#pak-sb:hover .psb-lbl{"
        "opacity:1;transform:translateX(0);pointer-events:all;}"
        ".psb-item:hover .psb-lbl{color:#c8d6e8;}"
        ".psb-item.psb-active .psb-lbl{color:#38bdf8;font-weight:700;}"

        # footer
        ".psb-footer{flex-shrink:0;padding:10px 6px 14px;"
        "border-top:1px solid rgba(255,255,255,.06);min-width:" + ew + "px;}"
        ".psb-urow{display:flex;align-items:center;gap:9px;"
        "padding:7px 8px;border-radius:8px;margin-bottom:6px;}"
        ".psb-avatar{font-size:15px;flex-shrink:0;width:22px;text-align:center;}"
        ".psb-uname{font-size:11.5px;font-weight:600;color:#3d5068;white-space:nowrap;"
        "opacity:0;transform:translateX(-6px);"
        "transition:opacity .20s ease .05s,transform .20s ease .05s;}"
        "#pak-sb:hover .psb-uname{opacity:1;transform:translateX(0);}"

        # logout button
        "#pak-logout{display:flex;align-items:center;gap:9px;width:100%;"
        "padding:7px 8px 7px 9px;border-radius:8px;"
        "background:#990000;border:1px solid rgba(239,68,68,.18);"
        "cursor:pointer;font-family:inherit;"
        "transition:background .15s,border-color .15s;}"
        "#pak-logout:hover{"
        "background:#008000;border-color:rgba(239,68,68,.40);}"
        ".psb-lico{font-size:15px;flex-shrink:0;width:22px;text-align:center;}"
        ".psb-ltxt{font-size:12.5px;font-weight:600;color:#aee800;white-space:nowrap;"
        "opacity:0;transform:translateX(-6px);"
        "transition:opacity .20s ease .05s,transform .20s ease .05s;}"
        "#pak-sb:hover .psb-ltxt{opacity:1;transform:translateX(0);}"
    )

    # ── 4. IFRAME HTML + JS ──────────────────────────────────────────────────
    # JS strings use single-quotes only to avoid escaping issues.
    # LOGO_SRC is injected as a Python string; empty string → show fallback.
    html = """<!DOCTYPE html>
<html><head><meta charset='utf-8'></head>
<body style='margin:0;padding:0;background:transparent;'>
<script>
(function(){

var TABS     = [""" + tab_js + """];
var USER     = '""" + user_str + """';
var LOGO_SRC = '""" + logo_src + """';   /* base64 data-URI or empty */

/* ── retry boot until parent DOM ready ── */
var gaps=[0,100,300,700,1500,3000], gi=0;
(function attempt(){
  if(gi>=gaps.length)return;
  setTimeout(function(){ gi++; boot(); attempt(); }, gaps[gi]);
})();

function boot(){
  var P=window.parent.document;
  if(!P||!P.body) return;
  /* Remove login-page left panel if it survived from before login */
  ['pak-login-left','pak-login-left-css'].forEach(function(id){
    var e=P.getElementById(id); if(e) e.remove();
  });
  if(P.getElementById('pak-sb')){ rebind(P); return; }
  injectCSS(P);
  injectHTML(P);
  hideTabBar(P);
  setTimeout(function(){ bindAll(P); hideTabBar(P); }, 300);
  setTimeout(function(){ hideTabBar(P); }, 1200);
}

/* ── inject CSS into parent <head> ── */
function injectCSS(P){
  var s=P.createElement('style');
  s.id='pak-sb-css';
  s.textContent=""" + repr(css) + """;
  P.head.appendChild(s);
}

/* ── build logo / brand header markup ── */
function buildLogoHTML(){
  var icon = LOGO_SRC
    ? '<img class="psb-logo-img" src="'+LOGO_SRC+'" alt="PEAKADS">'
    : '<span class="psb-ham">&#9776;</span>';
  return '<div class="psb-logo">'+icon
         +'<span class="psb-brand">PEAKADS&nbsp;LLP</span></div>';
}

/* ── inject sidebar HTML into parent <body> ── */
function injectHTML(P){
  var items=TABS.map(function(t){
    return '<div class="psb-item" data-label="'+t.label+'">'
      +'<span class="psb-icon">'+t.icon+'</span>'
      +'<span class="psb-lbl">'+t.label+'</span></div>';
  }).join('');

  var el=P.createElement('div');
  el.id='pak-sb';
  el.innerHTML=
    buildLogoHTML()
    +'<div class="psb-nav">'+items+'</div>'
    +'<div class="psb-footer">'
    +'<div class="psb-urow">'
    +'<span class="psb-avatar">&#128100;</span>'
    +'<span class="psb-uname">'+USER+'</span></div>'
    +'<button id="pak-logout">'
    +'<span class="psb-lico">&#9211;</span>'
    +'<span class="psb-ltxt">Logout</span></button></div>';

  P.body.insertBefore(el, P.body.firstChild);
}

/* ── force-hide native tab bar via JS (belt-and-suspenders) ── */
function hideTabBar(P){
  var bars=P.querySelectorAll('[data-testid="stTabBar"],[data-baseweb="tab-list"]');
  bars.forEach(function(b){
    b.style.cssText='display:none!important;height:0!important;'
      +'visibility:hidden!important;overflow:hidden!important;'
      +'margin:0!important;padding:0!important;';
  });
  if(bars.length===0){
    setTimeout(function(){ hideTabBar(P); }, 400);
  }
}

/* ── find native Streamlit tab button by label text ── */
function findTab(P,lbl){
  var btns=P.querySelectorAll('button[data-testid="stTab"]');
  for(var i=0;i<btns.length;i++){
    if(btns[i].innerText.trim()===lbl.trim()) return btns[i];
  }
  return null;
}

/* ── sync active highlight ── */
function syncActive(P){
  var sel=P.querySelector('button[data-testid="stTab"][aria-selected="true"]');
  if(!sel) return;
  var lbl=sel.innerText.trim();
  P.querySelectorAll('.psb-item').forEach(function(el){
    el.classList.toggle('psb-active', el.dataset.label===lbl);
  });
}

/* ── logout: find the hidden Streamlit "Logout" button in st.sidebar ── */
function doLogout(P){
  var all=P.querySelectorAll('button');
  for(var i=0;i<all.length;i++){
    /* skip our own visual sidebar button */
    if(all[i].id==='pak-logout') continue;
    if(all[i].innerText.trim()==='Logout'){
      all[i].click();
      return;
    }
  }
  /* Fallback: broader match in case label changes */
  for(var j=0;j<all.length;j++){
    if(all[j].id==='pak-logout') continue;
    if(all[j].innerText.trim().toLowerCase().includes('logout')){
      all[j].click();
      return;
    }
  }
}

/* ── bind click events ── */
function bindAll(P){
  /* fresh clones drop stale listeners */
  P.querySelectorAll('.psb-item').forEach(function(el){
    var f=el.cloneNode(true); el.parentNode.replaceChild(f,el);
  });
  P.querySelectorAll('.psb-item').forEach(function(el){
    el.addEventListener('click',function(){
      var btn=findTab(P,this.dataset.label);
      if(btn){
        btn.click();
        P.querySelectorAll('.psb-item').forEach(function(x){
          x.classList.remove('psb-active');
        });
        el.classList.add('psb-active');
      }
    });
  });

  /* logout */
  var lb=P.getElementById('pak-logout');
  if(lb){
    var lf=lb.cloneNode(true); lb.parentNode.replaceChild(lf,lb);
    lf.addEventListener('click',function(){ doLogout(P); });
  }

  syncActive(P);

  /* MutationObserver: watch tab bar aria-selected */
  var bar=P.querySelector('[data-testid="stTabBar"]');
  if(bar){
    new MutationObserver(function(){ syncActive(P); })
      .observe(bar,{subtree:true,attributes:true,attributeFilter:['aria-selected']});
  }
}

function rebind(P){
  [200,600,1400].forEach(function(d){
    setTimeout(function(){ bindAll(P); hideTabBar(P); }, d);
  });
}

})();
</script>
</body></html>"""

    components.html(html, height=0, scrolling=False)