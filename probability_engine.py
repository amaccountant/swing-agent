# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Malviyaarjun
# Swing Research Agent - Probability Engine v4.1 (Germany, XETRA)
# RESEARCH MODE: estimates the probability that a stock touches its target
# before its stop within 5 trading sessions. It does NOT issue trade calls.
# Research/education only. NOT financial advice. Data ~15-min delayed.
#
# Changes from v4:
#  1. RESEARCH_MODE - nothing is marked actionable. Every scored pick becomes a
#     paper "probe" that track_review.py resolves and scores for calibration.
#  2. Monte Carlo: Student-t draws rescaled to unit variance (df=4 has variance
#     2, which inflated simulated volatility by ~41%).
#  3. Monte Carlo: paths continue after touching target/stop, so the 5/50/95
#     percentile range is no longer censored at the stop.
#  4. GARCH(1,1) uses variance targeting instead of a fixed constant.
#  5. Records the date of the last complete price bar, so the tracker starts
#     on the first session AFTER the signal.
#  6. Ignores today's incomplete bar if run during market hours.

import csv, json, math, os, random, datetime
import yfinance as yf

ENGINE_VERSION   = "v4.1"
RESEARCH_MODE    = True
PAPER_CAPITAL    = 2000.0
RISK_PCT         = 2.0
MAX_POSITIONS    = 2
MIN_POSITION     = 500.0
FEE_PER_ORDER    = 1.0
GAP_FACTOR       = 1.8
HORIZON_DAYS     = 5
MC_PATHS         = 4000
T_DF             = 4
MIN_SAMPLE       = 80
ATR_MIN, ATR_MAX = 1.0, 6.0
MIN_TURNOVER     = 2000000.0
MAX_DD_PCT       = 15.0
TOP_N            = 4
INDEX            = "^GDAXI"
STATUS_TEXT      = ("Research mode: no validated edge. Probabilities are tracked on "
                    "paper to measure calibration. Not a recommendation to trade.")
random.seed(42)


def berlin_now():
    try:
        from zoneinfo import ZoneInfo
        return datetime.datetime.now(ZoneInfo("Europe/Berlin"))
    except Exception:
        return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=1)))


def sma(x, n):
    return sum(x[-n:]) / n if len(x) >= n else None


def stdev(x):
    if len(x) < 2:
        return 0.0
    m = sum(x) / len(x)
    return math.sqrt(sum((v - m) ** 2 for v in x) / (len(x) - 1))


def rsi(c, n=14):
    if len(c) < n + 1:
        return None
    g = l = 0.0
    for k in range(-n, 0):
        ch = c[k] - c[k - 1]
        g += max(ch, 0)
        l += max(-ch, 0)
    if l == 0:
        return 100.0
    return 100 - (100 / (1 + (g / n) / (l / n)))


def atr_pct(h, lo, c, n=14):
    if len(c) < n + 1:
        return None
    trs = []
    for k in range(-n, 0):
        trs.append(max(h[k] - lo[k], abs(h[k] - c[k - 1]), abs(lo[k] - c[k - 1])))
    return (sum(trs) / n / c[-1]) * 100 if c[-1] else None


def pctl(data, q):
    if not data:
        return 0.0
    s = sorted(data)
    k = (len(s) - 1) * q
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def add_trading_days(date_str, n):
    d = datetime.date.fromisoformat(date_str)
    added = 0
    while added < n:
        d += datetime.timedelta(days=1)
        if d.weekday() < 5:
            added += 1
    return d.isoformat()


def garch_sigma(rets):
    """GARCH(1,1) with variance targeting. Returns next-day sigma (decimal)."""
    if len(rets) < 30:
        return stdev(rets) if rets else 0.01
    alpha, beta = 0.10, 0.85
    long_var = stdev(rets) ** 2
    omega = long_var * (1 - alpha - beta)
    var = long_var
    for r in rets:
        var = omega + alpha * r * r + beta * var
    return math.sqrt(max(var, 1e-10))


def t_draw():
    """Student-t draw rescaled to unit variance: fat tails, correct size."""
    z = random.gauss(0, 1)
    chi = sum(random.gauss(0, 1) ** 2 for _ in range(T_DF))
    t = z / math.sqrt(chi / T_DF) if chi > 0 else z
    return t * math.sqrt((T_DF - 2) / T_DF)


