# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Malviyaarjun
# backtest.py — rigorous backtest of the Swing Agent rules. Original implementation.
#
# HONEST DESIGN CHOICES (anti-self-deception):
#   * Signals use ONLY bars up to and including day t  -> no look-ahead.
#   * Entry = NEXT day's OPEN, worsened by slippage.
#   * Stop is checked BEFORE target on the same bar (conservative).
#   * Gap-through-stop fills at the OPEN (worse than the stop), not at the stop.
#   * Whole shares only; one position at a time per market; real broker costs.
#   * Exit at close of day MAX_HOLD if neither stop nor target is touched.
#
# Backtests can still flatter a strategy. Past results NEVER guarantee the future.

import json, math, datetime
import yfinance as yf

LOOKBACK    = "2y"
WARMUP      = 60     # bars required before the first signal
MAX_HOLD    = 3      # exit at close of day 3 (your rule); hard cap is 5 days
SLIP_PCT    = 0.10   # slippage each side, %
TARGET_PCTL = 0.60   # target = 60th pctl of historical high-above-prior-close

DE_UNIVERSE = {
 "SAP.DE":"SAP","DTE.DE":"Deutsche Telekom","DBK.DE":"Deutsche Bank","CBK.DE":"Commerzbank",
 "LHA.DE":"Lufthansa","IFX.DE":"Infineon","RWE.DE":"RWE","EOAN.DE":"E.ON","VOW3.DE":"VW pref",
 "BAYN.DE":"Bayer","BMW.DE":"BMW","MBG.DE":"Mercedes-Benz","ALV.DE":"Allianz","BAS.DE":"BASF",
 "SIE.DE":"Siemens","MUV2.DE":"Munich Re","ADS.DE":"Adidas","HEN3.DE":"Henkel","FRE.DE":"Fresenius",
 "CON.DE":"Continental","ZAL.DE":"Zalando","HFG.DE":"HelloFresh","SHL.DE":"Siemens Healthineers",
 "P911.DE":"Porsche AG","1COV.DE":"Covestro","RHM.DE":"Rheinmetall","HEI.DE":"Heidelberg Materials",
 "SY1.DE":"Symrise","EVK.DE":"Evonik","LXS.DE":"Lanxess","PUM.DE":"Puma","TKA.DE":"ThyssenKrupp",
 "SDF.DE":"K+S","FNTN.DE":"Freenet","NEM.DE":"Nemetschek","AIR.DE":"Airbus","DHER.DE":"Delivery Hero"
}
IN_UNIVERSE = {
 "RELIANCE.NS":"Reliance","TCS.NS":"TCS","INFY.NS":"Infosys","HDFCBANK.NS":"HDFC Bank",
 "ICICIBANK.NS":"ICICI Bank","SBIN.NS":"SBI","TATAMOTORS.NS":"Tata Motors","AXISBANK.NS":"Axis Bank",
 "LT.NS":"L&T","ITC.NS":"ITC","TATASTEEL.NS":"Tata Steel","HINDALCO.NS":"Hindalco",
 "BAJFINANCE.NS":"Bajaj Finance","ADANIENT.NS":"Adani Ent","WIPRO.NS":"Wipro","MARUTI.NS":"Maruti",
 "SUNPHARMA.NS":"Sun Pharma","TITAN.NS":"Titan","ONGC.NS":"ONGC","COALINDIA.NS":"Coal India",
 "JSWSTEEL.NS":"JSW Steel","POWERGRID.NS":"Power Grid","NTPC.NS":"NTPC","BPCL.NS":"BPCL",
 "TECHM.NS":"Tech Mahindra","HCLTECH.NS":"HCL Tech","GRASIM.NS":"Grasim","VEDL.NS":"Vedanta",
 "ADANIPORTS.NS":"Adani Ports","TATAPOWER.NS":"Tata Power","IOC.NS":"IOC","GAIL.NS":"GAIL",
 "SAIL.NS":"SAIL","PNB.NS":"PNB","BANKBARODA.NS":"Bank of Baroda","ASHOKLEY.NS":"Ashok Leyland"
}

MARKETS = {
 "DE": {"uni":DE_UNIVERSE, "capital":200.0,   "fee_kind":"flat", "fee":1.0,  "min_move":3.0, "cur":"EUR"},
 "IN": {"uni":IN_UNIVERSE, "capital":20000.0, "fee_kind":"pct",  "fee":0.35, "min_move":1.5, "cur":"INR"},
}
STRATEGIES = ["baseline","momentum","meanrev","breakout"]
HIST = {}

def sma(x, n):
    return sum(x[-n:]) / n if len(x) >= n else None

def rsi(c, n=14):
    if len(c) < n + 1: return None
    g = l = 0.0
    for k in range(-n, 0):
        ch = c[k] - c[k-1]; g += max(ch, 0); l += max(-ch, 0)
    if l == 0: return 100.0
    rs = (g / n) / (l / n)
    return 100 - (100 / (1 + rs))

def atr_pct(h, lo, c, n=14):
    if len(c) < n + 1: return None
    trs = []
    for k in range(-n, 0):
        trs.append(max(h[k]-lo[k], abs(h[k]-c[k-1]), abs(lo[k]-c[k-1])))
    return (sum(trs) / n / c[-1]) * 100 if c[-1] else None

