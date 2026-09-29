# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Malviyaarjun
# Probability Engine v4 (Drop 1) — calibrated probability estimation, not price prediction.
# Research/education. NOT financial advice. Data ~15-min delayed, prior close.
#
# METHOD (each component has a measurable job):
#   1. Empirical first-passage: from this stock's own history, how often did
#      +target get touched BEFORE -stop within the horizon? Sample size reported.
#   2. GARCH(1,1) volatility forecast (Engle) — volatility IS partly forecastable
#      at short horizons; direction largely is not.
#   3. Monte Carlo: 4000 paths, Student-t fat tails, overnight gaps modelled
#      SEPARATELY from intraday range (gaps were the hidden killer in v1-v3).
#   4. Blended P(win) = empirical and Monte Carlo, weighted by sample confidence.
#   5. Expectancy gate: P(win)*net_gain > P(loss)*net_loss_gap_adjusted.
#   6. Every prediction logged for Brier scoring / reliability curves.
#
# NO LOOK-AHEAD: all statistics use bars strictly before the decision bar.

import csv, json, math, os, random, datetime
import yfinance as yf

PAPER_CAPITAL   = 2000.0
RISK_PCT        = 2.0      # v3.1 fix: 2% at EUR2000 (1% contradicted min position)
MAX_POSITIONS   = 2
MIN_POSITION    = 500.0    # v3.1 fix: EUR800 was unreachable at 1% risk
FEE_PER_ORDER   = 1.0
GAP_FACTOR      = 1.8      # empirical: stops slipped ~1.8-2x in your replay
HORIZON_DAYS    = 5
PARALLEL_HORIZON= 20       # measured and displayed only, not traded
MC_PATHS        = 4000
MIN_SAMPLE      = 80       # minimum historical windows for a trustworthy estimate
MIN_EXPECTANCY  = 0.0      # must be strictly positive after costs
ATR_MIN, ATR_MAX= 1.0, 6.0
MIN_TURNOVER    = 2000000.0
MAX_DD_PCT      = 15.0
INDEX           = "^GDAXI"
random.seed(42)            # reproducible runs

# ---------- basic statistics ----------
def sma(x, n):
    return sum(x[-n:]) / n if len(x) >= n else None

def stdev(x):
    if len(x) < 2: return 0.0
    m = sum(x) / len(x)
    return math.sqrt(sum((v - m) ** 2 for v in x) / (len(x) - 1))

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

# ---------- GARCH(1,1) ----------
def garch_forecast(rets):
    """Simple GARCH(1,1) with standard parameters. Returns next-day sigma (decimal)."""
    if len(rets) < 30:
        return stdev(rets) if rets else 0.01
    omega, alpha, beta = 0.000002, 0.10, 0.85
    var = stdev(rets) ** 2
    for r in rets:
        var = omega + alpha * (r ** 2) + beta * var
        if var <= 0: var = 1e-8
    return math.sqrt(var)

# ---------- gap vs intraday decomposition ----------
def decompose(o, h, l, c):
    """Split returns into overnight gaps and intraday moves — they behave differently."""
    gaps, intra = [], []
    for i in range(1, len(c)):
        if c[i-1] > 0:
            gaps.append(o[i]/c[i-1] - 1)
        if o[i] > 0:
            intra.append(c[i]/o[i] - 1)
    return gaps, intra

# ---------- 1. empirical first-passage ----------
def empirical_first_passage(c, h, l, up_pct, dn_pct, days):
    """How often did +up_pct get touched BEFORE -dn_pct within `days`?
    Uses only completed historical windows. Returns (p_win, p_loss, p_none, n)."""
    win = loss = none = 0
    for j in range(1, len(c) - days):
        base = c[j-1]
        if base <= 0: continue
        tgt = base * (1 + up_pct/100.0)
        stp = base * (1 - dn_pct/100.0)
        res = None
        for k in range(j, j + days):
            if l[k] <= stp: res = "loss"; break     # stop checked first (conservative)
            if h[k] >= tgt: res = "win"; break
        if res == "win": win += 1
        elif res == "loss": loss += 1
        else: none += 1
    n = win + loss + none
    if n == 0: return None, None, None, 0
    return win/n, loss/n, none/n, n

