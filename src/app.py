import math
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
import json

from drones import DRONES
from engine import apply_rules, score_drones, get_num_drones
from weather import fetch_weather

st.set_page_config(page_title="SAR Drone DSS", layout="wide", initial_sidebar_state="collapsed")

# ── SESSION STATE ───────────────────────────────────────────────────────────────
for _key, _val in [
    ("weather_select", "Clear"), ("tod_radio", "Day"),
    ("weather_info", None), ("weather_error", None),
    ("altitude_auto", None),   # set from geocoding elevation
    ("sidebar_open",  True),   # custom toggle
    ("theme", "light"),
    # Persisted sidebar widget values (used when panel is hidden)
    ("emergency", "Missing Person"),
    ("area", 5.0),
    ("dist", 5.0),
    ("sup", 0.0),
    ("bud", 500),
    ("run", False),
    ("submitted_scenario", None),
    ("sim_run_id", 0),
    ("city_input", ""),
]:
    if _key not in st.session_state:
        st.session_state[_key] = _val

_dark = st.session_state["theme"] == "dark"

# ── DESIGN TOKENS ──────────────────────────────────────────────────────────────
T = {
    "bg":         "#0D1117" if _dark else "#F8FAFC",
    "surface":    "#161B22" if _dark else "#FFFFFF",
    "surface2":   "#21262D" if _dark else "#F1F5F9",
    "border":     "#30363D" if _dark else "#E2E8F0",
    "text":       "#E6EDF3" if _dark else "#0F172A",
    "muted":      "#8B949E" if _dark else "#64748B",
    "accent":     "#3B82F6",
    "accent_bg":  "rgba(59,130,246,0.12)" if _dark else "rgba(59,130,246,0.08)",
    "accent_border": "rgba(59,130,246,0.35)" if _dark else "rgba(59,130,246,0.25)",
    "green":      "#4ADE80" if _dark else "#16A34A",
    "green_bg":   "rgba(74,222,128,0.10)" if _dark else "rgba(22,163,74,0.08)",
    "green_border": "rgba(74,222,128,0.30)" if _dark else "rgba(22,163,74,0.25)",
    "red":        "#F87171" if _dark else "#DC2626",
    "red_bg":     "rgba(248,113,113,0.10)" if _dark else "rgba(220,38,38,0.06)",
    "red_border": "rgba(248,113,113,0.30)" if _dark else "rgba(220,38,38,0.20)",
    "amber":      "#FBBF24" if _dark else "#D97706",
    "amber_bg":   "rgba(251,191,36,0.10)" if _dark else "rgba(217,119,6,0.08)",
}

# ── GLOBAL CSS ─────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

*, *::before, *::after {{
    font-family: 'Inter', sans-serif !important;
    box-sizing: border-box;
}}

:root {{
    color-scheme: {"dark" if _dark else "light"} !important;
}}

html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"],
[data-testid="stToolbar"], .main {{
    background: {T['bg']} !important;
    color: {T['text']} !important;
}}

body, button, input, textarea, select {{
    color: {T['text']} !important;
}}

/* ── Hide native Streamlit sidebar entirely (we use a column panel instead) ── */
section[data-testid="stSidebar"],
[data-testid="stSidebarCollapseButton"],
[data-testid="collapsedControl"] {{
    display: none !important;
}}

/* ── App chrome ── */
.stApp {{
    background: {T['bg']} !important;
    color: {T['text']} !important;
    min-height: 100vh;
}}
#MainMenu, footer, header {{ visibility: hidden; }}
.block-container {{
    padding-top: 1.25rem !important;
    padding-bottom: 3rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
}}

/* ── Custom panel column (left sidebar replacement) ── */
.sar-panel {{
    background: {T['surface']};
    border: 1px solid {T['border']};
    border-radius: 12px;
    padding: 0.75rem 0.85rem 1rem;
    min-height: calc(100vh - 3.5rem);
    overflow-y: auto;
}}
.sar-panel hr {{
    border: none;
    border-top: 1px solid {T['border']};
    margin: 0.6rem 0;
}}

/* Panel inputs */
.sar-panel [data-baseweb="select"] > div {{
    background: {T['surface2']} !important;
    border: 1px solid {T['border']} !important;
    color: {T['text']} !important;
    border-radius: 8px !important;
    box-shadow: none !important;
}}
.sar-panel [data-baseweb="select"] span,
.sar-panel [data-baseweb="select"] input,
.sar-panel [data-baseweb="select"] [role="combobox"] {{
    color: {T['text']} !important;
    -webkit-text-fill-color: {T['text']} !important;
}}
.sar-panel [data-baseweb="select"] svg {{
    color: {T['muted']} !important;
    fill: {T['muted']} !important;
}}
.sar-panel li {{
    color: {T['text']} !important;
    background: {T['surface']} !important;
}}
.sar-panel li:hover {{
    background: {T['surface2']} !important;
}}
.sar-panel .stTextInput input {{
    background: {T['surface2']} !important;
    border: 1px solid {T['border']} !important;
    color: {T['text']} !important;
    -webkit-text-fill-color: {T['text']} !important;
    border-radius: 8px !important;
    box-shadow: none !important;
    transition: border-color 0.15s;
}}
.sar-panel .stTextInput input::placeholder {{
    color: {T['muted']} !important;
    -webkit-text-fill-color: {T['muted']} !important;
    opacity: 1 !important;
}}
.sar-panel .stTextInput input:focus {{
    border-color: {T['accent']} !important;
    box-shadow: 0 0 0 3px {T['accent_bg']} !important;
    outline: none;
}}
.sar-panel .stSlider [data-baseweb="thumb"] {{
    background: {T['accent']} !important;
    box-shadow: none !important;
    width: 16px !important; height: 16px !important;
    border: 2px solid {T['surface']} !important;
}}
.sar-panel .stSlider [data-baseweb="track"] {{
    background: {T['border']} !important; height: 4px !important;
}}
.sar-panel .stSlider [data-baseweb="track-fill"] {{
    background: {T['accent']} !important;
}}
.sar-panel .stRadio div[role="radiogroup"] label {{
    background: {T['surface2']};
    border: 1px solid {T['border']};
    color: {T['text']} !important;
    border-radius: 8px;
    padding: 5px 16px;
    margin: 3px 2px;
    transition: all 0.15s;
    font-size: 0.85rem;
}}
.sar-panel .stRadio div[role="radiogroup"] label:hover {{
    border-color: {T['accent']};
    background: {T['accent_bg']};
}}

/* Buttons */
div.stButton > button {{
    background: {T['accent']} !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.65rem 1.2rem !important;
    font-size: 0.875rem !important;
    font-weight: 600 !important;
    width: 100% !important;
    letter-spacing: 0.2px !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.15) !important;
    cursor: pointer !important;
}}
div.stButton > button:hover {{
    background: #2563EB !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(59,130,246,0.35) !important;
}}
div.stButton > button:active {{
    transform: translateY(0) !important;
}}

/* Theme toggle button — override to be subtle */
div.stButton.theme-toggle > button {{
    background: {T['surface2']} !important;
    color: {T['muted']} !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    padding: 0.4rem 0.8rem !important;
    box-shadow: none !important;
    border: 1px solid {T['border']} !important;
    border-radius: 6px !important;
}}
div.stButton.theme-toggle > button:hover {{
    border-color: {T['accent']} !important;
    color: {T['accent']} !important;
    transform: none !important;
    box-shadow: none !important;
    background: {T['accent_bg']} !important;
}}

/* Collapsed menu button */
div.st-key-open_panel button {{
    background: {T['surface2']} !important;
    color: {T['text']} !important;
    -webkit-text-fill-color: {T['text']} !important;
    border: 1px solid {T['border']} !important;
    box-shadow: none !important;
}}
div.st-key-open_panel button:hover {{
    background: {T['accent_bg']} !important;
    color: {T['accent']} !important;
    -webkit-text-fill-color: {T['accent']} !important;
    border-color: {T['accent']} !important;
    transform: none !important;
    box-shadow: none !important;
}}
div.st-key-open_panel button * {{
    color: inherit !important;
    -webkit-text-fill-color: inherit !important;
}}

