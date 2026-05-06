"""
invoice_subnav.py  —  PEAKADS LLP
Right-side hover sub-nav for the Invoice Manager tab ONLY.

WHY THIS APPROACH IS CORRECT (mirrors dashboard_module._render_nav_bar exactly)
────────────────────────────────────────────────────────────────────────────────
dashboard_module uses st.markdown to render #dash-sidenav HTML.
That HTML lives INSIDE the Dashboard tab panel in the Streamlit DOM.
Streamlit hides inactive tab panels with display:none on the panel wrapper.
display:none propagates to ALL descendants — including position:fixed children.
So the fixed nav automatically disappears on other tabs with zero JS needed.

Previous versions injected HTML into document.body via iframe JS.
document.body is OUTSIDE all tab panels → never gets hidden → showed everywhere.

THIS VERSION:
  st.markdown  → renders the subnav HTML inside the Invoice Manager tab panel
                 (auto-hides when user switches away — exactly like dashboard nav)
  components.html (height=0) → JS ONLY: binds clicks on the subnav buttons
                                to programmatically click the hidden invoice stTab buttons

INTEGRATION (2 lines in invoice_module.py — unchanged)
────────────────────────────────────────────────────────
  from invoice_subnav import render_invoice_subnav
  render_invoice_subnav()   ← just before st.tabs([...])
"""

import streamlit as st
import streamlit.components.v1 as components

_INV_SUBTABS = [
    ("📄 Create Invoice",  "📄", "Create Invoice"),
    ("📋 Invoice History", "📋", "Invoice History"),
    ("🔔 Send Reminder",   "🔔", "Send Reminder"),
    ("📊 DSP Statement",   "📊", "DSP Statement"),
    ("📑 GST Report",      "📑", "GST Report"),
]


