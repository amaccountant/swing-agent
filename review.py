# review.py — end-of-day review + learning loop. Suggest-only, research/education.
# Fetches actual day-high/close for today's picks, logs deviations, updates strategy memory.
# Data ~15-min delayed. NOT financial advice.

import json, os, csv, datetime
import yfinance as yf

def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default

def actual_today(ticker):
    try:
        h = yf.Ticker(ticker).history(period="5d", interval="1d", auto_adjust=False)
        h = h[["High", "Low", "Close"]].dropna()
        if len(h) == 0:
            return None
        last = h.iloc[-1]
        return {"high": float(last["High"]), "low": float(last["Low"]),
                "close": float(last["Close"]), "date": str(h.index[-1].date())}
    except Exception as e:
        print("  [error] " + ticker + ": " + str(e))
        return None

def main():
    data = load_json("picks_today.json", {"picks": []})
    picks = data.get("picks", [])
    if not picks:
        print("No picks to review.")
        return

    log_exists = os.path.exists("performance_log.csv")
    f = open("performance_log.csv", "a", newline="")
    w = csv.writer(f)
    if not log_exists:
        w.writerow(["date", "ticker", "name", "conf", "predicted_dayhigh", "predicted_dayend",
                    "prior_close", "actual_dayhigh", "actual_close", "hit_miss", "dev_pct", "notes"])

    lessons = []
    for p in picks:
        act = actual_today(p["ticker"])
        if not act:
            w.writerow([data.get("date"), p["ticker"], p["name"], p["conf"], p["est_dayhigh"],
                        p["est_dayend"], p["price"], "NA", "NA", "NO DATA", "", "Could not fetch actuals"])
            continue
        pred = p["est_dayhigh"]
        actual = act["high"]
        reached = actual >= pred
        dev = round((actual / pred - 1) * 100, 2)
        hit = "HIT" if reached else "MISS"
        if reached and p["worthwhile"]:
            note = "Target achievable; setup valid."
        elif reached and not p["worthwhile"]:
            note = "Move happened but we correctly skipped (fees). No loss."
        else:
            note = "Day-high fell short of estimate."
        w.writerow([data.get("date"), p["ticker"], p["name"], p["conf"], pred, p["est_dayend"],
                    p["price"], round(actual, 2), round(act["close"], 2), hit, dev, note])
        lessons.append((p, act, hit, dev, note))
    f.close()

    stamp = datetime.datetime.now(datetime.timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M %Z")
    lines = ["", "## Review " + str(data.get("date")) + " (logged " + stamp + ")"]
    misses = [l for l in lessons if l[2] == "MISS"]
    hits = [l for l in lessons if l[2] == "HIT"]
    lines.append("- Picks reviewed: " + str(len(lessons)) + " | Day-high estimate reached: " +
                 str(len(hits)) + " | Fell short: " + str(len(misses)))
    for p, act, hit, dev, note in lessons:
        lines.append("  - " + p["ticker"] + " (" + p["conf"] + "): predicted high EUR" + str(p["est_dayhigh"]) +
                     ", actual EUR" + str(round(act["high"], 2)) + " (" + ("%+.2f" % dev) +
                     "% vs estimate) -> " + hit + ". " + note)
    if misses and len(misses) >= max(1, len(lessons) // 2):
        lines.append("- LESSON: Day-high estimates ran high today (several shortfalls). Next run: treat "
                     "estimates as optimistic; favour higher-liquidity, lower-volatility names and keep the "
                     "3% worthwhile bar strict.")
    elif hits and not misses:
        lines.append("- LESSON: Estimates were achievable across picks; calibration looks reasonable. Keep settings.")
    with open("strategy_memory.md", "a") as mf:
        mf.write("\n".join(lines) + "\n")
    print("\n".join(lines))

if __name__ == "__main__":
    main()