def pctl(data, q):
    if not data: return 0.0
    s = sorted(data); k = (len(s) - 1) * q
    lo = int(k); hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)

def get_hist(t):
    try:
        h = yf.Ticker(t).history(period=LOOKBACK, interval="1d", auto_adjust=False)
        if h is None or len(h) == 0:
            print("  [skip] " + t + ": no data"); return None
        h = h[["Open","High","Low","Close","Volume"]].dropna()
        h = h[h["Close"] > 0]
        if len(h) < WARMUP + 20:
            print("  [skip] " + t + ": only " + str(len(h)) + " bars"); return None
        return {"d":[str(x.date()) for x in h.index],
                "o":[float(x) for x in h["Open"]], "h":[float(x) for x in h["High"]],
                "l":[float(x) for x in h["Low"]],  "c":[float(x) for x in h["Close"]],
                "v":[float(x) for x in h["Volume"]]}
    except Exception as e:
        print("  [skip] " + t + ": " + str(e)); return None

def evaluate(strategy, hist, i, min_move):
    """Signal on bar i using ONLY data[0..i]. Returns dict or None."""
    c = hist["c"][:i+1]; hi = hist["h"][:i+1]; lo = hist["l"][:i+1]; v = hist["v"][:i+1]
    price = c[-1]
    s5, s20, s50 = sma(c,5), sma(c,20), sma(c,50)
    r = rsi(c); a = atr_pct(hi, lo, c); av = sma(v,20) or 0
    if None in (s5, s20, r, a): return None

    ok = False; score = 50.0
    if strategy == "baseline":
        score = 50.0
        score += 15 if s5 > s20 else -10
        if price > s20: score += 8
        if 45 <= r <= 68: score += 12
        elif r > 75: score -= 12
        elif r < 35: score -= 6
        if 1.2 <= a <= 4.5: score += 8
        elif a > 7: score -= 10
        if av > 300000: score += 7
        ok = score >= 60
    elif strategy == "momentum":
        ok = (s5 > s20) and (price > s20) and (50 <= r <= 72)
        score = 60 + min(a, 5) * 4 + (8 if av > 300000 else 0)
    elif strategy == "meanrev":
        ok = (s50 is not None) and (price > s50) and (r < 38)
        score = 60 + (40 - min(r, 40)) + (5 if av > 300000 else 0)
    elif strategy == "breakout":
        if len(hi) >= 21:
            ok = (price >= max(hi[-21:-1])) and (s5 > s20)
            score = 60 + min(a, 5) * 5
        else:
            ok = False
    if not ok: return None

    ups = []
    for j in range(1, len(c)):
        ups.append(max(hi[j] / c[j-1] - 1, 0) * 100)
    tgt_pct = pctl(ups, TARGET_PCTL)
    if tgt_pct < min_move: return None   # cost-aware "worthwhile" filter

    return {"score": round(score,1), "tgt_pct": round(tgt_pct,2),
            "target": price * (1 + tgt_pct/100),
            "stop":   price * (1 - (a/100) * 1.1),
            "atr": round(a,2), "ref_close": price}

