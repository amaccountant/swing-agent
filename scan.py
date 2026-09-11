# scan.py — Swing Agent morning scan (suggest-only, research/education).
# Data: Twelve Data free API (~15-min delayed for European exchanges). NOT live. NOT financial advice.

import os, csv, json, math, datetime, urllib.request, urllib.parse

API_KEY = os.environ.get("TWELVE_DATA_KEY", "").strip()
ACCOUNT_EUR = 200.0          # your total capital
FEE_PER_ORDER = 1.0          # Trade Republic manual order fee (EUR)
ROUNDTRIP_FEE = FEE_PER_ORDER * 2
MIN_GROSS_MOVE_PCT = 3.0     # only act if realistic target >= 3% (covers fees + edge)
BASE = "https://api.twelvedata.com"

def http_get(path, params):
    params = dict(params); params["apikey"] = API_KEY
    url = f"{BASE}/{path}?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode())

def get_series(symbol, outputsize=60):
    try:
        d = http_get("time_series", {"symbol": symbol, "interval": "1day",
                                     "outputsize": outputsize, "timezone": "Europe/Berlin"})
        if "values" not in d: return None
        vals = list(reversed(d["values"]))
        closes = [float(v["close"]) for v in vals]
        highs  = [float(v["high"])  for v in vals]
        lows   = [float(v["low"])   for v in vals]
        vols   = [float(v.get("volume") or 0) for v in vals]
        return {"closes": closes, "highs": highs, "lows": lows, "vols": vols}
    except Exception:
        return None

def sma(x, n):
    return sum(x[-n:]) / n if len(x) >= n else None

def rsi(closes, n=14):
    if len(closes) < n + 1: return None
    gains = losses = 0.0
    for i in range(-n, 0):
        ch = closes[i] - closes[i-1]
        gains += max(ch, 0); losses += max(-ch, 0)
    if losses == 0: return 100.0
    rs = (gains/n) / (losses/n)
    return 100 - (100/(1+rs))

def atr_pct(highs, lows, closes, n=14):
    if len(closes) < n + 1: return None
    trs = []
    for i in range(-n, 0):
        tr = max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1]))
        trs.append(tr)
    atr = sum(trs)/n
    return (atr / closes[-1]) * 100 if closes[-1] else None

def analyze(symbol, name):
    s = get_series(symbol)
    if not s or len(s["closes"]) < 20: return None
    c = s["closes"]; price = c[-1]
    sma5, sma20 = sma(c,5), sma(c,20)
    r = rsi(c); a = atr_pct(s["highs"], s["lows"], c)
    avgvol = sma(s["vols"],20) or 0
    if None in (sma5, sma20, r, a): return None

    score = 50.0
    if sma5 > sma20: score += 15
    else: score -= 10
    if price > sma20: score += 8
    if 45 <= r <= 68: score += 12
    elif r > 75: score -= 12
    elif r < 35: score -= 6
    if 1.2 <= a <= 4.0: score += 8
    elif a > 6: score -= 10
    if avgvol > 300000: score += 7
    affordable = price <= ACCOUNT_EUR
    if not affordable: score -= 25

    score = max(0, min(100, score))
    conf = "High" if score >= 72 else ("Med" if score >= 60 else "Low")

    buy_low  = round(price * (1 - 0.003), 2)
    buy_high = round(price * (1 + 0.004), 2)
    est_dayhigh = round(price * (1 + (a/100)*0.9), 2)
    est_dayend  = round(price * (1 + (a/100)*0.5), 2)
    stop        = round(price * (1 - (a/100)*1.1), 2)
    tgt_move_pct = (est_dayhigh/price - 1)*100

    max_alloc = min(ACCOUNT_EUR - ROUNDTRIP_FEE, ACCOUNT_EUR*0.95)
    shares = int(max_alloc // price) if price <= max_alloc else 0
    cost = round(shares*price, 2)
    fee_drag_pct = round((ROUNDTRIP_FEE / cost)*100, 2) if cost > 0 else None
    worthwhile = (shares >= 1) and (tgt_move_pct >= MIN_GROSS_MOVE_PCT)

    return {
        "symbol": symbol, "name": name, "price": round(price,2),
        "conf": conf, "score": round(score,1), "rsi": round(r,1), "atr_pct": round(a,2),
        "sma5": round(sma5,2), "sma20": round(sma20,2), "avgvol": int(avgvol),
        "buy_low": buy_low, "buy_high": buy_high,
        "est_dayhigh": est_dayhigh, "est_dayend": est_dayend, "stop": stop,
        "tgt_move_pct": round(tgt_move_pct,2),
        "shares": shares, "cost": cost, "fee_drag_pct": fee_drag_pct,
        "worthwhile": worthwhile, "affordable": affordable
    }

def reasoning(p):
    trend = "short-term uptrend (5-day above 20-day average)" if p["sma5"]>p["sma20"] else "no clear uptrend"
    mom = ("balanced momentum" if 45<=p["rsi"]<=68 else
           "overbought (pullback risk)" if p["rsi"]>68 else "weak momentum")
    liq = "good liquidity" if p["avgvol"]>300000 else "thinner liquidity — mind slippage"
    fee_line = (f"~{p['fee_drag_pct']}% fee drag on a €{p['cost']} position"
                if p["cost"]>0 else "does not fit as a whole share within €200")
    verdict = ("Worth considering" if p["worthwhile"]
               else "⚠️ Fees/return not attractive — likely SKIP")
    return (f"{p['name']} shows {trend} with {mom} (RSI {p['rsi']}) and {liq}. "
            f"Daily range (~ATR {p['atr_pct']}%) suggests a realistic day-high estimate of €{p['est_dayhigh']} "
            f"(~{p['tgt_move_pct']}% from €{p['price']}). Position: {p['shares']} whole share(s) ≈ €{p['cost']}, {fee_line}. "
            f"{verdict}. Confidence {p['conf']} (score {p['score']}/100). "
            f"All figures are volatility-based ESTIMATES from ~15-min delayed data, not guarantees.")

def sell_condition():
    return ("Sell when day-high estimate is reached (ideally before ~15:00 CET). "
            "If target not hit, exit by end of Day 3 to respect the 5-day max. "
            "Hard stop-loss protects capital if price falls to the stop.")

def main():
    picks = []
    with open("watchlist.csv") as f:
        for row in csv.DictReader(f):
            res = analyze(row["symbol"], row["name"])
            if res: picks.append(res)
    picks.sort(key=lambda x: (x["worthwhile"], x["score"]), reverse=True)
    top = picks[:3]
    actionable = [p for p in top if p["worthwhile"] and p["conf"] in ("Med","High")]

    now = datetime.datetime.now(datetime.timezone.utc).astimezone()
    stamp = now.strftime("%Y-%m-%d %H:%M %Z")

    with open("picks_today.json","w") as f:
        json.dump({"date": now.strftime("%Y-%m-%d"), "generated": stamp,
                   "picks": top, "actionable_count": len(actionable)}, f, indent=2)

    print(f"[{stamp}] scanned {len(picks)} names; top {len(top)}; actionable {len(actionable)}")
    for p in top:
        print(f"  {p['symbol']:12} {p['conf']:4} score {p['score']:5}  €{p['price']:8}  "
              f"{p['shares']}sh €{p['cost']:7}  tgt {p['tgt_move_pct']}%  worthwhile={p['worthwhile']}")

if __name__ == "__main__":
    main()
