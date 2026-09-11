# build_dashboard.py — writes today's picks + performance log + lessons into index.html.
# Suggest-only, research/education. Data ~15-min delayed, based on prior close. NOT financial advice.

import json, os, csv, html, datetime

def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default

def esc(x):
    return html.escape(str(x))

def conf_class(c):
    return {"Low": "low", "Med": "med", "High": "high"}.get(c, "low")

def reasoning(p):
    trend = "short-term uptrend (5-day above 20-day avg)" if p["sma5"] > p["sma20"] else "no clear short-term uptrend"
    mom = ("balanced momentum" if 45 <= p["rsi"] <= 68 else
           "overbought - pullback risk" if p["rsi"] > 68 else "weak momentum")
    liq = "good liquidity" if p["avgvol"] > 300000 else "thinner liquidity (mind slippage)"
    verdict = ("Worth considering." if p["worthwhile"]
               else "Fees vs. expected move make this NOT worthwhile - likely SKIP.")
    fee_txt = (" fee drag ~" + str(p["fee_drag_pct"]) + "%. ") if p["fee_drag_pct"] else ". "
    return (esc(p["name"]) + " shows " + trend + " with " + mom + " (RSI " + str(p["rsi"]) + "), and " + liq +
            ". Daily range (~ATR " + str(p["atr_pct"]) + "%) implies an estimated day-high near EUR " +
            str(p["est_dayhigh"]) + " (about " + str(p["tgt_move_pct"]) + "% above the prior close of EUR " +
            str(p["price"]) + "). Suggested position: " + str(p["shares"]) + " whole share(s) ~= EUR " +
            str(p["cost"]) + "," + fee_txt + verdict + " Confidence " + esc(p["conf"]) + " (score " +
            str(p["score"]) + "/100). All numbers are volatility-based ESTIMATES from ~15-min delayed data "
            "based on the prior close, not guarantees.")

def sell_condition():
    return ("Sell when the estimated day-high is reached (ideally before ~15:00 CET). "
            "If the target is not hit, exit by the end of Day 3 to respect the 5-day max. "
            "The stop-loss protects capital if price falls to that level.")

def pick_card(i, p):
    tag = ('<span class="conf high">ACTIONABLE</span>'
           if (p["worthwhile"] and p["conf"] in ("Med", "High"))
           else '<span class="conf low">WATCH / SKIP</span>')
    fee_disp = str(p["fee_drag_pct"]) if p["fee_drag_pct"] else "-"
    return (
        '<div class="card">'
        '<h3>Pick ' + str(i) + ' - ' + esc(p["name"]) + ' (' + esc(p["ticker"]) + ') - XETRA ' + tag +
        ' <span class="conf ' + conf_class(p["conf"]) + '">' + esc(p["conf"]) + ' confidence</span></h3>'
        '<p>' + reasoning(p) + '</p>'
        '<table>'
        '<tr><th>Prior close</th><td>EUR ' + str(p["price"]) + '</td><th>Buy zone (est.)</th><td>EUR ' + str(p["buy_low"]) + ' - ' + str(p["buy_high"]) + '</td></tr>'
        '<tr><th>Est. day-high</th><td>EUR ' + str(p["est_dayhigh"]) + '</td><th>Est. day-end target</th><td>EUR ' + str(p["est_dayend"]) + '</td></tr>'
        '<tr><th>Stop-loss</th><td>EUR ' + str(p["stop"]) + '</td><th>Est. move to target</th><td>' + str(p["tgt_move_pct"]) + '%</td></tr>'
        '<tr><th>Position</th><td>' + str(p["shares"]) + ' share(s) ~ EUR ' + str(p["cost"]) + '</td><th>Fee drag</th><td>' + fee_disp + '%</td></tr>'
        '</table>'
        '<p class="muted"><b>Sell rule:</b> ' + sell_condition() + '</p>'
        '<p class="muted"><b>Sources:</b> Price/technicals via Yahoo Finance (yfinance), ~15-min delayed '
        '[reliability: medium-high, cross-check with your broker]. Company events via official regulatory '
        'disclosure feeds [reliability: very high]. No rumor/forum sources used.</p>'
        '</div>'
    )

def perf_rows():
    rows = []
    if os.path.exists("performance_log.csv"):
        with open("performance_log.csv") as f:
            for r in csv.DictReader(f):
                rows.append('<tr><td>' + esc(r.get("date")) + '</td><td>' + esc(r.get("ticker")) +
                            '</td><td>' + esc(r.get("predicted_dayhigh")) + '</td><td>' +
                            esc(r.get("actual_dayhigh")) + '</td><td>' + esc(r.get("hit_miss")) +
                            '</td><td>' + esc(r.get("notes")) + '</td></tr>')
    if not rows:
        return '<tr><td colspan="6" class="muted">No history yet - fills after first end-of-day review.</td></tr>'
    return "".join(reversed(rows))