/* Expander */
[data-testid="stExpander"] {{
    background: {T['surface']} !important;
    border: 1px solid {T['border']} !important;
    border-radius: 10px !important;
    overflow: hidden !important;
}}
[data-testid="stExpander"] summary {{
    color: {T['text']} !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    padding: 0.75rem 1rem !important;
}}
[data-testid="stExpander"] summary:hover {{
    background: {T['surface2']} !important;
}}
[data-testid="stExpander"] > div > div {{
    padding: 0.25rem 0.75rem 0.75rem !important;
}}

/* Metrics */
[data-testid="stMetricValue"] {{
    color: {T['accent']} !important;
    font-weight: 700 !important;
}}
[data-testid="stMetricLabel"] {{
    color: {T['muted']} !important;
    font-size: 0.72rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
}}

/* General text */
.stMarkdown, .stMarkdown p, .stMarkdown div,
label, div[data-testid="stWidgetLabel"], div[data-testid="stWidgetLabel"] *,
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] *,
[data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] *,
[data-testid="stText"], [data-testid="stText"] * {{
    color: {T['text']} !important;
}}

.st-emotion-cache-ue6h4q,
.st-emotion-cache-16idsys,
.st-emotion-cache-1fttcpj,
.st-emotion-cache-10trblm,
.st-emotion-cache-183lzff {{
    color: {T['text']} !important;
}}

input, textarea, [contenteditable="true"] {{
    background: {T['surface2']} !important;
    color: {T['text']} !important;
    -webkit-text-fill-color: {T['text']} !important;
    caret-color: {T['accent']} !important;
}}

input::placeholder, textarea::placeholder {{
    color: {T['muted']} !important;
    -webkit-text-fill-color: {T['muted']} !important;
    opacity: 1 !important;
}}

