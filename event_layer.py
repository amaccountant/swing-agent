# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Malviyaarjun
# Event Layer (Drop 1) — does conditioning on EVENTS change the odds?
# Research/education. NOT financial advice.
#
# TESTS THREE THINGS, each with sample size reported:
#   A. Unconditional baseline: P(target before stop) on any random day.
#   B. Post-earnings drift (PEAD): same probability, but only for windows that
#      START the day after an earnings release, split by the day-0 reaction sign.
#   C. Overnight vs intraday decomposition: does close->open beat open->close?
#      (Large sample, robust, and free money if the asymmetry is real.)
#
# NO LOOK-AHEAD: every window uses only bars at or before its own start.
# HONESTY RULE: any result with n < 40 is labelled UNRELIABLE and must not be traded.

import json, math, statistics, datetime
import yfinance as yf

HORIZONS      = [1, 5, 20]
TARGET_PCTL   = 0.60
MIN_RELIABLE  = 40        # below this, do not draw conclusions
BREAKEVEN_REF = 0.43      # approx P(win) needed at ~0.8:1 payoff after costs

UNIVERSE = {
 "SAP.DE":"SAP","DTE.DE":"Deutsche Telekom","DBK.DE":"Deutsche Bank","CBK.DE":"Commerzbank",
 "IFX.DE":"Infineon","RWE.DE":"RWE","EOAN.DE":"E.ON","VOW3.DE":"Volkswagen pref",
 "BAYN.DE":"Bayer","BMW.DE":"BMW","MBG.DE":"Mercedes-Benz","ALV.DE":"Allianz",
 "BAS.DE":"BASF","SIE.DE":"Siemens","MUV2.DE":"Munich Re","ADS.DE":"Adidas",
 "DB1.DE":"Deutsche Boerse","AIR.DE":"Airbus","HEI.DE":"Heidelberg Materials",
 "RHM.DE":"Rheinmetall","ZAL.DE":"Zalando","LHA.DE":"Lufthansa"
}

def get_hist(t, period="5y"):
    try:
        h = yf.Ticker(t).history(period=period, interval="1d", auto_adjust=False)
        if h is None or len(h) == 0: return None
        h = h[["Open","High","Low","Close","Volume"]].dropna()
        h = h[h["Close"] > 0]
        if len(h) < 300: return None
        return {"d":[str(x.date()) for x in h.index],
                "o":[float(x) for x in h["Open"]], "h":[float(x) for x in h["High"]],
                "l":[float(x) for x in h["Low"]],  "c":[float(x) for x in h["Close"]]}
    except Exception as e:
        print("  [skip] " + t + ": " + str(e)); return None

def get_earnings_dates(t):
    """Historical earnings dates from yfinance. Returns list of 'YYYY-MM-DD'."""
    out = []
    try:
        tk = yf.Ticker(t)
        df = tk.get_earnings_dates(limit=40)
        if df is not None and len(df) > 0:
            for idx in df.index:
                try: out.append(str(idx.date()))
                except Exception: pass
    except Exception as e:
        print("    [earnings unavailable] " + t + ": " + str(e))
    return sorted(set(out))

def pctl(data, q):
    if not data: return 0.0
    s = sorted(data); k = (len(s)-1)*q
    lo = int(k); hi = min(lo+1, len(s)-1)
    return s[lo] + (s[hi]-s[lo])*(k-lo)

def atr_pct_at(h, l, c, i, n=14):
    if i < n + 1: return None
    trs = []
    for k in range(i-n+1, i+1):
        trs.append(max(h[k]-l[k], abs(h[k]-c[k-1]), abs(l[k]-c[k-1])))
    return (sum(trs)/n/c[i])*100 if c[i] > 0 else None

def target_pct_at(h, c, i, days, lookback=250):
    """60th percentile of best high within `days`, using ONLY bars before i."""
    ups = []
    start = max(1, i - lookback)
    for j in range(start, i - days + 1):
        base = c[j-1]
        if base > 0: ups.append(max(max(h[j:j+days])/base - 1, 0)*100)
    return pctl(ups, TARGET_PCTL) if ups else None

