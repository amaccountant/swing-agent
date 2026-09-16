# build_dashboard.py — PREMIUM interactive dashboard (Germany + India).
# Features: dark/light toggle, language dropdown (Google Translate), animations, filters,
# sort, search, sparklines + analytics (Chart.js CDN), preference memory (localStorage), PWA.
# All times CET. Research/education. NOT financial advice.

import json, os, csv, html, datetime

def load_json(p, d):
    if os.path.exists(p):
        with open(p) as f: return json.load(f)
    return d
def esc(x): return html.escape(str(x))

def collect(picks, cur, is_india):
    out = []
    for p in picks:
        actionable = p.get("worthwhile") and p.get("conf") in ("Med", "High")
        out.append({
            "ticker": p["ticker"], "name": p["name"], "cur": cur, "india": is_india,
            "conf": p["conf"], "score": p["score"], "price": p["price"],
            "buy_low": p["buy_low"], "buy_high": p["buy_high"], "stop": p["stop"],
            "target": p["est_dayhigh"], "dayend": p["est_dayend"],
            "tgt_move_pct": p["tgt_move_pct"], "shares": p["shares"], "cost": p["cost"],
            "cost_eur": p.get("cost_eur"), "rsi": p["rsi"], "atr_pct": p["atr_pct"],
            "sma5": p["sma5"], "sma20": p["sma20"], "worthwhile": p["worthwhile"],
            "actionable": bool(actionable), "spark": p.get("spark", [])
        })
    return out

def perf_stats(logfile):
    total = hit = 0
    if os.path.exists(logfile):
        with open(logfile) as f:
            for r in csv.DictReader(f):
                total += 1
                if r.get("hit_miss", "").startswith("HIT"): hit += 1
    return hit, total

def perf_series(logfile):
    # returns list of {date,ticker,pred,actual,hit} for charts + table
    rows = []
    if os.path.exists(logfile):
        with open(logfile) as f:
            for r in csv.DictReader(f):
                try:
                    rows.append({"date": r.get("date"), "ticker": r.get("ticker"),
                                 "pred": float(r.get("predicted_dayhigh") or 0),
                                 "actual": float(r.get("actual_dayhigh") or 0),
                                 "hit": 1 if r.get("hit_miss","").startswith("HIT") else 0,
                                 "hm": r.get("hit_miss","")})
                except Exception:
                    pass
    return rows

def lessons_text(mdfile):
    if os.path.exists(mdfile):
        with open(mdfile) as f: return f.read()
    return "No lessons recorded yet."