# ---------- 3. Monte Carlo with fat tails and gaps ----------
def student_t(df=4.0):
    """Student-t draw via normal/chi-square ratio — fat tails, unit-ish scale."""
    z = random.gauss(0, 1)
    chi = sum(random.gauss(0, 1) ** 2 for _ in range(int(df)))
    return z / math.sqrt(chi / df) if chi > 0 else z

def monte_carlo(price, sigma_day, gap_sd, intra_sd, up_pct, dn_pct, days, paths=MC_PATHS):
    tgt = price * (1 + up_pct/100.0)
    stp = price * (1 - dn_pct/100.0)
    win = loss = none = 0
    finals = []
    gap_share = gap_sd / (gap_sd + intra_sd) if (gap_sd + intra_sd) > 0 else 0.35
    for _ in range(paths):
        p = price; res = None
        for _d in range(days):
            # overnight gap (fat-tailed) then intraday path
            g = student_t() * sigma_day * gap_share * 0.9
            p_open = p * (1 + g)
            if p_open <= stp: res = "loss"; p = p_open; break
            if p_open >= tgt: res = "win"; p = p_open; break
            i_ret = student_t() * sigma_day * (1 - gap_share)
            p_close = p_open * (1 + i_ret)
            day_lo = min(p_open, p_close) * (1 - abs(student_t()) * sigma_day * 0.35)
            day_hi = max(p_open, p_close) * (1 + abs(student_t()) * sigma_day * 0.35)
            if day_lo <= stp: res = "loss"; p = stp; break
            if day_hi >= tgt: res = "win"; p = tgt; break
            p = p_close
        if res == "win": win += 1
        elif res == "loss": loss += 1
        else: none += 1
        finals.append(p)
    finals.sort()
    return {"p_win": win/paths, "p_loss": loss/paths, "p_none": none/paths,
            "p05": round(finals[int(paths*0.05)], 2),
            "p50": round(finals[int(paths*0.50)], 2),
            "p95": round(finals[int(paths*0.95)], 2)}

# ---------- data ----------
def get_series(ticker, period="2y"):
    try:
        h = yf.Ticker(ticker).history(period=period, interval="1d", auto_adjust=False)
        if h is None or len(h) == 0:
            print("    [skip] " + ticker + ": no data"); return None
        h = h[["Open","High","Low","Close","Volume"]].dropna()
        h = h[h["Close"] > 0]
        if len(h) < 150:
            print("    [skip] " + ticker + ": only " + str(len(h)) + " rows"); return None
        return {"o":[float(x) for x in h["Open"]], "h":[float(x) for x in h["High"]],
                "l":[float(x) for x in h["Low"]],  "c":[float(x) for x in h["Close"]],
                "v":[float(x) for x in h["Volume"]]}
    except Exception as e:
        print("    [error] " + ticker + ": " + str(e)); return None

def index_context():
    s = get_series(INDEX)
    if not s:
        print("  [warn] index unavailable — regime and RS disabled")
        return {"regime_ok": True, "ret20": None, "rising": True}
    c = s["c"]
    s200 = sma(c, 200)
    ret20 = (c[-1]/c[-21] - 1) * 100 if len(c) >= 21 else None
    above = (s200 is not None) and (c[-1] > s200)
    rising = (ret20 is not None and ret20 > 0)          # v3.1 fix: require actually rising
    print("  DAX: last=" + str(round(c[-1],1)) + " above200=" + str(above)
          + " ret20=" + (str(round(ret20,2)) + "%" if ret20 is not None else "n/a")
          + " rising=" + str(rising))
    return {"regime_ok": above and rising, "ret20": ret20, "rising": rising}

def equity_state():
    st = {"equity": PAPER_CAPITAL, "peak": PAPER_CAPITAL, "halted": False, "dd_pct": 0.0}
    if os.path.exists("equity_state.json"):
        try:
            with open("equity_state.json") as f: st.update(json.load(f))
        except Exception: pass
    st["peak"] = max(st.get("peak", PAPER_CAPITAL), st.get("equity", PAPER_CAPITAL))
    dd = (st["peak"] - st["equity"]) / st["peak"] * 100 if st["peak"] > 0 else 0.0
    st["dd_pct"] = round(dd, 2); st["halted"] = dd >= MAX_DD_PCT
    with open("equity_state.json", "w") as f: json.dump(st, f, indent=2)
    return st