def render_invoice_subnav() -> None:
    """
    Call once, immediately before the Invoice Manager st.tabs([...]) call.
    """

    # ── Build pill buttons + dots HTML ──────────────────────────────────────
    pills_html = '<div class="inv-snav-title">Navigate</div>'
    dots_html  = ""
    for tab_label, icon, short in _INV_SUBTABS:
        pills_html += (
            f'<button class="inv-snav-btn" data-label="{tab_label}">'
            f'<span class="inv-snav-icon">{icon}</span>'
            f'<span class="inv-snav-label">{short}</span>'
            f'</button>'
        )
        dots_html += (
            f'<span class="inv-snav-dot" data-label="{tab_label}" '
            f'title="{short}"></span>'
        )

    # ── STEP 1: st.markdown — HTML rendered inside the Invoice Manager tab panel
    # Streamlit's display:none on inactive tabs hides this automatically.
    # No JS visibility toggling needed — same as dashboard _render_nav_bar().
    st.markdown(f"""
    <style>
    html {{ scroll-behavior: smooth !important; }}

    #inv-sidenav {{
        position      : fixed;
        right         : 0;
        top           : 50%;
        transform     : translateY(-50%);
        z-index       : 99998;
        display       : flex;
        flex-direction: row;
        align-items   : center;
    }}

    .inv-snav-handle {{
        width          : 10px;
        min-height     : 180px;
        background     : linear-gradient(180deg,
                            rgba(0,100,200,0)  0%,
                            #0076CE           40%,
                            #003a80           60%,
                            rgba(0,20,80,0)  100%);
        border-radius  : 8px 0 0 8px;
        display        : flex;
        flex-direction : column;
        align-items    : center;
        justify-content: center;
        gap            : 9px;
        padding        : 14px 0;
        cursor         : pointer;
        flex-shrink    : 0;
        box-shadow     : -3px 0 16px rgba(0,118,206,0.55),
                          0   0  8px rgba(0,118,206,0.30);
        transition     : width       0.30s cubic-bezier(.4,0,.2,1),
                         opacity     0.25s ease,
                         border-radius 0.30s;
    }}

    .inv-snav-dot {{
        width         : 5px;
        height        : 5px;
        border-radius : 50%;
        background    : rgba(255,255,255,0.55);
        flex-shrink   : 0;
        display       : block;
        cursor        : pointer;
        transition    : background 0.2s, transform 0.2s;
        text-decoration: none !important;
    }}
    .inv-snav-dot:hover {{
        background : #fff;
        transform  : scale(1.5);
    }}
    .inv-snav-dot.inv-active {{
        background : #4dabf7;
        transform  : scale(1.4);
    }}

    .inv-snav-panel {{
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

    #inv-sidenav:hover .inv-snav-panel {{
        max-width : 185px;
        padding   : 14px 10px;
    }}
    #inv-sidenav:hover .inv-snav-handle {{
        width   : 0;
        opacity : 0;
    }}

    .inv-snav-title {{
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

    .inv-snav-btn {{
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
        cursor         : pointer;
        letter-spacing : 0.25px;
        font-family    : -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        transition     : background 0.18s ease, border-color 0.18s ease,
                         transform  0.14s ease, box-shadow  0.18s ease;
        white-space    : nowrap;
        width          : 100%;
        text-align     : left;
    }}
    .inv-snav-btn:hover {{
        background  : rgba(0,118,206,0.55) !important;
        border-color: #4dabf7              !important;
        color       : #fff                 !important;
        transform   : translateX(-4px);
        box-shadow  : -3px 0 12px rgba(0,118,206,0.4);
    }}
    .inv-snav-btn:active {{
        background: #0076CE !important;
        transform : translateX(-1px);
    }}
    .inv-snav-btn.inv-active {{
        background  : rgba(0,118,206,0.30) !important;
        border-color: #4dabf7              !important;
        color       : #fff                 !important;
    }}
    .inv-snav-icon  {{ font-size: 15px; line-height: 1; flex-shrink: 0; }}
    .inv-snav-label {{ font-size: 12px; }}
    </style>

    <div id="inv-sidenav">
        <div class="inv-snav-panel">
            {pills_html}
        </div>
        <div class="inv-snav-handle">{dots_html}</div>
    </div>
    """, unsafe_allow_html=True)

    # ── STEP 2: components.html — JS only (zero-height iframe)
    # Binds click events on the subnav buttons rendered above.
    # Uses textContent (not innerText) because stTabBar is display:none.
    js_only = """<!DOCTYPE html>
<html><head><meta charset='utf-8'></head>
<body style='margin:0;padding:0;background:transparent;'>
<script>
(function(){

  var gaps=[0,200,500,1000,2000], gi=0;
  (function attempt(){
    if(gi>=gaps.length) return;
    setTimeout(function(){ gi++; bind(); attempt(); }, gaps[gi]);
  })();

  function findInvTab(P, lbl){
    var btns = P.querySelectorAll('button[data-testid="stTab"]');
    for(var i=0; i<btns.length; i++){
      if((btns[i].textContent||'').trim() === lbl.trim()) return btns[i];
    }
    return null;
  }

  function syncActive(P){
    var btns = P.querySelectorAll('button[data-testid="stTab"]');
    var activeLbl = '';
    for(var i=0; i<btns.length; i++){
      if(btns[i].getAttribute('aria-selected')==='true'){
        activeLbl = (btns[i].textContent||'').trim();
      }
    }
    P.querySelectorAll('.inv-snav-btn, .inv-snav-dot').forEach(function(el){
      el.classList.toggle('inv-active', el.dataset.label === activeLbl);
    });
  }

  function bind(){
    var P = window.parent.document;
    if(!P || !P.body) return;

    var btns = P.querySelectorAll('.inv-snav-btn, .inv-snav-dot');
    if(btns.length === 0) return;   // subnav not rendered yet — retry

    // Fresh clones to drop any stale listeners
    btns.forEach(function(el){
      var f = el.cloneNode(true);
      el.parentNode.replaceChild(f, el);
    });

    // Bind click on each subnav button
    P.querySelectorAll('.inv-snav-btn, .inv-snav-dot').forEach(function(el){
      el.addEventListener('click', function(){
        var btn = findInvTab(P, this.dataset.label);
        if(btn){
          btn.click();
          var lbl = this.dataset.label;
          P.querySelectorAll('.inv-snav-btn, .inv-snav-dot').forEach(function(x){
            x.classList.toggle('inv-active', x.dataset.label === lbl);
          });
        }
      });
    });

    // Watch all stTabBars for aria-selected changes → sync active pill
    P.querySelectorAll('[data-testid="stTabBar"]').forEach(function(bar){
      new MutationObserver(function(){ syncActive(P); })
        .observe(bar, { subtree:true, attributes:true,
                        attributeFilter:['aria-selected'] });
    });

    syncActive(P);
  }

})();
</script>
</body></html>"""

    components.html(js_only, height=0, scrolling=False)