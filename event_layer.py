# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Malviyaarjun
# Swing Research Agent - Event Lab study (v2)
# Question: does an earnings release change the odds enough to pay for costs?
# Also measures where returns accrue: overnight (close->open) vs intraday.
#
# v2 corrections:
#  - Each horizon is judged on NET EXPECTANCY after costs. v1 used one fixed
#    43% threshold derived from 5-day geometry, which wrongly passed 1-day.
#  - Every result carries a t-statistic. A result counts only if it is
#    positive after costs, n >= 40 AND t >= 2.
#  - A stop-out on a gap fills at the opening price, not at the stop.
# Caveats: windows overlap and earnings cluster in the same weeks, so the true
# independent sample is smaller than n. Research/education only. NOT advice.

import json, math, statistics, datetime
import yfinance as yf

HORIZONS = [1, 5, 20]
TARGET_PCTL = 0.60
MIN_RELIABLE = 40
T_MIN = 2.0
FEE_PCT = 0.25              # EUR2 round trip on an EUR800 position
SLIP_PCT = 0.20             # 0.10% each side
COST_PCT = FEE_PCT + SLIP_PCT
OVERNIGHT_COST_PCT = 0.20   # EUR2/day on EUR2000 = 0.10%, plus ~0.10% spread

UNIVERSE = {
 "SAP.DE": "SAP", "DTE.DE": "Deutsche Telekom", "DBK.DE": "Deutsche Bank",
 "CBK.DE": "Commerzbank", "IFX.DE": "Infineon", "RWE.DE": "RWE", "EOAN.DE": "E.ON",
 "VOW3.DE": "Volkswagen pref", "BAYN.DE": "Bayer", "BMW.DE": "BMW",
 "MBG.DE": "Mercedes-Benz", "ALV.DE": "Allianz", "BAS.DE": "BASF", "SIE.DE": "Siemens",
 "MUV2.DE": "Munich Re", "ADS.DE": "Adidas", "DB1.DE": "Deutsche Boerse",
 "AIR.DE": "Airbus", "HEI.DE": "Heidelberg Materials", "RHM.DE": "Rheinmetall",
 "ZAL.DE": "Zalando", "LHA.DE": "Lufthansa"
}


def get_hist(t, period="5y"):
    try:
        h = yf.Ticker(t).history(period=period, interval="1d", auto_adjust=False)
        if h is None or len(h) == 0:
            return None
        h = h[["Open", "High", "Low", "Close"]].dropna()
        h = h[h["Close"] > 0]
        if len(h) < 300:
            return None
        return {"d": [str(x.date()) for x in h.index],
                "o": [float(x) for x in h["Open"]], "h": [float(x) for x in h["High"]],
                "l": [float(x) for x in h["Low"]], "c": [float(x) for x in h["Close"]]}
    except Exception as e:
        print("  [skip] " + t + ": " + str(e))
        return None


def get_earnings_dates(t):
    out = []
    try:
        df = yf.Ticker(t).get_earnings_dates(limit=40)
        if df is not None and len(df) > 0:
            for idx in df.index:
                try:
                    out.append(str(idx.date()))
                except Exception:
                    pass
    except Exception as e:
        print("    [earnings unavailable] " + t + ": " + str(e))
    return sorted(set(out))


def pctl(data, q):
    if not data:
        return 0.0
    s = sorted(data)
    k = (len(s) - 1) * q
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def atr_pct_at(h, l, c, i, n=14):
    if i < n + 1:
        return None
    trs = []
    for k in range(i - n + 1, i + 1):
        trs.append(max(h[k] - l[k], abs(h[k] - c[k - 1]), abs(l[k] - c[k - 1])))
    return (sum(trs) / n / c[i]) * 100 if c[i] > 0 else None


def target_pct_at(h, c, i, days, lookback=250):
    """60th pctl of best high within `days`, using ONLY windows ending before i."""
    ups = []
    for j in range(max(1, i - lookback), i - days + 1):
        base = c[j - 1]
        if base > 0:
            ups.append(max(max(h[j:j + days]) / base - 1, 0) * 100)
    return pctl(ups, TARGET_PCTL) if ups else None