def first_passage(h, l, c, i, up_pct, dn_pct, days):
    """From bar i (decision close), does +up_pct hit before -dn_pct within `days`?
    Entry reference = close at i. Stop checked first (conservative)."""
    base = c[i]
    if base <= 0: return None
    tgt = base * (1 + up_pct/100.0)
    stp = base * (1 - dn_pct/100.0)
    end = min(i + 1 + days, len(c))
    for k in range(i+1, end):
        if l[k] <= stp: return "loss"
        if h[k] >= tgt: return "win"
    return "none"

def summarise(results, label, days, n_note=""):
    n = len(results)
    if n == 0:
        return {"label":label,"days":days,"n":0,"p_win":None,"reliable":False}
    w = results.count("win"); lo = results.count("loss"); no = results.count("none")
    p = w/n
    rel = n >= MIN_RELIABLE
    return {"label":label,"days":days,"n":n,
            "p_win":round(p,4),"p_loss":round(lo/n,4),"p_none":round(no/n,4),
            "reliable":rel,"beats_breakeven":bool(p > BREAKEVEN_REF),"note":n_note}

# ---------- TEST A + B ----------
def study_stock(t, name):
    hist = get_hist(t)
    if not hist: return None
    d, o, h, l, c = hist["d"], hist["o"], hist["h"], hist["l"], hist["c"]
    edates = get_earnings_dates(t)
    date_to_i = {dd: k for k, dd in enumerate(d)}

    # map each earnings date to the first trading bar on/after it
    ev_idx = []
    for ed in edates:
        if ed in date_to_i:
            ev_idx.append(date_to_i[ed])
        else:
            later = [k for k, dd in enumerate(d) if dd > ed]
            if later: ev_idx.append(later[0])
    ev_idx = sorted(set(i for i in ev_idx if 60 < i < len(c) - 25))

    out = {"ticker":t,"name":name,"n_earnings":len(ev_idx),"baseline":{},"pead_up":{},"pead_down":{}}

    for days in HORIZONS:
        base_res, up_res, dn_res = [], [], []
        # unconditional baseline: sample every 3rd bar to reduce overlap
        for i in range(60, len(c) - days - 1, 3):
            a = atr_pct_at(h, l, c, i)
            tp = target_pct_at(h, c, i, days)
            if a is None or tp is None or tp <= 0: continue
            r = first_passage(h, l, c, i, tp, a, days)
            if r: base_res.append(r)
        # event-conditioned: window starts the day AFTER the earnings bar
        for i in ev_idx:
            if i + days + 2 >= len(c): continue
            a = atr_pct_at(h, l, c, i)
            tp = target_pct_at(h, c, i, days)
            if a is None or tp is None or tp <= 0: continue
            reaction = (c[i]/c[i-1] - 1) * 100 if c[i-1] > 0 else 0
            r = first_passage(h, l, c, i, tp, a, days)
            if not r: continue
            if reaction > 0: up_res.append(r)
            else: dn_res.append(r)
        out["baseline"][str(days)] = summarise(base_res, "baseline", days)
        out["pead_up"][str(days)]  = summarise(up_res, "after positive reaction", days)
        out["pead_down"][str(days)]= summarise(dn_res, "after negative reaction", days)
    return out

# ---------- TEST C ----------
def overnight_study(t):
    hist = get_hist(t)
    if not hist: return None
    o, c = hist["o"], hist["c"]
    on, intra = [], []
    for i in range(1, len(c)):
        if c[i-1] > 0: on.append((o[i]/c[i-1] - 1) * 100)
        if o[i] > 0:  intra.append((c[i]/o[i] - 1) * 100)
    if len(on) < 200: return None
    def stats(x):
        m = statistics.mean(x); s = statistics.pstdev(x) if len(x) > 1 else 0
        return {"n":len(x), "mean_pct":round(m,4), "sd_pct":round(s,3),
                "total_pct":round(sum(x),2),
                "win_rate":round(sum(1 for v in x if v > 0)/len(x),4),
                "sharpe_daily":round(m/s,4) if s > 0 else 0}
    return {"ticker":t, "overnight":stats(on), "intraday":stats(intra)}

def pool(per_stock, key, days):
    n = w = 0
    for r in per_stock:
        s = r[key].get(str(days))
        if s and s["n"]:
            n += s["n"]; w += round(s["p_win"] * s["n"])
    if n == 0: return {"n":0,"p_win":None,"reliable":False}
    p = w/n
    return {"n":n, "p_win":round(p,4), "reliable":n >= MIN_RELIABLE,
            "beats_breakeven":bool(p > BREAKEVEN_REF)}

