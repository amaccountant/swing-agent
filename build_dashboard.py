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
        stale = '<div class="alert">⚠️ Some data isn\'t from today (' + today + ' CET): ' + ", ".join(w) + '. Run
