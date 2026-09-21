# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Malviyaarjun
# track_review.py — horizon-aware recommendation tracker.
# Registers each pick as an OPEN recommendation, then evaluates it every day
# until TARGET hit, STOP hit, or the 5-trading-day horizon expires.
# Outcomes are logged ONLY when resolved, so learning is never corrupted
# by judging a 5-day idea on day one.  Research/education. NOT financial advice.

import json, os, csv, datetime, sys
import yfinance as yf

MAX_DAYS = 5          # your hard maximum holding horizon

def load(p, d):
    if os.path.exists(p):
        with open(p) as f: return json.load(f)
    return d

def save(p, obj):
    with open(p, "w") as f: json.dump(obj, f, indent=2)

def bars_since(ticker, start_date):
    """Daily bars from start_date onward (inclusive-ish, tolerant of gaps)."""
    try:
        h = yf.Ticker(ticker).history(period="3mo", interval="1d", auto_adjust=False)
        h = h[["Open", "High", "Low", "Close"]].dropna()
        out = []
        for idx, row in h.iterrows():
            d = str(idx.date())
            if d >= start_date:
                out.append({"d": d, "o": float(row["Open"]), "h": float(row["High"]),
                            "l": float(row["Low"]), "c": float(row["Close"])})
        return out
    except Exception as e:
        print("  [error] " + ticker + ": " + str(e))
        return []

def register(picks_file, open_file, market):
    """Add today's picks as OPEN recommendations (skip duplicates)."""
    data = load(picks_file, {"picks": [], "date": None})
    book = load(open_file, {"open": [], "market": market})
    if not data.get("picks"): return book
    have = set((o["date"], o["ticker"]) for o in book["open"])
    added = 0
    for p in data["picks"]:
        key = (data.get("date"), p["ticker"])
        if key in have: continue
        # only track ideas the engine actually deemed actionable
        if not (p.get("worthwhile") and p.get("conf") in ("Med", "High")): continue
        book["open"].append({
            "date": data.get("date"), "ticker": p["ticker"], "name": p["name"],
            "conf": p["conf"], "score": p["score"],
            "ref_close": p["price"], "buy_low": p["buy_low"], "buy_high": p["buy_high"],
            "target": p["est_dayhigh"], "stop": p["stop"],
            "tgt_move_pct": p["tgt_move_pct"], "shares": p["shares"], "cost": p["cost"],
            "bars_seen": 0, "entry_price": None, "entry_date": None,
            "best_high": None, "worst_low": None
        })
        added += 1
    if added: print(market + ": registered " + str(added) + " new open recommendation(s)")
    save(open_file, book)
    return book

