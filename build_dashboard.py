# build_dashboard.py — Professional beginner-friendly dashboard (Germany + India).
# Pure HTML/CSS/SVG, no external libraries. All times CET. Research/education. NOT financial advice.

import json, os, csv, html, datetime

def load_json(p, d):
    if os.path.exists(p):
        with open(p) as f: return json.load(f)
    return d
def esc(x): return html.escape(str(x))
def cc(c): return {"Low":"low","Med":"med","High":"high"}.get(c, "low")

def tip(term, explain):
    return '<span class="tip">' + esc(term) + '<span class="tiptext">' + esc(explain) + '</span></span>'

# --- small SVG helpers (no libraries) ---
def gauge(score):
    # semicircle confidence gauge 0-100
    pct = max(0, min(100, score)) / 100
    ang = 180 * pct
    import math
    x = 60 + 50 * math.cos(math.radians(180 - ang))
    y = 60 - 50 * math.sin(math.radians(180 - ang))
    color = "#8affb0" if score >= 72 else "#ffd479" if score >= 60 else "#ff9aa2"
    large = 1 if ang > 90 else 0
    return ('<svg width="120" height="70" viewBox="0 0 120 70">'
            '<path d="M10 60 A50 50 0 0 1 110 60" fill="none" stroke="#262b36" stroke-width="10"/>'
            '<path d="M10 60 A50 50 0 ' + str(large) + ' 1 ' + str(round(x,1)) + ' ' + str(round(y,1)) +
            '" fill="none" stroke="' + color + '" stroke-width="10" stroke-linecap="round"/>'
            '<text x="60" y="55" text-anchor="middle" fill="#e8e8e8" font-size="18" font-weight="700">' +
            str(int(score)) + '</text>'
            '<text x="60" y="68" text-anchor="middle" fill="#9aa4b2" font-size="9">confidence</text></svg>')

def rr_bar(price, stop, target):
    # risk vs reward visual
    risk = max(price - stop, 0.0001)
    reward = max(target - price, 0.0001)
    total = risk + reward
    rw = round(100 * reward / total)
    rk = 100 - rw
    ratio = round(reward / risk, 1)
    return ('<div class="rrwrap"><div class="rrlabels"><span style="color:#ff9aa2">Risk</span>'
            '<span style="color:#8affb0">Reward &nbsp;(' + str(ratio) + ':1)</span></div>'
            '<div class="rrbar"><div class="rrrisk" style="width:' + str(rk) + '%"></div>'
            '<div class="rrreward" style="width:' + str(rw) + '%"></div></div></div>')

def price_pos(buy_low, buy_high, stop, target, price):
    # where prior close sits between stop and target
    lo = min(stop, buy_low); hi = max(target, buy_high)
    span = max(hi - lo, 0.0001)
    def p(v): return round(100 * (v - lo) / span, 1)
    return ('<div class="scale">'
            '<div class="scaletrack">'
            '<div class="marker stopm" style="left:' + str(p(stop)) + '%" title="Stop-loss"></div>'
            '<div class="zone" style="left:' + str(p(buy_low)) + '%;width:' + str(max(p(buy_high)-p(buy_low),2)) + '%"></div>'
            '<div class="marker pricem" style="left:' + str(p(price)) + '%" title="Prior close"></div>'
            '<div class="marker tgtm" style="left:' + str(p(target)) + '%" title="Target"></div>'
            '</div>'
            '<div class="scalelegend"><span>🛑 Stop</span><span>🟦 Buy zone</span><span>● Now</span><span>🎯 Target</span></div>'
            '</div>')

def donut(hit, total):
    pct = round(100 * hit / total) if total else 0
    import math
    circ = 2 * math.pi * 40
    fill = circ * pct / 100
    return ('<svg width="120" height="120" viewBox="0 0 120 120">'
            '<circle cx="60" cy="60" r="40" fill="none" stroke="#262b36" stroke-width="14"/>'
            '<circle cx="60" cy="60" r="40" fill="none" stroke="#7aa2ff" stroke-width="14" '
            'stroke-dasharray="' + str(round(fill,1)) + ' ' + str(round(circ,1)) + '" '
            'stroke-linecap="round" transform="rotate(-90 60 60)"/>'
            '<text x="60" y="58" text-anchor="middle" fill="#e8e8e8" font-size="22" font-weight="700">' +
            str(pct) + '%</text>'
            '<text x="60" y="76" text-anchor="middle" fill="#9aa4b2" font-size="10">' +
            str(hit) + '/' + str(total) + ' hit</text></svg>')

