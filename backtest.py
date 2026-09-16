# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Malviyaarjun
# backtest.py — Swing Agent backtest v2. Original implementation.
#
# ANTI-SELF-DECEPTION DESIGN:
#   * Signals use ONLY bars up to and including day t  -> no look-ahead.
#   * Entry = NEXT day's OPEN, worsened by slippage.
#   * Stop checked BEFORE target on the same bar (conservative).
#   * Gap through stop fills at the OPEN (worse than stop), not at the stop.
#   * Regime filter uses index data as-of the signal date only.
#   * Walk-forward: train window and unseen test window reported separately.
#   * Risk-based sizing; whole shares; one position at a time; real costs.
#
# A backtest is a simulation with known biases. Past results NEVER guarantee the future.

import json, math, bisect, datetime
import yfinance as yf

LOOKBACK      = "2y"
WARMUP        = 60
MAX_HOLD      = 5      # v2: 5-day cap (your hard maximum)
SLIP_PCT      = 0.10   # each side
R_TARGET      = 2.0    # v2: target = 2.0 x ATR
R_STOP        = 1.0    # v2: stop   = 1.0 x ATR  -> 2:1 reward:risk
RISK_PCT      = 2.0    # v2: risk at most 2% of equity per trade
MAX_COST_PCT  = 1.5    # v2: skip trade if round-trip costs exceed this % of position
ATR_MIN       = 1.0
ATR_MAX       = 6.0
TRAIN_FRAC    = 0.70   # walk-forward split

DE_UNIVERSE = {
 "SAP.DE":"SAP","DTE.DE":"Deutsche Telekom","DBK.DE":"Deutsche Bank","CBK.DE":"Commerzbank",
 "LHA.DE":"Lufthansa","IFX.DE":"Infineon","RWE.DE":"RWE","EOAN.DE":"E.ON","VOW3.DE":"VW pref",
 "BAYN.DE":"Bayer","BMW.DE":"BMW","MBG.DE":"Mercedes-Benz","ALV.DE":"Allianz","BAS.DE":"BASF",
 "SIE.DE":"Siemens","MUV2.DE":"Munich Re","ADS.DE":"Adidas","HEN3.DE":"Henkel","FRE.DE":"Fresenius",
 "CON.DE":"Continental","ZAL.DE":"Zalando","HFG.DE":"HelloFresh","SHL.DE":"Siemens Healthineers",
 "P911.DE":"Porsche AG","RHM.DE":"Rheinmetall","HEI.DE":"Heidelberg Materials","SY1.DE":"Symrise",
 "EVK.DE":"Evonik","LXS.DE":"Lanxess","PUM.DE":"Puma","TKA.DE":"ThyssenKrupp","SDF.DE":"K+S",
 "FNTN.DE":"Freenet","NEM.DE":"Nemetschek","AIR.DE":"Airbus","DHER.DE":"Delivery Hero"
}
IN_UNIVERSE = {
 "RELIANCE.NS":"Reliance","TCS.NS":"TCS","INFY.NS":"Infosys","HDFCBANK.NS":"HDFC Bank",
 "ICICIBANK.NS":"ICICI Bank","SBIN.NS":"SBI","AXISBANK.NS":"Axis Bank","LT.NS":"L&T","ITC.NS":"ITC",
 "TATASTEEL.NS":"Tata Steel","HINDALCO.NS":"Hindalco","BAJFINANCE.NS":"Bajaj Finance",
 "ADANIENT.NS":"Adani Ent","WIPRO.NS":"Wipro","MARUTI.NS":"Maruti","SUNPHARMA.NS":"Sun Pharma",
 "TITAN.NS":"Titan","ONGC.NS":"ONGC","COALINDIA.NS":"Coal India","JSWSTEEL.NS":"JSW Steel",
 "POWERGRID.NS":"Power Grid","NTPC.NS":"NTPC","BPCL.NS":"BPCL","TECHM.NS":"Tech Mahindra",
 "HCLTECH.NS":"HCL Tech","GRASIM.NS":"Grasim","VEDL.NS":"Vedanta","ADANIPORTS.NS":"Adani Ports",
 "TATAPOWER.NS":"Tata Power","IOC.NS":"IOC","GAIL.NS":"GAIL","SAIL.NS":"SAIL","PNB.NS":"PNB",
 "BANKBARODA.NS":"Bank of Baroda","ASHOKLEY.NS":"Ashok Leyland","M&M.NS":"M&M",
 "HEROMOTOCO.NS":"Hero MotoCorp","BAJAJ-AUTO.NS":"Bajaj Auto"
}

