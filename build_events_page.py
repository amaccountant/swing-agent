# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Malviyaarjun
# build_events_page.py — animated Event Lab page (events.html). Standalone by design:
# cannot break the main dashboard. Research/education. NOT financial advice.

import json, os, datetime

def load(p, d):
    if os.path.exists(p):
        with open(p) as f: return json.load(f)
    return d

def main():
    ev = load("event_results.json", {})
    data_json = json.dumps(ev)
    build = datetime.datetime.now(datetime.timezone.utc).isoformat()

    doc = r"""<!DOCTYPE html><html lang="en" data-theme="dark"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Cache-Control" content="no-cache, must-revalidate">
<meta name="last-build" content="__BUILD__">
<title>Event Lab — Swing Research Agent</title>
<link rel="icon" type="image/svg+xml" href="icon.svg">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"></script>
<style>
:root{--bg:#07090f;--panel:rgba(255,255,255,.045);--line:rgba(255,255,255,.10);--txt:#eaf0f7;
--mut:#8b95a7;--acc:#6c8cff;--acc2:#9a6cff;--good:#39d98a;--bad:#ff5d73;--warn:#ffc86b}
*{box-sizing:border-box}body{margin:0;font-family:-apple-system,'Segoe UI',Roboto,Arial,sans-serif;
background:var(--bg);color:var(--txt);overflow-x:hidden}
body::before{content:"";position:fixed;inset:-25%;z-index:-1;
background:radial-gradient(700px 420px at 18% 12%,rgba(108,140,255,.16),transparent),
radial-gradient(640px 400px at 82% 26%,rgba(154,108,255,.14),transparent),
radial-gradient(760px 500px at 50% 96%,rgba(57,217,138,.09),transparent);
animation:drift 22s ease-in-out infinite alternate}
@keyframes drift{to{transform:translate(-3%,2%) scale(1.07)}}
.num{font-variant-numeric:tabular-nums}
header{padding:30px 22px 14px;max-width:1080px;margin:0 auto}
h1{margin:0;font-size:30px;letter-spacing:-.4px}
h1 span{background:linear-gradient(120deg,var(--acc),var(--acc2));-webkit-background-clip:text;
background-clip:text;color:transparent}
.sub{color:var(--mut);font-size:13px;margin-top:8px}
.wrap{max-width:1080px;margin:0 auto;padding:0 22px 70px}
.back{display:inline-flex;gap:7px;align-items:center;margin:14px 0;color:var(--acc);
text-decoration:none;font-size:13px;font-weight:600}
.reveal{opacity:0;transform:translateY(22px);transition:opacity .7s cubic-bezier(.2,.8,.2,1),transform .7s cubic-bezier(.2,.8,.2,1)}
.reveal.in{opacity:1;transform:none}
.card{background:var(--panel);border:1px solid var(--line);border-radius:20px;padding:20px;
margin:16px 0;backdrop-filter:blur(10px)}
.h2{display:flex;align-items:center;gap:12px;margin:34px 0 4px}
.h2 .ic{width:42px;height:42px;border-radius:13px;display:grid;place-items:center;font-size:20px;
background:linear-gradient(135deg,rgba(108,140,255,.26),rgba(154,108,255,.18));border:1px solid var(--line)}
.h2 h2{margin:0;font-size:21px}.h2 p{margin:2px 0 0;color:var(--mut);font-size:13px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:18px;
text-align:center;transition:transform .3s,box-shadow .3s}
.kpi:hover{transform:translateY(-5px);box-shadow:0 18px 44px rgba(0,0,0,.4)}
.kpi .v{font-size:32px;font-weight:850}.kpi .l{color:var(--mut);font-size:11.5px;margin-top:5px}
.kpi .n{color:var(--mut);font-size:10.5px;margin-top:3px;opacity:.8}
.bars{margin-top:8px}
.bar{margin:13px 0}
.bar .top{display:flex;justify-content:space-between;font-size:12.5px;margin-bottom:5px}
.bar .track{height:15px;border-radius:9px;background:rgba(255,255,255,.07);position:relative;overflow:hidden}
.bar .fill{height:100%;border-radius:9px;width:0;transition:width 1.3s cubic-bezier(.2,.85,.2,1)}
.be{position:absolute;top:-4px;width:2px;height:23px;background:var(--warn);z-index:2}
.be::after{content:"break-even";position:absolute;top:-16px;left:-22px;font-size:9px;color:var(--warn);white-space:nowrap}
.tag{display:inline-block;padding:2px 9px;border-radius:20px;font-size:10.5px;font-weight:800;margin-left:6px}
.tag.ok{background:rgba(57,217,138,.16);color:var(--good)}
.tag.no{background:rgba(255,93,115,.16);color:var(--bad)}
.tag.un{background:rgba(255,200,107,.16);color:var(--warn)}
.verdict{border-radius:16px;padding:18px;margin:16px 0;border:1px solid}
.verdict h3{margin:0 0 6px;font-size:17px}
.verdict p{margin:0;font-size:13.5px;color:var(--mut)}
.v-no{border-color:var(--bad);background:rgba(255,93,115,.09)}
.v-ok{border-color:var(--good);background:rgba(57,217,138,.09)}
.v-un{border-color:var(--warn);background:rgba(255,200,107,.09)}
table{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:10px}
th,td{text-align:left;padding:9px 8px;border-bottom:1px solid var(--line)}
th{color:var(--mut);font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.4px}
.disc{background:rgba(255,200,107,.09);border:1px solid var(--warn);color:var(--warn);
padding:13px 15px;border-radius:14px;font-size:12px;margin:18px 0}
.soon{color:var(--mut);text-align:center;padding:46px 20px}
footer{color:var(--mut);font-size:11.5px;text-align:center;padding:26px}
</style></head><body>
<header>
  <a class="back" href="./">← Back to dashboard</a>
  <h1>Event <span>Lab</span></h1>
  <div class="sub">Does conditioning on real events change the odds? Measured, not assumed · <span id="gen"></span></div>
</header>
<div class="wrap">
  <div class="disc" translate="no"><b>Read first:</b> research &amp; education, <b>not financial advice</b>.
  Every probability below is an estimate from historical windows and carries survivorship, overlap and
  regime-change bias. Small samples are flagged UNRELIABLE and must not be traded.</div>

  <div class="h2 reveal"><div class="ic">📊</div><div><h2>The bar to clear</h2>
    <p>At the payoff geometry your engine measures, P(win) must exceed ~43% just to break even after costs.</p></div></div>
  <div class="grid reveal" id="kpis"></div>

  <div class="h2 reveal"><div class="ic">📣</div><div><h2>Post-earnings drift</h2>
    <p>Same probability test, but windows starting the day after an earnings release.</p></div></div>
  <div class="card reveal" id="pead"></div>

  <div class="h2 reveal"><div class="ic">🌙</div><div><h2>Overnight vs intraday</h2>
    <p>Where does the return actually accrue — while the market is open, or while it's shut?</p></div></div>
  <div class="card reveal"><canvas id="onChart" height="150"></canvas><div id="onNote"></div></div>

  <div class="h2 reveal"><div class="ic">🔬</div><div><h2>Per-stock detail</h2>
    <p>Earnings events available per name. Thin samples are the main limitation here.</p></div></div>
  <div class="card reveal" id="detail"></div>

  <div id="verdicts"></div>
</div>
<footer>Event Lab · Swing Research Agent · crafted by Malviyaarjun · research only, not financial advice</footer>
<script>
const D=__DATA__;
const BE=(D.config&&D.config.breakeven_ref)?D.config.breakeven_ref*100:43;
function pct(x){return x===null||x===undefined?'n/a':(x*100).toFixed(1)+'%';}
function io(){const o=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){e.target.classList.add('in');
  e.target.querySelectorAll('.fill').forEach(f=>{setTimeout(()=>{f.style.width=f.dataset.w+'%';},90);});
  e.target.querySelectorAll('[data-count]').forEach(el=>count(el));}}),{threshold:.12});
  document.querySelectorAll('.reveal').forEach(el=>o.observe(el));}
function count(el){const to=parseFloat(el.dataset.count);if(isNaN(to))return;let n=0;const steps=34;
  const t=setInterval(()=>{n+=to/steps;if(n>=to){n=to;clearInterval(t);}
  el.textContent=(el.dataset.suffix==='%')?n.toFixed(1)+'%':n.toFixed(0);},20);}
function bar(label,p,n,reliable){
  if(p===null||p===undefined)return '<div class="bar"><div class="top"><span>'+label+'</span><span>n/a</span></div></div>';
  const v=p*100;const col=v>BE?'var(--good)':'var(--bad)';
  const tag=!reliable?'<span class="tag un">n='+n+' UNRELIABLE</span>':(v>BE?'<span class="tag ok">clears</span>':'<span class="tag no">below</span>');
  return '<div class="bar"><div class="top"><span>'+label+tag+'</span><span class="num">'+v.toFixed(1)+'% <span style="color:var(--mut)">(n='+n+')</span></span></div>'
   +'<div class="track"><div class="be" style="left:'+BE+'%"></div>'
   +'<div class="fill" data-w="'+v.toFixed(1)+'" style="background:linear-gradient(90deg,'+col+','+col+'aa)"></div></div></div>';}
function init(){
  if(!D.pooled){document.getElementById('kpis').innerHTML='<div class="soon">No results yet. Run <b>Actions → Event Lab → Run workflow</b>, then refresh.</div>';return;}
  document.getElementById('gen').textContent=D.generated||'';
  const h5=D.pooled['5']||{};
  const k=[['Baseline P(win), 5d',h5.baseline?h5.baseline.p_win:null,h5.baseline?h5.baseline.n:0],
           ['After positive surprise',h5.pead_up?h5.pead_up.p_win:null,h5.pead_up?h5.pead_up.n:0],
           ['After negative surprise',h5.pead_down?h5.pead_down.p_win:null,h5.pead_down?h5.pead_down.n:0],
           ['Break-even needed',BE/100,null]];
  document.getElementById('kpis').innerHTML=k.map(function(x){
    const v=x[1]===null?null:x[1]*100;
    const col=x[0]==='Break-even needed'?'var(--warn)':(v!==null&&v>BE?'var(--good)':'var(--bad)');
    return '<div class="kpi"><div class="v" style="color:'+col+'" data-count="'+(v!==null?v:0)+'" data-suffix="%">0%</div>'
      +'<div class="l">'+x[0]+'</div>'+(x[2]!==null?'<div class="n">n='+x[2]+'</div>':'<div class="n">threshold</div>')+'</div>';}).join('');

  let ph='';
  [1,5,20].forEach(function(dd){const p=D.pooled[String(dd)];if(!p)return;
    ph+='<div style="margin:18px 0 6px;font-weight:700;font-size:14px">Horizon: '+dd+' day'+(dd>1?'s':'')+'</div>';
    ph+=bar('Baseline (any day)',p.baseline?p.baseline.p_win:null,p.baseline?p.baseline.n:0,p.baseline?p.baseline.reliable:false);
    ph+=bar('After POSITIVE earnings reaction',p.pead_up?p.pead_up.p_win:null,p.pead_up?p.pead_up.n:0,p.pead_up?p.pead_up.reliable:false);
    ph+=bar('After NEGATIVE earnings reaction',p.pead_down?p.pead_down.p_win:null,p.pead_down?p.pead_down.n:0,p.pead_down?p.pead_down.reliable:false);
    if(p.pead_up_lift_pp!==null&&p.pead_up_lift_pp!==undefined){
      const L=p.pead_up_lift_pp;
      ph+='<p style="font-size:12.5px;color:'+(L>0?'var(--good)':'var(--bad)')+';margin:6px 0 0">Event lift vs baseline: '+(L>0?'+':'')+L+' percentage points</p>';}
  });
  document.getElementById('pead').innerHTML=ph;

  if(D.overnight&&D.overnight.overnight){
    const a=D.overnight.overnight,b=D.overnight.intraday;
    new Chart(document.getElementById('onChart'),{type:'bar',
      data:{labels:['Avg total return %','Avg win rate %','Daily Sharpe ×100'],
        datasets:[{label:'Overnight (close→open)',data:[a.avg_total_pct,a.avg_win_rate*100,a.avg_daily_sharpe*100],backgroundColor:'#6c8cff'},
                  {label:'Intraday (open→close)',data:[b.avg_total_pct,b.avg_win_rate*100,b.avg_daily_sharpe*100],backgroundColor:'#9a6cff'}]},
      options:{animation:{duration:1500,easing:'easeOutQuart'},
        plugins:{legend:{labels:{color:'#eaf0f7'}}},
        scales:{y:{ticks:{color:'#8b95a7'},grid:{color:'rgba(255,255,255,.06)'}},x:{ticks:{color:'#8b95a7'},grid:{display:false}}}}});
    const diff=(a.avg_total_pct-b.avg_total_pct).toFixed(2);
    document.getElementById('onNote').innerHTML='<p style="font-size:13px;color:var(--mut);margin-top:12px">'
      +'Across '+a.stocks+' stocks, the overnight session contributed <b style="color:var(--txt)">'+a.avg_total_pct
      +'%</b> on average versus <b style="color:var(--txt)">'+b.avg_total_pct+'%</b> intraday — a gap of <b style="color:'
      +(diff>0?'var(--good)':'var(--bad)')+'">'+(diff>0?'+':'')+diff+' pp</b>. '
      +'This is descriptive only: capturing it still costs spread and fees on every entry and exit.</p>';}

  if(D.per_stock&&D.per_stock.length){
    let rows=D.per_stock.map(function(s){const b5=s.baseline&&s.baseline['5'],u5=s.pead_up&&s.pead_up['5'];
      return '<tr><td><b>'+s.name+'</b><br><span style="color:var(--acc);font-size:11px">'+s.ticker+'</span></td>'
      +'<td class="num">'+s.n_earnings+'</td><td class="num">'+(b5?pct(b5.p_win):'n/a')+'</td>'
      +'<td class="num">'+(u5&&u5.p_win!==null?pct(u5.p_win):'n/a')+'</td>'
      +'<td class="num">'+(u5?u5.n:0)+'</td></tr>';}).join('');
    document.getElementById('detail').innerHTML='<table><thead><tr><th>Stock</th><th>Earnings events</th>'
      +'<th>Baseline 5d</th><th>Post-earnings 5d</th><th>n</th></tr></thead><tbody>'+rows+'</tbody></table>';}

  const p5=D.pooled['5'];let vh='';
  if(p5&&p5.pead_up&&p5.pead_up.p_win!==null){
    const rel=p5.pead_up.reliable,cl=p5.pead_up.p_win*100>BE;
    if(!rel)vh='<div class="verdict v-un"><h3>⚠ Inconclusive — sample too small</h3><p>Only '+p5.pead_up.n
      +' usable post-earnings windows. That is not enough to distinguish a real effect from noise. Do not trade on this.</p></div>';
    else if(cl)vh='<div class="verdict v-ok"><h3>Event conditioning clears break-even</h3><p>This is a hypothesis worth paper-testing over 20–30 resolved recommendations — not a green light to deploy capital.</p></div>';
    else vh='<div class="verdict v-no"><h3>Event conditioning does not clear break-even</h3><p>Post-earnings odds remain below the ~'+BE.toFixed(0)
      +'% needed after costs. On this evidence, the strategy family stays rejected.</p></div>';}
  document.getElementById('verdicts').innerHTML=vh;
  io();
}
document.addEventListener('DOMContentLoaded',init);
</script></body></html>"""
    doc = doc.replace("__DATA__", data_json).replace("__BUILD__", build)
    with open("events.html","w") as f: f.write(doc)
    print("events.html written (" + str(len(ev.get("per_stock", []))) + " stocks studied)")

if __name__ == "__main__":
    main()