def main():
    de = load_json("picks_today.json", {"picks": [], "date": "-", "generated": "—", "actionable_count": 0})
    ind = load_json("picks_today_in.json", {"picks": [], "date": "-", "generated": "—", "actionable_count": 0, "eurinr": "?"})
    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=1))).strftime("%Y-%m-%d")

    picks_all = collect(de.get("picks", []), "€", False) + collect(ind.get("picks", []), "₹", True)
    dh, dt = perf_stats("performance_log.csv")
    ih, it = perf_stats("performance_log_in.csv")
    de_series = perf_series("performance_log.csv")
    in_series = perf_series("performance_log_in.csv")

    payload = {
        "generatedDE": de.get("generated", "—"), "generatedIN": ind.get("generated", "—"),
        "dateDE": de.get("date"), "dateIN": ind.get("date"), "today": today,
        "eurinr": ind.get("eurinr", "?"),
        "picks": picks_all,
        "perf": {"deHit": dh, "deTot": dt, "inHit": ih, "inTot": it,
                 "deSeries": de_series, "inSeries": in_series},
        "lessonsDE": lessons_text("strategy_memory.md"),
        "lessonsIN": lessons_text("strategy_memory_in.md"),
        "actionableToday": de.get("actionable_count", 0) + ind.get("actionable_count", 0),
    }
    data_json = json.dumps(payload)

    # ---------- HTML ----------
    doc = """<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Swing Agent — Stock Ideas</title>
<link rel="manifest" href="manifest.json">
<meta name="theme-color" content="#0b0e14">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"></script>
<style>
:root{--bg:#0b0e14;--panel:#141a26;--line:#262b36;--txt:#e8e8e8;--mut:#9aa4b2;--acc:#7aa2ff;--good:#8affb0;--bad:#ff9aa2;--card:#141a26}
[data-theme="light"]{--bg:#f4f6fb;--panel:#ffffff;--line:#e2e8f0;--txt:#1a2233;--mut:#5b6577;--acc:#2b5cff;--good:#12a150;--bad:#e03e52;--card:#ffffff}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{font-family:-apple-system,'Segoe UI',Roboto,Arial,sans-serif;margin:0;background:var(--bg);color:var(--txt);line-height:1.5;transition:background .4s,color .4s}
.top{background:linear-gradient(135deg,#1a2233,#0f1420);padding:22px 20px;border-bottom:1px solid var(--line);position:sticky;top:0;z-index:50;backdrop-filter:blur(6px)}
[data-theme="light"] .top{background:linear-gradient(135deg,#2b5cff,#5b8bff)}
.topbar{max-width:1040px;margin:0 auto;display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
.brand h1{margin:0;font-size:22px;color:#fff}.brand .tag{color:#cdd6e0;font-size:12px;margin-top:3px}
.ctrls{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.ctrls select,.ctrls input,.ctrls button{background:rgba(255,255,255,.12);color:#fff;border:1px solid rgba(255,255,255,.25);border-radius:10px;padding:7px 10px;font-size:13px}
.ctrls input::placeholder{color:#dbe2ee}
.wrap{max-width:1040px;margin:0 auto;padding:20px}
.reveal{opacity:0;transform:translateY(16px);transition:opacity .6s,transform .6s}
.reveal.show{opacity:1;transform:none}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:16px 0}
.tile{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:18px;text-align:center;transition:transform .25s,box-shadow .25s}
.tile:hover{transform:translateY(-4px);box-shadow:0 10px 26px rgba(0,0,0,.25)}
.tile .big{font-size:30px;font-weight:800;color:var(--acc)}.tile .lbl{color:var(--mut);font-size:12px;margin-top:4px}
.alert{background:#3a1f22;border:1px solid #6b1f2a;color:#ff9aa2;padding:12px 14px;border-radius:12px;margin:12px 0;font-size:14px}
.disc{background:#241b00;border:1px solid #6b5200;color:#ffd479;padding:12px 14px;border-radius:12px;margin:12px 0;font-size:13px}
.guide{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:18px;margin:12px 0}
.guide h3{margin:0 0 8px}.guide ol{margin:8px 0 0 18px;color:var(--txt);font-size:14px}.guide li{margin:5px 0}
.mkt{display:flex;align-items:center;gap:10px;margin:26px 0 8px;font-size:20px;font-weight:700}.flag{font-size:26px}
.sub{color:var(--mut);font-size:13px;margin-bottom:6px}
.filters{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}
.chip{background:var(--panel);border:1px solid var(--line);color:var(--txt);border-radius:20px;padding:6px 14px;font-size:13px;cursor:pointer;transition:.2s}
.chip.active{background:var(--acc);color:#fff;border-color:var(--acc)}
.pcard{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:18px;margin:14px 0;box-shadow:0 4px 18px rgba(0,0,0,.18);transition:transform .25s,box-shadow .25s}
.pcard:hover{transform:translateY(-3px);box-shadow:0 12px 30px rgba(0,0,0,.28)}
.pcard.act{border-left:4px solid var(--good)}.pcard.skp{border-left:4px solid var(--bad)}
.pchead{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}
.pchead h3{margin:0;font-size:18px}.ticker{color:var(--acc);font-size:13px;font-weight:600}
.badge{display:inline-block;margin-top:6px;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:700}
.badge.go{background:#12331f;color:#8affb0;border:1px solid #1f5133}.badge.skip{background:#331416;color:#ff9aa2;border:1px solid #5a1f24}
.plain{color:var(--txt);font-size:14px}
.spark{width:100%;height:44px;margin:8px 0}
.scaletrack{position:relative;height:14px;background:var(--line);border-radius:8px;margin:8px 0}
.zone{position:absolute;top:0;height:14px;background:rgba(122,162,255,.35);border:1px solid var(--acc);border-radius:4px}
.marker{position:absolute;top:-3px;width:2px;height:20px}
.stopm{background:#ff6b78}.tgtm{background:var(--good)}.pricem{width:10px;height:10px;top:2px;border-radius:50%;background:var(--txt);transform:translateX(-4px)}
.scalelegend{display:flex;justify-content:space-between;color:var(--mut);font-size:11px}
.rrbar{display:flex;height:12px;border-radius:6px;overflow:hidden;margin:10px 0}
.rrrisk{background:#ff6b78}.rrreward{background:#5fd18e}
.rrlabels{display:flex;justify-content:space-between;font-size:12px;margin-bottom:3px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:12px 0}
.kv{background:var(--bg);border:1px solid var(--line);border-radius:10px;padding:8px 10px;font-size:13px;display:flex;flex-direction:column;gap:2px}
.kv span{color:var(--mut);font-size:12px}.kv b{font-size:15px}
.tip{border-bottom:1px dotted var(--acc);cursor:help;position:relative}
.tip .tiptext{visibility:hidden;opacity:0;transition:.15s;position:absolute;bottom:130%;left:0;z-index:9;background:#0a0f18;color:#fff;border:1px solid #3a4658;border-radius:8px;padding:8px 10px;width:220px;font-size:12px}
.tip:hover .tiptext{visibility:visible;opacity:1}
.sellrule{background:var(--bg);border:1px dashed var(--line);border-radius:10px;padding:10px;font-size:13px;margin-top:6px}
.src{color:var(--mut);font-size:11px;margin-top:8px}
.gauge{position:relative;width:120px;height:70px;flex:none}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:18px;margin:14px 0}
table.perf{width:100%;border-collapse:collapse;font-size:13px;margin-top:10px}
table.perf th,table.perf td{text-align:left;padding:8px;border-bottom:1px solid var(--line)}
.pill{padding:2px 8px;border-radius:12px;font-size:11px;font-weight:700}.pill.hit{background:#12331f;color:#8affb0}.pill.miss{background:#331416;color:#ff9aa2}
.lessons{white-space:pre-wrap;font-family:inherit;color:var(--txt);font-size:13px;margin:0}
.muted{color:var(--mut);font-size:13px}
footer{color:var(--mut);font-size:12px;text-align:center;padding:26px}
#google_translate_element{display:inline-block}
.goog-te-gadget{color:transparent!important;font-size:0!important}.goog-te-gadget .goog-te-combo{color:#111;font-size:13px;padding:6px;border-radius:8px}
.hidden{display:none!important}
</style></head><body>
<div class="top"><div class="topbar">
  <div class="brand"><h1>📈 Swing Agent</h1><div class="tag">Beginner-friendly stock ideas · Germany 🇩🇪 &amp; India 🇮🇳 · times in CET</div></div>
  <div class="ctrls">
    <div id="google_translate_element"></div>
    <input id="search" placeholder="🔎 Search stock…" oninput="applyFilters()">
    <select id="sortsel" onchange="applyFilters()">
      <option value="score">Sort: Confidence</option>
      <option value="reward">Sort: Reward %</option>
      <option value="move">Sort: Movement</option>
    </select>
    <button id="themeBtn" onclick="toggleTheme()">🌙 Theme</button>
  </div>
</div></div>
<div class="wrap">
  <div id="staleBox"></div>
  <div class="disc" translate="no"><b>Please read:</b> Research &amp; education, <b>not financial advice</b>. Numbers are estimates from ~15-min delayed data (based on the previous close). You decide and place every trade yourself and are responsible for it.</div>
  <div class="tiles reveal">
    <div class="tile"><div class="big" id="tActionable">0</div><div class="lbl">Actionable ideas today</div></div>
    <div class="tile"><div class="big" id="tAnalysed">0</div><div class="lbl">Stocks analysed today</div></div>
    <div class="tile"><div class="big" id="tAccuracy">—</div><div class="lbl">Overall target accuracy</div></div>
    <div class="tile"><div class="big">2</div><div class="lbl">Markets covered</div></div>
  </div>
  <div class="guide reveal"><h3>🧭 How to read this (no experience needed)</h3><ol>
    <li>Look for a green <b>“✓ ACTIONABLE”</b> tag. “WATCH / SKIP” means don’t trade it today.</li>
    <li>The <b>confidence dial</b> shows signal strength (green=strong).</li>
    <li>The <b>Risk vs Reward</b> bar — more green than red is better.</li>
    <li>The <b>line scale</b>: 🛑 safety exit, 🟦 buy zone, ● price now, 🎯 target.</li>
    <li><b>Hover underlined words</b> for plain-English meaning. Use filters/search above to tailor the view.</li>
    <li><b>Always confirm the live price in your broker</b> — our data is ~15 min delayed.</li>
  </ol></div>

  <div class="filters reveal">
    <span class="chip active" data-f="all" onclick="setFilter(this)">All</span>
    <span class="chip" data-f="actionable" onclick="setFilter(this)">✓ Actionable only</span>
    <span class="chip" data-f="de" onclick="setFilter(this)">🇩🇪 Germany</span>
    <span class="chip" data-f="in" onclick="setFilter(this)">🇮🇳 India</span>
    <span class="chip" data-f="high" onclick="setFilter(this)">High confidence</span>
  </div>

  <div class="mkt reveal"><span class="flag">💡</span> Today’s Ideas</div>
  <div class="sub reveal" id="updatedLine"></div>
  <div id="cards"></div>

  <div class="mkt reveal">📊 Track Record</div>
  <div class="panel reveal"><p class="plain">How often the estimated target was actually reached. A low score early is normal — the system learns and recalibrates. This measures <b>estimate accuracy, not your profit</b>.</p>
    <canvas id="accChart" height="120"></canvas>
    <p class="muted" id="perfBreak"></p></div>
  <div class="panel reveal"><h3 style="margin-top:0">🇩🇪 Germany — recent results</h3><div id="deTable"></div></div>
  <div class="panel reveal"><h3 style="margin-top:0">🇮🇳 India — recent results</h3><div id="inTable"></div></div>

  <div class="mkt reveal">🧠 What the system learned</div>
  <div class="panel reveal"><h3 style="margin-top:0">🇩🇪 Germany</h3><pre class="lessons" id="lessonsDE"></pre></div>
  <div class="panel reveal"><h3 style="margin-top:0">🇮🇳 India</h3><pre class="lessons" id="lessonsIN"></pre></div>
</div>
<footer translate="no">Swing Agent · free tools · times in CET · research/education only, not financial advice</footer>

<script>
const DATA = __DATA__;

/* ---------- preferences (localStorage) ---------- */
function loadPrefs(){
  const t = localStorage.getItem('sa_theme'); if(t) document.documentElement.setAttribute('data-theme',t);
  const f = localStorage.getItem('sa_filter')||'all'; window._filter=f;
  const s = localStorage.getItem('sa_sort')||'score'; document.getElementById('sortsel').value=s;
}
function toggleTheme(){
  const cur=document.documentElement.getAttribute('data-theme');
  const nxt=cur==='light'?'':'light';
  if(nxt) document.documentElement.setAttribute('data-theme',nxt); else document.documentElement.removeAttribute('data-theme');
  localStorage.setItem('sa_theme',nxt);
  document.getElementById('themeBtn').textContent = nxt==='light'?'☀️ Theme':'🌙 Theme';
}
/* ---------- helpers ---------- */
function gauge(score){
  const pct=Math.max(0,Math.min(100,score))/100, ang=180*pct, rad=(180-ang)*Math.PI/180;
  const x=60+50*Math.cos(rad), y=60-50*Math.sin(rad);
  const color=score>=72?'var(--good)':score>=60?'#ffd479':'var(--bad)';
  const large=ang>90?1:0;
  return `<svg class="gauge" viewBox="0 0 120 70"><path d="M10 60 A50 50 0 0 1 110 60" fill="none" stroke="var(--line)" stroke-width="10"/>
  <path d="M10 60 A50 50 0 ${large} 1 ${x.toFixed(1)} ${y.toFixed(1)}" fill="none" stroke="${color}" stroke-width="10" stroke-linecap="round"/>
  <text x="60" y="55" text-anchor="middle" fill="var(--txt)" font-size="18" font-weight="700">${Math.round(score)}</text>
  <text x="60" y="68" text-anchor="middle" fill="var(--mut)" font-size="9">confidence</text></svg>`;
}
function sparkSVG(arr){
  if(!arr||arr.length<2) return '';
  const w=300,h=44,mn=Math.min(...arr),mx=Math.max(...arr),sp=(mx-mn)||1;
  const pts=arr.map((v,i)=>`${(i/(arr.length-1)*w).toFixed(1)},${(h-((v-mn)/sp)*h).toFixed(1)}`).join(' ');
  const up=arr[arr.length-1]>=arr[0];
  return `<svg class="spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none"><polyline points="${pts}" fill="none" stroke="${up?'#5fd18e':'#ff6b78'}" stroke-width="2"/></svg>`;
}
function scaleBar(p){
  const lo=Math.min(p.stop,p.buy_low), hi=Math.max(p.target,p.buy_high), span=(hi-lo)||1;
  const P=v=>((v-lo)/span*100).toFixed(1);
  return `<div class="scaletrack">
    <div class="marker stopm" style="left:${P(p.stop)}%"></div>
    <div class="zone" style="left:${P(p.buy_low)}%;width:${Math.max(P(p.buy_high)-P(p.buy_low),2)}%"></div>
    <div class="marker pricem" style="left:${P(p.price)}%"></div>
    <div class="marker tgtm" style="left:${P(p.target)}%"></div></div>
    <div class="scalelegend"><span>🛑 Stop</span><span>🟦 Buy</span><span>● Now</span><span>🎯 Target</span></div>`;
}
function rrBar(p){
  const risk=Math.max(p.price-p.stop,1e-4), rew=Math.max(p.target-p.price,1e-4), tot=risk+rew;
  const rw=Math.round(100*rew/tot), rk=100-rw, ratio=(rew/risk).toFixed(1);
  return `<div class="rrlabels"><span style="color:var(--bad)">Risk</span><span style="color:var(--good)">Reward (${ratio}:1)</span></div>
  <div class="rrbar"><div class="rrrisk" style="width:${rk}%"></div><div class="rrreward" style="width:${rw}%"></div></div>`;
}
function tip(term,ex){return `<span class="tip" translate="no">${term}<span class="tiptext">${ex}</span></span>`;}
function reasoning(p){
  const trend=p.sma5>p.sma20?'in a short-term uptrend':'not in a clear uptrend';
  const mom=(p.rsi>=45&&p.rsi<=68)?'with balanced momentum':(p.rsi>68?'looking overbought (could pull back)':'with weak momentum');
  const v=p.worthwhile?'This setup looks worth considering.':'The likely move is too small to beat trading costs — probably best to skip.';
  return `${p.name} is ${trend} ${mom}. Based on how it usually moves, a realistic target is around ${p.cur}${p.target} (about ${p.tgt_move_pct}% above its last close of ${p.cur}${p.price}). ${v}`;
}
function card(p){
  const tag=p.actionable?'<span class="badge go">✓ ACTIONABLE</span>':'<span class="badge skip">✕ WATCH / SKIP</span>';
  const eur=p.india&&p.cost_eur!=null?` <span class="muted">(~€${p.cost_eur})</span>`:'';
  return `<div class="pcard ${p.actionable?'act':'skp'} reveal" data-india="${p.india?1:0}" data-act="${p.actionable?1:0}" data-conf="${p.conf}" data-name="${(p.name+' '+p.ticker).toLowerCase()}" data-score="${p.score}" data-reward="${p.tgt_move_pct}" data-move="${p.atr_pct}">
    <div class="pchead"><div><h3>${p.name} <span class="ticker" translate="no">${p.ticker}</span></h3>${tag}</div>${gauge(p.score)}</div>
    <p class="plain">${reasoning(p)}</p>
    ${sparkSVG(p.spark)}
    ${scaleBar(p)}
    ${rrBar(p)}
    <div class="grid">
      <div class="kv"><span>${tip('Buy zone','Price range where entering makes sense. Only buy if the live price is here.')}</span><b>${p.cur}${p.buy_low} – ${p.cur}${p.buy_high}</b></div>
      <div class="kv"><span>${tip('Target','Realistic price to aim to sell at, from the stock’s own history. An estimate, not a promise.')}</span><b>${p.cur}${p.target}</b></div>
      <div class="kv"><span>${tip('Stop-loss','Your safety exit. If price falls here, sell to limit the loss. Set it right after buying.')}</span><b>${p.cur}${p.stop}</b></div>
      <div class="kv"><span>${tip('Position','Whole shares that fit your budget, and the cost.')}</span><b>${p.shares} shares ≈ ${p.cur}${p.cost}${eur}</b></div>
    </div>
    <div class="sellrule">🕒 <b>When to sell:</b> aim for the target (ideally before mid-session). If not reached, exit by end of Day 3 (max 5 days). The stop-loss protects you if it drops.</div>
    <div class="src">Source: Yahoo Finance (~15-min delayed) · reliability medium-high · confirm live price in your broker.</div>
  </div>`;
}
window._filter='all';
function setFilter(el){document.querySelectorAll('.chip').forEach(c=>c.classList.remove('active'));el.classList.add('active');window._filter=el.dataset.f;localStorage.setItem('sa_filter',window._filter);applyFilters();}
function applyFilters(){
  const q=(document.getElementById('search').value||'').toLowerCase();
  const sort=document.getElementById('sortsel').value; localStorage.setItem('sa_sort',sort);
  let arr=[...DATA.picks];
  arr.sort((a,b)=> sort==='reward'?b.tgt_move_pct-a.tgt_move_pct : sort==='move'?b.atr_pct-a.atr_pct : b.score-a.score);
  const f=window._filter;
  arr=arr.filter(p=>{
    if(f==='actionable'&&!p.actionable)return false;
    if(f==='de'&&p.india)return false;
    if(f==='in'&&!p.india)return false;
    if(f==='high'&&p.conf!=='High')return false;
    if(q&&!(p.name+' '+p.ticker).toLowerCase().includes(q))return false;
    return true;
  });
  const host=document.getElementById('cards');
  host.innerHTML = arr.length?arr.map(card).join(''):'<div class="pcard skp"><p class="plain">No ideas match this filter. Sitting in cash is a valid, cost-free choice.</p></div>';
  revealObserve();
}
/* ---------- tables ---------- */
function tableHTML(series){
  if(!series.length) return '<p class="muted">No history yet.</p>';
  const rows=[...series].reverse().map(r=>`<tr><td>${r.date}</td><td translate="no">${r.ticker}</td><td>${r.pred}</td><td>${r.actual}</td><td><span class="pill ${r.hit?'hit':'miss'}">${r.hm}</span></td></tr>`).join('');
  return `<table class="perf"><thead><tr><th>Date</th><th>Stock</th><th>Predicted</th><th>Actual</th><th>Result</th></tr></thead><tbody>${rows}</tbody></table>`;
}
/* ---------- accuracy chart (cumulative %) ---------- */
function buildAccChart(){
  const merge={};
  [['DE',DATA.perf.deSeries],['IN',DATA.perf.inSeries]].forEach(([m,s])=>{
    let h=0,t=0; s.forEach(r=>{t++;h+=r.hit; (merge[r.date]=merge[r.date]||{}); });
  });
  // cumulative accuracy over ordered dates (both markets combined)
  const all=[...DATA.perf.deSeries,...DATA.perf.inSeries].sort((a,b)=>a.date.localeCompare(b.date));
  const labels=[],vals=[]; let h=0,t=0; const seen={};
  all.forEach(r=>{t++;h+=r.hit; labels.push(r.date); vals.push(Math.round(100*h/t));});
  if(!labels.length){document.getElementById('accChart').replaceWith(Object.assign(document.createElement('p'),{className:'muted',textContent:'No data yet — accuracy chart appears after the first reviews.'}));return;}
  new Chart(document.getElementById('accChart'),{type:'line',
    data:{labels,datasets:[{label:'Cumulative target accuracy %',data:vals,borderColor:'#7aa2ff',backgroundColor:'rgba(122,162,255,.15)',fill:true,tension:.3,pointRadius:3}]},
    options:{responsive:true,plugins:{legend:{labels:{color:getComputedStyle(document.body).color}}},scales:{y:{min:0,max:100,ticks:{color:'#9aa4b2'}},x:{ticks:{color:'#9aa4b2'}}}}});
}
/* ---------- scroll reveal ---------- */
let _io;
function revealObserve(){
  if(!_io){_io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting)e.target.classList.add('show');}),{threshold:.08});}
  document.querySelectorAll('.reveal:not(.show)').forEach(el=>_io.observe(el));
}
/* ---------- stale banner ---------- */
function staleCheck(){
  const w=[];
  if(DATA.dateDE!==DATA.today&&DATA.dateDE!=='-')w.push('Germany ('+DATA.dateDE+')');
  if(DATA.dateIN!==DATA.today&&DATA.dateIN!=='-')w.push('India ('+DATA.dateIN+')');
  if(w.length)document.getElementById('staleBox').innerHTML='<div class="alert">⚠️ Some data isn’t from today ('+DATA.today+' CET): '+w.join(', ')+'. Run the scan workflow to refresh before acting.</div>';
}
/* ---------- google translate ---------- */
function googleTranslateElementInit(){new google.translate.TranslateElement({pageLanguage:'en',includedLanguages:'en,de,hi,fr,es,zh-CN,ar,ru,it,pt',layout:google.translate.TranslateElement.InlineLayout.SIMPLE},'google_translate_element');}
/* ---------- init ---------- */
function init(){
  loadPrefs();
  document.getElementById('themeBtn').textContent=document.documentElement.getAttribute('data-theme')==='light'?'☀️ Theme':'🌙 Theme';
  document.getElementById('tActionable').textContent=DATA.actionableToday;
  document.getElementById('tAnalysed').textContent=DATA.picks.length;
  const ah=DATA.perf.deHit+DATA.perf.inHit, at=DATA.perf.deTot+DATA.perf.inTot;
  document.getElementById('tAccuracy').textContent=at?Math.round(100*ah/at)+'%':'—';
  document.getElementById('perfBreak').textContent='🇩🇪 Germany: '+DATA.perf.deHit+'/'+DATA.perf.deTot+' · 🇮🇳 India: '+DATA.perf.inHit+'/'+DATA.perf.inTot;
  document.getElementById('updatedLine').textContent='🇩🇪 '+DATA.generatedDE+'  ·  🇮🇳 '+DATA.generatedIN;
  document.getElementById('lessonsDE').textContent=DATA.lessonsDE;
  document.getElementById('lessonsIN').textContent=DATA.lessonsIN;
  document.getElementById('deTable').innerHTML=tableHTML(DATA.perf.deSeries);
  document.getElementById('inTable').innerHTML=tableHTML(DATA.perf.inSeries);
  // restore active filter chip
  document.querySelectorAll('.chip').forEach(c=>{c.classList.toggle('active',c.dataset.f===window._filter);});
  applyFilters();
  buildAccChart();
  revealObserve();
  const s=document.createElement('script');s.src='https://translate.google.com/translate_a/element.js?cb=googleTranslateElementInit';document.head.appendChild(s);
}
document.addEventListener('DOMContentLoaded',init);
</script>
</body></html>"""

    doc = doc.replace("__DATA__", data_json)
    with open("index.html", "w") as f:
        f.write(doc)
    print("Premium dashboard written: " + str(len(picks_all)) + " picks total")

if __name__ == "__main__":
    main()