def realised(o, h, l, c, i, up_pct, dn_pct, days):
    """Enter at the close of bar i. Returns (label, return %) over `days` bars."""
    base = c[i]
    if base <= 0 or i + days >= len(c):
        return None
    tgt = base * (1 + up_pct / 100.0)
    stp = base * (1 - dn_pct / 100.0)
    for k in range(i + 1, i + 1 + days):
        if l[k] <= stp:
            fill = o[k] if o[k] < stp else stp
            return ("loss", (fill / base - 1) * 100)
        if h[k] >= tgt:
            return ("win", up_pct)
    return ("none", (c[i + days] / base - 1) * 100)


def summarise(items):
    n = len(items)
    if n == 0:
        return {"n": 0, "verdict": "no data"}
    rets = [r for _, r in items]
    wins = [r for lab, r in items if lab == "win"]
    losses = [r for lab, r in items if lab == "loss"]
    gross = statistics.mean(rets)
    net = gross - COST_PCT
    sd = statistics.stdev(rets) if n > 1 else 0.0
    se = sd / math.sqrt(n) if n > 1 else 0.0
    t = net / se if se > 0 else 0.0
    avg_w = statistics.mean(wins) if wins else 0.0
    avg_l = abs(statistics.mean(losses)) if losses else 0.0
    be = (avg_l + COST_PCT) / (avg_w + avg_l) if (avg_w + avg_l) > 0 else None
    if n < MIN_RELIABLE:
        verdict = "insufficient sample"
    elif net > 0 and t >= T_MIN:
        verdict = "positive and significant"
    elif net > 0:
        verdict = "positive but not significant"
    else:
        verdict = "negative after costs"
    return {"n": n, "p_win": round(len(wins) / n, 4), "avg_win_pct": round(avg_w, 3),
            "avg_loss_pct": round(avg_l, 3), "mean_gross_pct": round(gross, 3),
            "mean_net_pct": round(net, 3), "t_stat": round(t, 2),
            "breakeven_p": round(be, 4) if be is not None else None, "verdict": verdict}


def study_stock(t):
    hist = get_hist(t)
    if not hist:
        return None
    d, o, h, l, c = hist["d"], hist["o"], hist["h"], hist["l"], hist["c"]
    events = set()
    for ed in get_earnings_dates(t):
        later = [k for k, dd in enumerate(d) if dd >= ed]
        if later:
            events.add(later[0])
    events = sorted(i for i in events if 60 < i < len(c) - 25)
    raw = {}
    for days in HORIZONS:
        base, pos, neg = [], [], []
        for i in range(60, len(c) - days - 1, 3):
            a = atr_pct_at(h, l, c, i)
            tp = target_pct_at(h, c, i, days)
            if not a or not tp or tp <= 0:
                continue
            r = realised(o, h, l, c, i, tp, a, days)
            if r:
                base.append(r)
        for i in events:
            a = atr_pct_at(h, l, c, i)
            tp = target_pct_at(h, c, i, days)
            if not a or not tp or tp <= 0:
                continue
            r = realised(o, h, l, c, i, tp, a, days)
            if not r:
                continue
            reaction = (c[i] / c[i - 1] - 1) * 100 if c[i - 1] > 0 else 0
            (pos if reaction > 0 else neg).append(r)
        raw[days] = {"baseline": base, "after_positive": pos, "after_negative": neg}
    return {"n_earnings": len(events), "raw": raw, "hist": hist}


def overnight(hist):
    o, c = hist["o"], hist["c"]
    on = [(o[i] / c[i - 1] - 1) * 100 for i in range(1, len(c)) if c[i - 1] > 0]
    it = [(c[i] / o[i] - 1) * 100 for i in range(1, len(c)) if o[i] > 0]
    if len(on) < 200:
        return None
    return {"overnight_mean": statistics.mean(on), "intraday_mean": statistics.mean(it),
            "overnight_total": sum(on), "intraday_total": sum(it),
            "overnight_win": sum(1 for x in on if x > 0) / len(on),
            "intraday_win": sum(1 for x in it if x > 0) / len(it)}


