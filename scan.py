# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Malviyaarjun
# Swing Research Agent v3 — Germany (XETRA). PAPER MODE. Suggest-only.
# Research/education. NOT financial advice. Data ~15-min delayed, prior close.
#
# v3 fixes: 5-day target matched to 5-day horizon; gap-adjusted stops; relative
# strength vs DAX (alpha not beta); 1% risk sizing; min EUR800 position so fees
# stay <=20% of expected gain; max 2 positions; -15% drawdown circuit breaker;
# GROSS and NET reported separately.

import csv, json, math, os, datetime
import yfinance as yf

PAPER_MODE     = True
PAPER_CAPITAL  = 2000.0    # simulated capital (change only when validated)
RISK_PCT       = 1.0       # risk per trade, % of equity
MAX_POSITIONS  = 2
MIN_POSITION   = 800.0     # below this, fees eat too much of the gain
FEE_PER_ORDER  = 1.0       # EUR, Trade Republic manual order
FEE_MAX_SHARE  = 0.20      # fees must be <=20% of expected gross gain
GAP_FACTOR     = 2.0       # assume stop slips 2x due to overnight gaps
MAX_DD_PCT     = 15.0      # circuit breaker
HORIZON_DAYS   = 5
TARGET_PCTL    = 0.60
SCORE_MIN      = 78.0      # top-decile selectivity
ATR_MIN, ATR_MAX = 1.2, 5.0
MIN_TURNOVER   = 2000000.0
INDEX          = "^GDAXI"

def sma(x, n):
    return sum(x[-n:]) / n if len(x) >= n else None

def rsi(c, n=14):
    if len(c) < n + 1: return None
    g = l = 0.0
    for k in range(-n, 0):
        ch = c[k] - c[k-1]; g += max(ch, 0); l += max(-ch, 0)
    if l == 0: return 100.0
    return 100 - (100 / (1 + (g/n)/(l/n)))

def atr_pct(h, lo, c, n=14):
    if len(c) < n + 1: return None
    trs = []
    for k in range(-n, 0):
        trs.append(max(h[k]-lo[k], abs(h[k]-c[k-1]), abs(lo[k]-c[k-1])))
    return (sum(trs)/n/c[-1])*100 if c[-1] else None

def pctl(data, q):
    if not data: return 0.0
    s = sorted(data); k = (len(s)-1)*q
    lo = int(k); hi = min(lo+1, len(s)-1)
    return s[lo] + (s[hi]-s[lo])*(k-lo)

def fwd_pctl(closes, highs, days=HORIZON_DAYS, q=TARGET_PCTL):
    """Percentile of best high within `days` sessions after a close. Past data only."""
    ups = []
    for j in range(1, len(closes) - days + 1):
        base = closes[j-1]
        mx = max(highs[j:j+days])
        if base > 0: ups.append(max(mx/base - 1, 0) * 100)
    return pctl(ups, q)

def get_series(ticker):
    try:
        h = yf.Ticker(ticker).history(period="1y", interval="1d", auto_adjust=False)
        if h is None or len(h) == 0:
            print("    [skip] " + ticker + ": no data"); return None
        h = h[["Open","High","Low","Close","Volume"]].dropna()
        h = h[h["Close"] > 0]
        if len(h) < 60:
            print("    [skip] " + ticker + ": only " + str(len(h)) + " rows"); return None
        return {"c":[float(x) for x in h["Close"]], "h":[float(x) for x in h["High"]],
                "l":[float(x) for x in h["Low"]],  "v":[float(x) for x in h["Volume"]]}
    except Exception as e:
        print("    [error] " + ticker + ": " + str(e)); return None

def index_context():
    """DAX regime (above 200-day SMA) and 20-day return, for relative strength."""
    s = get_series(INDEX)
    if not s:
        print("  [warn] index unavailable — regime filter disabled, RS disabled")
        return {"ok": True, "ret20": None}
    c = s["c"]
    s200 = sma(c, 200)
    regime = (s200 is not None) and (c[-1] > s200)
    ret20 = (c[-1]/c[-21] - 1) * 100 if len(c) >= 21 else None
    print("  DAX: last=" + str(round(c[-1],1)) + " 200dSMA=" + str(round(s200,1) if s200 else "n/a")
          + " regime_ok=" + str(regime) + " ret20=" + str(round(ret20,2) if ret20 is not None else "n/a") + "%")
    return {"ok": regime, "ret20": ret20}