def accuracy_summary():
    if not os.path.exists("performance_log.csv"):
        return ""
    total = hit = 0
    with open("performance_log.csv") as f:
        for r in csv.DictReader(f):
            total += 1
            if r.get("hit_miss", "").startswith("HIT"):
                hit += 1
    if total == 0:
        return ""
    return ('<p class="muted">Running accuracy (day-high within estimate): <b>' + str(hit) + '/' +
            str(total) + '</b> (' + str(round(100 * hit / total)) + '%).</p>')

def lessons_html():
    if os.path.exists("strategy_memory.md"):
        with open("strategy_memory.md") as f:
            txt = f.read()
        return "<pre style='white-space:pre-wrap;font-family:inherit;color:#cdd6e0'>" + esc(txt) + "</pre>"
    return '<p class="muted">The agent will record why each miss happened and how it adjusts. Empty for now.</p>'

def main():
    data = load_json("picks_today.json", {"date": "-", "generated": "no run yet", "picks": [], "actionable_count": 0})
    picks = data.get("picks", [])
    cards = "".join(pick_card(i + 1, p) for i, p in enumerate(picks)) if picks else \
        '<div class="card"><h3>No picks</h3><p class="muted">No qualifying setups today.</p></div>'
    updated = esc(data.get("generated")) + " - " + str(len(picks)) + " picks - " + str(data.get("actionable_count", 0)) + " actionable"

    css = (
        "body{font-family:-apple-system,Arial,sans-serif;margin:0;background:#0f1115;color:#e8e8e8}"
        "header{background:#161a22;padding:16px 20px;border-bottom:1px solid #262b36}"
        "h1{margin:0;font-size:20px}.sub{color:#9aa4b2;font-size:13px;margin-top:4px}"
        ".wrap{padding:16px 20px;max-width:900px;margin:0 auto}"
        ".disclaimer{background:#2a1f00;border:1px solid #6b5200;color:#ffd479;padding:12px;border-radius:8px;font-size:13px;margin:14px 0}"
        ".card{background:#161a22;border:1px solid #262b36;border-radius:10px;padding:16px;margin:12px 0}"
        ".card h3{margin:0 0 8px 0;font-size:16px}.muted{color:#9aa4b2;font-size:13px}"
        ".conf{display:inline-block;padding:2px 8px;border-radius:6px;font-size:12px;font-weight:600;margin-left:6px}"
        ".low{background:#3a1f22;color:#ff9aa2}.med{background:#3a3320;color:#ffd479}.high{background:#1f3a2a;color:#8affb0}"
        "table{width:100%;border-collapse:collapse;font-size:13px;margin-top:8px}"
        "th,td{text-align:left;padding:7px;border-bottom:1px solid #262b36}"
        "footer{color:#6b7280;font-size:12px;padding:20px;text-align:center}"
    )

    html_doc = (
        '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        '<title>Swing Agent Dashboard</title><style>' + css + '</style></head><body>'
        '<header><h1>Swing Agent Dashboard</h1>'
        '<div class="sub">Suggest-only research - German stocks (XETRA) - Short swing (2h-5 days)</div>'
        '<div class="sub">Last updated: ' + updated + '</div></header>'
        '<div class="wrap">'
        '<div class="disclaimer">WARNING: Research/education only - NOT financial advice. You place all trades '
        'manually and are responsible for them. Data is ~15-min delayed and based on the PRIOR CLOSE - not live.</div>'
        '<h2>Today\'s Picks</h2>' + cards +
        '<h2>Performance Log</h2><div class="card">' + accuracy_summary() +
        '<table><thead><tr><th>Date</th><th>Pick</th><th>Predicted high</th><th>Actual high</th>'
        '<th>Hit/Miss</th><th>Notes</th></tr></thead><tbody>' + perf_rows() + '</tbody></table></div>'
        '<h2>Lessons Learned (Strategy Memory)</h2><div class="card">' + lessons_html() + '</div>'
        '</div><footer>Swing Agent - EUR0 free-tier data - GitHub Pages</footer></body></html>'
    )
    with open("index.html", "w") as f:
        f.write(html_doc)
    print("Dashboard written: " + str(len(picks)) + " picks, updated " + updated)

if __name__ == "__main__":
    main()
