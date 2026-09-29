# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Malviyaarjun
# Swing Research Agent - Paper Tracker & Calibration Audit (v2)
#
# Every stock the engine scores is registered as a "probe" carrying its stated
# P(win). A probe is resolved ONLY when its target is touched, its stop is
# touched, or 5 trading sessions pass. Nothing is judged early.
#   probes_open.json          probes still inside their 5-session window
#   calibration_resolved.csv  one row per resolved probe
#   calibration_summary.json  Brier score, reliability table, paper P&L
#   strategy_memory.md        lessons, written only from resolved probes
#   equity_state.json         paper equity for probes the engine WOULD trade
# Research/education only. NOT financial advice.

import csv, json, os, datetime
import yfinance as yf

MAX_DAYS = 5
FEE_PER_ORDER = 1.0
PAPER_CAPITAL = 2000.0
MIN_FOR_VERDICT = 20
PICKS_FILE = "picks_today.json"
OPEN_FILE = "probes_open.json"
RESOLVED_FILE = "calibration_resolved.csv"
SUMMARY_FILE = "calibration_summary.json"
MEMORY_FILE = "strategy_memory.md"
EQUITY_FILE = "equity_state.json"
FIELDS = ["signal_bar", "resolved_on", "ticker", "name", "engine", "p_win_stated",
          "target", "stop", "entry", "exit", "outcome", "hit", "sessions",
          "gross_pct", "would_trade", "shares", "paper_pnl_eur"]


def berlin_now():
    try:
        from zoneinfo import ZoneInfo
        return datetime.datetime.now(ZoneInfo("Europe/Berlin"))
    except Exception:
        return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=1)))


def load(path, default):
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            return default
    return default


def save(path, obj):
    with open(path, "w") as f:
        json.dump(obj, f, indent=2)


def read_resolved():
    if not os.path.exists(RESOLVED_FILE):
        return []
    with open(RESOLVED_FILE) as f:
        return list(csv.DictReader(f))


def register():
    data = load(PICKS_FILE, {})
    book = load(OPEN_FILE, {"open": []})
    seen = set((p["signal_bar"], p["ticker"]) for p in book["open"])
    seen |= set((r["signal_bar"], r["ticker"]) for r in read_resolved())
    added = 0
    for p in data.get("picks", []):
        sb = p.get("signal_bar")
        if not sb or p.get("p_win") is None:
            continue                          # only probes from engine v4.1 onward
        key = (sb, p["ticker"])
        if key in seen:
            continue
        book["open"].append({"signal_bar": sb, "ticker": p["ticker"], "name": p["name"],
                             "engine": data.get("version", "?"), "p_win": p["p_win"],
                             "target": p["est_dayhigh"], "stop": p["stop"],
                             "shares": int(p.get("shares") or 0),
                             "would_trade": bool(p.get("would_trade"))})
        seen.add(key)
        added += 1
    save(OPEN_FILE, book)
    print("registered " + str(added) + " new probe(s); open probes: " + str(len(book["open"])))
    return book


def bars_after(ticker, signal_bar):
    try:
        h = yf.Ticker(ticker).history(period="3mo", interval="1d", auto_adjust=False)
        h = h[["Open", "High", "Low", "Close"]].dropna()
    except Exception as e:
        print("  [error] " + ticker + ": " + str(e))
        return None
    now = berlin_now()
    today = now.date().isoformat()
    out = []
    for idx, row in h.iterrows():
        d = str(idx.date())
        if d <= signal_bar:
            continue
        if d == today and (now.hour, now.minute) < (17, 45):
            continue                          # ignore today's incomplete bar
        out.append({"d": d, "o": float(row["Open"]), "h": float(row["High"]),
                    "l": float(row["Low"]), "c": float(row["Close"])})
    return out