/* Scrollbar */
::-webkit-scrollbar {{ width: 5px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{
    background: {T['border']};
    border-radius: 3px;
}}

/* Spinner */
.stSpinner > div {{ border-top-color: {T['accent']} !important; }}

/* ── Secondary button style for collapse / theme toggles ── */
div[data-testid="stHorizontalBlock"] div.stButton > button {{
    background: {T['surface2']} !important;
    color: {T['muted']} !important;
    border: 1px solid {T['border']} !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    padding: 0.4rem 0.5rem !important;
    box-shadow: none !important;
}}
div[data-testid="stHorizontalBlock"] div.stButton > button:hover {{
    border-color: {T['accent']} !important;
    color: {T['accent']} !important;
    background: {T['accent_bg']} !important;
    transform: none !important;
    box-shadow: none !important;
}}
</style>
""", unsafe_allow_html=True)

# ── LAYOUT ──────────────────────────────────────────────────────────────────────
_sb_open = st.session_state["sidebar_open"]
run      = st.session_state["run"]

def current_scenario_from_state():
    return {
        "emergency":     st.session_state["emergency"],
        "weather":       st.session_state["weather_select"],
        "time_of_day":   st.session_state["tod_radio"],
        "altitude":      st.session_state.get("altitude_auto") or 1500,
        "area":          st.session_state["area"],
        "distance":      st.session_state["dist"],
        "supply_weight": st.session_state["sup"],
        "budget":        st.session_state["bud"],
    }

if _sb_open:
    _col_sb, _col_main = st.columns([1, 3], gap="small")
else:
    _col_main = st.container()

# ── SIDEBAR PANEL (column) ───────────────────────────────────────────────────────
if _sb_open:
    with _col_sb:
        # JS: add CSS class to this column element so .sar-panel styles apply
        components.html("""<script>
        (function(){
            function tag(){
                var fs=window.parent.document.querySelectorAll('iframe');
                for(var i=0;i<fs.length;i++){
                    try{if(fs[i].contentWindow===window){
                        var c=fs[i].closest('[data-testid="stColumn"]');
                        if(c){c.classList.add('sar-panel');} return;
                    }}catch(e){}
                }
            }
            tag(); setTimeout(tag,80); setTimeout(tag,300);
        })();
        </script>""", height=1, scrolling=False)

        # ── Section label helper ──
        def slabel(txt):
            st.markdown(
                f"<p style='color:{T['muted']};font-size:0.7rem;font-weight:600;"
                f"letter-spacing:0.8px;text-transform:uppercase;margin:0.75rem 0 0.25rem;'>{txt}</p>",
                unsafe_allow_html=True,
            )

        # Logo
        st.markdown(f"""
        <div style="padding:0.5rem 0.1rem 0.5rem;display:flex;align-items:center;gap:0.75rem;">
            <div style="width:36px;height:36px;border-radius:9px;
                        background:{T['accent_bg']};border:1px solid {T['accent_border']};
                        display:flex;align-items:center;justify-content:center;
                        font-size:1.2rem;flex-shrink:0;">🚁</div>
            <div>
                <div style="font-weight:800;font-size:0.95rem;color:{T['text']};
                            letter-spacing:-0.2px;">SAR Drone DSS</div>
                <div style="font-size:0.7rem;color:{T['muted']};margin-top:1px;">
                    Decision Support System</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("---")

        slabel("Emergency Type")
        emergency = st.selectbox("Emergency", ["Missing Person", "Injured Person",
                                               "Altitude Sickness", "Supply Delivery"],
                                 key="emergency", label_visibility="collapsed")

        slabel("Mission Location")
        city_input = st.text_input("Location", key="city_input",
                                   placeholder="e.g. Stockholm, Kiruna…",
                                   label_visibility="collapsed")

        if st.button("🌐  Fetch Live Weather", key="fetch_weather", use_container_width=True):
            if city_input.strip():
                try:
                    with st.spinner("Fetching weather…"):
                        _info = fetch_weather(city_input.strip())
                    st.session_state["weather_select"] = _info["condition"]
                    st.session_state["tod_radio"]      = _info["time_of_day"]
                    st.session_state["weather_info"]   = _info
                    st.session_state["altitude_auto"]  = _info.get("elevation", 0)
                    st.session_state["weather_error"]  = None
                except Exception as _e:
                    st.session_state["weather_error"] = str(_e)
                    st.session_state["weather_info"]  = None
            else:
                st.session_state["weather_error"] = "Enter a city name first."

        if st.session_state["weather_info"]:
            _wi = st.session_state["weather_info"]
            st.markdown(
                f"<div style='background:{T['green_bg']};border:1px solid {T['green_border']};"
                f"border-radius:8px;padding:0.5rem 0.75rem;margin:0.35rem 0;font-size:0.78rem;'>"
                f"<span style='color:{T['green']};font-weight:600;'>📍 {_wi['location']}</span><br>"
                f"<span style='color:{T['muted']};'>💨 {_wi['wind_speed']} m/s · "
                f"<b style='color:{T['text']};'>{_wi['condition']}</b> · {_wi['time_of_day']}"
                f"</span></div>", unsafe_allow_html=True,
            )
        elif st.session_state["weather_error"]:
            st.markdown(
                f"<div style='background:{T['red_bg']};border:1px solid {T['red_border']};"
                f"border-radius:8px;padding:0.5rem 0.75rem;margin:0.35rem 0;font-size:0.78rem;"
                f"color:{T['red']};'>⚠ {st.session_state['weather_error']}</div>",
                unsafe_allow_html=True,
            )

        # Weather Condition — read-only, set by API fetch
        _wc_val = st.session_state.get("weather_select", "Clear")
        _wc_has_data = st.session_state.get("weather_info") is not None
        _wc_color = T["green"] if _wc_has_data else T["muted"]
        _wc_note  = "from location" if _wc_has_data else "fetch a location above"
        weather   = _wc_val
        slabel("Weather Condition")
        st.markdown(
            f"<div style='background:{T['surface2']};border:1px solid {T['border']};"
            f"border-radius:8px;padding:0.5rem 0.75rem;margin-bottom:0.25rem;"
            f"display:flex;align-items:center;justify-content:space-between;'>"
            f"<span style='font-size:1rem;font-weight:700;color:{T['text']};'>{_wc_val}</span>"
            f"<span style='font-size:0.7rem;color:{_wc_color};font-weight:500;'>{_wc_note}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # Time of Day — read-only, set by API fetch
        _tod_val    = st.session_state.get("tod_radio", "Day")
        _tod_icon   = "☀️" if _tod_val == "Day" else "🌙"
        _tod_color  = T["green"] if _wc_has_data else T["muted"]
        _tod_note   = "from location" if _wc_has_data else "fetch a location above"
        time_of_day = _tod_val
        slabel("Time of Day")
        st.markdown(
            f"<div style='background:{T['surface2']};border:1px solid {T['border']};"
            f"border-radius:8px;padding:0.5rem 0.75rem;margin-bottom:0.25rem;"
            f"display:flex;align-items:center;justify-content:space-between;'>"
            f"<span style='font-size:1rem;font-weight:700;color:{T['text']};'>{_tod_icon} {_tod_val}</span>"
            f"<span style='font-size:0.7rem;color:{_tod_color};font-weight:500;'>{_tod_note}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

        st.markdown("---")

        # Altitude: auto from geocoding, not a user slider
        _alt_val = st.session_state.get("altitude_auto")
        if _alt_val is not None:
            _alt_display = f"{_alt_val:,} m"
            _alt_note    = "from location"
            _alt_color   = T["green"]
        else:
            _alt_val     = 1500
            _alt_display = "—"
            _alt_note    = "set a location above"
            _alt_color   = T["muted"]

        slabel("Altitude (m)")
        st.markdown(
            f"<div style='background:{T['surface2']};border:1px solid {T['border']};"
            f"border-radius:8px;padding:0.5rem 0.75rem;margin-bottom:0.25rem;"
            f"display:flex;align-items:center;justify-content:space-between;'>"
            f"<span style='font-size:1rem;font-weight:700;color:{T['text']};'>{_alt_display}</span>"
            f"<span style='font-size:0.7rem;color:{_alt_color};font-weight:500;'>{_alt_note}</span>"
            f"</div>", unsafe_allow_html=True,
        )
        alt = _alt_val

        slabel("Area to Cover (km²)")
        area = st.slider("Area", 0.5, 30.0, 5.0, 0.5, key="area", label_visibility="collapsed")

        _dist_estimate = round(min(25.0, max(0.5, math.sqrt(area) * 1.5)), 1)
        slabel(f"Distance (km) &nbsp;·&nbsp; <span style='color:{T['muted']};font-weight:400;"
               f"font-size:0.68rem;'>~{_dist_estimate} km suggested</span>")
        dist = st.slider("Distance", 0.5, 25.0, 5.0, 0.5, key="dist", label_visibility="collapsed")

        slabel("Supply Weight (kg)")
        sup = st.slider("Supply", 0.0, 30.0, 0.0, 0.5, key="sup", label_visibility="collapsed")

        slabel("Budget per Drone (€)")
        bud = st.slider("Budget", 100, 1000, 500, 25, key="bud", label_visibility="collapsed")

        st.markdown("---")

        if st.button("⚡  Run DSS Simulation", key="run_btn", use_container_width=True):
            st.session_state["submitted_scenario"] = current_scenario_from_state()
            st.session_state["sim_run_id"] += 1
            st.session_state["run"] = True
            st.rerun()

        _c1, _c2 = st.columns(2)
        with _c1:
            _toggle_label = "☀️ Light" if _dark else "🌙 Dark"
            if st.button(_toggle_label, key="theme_toggle", use_container_width=True):
                st.session_state["theme"] = "light" if _dark else "dark"
                st.rerun()
        with _c2:
            if st.button("← Hide", key="hide_panel", use_container_width=True):
                st.session_state["sidebar_open"] = False
                st.rerun()

else:
    # Panel is hidden — read all widget values from session state
    emergency   = st.session_state["emergency"]
    weather     = st.session_state["weather_select"]
    time_of_day = st.session_state["tod_radio"]
    alt         = st.session_state.get("altitude_auto") or 1500
    area        = st.session_state["area"]
    dist        = st.session_state["dist"]
    sup         = st.session_state["sup"]
    bud         = st.session_state["bud"]

# ── MAIN CONTENT — enter column context ─────────────────────────────────────────
# Using __enter__ so the 1000-line simulation block below needs no re-indenting
_col_main.__enter__()

# ── HEADER ──
if not _sb_open:
    _hcol_btn, _hcol_hdr = st.columns([1, 11])
    with _hcol_btn:
        if st.button("☰", key="open_panel", help="Open mission parameters"):
            st.session_state["sidebar_open"] = True
            st.rerun()
    _header_area = _hcol_hdr
else:
    _header_area = st.container()

with _header_area:
    _new_mission_btn = ""
    if run:
        _new_mission_btn = f"""
        <span style="cursor:pointer;" id="nm-placeholder"></span>"""
    st.markdown(f"""
<div style="
    background:{T['surface']};border:1px solid {T['border']};border-radius:14px;
    padding:1rem 1.5rem;margin-bottom:1rem;
    display:flex;align-items:center;justify-content:space-between;gap:1rem;">
    <div>
        <div style="font-size:0.68rem;font-weight:600;letter-spacing:1px;
                    text-transform:uppercase;color:{T['muted']};margin-bottom:0.25rem;">
            BTH · DV2573 · Group 2 · Spring 2026</div>
        <div style="font-size:1.4rem;font-weight:800;color:{T['text']};
                    letter-spacing:-0.5px;margin-bottom:0.15rem;">
            SAR Drone Selection DSS</div>
        <div style="font-size:0.83rem;color:{T['muted']};">
            Intelligent Decision Support System for Search &amp; Rescue Operations</div>
    </div>
    <div style="display:flex;gap:0.5rem;flex-shrink:0;align-items:center;">
        <span style="background:{T['green_bg']};border:1px solid {T['green_border']};
                     color:{T['green']};font-size:0.7rem;font-weight:600;
                     padding:4px 10px;border-radius:20px;letter-spacing:0.3px;">
            ● System Ready</span>
    </div>
</div>
""", unsafe_allow_html=True)

if run:
    if st.button("↺  New Mission", key="new_mission"):
        st.session_state["run"] = False
        st.session_state["submitted_scenario"] = None
        st.rerun()

# ── WELCOME ─────────────────────────────────────────────────────────────────────
if not run:
    col1, col2, col3 = st.columns(3, gap="medium")

    _cards = [
        ("🎬", "Step-by-Step Simulation",
         "Watch the DSS work in real time. Parameters feed in, rules fire one by one, drones are eliminated, survivors are scored, and the winner is revealed."),
        ("🧠", "Knowledge Base Filtering",
         "Expert rules automatically remove drones that cannot handle the weather, altitude, range, payload, or budget constraints of your mission."),
        ("📊", "Weighted Decision Matrix",
         "Remaining drones are scored across 8 criteria. Weights shift dynamically — blizzard boosts wind score, night ops boost camera score."),
    ]

    for col, (icon, title, desc) in zip([col1, col2, col3], _cards):
        with col:
            st.markdown(f"""
            <div style="
                background:{T['surface']};
                border:1px solid {T['border']};
                border-radius:12px;
                padding:1.5rem;
                height:100%;
            ">
                <div style="font-size:1.75rem;margin-bottom:0.75rem;">{icon}</div>
                <div style="font-weight:700;font-size:0.95rem;color:{T['text']};
                            margin-bottom:0.5rem;">{title}</div>
                <div style="font-size:0.83rem;color:{T['muted']};line-height:1.65;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="
        background:{T['accent_bg']};
        border:1px solid {T['accent_border']};
        border-radius:10px;
        padding:0.9rem 1.25rem;
        margin-top:1rem;
        font-size:0.875rem;
        color:{T['muted']};
    ">
        Set mission parameters in the sidebar and click <strong style="color:{T['accent']};">
        ⚡ Run DSS Simulation</strong> to watch the decision process unfold.
    </div>
    """, unsafe_allow_html=True)

# ── SIMULATION ──────────────────────────────────────────────────────────────────
else:
    scenario = st.session_state.get("submitted_scenario") or current_scenario_from_state()

    passed, eliminated = apply_rules(DRONES, scenario)

    # ── No drones pass ──
    if not passed:
        st.markdown(f"""
        <div style="
            background:{T['red_bg']};
            border:2px dashed {T['red_border']};
            border-radius:14px;
            padding:2.5rem;
            text-align:center;
        ">
            <div style="font-size:2.5rem;margin-bottom:0.75rem;">🚫</div>
            <div style="font-weight:700;font-size:1.1rem;color:{T['red']};
                        margin-bottom:0.4rem;">No Drones Meet the Requirements</div>
            <div style="color:{T['muted']};font-size:0.875rem;">
                Try adjusting budget, supply weight, or distance constraints.
            </div>
        </div>
        """, unsafe_allow_html=True)

    else:
        scored     = score_drones(passed, scenario)
        top        = scored[0]
        num_drones = get_num_drones(scenario["area"])
        total_cost = num_drones * top["cost"]

        # ── Build simulation payload ──
        score_map    = {d["name"]: d["score"]  for d in scored}
        elim_map     = {d["name"]: d["reasons"] for d in eliminated}
        passed_names = {d["name"] for d in passed}

        sim_drones = []
        for drone in DRONES:
            sim_drones.append({
                "name":            drone["name"],
                "type":            drone["type"],
                "is_plane":        "Fixed" in drone["type"],
                "wind_resistance": drone["wind_resistance"],
                "max_altitude":    drone["max_altitude"],
                "battery_life":    drone["battery_life"],
                "max_range":       drone["max_range"],
                "payload":         drone["payload"],
                "speed":           drone["speed"],
                "thermal":         drone["thermal"],
                "night_vision":    drone["night_vision"],
                "cost":            drone["cost"],
                "eliminated":      drone["name"] not in passed_names,
                "reasons":         elim_map.get(drone["name"], []),
                "score":           score_map.get(drone["name"], 0),
            })

        top_cams = []
        if top["thermal"]:      top_cams.append("Thermal")
        if top["night_vision"]: top_cams.append("Night Vision")

        sim_data = {
            "run_id": st.session_state["sim_run_id"],
            "drones": sim_drones,
            "scenario": scenario,
            "top": {
                "name":            top["name"],
                "type":            top["type"],
                "is_plane":        "Fixed" in top["type"],
                "score":           top["score"],
                "desc":            top["description"],
                "cams":            top_cams,
                "wind_resistance": top["wind_resistance"],
                "max_altitude":    top["max_altitude"],
                "battery_life":    top["battery_life"],
                "max_range":       top["max_range"],
                "payload":         top["payload"],
                "speed":           top["speed"],
                "cost":            top["cost"],
            },
            "num_drones":  num_drones,
            "total_cost":  total_cost,
            "elim_count":  len(eliminated),
            "pass_count":  len(passed),
        }
        sim_json = json.dumps(sim_data)

        # ── Palette passed into the iframe ──
        SIM = {
            # backgrounds
            "bg":          "#0F1117" if _dark else "#FFFFFF",
            "surface":     "#161B22" if _dark else "#F8FAFC",
            "surface2":    "#21262D" if _dark else "#EFF2F7",
            "border":      "#30363D" if _dark else "#DDE3EE",
            # text
            "text":        "#E6EDF3" if _dark else "#0F172A",
            "muted":       "#8B949E" if _dark else "#6B7280",
            # accents
            "accent":      "#3B82F6",
            "accent_bg":   "rgba(59,130,246,0.12)" if _dark else "rgba(59,130,246,0.07)",
            "accent_bdr":  "rgba(59,130,246,0.30)" if _dark else "rgba(59,130,246,0.20)",
            "green":       "#4ADE80" if _dark else "#16A34A",
            "green_bg":    "rgba(74,222,128,0.10)" if _dark else "rgba(22,163,74,0.07)",
            "green_bdr":   "rgba(74,222,128,0.25)" if _dark else "rgba(22,163,74,0.20)",
            "red":         "#F87171" if _dark else "#DC2626",
            "red_bg":      "rgba(248,113,113,0.10)" if _dark else "rgba(220,38,38,0.05)",
            "red_bdr":     "rgba(248,113,113,0.25)" if _dark else "rgba(220,38,38,0.18)",
            "amber":       "#FBBF24" if _dark else "#D97706",
            "amber_bg":    "rgba(251,191,36,0.10)" if _dark else "rgba(217,119,6,0.07)",
        }

        # ────────────────────────────────────────────────────────────────────────
        #  CINEMATIC SIMULATION COMPONENT
        # ────────────────────────────────────────────────────────────────────────
        components.html(f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

*, *::before, *::after {{
    font-family: 'Inter', sans-serif;
    box-sizing: border-box;
    margin: 0; padding: 0;
}}
body {{
    background: {SIM['bg']};
    color: {SIM['text']};
    overflow: hidden;
    padding: 4px 2px;
    font-size: 14px;
}}

/* ── Phase progress bar ── */
.pbar {{
    display: flex;
    align-items: center;
    gap: 0;
    background: {SIM['surface']};
    border: 1px solid {SIM['border']};
    border-radius: 10px;
    padding: 0.45rem 1rem;
    margin-bottom: 1rem;
}}
.ps {{
    padding: 0.25rem 0.6rem;
    border-radius: 6px;
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.5px;
    color: {SIM['muted']};
    transition: all 0.4s ease;
    white-space: nowrap;
}}
.ps.active {{
    background: {SIM['accent_bg']};
    color: {SIM['accent']};
}}
.ps.done {{
    color: {SIM['green']};
}}
.arr {{
    color: {SIM['border']};
    font-size: 0.75rem;
    padding: 0 0.2rem;
    flex-shrink: 0;
}}

/* ── Phase containers ── */
.ph {{ display: none; }}
.ph.show {{
    display: block;
    animation: fadeIn 0.4s ease;
}}
@keyframes fadeIn {{ from {{ opacity:0 }} to {{ opacity:1 }} }}
@keyframes slideUp {{
    from {{ opacity:0; transform:translateY(20px) }}
    to   {{ opacity:1; transform:translateY(0) }}
}}
@keyframes scaleIn {{
    from {{ opacity:0; transform:scale(0.7) }}
    to   {{ opacity:1; transform:scale(1) }}
}}
@keyframes popIn {{
    from {{ opacity:0; transform:scale(0.5) rotate(-3deg) }}
    to   {{ opacity:1; transform:scale(1) rotate(0deg) }}
}}

/* ── PHASE 1: Terminal ── */
.terminal {{
    background: {'#0D1117' if _dark else '#1A1E2B'};
    border: 1px solid {'#30363D' if _dark else '#2D3340'};
    border-radius: 12px;
    overflow: hidden;
    max-width: 660px;
    margin: 0 auto;
    animation: slideUp 0.4s ease;
}}
.term-head {{
    background: {'#161B22' if _dark else '#22273A'};
    border-bottom: 1px solid {'#30363D' if _dark else '#2D3340'};
    padding: 0.5rem 1rem;
    display: flex;
    align-items: center;
    gap: 0.45rem;
}}
.td {{ width: 10px; height: 10px; border-radius: 50%; }}
.td.r {{ background: #FF5F56; }}
.td.y {{ background: #FFBD2E; }}
.td.g {{ background: #27C93F; }}
.tlabel {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    color: rgba(255,255,255,0.3);
    margin-left: 0.4rem;
}}
.term-body {{
    padding: 1rem 1.25rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    line-height: 1.85;
    min-height: 185px;
    color: #A3E6A3;
}}
.tline .key   {{ color: #6CB6FF; }}
.tline .val   {{ color: #E6EDF3; }}
.tline .prompt {{ color: rgba(163,230,163,0.45); }}
.cursor {{
    display: inline-block;
    width: 7px; height: 13px;
    background: rgba(163,230,163,0.7);
    animation: blink 1s step-end infinite;
    vertical-align: text-bottom;
}}
@keyframes blink {{ 0%,100% {{ opacity:1 }} 50% {{ opacity:0 }} }}

/* ── PHASE 2: Drone grid ── */
.rule-banner {{
    background: {SIM['accent_bg']};
    border: 1px solid {SIM['accent_bdr']};
    border-radius: 8px;
    padding: 0.5rem 1rem;
    text-align: center;
    font-size: 0.73rem;
    font-weight: 600;
    letter-spacing: 0.5px;
    color: {SIM['accent']};
    margin-bottom: 0.75rem;
    transition: all 0.35s ease;
}}
.rule-banner.warn {{
    background: {SIM['red_bg']};
    border-color: {SIM['red_bdr']};
    color: {SIM['red']};
}}
.rule-banner.ok {{
    background: {SIM['green_bg']};
    border-color: {SIM['green_bdr']};
    color: {SIM['green']};
}}
.dgrid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.5rem;
}}
.dc {{
    background: {SIM['surface']};
    border: 1px solid {SIM['border']};
    border-radius: 10px;
    padding: 0.65rem 0.75rem;
    transition: all 0.45s ease;
    position: relative;
    overflow: hidden;
    animation: slideUp 0.35s ease both;
}}
.dc:nth-child(1)  {{ animation-delay: 0.04s; }}
.dc:nth-child(2)  {{ animation-delay: 0.08s; }}
.dc:nth-child(3)  {{ animation-delay: 0.12s; }}
.dc:nth-child(4)  {{ animation-delay: 0.16s; }}
.dc:nth-child(5)  {{ animation-delay: 0.20s; }}
.dc:nth-child(6)  {{ animation-delay: 0.24s; }}
.dc:nth-child(7)  {{ animation-delay: 0.28s; }}
.dc .dname {{
    font-size: 0.73rem;
    font-weight: 700;
    color: {SIM['text']};
    margin-bottom: 0.15rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}
.dc .dtype {{
    font-size: 0.6rem;
    color: {SIM['accent']};
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 0.4rem;
    opacity: 0.75;
}}
.dc .dstats {{ display: flex; flex-wrap: wrap; gap: 3px; }}
.dc .dstat {{
    font-size: 0.57rem;
    color: {SIM['muted']};
    background: {SIM['surface2']};
    border: 1px solid {SIM['border']};
    padding: 2px 5px;
    border-radius: 4px;
}}
.dc.elim {{
    border-color: {SIM['red_bdr']} !important;
    background: {SIM['red_bg']} !important;
    transform: scale(0.88);
    opacity: 0.4;
}}
.dc.elim::after {{
    content: 'ELIMINATED';
    position: absolute;
    top: 50%; left: 50%;
    transform: translate(-50%,-50%) rotate(-10deg);
    font-size: 0.52rem;
    font-weight: 800;
    letter-spacing: 1.5px;
    color: {SIM['red']};
    border: 1.5px solid {SIM['red_bdr']};
    padding: 2px 7px;
    border-radius: 4px;
    white-space: nowrap;
    background: {SIM['bg']};
    opacity: 0.9;
}}

/* ── PHASE 3: Score bars ── */
.sc-title {{
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    color: {SIM['muted']};
    text-align: center;
    margin-bottom: 1rem;
}}
.sc-item {{
    display: flex;
    align-items: center;
    gap: 0.65rem;
    margin-bottom: 0.6rem;
    animation: slideUp 0.35s ease both;
}}
.sc-name {{
    width: 180px;
    font-size: 0.8rem;
    font-weight: 600;
    color: {SIM['text']};
    text-align: right;
    flex-shrink: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}
.sc-name.top {{ color: {SIM['green']}; }}
.sc-wrap {{
    flex: 1;
    background: {SIM['surface2']};
    border: 1px solid {SIM['border']};
    border-radius: 20px;
    height: 24px;
    overflow: hidden;
}}
.sc-bar {{
    height: 100%;
    border-radius: 20px;
    width: 0%;
    transition: width 1.1s cubic-bezier(0.25,0.46,0.45,0.94);
    display: flex;
    align-items: center;
    justify-content: flex-end;
    padding-right: 9px;
    font-size: 0.72rem;
    font-weight: 700;
    color: white;
}}
.sc-bar.top  {{ background: {SIM['green']}; }}
.sc-bar.two  {{ background: {SIM['accent']}; }}
.sc-bar.rest {{ background: {SIM['muted']}; opacity: 0.75; }}
.sc-pct {{
    width: 42px;
    font-size: 0.85rem;
    font-weight: 700;
    text-align: right;
    flex-shrink: 0;
    color: {SIM['muted']};
}}
.sc-pct.top {{ color: {SIM['green']}; }}

/* ── PHASE 4: Winner ── */
.win-wrap {{
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.9rem;
}}
.win-badge {{
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: {SIM['green']};
    animation: slideUp 0.4s ease;
}}
.win-card {{
    background: {SIM['surface']};
    border: 1px solid {SIM['green_bdr']};
    border-radius: 14px;
    padding: 1.4rem 1.6rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1.5rem;
    animation: popIn 0.6s cubic-bezier(0.175,0.885,0.32,1.275);
    width: 100%;
    position: relative;
    overflow: hidden;
}}
.win-card::before {{
    content: '';
    position: absolute;
    top: 0; left: -100%;
    width: 50%; height: 100%;
    background: linear-gradient(90deg, transparent, rgba(74,222,128,0.04), transparent);
    animation: sweep 3s linear infinite;
}}
@keyframes sweep {{ 0% {{ left:-100% }} 100% {{ left:200% }} }}

.wname {{
    font-size: 1.5rem;
    font-weight: 800;
    color: {SIM['text']};
    margin-bottom: 0.2rem;
    letter-spacing: -0.3px;
}}
.wtype {{
    font-size: 0.8rem;
    color: {SIM['muted']};
    margin-bottom: 0.6rem;
}}
.wcam {{
    display: inline-block;
    background: {SIM['accent_bg']};
    border: 1px solid {SIM['accent_bdr']};
    color: {SIM['accent']};
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.7rem;
    font-weight: 600;
    margin: 2px;
}}
.sring {{
    width: 108px;
    height: 108px;
    border-radius: 50%;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    position: relative;
}}
.sring::before {{
    content: '';
    position: absolute;
    inset: 10px;
    border-radius: 50%;
    background: {SIM['surface']};
}}
.snum {{
    position: relative;
    z-index: 1;
    font-size: 1.4rem;
    font-weight: 800;
    color: {SIM['text']};
}}
.slabel {{
    position: relative;
    z-index: 1;
    font-size: 0.55rem;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: {SIM['muted']};
    margin-top: 0.2rem;
}}
.wstats {{
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 0.4rem;
    width: 100%;
}}
.wstat {{
    background: {SIM['surface']};
    border: 1px solid {SIM['border']};
    border-radius: 9px;
    padding: 0.5rem 0.35rem;
    text-align: center;
    animation: slideUp 0.4s ease both;
}}
.wstat .wl {{
    font-size: 0.57rem;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    color: {SIM['muted']};
    margin-bottom: 0.2rem;
}}
.wstat .wv {{
    font-size: 0.83rem;
    font-weight: 700;
    color: {SIM['accent']};
}}
.win-meta {{
    display: flex;
    gap: 1.5rem;
    align-items: center;
}}
.win-meta-item {{ text-align: center; }}
.win-meta-item .wml {{
    font-size: 0.6rem;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    color: {SIM['muted']};
    margin-bottom: 0.15rem;
}}
.win-meta-item .wmv {{
    font-size: 1.35rem;
    font-weight: 800;
}}
.win-meta-item .wmv.accent {{ color: {SIM['accent']}; }}
.win-meta-item .wmv.green  {{ color: {SIM['green']};  }}
.divider {{
    width: 1px;
    height: 36px;
    background: {SIM['border']};
}}
.replay {{
    background: {SIM['surface']};
    border: 1px solid {SIM['border']};
    color: {SIM['muted']};
    border-radius: 8px;
    padding: 0.5rem 1.2rem;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.3px;
    cursor: pointer;
    transition: all 0.2s;
    display: none;
    font-family: 'Inter', sans-serif;
}}
.replay:hover {{
    border-color: {SIM['accent']};
    color: {SIM['accent']};
    background: {SIM['accent_bg']};
}}
#confetti {{
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    pointer-events: none;
    z-index: 99;
}}
</style>

<div id="root">
  <!-- Phase progress bar -->
  <div class="pbar">
    <div class="ps" id="ps1">1 · Mission Input</div>
    <div class="arr">›</div>
    <div class="ps" id="ps2">2 · Rule Filtering</div>
    <div class="arr">›</div>
    <div class="ps" id="ps3">3 · Scoring</div>
    <div class="arr">›</div>
    <div class="ps" id="ps4">4 · Recommendation</div>
  </div>

  <!-- Phase 1: Terminal -->
  <div class="ph" id="ph1">
    <div class="terminal">
      <div class="term-head">
        <span class="td r"></span><span class="td y"></span><span class="td g"></span>
        <span class="tlabel">SAR-DSS MISSION ANALYSIS SYSTEM v2.6</span>
      </div>
      <div class="term-body" id="tbody"><span class="cursor" id="cur"></span></div>
    </div>
  </div>

  <!-- Phase 2: Drone grid -->
  <div class="ph" id="ph2">
    <div class="rule-banner" id="rbanner">INITIALIZING KNOWLEDGE BASE…</div>
    <div class="dgrid" id="dgrid"></div>
  </div>

  <!-- Phase 3: Scoring -->
  <div class="ph" id="ph3">
    <div class="sc-title" id="sctitle">SCORING CANDIDATES WITH WEIGHTED DECISION MATRIX</div>
    <div id="scbars"></div>
  </div>

  <!-- Phase 4: Winner -->
  <div class="ph" id="ph4">
    <div class="win-wrap">
      <div class="win-badge">✦ Mission-Optimal Drone Selected ✦</div>
      <div class="win-card">
        <div style="flex:1;min-width:0;">
          <div class="wname" id="wname"></div>
          <div class="wtype" id="wtype"></div>
          <div id="wcams"></div>
        </div>
        <div style="text-align:center;flex-shrink:0;">
          <div class="sring" id="sring"><div class="snum" id="snum">0%</div><div class="slabel">MATCH SCORE</div></div>
        </div>
      </div>
      <div class="wstats" id="wstats"></div>
      <div class="win-meta" id="wmeta"></div>
      <button class="replay" id="rbtn" onclick="replay()">↻ Replay Simulation</button>
    </div>
  </div>
</div>

<canvas id="confetti"></canvas>

<script>
var DATA = {sim_json};
var STORAGE_KEY = 'sar-dss-sim-seen-' + DATA.run_id;
var SHOULD_RESUME = false;
try {{
    SHOULD_RESUME = localStorage.getItem(STORAGE_KEY) === '1';
}} catch(e) {{}}

function markSeen() {{
    try {{ localStorage.setItem(STORAGE_KEY, '1'); }} catch(e) {{}}
}}

function setPhase(n) {{
    ['ps1','ps2','ps3','ps4'].forEach(function(id, i) {{
        var el = document.getElementById(id);
        el.className = 'ps';
        if (i+1 < n)  el.classList.add('done');
        if (i+1 === n) el.classList.add('active');
    }});
    ['ph1','ph2','ph3','ph4'].forEach(function(id, j) {{
        var p = document.getElementById(id);
        p.className = 'ph';
        if (j+1 === n) p.classList.add('show');
    }});
}}

/* Phase 1 — Terminal */
function phase1() {{
    setPhase(1);
    var body = document.getElementById('tbody');
    var cur  = document.getElementById('cur');
    var s    = DATA.scenario;
    var params = [
        ['EMERGENCY TYPE',  s.emergency],
        ['WEATHER',         s.weather],
        ['TIME OF DAY',     s.time_of_day],
        ['ALTITUDE',        s.altitude + ' m'],
        ['AREA TO COVER',   s.area + ' km²'],
        ['TRAVEL DISTANCE', s.distance + ' km'],
        ['SUPPLY WEIGHT',   s.supply_weight + ' kg'],
        ['BUDGET LIMIT',    '€' + s.budget]
    ];
    setTimeout(function() {{
        var bl = document.createElement('div'); bl.className='tline';
        bl.innerHTML = '<span class="prompt">SAR-DSS &gt;</span> MISSION PARAMETERS RECEIVED';
        body.insertBefore(bl, cur);
    }}, 200);
    params.forEach(function(pair, i) {{
        setTimeout(function() {{
            var ln = document.createElement('div'); ln.className='tline';
            ln.innerHTML = '<span class="prompt">&nbsp;&nbsp;&gt;&gt;</span> <span class="key">'
                         + pair[0] + '</span>: <span class="val">' + pair[1] + '</span>';
            body.insertBefore(ln, cur);
        }}, 500 + i*280);
    }});
    var t = 500 + params.length*280 + 350;
    setTimeout(function() {{
        var p1 = document.createElement('div'); p1.className='tline';
        p1.innerHTML = '<span class="prompt">SAR-DSS &gt;</span> <span style="color:#6CB6FF;">LOADING DRONE DATABASE… '
                     + DATA.drones.length + ' CANDIDATES FOUND</span>';
        body.insertBefore(p1, cur);
    }}, t);
    setTimeout(function() {{
        var p2 = document.createElement('div'); p2.className='tline';
        p2.innerHTML = '<span class="prompt">SAR-DSS &gt;</span> <span style="color:#6CB6FF;">ACTIVATING KNOWLEDGE BASE RULES…</span>';
        body.insertBefore(p2, cur);
    }}, t+350);
    setTimeout(phase2, t+1100);
}}

/* Phase 2 — Rule filtering */
function phase2() {{
    setPhase(2);
    var grid = document.getElementById('dgrid');
    DATA.drones.forEach(function(d, idx) {{
        var card = document.createElement('div');
        card.className = 'dc'; card.id = 'dc'+idx;
        var ico = d.is_plane ? '✈' : '🚁';
        card.innerHTML =
            '<div class="dname">' + ico + ' ' + d.name + '</div>' +
            '<div class="dtype">' + d.type + '</div>' +
            '<div class="dstats">' +
              '<span class="dstat">💨' + d.wind_resistance + 'm/s</span>' +
              '<span class="dstat">⛰' + Math.round(d.max_altitude/100)/10 + 'km</span>' +
              '<span class="dstat">🔋' + d.battery_life + 'min</span>' +
              '<span class="dstat">📡' + d.max_range + 'km</span>' +
              '<span class="dstat">€' + d.cost + '</span>' +
            '</div>';
        grid.appendChild(card);
    }});

    var elims = [];
    DATA.drones.forEach(function(d,i) {{ if(d.eliminated) elims.push({{d:d,i:i}}); }});
    var banner = document.getElementById('rbanner');

    setTimeout(function() {{
        banner.textContent = 'APPLYING EXPERT RULES TO ' + DATA.drones.length + ' CANDIDATES…';
    }}, 600);

    var delay = 1200;
    elims.forEach(function(item) {{
        setTimeout(function() {{
            banner.className = 'rule-banner warn';
            var r = item.d.reasons.length > 0 ? item.d.reasons[0] : 'Failed requirement';
            banner.innerHTML = '✗ RULE VIOLATION — ' + r;
        }}, delay);
        setTimeout(function() {{
            var card = document.getElementById('dc'+item.i);
            if (card) card.classList.add('elim');
        }}, delay+280);
        delay += 950;
    }});
    setTimeout(function() {{
        banner.className = 'rule-banner ok';
        banner.textContent = '✓ FILTERING COMPLETE: ' + DATA.pass_count
                           + ' QUALIFY  ·  ' + DATA.elim_count + ' ELIMINATED';
    }}, delay);
    setTimeout(phase3, delay+900);
}}

/* Phase 3 — Scoring */
function phase3() {{
    setPhase(3);
    var title = document.getElementById('sctitle');
    title.textContent = 'SCORING ' + DATA.pass_count + ' CANDIDATES WITH WEIGHTED DECISION MATRIX';
    var cont = document.getElementById('scbars');
    var survivors = DATA.drones
        .filter(function(d){{ return !d.eliminated; }})
        .sort(function(a,b){{ return b.score-a.score; }});
    survivors.forEach(function(d, i) {{
        var item = document.createElement('div');
        item.className = 'sc-item'; item.style.animationDelay=(i*0.1)+'s';
        var cls = i===0?'top':i===1?'two':'rest';
        var ico = d.is_plane?'✈':'🚁';
        item.innerHTML =
            '<div class="sc-name'+(i===0?' top':'')+'">'+ico+' '+d.name+'</div>'+
            '<div class="sc-wrap"><div class="sc-bar '+cls+'" id="bar'+i+'"></div></div>'+
            '<div class="sc-pct'+(i===0?' top':'')+'" id="pct'+i+'">0%</div>';
        cont.appendChild(item);
    }});
    setTimeout(function() {{
        survivors.forEach(function(d, i) {{
            var bar = document.getElementById('bar'+i);
            var pct = document.getElementById('pct'+i);
            if (bar) bar.style.width = d.score+'%';
            var cur=0, target=d.score;
            var t = setInterval(function() {{
                cur = Math.min(cur+target/40, target);
                if (pct) pct.textContent = Math.round(cur)+'%';
                if (cur>=target) clearInterval(t);
            }}, 30);
        }});
    }}, 400);
    setTimeout(phase4, 3000);
}}

/* Phase 4 — Winner */
function phase4() {{
    setPhase(4);
    var top = DATA.top;
    var ico = top.is_plane ? '✈ ' : '🚁 ';
    document.getElementById('wname').textContent = ico + top.name;
    document.getElementById('wtype').textContent = top.type + ' · ' + top.desc;
    var camsEl = document.getElementById('wcams');
    top.cams.forEach(function(c) {{
        var sp = document.createElement('span'); sp.className='wcam'; sp.textContent=c; camsEl.appendChild(sp);
    }});
    /* score ring */
    var ring=document.getElementById('sring'), numEl=document.getElementById('snum');
    var ringColor = '{SIM['green']}';
    var cur=0, target=top.score;
    var ringTimer = setInterval(function() {{
        cur = Math.min(cur+target/55, target);
        ring.style.background = 'conic-gradient('+ringColor+' 0%, '+ringColor+' '+cur+'%, {SIM['border']} '+cur+'%)';
        numEl.textContent = Math.round(cur)+'%';
        if(cur>=target) clearInterval(ringTimer);
    }}, 25);
    /* stats */
    var statsEl=document.getElementById('wstats');
    var stats=[
        ['Wind',     top.wind_resistance+' m/s'],
        ['Altitude', Math.round(top.max_altitude/100)/10+' km'],
        ['Battery',  top.battery_life+' min'],
        ['Range',    top.max_range+' km'],
        ['Payload',  top.payload+' kg'],
        ['Cost',     '€'+top.cost]
    ];
    stats.forEach(function(s,i) {{
        var el=document.createElement('div'); el.className='wstat'; el.style.animationDelay=(i*0.08+0.3)+'s';
        el.innerHTML='<div class="wl">'+s[0]+'</div><div class="wv">'+s[1]+'</div>';
        statsEl.appendChild(el);
    }});
    /* meta */
    var metaEl=document.getElementById('wmeta');
    metaEl.innerHTML=
        '<div class="win-meta-item"><div class="wml">DRONES NEEDED</div><div class="wmv accent">'+DATA.num_drones+'</div></div>'+
        '<div class="divider"></div>'+
        '<div class="win-meta-item"><div class="wml">TOTAL DEPLOYMENT COST</div><div class="wmv green">€'+DATA.total_cost+'</div></div>';
    setTimeout(confetti, 500);
    setTimeout(function() {{ document.getElementById('rbtn').style.display='inline-block'; }}, 2200);
}}

function renderCompleted() {{
    setPhase(4);
    var top = DATA.top;
    var planeIcon = String.fromCharCode(0x2708) + ' ';
    var droneIcon = String.fromCodePoint(0x1f681) + ' ';
    var bullet = ' ' + String.fromCharCode(0xb7) + ' ';
    var euro = String.fromCharCode(0x20ac);
    var ico = top.is_plane ? 'âœˆ ' : 'ðŸš ';
    document.getElementById('wname').textContent = ico + top.name;
    document.getElementById('wtype').textContent = top.type + ' Â· ' + top.desc;

    document.getElementById('wname').textContent = (top.is_plane ? planeIcon : droneIcon) + top.name;
    document.getElementById('wtype').textContent = top.type + bullet + top.desc;

    var camsEl = document.getElementById('wcams');
    camsEl.innerHTML = '';
    top.cams.forEach(function(c) {{
        var sp = document.createElement('span');
        sp.className = 'wcam';
        sp.textContent = c;
        camsEl.appendChild(sp);
    }});

    document.getElementById('sring').style.background =
        'conic-gradient({SIM['green']} 0%, {SIM['green']} ' + top.score + '%, {SIM['border']} ' + top.score + '%)';
    document.getElementById('snum').textContent = Math.round(top.score) + '%';

    var statsEl = document.getElementById('wstats');
    statsEl.innerHTML = '';
    [
        ['Wind',     top.wind_resistance+' m/s'],
        ['Altitude', Math.round(top.max_altitude/100)/10+' km'],
        ['Battery',  top.battery_life+' min'],
        ['Range',    top.max_range+' km'],
        ['Payload',  top.payload+' kg'],
        ['Cost',     'â‚¬'+top.cost]
    ].forEach(function(s) {{
        var el = document.createElement('div');
        el.className = 'wstat';
        el.style.opacity = '1';
        el.style.transform = 'none';
        el.innerHTML = '<div class="wl">'+s[0]+'</div><div class="wv">'+s[1]+'</div>';
        statsEl.appendChild(el);
    }});
    var statValues = statsEl.querySelectorAll('.wv');
    if (statValues.length) statValues[statValues.length - 1].textContent = euro + top.cost;

    document.getElementById('wmeta').innerHTML =
        '<div class="win-meta-item"><div class="wml">DRONES NEEDED</div><div class="wmv accent">'+DATA.num_drones+'</div></div>'+
        '<div class="divider"></div>'+
        '<div class="win-meta-item"><div class="wml">TOTAL DEPLOYMENT COST</div><div class="wmv green">â‚¬'+DATA.total_cost+'</div></div>';
    document.querySelector('#wmeta .wmv.green').textContent = euro + DATA.total_cost;
    document.getElementById('rbtn').style.display = 'inline-block';
}}

/* Confetti */
function confetti() {{
    var cv=document.getElementById('confetti');
    var ctx=cv.getContext('2d');
    cv.width=window.innerWidth||900; cv.height=window.innerHeight||700;
    var colors=['{SIM['green']}','{SIM['accent']}','#FFFFFF','#FBBF24','#F87171'];
    var parts=[];
    for(var i=0;i<120;i++) {{
        parts.push({{
            x: cv.width/2+(Math.random()-0.5)*280,
            y: cv.height*0.35,
            vx:(Math.random()-0.5)*11, vy:(Math.random()*-8-2),
            sz:Math.random()*6+3,
            c:colors[Math.floor(Math.random()*colors.length)],
            rot:Math.random()*360, rs:(Math.random()-0.5)*8,
            g:0.25, a:1
        }});
    }}
    var frames=0;
    function draw() {{
        ctx.clearRect(0,0,cv.width,cv.height);
        parts.forEach(function(p) {{
            p.x+=p.vx; p.y+=p.vy; p.vy+=p.g; p.rot+=p.rs;
            p.a=Math.max(0,p.a-0.007);
            ctx.save(); ctx.globalAlpha=p.a;
            ctx.translate(p.x,p.y); ctx.rotate(p.rot*Math.PI/180);
            ctx.fillStyle=p.c; ctx.fillRect(-p.sz/2,-p.sz/4,p.sz,p.sz/2);
            ctx.restore();
        }});
        frames++;
        if(frames<210) requestAnimationFrame(draw);
        else ctx.clearRect(0,0,cv.width,cv.height);
    }}
    draw();
}}

/* Replay */
function replay() {{
    markSeen();
    document.getElementById('tbody').innerHTML='<span class="cursor" id="cur"></span>';
    document.getElementById('dgrid').innerHTML='';
    document.getElementById('scbars').innerHTML='';
    document.getElementById('wname').textContent='';
    document.getElementById('wtype').textContent='';
    document.getElementById('wcams').innerHTML='';
    document.getElementById('wstats').innerHTML='';
    document.getElementById('wmeta').innerHTML='';
    document.getElementById('snum').textContent='0%';
    document.getElementById('sring').style.background='conic-gradient({SIM['green']} 0%, {SIM['border']} 0%)';
    document.getElementById('rbtn').style.display='none';
    phase1();
}}

if (SHOULD_RESUME) {{
    renderCompleted();
}} else {{
    markSeen();
    phase1();
}}
</script>
</html>""", height=680)

        # ── DETAILED ANALYSIS ──────────────────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)

        # Section divider
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:0.75rem;margin:0.5rem 0 1rem;">
            <div style="flex:1;height:1px;background:{T['border']};"></div>
            <div style="font-size:0.68rem;font-weight:600;letter-spacing:1px;
                        text-transform:uppercase;color:{T['muted']};">Detailed Analysis</div>
            <div style="flex:1;height:1px;background:{T['border']};"></div>
        </div>
        """, unsafe_allow_html=True)

        col_chart, col_sum = st.columns([3, 2], gap="large")

        with col_chart:
            st.markdown(f"<p style='color:{T['muted']};font-size:0.72rem;font-weight:600;"
                        f"letter-spacing:0.8px;text-transform:uppercase;margin-bottom:0.5rem;'>"
                        f"Score Comparison</p>", unsafe_allow_html=True)

            names  = [d["name"] for d in scored]
            scores = [d["score"] for d in scored]
            bar_colors = []
            for i in range(len(scored)):
                if i == 0:   bar_colors.append(T["green"])
                elif i == 1: bar_colors.append(T["accent"])
                else:        bar_colors.append(T["muted"])

            fig = go.Figure(go.Bar(
                x=scores, y=names, orientation="h",
                marker=dict(color=bar_colors, line=dict(width=0), opacity=0.85),
                text=[f"{s}%" for s in scores],
                textposition="inside", insidetextanchor="end",
                textfont=dict(color="white", size=12, family="Inter"),
            ))
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor=T["surface2"],
                margin=dict(l=10, r=20, t=10, b=10),
                xaxis=dict(
                    range=[0, 100],
                    showgrid=True,
                    gridcolor=T["border"],
                    ticksuffix="%", title="",
                    color=T["muted"],
                    tickfont=dict(color=T["muted"], size=11),
                ),
                yaxis=dict(
                    autorange="reversed",
                    showgrid=False, title="",
                    tickfont=dict(color=T["text"], size=11),
                ),
                height=260,
                font=dict(family="Inter", size=12, color=T["text"]),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_sum:
            st.markdown(f"<p style='color:{T['muted']};font-size:0.72rem;font-weight:600;"
                        f"letter-spacing:0.8px;text-transform:uppercase;margin-bottom:0.5rem;'>"
                        f"Mission Summary</p>", unsafe_allow_html=True)

            wi = {"Clear": "☀️", "Windy": "💨", "Storm": "⛈️", "Blizzard": "🌨️"}.get(weather, "")
            rows = [
                ("Emergency",  emergency),
                ("Weather",    f"{wi} {weather}"),
                ("Time",       f"{'🌙' if time_of_day=='Night' else '☀️'} {time_of_day}"),
                ("Altitude",   f"{scenario['altitude']:,} m"),
                ("Area",       f"{scenario['area']} km²"),
                ("Distance",   f"{scenario['distance']} km"),
            ]
            rows_html = "".join([
                f"<tr>"
                f"<td style='color:{T['muted']};padding:0.4rem 0;font-size:0.83rem;'>{k}</td>"
                f"<td style='font-weight:600;text-align:right;color:{T['text']};font-size:0.83rem;'>{v}</td>"
                f"</tr>"
                for k, v in rows
            ])

            st.markdown(f"""
            <div style="background:{T['surface']};border:1px solid {T['border']};
                        border-radius:12px;padding:1.25rem 1.4rem;">
              <table style="width:100%;border-collapse:collapse;">
                {rows_html}
                <tr style="border-top:1px solid {T['border']};">
                  <td style="color:{T['muted']};padding:0.65rem 0 0.25rem;
                             font-size:0.7rem;font-weight:600;letter-spacing:0.8px;
                             text-transform:uppercase;">Drones Needed</td>
                  <td style="text-align:right;font-size:1.4rem;font-weight:800;
                             color:{T['accent']};padding-top:0.3rem;">{num_drones}</td>
                </tr>
                <tr>
                  <td style="color:{T['muted']};padding:0.25rem 0;
                             font-size:0.7rem;font-weight:600;letter-spacing:0.8px;
                             text-transform:uppercase;">Total Cost</td>
                  <td style="text-align:right;font-size:1.4rem;font-weight:800;
                             color:{T['green']};">€{total_cost:,}</td>
                </tr>
              </table>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Alternative drones ──
        if len(scored) > 1:
            with st.expander(f"📋  {len(scored)-1} alternative drone(s)"):
                for d in scored[1:]:
                    ai = "✈️" if "Fixed" in d["type"] else "🚁"
                    st.markdown(f"""
                    <div style="background:{T['surface2']};border:1px solid {T['border']};
                                border-left:3px solid {T['accent']};border-radius:10px;
                                padding:0.85rem 1.1rem;margin:0.35rem 0;
                                display:flex;justify-content:space-between;align-items:center;">
                      <div>
                        <div style="font-weight:600;color:{T['text']};font-size:0.875rem;">
                            {ai} {d['name']}
                        </div>
                        <div style="color:{T['muted']};font-size:0.78rem;margin-top:0.2rem;">
                            {d['description']}
                        </div>
                      </div>
                      <div style="background:{T['accent_bg']};border:1px solid {T['accent_border']};
                                  color:{T['accent']};padding:4px 14px;border-radius:20px;
                                  font-weight:700;font-size:0.9rem;flex-shrink:0;margin-left:1rem;">
                        {d['score']}%
                      </div>
                    </div>""", unsafe_allow_html=True)

        # ── Eliminated drones ──
        if eliminated:
            with st.expander(f"❌  {len(eliminated)} drone(s) eliminated by rules"):
                for d in eliminated:
                    ei = "✈️" if "Fixed" in d["type"] else "🚁"
                    reasons_html = "".join([
                        f"<div style='color:{T['red']};font-size:0.76rem;margin-top:0.2rem;opacity:0.85;'>· {r}</div>"
                        for r in d["reasons"]
                    ])
                    st.markdown(f"""
                    <div style="background:{T['surface2']};border:1px solid {T['border']};
                                border-left:3px solid {T['red']};border-radius:10px;
                                padding:0.85rem 1.1rem;margin:0.35rem 0;">
                      <div style="font-weight:600;color:{T['text']};font-size:0.875rem;
                                  opacity:0.75;">{ei} {d['name']}</div>
                      {reasons_html}
                    </div>""", unsafe_allow_html=True)
