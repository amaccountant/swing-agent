# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Malviyaarjun
# review_in.py — India end-of-day review + learning loop. Times shown in CET.
# Suggest-only, research/education. Data ~15-min delayed. NOT financial advice.

import json, os, csv, datetime
import yfinance as yf

def load_json(p,d):
    if os.path.exists(p):
        with open(p) as f: return json.load(f)
    return d

def actual_today(t):
    try:
        h=yf.Ticker(t).history(period="5d",interval="1d",auto_adjust=False)
        h=h[["High","Low","Close"]].dropna()
        if len(h)==0: return None
        last=h.iloc[-1]
        return {"high":float(last["High"]),"low":float(last["Low"]),
                "close":float(last["Close"]),"date":str(h.index[-1].date())}
    except Exception as e:
        print("  [error] "+t+": "+str(e)); return None

def main():
    data=load_json("picks_today_in.json",{"picks":[]})
    picks=data.get("picks",[])
    if not picks:
        print("India: no picks to review."); return

    # avoid duplicate rows if the review runs more than once for the same date
    already = set()
    if os.path.exists("performance_log.csv"):
        with open("performance_log.csv") as _f:
            for _r in csv.DictReader(_f):
                already.add((_r.get("date"), _r.get("ticker")))
    picks = [p for p in picks if (data.get("date"), p["ticker"]) not in already]
    if not picks:
        print("All of today's picks already reviewed - skipping.")
        return
    exists=os.path.exists("performance_log_in.csv")
    f=open("performance_log_in.csv","a",newline=""); w=csv.writer(f)
    if not exists:
        w.writerow(["date","ticker","name","conf","predicted_dayhigh","predicted_dayend",
                    "prior_close","actual_dayhigh","actual_close","hit_miss","dev_pct","notes"])
    lessons=[]
    for p in picks:
        act=actual_today(p["ticker"])
        if not act:
            w.writerow([data.get("date"),p["ticker"],p["name"],p["conf"],p["est_dayhigh"],
                        p["est_dayend"],p["price"],"NA","NA","NO DATA","","Could not fetch actuals"]); continue
        pred=p["est_dayhigh"]; actual=act["high"]; reached=actual>=pred
        dev=round((actual/pred-1)*100,2); hit="HIT" if reached else "MISS"
        if reached and p["worthwhile"]: note="Target achievable; setup valid."
        elif reached and not p["worthwhile"]: note="Move happened but correctly skipped (costs). No loss."
        else: note="Day-high fell short of estimate."
        w.writerow([data.get("date"),p["ticker"],p["name"],p["conf"],pred,p["est_dayend"],
                    p["price"],round(actual,2),round(act["close"],2),hit,dev,note])
        lessons.append((p,act,hit,dev,note))
    f.close()
    now=datetime.datetime.now(datetime.timezone.utc).astimezone(
        datetime.timezone(datetime.timedelta(hours=1)))
    stamp=now.strftime("%Y-%m-%d %H:%M CET")
    lines=["","## India Review "+str(data.get("date"))+" (logged "+stamp+")"]
    hits=[l for l in lessons if l[2]=="HIT"]; misses=[l for l in lessons if l[2]=="MISS"]
    lines.append("- Picks reviewed: "+str(len(lessons))+" | Reached: "+str(len(hits))+
                 " | Fell short: "+str(len(misses)))
    for p,act,hit,dev,note in lessons:
        lines.append("  - "+p["ticker"]+" ("+p["conf"]+"): predicted INR"+str(p["est_dayhigh"])+
                     ", actual INR"+str(round(act["high"],2))+" ("+("%+.2f"%dev)+"%) -> "+hit+". "+note)
    if misses and len(misses)>=max(1,len(lessons)//2):
        lines.append("- LESSON: India day-high estimates ran high; favour steadier high-liquidity names, "
                     "keep the 1.5% bar strict.")
    elif hits and not misses:
        lines.append("- LESSON: India estimates achievable; calibration reasonable. Keep settings.")
    with open("strategy_memory_in.md","a") as mf:
        mf.write("\n".join(lines)+"\n")
    print("\n".join(lines))

if __name__=="__main__":
    main()
