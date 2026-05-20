import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
import json

from drones import DRONES
from engine import apply_rules, score_drones, get_num_drones

st.set_page_config(page_title="SAR Drone DSS", layout="wide", initial_sidebar_state="expanded")

# ── GLOBAL CSS ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
* { font-family: 'Inter', sans-serif !important; box-sizing: border-box; }
[data-testid="collapsedControl"] { display: none !important; }
[data-testid="stSidebarCollapseButton"] { display: none !important; }
section[data-testid="stSidebar"] { display: block !important; transform: translateX(0) !important; min-width: 320px !important; width: 320px !important; }
section[data-testid="stSidebar"] > div { width: 320px !important; }
.stApp {
    background: linear-gradient(135deg, #020818 0%, #050f25 50%, #0a1628 100%) !important;
    min-height: 100vh;
}
.stApp::before {
    content: ''; position: fixed; top: -50%; left: -50%; width: 200%; height: 200%;
    background:
        radial-gradient(ellipse at 15% 50%, rgba(0,195,255,0.07) 0%, transparent 55%),
        radial-gradient(ellipse at 85% 20%, rgba(120,40,200,0.06) 0%, transparent 55%),
        radial-gradient(ellipse at 55% 85%, rgba(0,255,136,0.04) 0%, transparent 55%);
    animation: rotateGlow 25s linear infinite; pointer-events: none; z-index: 0;
}
@keyframes rotateGlow { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
#MainMenu { visibility: hidden; } footer { visibility: hidden; } header { visibility: hidden; }
.block-container { padding-top: 1.5rem !important; position: relative; z-index: 1; }
[data-testid="stSidebar"] {
    background: rgba(2,8,24,0.97) !important;
    border-right: 1px solid rgba(0,195,255,0.12) !important;
    backdrop-filter: blur(30px);
}
[data-testid="stSidebar"] * { color: #e0eaff !important; }
[data-testid="stSidebar"] hr { border-color: rgba(0,195,255,0.15) !important; }
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: rgba(0,195,255,0.07) !important; border: 1px solid rgba(0,195,255,0.2) !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] * { color: white !important; }
[data-testid="stSidebar"] li { color: #0a1628 !important; }
[data-testid="stSidebar"] .stSlider [data-baseweb="thumb"] { background: #00c3ff !important; box-shadow: 0 0 10px rgba(0,195,255,0.6) !important; }
[data-testid="stSidebar"] .stSlider [data-baseweb="track"] { background: rgba(0,195,255,0.15) !important; }
[data-testid="stSidebar"] .stSlider [data-baseweb="track-fill"] { background: #00c3ff !important; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
    background: rgba(0,195,255,0.07); border: 1px solid rgba(0,195,255,0.2);
    border-radius: 8px; padding: 4px 14px; margin: 2px; transition: all 0.2s;
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover { background: rgba(0,195,255,0.15); }
div.stButton > button {
    background: linear-gradient(135deg, rgba(0,195,255,0.15), rgba(0,100,255,0.2));
    color: #00c3ff !important; border: 1px solid rgba(0,195,255,0.4) !important;
    border-radius: 12px; padding: 0.8rem 1.5rem; font-size: 1rem; font-weight: 700;
    width: 100%; letter-spacing: 1px; text-transform: uppercase; transition: all 0.3s ease;
    position: relative; overflow: hidden;
}
div.stButton > button::before {
    content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%;
    background: linear-gradient(45deg, transparent 30%, rgba(0,195,255,0.1) 50%, transparent 70%);
    animation: shimmer 2.5s infinite;
}
@keyframes shimmer { 0% { transform: translateX(-100%) rotate(45deg); } 100% { transform: translateX(100%) rotate(45deg); } }
div.stButton > button:hover {
    background: linear-gradient(135deg, rgba(0,195,255,0.3), rgba(0,100,255,0.35));
    box-shadow: 0 0 25px rgba(0,195,255,0.4); transform: translateY(-2px);
    border-color: rgba(0,195,255,0.7) !important;
}
[data-testid="stExpander"] {
    background: rgba(255,255,255,0.02) !important; border: 1px solid rgba(255,255,255,0.07) !important; border-radius: 14px !important;
}
[data-testid="stExpander"] summary { color: rgba(255,255,255,0.7) !important; }
[data-testid="stMetricValue"] { color: #00c3ff !important; font-weight: 700 !important; }
[data-testid="stMetricLabel"] { color: rgba(255,255,255,0.5) !important; font-size: 0.75rem !important; }
</style>
""", unsafe_allow_html=True)

# ── PARTICLE BACKGROUND ─────────────────────────────────────────────────────────
components.html("""
<script>
(function() {
    try {
        const p = window.parent;
        if (p.document.getElementById('sar-canvas')) return;
        const canvas = p.document.createElement('canvas');
        canvas.id = 'sar-canvas';
        canvas.style.cssText = 'position:fixed;top:0;left:0;width:100vw;height:100vh;pointer-events:none;z-index:0;opacity:0.5';
        p.document.body.prepend(canvas);
        const ctx = canvas.getContext('2d');
        let W = canvas.width = p.innerWidth, H = canvas.height = p.innerHeight;
        const pts = Array.from({length: 100}, () => ({
            x: Math.random()*W, y: Math.random()*H,
            vx: (Math.random()-0.5)*0.4, vy: (Math.random()-0.5)*0.4,
            r: Math.random()*1.5+0.3, a: Math.random()*0.5+0.2,
            c: Math.random()>0.5?'0,195,255':'100,80,255'
        }));
        function draw() {
            ctx.clearRect(0,0,W,H);
            for (let i=0;i<pts.length;i++) {
                const a=pts[i]; a.x+=a.vx; a.y+=a.vy;
                if(a.x<0)a.x=W; if(a.x>W)a.x=0; if(a.y<0)a.y=H; if(a.y>H)a.y=0;
                ctx.beginPath(); ctx.arc(a.x,a.y,a.r,0,Math.PI*2);
                ctx.fillStyle='rgba('+a.c+','+a.a+')'; ctx.fill();
                for(let j=i+1;j<pts.length;j++){
                    const b=pts[j],dx=a.x-b.x,dy=a.y-b.y,d=Math.sqrt(dx*dx+dy*dy);
                    if(d<110){ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);
                    ctx.strokeStyle='rgba(0,195,255,'+(0.1*(1-d/110))+')';ctx.lineWidth=0.5;ctx.stroke();}
                }
            }
            requestAnimationFrame(draw);
        }
        draw();
        p.addEventListener('resize',()=>{W=canvas.width=p.innerWidth;H=canvas.height=p.innerHeight;});
    } catch(e){}
})();
</script>
""", height=0)

# ── SIDEBAR ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center;padding:1rem 0 0.5rem;">
        <div style="font-size:2.5rem;animation:float 3s ease-in-out infinite;display:inline-block;">🚁</div>
        <div style="color:#00c3ff;font-weight:800;font-size:1.1rem;letter-spacing:2px;text-transform:uppercase;margin-top:0.3rem;">SAR DSS</div>
        <div style="color:rgba(255,255,255,0.4);font-size:0.72rem;letter-spacing:1px;">DRONE SELECTION SYSTEM</div>
    </div>
    <style>@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-8px)}}</style>
    """, unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("<p style='color:rgba(0,195,255,0.8);font-size:0.72rem;letter-spacing:2px;text-transform:uppercase;margin-bottom:0.3rem;'>Emergency Type</p>", unsafe_allow_html=True)
    emergency = st.selectbox("et", ["Missing Person","Injured Person","Altitude Sickness","Supply Delivery"], label_visibility="collapsed")

    st.markdown("<p style='color:rgba(0,195,255,0.8);font-size:0.72rem;letter-spacing:2px;text-transform:uppercase;margin:0.6rem 0 0.3rem;'>Weather Condition</p>", unsafe_allow_html=True)
    weather = st.selectbox("wc", ["Clear","Windy","Storm","Blizzard"], label_visibility="collapsed")

    st.markdown("<p style='color:rgba(0,195,255,0.8);font-size:0.72rem;letter-spacing:2px;text-transform:uppercase;margin:0.6rem 0 0.3rem;'>Time of Day</p>", unsafe_allow_html=True)
    time_of_day = st.radio("tod", ["Day","Night"], horizontal=True, label_visibility="collapsed")
    st.markdown("---")

    for label, key, lo, hi, default, step in [
        ("Altitude (metres)",       "alt",  100,  5000, 1500, 100),
        ("Area to Cover (km²)",     "area", 0.5,  30.0, 5.0,  0.5),
        ("Distance to Travel (km)", "dist", 0.5,  25.0, 5.0,  0.5),
        ("Supply Weight (kg)",      "sup",  0.0,  30.0, 0.0,  0.5),
        ("Budget per Drone (€)",    "bud",  100,  1000, 500,  25 ),
    ]:
        st.markdown(f"<p style='color:rgba(0,195,255,0.8);font-size:0.72rem;letter-spacing:2px;text-transform:uppercase;margin:0.6rem 0 0.3rem;'>{label}</p>", unsafe_allow_html=True)
        locals()[key] = st.slider(key, lo, hi, default, step, label_visibility="collapsed")

    st.markdown("---")
    run = st.button("⚡  RUN DSS SIMULATION")

# ── HEADER ──────────────────────────────────────────────────────────────────────
components.html("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800;900&display=swap');
  *{font-family:'Inter',sans-serif;box-sizing:border-box;margin:0;}
  body{background:transparent;overflow:hidden;}
  .banner{
    background:linear-gradient(135deg,rgba(0,195,255,0.08) 0%,rgba(0,50,120,0.15) 50%,rgba(120,40,200,0.06) 100%);
    border:1px solid rgba(0,195,255,0.15);border-radius:20px;padding:2rem 2.5rem;
    position:relative;overflow:hidden;animation:slideUp 0.7s ease forwards;backdrop-filter:blur(20px);
  }
  .banner::before{content:'';position:absolute;top:0;left:-100%;width:60%;height:100%;
    background:linear-gradient(90deg,transparent,rgba(0,195,255,0.06),transparent);animation:scanline 4s linear infinite;}
  @keyframes scanline{0%{left:-100%}100%{left:200%}}
  @keyframes slideUp{from{opacity:0;transform:translateY(30px)}to{opacity:1;transform:translateY(0)}}
  .meta{font-size:0.72rem;letter-spacing:2.5px;text-transform:uppercase;color:rgba(0,195,255,0.6);margin-bottom:0.5rem;}
  .title{font-size:2rem;font-weight:900;color:white;letter-spacing:-0.5px;margin-bottom:0.3rem;}
  .title span{color:#00c3ff;}
  .sub{font-size:0.88rem;color:rgba(255,255,255,0.45);}
  .dots{position:absolute;right:2.5rem;top:50%;transform:translateY(-50%);display:flex;gap:8px;}
  .dot{width:10px;height:10px;border-radius:50%;animation:blink 1.5s ease-in-out infinite;}
  .dot:nth-child(1){background:#00ff88;animation-delay:0s;box-shadow:0 0 10px #00ff88;}
  .dot:nth-child(2){background:#00c3ff;animation-delay:0.3s;box-shadow:0 0 10px #00c3ff;}
  .dot:nth-child(3){background:#7830c8;animation-delay:0.6s;box-shadow:0 0 10px #7830c8;}
  @keyframes blink{0%,100%{opacity:1;transform:scale(1)}50%{opacity:0.3;transform:scale(0.7)}}
</style>
<div class="banner">
  <div class="meta">BTH &nbsp;·&nbsp; DV2573 &nbsp;·&nbsp; Group 2 &nbsp;·&nbsp; Spring 2026</div>
  <div class="title">🚁 SAR <span>Drone Selection</span> DSS</div>
  <div class="sub">Intelligent Decision Support System for Search and Rescue Operations</div>
  <div class="dots"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>
</div>
""", height=130)

# ── WELCOME ─────────────────────────────────────────────────────────────────────
if not run:
    components.html("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
  *{font-family:'Inter',sans-serif;box-sizing:border-box;margin:0;}
  body{background:transparent;overflow:hidden;}
  .grid{display:grid;grid-template-columns:repeat(3,1fr);gap:1.2rem;margin-bottom:1.5rem;}
  .card{background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:18px;
        padding:1.8rem;backdrop-filter:blur(20px);transition:all 0.4s cubic-bezier(0.175,0.885,0.32,1.275);
        animation:slideUp 0.6s ease forwards;opacity:0;cursor:default;position:relative;overflow:hidden;}
  .card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:var(--accent);box-shadow:0 0 15px var(--accent);}
  .card:nth-child(1){--accent:#00c3ff;animation-delay:0.1s;}
  .card:nth-child(2){--accent:#00ff88;animation-delay:0.2s;}
  .card:nth-child(3){--accent:#7830c8;animation-delay:0.3s;}
  .card:hover{transform:perspective(800px) rotateX(-3deg) rotateY(3deg) translateY(-10px);
              border-color:var(--accent);box-shadow:0 20px 50px rgba(0,0,0,0.4);}
  @keyframes slideUp{from{opacity:0;transform:translateY(30px)}to{opacity:1;transform:translateY(0)}}
  .icon{font-size:2.2rem;margin-bottom:0.8rem;}
  .ttl{font-size:1rem;font-weight:700;color:white;margin-bottom:0.5rem;}
  .txt{font-size:0.85rem;color:rgba(255,255,255,0.45);line-height:1.6;}
  .hint{background:rgba(0,195,255,0.05);border:1px solid rgba(0,195,255,0.15);border-radius:12px;
        padding:1rem 1.4rem;color:rgba(255,255,255,0.5);font-size:0.87rem;
        animation:slideUp 0.6s 0.4s ease forwards;opacity:0;}
  .hint strong{color:#00c3ff;}
</style>
<div class="grid">
  <div class="card"><div class="icon">🎬</div><div class="ttl">Step-by-Step Simulation</div>
    <div class="txt">Watch the DSS work live. Mission parameters feed in, rules fire one by one, drones get eliminated, survivors are scored, and the winner is revealed.</div></div>
  <div class="card"><div class="icon">🧠</div><div class="ttl">Knowledge Base Filtering</div>
    <div class="txt">Expert rules automatically remove drones that cannot handle the weather, altitude, range, payload, or budget constraints of your mission.</div></div>
  <div class="card"><div class="icon">📊</div><div class="ttl">Weighted Decision Matrix</div>
    <div class="txt">Remaining drones are scored across 8 criteria. Weights shift dynamically based on mission type — blizzard boosts wind score, night ops boost camera score.</div></div>
</div>
<div class="hint">Set mission parameters in the sidebar and click <strong>⚡ RUN DSS SIMULATION</strong> to watch the decision process unfold.</div>
""", height=340)

# ── SIMULATION ──────────────────────────────────────────────────────────────────
else:
    scenario = {
        "emergency":     emergency,
        "weather":       weather,
        "time_of_day":   time_of_day,
        "altitude":      locals().get("alt",  1500),
        "area":          locals().get("area", 5.0),
        "distance":      locals().get("dist", 5.0),
        "supply_weight": locals().get("sup",  0.0),
        "budget":        locals().get("bud",  500),
    }

    passed, eliminated = apply_rules(DRONES, scenario)

    if not passed:
        components.html("""
<style>body{background:transparent;margin:0;font-family:'Inter',sans-serif;}
.box{background:rgba(231,76,60,0.08);border:2px dashed rgba(231,76,60,0.4);
     border-radius:18px;padding:2.5rem;text-align:center;}
h3{color:#e74c3c;margin:0 0 0.5rem;}p{color:rgba(255,255,255,0.4);margin:0;font-size:0.9rem;}</style>
<div class="box"><div style="font-size:3rem;margin-bottom:0.5rem;">🚫</div>
<h3>No Drones Meet the Requirements</h3>
<p>Try adjusting budget, supply weight, or distance.</p></div>
""", height=200)

    else:
        scored     = score_drones(passed, scenario)
        top        = scored[0]
        num_drones = get_num_drones(locals().get("area", 5.0))
        total_cost = num_drones * top["cost"]

        # ── build simulation JSON ──────────────────────────────────────────
        score_map   = {d["name"]: d["score"]   for d in scored}
        elim_map    = {d["name"]: d["reasons"]  for d in eliminated}
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
            "drones": sim_drones,
            "scenario": {
                "emergency":     scenario["emergency"],
                "weather":       scenario["weather"],
                "time_of_day":   scenario["time_of_day"],
                "altitude":      scenario["altitude"],
                "area":          scenario["area"],
                "distance":      scenario["distance"],
                "supply_weight": scenario["supply_weight"],
                "budget":        scenario["budget"],
            },
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

        # ── CINEMATIC SIMULATION COMPONENT ────────────────────────────────
        components.html(f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800;900&family=JetBrains+Mono:wght@400;700&display=swap');
*{{font-family:'Inter',sans-serif;box-sizing:border-box;margin:0;padding:0;}}
body{{background:transparent;color:white;overflow:hidden;padding:4px 2px;}}

/* ── Phase bar ── */
.pbar{{display:flex;justify-content:center;align-items:center;padding:0.5rem 1rem;
       gap:0;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);
       border-radius:12px;margin-bottom:1rem;}}
.ps{{padding:0.3rem 0.7rem;border-radius:8px;font-size:0.68rem;font-weight:700;
     letter-spacing:1.5px;text-transform:uppercase;color:rgba(255,255,255,0.2);
     transition:all 0.5s ease;white-space:nowrap;}}
.ps.active{{background:rgba(0,195,255,0.15);color:#00c3ff;box-shadow:0 0 15px rgba(0,195,255,0.2);}}
.ps.done{{color:rgba(0,255,136,0.6);}}
.arr{{color:rgba(255,255,255,0.12);font-size:0.8rem;padding:0 0.25rem;}}

/* ── Phase containers ── */
.ph{{display:none;}}
.ph.show{{display:block;animation:fadeIn 0.5s ease;}}
@keyframes fadeIn{{from{{opacity:0}}to{{opacity:1}}}}
@keyframes slideUp{{from{{opacity:0;transform:translateY(25px)}}to{{opacity:1;transform:translateY(0)}}}}
@keyframes scaleIn{{from{{opacity:0;transform:scale(0.6)}}to{{opacity:1;transform:scale(1)}}}}
@keyframes popIn{{from{{opacity:0;transform:scale(0.3) rotate(-5deg)}}to{{opacity:1;transform:scale(1) rotate(0deg)}}}}

/* ── PHASE 1: Terminal ── */
.terminal{{background:rgba(0,0,0,0.75);border:1px solid rgba(0,255,100,0.18);
           border-radius:14px;overflow:hidden;max-width:680px;margin:0 auto;
           box-shadow:0 0 40px rgba(0,255,100,0.06);animation:slideUp 0.5s ease;}}
.term-head{{background:rgba(0,255,100,0.04);border-bottom:1px solid rgba(0,255,100,0.1);
            padding:0.55rem 1rem;display:flex;align-items:center;gap:0.5rem;}}
.td{{width:10px;height:10px;border-radius:50%;}}
.td.r{{background:#ff5f57;}}.td.y{{background:#febc2e;}}.td.g{{background:#28c840;}}
.tlabel{{font-family:'JetBrains Mono',monospace;font-size:0.7rem;color:rgba(255,255,255,0.35);margin-left:0.4rem;}}
.term-body{{padding:1rem 1.4rem;font-family:'JetBrains Mono',monospace;font-size:0.8rem;
            line-height:1.9;min-height:190px;}}
.tline{{color:rgba(0,255,100,0.65);}}
.tline .key{{color:rgba(0,195,255,0.75);}}
.tline .val{{color:#fff;}}
.tline .prompt{{color:rgba(0,255,100,0.4);}}
.cursor{{display:inline-block;width:7px;height:13px;background:rgba(0,255,100,0.7);
         animation:blink 1s step-end infinite;vertical-align:text-bottom;}}
@keyframes blink{{0%,100%{{opacity:1}}50%{{opacity:0}}}}

/* ── PHASE 2: Drone Grid ── */
.rule-banner{{background:rgba(0,195,255,0.07);border:1px solid rgba(0,195,255,0.18);
              border-radius:10px;padding:0.55rem 1.1rem;text-align:center;
              font-size:0.74rem;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;
              color:#00c3ff;margin-bottom:0.8rem;transition:all 0.4s ease;}}
.rule-banner.warn{{background:rgba(231,76,60,0.09);border-color:rgba(231,76,60,0.3);
                   color:#ff7575;box-shadow:0 0 20px rgba(231,76,60,0.08);}}
.rule-banner.ok{{background:rgba(0,255,136,0.07);border-color:rgba(0,255,136,0.25);color:#00ff88;}}
.dgrid{{display:grid;grid-template-columns:repeat(4,1fr);gap:0.55rem;}}
.dc{{background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);
     border-radius:11px;padding:0.7rem;transition:all 0.55s cubic-bezier(0.175,0.885,0.32,1.275);
     position:relative;overflow:hidden;animation:slideUp 0.4s ease both;}}
.dc:nth-child(1){{animation-delay:0.04s;}}.dc:nth-child(2){{animation-delay:0.08s;}}
.dc:nth-child(3){{animation-delay:0.12s;}}.dc:nth-child(4){{animation-delay:0.16s;}}
.dc:nth-child(5){{animation-delay:0.20s;}}.dc:nth-child(6){{animation-delay:0.24s;}}
.dc:nth-child(7){{animation-delay:0.28s;}}
.dc .dname{{font-size:0.75rem;font-weight:800;color:white;margin-bottom:0.1rem;
            white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}}
.dc .dtype{{font-size:0.6rem;color:rgba(0,195,255,0.5);text-transform:uppercase;
            letter-spacing:0.8px;margin-bottom:0.4rem;}}
.dc .dstats{{display:flex;flex-wrap:wrap;gap:3px;}}
.dc .dstat{{font-size:0.58rem;color:rgba(255,255,255,0.4);
            background:rgba(255,255,255,0.05);padding:2px 5px;border-radius:4px;}}
.dc.elim{{border-color:rgba(231,76,60,0.35)!important;
          background:rgba(231,76,60,0.05)!important;
          transform:scale(0.87);opacity:0.38;}}
.dc.elim::after{{content:'ELIMINATED';position:absolute;top:50%;left:50%;
                 transform:translate(-50%,-50%) rotate(-12deg);
                 font-size:0.55rem;font-weight:900;letter-spacing:2px;
                 color:rgba(231,76,60,0.7);border:1.5px solid rgba(231,76,60,0.4);
                 padding:2px 7px;border-radius:4px;white-space:nowrap;background:rgba(0,0,0,0.55);}}

/* ── PHASE 3: Scoring ── */
.sc-title{{font-size:0.7rem;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;
           color:rgba(0,195,255,0.7);text-align:center;margin-bottom:1rem;}}
.sc-item{{display:flex;align-items:center;gap:0.7rem;margin-bottom:0.65rem;
          animation:slideUp 0.4s ease both;}}
.sc-name{{width:185px;font-size:0.8rem;font-weight:600;color:white;
          text-align:right;flex-shrink:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}}
.sc-name.top{{color:#00ff88;}}
.sc-wrap{{flex:1;background:rgba(255,255,255,0.05);border-radius:20px;height:26px;overflow:hidden;}}
.sc-bar{{height:100%;border-radius:20px;width:0%;
         transition:width 1.2s cubic-bezier(0.25,0.46,0.45,0.94);
         display:flex;align-items:center;justify-content:flex-end;
         padding-right:10px;font-size:0.75rem;font-weight:700;color:white;
         text-shadow:0 1px 3px rgba(0,0,0,0.5);}}
.sc-bar.top{{background:linear-gradient(90deg,rgba(0,150,80,0.7),#00ff88);}}
.sc-bar.two{{background:linear-gradient(90deg,rgba(0,100,150,0.7),#00c3ff);}}
.sc-bar.rest{{background:linear-gradient(90deg,rgba(30,50,100,0.7),rgba(80,120,200,0.8));}}
.sc-pct{{width:48px;font-size:0.88rem;font-weight:800;text-align:right;flex-shrink:0;
         color:rgba(255,255,255,0.6);}}
.sc-pct.top{{color:#00ff88;}}

/* ── PHASE 4: Winner ── */
.win-wrap{{display:flex;flex-direction:column;align-items:center;gap:1rem;}}
.win-badge{{font-size:0.68rem;font-weight:700;letter-spacing:3px;text-transform:uppercase;
            color:#00ff88;text-shadow:0 0 20px rgba(0,255,136,0.5);
            animation:slideUp 0.5s ease;}}
.win-card{{background:linear-gradient(135deg,rgba(0,255,136,0.05),rgba(0,195,255,0.03));
           border:1px solid rgba(0,255,136,0.2);border-radius:20px;padding:1.6rem 1.8rem;
           display:flex;justify-content:space-between;align-items:center;gap:1.8rem;
           animation:popIn 0.7s cubic-bezier(0.175,0.885,0.32,1.275);
           box-shadow:0 0 60px rgba(0,255,136,0.08);width:100%;
           position:relative;overflow:hidden;}}
.win-card::before{{content:'';position:absolute;top:0;left:-100%;width:50%;height:100%;
                   background:linear-gradient(90deg,transparent,rgba(0,255,136,0.05),transparent);
                   animation:sweep 3s linear infinite;}}
@keyframes sweep{{0%{{left:-100%}}100%{{left:200%}}}}
.wname{{font-size:1.65rem;font-weight:900;color:white;margin-bottom:0.25rem;}}
.wtype{{font-size:0.82rem;color:rgba(255,255,255,0.4);margin-bottom:0.7rem;}}
.wcam{{display:inline-block;background:rgba(0,195,255,0.1);border:1px solid rgba(0,195,255,0.25);
       color:#00c3ff;padding:3px 11px;border-radius:20px;font-size:0.72rem;font-weight:600;margin:2px;}}
.sring{{width:115px;height:115px;border-radius:50%;flex-shrink:0;
        display:flex;align-items:center;justify-content:center;
        box-shadow:0 0 40px rgba(0,255,136,0.2);position:relative;}}
.sring::before{{content:'';position:absolute;inset:11px;border-radius:50%;background:#050f25;}}
.snum{{position:relative;z-index:1;font-size:1.5rem;font-weight:900;color:white;
       text-shadow:0 0 15px rgba(0,255,136,0.5);}}
.slabel{{font-size:0.58rem;letter-spacing:1.5px;text-transform:uppercase;
         color:rgba(255,255,255,0.3);margin-top:0.3rem;}}
.wstats{{display:grid;grid-template-columns:repeat(6,1fr);gap:0.45rem;width:100%;}}
.wstat{{background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);
        border-radius:10px;padding:0.55rem 0.4rem;text-align:center;
        animation:slideUp 0.5s ease both;}}
.wstat .wl{{font-size:0.58rem;letter-spacing:0.8px;text-transform:uppercase;
            color:rgba(255,255,255,0.28);margin-bottom:0.2rem;}}
.wstat .wv{{font-size:0.85rem;font-weight:800;color:#00c3ff;}}
.win-meta{{display:flex;gap:1.5rem;align-items:center;}}
.win-meta-item{{text-align:center;}}
.win-meta-item .wml{{font-size:0.6rem;letter-spacing:1.5px;text-transform:uppercase;color:rgba(255,255,255,0.3);}}
.win-meta-item .wmv{{font-size:1.4rem;font-weight:900;}}
.win-meta-item .wmv.cyan{{color:#00c3ff;text-shadow:0 0 20px rgba(0,195,255,0.5);}}
.win-meta-item .wmv.green{{color:#00ff88;text-shadow:0 0 20px rgba(0,255,136,0.5);}}
.replay{{background:rgba(0,195,255,0.1);border:1px solid rgba(0,195,255,0.3);
         color:#00c3ff;border-radius:10px;padding:0.55rem 1.4rem;
         font-size:0.78rem;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;
         cursor:pointer;transition:all 0.3s;display:none;font-family:'Inter',sans-serif;}}
.replay:hover{{background:rgba(0,195,255,0.2);box-shadow:0 0 20px rgba(0,195,255,0.3);}}
#confetti{{position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:99;}}
</style>

<div id="root">
  <div class="pbar">
    <div class="ps" id="ps1">1 · Mission Input</div>
    <div class="arr">▶</div>
    <div class="ps" id="ps2">2 · Rule Filtering</div>
    <div class="arr">▶</div>
    <div class="ps" id="ps3">3 · Scoring</div>
    <div class="arr">▶</div>
    <div class="ps" id="ps4">4 · Recommendation</div>
  </div>

  <div class="ph" id="ph1">
    <div class="terminal">
      <div class="term-head">
        <span class="td r"></span><span class="td y"></span><span class="td g"></span>
        <span class="tlabel">SAR-DSS MISSION ANALYSIS SYSTEM v2.6</span>
      </div>
      <div class="term-body" id="tbody"><span class="cursor" id="cur"></span></div>
    </div>
  </div>

  <div class="ph" id="ph2">
    <div class="rule-banner" id="rbanner">INITIALIZING KNOWLEDGE BASE...</div>
    <div class="dgrid" id="dgrid"></div>
  </div>

  <div class="ph" id="ph3">
    <div class="sc-title" id="sctitle">SCORING CANDIDATES WITH DECISION MATRIX</div>
    <div id="scbars"></div>
  </div>

  <div class="ph" id="ph4">
    <div class="win-wrap">
      <div class="win-badge">◆ MISSION-OPTIMAL DRONE SELECTED ◆</div>
      <div class="win-card">
        <div style="flex:1;min-width:0;">
          <div class="wname" id="wname"></div>
          <div class="wtype" id="wtype"></div>
          <div id="wcams"></div>
        </div>
        <div style="text-align:center;flex-shrink:0;">
          <div class="slabel">MATCH SCORE</div>
          <div class="sring" id="sring"><div class="snum" id="snum">0%</div></div>
        </div>
      </div>
      <div class="wstats" id="wstats"></div>
      <div class="win-meta" id="wmeta"></div>
      <button class="replay" id="rbtn" onclick="replay()">&#8635; REPLAY SIMULATION</button>
    </div>
  </div>
</div>

<canvas id="confetti"></canvas>

<script>
var DATA = {sim_json};

function setPhase(n) {{
    var ids = ['ps1','ps2','ps3','ps4'];
    for (var i=0;i<ids.length;i++) {{
        var el = document.getElementById(ids[i]);
        el.className = 'ps';
        if (i+1 < n) el.classList.add('done');
        if (i+1 === n) el.classList.add('active');
    }}
    var phs = ['ph1','ph2','ph3','ph4'];
    for (var j=0;j<phs.length;j++) {{
        var p = document.getElementById(phs[j]);
        p.className = 'ph';
        if (j+1 === n) p.classList.add('show');
    }}
}}

/* ── PHASE 1 ── */
function phase1() {{
    setPhase(1);
    var body = document.getElementById('tbody');
    var cur  = document.getElementById('cur');
    var s    = DATA.scenario;
    var params = [
        ['EMERGENCY TYPE',   s.emergency],
        ['WEATHER',          s.weather],
        ['TIME OF DAY',      s.time_of_day],
        ['ALTITUDE',         s.altitude + ' m'],
        ['AREA TO COVER',    s.area + ' km²'],
        ['TRAVEL DISTANCE',  s.distance + ' km'],
        ['SUPPLY WEIGHT',    s.supply_weight + ' kg'],
        ['BUDGET LIMIT',     '€' + s.budget]
    ];
    setTimeout(function() {{
        var bl = document.createElement('div'); bl.className='tline';
        bl.innerHTML = '<span class="prompt">SAR-DSS &gt;</span> MISSION PARAMETERS RECEIVED';
        body.insertBefore(bl, cur);
    }}, 200);
    params.forEach(function(pair, i) {{
        setTimeout(function() {{
            var ln = document.createElement('div'); ln.className='tline';
            ln.innerHTML = '<span class="prompt">&nbsp;&nbsp;&gt;&gt;</span> <span class="key">' + pair[0] + '</span>: <span class="val">' + pair[1] + '</span>';
            body.insertBefore(ln, cur);
        }}, 500 + i*280);
    }});
    var t = 500 + params.length*280 + 350;
    setTimeout(function() {{
        var proc = document.createElement('div'); proc.className='tline';
        proc.innerHTML = '<span class="prompt">SAR-DSS &gt;</span> <span style="color:#00c3ff;">LOADING DRONE DATABASE... ' + DATA.drones.length + ' CANDIDATES FOUND</span>';
        body.insertBefore(proc, cur);
    }}, t);
    setTimeout(function() {{
        var proc2 = document.createElement('div'); proc2.className='tline';
        proc2.innerHTML = '<span class="prompt">SAR-DSS &gt;</span> <span style="color:#00c3ff;">ACTIVATING KNOWLEDGE BASE RULES...</span>';
        body.insertBefore(proc2, cur);
    }}, t+350);
    setTimeout(phase2, t+1100);
}}

/* ── PHASE 2 ── */
function phase2() {{
    setPhase(2);
    var grid = document.getElementById('dgrid');
    DATA.drones.forEach(function(d, idx) {{
        var card = document.createElement('div');
        card.className = 'dc'; card.id = 'dc'+idx;
        var ico = d.is_plane ? '✈' : '🚁';
        var r   = d.eliminated && d.reasons.length > 0 ? d.reasons[0] : '';
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
    DATA.drones.forEach(function(d,i){{ if(d.eliminated) elims.push({{d:d,i:i}}); }});
    var banner = document.getElementById('rbanner');
    setTimeout(function() {{
        banner.textContent = 'APPLYING EXPERT RULES TO ' + DATA.drones.length + ' CANDIDATES...';
    }}, 600);
    var delay = 1200;
    elims.forEach(function(item) {{
        setTimeout(function() {{
            banner.className = 'rule-banner warn';
            var r = item.d.reasons.length > 0 ? item.d.reasons[0] : 'Failed requirement';
            banner.innerHTML = '⚠ RULE VIOLATION &mdash; ' + r;
        }}, delay);
        setTimeout(function() {{
            var card = document.getElementById('dc'+item.i);
            if (card) card.classList.add('elim');
        }}, delay+280);
        delay += 950;
    }});
    setTimeout(function() {{
        banner.className = 'rule-banner ok';
        banner.textContent = '✓ FILTERING COMPLETE: ' + DATA.pass_count + ' QUALIFY  •  ' + DATA.elim_count + ' ELIMINATED';
    }}, delay);
    setTimeout(phase3, delay+900);
}}

/* ── PHASE 3 ── */
function phase3() {{
    setPhase(3);
    var title = document.getElementById('sctitle');
    title.textContent = 'SCORING ' + DATA.pass_count + ' CANDIDATES WITH WEIGHTED DECISION MATRIX';
    var cont = document.getElementById('scbars');
    var survivors = DATA.drones.filter(function(d){{return !d.eliminated;}}).sort(function(a,b){{return b.score-a.score;}});
    survivors.forEach(function(d, i) {{
        var item = document.createElement('div');
        item.className = 'sc-item'; item.style.animationDelay=(i*0.12)+'s';
        var cls = i===0?'top':i===1?'two':'rest';
        var ico = d.is_plane ? '✈' : '🚁';
        item.innerHTML =
            '<div class="sc-name' + (i===0?' top':'') + '">' + ico + ' ' + d.name + '</div>' +
            '<div class="sc-wrap"><div class="sc-bar ' + cls + '" id="bar'+i+'"></div></div>' +
            '<div class="sc-pct' + (i===0?' top':'') + '" id="pct'+i+'">0%</div>';
        cont.appendChild(item);
    }});
    setTimeout(function() {{
        survivors.forEach(function(d, i) {{
            var bar = document.getElementById('bar'+i);
            var pct = document.getElementById('pct'+i);
            if (bar) bar.style.width = d.score + '%';
            var cur=0, target=d.score;
            var t = setInterval(function(){{
                cur = Math.min(cur+target/40, target);
                if (pct) pct.textContent = Math.round(cur)+'%';
                if (cur>=target) clearInterval(t);
            }},30);
        }});
    }}, 400);
    setTimeout(phase4, 3200);
}}

/* ── PHASE 4 ── */
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
    var cur=0, target=top.score;
    var ringTimer = setInterval(function(){{
        cur = Math.min(cur+target/55, target);
        ring.style.background = 'conic-gradient(#00ff88 0%, #00c3ff '+cur+'%, rgba(255,255,255,0.05) '+cur+'%)';
        numEl.textContent = Math.round(cur)+'%';
        if(cur>=target) clearInterval(ringTimer);
    }},25);
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
    stats.forEach(function(s,i){{
        var el=document.createElement('div'); el.className='wstat'; el.style.animationDelay=(i*0.08+0.4)+'s';
        el.innerHTML='<div class="wl">'+s[0]+'</div><div class="wv">'+s[1]+'</div>';
        statsEl.appendChild(el);
    }});
    /* meta: drones needed + total cost */
    var metaEl=document.getElementById('wmeta');
    metaEl.innerHTML=
        '<div class="win-meta-item"><div class="wml">DRONES NEEDED</div><div class="wmv cyan">'+DATA.num_drones+'</div></div>'+
        '<div style="width:1px;height:40px;background:rgba(255,255,255,0.08);"></div>'+
        '<div class="win-meta-item"><div class="wml">TOTAL DEPLOYMENT COST</div><div class="wmv green">€'+DATA.total_cost+'</div></div>';
    /* confetti */
    setTimeout(confetti, 500);
    /* replay button */
    setTimeout(function(){{document.getElementById('rbtn').style.display='inline-block';}},2000);
}}

/* ── CONFETTI ── */
function confetti() {{
    var cv=document.getElementById('confetti');
    var ctx=cv.getContext('2d');
    cv.width=window.innerWidth||900; cv.height=window.innerHeight||700;
    var colors=['#00ff88','#00c3ff','#7830c8','#ffffff','#ffdd00','#ff6b9d'];
    var parts=[];
    for(var i=0;i<130;i++){{
        parts.push({{
            x: cv.width/2+(Math.random()-0.5)*300,
            y: cv.height*0.35,
            vx:(Math.random()-0.5)*12,
            vy:(Math.random()*-9-2),
            sz:Math.random()*7+3,
            c:colors[Math.floor(Math.random()*colors.length)],
            rot:Math.random()*360, rs:(Math.random()-0.5)*9,
            g:0.28, a:1
        }});
    }}
    var frames=0;
    function draw(){{
        ctx.clearRect(0,0,cv.width,cv.height);
        parts.forEach(function(p){{
            p.x+=p.vx; p.y+=p.vy; p.vy+=p.g; p.rot+=p.rs;
            p.a=Math.max(0,p.a-0.007);
            ctx.save(); ctx.globalAlpha=p.a;
            ctx.translate(p.x,p.y); ctx.rotate(p.rot*Math.PI/180);
            ctx.fillStyle=p.c; ctx.fillRect(-p.sz/2,-p.sz/4,p.sz,p.sz/2);
            ctx.restore();
        }});
        frames++;
        if(frames<220) requestAnimationFrame(draw);
        else ctx.clearRect(0,0,cv.width,cv.height);
    }}
    draw();
}}

/* ── REPLAY ── */
function replay() {{
    document.getElementById('tbody').innerHTML='<span class="cursor" id="cur"></span>';
    document.getElementById('dgrid').innerHTML='';
    document.getElementById('scbars').innerHTML='';
    document.getElementById('wname').textContent='';
    document.getElementById('wtype').textContent='';
    document.getElementById('wcams').innerHTML='';
    document.getElementById('wstats').innerHTML='';
    document.getElementById('wmeta').innerHTML='';
    document.getElementById('snum').textContent='0%';
    document.getElementById('sring').style.background='conic-gradient(#00ff88 0%,rgba(255,255,255,0.05) 0%)';
    document.getElementById('rbtn').style.display='none';
    phase1();
}}

phase1();
</script>
</html>""", height=680)

        # ── DETAILED ANALYSIS ───────────────────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="display:flex;align-items:center;gap:1rem;margin:0.5rem 0 1rem;">
          <div style="flex:1;height:1px;background:rgba(255,255,255,0.06);"></div>
          <div style="font-size:0.7rem;letter-spacing:2.5px;text-transform:uppercase;color:rgba(255,255,255,0.25);">DETAILED ANALYSIS</div>
          <div style="flex:1;height:1px;background:rgba(255,255,255,0.06);"></div>
        </div>""", unsafe_allow_html=True)

        col_chart, col_sum = st.columns([3, 2], gap="large")

        with col_chart:
            st.markdown("<p style='color:rgba(255,255,255,0.5);font-size:0.75rem;letter-spacing:2px;text-transform:uppercase;margin-bottom:0.5rem;'>Score Comparison</p>", unsafe_allow_html=True)
            names  = [d["name"] for d in scored]
            scores = [d["score"] for d in scored]
            colors = ["#00ff88" if i==0 else "#00c3ff" if i==1 else "#4a7fbf" if i==2 else "#2a3f5f"
                      for i in range(len(scored))]
            fig = go.Figure(go.Bar(
                x=scores, y=names, orientation="h",
                marker=dict(color=colors, line=dict(width=0), opacity=0.9),
                text=[f"{s}%" for s in scores],
                textposition="inside", insidetextanchor="end",
                textfont=dict(color="white", size=13, family="Inter"),
            ))
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(255,255,255,0.02)",
                margin=dict(l=10, r=20, t=10, b=10),
                xaxis=dict(range=[0,100], showgrid=True, gridcolor="rgba(255,255,255,0.05)",
                           ticksuffix="%", title="", color="rgba(255,255,255,0.3)",
                           tickfont=dict(color="rgba(255,255,255,0.3)")),
                yaxis=dict(autorange="reversed", showgrid=False, title="",
                           tickfont=dict(color="rgba(255,255,255,0.6)", size=11)),
                height=280, font=dict(family="Inter", size=12, color="white"), showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_sum:
            st.markdown("<p style='color:rgba(255,255,255,0.5);font-size:0.75rem;letter-spacing:2px;text-transform:uppercase;margin-bottom:0.5rem;'>Mission Summary</p>", unsafe_allow_html=True)
            wi = {"Clear":"☀️","Windy":"💨","Storm":"⛈️","Blizzard":"🌨️"}.get(weather,"")
            rows = [
                ("Emergency",  emergency),
                ("Weather",    f"{wi} {weather}"),
                ("Time",       f"{'🌙' if time_of_day=='Night' else '☀️'} {time_of_day}"),
                ("Altitude",   f"{scenario['altitude']:,} m"),
                ("Area",       f"{scenario['area']} km²"),
                ("Distance",   f"{scenario['distance']} km"),
            ]
            rows_html = "".join([
                f"<tr><td style='color:rgba(255,255,255,0.35);padding:0.4rem 0;font-size:0.85rem;'>{k}</td>"
                f"<td style='font-weight:600;text-align:right;color:rgba(255,255,255,0.8);font-size:0.85rem;'>{v}</td></tr>"
                for k, v in rows
            ])
            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.07);
                        border-radius:18px;padding:1.4rem;backdrop-filter:blur(20px);">
              <table style="width:100%;border-collapse:collapse;">{rows_html}
                <tr style="border-top:1px solid rgba(255,255,255,0.08);">
                  <td style="color:rgba(255,255,255,0.4);padding:0.7rem 0 0.3rem;font-size:0.8rem;letter-spacing:1px;text-transform:uppercase;">Drones Needed</td>
                  <td style="text-align:right;font-size:1.5rem;font-weight:900;color:#00c3ff;text-shadow:0 0 20px rgba(0,195,255,0.5);padding-top:0.3rem;">{num_drones}</td>
                </tr>
                <tr>
                  <td style="color:rgba(255,255,255,0.4);padding:0.3rem 0;font-size:0.8rem;letter-spacing:1px;text-transform:uppercase;">Total Cost</td>
                  <td style="text-align:right;font-size:1.5rem;font-weight:900;color:#00ff88;text-shadow:0 0 20px rgba(0,255,136,0.5);">€{total_cost:,}</td>
                </tr>
              </table>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        if len(scored) > 1:
            with st.expander(f"📋  {len(scored)-1} alternative drone(s)"):
                for d in scored[1:]:
                    ai = "✈️" if "Fixed" in d["type"] else "🚁"
                    st.markdown(f"""
                    <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(0,195,255,0.12);
                                border-left:4px solid rgba(0,195,255,0.4);border-radius:12px;
                                padding:0.9rem 1.2rem;margin:0.4rem 0;
                                display:flex;justify-content:space-between;align-items:center;">
                      <div><div style="font-weight:700;color:white;">{ai} {d['name']}</div>
                        <div style="color:rgba(255,255,255,0.35);font-size:0.8rem;margin-top:0.2rem;">{d['description']}</div></div>
                      <div style="background:rgba(0,195,255,0.1);border:1px solid rgba(0,195,255,0.25);
                                  color:#00c3ff;padding:4px 16px;border-radius:20px;font-weight:800;font-size:0.95rem;">
                        {d['score']}%</div>
                    </div>""", unsafe_allow_html=True)

        if eliminated:
            with st.expander(f"❌  {len(eliminated)} drone(s) eliminated by rules"):
                for d in eliminated:
                    ei = "✈️" if "Fixed" in d["type"] else "🚁"
                    reasons = "".join([
                        f"<div style='color:rgba(231,76,60,0.8);font-size:0.78rem;margin-top:0.2rem;'>• {r}</div>"
                        for r in d["reasons"]
                    ])
                    st.markdown(f"""
                    <div style="background:rgba(231,76,60,0.04);border:1px solid rgba(231,76,60,0.15);
                                border-left:4px solid rgba(231,76,60,0.4);border-radius:12px;
                                padding:0.9rem 1.2rem;margin:0.4rem 0;">
                      <div style="font-weight:700;color:rgba(255,255,255,0.7);">{ei} {d['name']}</div>
                      {reasons}
                    </div>""", unsafe_allow_html=True)
