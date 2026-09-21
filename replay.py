# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Malviyaarjun
# replay.py — retrospective test of the CURRENT live rules.
#
# PART A: Re-grade the real picks already in performance_log.csv using the proper
#         5-trading-day horizon (instead of the old same-day verdict).
# PART B: Replay today's live scan rules across ~2 years of history, resolved
#         honestly: entry at NEXT day's open + slippage, stop checked before
#         target, expiry after 5 days, real broker costs.
# PART C: Compare the current 1-day-based target against a 5-day-horizon target,
#         to see whether aligning the target with the holding period helps.
#
# No look-ahead: every signal uses only bars up to and including the signal day.
# Known biases: universe = today's survivors; dividends ignored; one position at
# a time. A replay is a simulation, NOT a track record. NOT financial advice.

import csv, os, json, math, datetime
import yfinance as yf

SLIP      = 0.001    # 0.1% slippage each side
MAX_DAYS  = 5        # your maximum holding horizon
WARMUP    = 70
PCTL      = 0.60     # same percentile your live scan uses

DE_UNIVERSE = ["SAP.DE","DTE.DE","DBK.DE","CBK.DE","LHA.DE","IFX.DE","RWE.DE","EOAN.DE",
 "VOW3.DE","BAYN.DE","BMW.DE","MBG.DE","ALV.DE","BAS.DE","SIE.DE","MUV2.DE","ADS.DE",
 "HEN3.DE","FRE.DE","CON.DE","ZAL.DE","HFG.DE","SHL.DE","P911.DE","RHM.DE","HEI.DE",
 "SY1.DE","EVK.DE","LXS.DE","PUM.DE","TKA.DE","SDF.DE","FNTN.DE","NEM.DE","AIR.DE","DHER.DE"]

IN_UNIVERSE = ["RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS","ICICIBANK.NS","SBIN.NS",
 "AXISBANK.NS","LT.NS","ITC.NS","TATASTEEL.NS","HINDALCO.NS","BAJFINANCE.NS","ADANIENT.NS",
 "WIPRO.NS","MARUTI.NS","SUNPHARMA.NS","TITAN.NS","ONGC.NS","COALINDIA.NS","JSWSTEEL.NS",
 "POWERGRID.NS","NTPC.NS","BPCL.NS","TECHM.NS","HCLTECH.NS","GRASIM.NS","VEDL.NS",
 "ADANIPORTS.NS","TATAPOWER.NS","IOC.NS","GAIL.NS","SAIL.NS","PNB.NS","BANKBARODA.NS"]

MARKETS = {
 "DE": {"uni":DE_UNIVERSE,"cap":200.0,  "fee_kind":"flat","fee":1.0, "min_move":3.0,
        "cur":"EUR","atr_hi":4.0,"vol_min":300000},
 "IN": {"uni":IN_UNIVERSE,"cap":20000.0,"fee_kind":"pct", "fee":0.35,"min_move":1.5,
        "cur":"INR","atr_hi":4.5,"vol_min":500000},
}

HIST = {}

def get_hist(t):
    if t in HIST: return HIST[t]
    try:
        h = yf.Ticker(t).history(period="2y", interval="1d", auto_adjust=False)
        if h is None or len(h) == 0:
            HIST[t] = None; return None
        h = h[["Open","High","Low","Close","Volume"]].dropna()
        h = h[h["Close"] > 0]
        if len(h) < WARMUP + 10:
            HIST[t] = None; return None
        HIST[t] = {"d":[str(x.date()) for x in h.index],
                   "o":[float(x) for x in h["Open"]],"h":[float(x) for x in h["High"]],
                   "l":[float(x) for x in h["Low"]], "c":[float(x) for x in h["Close"]],
                   "v":[float(x) for x in h["Volume"]]}
        return HIST[t]
    except Exception as e:
        print("  [skip] " + t + ": " + str(e)); HIST[t] = None; return None

def sma(x, n): return sum(x[-n:])/n if len(x) >= n else None