def equity_state():
    st = {"equity": PAPER_CAPITAL, "peak": PAPER_CAPITAL, "halted": False, "dd_pct": 0.0}
    if os.path.exists("equity_state.json"):
        try:
            with open("equity_state.json") as f: st.update(json.load(f))
        except Exception: pass
    st["peak"] = max(st.get("peak", PAPER_CAPITAL), st.get("equity", PAPER_CAPITAL))
    dd = (st["peak"] - st["equity"]) / st["peak"] * 100 if st["peak"] > 0 else 0.0
    st["dd_pct"] = round(dd, 2)
    st["halted"] = dd >= MAX_DD_PCT
    with open("equity_state.json", "w") as f: json.dump(st, f, indent=2)
    return st

def analyze(ticker, name, idx, equity, halted):
    s = get_series(ticker)
    if not s: return None
    c, hh, ll, vv = s["c"], s["h"], s["l"], s["v"]
    price = c[-1]
    s5, s20, s50 = sma(c,5), sma(c,20), sma(c,50)
    r = rsi(c); a = atr_pct(hh, ll, c); av = sma(vv,20) or 0
    if None in (s5, s20, r, a): return None

    ret20 = (price/c[-21] - 1) * 100 if len(c) >= 21 else None
    rel = (ret20 - idx["ret20"]) if (ret20 is not None and idx["ret20"] is not None) else None
    turnover = av * price

    # ---- scoring (alpha-seeking) ----
    score = 40.0
    if s5 > s20: score += 12
    if price > s20: score += 8
    if s50 is not None and price > s50: score += 6
    if 45 <= r <= 70: score += 12
    elif r > 78: score -= 15
    elif r < 35: score -= 8
    if ATR_MIN <= a <= ATR_MAX: score += 8
    elif a > 6: score -= 12
    if turnover > MIN_TURNOVER: score += 6
    if rel is not None:
        if rel > 3: score += 14
        elif rel > 0: score += 8
        else: score -= 18          # underperforming the index = not alpha
    score = max(0, min(100, round(score, 1)))
    conf = "High" if score >= 80 else ("Med" if score >= SCORE_MIN else "Low")

    # ---- target matched to the 5-day horizon ----
    tgt_pct = fwd_pctl(c, hh)
    target  = round(price * (1 + tgt_pct/100.0), 2)
    mid     = round(price * (1 + tgt_pct/200.0), 2)
    stop    = round(price * (1 - a/100.0), 2)                 # 1.0 x ATR
    stop_dist      = max(price - stop, 0.01)
    eff_stop_dist  = stop_dist * GAP_FACTOR                   # gap-adjusted for sizing

    # ---- sizing: 1% risk, position caps ----
    risk_budget = equity * RISK_PCT / 100.0
    sh_risk = int(risk_budget // eff_stop_dist)
    cap_per_pos = equity / MAX_POSITIONS
    sh_cap  = int(cap_per_pos // price)
    shares  = max(min(sh_risk, sh_cap), 0)
    notional = round(shares * price, 2)
    fees = FEE_PER_ORDER * 2

    # ---- GROSS vs NET (reported separately, always) ----
    gross_gain = round(notional * tgt_pct / 100.0, 2)
    net_gain   = round(gross_gain - fees, 2)
    gross_loss = round(shares * eff_stop_dist, 2)             # gap-adjusted worst case
    net_loss   = round(gross_loss + fees, 2)
    fee_share  = (fees / gross_gain) if gross_gain > 0 else 9.99
    fee_drag   = round(fees / notional * 100, 2) if notional > 0 else None
    rr_net     = round(net_gain / net_loss, 2) if net_loss > 0 else 0

    # ---- ideal quantity to absorb fees (fees <=20% of expected gain) ----
    ideal_notional = (fees / FEE_MAX_SHARE) / (tgt_pct/100.0) if tgt_pct > 0 else None
    ideal_shares   = int(math.ceil(ideal_notional / price)) if ideal_notional else None

    gates = {
        "regime_ok": bool(idx["ok"]),
        "rel_strength_ok": bool(rel is not None and rel > 0),
        "score_ok": score >= SCORE_MIN,
        "atr_ok": ATR_MIN <= a <= ATR_MAX,
        "liquidity_ok": turnover > MIN_TURNOVER,
        "size_ok": shares >= 1 and notional >= MIN_POSITION,
        "fee_ok": fee_share <= FEE_MAX_SHARE,
        "rr_ok": rr_net >= 1.0,
        "not_halted": not halted,
    }
    worthwhile = all(gates.values())
    block = [k for k, v in gates.items() if not v]

    return {
        "ticker":ticker, "name":name, "price":round(price,2), "conf":conf, "score":score,
        "rsi":round(r,1), "atr_pct":round(a,2), "sma5":round(s5,2), "sma20":round(s20,2),
        "avgvol":int(av), "turnover":int(turnover),
        "ret20":round(ret20,2) if ret20 is not None else None,
        "rel_strength":round(rel,2) if rel is not None else None,
        "buy_low":round(price*0.997,2), "buy_high":round(price*1.004,2),
        "est_dayhigh":target, "est_dayend":mid, "stop":stop,
        "stop_pct":round(a,2), "eff_stop_pct":round(a*GAP_FACTOR,2),
        "tgt_move_pct":round(tgt_pct,2),
        "shares":shares, "cost":notional, "fee_drag_pct":fee_drag,
        "gross_gain_eur":gross_gain, "net_gain_eur":net_gain,
        "gross_loss_eur":gross_loss, "net_loss_eur":net_loss,
        "fees_eur":fees, "fee_share_of_gain_pct":round(fee_share*100,1),
        "rr_net":rr_net, "ideal_shares":ideal_shares,
        "ideal_notional":round(ideal_notional,2) if ideal_notional else None,
        "worthwhile":worthwhile, "blocked_by":block, "affordable":shares >= 1,
        "spark":[round(x,2) for x in c[-30:]],
        "target_by":(datetime.date.today()+datetime.timedelta(days=7)).isoformat(),
        "horizon_days":HORIZON_DAYS,
    }

def main():
    st = equity_state()
    equity = st["equity"]; halted = st["halted"]
    print("Swing Research Agent v3 (PAPER MODE) — equity EUR" + str(equity)
          + " peak EUR" + str(st["peak"]) + " drawdown " + str(st["dd_pct"]) + "%"
          + ("  *** CIRCUIT BREAKER ACTIVE — no actionable picks ***" if halted else ""))
    idx = index_context()

    picks = []
    with open("watchlist.csv") as f:
        for row in csv.DictReader(f):
            res = analyze(row["ticker"], row["name"], idx, equity, halted)
            if res: picks.append(res)

    picks.sort(key=lambda x: (x["worthwhile"], x["score"]), reverse=True)
    top = picks[:3]
    actionable = [p for p in top if p["worthwhile"]][:MAX_POSITIONS]
    for p in top:
        p["worthwhile"] = p in actionable

    now = datetime.datetime.now(datetime.timezone.utc).astimezone(
        datetime.timezone(datetime.timedelta(hours=1)))
    stamp = now.strftime("%Y-%m-%d %H:%M CET")

    with open("picks_today.json","w") as f:
        json.dump({"date":now.strftime("%Y-%m-%d"), "generated":stamp, "version":"v3",
                   "paper_mode":PAPER_MODE, "equity":equity, "peak":st["peak"],
                   "drawdown_pct":st["dd_pct"], "halted":halted,
                   "regime_ok":idx["ok"], "index_ret20":idx["ret20"],
                   "picks":top, "actionable_count":len(actionable)}, f, indent=2)

    with open("analysed_all.json","w") as f:
        slim=[{"ticker":p["ticker"],"name":p["name"],"price":p["price"],"conf":p["conf"],
               "score":p["score"],"atr_pct":p["atr_pct"],"rsi":p["rsi"],
               "worthwhile":p["worthwhile"],"tgt_move_pct":p["tgt_move_pct"],
               "shares":p["shares"],"spark":p.get("spark",[])} for p in picks]
        json.dump({"date":now.strftime("%Y-%m-%d"),"market":"DE","items":slim}, f, indent=2)

    print("[" + stamp + "] scanned " + str(len(picks)) + "; top " + str(len(top))
          + "; ACTIONABLE " + str(len(actionable)))
    for p in top:
        print("  " + p["ticker"] + " " + p["conf"] + " score " + str(p["score"])
              + " | EUR" + str(p["price"]) + " RS " + str(p["rel_strength"]) + "%")
        print("      target " + str(p["est_dayhigh"]) + " (+" + str(p["tgt_move_pct"])
              + "%) stop " + str(p["stop"]) + " (gap-adj -" + str(p["eff_stop_pct"]) + "%)")
        print("      size " + str(p["shares"]) + " sh = EUR" + str(p["cost"])
              + " | GROSS gain EUR" + str(p["gross_gain_eur"])
              + " - fees EUR" + str(p["fees_eur"])
              + " = NET EUR" + str(p["net_gain_eur"])
              + " (fees are " + str(p["fee_share_of_gain_pct"]) + "% of gain)")
        print("      worst case NET loss EUR" + str(p["net_loss_eur"])
              + " | net R:R " + str(p["rr_net"])
              + " | ideal qty to absorb fees: " + str(p["ideal_shares"]) + " sh")
        print("      actionable=" + str(p["worthwhile"])
              + ("" if p["worthwhile"] else "  blocked_by=" + ",".join(p["blocked_by"])))

if __name__ == "__main__":
    main()