def reasoning(p, cur):
    trend = "in a short-term uptrend" if p["sma5"] > p["sma20"] else "not in a clear uptrend"
    mom = ("with balanced momentum" if 45 <= p["rsi"] <= 68 else
           "looking overbought (could pull back)" if p["rsi"] > 68 else "with weak momentum")
    verdict = ("This setup looks worth considering." if p["worthwhile"]
               else "The likely move is too small to beat trading costs — probably best to skip.")
    return (esc(p["name"]) + " is " + trend + " " + mom + ". Based on how this stock usually moves, "
            "a realistic target is around " + cur + str(p["est_dayhigh"]) + " (about " + str(p["tgt_move_pct"]) +
            "% above its last close of " + cur + str(p["price"]) + "). " + verdict)

def card(i, p, cur, is_india=False):
    actionable = p["worthwhile"] and p["conf"] in ("Med", "High")
    tag = ('<span class="badge go">✓ ACTIONABLE</span>' if actionable
           else '<span class="badge skip">✕ WATCH / SKIP</span>')
    eur = (' <span class="muted">(~€' + str(p.get("cost_eur","?")) + ')</span>') if is_india else ''
    return (
      '<div class="pcard ' + ('act' if actionable else 'skp') + '">'
      '<div class="pchead"><div><h3>' + esc(p["name"]) + ' <span class="ticker">' + esc(p["ticker"]) + '</span></h3>'
      + tag + '</div>' + gauge(p["score"]) + '</div>'
      '<p class="plain">' + reasoning(p, cur) + '</p>'
      + price_pos(p["buy_low"], p["buy_high"], p["stop"], p["est_dayhigh"], p["price"]) +
      rr_bar(p["price"], p["stop"], p["est_dayhigh"]) +
      '<div class="grid">'
      '<div class="kv"><span>' + tip("Buy zone", "The price range where entering makes sense. Only buy if the live price is here.") + '</span><b>' + cur + str(p["buy_low"]) + ' – ' + cur + str(p["buy_high"]) + '</b></div>'
      '<div class="kv"><span>' + tip("Target", "A realistic price to aim to sell at, based on the stock's own history. An estimate, not a promise.") + '</span><b>' + cur + str(p["est_dayhigh"]) + '</b></div>'
      '<div class="kv"><span>' + tip("Stop-loss", "Your safety exit. If price falls here, sell to limit the loss. Set this order right after buying.") + '</span><b>' + cur + str(p["stop"]) + '</b></div>'
      '<div class="kv"><span>' + tip("Position", "How many whole shares fit your budget, and the cost.") + '</span><b>' + str(p["shares"]) + ' shares ≈ ' + cur + str(p["cost"]) + eur + '</b></div>'
      '</div>'
      '<div class="sellrule">🕒 <b>When to sell:</b> aim for the target (ideally before mid-session). If it doesn\'t reach, exit by end of Day 3 (max 5 days). The stop-loss protects you if it drops.</div>'
      '<div class="src">Source: prices via Yahoo Finance (~15-min delayed) · reliability: medium-high · always confirm the live price in your broker.</div>'
      '</div>')

def section(data, cur, is_india=False):
    picks = data.get("picks", [])
    sub = ('Updated ' + esc(data.get("generated","—")) + ' · ' + str(data.get("actionable_count",0)) +
           ' actionable of ' + str(len(picks)) + (' · €1=₹' + str(data.get("eurinr","?")) if is_india else ''))
    if not picks:
        return '<div class="sub">' + sub + '</div><div class="pcard skp"><p class="plain">No qualifying setups today. Sitting in cash is a valid, cost-free choice.</p></div>'
    return '<div class="sub">' + sub + '</div>' + "".join(card(i+1, p, cur, is_india) for i, p in enumerate(picks))

