# build_dashboard.py — SPA dashboard (Drop 2 complete): Overview, Ideas, Analytics,
# Watchlist (full universe), Learnings, About. All times CET. NOT financial advice.

import json, os, csv, datetime

def load_json(p, d):
    if os.path.exists(p):
        with open(p) as f: return json.load(f)
    return d

def collect(picks, cur, is_india):
    out=[]
    for p in picks:
        act=p.get("worthwhile") and p.get("conf") in ("Med","High")
        out.append({"ticker":p["ticker"],"name":p["name"],"cur":cur,"india":is_india,"conf":p["conf"],
            "score":p["score"],"price":p["price"],"buy_low":p["buy_low"],"buy_high":p["buy_high"],
            "stop":p["stop"],"target":p["est_dayhigh"],"dayend":p["est_dayend"],"tgt_move_pct":p["tgt_move_pct"],
            "shares":p["shares"],"cost":p["cost"],"cost_eur":p.get("cost_eur"),"rsi":p["rsi"],
            "atr_pct":p["atr_pct"],"sma5":p["sma5"],"sma20":p["sma20"],"worthwhile":p["worthwhile"],
            "actionable":bool(act),"spark":p.get("spark",[])})
    return out

def perf_stats(f):
    t=h=0
    if os.path.exists(f):
        with open(f) as fh:
            for r in csv.DictReader(fh):
                t+=1
                if r.get("hit_miss","").startswith("HIT"): h+=1
    return h,t

def perf_series(f):
    rows=[]
    if os.path.exists(f):
        with open(f) as fh:
            for r in csv.DictReader(fh):
                try: rows.append({"date":r.get("date"),"ticker":r.get("ticker"),
                    "pred":float(r.get("predicted_dayhigh") or 0),"actual":float(r.get("actual_dayhigh") or 0),
                    "hit":1 if r.get("hit_miss","").startswith("HIT") else 0,"hm":r.get("hit_miss","")})
                except Exception: pass
    return rows

def lessons_text(f):
    if os.path.exists(f):
        with open(f) as fh: return fh.read()
    return "No lessons recorded yet."