def monte_carlo(price, gap_sd, intra_sd, scale, up_pct, dn_pct, days):
    tgt = price * (1 + up_pct / 100.0)
    stp = price * (1 - dn_pct / 100.0)
    win = loss = 0
    finals = []
    for _ in range(MC_PATHS):
        p = price
        res = None
        for _d in range(days):
            p_open = p * (1 + t_draw() * gap_sd * scale)
            p_close = p_open * (1 + t_draw() * intra_sd * scale)
            wick = abs(t_draw()) * intra_sd * scale * 0.5
            day_hi = max(p_open, p_close) * (1 + wick)
            day_lo = min(p_open, p_close) * (1 - wick)
            if res is None:
                if day_lo <= stp:
                    res = "loss"          # stop checked first (conservative)
                elif day_hi >= tgt:
                    res = "win"
            p = p_close
        if res == "win":
            win += 1
        elif res == "loss":
            loss += 1
        finals.append(p)
    finals.sort()
    n = float(MC_PATHS)
    return {"p_win": win / n, "p_loss": loss / n,
            "p05": round(finals[int(n * 0.05)], 2),
            "p50": round(finals[int(n * 0.50)], 2),
            "p95": round(finals[int(n * 0.95)], 2)}


def empirical_first_passage(c, h, l, up_pct, dn_pct, days):
    """Share of historical windows where +up_pct was touched before -dn_pct."""
    win = loss = none = 0
    for j in range(1, len(c) - days):
        base = c[j - 1]
        if base <= 0:
            continue
        tgt = base * (1 + up_pct / 100.0)
        stp = base * (1 - dn_pct / 100.0)
        res = None
        for k in range(j, j + days):
            if l[k] <= stp:
                res = "loss"
                break
            if h[k] >= tgt:
                res = "win"
                break
        if res == "win":
            win += 1
        elif res == "loss":
            loss += 1
        else:
            none += 1
    n = win + loss + none
    if n == 0:
        return None, None, 0
    return win / n, loss / n, n


def get_series(ticker, period="2y"):
    try:
        h = yf.Ticker(ticker).history(period=period, interval="1d", auto_adjust=False)
        if h is None or len(h) == 0:
            print("    [skip] " + ticker + ": no data")
            return None
        h = h[["Open", "High", "Low", "Close", "Volume"]].dropna()
        h = h[h["Close"] > 0]
        s = {"d": [str(x.date()) for x in h.index],
             "o": [float(x) for x in h["Open"]], "h": [float(x) for x in h["High"]],
             "l": [float(x) for x in h["Low"]], "c": [float(x) for x in h["Close"]],
             "v": [float(x) for x in h["Volume"]]}
        now = berlin_now()
        if s["d"] and s["d"][-1] == now.date().isoformat() and (now.hour, now.minute) < (17, 45):
            for k in s:
                s[k] = s[k][:-1]          # drop today's incomplete bar
        if len(s["c"]) < 150:
            print("    [skip] " + ticker + ": only " + str(len(s["c"])) + " rows")
            return None
        return s
    except Exception as e:
        print("    [error] " + ticker + ": " + str(e))
        return None


def index_context():
    s = get_series(INDEX)
    if not s:
        print("  [warn] index unavailable - market filters disabled")
        return {"regime_ok": True, "ret20": None}
    c = s["c"]
    s200 = sma(c, 200)
    ret20 = (c[-1] / c[-21] - 1) * 100 if len(c) >= 21 else None
    above = s200 is not None and c[-1] > s200
    rising = ret20 is not None and ret20 > 0
    print("  DAX " + str(round(c[-1], 1)) + " | above 200-day: " + str(above)
          + " | 20-day return: " + (str(round(ret20, 2)) + "%" if ret20 is not None else "n/a"))
    return {"regime_ok": above and rising, "ret20": ret20}


def equity_state():
    st = {"equity": PAPER_CAPITAL, "peak": PAPER_CAPITAL}
    if os.path.exists("equity_state.json"):
        try:
            with open("equity_state.json") as f:
                st.update(json.load(f))
        except Exception:
            pass
    peak = max(st.get("peak", PAPER_CAPITAL), st.get("equity", PAPER_CAPITAL))
    dd = (peak - st["equity"]) / peak * 100 if peak > 0 else 0.0
    return st["equity"], round(dd, 2), dd >= MAX_DD_PCT