def perf_stats(logfile):
    total = hit = 0
    if os.path.exists(logfile):
        with open(logfile) as f:
            for r in csv.DictReader(f):
                total += 1
                if r.get("hit_miss","").startswith("HIT"): hit += 1
    return hit, total

def perf_table(logfile):
    rows = []
    if os.path.exists(logfile):
        with open(logfile) as f:
            for r in csv.DictReader(f):
                hm = r.get("hit_miss","")
                cls = "hit" if hm.startswith("HIT") else "miss"
                rows.append('<tr><td>' + esc(r.get("date")) + '</td><td>' + esc(r.get("ticker")) +
                            '</td><td>' + esc(r.get("predicted_dayhigh")) + '</td><td>' +
                            esc(r.get("actual_dayhigh")) + '</td><td><span class="pill ' + cls + '">' +
                            esc(hm) + '</span></td></tr>')
    body = "".join(reversed(rows)) or '<tr><td colspan="5" class="muted">No history yet.</td></tr>'
    return ('<table class="perf"><thead><tr><th>Date</th><th>Stock</th><th>Predicted high</th>'
            '<th>Actual high</th><th>Result</th></tr></thead><tbody>' + body + '</tbody></table>')

def lessons(mdfile):
    if os.path.exists(mdfile):
        with open(mdfile) as f: txt = f.read()
        return '<pre class="lessons">' + esc(txt) + '</pre>'
    return '<p class="muted">No lessons recorded yet.</p>'