MARKETS = {
 "DE": {"uni":DE_UNIVERSE, "capital":200.0,   "fee_kind":"flat", "fee":1.0,
        "min_move":3.0, "cur":"EUR", "index":"^GDAXI", "min_turnover":2000000},
 "IN": {"uni":IN_UNIVERSE, "capital":20000.0, "fee_kind":"pct",  "fee":0.35,
        "min_move":1.5, "cur":"INR", "index":"^NSEI",  "min_turnover":100000000},
}
STRATEGIES = ["baseline","momentum","meanrev","breakout"]
HIST = {}
REGIME = {}

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

def build_regime(mk, sym):
    try:
        h = yf.Ticker(sym).history(period="4y", interval="1d", auto_adjust=False)
        h = h[["Close"]].dropna()
        d = [str(x.date()) for x in h.index]; c = [float(x) for x in h["Close"]]
        ok = []
        run = 0.0
        for k in range(len(c)):
            if k < 200:
                run += c[k]; ok.append(False)
            else:
                run += c[k] - c[k-200]
                ok.append(c[k] > run/200.0)
        REGIME[mk] = {"d": d, "ok": ok}
        print("regime " + mk + " (" + sym + "): " + str(len(d)) + " bars loaded")
    except Exception as e:
        print("regime fetch failed for " + mk + ": " + str(e))
        REGIME[mk] = None

def regime_ok(mk, date):
    r = REGIME.get(mk)
    if not r: return True          # unavailable -> do not block
    i = bisect.bisect_right(r["d"], date) - 1
    if i < 0: return False
    return r["ok"][i]

def evaluate(strategy, hist, i, cfg):
    c = hist["c"][:i+1]; hi = hist["h"][:i+1]; lo = hist["l"][:i+1]; v = hist["v"][:i+1]
    price = c[-1]
    s5, s20, s50 = sma(c,5), sma(c,20), sma(c,50)
    r = rsi(c); a = atr_pct(hi, lo, c); av = sma(v,20) or 0
    if None in (s5, s20, r, a): return None
    if a < ATR_MIN or a > ATR_MAX: return None
    if av * price < cfg["min_turnover"]: return None

    ok = False; score = 50.0
    if strategy == "baseline":
        score = 50.0
        score += 15 if s5 > s20 else -10
        if price > s20: score += 8
        if 45 <= r <= 68: score += 12
        elif r > 75: score -= 12
        elif r < 35: score -= 6
        if 1.2 <= a <= 4.5: score += 8
        ok = score >= 70                      # v2: stricter
    elif strategy == "momentum":
        ok = (s5 > s20) and (price > s20) and (52 <= r <= 70) and (s50 is not None and price > s50)
        score = 62 + min(a,5)*4
    elif strategy == "meanrev":
        ok = (s50 is not None) and (price > s50) and (r < 40) and (price > lo[-1])
        score = 62 + (40 - min(r,40))
    elif strategy == "breakout":
        if len(hi) >= 41:
            ok = (price >= max(hi[-41:-1])) and (s5 > s20)   # v2: 40-day breakout
            score = 64 + min(a,5)*4
        else:
            ok = False
    if not ok: return None

    tgt_pct = R_TARGET * a
    if tgt_pct < cfg["min_move"]: return None     # cost hurdle
    return {"score": round(score,1), "tgt_pct": round(tgt_pct,2), "atr": round(a,2),
            "target": price * (1 + R_TARGET*a/100.0),
            "stop":   price * (1 - R_STOP*a/100.0)}

