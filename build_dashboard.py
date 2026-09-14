# build_dashboard.py — renders Germany + India picks on one page. All times shown in CET.
# Suggest-only, research/education. Data ~15-min delayed, prior close. NOT financial advice.

import json, os, csv, html

def load_json(p,d):
    if os.path.exists(p):
        with open(p) as f: return json.load(f)
    return d
def esc(x): return html.escape(str(x))
def cc(c): return {"Low":"low","Med":"med","High":"high"}.get(c,"low")

def reasoning(p,cur):
    trend="short-term uptrend (5d>20d avg)" if p["sma5"]>p["sma20"] else "no clear uptrend"
    mom=("balanced momentum" if 45<=p["rsi"]<=68 else "overbought - pullback risk" if p["rsi"]>68 else "weak momentum")
    liq="good liquidity" if p["avgvol"]>300000 else "thinner liquidity (mind slippage)"
    verdict=("Worth considering." if p["worthwhile"] else "Costs vs expected move make this NOT worthwhile - likely SKIP.")
    return (esc(p["name"])+" shows "+trend+" with "+mom+" (RSI "+str(p["rsi"])+"), "+liq+
            ". Range (~ATR "+str(p["atr_pct"])+"%) implies an estimated day-high near "+cur+str(p["est_dayhigh"])+
            " (~"+str(p["tgt_move_pct"])+"% above prior close "+cur+str(p["price"])+"). "+verdict+
            " Confidence "+esc(p["conf"])+" (score "+str(p["score"])+"/100). Estimates from ~15-min delayed data, prior close.")

def sell_rule():
    return ("Sell when estimated day-high is reached (ideally before mid-session). If not hit, exit by end of Day 3 "
            "(5-day max). Stop-loss protects capital.")

def card(i,p,cur,extra_pos=""):
    tag=('<span class="conf high">ACTIONABLE</span>' if (p["worthwhile"] and p["conf"] in ("Med","High"))
         else '<span class="conf low">WATCH / SKIP</span>')
    return ('<div class="card"><h3>Pick '+str(i)+' - '+esc(p["name"])+' ('+esc(p["ticker"])+') '+tag+
            ' <span class="conf '+cc(p["conf"])+'">'+esc(p["conf"])+'</span></h3>'
            '<p>'+reasoning(p,cur)+'</p><table>'
            '<tr><th>Prior close</th><td>'+cur+str(p["price"])+'</td><th>Buy zone</th><td>'+cur+str(p["buy_low"])+' - '+cur+str(p["buy_high"])+'</td></tr>'
            '<tr><th>Est. day-high</th><td>'+cur+str(p["est_dayhigh"])+'</td><th>Est. day-end</th><td>'+cur+str(p["est_dayend"])+'</td></tr>'
            '<tr><th>Stop-loss</th><td>'+cur+str(p["stop"])+'</td><th>Est. move</th><td>'+str(p["tgt_move_pct"])+'%</td></tr>'
            '<tr><th>Position</th><td>'+str(p["shares"])+' sh ~ '+cur+str(p["cost"])+extra_pos+'</td><th>Cost drag</th><td>'+str(p["fee_drag_pct"])+'%</td></tr>'
            '</table><p class="muted"><b>Sell rule:</b> '+sell_rule()+'</p>'
            '<p class="muted"><b>Sources:</b> Prices/technicals via Yahoo Finance (yfinance), ~15-min delayed '
            '[medium-high; cross-check with your broker]. Events via official regulatory disclosures [very high]. No rumor sources.</p></div>')

def section(title, data, cur, is_india=False):
    picks=data.get("picks",[])
    head=('<h2>'+title+'</h2><div class="sub">Updated: '+esc(data.get("generated","no run yet"))+
          ' - '+str(len(picks))+' picks - '+str(data.get("actionable_count",0))+' actionable' +
          ((' - EURINR '+str(data.get("eurinr","?"))) if is_india else '')+'</div>')
    if not picks:
        return head+'<div class="card"><p class="muted">No qualifying setups.</p></div>'
    cards=""
    for i,p in enumerate(picks):
        extra = (" (~EUR"+str(p.get("cost_eur","?"))+")") if is_india else ""
        cards+=card(i+1,p,cur,extra)
    return head+cards

