# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Malviyaarjun
# build_dashboard.py — Premium SPA: drill-down modals, language switcher, editorial copy, rich visuals.
# By Malviyaarjun. All times CET. Research/education. NOT financial advice.

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
    uni_de=load_json("analysed_all.json",{"items":[]}); uni_in=load_json("analysed_all_in.json",{"items":[]})
    today=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=1))).strftime("%Y-%m-%d")
    picks_all=collect(de.get("picks",[]),"€",False)+collect(ind.get("picks",[]),"₹",True)
    dh,dt=perf_stats("performance_log.csv"); ih,it=perf_stats("performance_log_in.csv")
    payload={"generatedDE":de.get("generated","—"),"generatedIN":ind.get("generated","—"),
        "dateDE":de.get("date"),"dateIN":ind.get("date"),"today":today,"eurinr":ind.get("eurinr","?"),
        "picks":picks_all,"uni":{"DE":uni_de.get("items",[]),"IN":uni_in.get("items",[])},
        "perf":{"deHit":dh,"deTot":dt,"inHit":ih,"inTot":it,
            "deSeries":perf_series("performance_log.csv"),"inSeries":perf_series("performance_log_in.csv")},
        "lessonsDE":lessons_text("strategy_memory.md"),"lessonsIN":lessons_text("strategy_memory_in.md"),
        "actionableToday":de.get("actionable_count",0)+ind.get("actionable_count",0)}
    data_json=json.dumps(payload)

    doc = r"""<!DOCTYPE html><html lang="en" data-theme="dark"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="Cache-Control" content="no-cache, must-revalidate"><meta name="last-build" content="__BUILD__">
<title>Swing Agent — Today's edge, distilled.</title><link rel="manifest" href="manifest.json"><link rel="icon" type="image/svg+xml" href="icon.svg"><link rel="apple-touch-icon" href="icon.svg"><meta name="theme-color" content="#0a0d14">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"></script>
<style>
:root{--bg:#0a0d14;--bg2:#0f1420;--glass:rgba(255,255,255,.05);--line:rgba(255,255,255,.09);--txt:#eaf0f7;--mut:#8b95a7;--acc:#6c8cff;--acc2:#9a6cff;--good:#39d98a;--bad:#ff5d73;--warn:#ffc86b}
[data-theme="light"]{--bg:#eef1f7;--bg2:#fff;--glass:rgba(0,0,0,.03);--line:rgba(0,0,0,.10);--txt:#141b2b;--mut:#5b6577;--acc:#2b5cff;--acc2:#7a3cff;--good:#12a150;--bad:#e03e52;--warn:#b7791f}
*{box-sizing:border-box}html,body{margin:0;height:100%}
body{font-family:-apple-system,'Segoe UI',Roboto,Arial,sans-serif;color:var(--txt);transition:.4s;position:relative;overflow-x:hidden;background:var(--bg)}
body::before{content:"";position:fixed;inset:-30%;z-index:-1;background:radial-gradient(600px 400px at 15% 10%,rgba(108,140,255,.16),transparent),radial-gradient(600px 400px at 85% 20%,rgba(154,108,255,.14),transparent),radial-gradient(700px 500px at 50% 100%,rgba(57,217,138,.08),transparent);animation:aurora 18s ease-in-out infinite alternate}
@keyframes aurora{0%{transform:translate(0,0) scale(1)}100%{transform:translate(-3%,2%) scale(1.06)}}
.num{font-variant-numeric:tabular-nums}.app{display:flex;min-height:100vh}
.side{width:238px;flex:none;background:linear-gradient(180deg,var(--bg2),transparent);border-right:1px solid var(--line);padding:18px 12px;position:sticky;top:0;height:100vh;transition:width .3s}
.side.collapsed{width:72px}.logo{display:flex;align-items:center;gap:10px;padding:6px 8px 16px;font-weight:800;font-size:18px}
.logo .dot{width:32px;height:32px;border-radius:10px;background:linear-gradient(135deg,var(--acc),var(--acc2));display:grid;place-items:center;box-shadow:0 6px 16px rgba(108,140,255,.4)}
.side.collapsed .logo span,.side.collapsed .nav b span,.side.collapsed .sideft{display:none}
.nav{display:flex;flex-direction:column;gap:4px;margin-top:6px}
.nav b{display:flex;align-items:center;gap:12px;padding:11px 12px;border-radius:12px;color:var(--mut);font-weight:600;font-size:14px;cursor:pointer;transition:.2s;border:1px solid transparent}
.nav b .ic{font-size:18px;width:22px;text-align:center}.nav b:hover{background:var(--glass);color:var(--txt);transform:translateX(2px)}
.nav b.active{background:linear-gradient(135deg,rgba(108,140,255,.22),rgba(154,108,255,.16));color:var(--txt);border-color:var(--line)}
.sideft{color:var(--mut);font-size:11px;padding:12px 10px;position:absolute;bottom:8px;width:214px}.sideft .by{color:var(--txt);font-weight:700;margin-bottom:4px;background:linear-gradient(135deg,var(--acc),var(--acc2));-webkit-background-clip:text;background-clip:text;color:transparent}
.collapseBtn{margin:8px;background:var(--glass);border:1px solid var(--line);color:var(--mut);border-radius:10px;padding:7px;cursor:pointer;width:calc(100% - 16px)}
.main{flex:1;min-width:0;display:flex;flex-direction:column}
.topbar{position:sticky;top:0;z-index:40;display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 20px;background:rgba(10,13,20,.55);backdrop-filter:blur(14px);border-bottom:1px solid var(--line)}
[data-theme="light"] .topbar{background:rgba(255,255,255,.6)}
.vt{font-size:18px;font-weight:800}.vt small{display:block;font-size:12px;font-weight:500;color:var(--mut)}
.ctrls button{background:var(--glass);color:var(--txt);border:1px solid var(--line);border-radius:12px;padding:8px 12px;font-size:14px;cursor:pointer}
.content{padding:22px;max-width:1120px;width:100%;margin:0 auto}
.view{display:none;animation:fade .5s}.view.active{display:block}@keyframes fade{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
.sectionhead{display:flex;align-items:center;gap:12px;margin:26px 0 6px}
.shicon{width:40px;height:40px;border-radius:12px;display:grid;place-items:center;font-size:20px;background:linear-gradient(135deg,rgba(108,140,255,.25),rgba(154,108,255,.18));border:1px solid var(--line)}
.sectionhead h2{margin:0;font-size:20px}.sectionhead p{margin:2px 0 0;color:var(--mut);font-size:13px}
.bento{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}
.glass{background:var(--glass);border:1px solid var(--line);border-radius:20px;padding:18px;backdrop-filter:blur(8px);transition:.25s}
.glass:hover{transform:translateY(-3px);box-shadow:0 16px 40px rgba(0,0,0,.32)}
.span2{grid-column:span 2}.span4{grid-column:span 4}
.hero{grid-column:span 2;grid-row:span 2;display:flex;flex-direction:column;justify-content:center;background:linear-gradient(135deg,rgba(108,140,255,.20),rgba(154,108,255,.12));position:relative;overflow:hidden;cursor:pointer}
.hero::after{content:"💡";position:absolute;right:-10px;bottom:-14px;font-size:120px;opacity:.08}
.hero .eyebrow{color:var(--acc);font-size:12px;font-weight:800;letter-spacing:1px;text-transform:uppercase}
.hero .hn{font-size:66px;font-weight:900;line-height:1;background:linear-gradient(135deg,var(--acc),var(--acc2));-webkit-background-clip:text;background-clip:text;color:transparent}
.hero .hl{color:var(--txt);opacity:.85;margin-top:8px;font-size:14px}
.tile{cursor:pointer;position:relative;overflow:hidden}.tile .ti{position:absolute;right:10px;top:10px;font-size:18px;opacity:.5}
.tile .k{font-size:30px;font-weight:800;color:var(--acc)}.tile .l{color:var(--mut);font-size:12px;margin-top:4px}
.tile .go{color:var(--acc);font-size:11px;margin-top:8px;font-weight:700}
.spot{border-left:3px solid var(--good)}
.toolbar{display:flex;gap:8px;flex-wrap:wrap;margin:6px 0 14px}
.chip{background:var(--glass);border:1px solid var(--line);color:var(--txt);border-radius:20px;padding:7px 14px;font-size:13px;cursor:pointer;transition:.2s}
.chip.active{background:linear-gradient(135deg,var(--acc),var(--acc2));color:#fff;border-color:transparent}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px}
.pcard{background:var(--glass);border:1px solid var(--line);border-radius:20px;padding:16px;backdrop-filter:blur(8px);transition:.25s}
.pcard:hover{transform:translateY(-4px);box-shadow:0 18px 40px rgba(0,0,0,.34)}
.pcard.act{border-top:3px solid var(--good)}.pcard.skp{border-top:3px solid var(--bad)}
.pchead{display:flex;justify-content:space-between;gap:10px;align-items:center}.pchead h3{margin:0;font-size:16px}.ticker{color:var(--acc);font-size:12px;font-weight:600}
.badge{display:inline-block;margin-top:6px;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:800}
.badge.go{background:rgba(57,217,138,.15);color:var(--good)}.badge.skip{background:rgba(255,93,115,.15);color:var(--bad)}
.plain{color:var(--txt);font-size:13px;opacity:.92}.spark{width:100%;height:40px;margin:6px 0}
.scaletrack{position:relative;height:12px;background:var(--line);border-radius:8px;margin:8px 0}
.zone{position:absolute;top:0;height:12px;background:rgba(108,140,255,.35);border:1px solid var(--acc);border-radius:4px}
.marker{position:absolute;top:-4px;width:2px;height:20px}.stopm{background:var(--bad)}.tgtm{background:var(--good)}
.pricem{width:10px;height:10px;top:1px;border-radius:50%;background:var(--txt);transform:translateX(-4px)}
.scalelegend{display:flex;justify-content:space-between;color:var(--mut);font-size:10px}
.rrbar{display:flex;height:10px;border-radius:6px;overflow:hidden;margin:8px 0}.rrrisk{background:var(--bad)}.rrreward{background:var(--good)}
.rrlabels{display:flex;justify-content:space-between;font-size:11px;margin-bottom:3px}.weakrr{color:var(--warn);font-size:11px;margin:2px 0 0}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:10px 0}
.kv{background:var(--bg2);border:1px solid var(--line);border-radius:10px;padding:8px;font-size:12px}.kv span{color:var(--mut);font-size:11px;display:block}.kv b{font-size:14px}
.tip{border-bottom:1px dotted var(--acc);cursor:help;position:relative}
.tip .tt{visibility:hidden;opacity:0;transition:.15s;position:absolute;bottom:130%;left:0;z-index:9;background:#0a0f18;color:#fff;border:1px solid var(--line);border-radius:8px;padding:8px;width:200px;font-size:11px}
.tip:hover .tt{visibility:visible;opacity:1}
.sellrule{background:var(--bg2);border:1px dashed var(--line);border-radius:10px;padding:9px;font-size:12px;margin-top:6px}
.src{color:var(--mut);font-size:10px;margin-top:6px}
.ring{width:74px;height:74px;flex:none;position:relative}.ring .lbl{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center}
.ring .lbl .n{font-size:20px;font-weight:800}.ring .lbl .c{font-size:8px;color:var(--mut);text-transform:uppercase;letter-spacing:.5px}
.alert{background:rgba(255,93,115,.12);border:1px solid var(--bad);color:var(--bad);padding:11px 14px;border-radius:12px;margin:0 0 12px;font-size:13px}
.disc{background:rgba(255,200,107,.10);border:1px solid var(--warn);color:var(--warn);padding:11px 14px;border-radius:12px;margin:12px 0;font-size:12px}
.soon{color:var(--mut);text-align:center;padding:50px 20px}
table.tbl{width:100%;border-collapse:collapse;font-size:13px;margin-top:10px}table.tbl th,table.tbl td{text-align:left;padding:8px;border-bottom:1px solid var(--line)}
.pill{padding:2px 8px;border-radius:12px;font-size:11px;font-weight:700}.pill.hit{background:rgba(57,217,138,.15);color:var(--good)}.pill.miss{background:rgba(255,93,115,.15);color:var(--bad)}
.lessons{white-space:pre-wrap;font-family:inherit;color:var(--txt);font-size:13px;margin:0}
.tag2{padding:2px 8px;border-radius:8px;font-size:11px;font-weight:700}.tag2.h{background:rgba(57,217,138,.15);color:var(--good)}.tag2.m{background:rgba(255,200,107,.15);color:var(--warn)}.tag2.l{background:rgba(255,93,115,.15);color:var(--bad)}
/* modal */
.overlay{position:fixed;inset:0;z-index:100;background:rgba(4,7,13,.6);backdrop-filter:blur(6px);display:none;align-items:center;justify-content:center;padding:20px;animation:fade .25s}
.overlay.show{display:flex}
.modal{background:var(--bg2);border:1px solid var(--line);border-radius:22px;max-width:560px;width:100%;max-height:82vh;overflow:auto;padding:22px;box-shadow:0 30px 80px rgba(0,0,0,.6);animation:pop .3s}
@keyframes pop{from{opacity:0;transform:scale(.94) translateY(10px)}to{opacity:1;transform:none}}
.modal .mh{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}.modal .mh h3{margin:0;font-size:20px}
.modal .x{cursor:pointer;border:1px solid var(--line);background:var(--glass);border-radius:10px;width:34px;height:34px;display:grid;place-items:center;font-size:16px}
.mrow{display:flex;align-items:center;gap:12px;padding:12px;border:1px solid var(--line);border-radius:14px;margin:10px 0;background:var(--glass)}
.mrow .mmeta{flex:1}.mrow h4{margin:0;font-size:15px}.mrow .sub{color:var(--mut);font-size:12px}
.mbtn{display:inline-flex;align-items:center;gap:8px;margin-top:8px;background:linear-gradient(135deg,var(--acc),var(--acc2));color:#fff;border:none;border-radius:12px;padding:11px 16px;font-size:14px;font-weight:700;cursor:pointer;width:100%;justify-content:center}
/* language switcher */
.fab{position:fixed;bottom:18px;right:18px;z-index:80;width:52px;height:52px;border-radius:50%;background:linear-gradient(135deg,var(--acc),var(--acc2));color:#fff;border:none;font-size:22px;cursor:pointer;box-shadow:0 10px 26px rgba(108,140,255,.5);transition:transform .2s}
.fab:hover{transform:scale(1.08) rotate(8deg)}
.langpop{position:fixed;bottom:80px;right:18px;z-index:81;background:var(--bg2);border:1px solid var(--line);border-radius:16px;padding:12px;width:220px;box-shadow:0 20px 50px rgba(0,0,0,.5);display:none}
.langpop.show{display:block;animation:pop .25s}.langpop .lh{font-size:11px;color:var(--mut);margin-bottom:8px;text-transform:uppercase;letter-spacing:.5px}
.langgrid{display:grid;grid-template-columns:1fr 1fr;gap:6px}
.langgrid b{display:flex;align-items:center;gap:6px;padding:8px;border:1px solid var(--line);border-radius:10px;font-size:13px;font-weight:600;cursor:pointer;transition:.15s}
.langgrid b:hover{background:var(--glass);border-color:var(--acc)}
#gt{position:absolute;left:-9999px}.goog-te-banner-frame{display:none!important}body{top:0!important}
.bottomnav{display:none}
@media(max-width:820px){.side{display:none}.cards{grid-template-columns:1fr}.bento{grid-template-columns:repeat(2,1fr)}.hero{grid-column:span 2}.span2{grid-column:span 2}.span4{grid-column:span 2}.content{padding:14px 12px 90px}
.fab{bottom:78px}.langpop{bottom:140px}
.bottomnav{display:flex;position:fixed;bottom:0;left:0;right:0;z-index:60;background:rgba(10,13,20,.92);backdrop-filter:blur(12px);border-top:1px solid var(--line);justify-content:space-around;padding:8px 4px}
[data-theme="light"] .bottomnav{background:rgba(255,255,255,.92)}
.bottomnav b{display:flex;flex-direction:column;align-items:center;gap:2px;color:var(--mut);font-size:10px;font-weight:600;cursor:pointer;padding:4px 8px;border-radius:10px}.bottomnav b.active{color:var(--acc)}.bottomnav b .ic{font-size:20px}}
.pactions{display:flex;gap:6px;margin-top:10px;flex-wrap:wrap}
.pactions button{flex:1;min-width:86px;background:var(--bg2);border:1px solid var(--line);color:var(--txt);border-radius:10px;padding:8px 6px;font-size:11px;font-weight:700;cursor:pointer;transition:.18s}
.pactions button:hover{border-color:var(--acc);color:var(--acc);transform:translateY(-2px)}
#toast{position:fixed;left:50%;bottom:28px;transform:translate(-50%,90px);z-index:200;background:var(--bg2);border:1px solid var(--acc);color:var(--txt);padding:12px 18px;border-radius:14px;font-size:13px;font-weight:600;box-shadow:0 16px 40px rgba(0,0,0,.5);opacity:0;transition:.35s;pointer-events:none}
#toast.show{transform:translate(-50%,0);opacity:1}
.sizerow{display:flex;gap:8px;align-items:center;margin:8px 0}
.sizerow label{flex:1;font-size:12px;color:var(--mut)}
.sizerow input{width:130px;background:var(--bg);border:1px solid var(--line);color:var(--txt);border-radius:10px;padding:8px;font-size:13px}
.sizeout{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px}
.sizeout div{background:var(--glass);border:1px solid var(--line);border-radius:12px;padding:10px}
.sizeout span{display:block;color:var(--mut);font-size:11px}.sizeout b{font-size:15px}
kbd{background:var(--bg2);border:1px solid var(--line);border-radius:6px;padding:2px 7px;font-size:11px}
@media print{body::before,.side,.topbar,.bottomnav,.fab,.langpop,.toolbar,#toast,.pactions,#staleBox,.sectionhead,.disc{display:none!important}
body{background:#fff!important;color:#000!important}.view{display:none!important}.view.printing{display:block!important}
.pcard{display:none!important}.pcard.printme{display:block!important;border:1px solid #999!important;box-shadow:none!important;break-inside:avoid}
.glass{box-shadow:none!important;border-color:#ccc!important}}
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
    <div class="sideft"><div class="by">Crafted by Malviyaarjun</div><span translate="no">Research &amp; education — not financial advice. Data ~15-min delayed.</span></div>
  </aside>
  <div class="main">
    <div class="topbar"><div class="vt" id="viewTitle">Overview<small id="viewSub">Today's edge, distilled.</small></div>
    <div class="ctrls"><button onclick="exportCSV()" title="Export today's picks (E)">📥</button><button onclick="keyHelp()" title="Keyboard shortcuts (?)">⌨️</button><button id="themeBtn" onclick="toggleTheme()">☀️</button></div>
    </div>
    <div class="content"><div id="staleBox"></div>
      <section class="view active" id="v-overview">
        <div class="disc" translate="no"><b>Please read:</b> Research &amp; education, <b>not financial advice</b>. Estimates from ~15-min delayed data (prior close). You place &amp; own every trade.</div>
        <div class="bento">
          <div class="glass hero tile" onclick="openModal('actionable')"><div class="eyebrow">Today · Both markets</div><div class="hn num" id="heroNum">0</div><div class="hl">Actionable ideas, already filtered for trading costs. <b style="color:var(--acc)">Tap to preview →</b></div></div>
          <div class="glass tile" onclick="openModal('analysed')"><span class="ti">🔍</span><div class="k num" id="kAnalysed">0</div><div class="l">Stocks scanned today</div><div class="go">See the field →</div></div>
          <div class="glass tile" onclick="openModal('accuracy')"><span class="ti">🎯</span><div class="k num" id="kAccuracy">—</div><div class="l">Target accuracy, all-time</div><div class="go">How we score →</div></div>
          <div class="glass tile" onclick="openModal('de')"><span class="ti">🇩🇪</span><div class="k num" id="kDE">0</div><div class="l">German ideas</div><div class="go">Preview →</div></div>
          <div class="glass tile" onclick="openModal('in')"><span class="ti">🇮🇳</span><div class="k num" id="kIN">0</div><div class="l">Indian ideas</div><div class="go">Preview →</div></div>
          <div class="glass span2 spot" id="spotlight"></div>
          <div class="glass span2"><canvas id="miniAcc" height="120"></canvas></div>
        </div>
        <div class="sectionhead"><div class="shicon">🧭</div><div><h2>New here? Start in ten seconds.</h2><p>No jargon, no pressure — just the essentials.</p></div></div>
        <div class="glass"><ol style="margin:0 0 0 18px;font-size:14px;line-height:1.9">
          <li>Green <b>✓ ACTIONABLE</b> means worth a look. <b>WATCH / SKIP</b> means sit this one out.</li>
          <li>The <b>confidence ring</b> and <b>risk-vs-reward</b> bar tell the story at a glance.</li>
          <li>The <b>price scale</b> maps your safety net, entry, and goal on one line.</li>
          <li>We're ~15 minutes behind live — <b>always confirm the price in your broker</b> before acting.</li>
        </ol></div>
      </section>
      <section class="view" id="v-ideas">
        <div class="sectionhead"><div class="shicon">💡</div><div><h2>Opportunities, hand-picked.</h2><p>A tight shortlist — quality over quantity, costs already accounted for.</p></div></div>
        <div class="toolbar"><span class="chip active" data-f="all" onclick="setFilter(this)">All</span>
          <span class="chip" data-f="actionable" onclick="setFilter(this)">✓ Actionable</span>
          <span class="chip" data-f="de" onclick="setFilter(this)">🇩🇪 Germany</span>
          <span class="chip" data-f="in" onclick="setFilter(this)">🇮🇳 India</span>
          <span class="chip" data-f="high" onclick="setFilter(this)">High confidence</span></div>
        <div class="cards" id="cards"></div>
      </section>
      <section class="view" id="v-analytics">
        <div class="sectionhead"><div class="shicon">📊</div><div><h2>The numbers behind the calls.</h2><p>Honest scorekeeping — this tracks estimate accuracy, not profit.</p></div></div>
        <div class="bento">
          <div class="glass span2"><h3 style="margin:0 0 8px">Accuracy, building over time</h3><canvas id="accChart" height="150"></canvas></div>
          <div class="glass"><h3 style="margin:0 0 8px">🇩🇪 Germany hit-rate</h3><canvas id="deDonut" height="150"></canvas></div>
          <div class="glass"><h3 style="margin:0 0 8px">🇮🇳 India hit-rate</h3><canvas id="inDonut" height="150"></canvas></div>
          <div class="glass span4"><h3 style="margin:0 0 8px">Aim vs reality</h3><canvas id="devChart" height="140"></canvas>
            <p class="plain" style="color:var(--mut);margin-top:8px">Above the line, we hit the target; below, we fell short. Over time this reveals whether our aim runs hot or cold.</p></div>
        </div>
      </section>
      <section class="view" id="v-watchlist">
        <div class="sectionhead"><div class="shicon">📋</div><div><h2>Every stock we watched.</h2><p>The full field the engine scanned this morning — not just the finalists.</p></div></div>
        <div class="toolbar"><span class="chip active" data-w="all" onclick="setWFilter(this)">All markets</span>
          <span class="chip" data-w="DE" onclick="setWFilter(this)">🇩🇪 Germany</span>
          <span class="chip" data-w="IN" onclick="setWFilter(this)">🇮🇳 India</span></div>
        <div class="glass"><div id="uniTable"></div></div>
      </section>
      <section class="view" id="v-learnings">
        <div class="sectionhead"><div class="shicon">🧠</div><div><h2>How the system gets smarter.</h2><p>Every miss becomes a lesson. Here's the running memory.</p></div></div>
        <div class="glass"><h3 style="margin-top:0">🇩🇪 Germany — strategy memory</h3><pre class="lessons" id="lessonsDE"></pre></div>
        <div class="glass"><h3 style="margin-top:0">🇮🇳 India — strategy memory</h3><pre class="lessons" id="lessonsIN"></pre></div>
      </section>
      <section class="view" id="v-about">
        <div class="sectionhead"><div class="shicon">ℹ️</div><div><h2>Built on transparency.</h2><p>No black boxes. Here's exactly how it thinks.</p></div></div>
        <div class="glass"><h3 style="margin-top:0">The method, in plain English</h3>
          <p class="plain">Every morning the engine assembles a fresh field of liquid, affordable movers, then scores each on trend, momentum, volatility and liquidity. It sets a <b>history-based, reachable target</b>, a protective stop, and a cost-aware “worthwhile” test — Germany must clear ~3% (fees ~1%), India ~1.5% (costs ~0.35%). After the close, it grades itself and writes a lesson that sharpens tomorrow.</p></div>
        <div class="glass"><h3 style="margin-top:0">Where the data comes from</h3>
          <p class="plain">Prices via Yahoo Finance, <b>~15-min delayed, based on the prior close</b> — reliability medium-high. Always confirm live in your broker. No rumor or forum sources, ever.</p></div>
        <div class="glass"><h3 style="margin-top:0">The maker</h3><p class="plain">Designed &amp; engineered by <b>Malviyaarjun</b> — powered entirely by free, open tools.</p></div>
        <div class="disc" translate="no"><b>Risk &amp; responsibility:</b> Research/education, <b>NOT financial advice</b>. Markets are risky; you can lose money. India costs are estimates — confirm on your contract note. You are responsible for every trade and for compliance (BaFin/MiFID in the EU; SEBI/STT in India).</div>
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
<div class="overlay" id="overlay" onclick="if(event.target===this)closeModal()"><div class="modal" id="modalBody"></div></div>
<div id="toast"></div>
<button class="fab" id="langfab" onclick="toggleLang()" title="Language">🌐</button>
<div class="langpop" id="langpop"><div class="lh" translate="no">Choose language</div><div class="langgrid" id="langgrid"></div></div>
<div id="gt"></div>
<script>
const DATA=__DATA__;const TITLES={overview:['Overview',"Today's edge, distilled."],ideas:["Today's Ideas","Opportunities, hand-picked."],analytics:['Analytics','The numbers behind the calls.'],watchlist:['Watchlist','Every stock we watched.'],learnings:['Learnings','How the system gets smarter.'],about:['About','Built on transparency.']};
let _charts={};window._filter='all';window._wfilter='all';
function fmt(n){return (typeof n==='number'?n:parseFloat(n)||0).toLocaleString('en-US');}
function loadPrefs(){document.documentElement.setAttribute('data-theme',localStorage.getItem('sa_theme')||'dark');window._filter=localStorage.getItem('sa_filter')||'all';if(localStorage.getItem('sa_side')==='1')document.getElementById('side').classList.add('collapsed');}
function toggleTheme(){const c=document.documentElement.getAttribute('data-theme'),n=c==='light'?'dark':'light';document.documentElement.setAttribute('data-theme',n);localStorage.setItem('sa_theme',n);document.getElementById('themeBtn').textContent=n==='light'?'🌙':'☀️';}
function toggleSide(){document.getElementById('side').classList.toggle('collapsed');localStorage.setItem('sa_side',document.getElementById('side').classList.contains('collapsed')?'1':'0');}
function nav(v){document.querySelectorAll('.view').forEach(s=>s.classList.remove('active'));document.getElementById('v-'+v).classList.add('active');document.querySelectorAll('#nav b,#bnav b').forEach(b=>b.classList.toggle('active',b.dataset.v===v));document.getElementById('viewTitle').childNodes[0].nodeValue=TITLES[v][0];document.getElementById('viewSub').textContent=TITLES[v][1];window.scrollTo({top:0,behavior:'smooth'});if(v==='analytics')buildAnalytics();if(v==='watchlist')buildWatch();}
function ring(s){const c=s>=72?'var(--good)':s>=60?'var(--warn)':'var(--bad)',C=2*Math.PI*30,off=C*(1-Math.max(0,Math.min(100,s))/100);return `<div class="ring"><svg width="74" height="74" viewBox="0 0 74 74"><circle cx="37" cy="37" r="30" fill="none" stroke="var(--line)" stroke-width="7"/><circle cx="37" cy="37" r="30" fill="none" stroke="${c}" stroke-width="7" stroke-linecap="round" stroke-dasharray="${C.toFixed(1)}" stroke-dashoffset="${off.toFixed(1)}" transform="rotate(-90 37 37)"/></svg><div class="lbl"><div class="n" style="color:${c}">${Math.round(s)}</div><div class="c">conf</div></div></div>`;}
function spark(a){if(!a||a.length<2)return'';const w=300,h=40,mn=Math.min(...a),mx=Math.max(...a),sp=(mx-mn)||1,pts=a.map((v,i)=>`${(i/(a.length-1)*w).toFixed(1)},${(h-((v-mn)/sp)*h).toFixed(1)}`).join(' '),up=a[a.length-1]>=a[0];return `<svg class="spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none"><polyline points="${pts}" fill="none" stroke="${up?'var(--good)':'var(--bad)'}" stroke-width="2"/></svg>`;}
function scale(p){const lo=Math.min(p.stop,p.buy_low),hi=Math.max(p.target,p.buy_high),sp=(hi-lo)||1,P=v=>((v-lo)/sp*100).toFixed(1);return `<div class="scaletrack"><div class="marker stopm" style="left:${P(p.stop)}%"></div><div class="zone" style="left:${P(p.buy_low)}%;width:${Math.max(P(p.buy_high)-P(p.buy_low),2)}%"></div><div class="marker pricem" style="left:${P(p.price)}%"></div><div class="marker tgtm" style="left:${P(p.target)}%"></div></div><div class="scalelegend"><span>🛑 Stop</span><span>🟦 Buy</span><span>● Now</span><span>🎯 Target</span></div>`;}
function rr(p){const rk=Math.max(p.price-p.stop,1e-4),rw=Math.max(p.target-p.price,1e-4),t=rk+rw,W=Math.round(100*rw/t),R=100-W,ra=(rw/rk).toFixed(1);const weak=(rw/rk)<1?'<div class="weakrr">⚠ Reward is smaller than risk (below 1:1) — weaker setup.</div>':'';return `<div class="rrlabels"><span style="color:var(--bad)">Risk</span><span style="color:var(--good)">Reward (${ra}:1)</span></div><div class="rrbar"><div class="rrrisk" style="width:${R}%"></div><div class="rrreward" style="width:${W}%"></div></div>${weak}`;}
function tip(t,e){return `<span class="tip" translate="no">${t}<span class="tt">${e}</span></span>`;}
function reason(p){const tr=p.sma5>p.sma20?'in a short-term uptrend':'not in a clear uptrend',m=(p.rsi>=45&&p.rsi<=68)?'with balanced momentum':(p.rsi>68?'looking overbought':'with weak momentum'),v=p.worthwhile?'Worth considering.':'Likely move too small to beat costs — probably skip.';return `${p.name} is ${tr} ${m}. Realistic target ~${p.cur}${fmt(p.target)} (about ${p.tgt_move_pct}% above last close ${p.cur}${fmt(p.price)}). ${v}`;}
function card(p){const tag=p.actionable?'<span class="badge go">✓ ACTIONABLE</span>':'<span class="badge skip">✕ WATCH / SKIP</span>',eur=p.india&&p.cost_eur!=null?` <span style="color:var(--mut)">(~€${fmt(p.cost_eur)})</span>`:'';return `<div class="pcard ${p.actionable?'act':'skp'}" data-tk="${p.ticker}"><div class="pchead"><div><h3>${p.name} <span class="ticker" translate="no">${p.ticker}</span></h3>${tag}</div>${ring(p.score)}</div><p class="plain">${reason(p)}</p>${spark(p.spark)}${scale(p)}${rr(p)}<div class="grid2"><div class="kv"><span>${tip('Buy zone','Enter only if live price is here.')}</span><b class="num">${p.cur}${fmt(p.buy_low)}–${p.cur}${fmt(p.buy_high)}</b></div><div class="kv"><span>${tip('Target','Realistic sell aim, from history. Estimate.')}</span><b class="num">${p.cur}${fmt(p.target)}</b></div><div class="kv"><span>${tip('Stop-loss','Safety exit. Set right after buying.')}</span><b class="num">${p.cur}${fmt(p.stop)}</b></div><div class="kv"><span>${tip('Position','Whole shares fitting budget.')}</span><b class="num">${p.shares} sh ≈ ${p.cur}${fmt(p.cost)}${eur}</b></div></div><div class="sellrule">🕒 <b>Sell:</b> aim for target (before mid-session). Else exit by Day 3 (max 5). Stop-loss protects you.</div><div class="pactions"><button onclick="copyTicket('${p.ticker}')">📋 Copy ticket</button><button onclick="openSizer('${p.ticker}')">🧮 Size it</button><button onclick="printCard('${p.ticker}')">🖨️ Print</button></div><div class="src">Yahoo Finance (~15-min delayed) · confirm live price in broker.</div></div>`;}
/* ---- modal ---- */
function miniRow(p){return `<div class="mrow">${ring(p.score)}<div class="mmeta"><h4>${p.name} <span class="ticker" translate="no">${p.ticker}</span> ${p.india?'🇮🇳':'🇩🇪'}</h4><div class="sub">${p.actionable?'✓ Actionable':'Watch/Skip'} · Confidence ${p.conf} · Target ${p.cur}${fmt(p.target)} (~${p.tgt_move_pct}%) · Stop ${p.cur}${fmt(p.stop)}</div></div></div>`;}
function openModal(kind){const o=document.getElementById('overlay'),b=document.getElementById('modalBody');let title='',body='',go='ideas',btn='View full details →';
  if(kind==='actionable'){const a=DATA.picks.filter(p=>p.actionable).sort((x,y)=>y.score-x.score);title='🎯 Actionable ideas today';body=a.length?a.map(miniRow).join(''):'<p class="plain">No forced trades today. Patience is a position.</p>';}
  else if(kind==='analysed'){title='🔍 The field we scanned';const de=DATA.picks.filter(p=>!p.india).length,inn=DATA.picks.filter(p=>p.india).length;body=`<p class="plain">Today the engine surfaced <b>${DATA.picks.length}</b> finalists — <b>${de}</b> German 🇩🇪 and <b>${inn}</b> Indian 🇮🇳 — from a much larger daily field of movers, filtered for liquidity, affordability and trading costs.</p>`+DATA.picks.sort((x,y)=>y.score-x.score).map(miniRow).join('');go='watchlist';btn='See the full field →';}
  else if(kind==='accuracy'){const ah=DATA.perf.deHit+DATA.perf.inHit,at=DATA.perf.deTot+DATA.perf.inTot;title='🎯 How accuracy works';body=`<p class="plain">Accuracy = how often a stock actually reached our estimated target. So far: <b>${ah}/${at}</b>${at?' ('+Math.round(100*ah/at)+'%)':''}.</p><p class="plain" style="color:var(--mut)">Early numbers swing a lot and improve as the system recalibrates. Importantly, this measures <b>estimate accuracy — not your profit</b>.</p>`;go='analytics';btn='Open Analytics →';}
  else if(kind==='de'||kind==='in'){const isIn=kind==='in';const a=DATA.picks.filter(p=>p.india===isIn).sort((x,y)=>y.score-x.score);title=(isIn?'🇮🇳 Indian':'🇩🇪 German')+' ideas today';body=a.length?a.map(miniRow).join(''):'<p class="plain">No ideas in this market today. Cash is a valid position.</p>';window._pref=kind;}
  b.innerHTML=`<div class="mh"><h3>${title}</h3><div class="x" onclick="closeModal()">✕</div></div>${body}<button class="mbtn" onclick="closeModal();nav('${go}')">${btn}</button>`;o.classList.add('show');}
function closeModal(){document.getElementById('overlay').classList.remove('show');}
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeModal();});
/* ---- filters ---- */
function setFilter(el){document.querySelectorAll('#v-ideas .chip').forEach(c=>c.classList.remove('active'));el.classList.add('active');window._filter=el.dataset.f;localStorage.setItem('sa_filter',window._filter);applyFilters();}
function applyFilters(){let a=[...DATA.picks].sort((x,y)=>y.score-x.score);const f=window._filter;a=a.filter(p=>{if(f==='actionable'&&!p.actionable)return false;if(f==='de'&&p.india)return false;if(f==='in'&&!p.india)return false;if(f==='high'&&p.conf!=='High')return false;return true;});document.getElementById('cards').innerHTML=a.length?a.map(card).join(''):'<div class="pcard skp"><p class="plain">No forced trades today. Patience is a position.</p></div>';}
function setWFilter(el){document.querySelectorAll('#v-watchlist .chip').forEach(c=>c.classList.remove('active'));el.classList.add('active');window._wfilter=el.dataset.w;buildWatch();}
function buildWatch(){let items=[];if(window._wfilter!=='IN')items=items.concat(DATA.uni.DE.map(x=>({...x,m:'🇩🇪'})));if(window._wfilter!=='DE')items=items.concat(DATA.uni.IN.map(x=>({...x,m:'🇮🇳'})));items.sort((a,b)=>b.score-a.score);if(!items.length){document.getElementById('uniTable').innerHTML='<p class="soon">No field data yet — run the morning scan once.</p>';return;}const rows=items.map(x=>{const cl=x.conf==='High'?'h':x.conf==='Med'?'m':'l';return `<tr><td>${x.m}</td><td><b>${x.name}</b><br><span class="ticker" translate="no">${x.ticker}</span></td><td class="num">${fmt(x.price)}</td><td><span class="tag2 ${cl}">${x.conf} ${x.score}</span></td><td class="num">${x.atr_pct}%</td><td class="num">${x.rsi}</td><td>${x.worthwhile?'<span class="pill hit">✓</span>':'<span class="pill miss">skip</span>'}</td><td style="width:120px">${spark(x.spark)}</td></tr>`;}).join('');document.getElementById('uniTable').innerHTML=`<table class="tbl"><thead><tr><th></th><th>Stock</th><th>Price</th><th>Confidence</th><th>Move(ATR)</th><th>RSI</th><th>Tradable</th><th>30-day</th></tr></thead><tbody>${rows}</tbody></table>`;}
function countUp(el,to){let n=0;const st=Math.max(1,Math.ceil(to/24)),t=setInterval(()=>{n+=st;if(n>=to){n=to;clearInterval(t);}el.textContent=n;},22);}
function spotlight(){const acts=DATA.picks.filter(p=>p.actionable).sort((a,b)=>b.score-a.score),el=document.getElementById('spotlight');if(!acts.length){el.innerHTML='<b>🌙 Idea of the day</b><p class="plain" style="margin:8px 0 0">No forced trades today. Patience is a position.</p>';return;}const p=acts[0];el.innerHTML=`<b>🌟 Idea of the day</b><h3 style="margin:8px 0 2px">${p.name} <span class="ticker" translate="no">${p.ticker}</span></h3><p class="plain" style="margin:0">Confidence ${p.conf} · target ${p.cur}${fmt(p.target)} (~${p.tgt_move_pct}%)</p><p class="plain" style="margin:6px 0 0;color:var(--acc);cursor:pointer" onclick="nav('ideas')">Open the full breakdown →</p>`;}
function mkLine(id,L,V){const c=document.getElementById(id);if(!c)return;if(!L.length){c.replaceWith(Object.assign(document.createElement('div'),{className:'soon',textContent:'Chart appears after first reviews.'}));return;}_charts[id]&&_charts[id].destroy();_charts[id]=new Chart(c,{type:'line',data:{labels:L,datasets:[{label:'Cumulative accuracy %',data:V,borderColor:'#6c8cff',backgroundColor:'rgba(108,140,255,.15)',fill:true,tension:.3,pointRadius:2}]},options:{plugins:{legend:{labels:{color:getComputedStyle(document.body).color}}},scales:{y:{min:0,max:100,ticks:{color:'#8b95a7'}},x:{ticks:{color:'#8b95a7'}}}}});}
function mkDonut(id,hit,tot){const c=document.getElementById(id);if(!c)return;_charts[id]&&_charts[id].destroy();_charts[id]=new Chart(c,{type:'doughnut',data:{labels:['Hit','Miss'],datasets:[{data:[hit,Math.max(tot-hit,0)],backgroundColor:['#39d98a','#ff5d73'],borderWidth:0}]},options:{cutout:'68%',plugins:{legend:{labels:{color:getComputedStyle(document.body).color}}}}});}
function buildAnalytics(){const all=[...DATA.perf.deSeries,...DATA.perf.inSeries].sort((a,b)=>a.date.localeCompare(b.date));const L=[],V=[];let h=0,t=0;all.forEach(r=>{t++;h+=r.hit;L.push(r.date);V.push(Math.round(100*h/t));});mkLine('accChart',L,V);mkDonut('deDonut',DATA.perf.deHit,DATA.perf.deTot);mkDonut('inDonut',DATA.perf.inHit,DATA.perf.inTot);const dev=all.slice(-14),c=document.getElementById('devChart');if(!c)return;if(!dev.length){c.replaceWith(Object.assign(document.createElement('div'),{className:'soon',textContent:'Chart appears after first reviews.'}));return;}_charts['dev']&&_charts['dev'].destroy();_charts['dev']=new Chart(c,{type:'bar',data:{labels:dev.map(d=>d.ticker),datasets:[{label:'Actual − Predicted %',data:dev.map(d=>d.pred?+(100*(d.actual-d.pred)/d.pred).toFixed(2):0),backgroundColor:dev.map(d=>d.hit?'#39d98a':'#ff5d73')}]},options:{plugins:{legend:{labels:{color:getComputedStyle(document.body).color}}},scales:{y:{ticks:{color:'#8b95a7'}},x:{ticks:{color:'#8b95a7'}}}}});}
function miniAcc(){const all=[...DATA.perf.deSeries,...DATA.perf.inSeries].sort((a,b)=>a.date.localeCompare(b.date)),L=[],V=[];let h=0,t=0;all.forEach(r=>{t++;h+=r.hit;L.push(r.date);V.push(Math.round(100*h/t));});mkLine('miniAcc',L,V);}
function stale(){const w=[];if(DATA.dateDE!==DATA.today&&DATA.dateDE!=='-')w.push('Germany ('+DATA.dateDE+')');if(DATA.dateIN!==DATA.today&&DATA.dateIN!=='-')w.push('India ('+DATA.dateIN+')');if(w.length)document.getElementById('staleBox').innerHTML='<div class="alert">⚠️ Some data isn’t from today ('+DATA.today+' CET): '+w.join(', ')+'. Run the scan to refresh.</div>';}
/* ---- language ---- */
const LANGS=[['en','🇬🇧 English'],['de','🇩🇪 Deutsch'],['hi','🇮🇳 हिन्दी'],['fr','🇫🇷 Français'],['es','🇪🇸 Español'],['it','🇮🇹 Italiano'],['pt','🇵🇹 Português'],['zh-CN','🇨🇳 中文'],['ar','🇸🇦 العربية'],['ru','🇷🇺 Русский']];
function toggleLang(){document.getElementById('langpop').classList.toggle('show');}
function setLang(code){const sel=document.querySelector('#gt select');if(sel){sel.value=code;sel.dispatchEvent(new Event('change'));}document.getElementById('langpop').classList.remove('show');}
function buildLangGrid(){document.getElementById('langgrid').innerHTML=LANGS.map(l=>`<b onclick="setLang('${l[0]}')" translate="no">${l[1]}</b>`).join('');}
document.addEventListener('click',e=>{const lp=document.getElementById('langpop'),fb=document.getElementById('langfab');if(lp.classList.contains('show')&&!lp.contains(e.target)&&e.target!==fb)lp.classList.remove('show');});
function googleTranslateElementInit(){new google.translate.TranslateElement({pageLanguage:'en',includedLanguages:'en,de,hi,fr,es,zh-CN,ar,ru,it,pt',autoDisplay:false},'gt');}
/* ===== original feature layer, written for this project (MIT) ===== */
function toast(m){const t=document.getElementById('toast');t.textContent=m;t.classList.add('show');clearTimeout(window._tt);window._tt=setTimeout(()=>t.classList.remove('show'),2600);}
function pickByTicker(tk){return DATA.picks.find(p=>p.ticker===tk);}
function ticketText(p){return ['SWING AGENT — TRADE TICKET (research only, NOT financial advice)','Stock: '+p.name+' ('+p.ticker+') — '+(p.india?'NSE / India':'XETRA / Germany'),'Status: '+(p.actionable?'ACTIONABLE':'WATCH-SKIP')+' | Confidence: '+p.conf+' ('+p.score+'/100)','Buy zone: '+p.cur+fmt(p.buy_low)+' - '+p.cur+fmt(p.buy_high),'Target: '+p.cur+fmt(p.target)+' (~'+p.tgt_move_pct+'%)','Stop-loss: '+p.cur+fmt(p.stop),'Suggested size: '+p.shares+' whole shares ~ '+p.cur+fmt(p.cost),'Sell rule: take target before mid-session; else exit by Day 3 (max 5 days).','Data: ~15-min delayed, prior close. Verify the live price in your broker.'].join('\n');}
function fallbackCopy(t){const a=document.createElement('textarea');a.value=t;document.body.appendChild(a);a.select();try{document.execCommand('copy');toast('📋 Trade ticket copied');}catch(e){toast('Copy not supported here');}document.body.removeChild(a);}
function copyTicket(tk){const p=pickByTicker(tk);if(!p)return;const t=ticketText(p);if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(t).then(()=>toast('📋 Trade ticket copied')).catch(()=>fallbackCopy(t));}else{fallbackCopy(t);}}
function printCard(tk){nav('ideas');setTimeout(function(){document.querySelectorAll('.pcard').forEach(c=>c.classList.remove('printme'));const el=document.querySelector('.pcard[data-tk="'+tk+'"]');if(el)el.classList.add('printme');const v=document.getElementById('v-ideas');v.classList.add('printing');window.print();setTimeout(function(){v.classList.remove('printing');if(el)el.classList.remove('printme');},500);},150);}
function openSizer(tk){const p=pickByTicker(tk);if(!p)return;const key=p.india?'in':'de';const cap=localStorage.getItem('sa_cap_'+key)||(p.india?20000:200);const fee=localStorage.getItem('sa_fee_'+key)||(p.india?0.35:1);document.getElementById('modalBody').innerHTML='<div class="mh"><h3>🧮 Size it your way</h3><div class="x" onclick="closeModal()">✕</div></div><p class="plain" style="color:var(--mut)">Enter your own capital and cost. Everything recalculates instantly — including what you actually risk if the stop is hit.</p><div class="sizerow"><label>Capital available ('+p.cur+')</label><input id="szCap" type="number" value="'+cap+'" oninput="calcSizer(\''+tk+'\')"></div><div class="sizerow"><label>'+(p.india?'Round-trip cost (%)':'Fee per order ('+p.cur+')')+'</label><input id="szFee" type="number" step="0.01" value="'+fee+'" oninput="calcSizer(\''+tk+'\')"></div><div class="sizeout" id="szOut"></div><button class="mbtn" onclick="closeModal()">Done</button>';document.getElementById('overlay').classList.add('show');calcSizer(tk);}
function calcSizer(tk){const p=pickByTicker(tk);if(!p)return;const key=p.india?'in':'de';const cap=parseFloat(document.getElementById('szCap').value)||0;const fee=parseFloat(document.getElementById('szFee').value)||0;localStorage.setItem('sa_cap_'+key,cap);localStorage.setItem('sa_fee_'+key,fee);const reserve=p.india?0:fee*2;const usable=Math.max(cap-reserve,0);const sh=Math.floor(usable/p.price);const spend=sh*p.price;const costs=p.india?spend*fee/100:fee*2;const drag=spend>0?costs/spend*100:0;const riskTot=Math.max(p.price-p.stop,0)*sh;const rewardTot=Math.max(p.target-p.price,0)*sh;const net=rewardTot-costs;const riskPct=cap>0?riskTot/cap*100:0;document.getElementById('szOut').innerHTML='<div><span>Whole shares</span><b class="num">'+sh+'</b></div><div><span>Amount invested</span><b class="num">'+p.cur+fmt(spend.toFixed(2))+'</b></div><div><span>Est. total costs</span><b class="num">'+p.cur+fmt(costs.toFixed(2))+' ('+drag.toFixed(2)+'%)</b></div><div><span>Risk if stop hit</span><b class="num" style="color:var(--bad)">-'+p.cur+fmt(riskTot.toFixed(2))+' ('+riskPct.toFixed(1)+'% of capital)</b></div><div><span>Net if target hit</span><b class="num" style="color:'+(net>0?'var(--good)':'var(--bad)')+'">'+(net>=0?'+':'-')+p.cur+fmt(Math.abs(net).toFixed(2))+'</b></div><div><span>Verdict</span><b style="color:'+(sh>0&&net>0?'var(--good)':'var(--warn)')+'">'+(sh<1?'Too expensive':(net>0?'Costs covered':'Costs eat the move'))+'</b></div>';}
function exportCSV(){const rows=[['market','ticker','name','status','confidence','score','prior_close','buy_low','buy_high','target','stop','est_move_pct','shares','cost']];DATA.picks.forEach(p=>rows.push([p.india?'IN':'DE',p.ticker,p.name,p.actionable?'ACTIONABLE':'WATCH-SKIP',p.conf,p.score,p.price,p.buy_low,p.buy_high,p.target,p.stop,p.tgt_move_pct,p.shares,p.cost]));const csv=rows.map(r=>r.map(v=>'"'+String(v).replace(/"/g,'""')+'"').join(',')).join('\n');const b=new Blob([csv],{type:'text/csv;charset=utf-8;'});const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='swing-agent-picks-'+DATA.today+'.csv';document.body.appendChild(a);a.click();document.body.removeChild(a);URL.revokeObjectURL(a.href);toast('📥 CSV downloaded');}
function keyHelp(){document.getElementById('modalBody').innerHTML='<div class="mh"><h3>⌨️ Keyboard shortcuts</h3><div class="x" onclick="closeModal()">✕</div></div><p class="plain" style="line-height:2.2"><kbd>1</kbd> Overview · <kbd>2</kbd> Ideas · <kbd>3</kbd> Analytics · <kbd>4</kbd> Watchlist · <kbd>5</kbd> Learnings · <kbd>6</kbd> About<br><kbd>E</kbd> export CSV · <kbd>T</kbd> theme · <kbd>L</kbd> language · <kbd>?</kbd> this help · <kbd>Esc</kbd> close</p><button class="mbtn" onclick="closeModal()">Got it</button>';document.getElementById('overlay').classList.add('show');}
document.addEventListener('keydown',function(e){if(e.target&&(e.target.tagName==='INPUT'||e.target.tagName==='SELECT'||e.target.tagName==='TEXTAREA'))return;const map={'1':'overview','2':'ideas','3':'analytics','4':'watchlist','5':'learnings','6':'about'};const k=e.key.toLowerCase();if(map[e.key]){nav(map[e.key]);}else if(k==='e'){exportCSV();}else if(k==='t'){toggleTheme();}else if(k==='l'){toggleLang();}else if(e.key==='?'){keyHelp();}});
function init(){loadPrefs();buildLangGrid();document.getElementById('themeBtn').textContent=document.documentElement.getAttribute('data-theme')==='light'?'🌙':'☀️';document.querySelectorAll('#nav b,#bnav b').forEach(b=>b.onclick=()=>nav(b.dataset.v));const ah=DATA.perf.deHit+DATA.perf.inHit,at=DATA.perf.deTot+DATA.perf.inTot;countUp(document.getElementById('heroNum'),DATA.actionableToday);countUp(document.getElementById('kAnalysed'),DATA.picks.length);document.getElementById('kAccuracy').textContent=at?Math.round(100*ah/at)+'%':'—';countUp(document.getElementById('kDE'),DATA.picks.filter(p=>!p.india).length);countUp(document.getElementById('kIN'),DATA.picks.filter(p=>p.india).length);document.querySelectorAll('#v-ideas .chip').forEach(c=>c.classList.toggle('active',c.dataset.f===window._filter));applyFilters();spotlight();miniAcc();document.getElementById('lessonsDE').textContent=DATA.lessonsDE;document.getElementById('lessonsIN').textContent=DATA.lessonsIN;stale();const s=document.createElement('script');s.src='https://translate.google.com/translate_a/element.js?cb=googleTranslateElementInit';document.head.appendChild(s);}
document.addEventListener('DOMContentLoaded',init);
</script></body></html>"""
    doc = doc.replace("__DATA__", data_json).replace("__BUILD__", datetime.datetime.now(datetime.timezone.utc).isoformat())
    with open("index.html","w") as f: f.write(doc)
    print("Premium editorial dashboard written: " + str(len(picks_all)) + " picks")

if __name__ == "__main__":
    main()