def main():
    de = load_json("picks_today.json", {"picks": []})
    ind = load_json("picks_today_in.json", {"picks": []})
    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=1))).strftime("%Y-%m-%d")
    de_stale = de.get("date") not in (today, "-")
    in_stale = ind.get("date") not in (today, "-")
    stale = ""
    if de_stale or in_stale:
        w = []
        if de_stale: w.append("Germany (" + str(de.get("date")) + ")")
        if in_stale: w.append("India (" + str(ind.get("date")) + ")")
        stale = '<div class="alert">⚠️ Some data isn\'t from today (' + today + ' CET): ' + ", ".join(w) + '. Run the scan workflow to refresh before acting.</div>'

    dh, dt = perf_stats("performance_log.csv")
    ih, it = perf_stats("performance_log_in.csv")
    tot_act = de.get("actionable_count",0) + ind.get("actionable_count",0)
    all_hit, all_tot = dh + ih, dt + it

    css = """
    *{box-sizing:border-box}body{font-family:-apple-system,'Segoe UI',Roboto,Arial,sans-serif;margin:0;background:#0b0e14;color:#e8e8e8;line-height:1.5}
    .top{background:linear-gradient(135deg,#1a2233,#0f1420);padding:26px 20px;border-bottom:1px solid #262b36}
    .top h1{margin:0;font-size:24px;letter-spacing:.3px}.top .tag{color:#9aa4b2;font-size:13px;margin-top:6px}
    .wrap{max-width:1000px;margin:0 auto;padding:20px}
    .tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:16px 0}
    .tile{background:#141a26;border:1px solid #262b36;border-radius:14px;padding:16px;text-align:center}
    .tile .big{font-size:28px;font-weight:800;color:#7aa2ff}.tile .lbl{color:#9aa4b2;font-size:12px;margin-top:4px}
    .alert{background:#3a1f22;border:1px solid #6b1f2a;color:#ff9aa2;padding:12px 14px;border-radius:10px;margin:12px 0;font-size:14px}
    .disc{background:#241b00;border:1px solid #6b5200;color:#ffd479;padding:12px 14px;border-radius:10px;margin:12px 0;font-size:13px}
    .guide{background:#101725;border:1px solid #262b36;border-radius:14px;padding:16px;margin:12px 0}
    .guide h3{margin:0 0 8px}.guide ol{margin:8px 0 0 18px;padding:0;color:#c7d0dc;font-size:14px}
    .guide li{margin:5px 0}
    .mkt{display:flex;align-items:center;gap:10px;margin:26px 0 6px;font-size:20px;font-weight:700}
    .flag{font-size:26px}.sub{color:#9aa4b2;font-size:13px;margin-bottom:10px}
    .pcard{background:#141a26;border:1px solid #262b36;border-radius:16px;padding:18px;margin:14px 0;box-shadow:0 4px 18px rgba(0,0,0,.25)}
    .pcard.act{border-left:4px solid #8affb0}.pcard.skp{border-left:4px solid #ff9aa2;opacity:.92}
    .pchead{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}
    .pchead h3{margin:0;font-size:18px}.ticker{color:#7aa2ff;font-size:13px;font-weight:600}
    .badge{display:inline-block;margin-top:6px;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:700}
    .badge.go{background:#12331f;color:#8affb0;border:1px solid #1f5133}.badge.skip{background:#331416;color:#ff9aa2;border:1px solid #5a1f24}
    .plain{color:#d5dde8;font-size:14px}
    .scale{margin:14px 0}.scaletrack{position:relative;height:14px;background:#1c2432;border-radius:8px;margin:6px 0}
    .zone{position:absolute;top:0;height:14px;background:rgba(122,162,255,.35);border:1px solid #7aa2ff;border-radius:4px}
    .marker{position:absolute;top:-3px;width:2px;height:20px}
    .stopm{background:#ff6b78}.tgtm{background:#8affb0}.pricem{width:10px;height:10px;top:2px;border-radius:50%;background:#fff;transform:translateX(-4px)}
    .scalelegend{display:flex;justify-content:space-between;color:#9aa4b2;font-size:11px}
    .rrwrap{margin:12px 0}.rrlabels{display:flex;justify-content:space-between;font-size:12px;margin-bottom:3px}
    .rrbar{display:flex;height:12px;border-radius:6px;overflow:hidden}.rrrisk{background:#ff6b78}.rrreward{background:#5fd18e}
    .grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:12px 0}
    .kv{background:#0f1622;border:1px solid #222a38;border-radius:10px;padding:8px 10px;font-size:13px;display:flex;flex-direction:column;gap:2px}
    .kv span{color:#9aa4b2;font-size:12px}.kv b{font-size:15px}
    .sellrule{background:#0f1622;border:1px dashed #2c3648;border-radius:10px;padding:10px;font-size:13px;color:#cdd6e0;margin-top:6px}
    .src{color:#6b7280;font-size:11px;margin-top:8px}
    .tip{border-bottom:1px dotted #7aa2ff;cursor:help;position:relative}
    .tip .tiptext{visibility:hidden;opacity:0;transition:.15s;position:absolute;bottom:130%;left:0;z-index:9;background:#0a0f18;color:#e8e8e8;border:1px solid #3a4render;border-radius:8px;padding:8px 10px;width:220px;font-size:12px;box-shadow:0 6px 20px rgba(0,0,0,.4)}
    .tip:hover .tiptext{visibility:visible;opacity:1}
    .panel{background:#141a26;border:1px solid #262b36;border-radius:16px;padding:18px;margin:14px 0}
    .perfhead{display:flex;align-items:center;gap:20px;flex-wrap:wrap}
    table.perf{width:100%;border-collapse:collapse;font-size:13px;margin-top:10px}
    table.perf th,table.perf td{text-align:left;padding:8px;border-bottom:1px solid #222a38}
    .pill{padding:2px 8px;border-radius:12px;font-size:11px;font-weight:700}.pill.hit{background:#12331f;color:#8affb0}.pill.miss{background:#331416;color:#ff9aa2}
    .lessons{white-space:pre-wrap;font-family:inherit;color:#c7d0dc;font-size:13px;margin:0}
    .muted{color:#9aa4b2;font-size:13px}
    footer{color:#6b7280;font-size:12px;text-align:center;padding:26px}
    """.replace("3a4render", "3a4658")

    doc = (
      '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
      '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
      '<title>Swing Agent — Stock Ideas Dashboard</title><style>' + css + '</style></head><body>'
      '<div class="top"><h1>📈 Swing Agent</h1>'
      '<div class="tag">Beginner-friendly stock research · Germany 🇩🇪 &amp; India 🇮🇳 · Short-term ideas (hours to 5 days) · All times CET</div></div>'
      '<div class="wrap">'
      + stale +
      '<div class="disc"><b>Please read:</b> This is research &amp; education, <b>not financial advice</b>. '
      'Numbers are estimates from data that is ~15-min delayed (based on the previous close). '
      'You decide and place every trade yourself, and you are responsible for it.</div>'
      '<div class="tiles">'
      '<div class="tile"><div class="big">' + str(tot_act) + '</div><div class="lbl">Actionable ideas today</div></div>'
      '<div class="tile"><div class="big">' + str(len(de.get("picks",[])) + len(ind.get("picks",[]))) + '</div><div class="lbl">Stocks analysed today</div></div>'
      '<div class="tile"><div class="big">' + (str(round(100*all_hit/all_tot)) + '%' if all_tot else '—') + '</div><div class="lbl">Overall target accuracy</div></div>'
      '<div class="tile"><div class="big">2</div><div class="lbl">Markets covered</div></div>'
      '</div>'
      '<div class="guide"><h3>🧭 How to read this (no experience needed)</h3><ol>'
      '<li><b>Look for a green “✓ ACTIONABLE” tag.</b> Grey/red “WATCH / SKIP” means don’t trade it today.</li>'
      '<li><b>Check the confidence dial</b> (top-right of each card) — higher = stronger signal.</li>'
      '<li><b>The coloured bar</b> shows Risk vs Reward. More green than red is better.</li>'
      '<li><b>The line scale</b> shows the safety exit (🛑), buy zone (🟦), price now (●) and target (🎯).</li>'
      '<li><b>Hover any underlined word</b> for a plain-English explanation.</li>'
      '<li><b>Always check the live price in your broker</b> before buying — our data is ~15 min delayed.</li>'
      '</ol></div>'
      '<div class="mkt"><span class="flag">🇩🇪</span> Germany <span class="muted" style="font-weight:400;font-size:13px">· trade via Trade Republic (€)</span></div>'
      + section(de, "€") +
      '<div class="mkt"><span class="flag">🇮🇳</span> India <span class="muted" style="font-weight:400;font-size:13px">· trade via Ventura (₹) · NSE open ~05:45–12:00 CET</span></div>'
      + section(ind, "₹", True) +
      '<div class="mkt">📊 Track Record</div>'
      '<div class="panel"><div class="perfhead">' + donut(all_hit, all_tot) +
      '<div><p class="plain">This shows how often the estimated target was actually reached. '
      'A low score early on is normal — the system learns and recalibrates over time. '
      'It measures <i>estimate accuracy</i>, not your profit.</p>'
      '<p class="muted">🇩🇪 Germany: ' + str(dh) + '/' + str(dt) + ' · 🇮🇳 India: ' + str(ih) + '/' + str(it) + '</p></div></div></div>'
      '<div class="panel"><h3 style="margin-top:0">🇩🇪 Germany — recent results</h3>' + perf_table("performance_log.csv") + '</div>'
      '<div class="panel"><h3 style="margin-top:0">🇮🇳 India — recent results</h3>' + perf_table("performance_log_in.csv") + '</div>'
      '<div class="mkt">🧠 What the system learned</div>'
      '<div class="panel"><h3 style="margin-top:0">🇩🇪 Germany</h3>' + lessons("strategy_memory.md") + '</div>'
      '<div class="panel"><h3 style="margin-top:0">🇮🇳 India</h3>' + lessons("strategy_memory_in.md") + '</div>'
      '</div><footer>Swing Agent · built on free tools · times in CET · research/education only, not financial advice</footer>'
      '</body></html>')
    with open("index.html", "w") as f:
        f.write(doc)
    print("Pro dashboard written: DE " + str(len(de.get('picks',[]))) + " picks, IN " +
          str(len(ind.get('picks',[]))) + " picks")

if __name__ == "__main__":
    main()