def simulate(strategy, mk):
    cfg = MARKETS[mk]
    slip = SLIP_PCT / 100.0
    cands = []
    for t in cfg["uni"]:
        h = HIST.get(t)
        if not h: continue
        n = len(h["c"])
        for i in range(WARMUP, n - 1):
            sig = evaluate(strategy, h, i, cfg["min_move"])
            if not sig: continue
            fwd = []
            for j in range(i + 1, min(i + 1 + MAX_HOLD, n)):
                fwd.append((h["d"][j], h["o"][j], h["h"][j], h["l"][j], h["c"][j]))
            if not fwd: continue
            cands.append({"sd": h["d"][i], "t": t, "sig": sig, "fwd": fwd})

    cands.sort(key=lambda x: (x["sd"], -x["sig"]["score"]))
    equity = cfg["capital"]; trades = []; curve = []; busy_until = None

    for cd in cands:
        if busy_until and cd["sd"] <= busy_until:
            continue
        sig = cd["sig"]; fwd = cd["fwd"]
        entry = fwd[0][1] * (1 + slip)                 # next open, worsened
        if entry <= 0: continue
        if cfg["fee_kind"] == "flat":
            usable = max(equity - cfg["fee"] * 2, 0) * 0.99
        else:
            usable = equity * 0.98
        shares = int(usable // entry)
        if shares < 1: continue
        notional = shares * entry
        costs = cfg["fee"] * 2 if cfg["fee_kind"] == "flat" else notional * cfg["fee"] / 100.0

        ex = None; reason = ""; days = 0
        for k, (d, o, hh, ll, cc) in enumerate(fwd):
            days = k + 1
            if ll <= sig["stop"]:                       # stop checked FIRST
                ex = (o if o < sig["stop"] else sig["stop"]) * (1 - slip)
                reason = "stop"; exit_date = d; break
            if hh >= sig["target"]:
                ex = (o if o > sig["target"] else sig["target"]) * (1 - slip)
                reason = "target"; exit_date = d; break
            if k == len(fwd) - 1:
                ex = cc * (1 - slip); reason = "time"; exit_date = d
        if ex is None: continue

        pnl = (ex - entry) * shares - costs
        equity += pnl
        trades.append({"t": cd["t"], "in": fwd[0][0], "out": exit_date, "why": reason,
                       "sh": shares, "entry": round(entry,2), "exit": round(ex,2),
                       "pnl": round(pnl,2),
                       "ret_pct": round(pnl / notional * 100, 2) if notional else 0,
                       "days": days})
        curve.append({"d": exit_date, "v": round(equity,2)})
        busy_until = exit_date

    return metrics(cfg, trades, curve)

def metrics(cfg, trades, curve):
    start = cfg["capital"]
    out = {"trades_n": len(trades), "start_equity": start, "cur": cfg["cur"],
           "equity": curve[-400:], "trades": trades[-30:]}
    if not trades:
        out.update({"win_rate":0,"total_return_pct":0,"final_equity":start,"sharpe":0,
                    "max_dd_pct":0,"profit_factor":0,"avg_win_pct":0,"avg_loss_pct":0,
                    "expectancy_pct":0,"avg_hold_days":0})
        return out
    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    gw = sum(t["pnl"] for t in wins); gl = abs(sum(t["pnl"] for t in losses))
    vals = [start] + [p["v"] for p in curve]
    rets = []
    for k in range(1, len(vals)):
        if vals[k-1] > 0: rets.append(vals[k]/vals[k-1] - 1)
    mean = sum(rets)/len(rets) if rets else 0
    var = sum((x-mean)**2 for x in rets)/(len(rets)-1) if len(rets) > 1 else 0
    sd = math.sqrt(var)
    try:
        d0 = datetime.date.fromisoformat(trades[0]["in"])
        d1 = datetime.date.fromisoformat(trades[-1]["out"])
        years = max((d1 - d0).days / 365.25, 0.25)
    except Exception:
        years = 1.0
    tpy = len(trades) / years
    sharpe = (mean / sd) * math.sqrt(tpy) if sd > 0 else 0
    peak = vals[0]; mdd = 0.0
    for v in vals:
        peak = max(peak, v)
        if peak > 0: mdd = max(mdd, (peak - v) / peak * 100)
    final = vals[-1]
    out.update({
        "win_rate": round(100*len(wins)/len(trades), 1),
        "avg_win_pct": round(sum(t["ret_pct"] for t in wins)/len(wins), 2) if wins else 0,
        "avg_loss_pct": round(sum(t["ret_pct"] for t in losses)/len(losses), 2) if losses else 0,
        "profit_factor": round(gw/gl, 2) if gl > 0 else (999 if gw > 0 else 0),
        "expectancy_pct": round(sum(t["ret_pct"] for t in trades)/len(trades), 2),
        "total_return_pct": round((final/start - 1)*100, 2),
        "final_equity": round(final, 2),
        "max_dd_pct": round(mdd, 2),
        "sharpe": round(sharpe, 2),
        "avg_hold_days": round(sum(t["days"] for t in trades)/len(trades), 2),
        "trades_per_year": round(tpy, 1),
    })
    return out

def benchmark(mk):
    cfg = MARKETS[mk]; rs = []
    for t in cfg["uni"]:
        h = HIST.get(t)
        if not h or len(h["c"]) < WARMUP + 2: continue
        a = h["c"][WARMUP]; b = h["c"][-1]
        if a > 0: rs.append((b/a - 1) * 100)
    return round(sum(rs)/len(rs), 2) if rs else 0

def main():
    for mk in MARKETS:
        for t in MARKETS[mk]["uni"]:
            if t not in HIST:
                HIST[t] = get_hist(t)
    res = {"generated": datetime.datetime.now(datetime.timezone.utc).astimezone(
               datetime.timezone(datetime.timedelta(hours=1))).strftime("%Y-%m-%d %H:%M CET"),
           "config": {"lookback": LOOKBACK, "max_hold_days": MAX_HOLD,
                      "slippage_pct_each_side": SLIP_PCT, "target_percentile": TARGET_PCTL,
                      "entry": "next day open", "stop_priority": "stop before target"},
           "markets": {}}
    for mk in MARKETS:
        res["markets"][mk] = {"benchmark_pct": benchmark(mk), "strategies": {}}
        for st in STRATEGIES:
            m = simulate(st, mk)
            res["markets"][mk]["strategies"][st] = m
            print(mk + "/" + st + ": trades=" + str(m["trades_n"]) +
                  " win%=" + str(m.get("win_rate")) + " ret%=" + str(m.get("total_return_pct")) +
                  " sharpe=" + str(m.get("sharpe")) + " maxDD%=" + str(m.get("max_dd_pct")))
        print(mk + " benchmark (avg stock buy&hold): " + str(res["markets"][mk]["benchmark_pct"]) + "%")
    with open("backtest_results.json", "w") as f:
        json.dump(res, f, indent=2)
    print("backtest_results.json written")

if __name__ == "__main__":
    main()