def main():
    per_stock, on_studies = [], []
    for t, name in UNIVERSE.items():
        print("studying " + t + " ...")
        r = study_stock(t, name)
        if r:
            per_stock.append(r)
            print("    earnings events usable: " + str(r["n_earnings"]))
        o = overnight_study(t)
        if o: on_studies.append(o)

    res = {"generated": datetime.datetime.now(datetime.timezone.utc).astimezone(
               datetime.timezone(datetime.timedelta(hours=1))).strftime("%Y-%m-%d %H:%M CET"),
           "config": {"horizons":HORIZONS, "target_percentile":TARGET_PCTL,
                      "min_reliable_n":MIN_RELIABLE, "breakeven_ref":BREAKEVEN_REF},
           "per_stock": per_stock, "pooled": {}, "overnight": {}}

    print("")
    print("================ POOLED RESULTS ================")
    print("break-even reference: P(win) must exceed " + str(round(BREAKEVEN_REF*100,1)) + "%")
    for days in HORIZONS:
        b  = pool(per_stock, "baseline", days)
        pu = pool(per_stock, "pead_up", days)
        pd = pool(per_stock, "pead_down", days)
        res["pooled"][str(days)] = {"baseline":b, "pead_up":pu, "pead_down":pd}
        lift = (round((pu["p_win"] - b["p_win"])*100, 2)
                if (pu["p_win"] is not None and b["p_win"] is not None) else None)
        res["pooled"][str(days)]["pead_up_lift_pp"] = lift
        print("")
        print("--- horizon " + str(days) + " day(s) ---")
        print("  baseline              P(win)=" + (str(round(b["p_win"]*100,1))+"%" if b["p_win"] is not None else "n/a")
              + "  n=" + str(b["n"]))
        print("  after POSITIVE surprise P(win)=" + (str(round(pu["p_win"]*100,1))+"%" if pu["p_win"] is not None else "n/a")
              + "  n=" + str(pu["n"]) + ("  [UNRELIABLE n<40]" if not pu["reliable"] else ""))
        print("  after NEGATIVE surprise P(win)=" + (str(round(pd["p_win"]*100,1))+"%" if pd["p_win"] is not None else "n/a")
              + "  n=" + str(pd["n"]) + ("  [UNRELIABLE n<40]" if not pd["reliable"] else ""))
        if lift is not None:
            print("  PEAD lift over baseline: " + ("%+.2f" % lift) + " percentage points")
        if pu["p_win"] is not None:
            print("  verdict: " + ("CLEARS break-even" if pu.get("beats_breakeven") else "BELOW break-even"))

    # overnight pooled
    if on_studies:
        def agg(k):
            tot = sum(s[k]["total_pct"] for s in on_studies)
            mn  = sum(s[k]["mean_pct"] for s in on_studies)/len(on_studies)
            wr  = sum(s[k]["win_rate"] for s in on_studies)/len(on_studies)
            sh  = sum(s[k]["sharpe_daily"] for s in on_studies)/len(on_studies)
            return {"avg_total_pct":round(tot/len(on_studies),2),
                    "avg_mean_pct":round(mn,4), "avg_win_rate":round(wr,4),
                    "avg_daily_sharpe":round(sh,4), "stocks":len(on_studies)}
        res["overnight"] = {"overnight":agg("overnight"), "intraday":agg("intraday"),
                            "per_stock":on_studies}
        print("")
        print("--- OVERNIGHT vs INTRADAY (per stock averages, " + str(len(on_studies)) + " stocks) ---")
        for k in ("overnight","intraday"):
            a = res["overnight"][k]
            print("  " + k.ljust(9) + " avg total " + str(a["avg_total_pct"]) + "%  mean/day "
                  + str(a["avg_mean_pct"]) + "%  win rate " + str(round(a["avg_win_rate"]*100,1))
                  + "%  daily Sharpe " + str(a["avg_daily_sharpe"]))
        d_on = res["overnight"]["overnight"]["avg_total_pct"]
        d_in = res["overnight"]["intraday"]["avg_total_pct"]
        print("  asymmetry: overnight minus intraday = " + ("%+.2f" % (d_on - d_in)) + " pp total")

    with open("event_results.json","w") as f:
        json.dump(res, f, indent=2)
    print("")
    print("event_results.json written")

if __name__ == "__main__":
    main()