def resolve(open_file, log_file, memory_file, market, fee_kind, fee, currency):
    book = load(open_file, {"open": [], "market": market})
    if not book["open"]:
        print(market + ": no open recommendations to evaluate.")
        return
    new_log = not os.path.exists(log_file)
    fh = open(log_file, "a", newline="")
    w = csv.writer(fh)
    if new_log:
        w.writerow(["resolved_on", "signal_date", "ticker", "name", "conf",
                    "entry_price", "target", "stop", "exit_price", "outcome",
                    "days_held", "gross_pct", "net_pct_after_fees", "max_favourable_pct",
                    "max_adverse_pct", "note"])
    still_open = []
    resolved = []
    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=1))).strftime("%Y-%m-%d")

    for pos in book["open"]:
        bars = bars_since(pos["ticker"], pos["date"])
        # drop the signal day itself; entry is the NEXT session's open
        fwd = [b for b in bars if b["d"] > pos["date"]]
        if not fwd:
            still_open.append(pos); continue

        if pos["entry_price"] is None:
            pos["entry_price"] = round(fwd[0]["o"], 2)
            pos["entry_date"] = fwd[0]["d"]

        entry = pos["entry_price"]
        outcome = None; exit_px = None; exit_day = None; held = 0
        best = pos.get("best_high") or entry
        worst = pos.get("worst_low") or entry

        for k, b in enumerate(fwd[:MAX_DAYS]):
            held = k + 1
            best = max(best, b["h"]); worst = min(worst, b["l"])
            if b["l"] <= pos["stop"]:                      # stop checked first (conservative)
                outcome = "STOP"; exit_px = pos["stop"]; exit_day = b["d"]; break
            if b["h"] >= pos["target"]:
                outcome = "TARGET"; exit_px = pos["target"]; exit_day = b["d"]; break
            if held >= MAX_DAYS or k == len(fwd) - 1:
                if held >= MAX_DAYS:
                    outcome = "EXPIRED"; exit_px = b["c"]; exit_day = b["d"]

        pos["bars_seen"] = len(fwd); pos["best_high"] = round(best, 2); pos["worst_low"] = round(worst, 2)

        if outcome is None:
            still_open.append(pos)
            print("  " + market + " " + pos["ticker"] + ": still open (day " + str(held) +
                  " of " + str(MAX_DAYS) + ") — no verdict yet, as designed.")
            continue

        notional = entry * max(pos["shares"], 1)
        fees = (fee * 2) if fee_kind == "flat" else (notional * fee / 100.0)
        gross = (exit_px / entry - 1) * 100 if entry else 0
        net = gross - (fees / notional * 100 if notional else 0)
        mfe = (best / entry - 1) * 100 if entry else 0
        mae = (worst / entry - 1) * 100 if entry else 0
        note = {"TARGET": "Target reached within horizon.",
                "STOP": "Stop triggered — loss capped as designed.",
                "EXPIRED": "Horizon expired without hitting target or stop."}[outcome]
        w.writerow([today, pos["date"], pos["ticker"], pos["name"], pos["conf"],
                    entry, pos["target"], pos["stop"], round(exit_px, 2), outcome,
                    held, round(gross, 2), round(net, 2), round(mfe, 2), round(mae, 2), note])
        resolved.append({"pos": pos, "outcome": outcome, "net": net, "held": held,
                         "mfe": mfe, "mae": mae})
        print("  " + market + " " + pos["ticker"] + ": " + outcome + " on day " +
              str(held) + " (net " + str(round(net, 2)) + "%)")

    book["open"] = still_open
    save(open_file, book)
    fh.close()

    if not resolved:
        print(market + ": nothing resolved today — learning left untouched (correct).")
        return

    tgt = [r for r in resolved if r["outcome"] == "TARGET"]
    stp = [r for r in resolved if r["outcome"] == "STOP"]
    exp = [r for r in resolved if r["outcome"] == "EXPIRED"]
    avg_net = sum(r["net"] for r in resolved) / len(resolved)
    lines = ["", "## " + market + " resolved trades — logged " + today,
             "- Resolved: " + str(len(resolved)) + " | Target " + str(len(tgt)) +
             " | Stop " + str(len(stp)) + " | Expired " + str(len(exp)) +
             " | Avg net " + ("%+.2f" % avg_net) + "%"]
    for r in resolved:
        p = r["pos"]
        lines.append("  - " + p["ticker"] + " (" + p["conf"] + "): " + r["outcome"] +
                     " in " + str(r["held"]) + "d, net " + ("%+.2f" % r["net"]) +
                     "%, best " + ("%+.2f" % r["mfe"]) + "%, worst " + ("%+.2f" % r["mae"]) + "%")
    near = [r for r in exp if r["mfe"] >= r["pos"]["tgt_move_pct"] * 0.7]
    if len(stp) > len(tgt) and stp:
        lines.append("- LESSON: stops are being hit more than targets. The stop may sit inside "
                     "normal daily noise — widen it or demand a stronger setup.")
    elif near and len(near) >= max(1, len(exp) // 2):
        lines.append("- LESSON: several expired trades came close to target. Targets look slightly "
                     "ambitious for a 5-day window, or exits are too early.")
    elif tgt and len(tgt) >= len(resolved) / 2:
        lines.append("- LESSON: targets are being reached within the horizon. Current calibration "
                     "looks reasonable — keep settings and keep sample size growing.")
    else:
        lines.append("- LESSON: mixed outcomes. Sample still small; avoid changing rules on noise.")
    with open(memory_file, "a") as mf:
        mf.write("\n".join(lines) + "\n")
    print("\n".join(lines))

def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "DE"
    if which == "IN":
        register("picks_today_in.json", "open_positions_in.json", "IN")
        resolve("open_positions_in.json", "resolved_log_in.csv",
                "strategy_memory_in.md", "IN", "pct", 0.35, "INR")
    else:
        register("picks_today.json", "open_positions.json", "DE")
        resolve("open_positions.json", "resolved_log.csv",
                "strategy_memory.md", "DE", "flat", 1.0, "EUR")

if __name__ == "__main__":
    main()