def rsi(c, n=14):
    if len(c) < n+1: return None
    g = l = 0.0
    for k in range(-n, 0):
        ch = c[k]-c[k-1]; g += max(ch,0); l += max(-ch,0)
    if l == 0: return 100.0
    return 100 - (100/(1+(g/n)/(l/n)))

def atr_pct(h, lo, c, n=14):
    if len(c) < n+1: return None
    trs = []
    for k in range(-n, 0):
        trs.append(max(h[k]-lo[k], abs(h[k]-c[k-1]), abs(lo[k]-c[k-1])))
    return (sum(trs)/n/c[-1])*100 if c[-1] else None

def pctl(data, q):
    if not data: return 0.0
    s = sorted(data); k = (len(s)-1)*q
    lo = int(k); hi = min(lo+1, len(s)-1)
    return s[lo] + (s[hi]-s[lo])*(k-lo)

def fwd_pctl(hist, i, days, q=PCTL):
    """Percentile of the best high reached within `days` sessions after a close.
    Uses ONLY windows that finish at or before bar i -> no look-ahead."""
    c = hist["c"]; h = hist["h"]; ups = []
    j = 1
    while j + days <= i:
        base = c[j-1]
        mx = max(h[j:j+days])
        if base > 0: ups.append(max(mx/base - 1, 0)*100)
        j += 1
    return pctl(ups, q)

def signal(hist, i, cfg):
    """Replicates the live scan.py scoring for bar i."""
    c = hist["c"][:i+1]; hi = hist["h"][:i+1]; lo = hist["l"][:i+1]; v = hist["v"][:i+1]
    price = c[-1]
    s5, s20 = sma(c,5), sma(c,20)
    r = rsi(c); a = atr_pct(hi, lo, c); av = sma(v,20) or 0
    if None in (s5, s20, r, a): return None
    sc = 50.0
    sc += 15 if s5 > s20 else -10
    if price > s20: sc += 8
    if 45 <= r <= 68: sc += 12
    elif r > 75: sc -= 12
    elif r < 35: sc -= 6
    if 1.2 <= a <= cfg["atr_hi"]: sc += 8
    elif a > 6: sc -= 10
    if av > cfg["vol_min"]: sc += 7
    sc = max(0, min(100, sc))
    conf = "High" if sc >= 72 else ("Med" if sc >= 60 else "Low")
    return {"price":price,"score":round(sc,1),"conf":conf,"atr":a}