def main():
    de=load_json("picks_today.json",{"picks":[],"date":"-","generated":"—","actionable_count":0})
    ind=load_json("picks_today_in.json",{"picks":[],"date":"-","generated":"—","actionable_count":0,"eurinr":"?"})
    uni_de=load_json("analysed_all.json",{"items":[]})
    uni_in=load_json("analysed_all_in.json",{"items":[]})
    today=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=1))).strftime("%Y-%m-%d")
    picks_all=collect(de.get("picks",[]),"€",False)+collect(ind.get("picks",[]),"₹",True)
    dh,dt=perf_stats("performance_log.csv"); ih,it=perf_stats("performance_log_in.csv")
    payload={"generatedDE":de.get("generated","—"),"generatedIN":ind.get("generated","—"),
        "dateDE":de.get("date"),"dateIN":ind.get("date"),"today":today,"eurinr":ind.get("eurinr","?"),
        "picks":picks_all,
        "uni":{"DE":uni_de.get("items",[]),"IN":uni_in.get("items",[])},
        "perf":{"deHit":dh,"deTot":dt,"inHit":ih,"inTot":it,
            "deSeries":perf_series("performance_log.csv"),"inSeries":perf_series("performance_log_in.csv")},
        "lessonsDE":lessons_text("strategy_memory.md"),"lessonsIN":lessons_text("strategy_memory_in.md"),
        "actionableToday":de.get("actionable_count",0)+ind.get("actionable_count",0)}
    data_json=json.dumps(payload)

    doc = r"""<!DOCTYPE html><html lang="en" data-theme="dark"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="Cache-Control" content="no-cache, must-revalidate"><meta name="last-build" content="__BUILD__">
<title>Swing Agent — Stock Ideas</title><link rel="manifest" href="manifest.json"><meta name="theme-color" content="#0b0e14">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"></script>
<style>
:root{--bg:#0a0d14;--bg2:#0f1420;--glass:rgba(255,255,255,.05);--line:rgba(255,255,255,.09);--txt:#eaf0f7;--mut:#8b95a7;--acc:#6c8cff;--acc2:#9a6cff;--good:#39d98a;--bad:#ff5d73;--warn:#ffc86b}
[data-theme="light"]{--bg:#eef1f7;--bg2:#fff;--glass:rgba(0,0,0,.03);--line:rgba(0,0,0,.10);--txt:#141b2b;--mut:#5b6577;--acc:#2b5cff;--acc2:#7a3cff;--good:#12a150;--bad:#e03e52;--warn:#b7791f}
*{box-sizing:border-box}html,body{margin:0;height:100%}
body{font-family:-apple-system,'Segoe UI',Roboto,Arial,sans-serif;background:radial-gradient(1200px 600px at 80% -10%,rgba(108,140,255,.12),transparent),radial-gradient(900px 500px at -10% 20%,rgba(154,108,255,.10),transparent),var(--bg);color:var(--txt);transition:.4s}
.num{font-variant-numeric:tabular-nums}.app{display:flex;min-height:100vh}
.side{width:236px;flex:none;background:linear-gradient(180deg,var(--bg2),transparent);border-right:1px solid var(--line);padding:18px 12px;position:sticky;top:0;height:100vh;transition:width .3s}
.side.collapsed{width:72px}.logo{display:flex;align-items:center;gap:10px;padding:6px 8px 16px;font-weight:800;font-size:18px}
.logo .dot{width:30px;height:30px;border-radius:9px;background:linear-gradient(135deg,var(--acc),var(--acc2));display:grid;place-items:center}
.side.collapsed .logo span,.side.collapsed .nav b span,.side.collapsed .sideft{display:none}
.nav{display:flex;flex-direction:column;gap:4px;margin-top:6px}
.nav b{display:flex;align-items:center;gap:12px;padding:11px 12px;border-radius:12px;color:var(--mut);font-weight:600;font-size:14px;cursor:pointer;transition:.2s;border:1px solid transparent}
.nav b .ic{font-size:18px;width:22px;text-align:center}.nav b:hover{background:var(--glass);color:var(--txt)}
.nav b.active{background:linear-gradient(135deg,rgba(108,140,255,.22),rgba(154,108,255,.16));color:var(--txt);border-color:var(--line)}
.sideft{color:var(--mut);font-size:11px;padding:12px 10px;position:absolute;bottom:8px;width:212px}
.collapseBtn{margin:8px;background:var(--glass);border:1px solid var(--line);color:var(--mut);border-radius:10px;padding:7px;cursor:pointer;width:calc(100% - 16px)}
.main{flex:1;min-width:0;display:flex;flex-direction:column}
.topbar{position:sticky;top:0;z-index:40;display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 20px;background:rgba(10,13,20,.6);backdrop-filter:blur(12px);border-bottom:1px solid var(--line)}
[data-theme="light"] .topbar{background:rgba(255,255,255,.6)}
.vt{font-size:18px;font-weight:700}.ctrls{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.ctrls select,.ctrls input,.ctrls button{background:var(--glass);color:var(--txt);border:1px solid var(--line);border-radius:10px;padding:8px 10px;font-size:13px}
.content{padding:20px;max-width:1100px;width:100%;margin:0 auto}
.view{display:none;animation:fade .45s}.view.active{display:block}@keyframes fade{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
.bento{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}
.glass{background:var(--glass);border:1px solid var(--line);border-radius:18px;padding:18px;backdrop-filter:blur(8px);transition:.25s}
.glass:hover{transform:translateY(-3px);box-shadow:0 14px 34px rgba(0,0,0,.3)}
.span2{grid-column:span 2}.span4{grid-column:span 4}
.hero{grid-column:span 2;grid-row:span 2;display:flex;flex-direction:column;justify-content:center;background:linear-gradient(135deg,rgba(108,140,255,.18),rgba(154,108,255,.12))}
.hero .hn{font-size:64px;font-weight:900;line-height:1;background:linear-gradient(135deg,var(--acc),var(--acc2));-webkit-background-clip:text;background-clip:text;color:transparent}
.hero .hl{color:var(--mut);margin-top:8px;font-size:14px}.kpi .k{font-size:30px;font-weight:800;color:var(--acc)}.kpi .l{color:var(--mut);font-size:12px;margin-top:4px}.spot{border-left:3px solid var(--good)}
.toolbar{display:flex;gap:8px;flex-wrap:wrap;margin:6px 0 14px}
.chip{background:var(--glass);border:1px solid var(--line);color:var(--txt);border-radius:20px;padding:7px 14px;font-size:13px;cursor:pointer;transition:.2s}
.chip.active{background:linear-gradient(135deg,var(--acc),var(--acc2));color:#fff;border-color:transparent}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px}
.pcard{background:var(--glass);border:1px solid var(--line);border-radius:18px;padding:16px;backdrop-filter:blur(8px);transition:.25s}
.pcard:hover{transform:translateY(-4px);box-shadow:0 16px 36px rgba(0,0,0,.32)}
.pcard.act{border-top:3px solid var(--good)}.pcard.skp{border-top:3px solid var(--bad)}
.pchead{display:flex;justify-content:space-between;gap:10px}.pchead h3{margin:0;font-size:16px}.ticker{color:var(--acc);font-size:12px;font-weight:600}
.badge{display:inline-block;margin-top:6px;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:800}
.badge.go{background:rgba(57,217,138,.15);color:var(--good)}.badge.skip{background:rgba(255,93,115,.15);color:var(--bad)}
.plain{color:var(--txt);font-size:13px;opacity:.92}.spark{width:100%;height:40px;margin:6px 0}
.scaletrack{position:relative;height:12px;background:var(--line);border-radius:8px;margin:8px 0}
.zone{position:absolute;top:0;height:12px;background:rgba(108,140,255,.35);border:1px solid var(--acc);border-radius:4px}
.marker{position:absolute;top:-4px;width:2px;height:20px}.stopm{background:var(--bad)}.tgtm{background:var(--good)}
.pricem{width:10px;height:10px;top:1px;border-radius:50%;background:var(--txt);transform:translateX(-4px)}
.scalelegend{display:flex;justify-content:space-between;color:var(--mut);font-size:10px}
.rrbar{display:flex;height:10px;border-radius:6px;overflow:hidden;margin:8px 0}.rrrisk{background:var(--bad)}.rrreward{background:var(--good)}
.rrlabels{display:flex;justify-content:space-between;font-size:11px;margin-bottom:3px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:10px 0}
.kv{background:var(--bg2);border:1px solid var(--line);border-radius:10px;padding:8px;font-size:12px}.kv span{color:var(--mut);font-size:11px;display:block}.kv b{font-size:14px}
.tip{border-bottom:1px dotted var(--acc);cursor:help;position:relative}
.tip .tt{visibility:hidden;opacity:0;transition:.15s;position:absolute;bottom:130%;left:0;z-index:9;background:#0a0f18;color:#fff;border:1px solid var(--line);border-radius:8px;padding:8px;width:200px;font-size:11px}
.tip:hover .tt{visibility:visible;opacity:1}
.sellrule{background:var(--bg2);border:1px dashed var(--line);border-radius:10px;padding:9px;font-size:12px;margin-top:6px}
.src{color:var(--mut);font-size:10px;margin-top:6px}.gauge{width:96px;height:58px;flex:none}
.alert{background:rgba(255,93,115,.12);border:1px solid var(--bad);color:var(--bad);padding:11px 14px;border-radius:12px;margin:0 0 12px;font-size:13px}
.disc{background:rgba(255,200,107,.10);border:1px solid var(--warn);color:var(--warn);padding:11px 14px;border-radius:12px;margin:12px 0;font-size:12px}
.soon{color:var(--mut);text-align:center;padding:50px 20px}.guide ol{margin:8px 0 0 18px;font-size:14px}.guide li{margin:6px 0}
table.tbl{width:100%;border-collapse:collapse;font-size:13px;margin-top:10px}table.tbl th,table.tbl td{text-align:left;padding:8px;border-bottom:1px solid var(--line)}
.pill{padding:2px 8px;border-radius:12px;font-size:11px;font-weight:700}.pill.hit{background:rgba(57,217,138,.15);color:var(--good)}.pill.miss{background:rgba(255,93,115,.15);color:var(--bad)}
.lessons{white-space:pre-wrap;font-family:inherit;color:var(--txt);font-size:13px;margin:0}
.tag2{padding:2px 8px;border-radius:8px;font-size:11px;font-weight:700}.tag2.h{background:rgba(57,217,138,.15);color:var(--good)}.tag2.m{background:rgba(255,200,107,.15);color:var(--warn)}.tag2.l{background:rgba(255,93,115,.15);color:var(--bad)}
#gt{display:inline-block}.goog-te-gadget{font-size:0!important}.goog-te-gadget .goog-te-combo{color:#111;font-size:13px;padding:6px;border-radius:8px}
.bottomnav{display:none}
@media(max-width:820px){.side{display:none}.cards{grid-template-columns:1fr}.bento{grid-template-columns:repeat(2,1fr)}.hero{grid-column:span 2}.span2{grid-column:span 2}.span4{grid-column:span 2}.content{padding:14px 12px 90px}
.bottomnav{display:flex;position:fixed;bottom:0;left:0;right:0;z-index:60;background:rgba(10,13,20,.9);backdrop-filter:blur(12px);border-top:1px solid var(--line);justify-content:space-around;padding:8px 4px}
[data-theme="light"] .bottomnav{background:rgba(255,255,255,.9)}
.bottomnav b{display:flex;flex-direction:column;align-items:center;gap:2px;color:var(--mut);font-size:10px;font-weight:600;cursor:pointer;padding:4px 8px;border-radius:10px}.bottomnav b.active{color:var(--acc)}.bottomnav b .ic{font-size:20px}}
</style></head><body>
<div class="app">
  <aside class="side" id="side">
    <div class="logo"><span class="dot">📈</span><span>Swing Agent</span></div>
    <nav class="nav" id="nav">
      <b data-v="overview" class="active"><span class="ic">🏠</span><span>Overview</span></b>
      <b data-v="ideas"><span class="ic">💡</span><span>Ideas</span></b>
      <b data-v="analytics"><span class="ic">📊</span><span>Analytics</span></b>
      <b data-v="watchlist"><span class="ic">📋</span><span>Watchlist</span></b>
      <b data-v="learnings"><span class="ic">🧠</span><span>Learnings</span></b>
      <b data-v="about"><span class="ic">ℹ️</span><span>About</span></b>
    </nav>
    <button class="collapseBtn" onclick="toggleSide()">⇔</button>
    <div class="sideft" translate="no">Research/education only — not financial advice. Data ~15-min delayed.</div>
  </aside>
  <div class="main">
    <div class="topbar"><div class="vt" id="viewTitle">Overview</div>
      <div class="ctrls"><div id="gt"></div>
        <input id="search" placeholder="🔎 Search…" oninput="applyFilters()">
        <select id="sortsel" onchange="applyFilters()"><option value="score">Confidence</option><option value="reward">Reward %</option><option value="move">Movement</option></select>
        <button id="themeBtn" onclick="toggleTheme()">☀️</button></div>
    </div>
    <div class="content"><div id="staleBox"></div>
      <section class="view active" id="v-overview">
        <div class="disc" translate="no"><b>Please read:</b> Research &amp; education, <b>not financial advice</b>. Estimates from ~15-min delayed data (prior close). You place &amp; own every trade.</div>
        <div class="bento">
          <div class="glass hero"><div class="hn num" id="heroNum">0</div><div class="hl">Actionable ideas today — filtered for trading costs across both markets.</div></div>
          <div class="glass kpi"><div class="k num" id="kAnalysed">0</div><div class="l">Stocks analysed today</div></div>
          <div class="glass kpi"><div class="k num" id="kAccuracy">—</div><div class="l">Target accuracy (all time)</div></div>
          <div class="glass kpi"><div class="k num" id="kDE">0</div><div class="l">🇩🇪 Germany ideas</div></div>
          <div class="glass kpi"><div class="k num" id="kIN">0</div><div class="l">🇮🇳 India ideas</div></div>
          <div class="glass span2 spot" id="spotlight"></div>
          <div class="glass span2"><canvas id="miniAcc" height="120"></canvas></div>
        </div>
        <div class="glass guide" style="margin-top:14px"><h3 style="margin:0 0 6px">🧭 How to read this</h3><ol>
          <li>Open <b>Ideas</b> for today’s picks.</li><li>Green <b>✓ ACTIONABLE</b> = worth considering; <b>WATCH/SKIP</b> = don’t trade today.</li>
          <li>Use <b>Analytics</b> for accuracy, <b>Watchlist</b> for the full scan, <b>Learnings</b> for how the system adapts.</li>
          <li>Always confirm the <b>live price</b> in your broker — data ~15 min delayed.</li></ol></div>
      </section>
      <section class="view" id="v-ideas">
        <div class="toolbar"><span class="chip active" data-f="all" onclick="setFilter(this)">All</span>
          <span class="chip" data-f="actionable" onclick="setFilter(this)">✓ Actionable</span>
          <span class="chip" data-f="de" onclick="setFilter(this)">🇩🇪 Germany</span>
          <span class="chip" data-f="in" onclick="setFilter(this)">🇮🇳 India</span>
          <span class="chip" data-f="high" onclick="setFilter(this)">High confidence</span></div>
        <div class="cards" id="cards"></div>
      </section>
      <section class="view" id="v-analytics">
        <div class="bento">
          <div class="glass span2"><h3 style="margin:0 0 8px">Cumulative accuracy over time</h3><canvas id="accChart" height="150"></canvas></div>
          <div class="glass"><h3 style="margin:0 0 8px">🇩🇪 Germany hit-rate</h3><canvas id="deDonut" height="150"></canvas></div>
          <div class="glass"><h3 style="margin:0 0 8px">🇮🇳 India hit-rate</h3><canvas id="inDonut" height="150"></canvas></div>
          <div class="glass span4"><h3 style="margin:0 0 8px">Predicted vs actual (recent)</h3><canvas id="devChart" height="140"></canvas>
            <p class="plain" style="color:var(--mut);margin-top:8px">Bars above 0 = target reached (HIT); below 0 = fell short (MISS). Helps see if estimates lean optimistic.</p></div>
        </div>
      </section>
      <section class="view" id="v-watchlist">
        <div class="toolbar"><span class="chip active" data-w="all" onclick="setWFilter(this)">All markets</span>
          <span class="chip" data-w="DE" onclick="setWFilter(this)">🇩🇪 Germany</span>
          <span class="chip" data-w="IN" onclick="setWFilter(this)">🇮🇳 India</span></div>
        <div class="glass"><div id="uniTable"></div></div>
      </section>
      <section class="view" id="v-learnings">
        <div class="glass"><h3 style="margin-top:0">🇩🇪 Germany — strategy memory</h3><pre class="lessons" id="lessonsDE"></pre></div>
        <div class="glass"><h3 style="margin-top:0">🇮🇳 India — strategy memory</h3><pre class="lessons" id="lessonsIN"></pre></div>
      </section>
      <section class="view" id="v-about">
        <div class="glass"><h3 style="margin-top:0">How it works</h3>
          <p class="plain">Each morning the agent auto-builds a watchlist of liquid, affordable movers, scores them on trend, momentum (RSI), volatility (ATR) and liquidity, then sets a <b>history-based realistic target</b>, a stop-loss and a cost-aware “worthwhile” check. Germany needs ≥3% expected move (fees ~1%), India ≥1.5% (costs ~0.35%). After market close it logs actual vs predicted and writes lessons that adjust future picks.</p></div>
        <div class="glass"><h3 style="margin-top:0">Data &amp; reliability</h3>
          <p class="plain">Prices via Yahoo Finance (yfinance), <b>~15-min delayed, based on prior close</b> — reliability medium-high; always confirm live in your broker. No rumor/forum sources used.</p></div>
        <div class="disc" translate="no"><b>Risk &amp; responsibility:</b> This is research/education, <b>NOT financial advice</b>. Markets are risky; you can lose money. India costs are estimates — confirm on your contract note. You are responsible for every trade and for tax/regulatory compliance (BaFin/MiFID in EU; SEBI/STT in India).</div>
      </section>
    </div>
  </div>
</div>
<nav class="bottomnav" id="bnav">
  <b data-v="overview" class="active"><span class="ic">🏠</span>Home</b>
  <b data-v="ideas"><span class="ic">💡</span>Ideas</b>
  <b data-v="analytics"><span class="ic">📊</span>Stats</b>
  <b data-v="watchlist"><span class="ic">📋</span>List</b>
  <b data-v="about"><span class="ic">ℹ️</span>Info</b>
</nav>
<script>
const DATA=__DATA__;const TITLES={overview:'Overview',ideas:'Today’s Ideas',analytics:'Analytics',watchlist:'Watchlist',learnings:'Learnings',about:'About & Methodology'};
let _charts={};window._filter='all';window._wfilter='all';
function loadPrefs(){document.documentElement.setAttribute('data-theme',localStorage.getItem('sa_theme')||'dark');window._filter=localStorage.getItem('sa_filter')||'all';document.getElementById('sortsel').value=localStorage.getItem('sa_sort')||'score';if(localStorage.getItem('sa_side')==='1')document.getElementById('side').classList.add('collapsed');}
function toggleTheme(){const c=document.documentElement.getAttribute('data-theme'),n=c==='light'?'dark':'light';document.documentElement.setAttribute('data-theme',n);localStorage.setItem('sa_theme',n);document.getElementById('themeBtn').textContent=n==='light'?'🌙':'☀️';}
function toggleSide(){document.getElementById('side').classList.toggle('collapsed');localStorage.setItem('sa_side',document.getElementById('side').classList.contains('collapsed')?'1':'0');}
function nav(v){document.querySelectorAll('.view').forEach(s=>s.classList.remove('active'));document.getElementById('v-'+v).classList.add('active');document.querySelectorAll('#nav b,#bnav b').forEach(b=>b.classList.toggle('active',b.dataset.v===v));document.getElementById('viewTitle').textContent=TITLES[v];window.scrollTo({top:0,behavior:'smooth'});if(v==='analytics')buildAnalytics();if(v==='watchlist')buildWatch();}
function gauge(s){const p=Math.max(0,Math.min(100,s))/100,a=180*p,r=(180-a)*Math.PI/180,x=48+40*Math.cos(r),y=48-40*Math.sin(r),c=s>=72?'var(--good)':s>=60?'var(--warn)':'var(--bad)',L=a>90?1:0;return `<svg class="gauge" viewBox="0 0 96 58"><path d="M8 48 A40 40 0 0 1 88 48" fill="none" stroke="var(--line)" stroke-width="8"/><path d="M8 48 A40 40 0 ${L} 1 ${x.toFixed(1)} ${y.toFixed(1)}" fill="none" stroke="${c}" stroke-width="8" stroke-linecap="round"/><text x="48" y="44" text-anchor="middle" fill="var(--txt)" font-size="16" font-weight="800">${Math.round(s)}</text></svg>`;}
function spark(a){if(!a||a.length<2)return'';const w=300,h=40,mn=Math.min(...a),mx=Math.max(...a),sp=(mx-mn)||1,pts=a.map((v,i)=>`${(i/(a.length-1)*w).toFixed(1)},${(h-((v-mn)/sp)*h).toFixed(1)}`).join(' '),up=a[a.length-1]>=a[0];return `<svg class="spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none"><polyline points="${pts}" fill="none" stroke="${up?'var(--good)':'var(--bad)'}" stroke-width="2"/></svg>`;}
function scale(p){const lo=Math.min(p.stop,p.buy_low),hi=Math.max(p.target,p.buy_high),sp=(hi-lo)||1,P=v=>((v-lo)/sp*100).toFixed(1);return `<div class="scaletrack"><div class="marker stopm" style="left:${P(p.stop)}%"></div><div class="zone" style="left:${P(p.buy_low)}%;width:${Math.max(P(p.buy_high)-P(p.buy_low),2)}%"></div><div class="marker pricem" style="left:${P(p.price)}%"></div><div class="marker tgtm" style="left:${P(p.target)}%"></div></div><div class="scalelegend"><span>🛑 Stop</span><span>🟦 Buy</span><span>● Now</span><span>🎯 Target</span></div>`;}
function rr(p){const rk=Math.max(p.price-p.stop,1e-4),rw=Math.max(p.target-p.price,1e-4),t=rk+rw,W=Math.round(100*rw/t),R=100-W,ra=(rw/rk).toFixed(1);return `<div class="rrlabels"><span style="color:var(--bad)">Risk</span><span style="color:var(--good)">Reward (${ra}:1)</span></div><div class="rrbar"><div class="rrrisk" style="width:${R}%"></div><div class="rrreward" style="width:${W}%"></div></div>`;}
function tip(t,e){return `<span class="tip" translate="no">${t}<span class="tt">${e}</span></span>`;}
function reason(p){const tr=p.sma5>p.sma20?'in a short-term uptrend':'not in a clear uptrend',m=(p.rsi>=45&&p.rsi<=68)?'with balanced momentum':(p.rsi>68?'looking overbought':'with weak momentum'),v=p.worthwhile?'Worth considering.':'Likely move too small to beat costs — probably skip.';return `${p.name} is ${tr} ${m}. Realistic target ~${p.cur}${p.target} (about ${p.tgt_move_pct}% above last close ${p.cur}${p.price}). ${v}`;}
function card(p){const tag=p.actionable?'<span class="badge go">✓ ACTIONABLE</span>':'<span class="badge skip">✕ WATCH / SKIP</span>',eur=p.india&&p.cost_eur!=null?` <span style="color:var(--mut)">(~€${p.cost_eur})</span>`:'';return `<div class="pcard ${p.actionable?'act':'skp'}"><div class="pchead"><div><h3>${p.name} <span class="ticker" translate="no">${p.ticker}</span></h3>${tag}</div>${gauge(p.score)}</div><p class="plain">${reason(p)}</p>${spark(p.spark)}${scale(p)}${rr(p)}<div class="grid2"><div class="kv"><span>${tip('Buy zone','Enter only if live price is here.')}</span><b class="num">${p.cur}${p.buy_low}–${p.cur}${p.buy_high}</b></div><div class="kv"><span>${tip('Target','Realistic sell aim, from history. Estimate.')}</span><b class="num">${p.cur}${p.target}</b></div><div class="kv"><span>${tip('Stop-loss','Safety exit. Set right after buying.')}</span><b class="num">${p.cur}${p.stop}</b></div><div class="kv"><span>${tip('Position','Whole shares fitting budget.')}</span><b class="num">${p.shares} sh ≈ ${p.cur}${p.cost}${eur}</b></div></div><div class="sellrule">🕒 <b>Sell:</b> aim for target (before mid-session). Else exit by Day 3 (max 5). Stop-loss protects you.</div><div class="src">Yahoo Finance (~15-min delayed) · confirm live price in broker.</div></div>`;}
function setFilter(el){document.querySelectorAll('#v-ideas .chip').forEach(c=>c.classList.remove('active'));el.classList.add('active');window._filter=el.dataset.f;localStorage.setItem('sa_filter',window._filter);applyFilters();}
function applyFilters(){const q=(document.getElementById('search').value||'').toLowerCase(),s=document.getElementById('sortsel').value;localStorage.setItem('sa_sort',s);let a=[...DATA.picks];a.sort((x,y)=>s==='reward'?y.tgt_move_pct-x.tgt_move_pct:s==='move'?y.atr_pct-x.atr_pct:y.score-x.score);const f=window._filter;a=a.filter(p=>{if(f==='actionable'&&!p.actionable)return false;if(f==='de'&&p.india)return false;if(f==='in'&&!p.india)return false;if(f==='high'&&p.conf!=='High')return false;if(q&&!(p.name+' '+p.ticker).toLowerCase().includes(q))return false;return true;});document.getElementById('cards').innerHTML=a.length?a.map(card).join(''):'<div class="pcard skp"><p class="plain">No ideas match. Cash is a valid, cost-free choice.</p></div>';}
function setWFilter(el){document.querySelectorAll('#v-watchlist .chip').forEach(c=>c.classList.remove('active'));el.classList.add('active');window._wfilter=el.dataset.w;buildWatch();}
function buildWatch(){let items=[];if(window._wfilter!=='IN')items=items.concat(DATA.uni.DE.map(x=>({...x,m:'🇩🇪'})));if(window._wfilter!=='DE')items=items.concat(DATA.uni.IN.map(x=>({...x,m:'🇮🇳'})));items.sort((a,b)=>b.score-a.score);if(!items.length){document.getElementById('uniTable').innerHTML='<p class="soon">No universe data yet — run the morning scan after adding Step 1.</p>';return;}const rows=items.map(x=>{const cl=x.conf==='High'?'h':x.conf==='Med'?'m':'l';return `<tr><td>${x.m}</td><td><b>${x.name}</b><br><span class="ticker" translate="no">${x.ticker}</span></td><td class="num">${x.price}</td><td><span class="tag2 ${cl}">${x.conf} ${x.score}</span></td><td class="num">${x.atr_pct}%</td><td class="num">${x.rsi}</td><td>${x.worthwhile?'<span class="pill hit">✓</span>':'<span class="pill miss">skip</span>'}</td><td style="width:120px">${spark(x.spark)}</td></tr>`;}).join('');document.getElementById('uniTable').innerHTML=`<table class="tbl"><thead><tr><th></th><th>Stock</th><th>Price</th><th>Confidence</th><th>Move(ATR)</th><th>RSI</th><th>Tradable</th><th>30-day</th></tr></thead><tbody>${rows}</tbody></table>`;}
function tblHTML(s){if(!s.length)return'<p class="soon">No history yet.</p>';const r=[...s].reverse().map(x=>`<tr><td>${x.date}</td><td translate="no">${x.ticker}</td><td class="num">${x.pred}</td><td class="num">${x.actual}</td><td><span class="pill ${x.hit?'hit':'miss'}">${x.hm}</span></td></tr>`).join('');return `<table class="tbl"><thead><tr><th>Date</th><th>Stock</th><th>Predicted</th><th>Actual</th><th>Result</th></tr></thead><tbody>${r}</tbody></table>`;}
function countUp(el,to){let n=0;const st=Math.max(1,Math.ceil(to/24)),t=setInterval(()=>{n+=st;if(n>=to){n=to;clearInterval(t);}el.textContent=n;},22);}
function spotlight(){const acts=DATA.picks.filter(p=>p.actionable).sort((a,b)=>b.score-a.score),el=document.getElementById('spotlight');if(!acts.length){el.innerHTML='<b>🎯 Idea of the day</b><p class="plain" style="margin:8px 0 0">No actionable idea today. Cash is a valid position.</p>';return;}const p=acts[0];el.innerHTML=`<b>🎯 Idea of the day</b><h3 style="margin:8px 0 2px">${p.name} <span class="ticker" translate="no">${p.ticker}</span></h3><p class="plain" style="margin:0">Confidence ${p.conf} · target ${p.cur}${p.target} (~${p.tgt_move_pct}%)</p><p class="plain" style="margin:6px 0 0;color:var(--mut)">Open <b>Ideas</b> for full details.</p>`;}
function mkLine(id,L,V){const c=document.getElementById(id);if(!L.length){c.replaceWith(Object.assign(document.createElement('div'),{className:'soon',textContent:'Chart appears after first reviews.'}));return;}_charts[id]&&_charts[id].destroy();_charts[id]=new Chart(c,{type:'line',data:{labels:L,datasets:[{label:'Cumulative accuracy %',data:V,borderColor:'#6c8cff',backgroundColor:'rgba(108,140,255,.15)',fill:true,tension:.3,pointRadius:2}]},options:{plugins:{legend:{labels:{color:getComputedStyle(document.body).color}}},scales:{y:{min:0,max:100,ticks:{color:'#8b95a7'}},x:{ticks:{color:'#8b95a7'}}}}});}
function mkDonut(id,hit,tot){const c=document.getElementById(id);_charts[id]&&_charts[id].destroy();_charts[id]=new Chart(c,{type:'doughnut',data:{labels:['Hit','Miss'],datasets:[{data:[hit,Math.max(tot-hit,0)],backgroundColor:['#39d98a','#ff5d73'],borderWidth:0}]},options:{cutout:'68%',plugins:{legend:{labels:{color:getComputedStyle(document.body).color}}}}});}
function buildAnalytics(){const all=[...DATA.perf.deSeries,...DATA.perf.inSeries].sort((a,b)=>a.date.localeCompare(b.date));const L=[],V=[];let h=0,t=0;all.forEach(r=>{t++;h+=r.hit;L.push(r.date);V.push(Math.round(100*h/t));});mkLine('accChart',L,V);mkDonut('deDonut',DATA.perf.deHit,DATA.perf.deTot);mkDonut('inDonut',DATA.perf.inHit,DATA.perf.inTot);const dev=all.slice(-14);const c=document.getElementById('devChart');if(!dev.length){c.replaceWith(Object.assign(document.createElement('div'),{className:'soon',textContent:'Deviation chart appears after first reviews.'}));return;}_charts['dev']&&_charts['dev'].destroy();_charts['dev']=new Chart(c,{type:'bar',data:{labels:dev.map(d=>d.ticker),datasets:[{label:'Actual − Predicted %',data:dev.map(d=>d.pred?+(100*(d.actual-d.pred)/d.pred).toFixed(2):0),backgroundColor:dev.map(d=>d.hit?'#39d98a':'#ff5d73')}]},options:{plugins:{legend:{labels:{color:getComputedStyle(document.body).color}}},scales:{y:{ticks:{color:'#8b95a7'}},x:{ticks:{color:'#8b95a7'}}}}});}
function miniAcc(){const all=[...DATA.perf.deSeries,...DATA.perf.inSeries].sort((a,b)=>a.date.localeCompare(b.date)),L=[],V=[];let h=0,t=0;all.forEach(r=>{t++;h+=r.hit;L.push(r.date);V.push(Math.round(100*h/t));});mkLine('miniAcc',L,V);}
function stale(){const w=[];if(DATA.dateDE!==DATA.today&&DATA.dateDE!=='-')w.push('Germany ('+DATA.dateDE+')');if(DATA.dateIN!==DATA.today&&DATA.dateIN!=='-')w.push('India ('+DATA.dateIN+')');if(w.length)document.getElementById('staleBox').innerHTML='<div class="alert">⚠️ Some data isn’t from today ('+DATA.today+' CET): '+w.join(', ')+'. Run the scan to refresh.</div>';}
function googleTranslateElementInit(){new google.translate.TranslateElement({pageLanguage:'en',includedLanguages:'en,de,hi,fr,es,zh-CN,ar,ru,it,pt',layout:google.translate.TranslateElement.InlineLayout.SIMPLE},'gt');}
function init(){loadPrefs();document.getElementById('themeBtn').textContent=document.documentElement.getAttribute('data-theme')==='light'?'🌙':'☀️';document.querySelectorAll('#nav b,#bnav b').forEach(b=>b.onclick=()=>nav(b.dataset.v));const ah=DATA.perf.deHit+DATA.perf.inHit,at=DATA.perf.deTot+DATA.perf.inTot;countUp(document.getElementById('heroNum'),DATA.actionableToday);countUp(document.getElementById('kAnalysed'),DATA.picks.length);document.getElementById('kAccuracy').textContent=at?Math.round(100*ah/at)+'%':'—';countUp(document.getElementById('kDE'),DATA.picks.filter(p=>!p.india).length);countUp(document.getElementById('kIN'),DATA.picks.filter(p=>p.india).length);document.querySelectorAll('#v-ideas .chip').forEach(c=>c.classList.toggle('active',c.dataset.f===window._filter));applyFilters();spotlight();miniAcc();document.getElementById('lessonsDE').textContent=DATA.lessonsDE;document.getElementById('lessonsIN').textContent=DATA.lessonsIN;stale();const s=document.createElement('script');s.src='https://translate.google.com/translate_a/element.js?cb=googleTranslateElementInit';document.head.appendChild(s);}
document.addEventListener('DOMContentLoaded',init);
</script></body></html>"""
    doc = doc.replace("__DATA__", data_json).replace("__BUILD__", datetime.datetime.now(datetime.timezone.utc).isoformat())
    with open("index.html","w") as f: f.write(doc)
    print("SPA dashboard (Drop 2 complete) written: " + str(len(picks_all)) + " picks; universe DE=" +
          str(len(uni_de.get('items',[]))) + " IN=" + str(len(uni_in.get('items',[]))))

if __name__ == "__main__":
    main()