def simulate(strategy, mk, d_start, d_end):
    cfg = MARKETS[mk]; slip = SLIP_PCT/100.0
    diag = {"blocked_regime":0, "skipped_size":0, "skipped_cost":0}
    cands = []
    for t in cfg["uni"]:
        h = HIST.get(t)
        if not h: continue
        n = len(h["c"])
        for i in range(WARMUP, n - 1):
            d = h["d"][i]
            if d < d_start or d > d_end: continue
            sig = evaluate(strategy, h, i, cfg)
            if not sig: continue
            if not regime_ok(mk, d):
                diag["blocked_regime"] += 1; continue
            fwd = []
            for j in range(i+1, min(i+1+MAX_HOLD, n)):
                fwd.append((h["d"][j], h["o"][j], h["h"][j], h["l"][j], h["c"][j]))
            if not fwd: continue
            cands.append({"sd": d, "t": t, "sig": sig, "fwd": fwd})

    cands.sort(key=lambda x: (x["sd"], -x["sig"]["score"]))
    equity = cfg["capital"]; trades = []; curve = []; busy_until = None

    for cd in cands:
        if busy_until and cd["sd"] <= busy_until: continue
        sig = cd["sig"]; fwd = cd["fwd"]
        entry = fwd[0][1] * (1 + slip)
        if entry <= 0: continue
        stop_p = sig["stop"]
        stop_dist = entry - stop_p
        if stop_dist <= 0: continue

        risk_budget = equity * RISK_PCT / 100.0
        sh_risk = int(risk_budget // stop_dist)
        usable = (max(equity - cfg["fee"]*2, 0) * 0.99) if cfg["fee_kind"]=="flat" else equity*0.98
        sh_aff = int(usable // entry)
        shares = min(sh_risk, sh_aff)
        if shares < 1:
            diag["skipped_size"] += 1; continue
        notional = shares * entry
        costs = cfg["fee"]*2 if cfg["fee_kind"]=="flat" else notional*cfg["fee"]/100.0
        if notional > 0 and (costs/notional*100.0) > MAX_COST_PCT:
            diag["skipped_cost"] += 1; continue

        ex = None; reason = ""; days = 0; exit_date = fwd[-1][0]
        for k, (d, o, hh, ll, cc) in enumerate(fwd):
            days = k + 1
            if ll <= stop_p:
                ex = (o if o < stop_p else stop_p) * (1 - slip); reason = "stop"; exit_date = d; break
            if hh >= sig["target"]:
                ex = (o if o > sig["target"] else sig["target"]) * (1 - slip); reason = "target"; exit_date = d; break
            if k == len(fwd) - 1:
                ex = cc * (1 - slip); reason = "time"; exit_date = d
        if ex is None: continue

        pnl = (ex - entry) * shares - costs
        equity += pnl
        trades.append({"t": cd["t"], "in": fwd[0][0], "out": exit_date, "why": reason,
                       "sh": shares, "entry": round(entry,2), "exit": round(ex,2),
                       "pnl": round(pnl,2),
                       "ret_pct": round(pnl/notional*100, 2) if notional else 0,
                       "days": days})
        curve.append({"d": exit_date, "v": round(equity,2)})
        busy_until = exit_date

    m = metrics(cfg, trades, curve)
    m["diag"] = diag
    return m

def metrics(cfg, trades, curve):
    start = cfg["capital"]
    out = {"trades_n": len(trades), "start_equity": start, "cur": cfg["cur"],
           "equity": curve[-400:], "trades": trades[-30:]}
    if not trades:
        out.update({"win_rate":0,"total_return_pct":0,"final_equity":start,"sharpe":0,
                    "max_dd_pct":0,"profit_factor":0,"avg_win_pct":0,"avg_loss_pct":0,
                    "expectancy_pct":0,"avg_hold_days":0,"trades_per_year":0})
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
        years = max((d1-d0).days/365.25, 0.25)
    except Exception:
        years = 1.0
    tpy = len(trades)/years
    sharpe = (mean/sd)*math.sqrt(tpy) if sd > 0 else 0
    peak = vals[0]; mdd = 0.0
    for v in vals:
        peak = max(peak, v)
        if peak > 0: mdd = max(mdd, (peak-v)/peak*100)
    final = vals[-1]
    out.update({
        "win_rate": round(100*len(wins)/len(trades),1),
        "avg_win_pct": round(sum(t["ret_pct"] for t in wins)/len(wins),2) if wins else 0,
        "avg_loss_pct": round(sum(t["ret_pct"] for t in losses)/len(losses),2) if losses else 0,
        "profit_factor": round(gw/gl,2) if gl > 0 else (999 if gw > 0 else 0),
        "expectancy_pct": round(sum(t["ret_pct"] for t in trades)/len(trades),2),
        "total_return_pct": round((final/start-1)*100,2),
        "final_equity": round(final,2),
        "max_dd_pct": round(mdd,2),
        "sharpe": round(sharpe,2),
        "avg_hold_days": round(sum(t["days"] for t in trades)/len(trades),2),
        "trades_per_year": round(tpy,1),
    })
    return out

def benchmark(mk, d_start, d_end):
    cfg = MARKETS[mk]; rs = []
    for t in cfg["uni"]:
        h = HIST.get(t)
        if not h: continue
        idx = [k for k,d in enumerate(h["d"]) if d_start <= d <= d_end]
        if len(idx) < 10: continue
        a = h["c"][idx[0]]; b = h["c"][idx[-1]]
        if a > 0: rs.append((b/a-1)*100)
    return round(sum(rs)/len(rs),2) if rs else 0

def date_span(mk):
    for t in MARKETS[mk]["uni"]:
        h = HIST.get(t)
        if h and len(h["d"]) > WARMUP + 20:
            ds = h["d"]
            split = ds[int(len(ds)*TRAIN_FRAC)]
            return ds[0], split, ds[-1]
    return "1900-01-01", "2000-01-01", "2100-01-01"

def slim(m):
    return {"trades_n":m["trades_n"],"win_rate":m["win_rate"],
            "total_return_pct":m["total_return_pct"],"profit_factor":m["profit_factor"],
            "sharpe":m["sharpe"],"max_dd_pct":m["max_dd_pct"],
            "expectancy_pct":m["expectancy_pct"]}

def main():
    for mk in MARKETS:
        build_regime(mk, MARKETS[mk]["index"])
        for t in MARKETS[mk]["uni"]:
            if t not in HIST: HIST[t] = get_hist(t)

    res = {"generated": datetime.datetime.now(datetime.timezone.utc).astimezone(
               datetime.timezone(datetime.timedelta(hours=1))).strftime("%Y-%m-%d %H:%M CET"),
           "version": "v2",
           "config": {"lookback":LOOKBACK,"max_hold_days":MAX_HOLD,
                      "slippage_pct_each_side":SLIP_PCT,"reward_atr":R_TARGET,"risk_atr":R_STOP,
                      "risk_pct_per_trade":RISK_PCT,"max_cost_pct":MAX_COST_PCT,
                      "entry":"next day open","regime":"index above 200-day average",
                      "walk_forward_train_frac":TRAIN_FRAC},
           "markets": {}}

    for mk in MARKETS:
        d0, dsplit, d1 = date_span(mk)
        res["markets"][mk] = {"benchmark_pct": benchmark(mk, d0, d1),
                              "benchmark_test_pct": benchmark(mk, dsplit, d1),
                              "split_date": dsplit, "strategies": {}}
        print("--- " + mk + " | full " + d0 + " to " + d1 + " | test starts " + dsplit)
        for st in STRATEGIES:
            full = simulate(st, mk, d0, d1)
            tr   = simulate(st, mk, d0, dsplit)
            te   = simulate(st, mk, dsplit, d1)
            full["train_summary"] = slim(tr)
            full["test_summary"]  = slim(te)
            res["markets"][mk]["strategies"][st] = full
            print(mk+"/"+st+" FULL: n="+str(full["trades_n"])+" win%="+str(full["win_rate"])
                  +" ret%="+str(full["total_return_pct"])+" PF="+str(full["profit_factor"])
                  +" sharpe="+str(full["sharpe"])+" DD%="+str(full["max_dd_pct"]))
            print("      TRAIN n="+str(tr["trades_n"])+" ret%="+str(tr["total_return_pct"])
                  +" PF="+str(tr["profit_factor"])+"  |  TEST n="+str(te["trades_n"])
                  +" ret%="+str(te["total_return_pct"])+" PF="+str(te["profit_factor"]))
            print("      diag full: "+str(full.get("diag")))
        print(mk+" benchmark full="+str(res["markets"][mk]["benchmark_pct"])
              +"%  test="+str(res["markets"][mk]["benchmark_test_pct"])+"%")

    with open("backtest_results.json","w") as f:
        json.dump(res, f, indent=2)
    print("backtest_results.json written (v2)")

if __name__ == "__main__":
    main()