def analyze(ticker, name, idx, equity, halted):
    s = get_series(ticker)
    if not s:
        return None
    o, h, l, c, v = s["o"], s["h"], s["l"], s["c"], s["v"]
    price = c[-1]
    a = atr_pct(h, l, c)
    r = rsi(c)
    av = sma(v, 20) or 0
    s5, s20 = sma(c, 5), sma(c, 20)
    if None in (a, r, s5, s20) or a <= 0:
        return None
    turnover = av * price

    rets = [c[i] / c[i - 1] - 1 for i in range(1, len(c))]
    gaps = [o[i] / c[i - 1] - 1 for i in range(1, len(c)) if c[i - 1] > 0]
    intra = [c[i] / o[i] - 1 for i in range(1, len(c)) if o[i] > 0]
    gap_sd, intra_sd = stdev(gaps[-250:]), stdev(intra[-250:])
    sigma = garch_sigma(rets[-250:])
    hist_sd = math.sqrt(gap_sd ** 2 + intra_sd ** 2)
    scale = min(max(sigma / hist_sd, 0.5), 2.0) if hist_sd > 0 else 1.0

    ret20 = (price / c[-21] - 1) * 100 if len(c) >= 21 else None
    rel = (ret20 - idx["ret20"]) if (ret20 is not None and idx["ret20"] is not None) else None

    ups = [max(max(h[j:j + HORIZON_DAYS]) / c[j - 1] - 1, 0) * 100
           for j in range(1, len(c) - HORIZON_DAYS) if c[j - 1] > 0]
    up_pct = pctl(ups, 0.60)
    dn_pct = a
    if up_pct <= 0:
        return None

    e_win, e_loss, n_sample = empirical_first_passage(c, h, l, up_pct, dn_pct, HORIZON_DAYS)
    mc = monte_carlo(price, gap_sd, intra_sd, scale, up_pct, dn_pct, HORIZON_DAYS)
    if e_win is None:
        w_emp = 0.0
        p_win, p_loss = mc["p_win"], mc["p_loss"]
    else:
        w_emp = min(n_sample / 300.0, 0.70)
        p_win = w_emp * e_win + (1 - w_emp) * mc["p_win"]
        p_loss = w_emp * e_loss + (1 - w_emp) * mc["p_loss"]
    p_none = max(1 - p_win - p_loss, 0.0)

    stop = round(price * (1 - dn_pct / 100.0), 2)
    target = round(price * (1 + up_pct / 100.0), 2)
    eff_stop_dist = (price - stop) * GAP_FACTOR
    risk_budget = equity * RISK_PCT / 100.0
    sh_risk = int(risk_budget // eff_stop_dist) if eff_stop_dist > 0 else 0
    sh_cap = int((equity / MAX_POSITIONS) // price)
    shares = max(min(sh_risk, sh_cap), 0)
    notional = round(shares * price, 2)
    fees = FEE_PER_ORDER * 2
    gross_gain = round(notional * up_pct / 100.0, 2)
    gross_loss = round(shares * eff_stop_dist, 2)
    net_gain = round(gross_gain - fees, 2)
    net_loss = round(gross_loss + fees, 2)
    expectancy = (round(p_win * net_gain - p_loss * net_loss - p_none * fees, 2)
                  if shares >= 1 else None)
    breakeven_p = (round((gross_loss + fees) / (gross_gain + gross_loss), 4)
                   if (gross_gain + gross_loss) > 0 else None)

    gates = {
        "market_rising": bool(idx["regime_ok"]),
        "beats_index": bool(rel is not None and rel > 0),
        "volatility_in_range": ATR_MIN <= a <= ATR_MAX,
        "liquid": turnover > MIN_TURNOVER,
        "enough_history": n_sample >= MIN_SAMPLE,
        "position_size_ok": shares >= 1 and notional >= MIN_POSITION,
        "positive_expectancy": expectancy is not None and expectancy > 0,
        "drawdown_ok": not halted,
    }
    signal_bar = s["d"][-1]
    return {
        "ticker": ticker, "name": name, "price": round(price, 2),
        "signal_bar": signal_bar,
        "p_win": round(p_win, 4), "p_loss": round(p_loss, 4), "p_none": round(p_none, 4),
        "p_win_history": round(e_win, 4) if e_win is not None else None,
        "p_win_simulation": round(mc["p_win"], 4), "history_windows": n_sample,
        "breakeven_p": breakeven_p,
        "conf": "High" if p_win >= 0.55 else ("Med" if p_win >= 0.45 else "Low"),
        "score": round(p_win * 100, 1),
        "rsi": round(r, 1), "atr_pct": round(a, 2), "sma5": round(s5, 2), "sma20": round(s20, 2),
        "sigma_daily_pct": round(sigma * 100, 2),
        "gap_sd_pct": round(gap_sd * 100, 2), "intra_sd_pct": round(intra_sd * 100, 2),
        "rel_strength": round(rel, 2) if rel is not None else None,
        "buy_low": round(price * 0.997, 2), "buy_high": round(price * 1.004, 2),
        "est_dayhigh": target, "est_dayend": round(price * (1 + up_pct / 200.0), 2),
        "stop": stop, "tgt_move_pct": round(up_pct, 2), "stop_pct": round(dn_pct, 2),
        "sim_p05": mc["p05"], "sim_p50": mc["p50"], "sim_p95": mc["p95"],
        "shares": shares, "cost": notional, "fees_eur": fees,
        "gross_gain_eur": gross_gain, "gross_loss_eur": gross_loss,
        "net_gain_eur": net_gain, "net_loss_eur": net_loss,
        "expectancy_eur": expectancy,
        "gates": gates, "gates_passed": all(gates.values()),
        "blocked_by": [k for k, ok in gates.items() if not ok],
        "would_trade": False, "worthwhile": False,
        "spark": [round(x, 2) for x in c[-30:]],
        "target_by": add_trading_days(signal_bar, HORIZON_DAYS),
        "horizon_days": HORIZON_DAYS,
    }


def main():
    equity, dd, halted = equity_state()
    now = berlin_now()
    stamp = now.strftime("%Y-%m-%d %H:%M %Z")
    print("Probability Engine " + ENGINE_VERSION + " | research mode: " + str(RESEARCH_MODE)
          + " | paper equity EUR" + str(round(equity, 2)) + " | drawdown " + str(dd) + "%")
    idx = index_context()

    picks = []
    with open("watchlist.csv") as f:
        for row in csv.DictReader(f):
            res = analyze(row["ticker"], row["name"], idx, equity, halted)
            if res:
                picks.append(res)
    picks.sort(key=lambda x: x["expectancy_eur"] if x["expectancy_eur"] is not None else -1e9,
               reverse=True)
    top = picks[:TOP_N]
    count = 0
    for p in top:
        if p["gates_passed"] and count < MAX_POSITIONS:
            p["would_trade"] = True
            count += 1
        p["worthwhile"] = p["would_trade"] and not RESEARCH_MODE

    with open("picks_today.json", "w") as f:
        json.dump({"date": now.date().isoformat(), "generated": stamp,
                   "version": ENGINE_VERSION, "research_mode": RESEARCH_MODE,
                   "status": STATUS_TEXT, "paper_equity": equity, "drawdown_pct": dd,
                   "market_ok": idx["regime_ok"], "index_ret20": idx["ret20"],
                   "picks": top,
                   "actionable_count": sum(1 for p in top if p["worthwhile"])}, f, indent=2)

    with open("analysed_all.json", "w") as f:
        slim = [{"ticker": p["ticker"], "name": p["name"], "price": p["price"],
                 "conf": p["conf"], "score": p["score"], "atr_pct": p["atr_pct"],
                 "rsi": p["rsi"], "worthwhile": p["worthwhile"],
                 "tgt_move_pct": p["tgt_move_pct"], "shares": p["shares"],
                 "spark": p["spark"]} for p in picks]
        json.dump({"date": now.date().isoformat(), "market": "DE", "items": slim}, f, indent=2)

    print("[" + stamp + "] scored " + str(len(picks)) + " stocks; tracking top "
          + str(len(top)) + " as paper probes")
    for p in top:
        needed = (str(round(p["breakeven_p"] * 100, 1)) + "%") if p["breakeven_p"] else "n/a"
        hist = (str(round(p["p_win_history"] * 100, 1)) + "%") if p["p_win_history"] is not None else "n/a"
        print("")
        print("  " + p["ticker"] + " " + p["name"] + "  EUR" + str(p["price"])
              + "  (last bar " + p["signal_bar"] + ")")
        print("    P(win) " + str(round(p["p_win"] * 100, 1)) + "%   needed " + needed
              + "   [history " + hist + " on " + str(p["history_windows"])
              + " windows | simulation " + str(round(p["p_win_simulation"] * 100, 1)) + "%]")
        print("    target " + str(p["est_dayhigh"]) + " (+" + str(p["tgt_move_pct"]) + "%)  stop "
              + str(p["stop"]) + " (-" + str(p["stop_pct"]) + "%)  by " + p["target_by"])
        print("    simulated price after 5 sessions: 5% " + str(p["sim_p05"]) + " | median "
              + str(p["sim_p50"]) + " | 95% " + str(p["sim_p95"]))
        print("    size " + str(p["shares"]) + " sh = EUR" + str(p["cost"]) + " | gross +"
              + str(p["gross_gain_eur"]) + " / -" + str(p["gross_loss_eur"]) + " | fees "
              + str(p["fees_eur"]) + " | expectancy EUR" + str(p["expectancy_eur"]))
        print("    would trade: " + ("YES (paper only)" if p["would_trade"] else "NO")
              + ("" if p["would_trade"] else "  blocked by: " + ", ".join(p["blocked_by"])))


if __name__ == "__main__":
    main()
