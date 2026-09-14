# scan.py — Swing Agent morning scan (suggest-only, research/education).
# Data source: yfinance (Yahoo Finance), German XETRA/Frankfurt tickers like SAP.DE.
# Data is ~15-min delayed. NOT live. NOT financial advice.

import csv, json, datetime
import yfinance as yf

ACCOUNT_EUR   = 200.0
FEE_PER_ORDER = 1.0
ROUNDTRIP_FEE = FEE_PER_ORDER * 2
MIN_GROSS_MOVE_PCT = 3.0

def get_series(ticker):
    try:
        h = yf.Ticker(ticker).history(period="4mo", interval="1d", auto_adjust=False)
        if h is None or len(h) == 0:
            print(f"    [skip] {ticker}: no data returned")
            return None
        # keep only the OHLCV columns, drop any rows with missing values
        h = h[["Open","High","Low","Close","Volume"]].dropna()
        # drop rows where price is zero or non-positive (bad ticks)
        h = h[h["Close"] > 0]
        if len(h) < 20:
            print(f"    [skip] {ticker}: only {len(h)} clean rows after cleaning")
            return None
        closes = [float(x) for x in h["Close"].tolist()]
        highs  = [float(x) for x in h["High"].tolist()]
        lows   = [float(x) for x in h["Low"].tolist()]
        vols   = [float(x) for x in h["Volume"].tolist()]
        # final guard: last close must be a real number
        if closes[-1] != closes[-1]:  # NaN check
            print(f"    [skip] {ticker}: last close is NaN after cleaning")
            return None
        return {"closes": closes, "highs": highs, "lows": lows, "vols": vols}
    except Exception as e:
        print(f"    [error] {ticker}: {e}")
        return None

def sma(x, n): return sum(x[-n:]) / n if len(x) >= n else None

def rsi(closes, n=14):
    if len(closes) < n + 1: return None
    g = l = 0.0
    for i in range(-n, 0):
        ch = closes[i] - closes[i-1]; g += max(ch,0); l += max(-ch,0)
    if l == 0: return 100.0
    rs = (g/n)/(l/n); return 100 - (100/(1+rs))

def atr_pct(highs, lows, closes, n=14):
    if len(closes) < n + 1: return None
    trs = []
    for i in range(-n, 0):
        tr = max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1]))
        trs.append(tr)
    atr = sum(trs)/n
    return (atr/closes[-1])*100 if closes[-1] else None

def analyze(ticker, name):
    s = get_series(ticker)
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

# --- Evidence-based targets: use this stock's OWN recent behaviour ---
    # How far above the PRIOR close did the daily HIGH actually reach, historically?
    up_moves = []
    for i in range(1, len(c)):
        up = (s["highs"][i] / c[i-1] - 1) * 100   # high vs previous close, in %
        if up == up:  # not NaN
            up_moves.append(max(up, 0))
    up_moves.sort()
    def pctl(data, q):
        if not data: return 0.0
        k = (len(data)-1) * q
        lo = int(k); hi = min(lo+1, len(data)-1)
        return data[lo] + (data[hi]-data[lo])*(k-lo)
    typ_up = pctl(up_moves, 0.50)     # median daily high-above-prior-close
    real_up = pctl(up_moves, 0.60)    # slightly optimistic but achievable target
    stretch_up = pctl(up_moves, 0.80) # "good day" high (context only)

    buy_low  = round(price*(1-0.003),2); buy_high = round(price*(1+0.004),2)
    est_dayend  = round(price*(1 + typ_up/100), 2)      # realistic day-end-ish
    est_dayhigh = round(price*(1 + real_up/100), 2)     # realistic, reachable target
    day_stretch = round(price*(1 + stretch_up/100), 2)  # optimistic scenario (context)
    stop        = round(price*(1 - (a/100)*1.1), 2)     # stop still ATR-based
    tgt_move_pct = round(real_up, 2)

    max_alloc = min(ACCOUNT_EUR-ROUNDTRIP_FEE, ACCOUNT_EUR*0.95)
    shares = int(max_alloc//price) if price <= max_alloc else 0
    cost = round(shares*price,2)
    fee_drag_pct = round((ROUNDTRIP_FEE/cost)*100,2) if cost>0 else None
    worthwhile = (shares>=1) and (tgt_move_pct>=MIN_GROSS_MOVE_PCT)

    return {"ticker":ticker,"name":name,"price":round(price,2),"conf":conf,"score":round(score,1),
            "rsi":round(r,1),"atr_pct":round(a,2),"sma5":round(sma5,2),"sma20":round(sma20,2),
            "avgvol":int(avgvol),"buy_low":buy_low,"buy_high":buy_high,"est_dayhigh":est_dayhigh,
            "est_dayend":est_dayend,"stop":stop,"tgt_move_pct":round(tgt_move_pct,2),
            "shares":shares,"cost":cost,"fee_drag_pct":fee_drag_pct,"day_stretch": day_stretch,"worthwhile":worthwhile,
            "affordable":affordable}

def main():
    picks = []
    with open("watchlist.csv") as f:
        for row in csv.DictReader(f):
            res = analyze(row["ticker"], row["name"])
            if res: picks.append(res)
    picks.sort(key=lambda x:(x["worthwhile"], x["score"]), reverse=True)
    top = picks[:3]
    actionable = [p for p in top if p["worthwhile"] and p["conf"] in ("Med","High")]
    now = datetime.datetime.now(datetime.timezone.utc).astimezone()
    stamp = now.strftime("%Y-%m-%d %H:%M %Z")
    with open("picks_today.json","w") as f:
        json.dump({"date":now.strftime("%Y-%m-%d"),"generated":stamp,
                   "picks":top,"actionable_count":len(actionable)}, f, indent=2)
    print(f"[{stamp}] scanned {len(picks)} names; top {len(top)}; actionable {len(actionable)}")
    for p in top:
        print(f"  {p['ticker']:9} {p['conf']:4} score {p['score']:5}  EUR{p['price']:8}  "
              f"{p['shares']}sh EUR{p['cost']:7}  tgt {p['tgt_move_pct']}%  worthwhile={p['worthwhile']}")

if __name__ == "__main__":
    main()