def main():
    pooled_raw = {d: {"baseline": [], "after_positive": [], "after_negative": []} for d in HORIZONS}
    per_stock, ovs = [], []
    for t, name in UNIVERSE.items():
        print("studying " + t + " ...")
        s = study_stock(t)
        if not s:
            continue
        row = {"ticker": t, "name": name, "n_earnings": s["n_earnings"]}
        for dd in HORIZONS:
            row["h" + str(dd)] = {}
            for g, items in s["raw"][dd].items():
                pooled_raw[dd][g].extend(items)
                row["h" + str(dd)][g] = summarise(items)
        per_stock.append(row)
        ov = overnight(s["hist"])
        if ov:
            ovs.append(ov)
        print("    earnings events usable: " + str(s["n_earnings"]))

    res = {"generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
           "version": "v2",
           "config": {"horizons": HORIZONS, "cost_pct_per_trade": COST_PCT,
                      "fee_pct": FEE_PCT, "slippage_pct": SLIP_PCT,
                      "min_reliable_n": MIN_RELIABLE, "t_min": T_MIN,
                      "overnight_cost_pct_per_day": OVERNIGHT_COST_PCT},
           "pooled": {}, "per_stock": per_stock, "overnight": {}}

    print("")
    print("================ POOLED RESULTS (cost " + str(COST_PCT) + "% per trade) ================")
    labels = {"baseline": "any day", "after_positive": "after + earnings",
              "after_negative": "after - earnings"}
    for dd in HORIZONS:
        res["pooled"][str(dd)] = {g: summarise(items) for g, items in pooled_raw[dd].items()}
        print("")
        print("--- " + str(dd) + "-day horizon ---")
        for g in ("baseline", "after_positive", "after_negative"):
            x = res["pooled"][str(dd)][g]
            if not x["n"]:
                print("  " + labels[g].ljust(17) + " no data")
                continue
            be = (str(round(x["breakeven_p"] * 100, 1)) + "%") if x["breakeven_p"] else "n/a"
            print("  " + labels[g].ljust(17) + " P(win) " + str(round(x["p_win"] * 100, 1))
                  + "% (needed " + be + ")  net " + ("%+.3f" % x["mean_net_pct"])
                  + "%/trade  t=" + str(x["t_stat"]) + "  n=" + str(x["n"])
                  + "  -> " + x["verdict"])

    if ovs:
        k = float(len(ovs))
        agg = {"stocks": len(ovs),
               "overnight_total_pct": round(sum(v["overnight_total"] for v in ovs) / k, 2),
               "intraday_total_pct": round(sum(v["intraday_total"] for v in ovs) / k, 2),
               "overnight_mean_pct": round(sum(v["overnight_mean"] for v in ovs) / k, 4),
               "intraday_mean_pct": round(sum(v["intraday_mean"] for v in ovs) / k, 4),
               "overnight_win_rate": round(sum(v["overnight_win"] for v in ovs) / k, 4),
               "intraday_win_rate": round(sum(v["intraday_win"] for v in ovs) / k, 4)}
        agg["overnight_net_after_cost_pct"] = round(agg["overnight_mean_pct"] - OVERNIGHT_COST_PCT, 4)
        res["overnight"] = agg
        print("")
        print("--- OVERNIGHT vs INTRADAY (" + str(len(ovs)) + " stocks) ---")
        print("  overnight: total " + str(agg["overnight_total_pct"]) + "%  mean/day "
              + str(agg["overnight_mean_pct"]) + "%")
        print("  intraday:  total " + str(agg["intraday_total_pct"]) + "%  mean/day "
              + str(agg["intraday_mean_pct"]) + "%")
        print("  capturing overnight costs ~" + str(OVERNIGHT_COST_PCT)
              + "%/day -> net " + str(agg["overnight_net_after_cost_pct"]) + "%/day")

    with open("event_results.json", "w") as f:
        json.dump(res, f, indent=2)
    print("")
    print("event_results.json written")


if __name__ == "__main__":
    main()