def resolve(hist, i, target, stop, cfg):
    """Entry next open + slippage; stop before target; expire after MAX_DAYS."""
    n = len(hist["c"])
    if i+1 >= n: return None
    entry = hist["o"][i+1]*(1+SLIP)
    if entry <= 0: return None
    if cfg["fee_kind"] == "flat":
        usable = max(cfg["cap"] - cfg["fee"]*2, 0)*0.95
    else:
        usable = cfg["cap"]*0.98
    shares = int(usable // entry)
    if shares < 1: return {"skip":"unaffordable"}
    notional = shares*entry
    fees = cfg["fee"]*2 if cfg["fee_kind"]=="flat" else notional*cfg["fee"]/100.0

    outcome = None; exit_px = None; held = 0; best = entry; worst = entry
    for k in range(i+1, min(i+1+MAX_DAYS, n)):
        held = k - i
        best = max(best, hist["h"][k]); worst = min(worst, hist["l"][k])
        if hist["l"][k] <= stop:
            o = hist["o"][k]
            exit_px = (o if o < stop else stop)*(1-SLIP); outcome = "STOP"; break
        if hist["h"][k] >= target:
            o = hist["o"][k]
            exit_px = (o if o > target else target)*(1-SLIP); outcome = "TARGET"; break
        if held >= MAX_DAYS or k == n-1:
            exit_px = hist["c"][k]*(1-SLIP); outcome = "EXPIRED"
    if outcome is None: return None
    gross = (exit_px/entry - 1)*100
    net = gross - (fees/notional*100 if notional else 0)
    return {"outcome":outcome,"held":held,"gross":round(gross,2),"net":round(net,2),
            "entry":round(entry,2),"exit":round(exit_px,2),"shares":shares,
            "mfe":round((best/entry-1)*100,2),"mae":round((worst/entry-1)*100,2),
            "pnl":round((exit_px-entry)*shares-fees,2),"notional":round(notional,2)}

# ---------------- PART A: re-grade real past picks ----------------
def part_a(logfile, market):
    cfg = MARKETS[market]
    if not os.path.exists(logfile):
        print("PART A (" + market + "): no " + logfile + " found — skipping.")
        return None
    seen = set(); picks = []
    with open(logfile) as f:
        for r in csv.DictReader(f):
            key = (r.get("date"), r.get("ticker"))
            if key in seen: continue
            seen.add(key)
            try:
                picks.append({"date":r.get("date"),"ticker":r.get("ticker"),
                              "target":float(r.get("predicted_dayhigh")),
                              "old":r.get("hit_miss","")})
            except Exception:
                pass
    if not picks:
        print("PART A (" + market + "): log had no usable rows."); return None

    res = {"TARGET":0,"STOP":0,"EXPIRED":0}; nets = []; rows = []
    for p in picks:
        h = get_hist(p["ticker"])
        if not h or p["date"] not in h["d"]:
            continue
        i = h["d"].index(p["date"])
        sg = signal(h, i, cfg)
        if not sg: continue
        stop = sg["price"]*(1 - (sg["atr"]/100)*1.1)   # same formula as live scan
        out = resolve(h, i, p["target"], stop, cfg)
        if not out or out.get("skip"): continue
        res[out["outcome"]] += 1; nets.append(out["net"])
        rows.append({"date":p["date"],"ticker":p["ticker"],"old_verdict":p["old"],
                     "new_outcome":out["outcome"],"days":out["held"],
                     "net_pct":out["net"],"best_pct":out["mfe"],"worst_pct":out["mae"]})

    n = len(nets)
    if n == 0:
        print("PART A (" + market + "): no rows could be re-graded."); return None
    avg = sum(nets)/n
    print("")
    print("=== PART A — " + market + ": your REAL past picks, re-graded over 5 days ===")
    print("  unique picks re-graded : " + str(n))
    print("  target reached         : " + str(res["TARGET"]) + "  (" + str(round(100*res["TARGET"]/n,1)) + "%)")
    print("  stopped out            : " + str(res["STOP"]))
    print("  expired (no verdict)   : " + str(res["EXPIRED"]))
    print("  average net per trade  : " + ("%+.2f" % avg) + "%  (after fees & slippage)")
    print("  sum of net returns     : " + ("%+.2f" % sum(nets)) + "%")
    for r in rows:
        print("   " + r["date"] + " " + r["ticker"] + ": old=" + str(r["old_verdict"]) +
              " -> new=" + r["new_outcome"] + " in " + str(r["days"]) + "d, net " +
              ("%+.2f" % r["net_pct"]) + "%, best " + ("%+.2f" % r["best_pct"]) + "%")
    return {"n":n,"counts":res,"avg_net":round(avg,2),"rows":rows}

# ---------------- PART B & C: replay current rules ----------------
def replay(market, horizon_target):
    cfg = MARKETS[market]
    cands = []
    for t in cfg["uni"]:
        h = get_hist(t)
        if not h: continue
        n = len(h["c"])
        for i in range(WARMUP, n-1):
            sg = signal(h, i, cfg)
            if not sg or sg["conf"] == "Low": continue
            days = MAX_DAYS if horizon_target else 1
            tpct = fwd_pctl(h, i, days)
            if tpct < cfg["min_move"]: continue          # live "worthwhile" hurdle
            target = sg["price"]*(1 + tpct/100.0)
            stop = sg["price"]*(1 - (sg["atr"]/100)*1.1)
            cands.append({"d":h["d"][i],"t":t,"i":i,"h":h,"target":target,
                          "stop":stop,"score":sg["score"],"tpct":tpct})
    cands.sort(key=lambda x: (x["d"], -x["score"]))

    equity = cfg["cap"]; busy = None
    res = {"TARGET":0,"STOP":0,"EXPIRED":0}; nets = []; trades = []
    for cd in cands:
        if busy and cd["d"] <= busy: continue
        out = resolve(cd["h"], cd["i"], cd["target"], cd["stop"], cfg)
        if not out or out.get("skip"): continue
        res[out["outcome"]] += 1; nets.append(out["net"])
        equity += out["pnl"]
        exit_i = min(cd["i"]+out["held"], len(cd["h"]["d"])-1)
        busy = cd["h"]["d"][exit_i]
        trades.append({"d":cd["d"],"t":cd["t"],"o":out["outcome"],"net":out["net"],
                       "days":out["held"],"tpct":round(cd["tpct"],2)})
    n = len(nets)
    label = "5-DAY-HORIZON target" if horizon_target else "CURRENT 1-day target"
    print("")
    print("=== " + market + " replay — " + label + " ===")
    if n == 0:
        print("  0 trades. The cost hurdle of " + str(cfg["min_move"]) +
              "% was never met by this target method. That itself is the finding.")
        return {"n":0,"label":label}
    wins = [x for x in nets if x > 0]; losses = [x for x in nets if x <= 0]
    gw = sum(wins); gl = abs(sum(losses))
    print("  trades                 : " + str(n))
    print("  target / stop / expired: " + str(res["TARGET"]) + " / " + str(res["STOP"]) + " / " + str(res["EXPIRED"]))
    print("  win rate (net > 0)     : " + str(round(100*len(wins)/n,1)) + "%")
    print("  avg net per trade      : " + ("%+.2f" % (sum(nets)/n)) + "%")
    print("  profit factor          : " + str(round(gw/gl,2) if gl > 0 else "n/a"))
    print("  equity " + cfg["cur"] + "          : " + str(round(cfg["cap"],2)) + " -> " + str(round(equity,2)) +
          "  (" + ("%+.2f" % ((equity/cfg["cap"]-1)*100)) + "%)")
    print("  avg hold (days)        : " + str(round(sum(t["days"] for t in trades)/n,2)))
    return {"n":n,"label":label,"counts":res,
            "win_rate":round(100*len(wins)/n,1),
            "avg_net":round(sum(nets)/n,2),
            "profit_factor":round(gw/gl,2) if gl > 0 else None,
            "final_equity":round(equity,2),
            "total_return_pct":round((equity/cfg["cap"]-1)*100,2),
            "trades":trades[-25:]}

def benchmark(market):
    cfg = MARKETS[market]; rs = []
    for t in cfg["uni"]:
        h = get_hist(t)
        if not h or len(h["c"]) < WARMUP+5: continue
        a = h["c"][WARMUP]; b = h["c"][-1]
        if a > 0: rs.append((b/a-1)*100)
    return round(sum(rs)/len(rs),2) if rs else 0

def main():
    out = {"generated": datetime.datetime.now(datetime.timezone.utc).astimezone(
               datetime.timezone(datetime.timedelta(hours=1))).strftime("%Y-%m-%d %H:%M CET"),
           "settings":{"max_days":MAX_DAYS,"slippage_each_side_pct":SLIP*100,
                       "percentile":PCTL,"entry":"next day open"},
           "markets":{}}
    for mk in MARKETS:
        print("")
        print("############ MARKET " + mk + " ############")
        a = part_a("performance_log.csv" if mk == "DE" else "performance_log_in.csv", mk)
        b = replay(mk, horizon_target=False)
        c = replay(mk, horizon_target=True)
        bm = benchmark(mk)
        print("")
        print("  buy & hold average stock: " + str(bm) + "%")
        out["markets"][mk] = {"regrade":a,"current_target":b,"horizon_target":c,"benchmark_pct":bm}
    with open("replay_results.json","w") as f:
        json.dump(out, f, indent=2)
    print("")
    print("replay_results.json written")

if __name__ == "__main__":
    main()
