# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Malviyaarjun
# build_events_page.py (v2) - writes events.html from event_results.json.
# Standalone by design: it cannot break the main dashboard.
# Research/education only. NOT financial advice.

import json, os, datetime


def main():
    ev = {}
    if os.path.exists("event_results.json"):
        with open("event_results.json") as f:
            ev = json.load(f)
    build = datetime.datetime.now(datetime.timezone.utc).isoformat()

    doc = r"""<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Cache-Control" content="no-cache, must-revalidate">
<meta name="last-build" content="__BUILD__">
<title>Event Lab | Swing Research Agent</title>
<link rel="icon" type="image/svg+xml" href="icon.svg">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"></script>
<style>
:root{--bg:#080b12;--panel:rgba(255,255,255,.04);--line:rgba(255,255,255,.09);--txt:#e9eef5;
--mut:#8a94a6;--acc:#6c8cff;--good:#3ccf8e;--bad:#f0616d;--warn:#f2b661}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,'Segoe UI',Roboto,Arial,sans-serif;background:var(--bg);color:var(--txt);line-height:1.55}
body::before{content:"";position:fixed;inset:-20%;z-index:-1;
background:radial-gradient(640px 400px at 15% 10%,rgba(108,140,255,.13),transparent),
radial-gradient(600px 380px at 85% 25%,rgba(140,110,255,.10),transparent);
animation:drift 24s ease-in-out infinite alternate}
@keyframes drift{to{transform:translate(-2%,2%) scale(1.05)}}
.num{font-variant-numeric:tabular-nums}
.wrap{max-width:1040px;margin:0 auto;padding:28px 22px 60px}
a.back{color:var(--acc);text-decoration:none;font-size:13px;font-weight:600}
h1{font-size:28px;margin:14px 0 4px;letter-spacing:-.3px}
.lead{color:var(--mut);font-size:14px;margin:0 0 18px;max-width:720px}
.status{border-radius:16px;padding:18px 20px;border:1px solid;margin:18px 0}
.status h2{margin:0 0 6px;font-size:17px}.status p{margin:0;color:var(--mut);font-size:13.5px}
.s-bad{border-color:var(--bad);background:rgba(240,97,109,.08)}
.s-good{border-color:var(--good);background:rgba(60,207,142,.08)}
.s-warn{border-color:var(--warn);background:rgba(242,182,97,.08)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:18px 0}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:16px;transition:transform .3s}
.kpi:hover{transform:translateY(-3px)}
.kpi .v{font-size:28px;font-weight:800}.kpi .l{color:var(--mut);font-size:12px;margin-top:4px}
.sec{margin:34px 0 8px}.sec h3{margin:0;font-size:18px}.sec p{margin:3px 0 0;color:var(--mut);font-size:13px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:18px;margin:12px 0}
.hz{font-weight:700;font-size:14px;margin:4px 0 10px}
.row{display:grid;grid-template-columns:160px 1fr 170px;gap:12px;align-items:center;margin:12px 0;font-size:13px}
.track{height:12px;border-radius:7px;background:rgba(255,255,255,.07);position:relative}
.fill{height:100%;border-radius:7px;width:0;transition:width 1.2s cubic-bezier(.2,.85,.2,1)}
.be{position:absolute;top:-4px;width:2px;height:20px;background:var(--warn)}
.meta{text-align:right;color:var(--mut);font-size:12px}
.chip{display:inline-block;padding:2px 8px;border-radius:12px;font-size:10.5px;font-weight:700;margin-top:3px}
.c-good{background:rgba(60,207,142,.15);color:var(--good)}.c-bad{background:rgba(240,97,109,.15);color:var(--bad)}
.c-warn{background:rgba(242,182,97,.15);color:var(--warn)}
.legend{color:var(--mut);font-size:11.5px;margin-top:6px}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th,td{text-align:left;padding:9px 8px;border-bottom:1px solid var(--line)}
th{color:var(--mut);font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.4px}
.note{color:var(--mut);font-size:12.5px}
.disc{border:1px solid var(--warn);background:rgba(242,182,97,.07);color:var(--warn);border-radius:14px;padding:13px 15px;font-size:12px;margin-top:26px}
.reveal{opacity:0;transform:translateY(18px);transition:opacity .6s,transform .6s}.reveal.in{opacity:1;transform:none}
@media(max-width:700px){.row{grid-template-columns:1fr}.meta{text-align:left}}
footer{color:var(--mut);font-size:11.5px;text-align:center;padding:20px}
</style></head><body><div class="wrap">
<a class="back" href="./">&larr; Dashboard</a>
<h1>Event Lab</h1>
<p class="lead">Does an earnings release change the odds enough to pay for trading costs? Every figure is measured on
historical windows, and a result only counts if it is positive after costs and statistically distinguishable from noise.</p>
<div id="status"></div>
<div class="kpis reveal" id="kpis"></div>
<div class="sec reveal"><h3>Probability of reaching target before stop</h3>
<p>The bar shows P(win). The yellow line shows the P(win) needed to break even after costs for that group.</p></div>
<div id="horizons"></div>
<div class="sec reveal"><h3>Overnight vs intraday</h3><p>Where the return accrues, and whether capturing it survives costs.</p></div>
<div class="card reveal"><canvas id="onChart" height="130"></canvas><p class="note" id="onNote"></p></div>
<div class="sec reveal"><h3>Per stock, 5-day horizon</h3><p>Earnings samples per name are small; read these as context, not evidence.</p></div>
<div class="card reveal" id="stocks"></div>
<div class="sec reveal"><h3>Method</h3></div>
<div class="card reveal note" id="method"></div>
<div class="disc" translate="no"><b>Research and education only, not financial advice.</b> Windows overlap and earnings
cluster in the same weeks, so the true independent sample is smaller than the n shown. Historical effects can disappear.</div>
</div><footer>Swing Research Agent &middot; Event Lab &middot; by Malviyaarjun</footer>
<script>
const D=__DATA__;
function pc(x,d){return x===null||x===undefined?'n/a':(x*100).toFixed(d===undefined?1:d)+'%';}
function sg(x,d){return (x>0?'+':'')+x.toFixed(d)+'%';}
function chip(v){const c=v==='positive and significant'?'c-good':(v==='insufficient sample'||v==='positive but not significant'?'c-warn':'c-bad');return '<span class="chip '+c+'">'+v+'</span>';}
function count(el){const to=parseFloat(el.dataset.to),dec=parseInt(el.dataset.dec||'2'),suf=el.dataset.suf||'';let i=0;const n=36;
 const t=setInterval(function(){i++;const v=to*i/n;el.textContent=(el.dataset.sign==='1'&&v>0?'+':'')+v.toFixed(dec)+suf;if(i>=n)clearInterval(t);},20);}
function observe(){const o=new IntersectionObserver(function(es){es.forEach(function(e){if(!e.isIntersecting)return;e.target.classList.add('in');
 e.target.querySelectorAll('.fill').forEach(function(f){f.style.width=f.dataset.w+'%';});
 e.target.querySelectorAll('[data-to]').forEach(function(el){if(!el.dataset.done){el.dataset.done=1;count(el);}});});},{threshold:.1});
 document.querySelectorAll('.reveal').forEach(function(el){o.observe(el);});}
function row(label,x){if(!x||!x.n)return '<div class="row"><div>'+label+'</div><div class="note">no data</div><div></div></div>';
 const w=(x.p_win*100).toFixed(1),be=x.breakeven_p?(x.breakeven_p*100).toFixed(1):null;
 const col=(be&&x.p_win*100>be)?'var(--good)':'var(--bad)';
 return '<div class="row"><div>'+label+'<br><span class="note">n='+x.n+'</span></div>'
 +'<div class="track">'+(be?'<div class="be" style="left:'+be+'%"></div>':'')+'<div class="fill" data-w="'+w+'" style="background:'+col+'"></div></div>'
 +'<div class="meta">P(win) '+w+'%'+(be?' / needs '+be+'%':'')+'<br>net '+sg(x.mean_net_pct,2)+' per trade, t='+x.t_stat+'<br>'+chip(x.verdict)+'</div></div>';}
function init(){
 if(!D.pooled){document.getElementById('status').innerHTML='<div class="status s-warn"><h2>No results yet</h2><p>Run Actions &rarr; Event Lab &rarr; Run workflow.</p></div>';return;}
 const p5=D.pooled['5'],b=p5.baseline,u=p5.after_positive,n=p5.after_negative;
 const good=[u,n].some(function(x){return x&&x.verdict==='positive and significant';});
 const thin=[u,n].every(function(x){return !x||x.verdict==='insufficient sample';});
 document.getElementById('status').innerHTML=good
  ?'<div class="status s-good"><h2>An event effect survives costs at 5 days</h2><p>Worth paper-testing over 20 to 30 resolved probes. Not a signal to deploy capital.</p></div>'
  :(thin?'<div class="status s-warn"><h2>Inconclusive</h2><p>Too few post-earnings windows to judge.</p></div>'
  :'<div class="status s-bad"><h2>No tradable earnings effect at the 5-day horizon</h2><p>After '+D.config.cost_pct_per_trade+'% costs per trade, post-earnings windows do not beat break-even with statistical confidence.</p></div>');
 const k=[[b.mean_net_pct,'Any day: net per trade, 5 days',1],[u.mean_net_pct,'After positive earnings: net per trade',1],
  [u.t_stat,'t-statistic (needs 2.0 or more)',0],[D.config.cost_pct_per_trade,'Assumed cost per round trip (%)',0]];
 document.getElementById('kpis').innerHTML=k.map(function(x){const neg=x[0]<0&&x[2];return '<div class="kpi"><div class="v num" style="color:'+(x[2]?(x[0]>0?'var(--good)':'var(--bad)'):'var(--txt)')+'" data-to="'+x[0]+'" data-dec="2" data-sign="'+x[2]+'" data-suf="'+(x[2]?'%':'')+'">0</div><div class="l">'+x[1]+'</div></div>';}).join('');
 let h='';['1','5','20'].forEach(function(dd){const p=D.pooled[dd];if(!p)return;
  h+='<div class="card reveal"><div class="hz">'+dd+'-day horizon</div>'+row('Any day',p.baseline)+row('After positive earnings',p.after_positive)+row('After negative earnings',p.after_negative)+'</div>';});
 document.getElementById('horizons').innerHTML=h+'<p class="legend">Green bar: P(win) is above its break-even line. Red: below it. A result still needs t of 2.0 or more to count.</p>';
 const o=D.overnight;if(o&&o.stocks){
  new Chart(document.getElementById('onChart'),{type:'bar',data:{labels:['Overnight (close to open)','Intraday (open to close)','Cost to capture overnight'],
   datasets:[{label:'Average % per day',data:[o.overnight_mean_pct,o.intraday_mean_pct,-D.config.overnight_cost_pct_per_day],backgroundColor:['#6c8cff','#8c6eff','#f0616d']}]},
   options:{animation:{duration:1400,easing:'easeOutQuart'},plugins:{legend:{display:false}},
   scales:{y:{ticks:{color:'#8a94a6'},grid:{color:'rgba(255,255,255,.06)'}},x:{ticks:{color:'#8a94a6'},grid:{display:false}}}}});
  document.getElementById('onNote').innerHTML='Across '+o.stocks+' stocks, the overnight session averaged '+o.overnight_mean_pct+'% per day and intraday '+o.intraday_mean_pct
   +'%. Capturing overnight returns means two orders every day, costing about '+D.config.overnight_cost_pct_per_day+'% per day, which leaves <b>'+o.overnight_net_after_cost_pct+'% per day</b>.';}
 document.getElementById('stocks').innerHTML='<table><thead><tr><th>Stock</th><th>Earnings events</th><th>Any day P(win)</th><th>After + earnings P(win)</th><th>n</th></tr></thead><tbody>'
  +D.per_stock.map(function(s){const a=s.h5.baseline,e=s.h5.after_positive;return '<tr><td>'+s.name+'</td><td class="num">'+s.n_earnings+'</td><td class="num">'+(a&&a.n?pc(a.p_win):'n/a')+'</td><td class="num">'+(e&&e.n?pc(e.p_win):'n/a')+'</td><td class="num">'+(e?e.n:0)+'</td></tr>';}).join('')+'</tbody></table>';
 document.getElementById('method').innerHTML='Entry at the close of the reaction day. Target: 60th percentile of past best highs over the same horizon, using only earlier data. Stop: 1 &times; ATR, filled at the open if price gaps through it. '
  +'Costs: '+D.config.fee_pct+'% fees plus '+D.config.slippage_pct+'% slippage per round trip. A result counts only if net expectancy is positive with n &ge; '+D.config.min_reliable_n+' and t &ge; '+D.config.t_min+'. Generated '+D.generated+'.';
 observe();}
document.addEventListener('DOMContentLoaded',init);
</script></body></html>"""
    doc = doc.replace("__DATA__", json.dumps(ev)).replace("__BUILD__", build)
    with open("events.html", "w") as f:
        f.write(doc)
    print("events.html written")


if __name__ == "__main__":
    main()