def resolve(book):
    still, done = [], []
    for pos in book["open"]:
        bars = bars_after(pos["ticker"], pos["signal_bar"])
        if not bars:
            still.append(pos)
            continue
        entry = bars[0]["o"]
        outcome = exit_px = exit_day = None
        sessions = 0
        for k, b in enumerate(bars[:MAX_DAYS]):
            sessions = k + 1
            if b["l"] <= pos["stop"]:                        # stop checked first
                outcome, exit_day = "STOP", b["d"]
                exit_px = b["o"] if b["o"] < pos["stop"] else pos["stop"]
                break
            if b["h"] >= pos["target"]:
                outcome, exit_day, exit_px = "TARGET", b["d"], pos["target"]
                break
        if outcome is None:
            if len(bars) >= MAX_DAYS:
                last = bars[MAX_DAYS - 1]
                outcome, exit_day, exit_px, sessions = "EXPIRED", last["d"], last["c"], MAX_DAYS
            else:
                print("  " + pos["ticker"] + ": open, session " + str(len(bars)) + " of "
                      + str(MAX_DAYS) + " - no verdict yet")
                still.append(pos)
                continue
        pnl = ""
        if pos["would_trade"] and pos["shares"] >= 1:
            pnl = round((exit_px - entry) * pos["shares"] - 2 * FEE_PER_ORDER, 2)
        row = {"signal_bar": pos["signal_bar"], "resolved_on": exit_day,
               "ticker": pos["ticker"], "name": pos["name"], "engine": pos["engine"],
               "p_win_stated": pos["p_win"], "target": pos["target"], "stop": pos["stop"],
               "entry": round(entry, 2), "exit": round(exit_px, 2), "outcome": outcome,
               "hit": 1 if outcome == "TARGET" else 0, "sessions": sessions,
               "gross_pct": round((exit_px / entry - 1) * 100, 2) if entry > 0 else 0,
               "would_trade": pos["would_trade"], "shares": pos["shares"],
               "paper_pnl_eur": pnl}
        done.append(row)
        print("  " + pos["ticker"] + ": " + outcome + " after " + str(sessions)
              + " session(s), stated P(win) " + str(round(pos["p_win"] * 100, 1)) + "%")
    book["open"] = still
    save(OPEN_FILE, book)
    if done:
        new = not os.path.exists(RESOLVED_FILE)
        with open(RESOLVED_FILE, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            if new:
                w.writeheader()
            for r in done:
                w.writerow(r)
    return done


def update_equity(rows):
    st = load(EQUITY_FILE, {"equity": PAPER_CAPITAL, "peak": PAPER_CAPITAL})
    for r in rows:
        if r["paper_pnl_eur"] != "":
            st["equity"] = round(st["equity"] + float(r["paper_pnl_eur"]), 2)
            st["peak"] = max(st.get("peak", PAPER_CAPITAL), st["equity"])
    save(EQUITY_FILE, st)
    return st


def summarise(eq):
    rows = read_resolved()
    n = len(rows)
    out = {"updated": berlin_now().strftime("%Y-%m-%d %H:%M %Z"), "resolved": n,
           "min_for_verdict": MIN_FOR_VERDICT,
           "paper_equity": eq.get("equity"), "paper_peak": eq.get("peak")}
    if n == 0:
        out["verdict"] = "No resolved probes yet."
        save(SUMMARY_FILE, out)
        return out
    ps = [float(r["p_win_stated"]) for r in rows]
    hs = [int(r["hit"]) for r in rows]
    brier = sum((p - o) ** 2 for p, o in zip(ps, hs)) / n
    base = sum(hs) / n
    ref = base * (1 - base)
    skill = (1 - brier / ref) if ref > 0 else None
    buckets = []
    for lo, hi in [(0, .2), (.2, .4), (.4, .6), (.6, .8), (.8, 1.01)]:
        sel = [(p, o) for p, o in zip(ps, hs) if lo <= p < hi]
        if sel:
            buckets.append({"range": str(int(lo * 100)) + "-" + str(min(int(hi * 100), 100)) + "%",
                            "n": len(sel),
                            "stated": round(sum(p for p, _ in sel) / len(sel), 3),
                            "actual": round(sum(o for _, o in sel) / len(sel), 3)})
    mean_p = sum(ps) / n
    gap = mean_p - base
    traded = [float(r["paper_pnl_eur"]) for r in rows if r["paper_pnl_eur"] not in ("", None)]
    out.update({"brier": round(brier, 4), "brier_reference": round(ref, 4),
                "skill": round(skill, 3) if skill is not None else None,
                "mean_stated": round(mean_p, 3), "actual_hit_rate": round(base, 3),
                "overconfidence_pp": round(gap * 100, 1), "buckets": buckets,
                "paper_trades": len(traded), "paper_pnl_eur": round(sum(traded), 2)})
    if n < MIN_FOR_VERDICT:
        out["verdict"] = ("Too few resolved probes (" + str(n) + " of "
                          + str(MIN_FOR_VERDICT) + ") for a verdict.")
    elif abs(gap) <= 0.05 and skill is not None and skill > 0:
        out["verdict"] = "Calibrated: stated odds match outcomes and beat a naive guess."
    elif gap > 0.05:
        out["verdict"] = "Over-confident: the engine claims better odds than it achieves."
    elif gap < -0.05:
        out["verdict"] = "Under-confident: outcomes beat the stated odds."
    else:
        out["verdict"] = "Stated odds roughly match outcomes but add no skill over a naive guess."
    save(SUMMARY_FILE, out)
    return out


def write_lesson(done, s):
    if not done:
        print("nothing resolved today - memory left untouched (correct)")
        return
    lines = ["", "## " + berlin_now().date().isoformat() + " - " + str(len(done))
             + " probe(s) resolved"]
    for r in done:
        lines.append("- " + r["ticker"] + ": " + r["outcome"] + " after " + str(r["sessions"])
                     + " session(s); stated P(win) " + str(round(float(r["p_win_stated"]) * 100, 1))
                     + "%, move " + str(r["gross_pct"]) + "%")
    lines.append("- Running record: " + str(s["resolved"]) + " resolved | stated "
                 + str(round(s.get("mean_stated", 0) * 100, 1)) + "% vs actual "
                 + str(round(s.get("actual_hit_rate", 0) * 100, 1)) + "% | Brier "
                 + str(s.get("brier")) + " | " + s["verdict"])
    with open(MEMORY_FILE, "a") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


def main():
    book = register()
    done = resolve(book)
    eq = update_equity(done)
    s = summarise(eq)
    write_lesson(done, s)
    print("calibration: " + s["verdict"])


if __name__ == "__main__":
    main()