def perf_block(title, logfile):
    rows=[]; total=hit=0
    if os.path.exists(logfile):
        with open(logfile) as f:
            for r in csv.DictReader(f):
                total+=1
                if r.get("hit_miss","").startswith("HIT"): hit+=1
                rows.append('<tr><td>'+esc(r.get("date"))+'</td><td>'+esc(r.get("ticker"))+'</td><td>'+
                            esc(r.get("predicted_dayhigh"))+'</td><td>'+esc(r.get("actual_dayhigh"))+
                            '</td><td>'+esc(r.get("hit_miss"))+'</td><td>'+esc(r.get("notes"))+'</td></tr>')
    acc=('<p class="muted">Accuracy: <b>'+str(hit)+'/'+str(total)+'</b> ('+str(round(100*hit/total))+'%).</p>') if total else ""
    body="".join(reversed(rows)) or '<tr><td colspan="6" class="muted">No history yet.</td></tr>'
    return ('<h3>'+title+'</h3><div class="card">'+acc+'<table><thead><tr><th>Date</th><th>Pick</th>'
            '<th>Pred high</th><th>Actual high</th><th>Hit/Miss</th><th>Notes</th></tr></thead><tbody>'+
            body+'</tbody></table></div>')

def lessons(title, mdfile):
    if os.path.exists(mdfile):
        with open(mdfile) as f: txt=f.read()
        return '<h3>'+title+'</h3><div class="card"><pre style="white-space:pre-wrap;font-family:inherit;color:#cdd6e0">'+esc(txt)+'</pre></div>'
    return '<h3>'+title+'</h3><div class="card"><p class="muted">Empty for now.</p></div>'

def main():
    de=load_json("picks_today.json",{"picks":[]})
    ind=load_json("picks_today_in.json",{"picks":[]})
    css=("body{font-family:-apple-system,Arial,sans-serif;margin:0;background:#0f1115;color:#e8e8e8}"
         "header{background:#161a22;padding:16px 20px;border-bottom:1px solid #262b36}h1{margin:0;font-size:20px}"
         ".sub{color:#9aa4b2;font-size:13px;margin:4px 0}.wrap{padding:16px 20px;max-width:920px;margin:0 auto}"
         ".disclaimer{background:#2a1f00;border:1px solid #6b5200;color:#ffd479;padding:12px;border-radius:8px;font-size:13px;margin:14px 0}"
         ".card{background:#161a22;border:1px solid #262b36;border-radius:10px;padding:16px;margin:12px 0}"
         ".card h3{margin:0 0 8px 0;font-size:16px}.muted{color:#9aa4b2;font-size:13px}"
         ".conf{display:inline-block;padding:2px 8px;border-radius:6px;font-size:12px;font-weight:600;margin-left:6px}"
         ".low{background:#3a1f22;color:#ff9aa2}.med{background:#3a3320;color:#ffd479}.high{background:#1f3a2a;color:#8affb0}"
         "table{width:100%;border-collapse:collapse;font-size:13px;margin-top:8px}th,td{text-align:left;padding:7px;border-bottom:1px solid #262b36}"
         "footer{color:#6b7280;font-size:12px;padding:20px;text-align:center}"
         ".flag{font-size:22px}")
    doc=('<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
         '<meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Swing Agent Dashboard</title>'
         '<style>'+css+'</style></head><body><header><h1>Swing Agent Dashboard</h1>'
         '<div class="sub">Suggest-only research - Germany (XETRA) &amp; India (NSE) - Short swing (2h-5 days) - All times CET</div></header>'
         '<div class="wrap"><div class="disclaimer">WARNING: Research/education only - NOT financial advice. '
         'You place all trades manually and are responsible for them. Data is ~15-min delayed, based on PRIOR CLOSE - not live. '
         'India figures include estimated Indian statutory costs (STT/GST/stamp) - confirm on your contract note.</div>'
         '<div class="card"><span class="flag">🇩🇪</span> <b>Germany</b> - trade via Trade Republic (EUR). '
         '<span class="flag">🇮🇳</span> <b>India</b> - trade via Ventura Securities (INR). Two separate capital pools.</div>'
         '<h2><span class="flag">🇩🇪</span> Germany Picks</h2>'+section("", de, "EUR")+
         '<h2><span class="flag">🇮🇳</span> India Picks <span class="sub">(NSE session ~05:45-12:00 CET)</span></h2>'+section("", ind, "INR", True)+
         '<h2>Performance Log</h2>'+perf_block("🇩🇪 Germany", "performance_log.csv")+perf_block("🇮🇳 India", "performance_log_in.csv")+
         '<h2>Lessons Learned (Strategy Memory)</h2>'+lessons("🇩🇪 Germany", "strategy_memory.md")+lessons("🇮🇳 India", "strategy_memory_in.md")+
         '</div><footer>Swing Agent - free-tier data - GitHub Pages - times in CET</footer></body></html>')
    with open("index.html","w") as f: f.write(doc)
    print("Dashboard written: DE "+str(len(de.get('picks',[])))+" picks, IN "+str(len(ind.get('picks',[])))+" picks")

if __name__=="__main__":
    main()