# ---------- core analysis ----------
def analyze(ticker, name, idx, equity, halted):
    s = get_series(ticker)
    if not s: return None
    o, h, l, c, v = s["o"], s["h"], s["l"], s["c"], s["v"]
    price = c[-1]
    rets = [c[i]/c[i-1] - 1 for i in range(1, len(c))]
    a = atr_pct(h, l, c); r = rsi(c); av = sma(v, 20) or 0
    s20, s50 = sma(c, 20), sma(c, 50)
    if None in (a, r, s20): return None
    turnover = av * price

    sigma = garch_forecast(rets[-250:])
    gaps, intra = decompose(o, h, l, c)
    gap_sd, intra_sd = stdev(gaps[-250:]), stdev(intra[-250:])

    ret20 = (price/c[-21] - 1) * 100 if len(c) >= 21 else None
    rel = (ret20 - idx["ret20"]) if (ret20 is not None and idx["ret20"] is not None) else None

    # target from the SAME horizon we hold (v3 fix), stop from ATR
    up_pct = pctl([max(max(h[j:j+HORIZON_DAYS])/c[j-1] - 1, 0)*100
                   for j in range(1, len(c)-HORIZON_DAYS)], 0.60)
    dn_pct = a
    if up_pct <= 0: return None

    e_win, e_loss, e_none, n_sample = empirical_first_passage(c, h, l, up_pct, dn_pct, HORIZON_DAYS)
    mc = monte_carlo(price, sigma, gap_sd, intra_sd, up_pct, dn_pct, HORIZON_DAYS)

    # blend: trust empirical more as sample grows
    if e_win is None:
        p_win, p_loss, p_none = mc["p_win"], mc["p_loss"], mc["p_none"]; w_emp = 0.0
    else:
        w_emp = min(n_sample / 300.0, 0.70)
        p_win  = w_emp*e_win  + (1-w_emp)*mc["p_win"]
        p_loss = w_emp*e_loss + (1-w_emp)*mc["p_loss"]
        p_none = max(1 - p_win - p_loss, 0)

    # parallel 20-day read-out (display only)
    up20 = pctl([max(max(h[j:j+PARALLEL_HORIZON])/c[j-1] - 1, 0)*100
                 for j in range(1, len(c)-PARALLEL_HORIZON)], 0.60)
    e20w, e20l, _, n20 = empirical_first_passage(c, h, l, up20, dn_pct, PARALLEL_HORIZON)

    # sizing: 2% risk, gap-adjusted stop distance
    stop = round(price * (1 - dn_pct/100.0), 2)
    target = round(price * (1 + up_pct/100.0), 2)
    eff_stop_dist = (price - stop) * GAP_FACTOR
    if eff_stop_dist <= 0: return None
    risk_budget = equity * RISK_PCT / 100.0
    sh_risk = int(risk_budget // eff_stop_dist)
    sh_cap  = int((equity / MAX_POSITIONS) // price)
    shares  = max(min(sh_risk, sh_cap), 0)
    notional = round(shares * price, 2)
    fees = FEE_PER_ORDER * 2

    gross_gain = round(notional * up_pct/100.0, 2)
    net_gain   = round(gross_gain - fees, 2)
    gross_loss = round(shares * eff_stop_dist, 2)
    net_loss   = round(gross_loss + fees, 2)
    # "no touch" case: assume roughly flat exit, still pay fees
    expectancy = round(p_win*net_gain - p_loss*net_loss - p_none*fees, 2)
    exp_pct = round(expectancy/notional*100, 3) if notional > 0 else None
    fee_share = round(fees/gross_gain*100, 1) if gross_gain > 0 else 999.0

    # Kelly (quarter-Kelly cap), for reference only
    b = (net_gain/net_loss) if net_loss > 0 else 0
    kelly = ((p_win*b - p_loss)/b) if b > 0 else -1
    kelly_q = round(max(kelly, 0)/4*100, 2)

    gates = {
        "regime_ok": bool(idx["regime_ok"]),
        "rel_strength_ok": bool(rel is not None and rel > 0),
        "atr_ok": ATR_MIN <= a <= ATR_MAX,
        "liquidity_ok": turnover > MIN_TURNOVER,
        "sample_ok": n_sample >= MIN_SAMPLE,
        "size_ok": shares >= 1 and notional >= MIN_POSITION,
        "expectancy_ok": expectancy > MIN_EXPECTANCY,
        "not_halted": not halted,
    }
    worthwhile = all(gates.values())
    blocked = [k for k, val in gates.items() if not val]

    conf_score = round(p_win * 100, 1)
    conf = "High" if (worthwhile and p_win >= 0.55) else ("Med" if worthwhile else "Low")

    return {
        "ticker":ticker, "name":name, "price":round(price,2),
        "conf":conf, "score":conf_score, "p_win":round(p_win,4),
        "p_loss":round(p_loss,4), "p_none":round(p_none,4),
        "p_win_empirical":round(e_win,4) if e_win is not None else None,
        "p_win_montecarlo":round(mc["p_win"],4), "sample_n":n_sample,
        "emp_weight":round(w_emp,2),
        "sigma_daily_pct":round(sigma*100,2), "gap_sd_pct":round(gap_sd*100,2),
        "intra_sd_pct":round(intra_sd*100,2),
        "rsi":round(r,1), "atr_pct":round(a,2), "sma5":round(sma(c,5),2), "sma20":round(s20,2),
        "avgvol":int(av), "turnover":int(turnover),
        "ret20":round(ret20,2) if ret20 is not None else None,
        "rel_strength":round(rel,2) if rel is not None else None,
        "buy_low":round(price*0.997,2), "buy_high":round(price*1.004,2),
        "est_dayhigh":target, "est_dayend":round(price*(1+up_pct/200.0),2), "stop":stop,
        "tgt_move_pct":round(up_pct,2), "stop_pct":round(dn_pct,2),
        "eff_stop_pct":round(dn_pct*GAP_FACTOR,2),
        "mc_p05":mc["p05"], "mc_p50":mc["p50"], "mc_p95":mc["p95"],
        "shares":shares, "cost":notional,
        "fee_drag_pct":round(fees/notional*100,2) if notional > 0 else None,
        "fees_eur":fees, "gross_gain_eur":gross_gain, "net_gain_eur":net_gain,
        "gross_loss_eur":gross_loss, "net_loss_eur":net_loss,
        "fee_share_of_gain_pct":fee_share,
        "expectancy_eur":expectancy, "expectancy_pct":exp_pct,
        "kelly_quarter_pct":kelly_q,
        "h20_target_pct":round(up20,2),
        "h20_p_win":round(e20w,4) if e20w is not None else None, "h20_sample":n20,
        "worthwhile":worthwhile, "blocked_by":blocked, "affordable":shares >= 1,
        "spark":[round(x,2) for x in c[-30:]],
        "target_by":(datetime.date.today()+datetime.timedelta(days=7)).isoformat(),
        "horizon_days":HORIZON_DAYS,
    }

def log_calibration(picks, date):
    """Store every stated probability so we can Brier-score it later."""
    new = not os.path.exists("calibration_log.csv")
    with open("calibration_log.csv", "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["date","ticker","p_win_stated","p_win_empirical","p_win_montecarlo",
                        "sample_n","target","stop","entry_ref","expectancy_eur",
                        "actionable","outcome","resolved_on"])
        for p in picks:
            w.writerow([date, p["ticker"], p["p_win"], p["p_win_empirical"],
                        p["p_win_montecarlo"], p["sample_n"], p["est_dayhigh"], p["stop"],
                        p["price"], p["expectancy_eur"], p["worthwhile"], "", ""])

def main():
    st = equity_state()
    equity, halted = st["equity"], st["halted"]
    print("Probability Engine v4 (PAPER MODE) — equity EUR" + str(equity)
          + " peak EUR" + str(st["peak"]) + " dd " + str(st["dd_pct"]) + "%"
          + ("  *** CIRCUIT BREAKER ACTIVE ***" if halted else ""))
    idx = index_context()

    picks = []
    with open("watchlist.csv") as f:
        for row in csv.DictReader(f):
            res = analyze(row["ticker"], row["name"], idx, equity, halted)
            if res: picks.append(res)

    picks.sort(key=lambda x: (x["worthwhile"], x["expectancy_eur"]), reverse=True)
    top = picks[:4]
    actionable = [p for p in top if p["worthwhile"]][:MAX_POSITIONS]
    for p in top:
        p["worthwhile"] = p in actionable

    now = datetime.datetime.now(datetime.timezone.utc).astimezone(
        datetime.timezone(datetime.timedelta(hours=1)))
    stamp = now.strftime("%Y-%m-%d %H:%M CET")

    with open("picks_today.json","w") as f:
        json.dump({"date":now.strftime("%Y-%m-%d"), "generated":stamp, "version":"v4-drop1",
                   "paper_mode":True, "equity":equity, "peak":st["peak"],
                   "drawdown_pct":st["dd_pct"], "halted":halted,
                   "regime_ok":idx["regime_ok"], "index_ret20":idx["ret20"],
                   "picks":top, "actionable_count":len(actionable)}, f, indent=2)

    with open("analysed_all.json","w") as f:
        slim=[{"ticker":p["ticker"],"name":p["name"],"price":p["price"],"conf":p["conf"],
               "score":p["score"],"atr_pct":p["atr_pct"],"rsi":p["rsi"],
               "worthwhile":p["worthwhile"],"tgt_move_pct":p["tgt_move_pct"],
               "shares":p["shares"],"spark":p.get("spark",[])} for p in picks]
        json.dump({"date":now.strftime("%Y-%m-%d"),"market":"DE","items":slim}, f, indent=2)

    log_calibration(top, now.strftime("%Y-%m-%d"))

    print("[" + stamp + "] scanned " + str(len(picks)) + "; ACTIONABLE " + str(len(actionable)))
    for p in top:
        print("")
        print("  " + p["ticker"] + " (" + p["name"] + ")  EUR" + str(p["price"])
              + "  RS " + str(p["rel_strength"]) + "%")
        print("    P(win)=" + str(round(p["p_win"]*100,1)) + "%  [empirical "
              + (str(round(p["p_win_empirical"]*100,1)) + "%" if p["p_win_empirical"] is not None else "n/a")
              + " on " + str(p["sample_n"]) + " windows, MC "
              + str(round(p["p_win_montecarlo"]*100,1)) + "%, emp weight " + str(p["emp_weight"]) + "]")
        print("    P(loss)=" + str(round(p["p_loss"]*100,1)) + "%  P(neither)="
              + str(round(p["p_none"]*100,1)) + "%")
        print("    target " + str(p["est_dayhigh"]) + " (+" + str(p["tgt_move_pct"])
              + "%)  stop " + str(p["stop"]) + " (-" + str(p["stop_pct"])
              + "%, gap-adj -" + str(p["eff_stop_pct"]) + "%)")
        print("    GARCH sigma/day " + str(p["sigma_daily_pct"]) + "%  (gap "
              + str(p["gap_sd_pct"]) + "% / intraday " + str(p["intra_sd_pct"]) + "%)")
        print("    MC 5d range: EUR" + str(p["mc_p05"]) + " / " + str(p["mc_p50"])
              + " / " + str(p["mc_p95"]) + "  (5th / 50th / 95th pct)")
        print("    size " + str(p["shares"]) + " sh = EUR" + str(p["cost"])
              + " | GROSS +EUR" + str(p["gross_gain_eur"]) + " / -EUR" + str(p["gross_loss_eur"])
              + " | fees EUR" + str(p["fees_eur"]) + " (" + str(p["fee_share_of_gain_pct"]) + "% of gain)")
        print("    NET +EUR" + str(p["net_gain_eur"]) + " / -EUR" + str(p["net_loss_eur"]))
        print("    EXPECTANCY = EUR" + str(p["expectancy_eur"])
              + " (" + str(p["expectancy_pct"]) + "% of position)  quarter-Kelly "
              + str(p["kelly_quarter_pct"]) + "%")
        print("    [20-day read-out] target +" + str(p["h20_target_pct"]) + "%  P(win)="
              + (str(round(p["h20_p_win"]*100,1)) + "%" if p["h20_p_win"] is not None else "n/a")
              + " on " + str(p["h20_sample"]) + " windows")
        print("    VERDICT: " + ("TAKE" if p["worthwhile"] else "DECLINE")
              + ("" if p["worthwhile"] else "  blocked_by=" + ",".join(p["blocked_by"])))

if __name__ == "__main__":
    main()
