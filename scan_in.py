# scan_in.py — India (NSE) morning scan. Suggest-only, research/education.
# Data: yfinance (~15-min delayed). Prices in INR; ~EUR shown for reference. Times displayed in CET.
# NOT live. NOT financial advice.

import csv, json, datetime
import yfinance as yf

POOL_INR = 20000.0          # India capital pool (INR)
ROUNDTRIP_FEE_PCT = 0.35    # all-in round-trip % (brokerage+STT+exch+GST+stamp) — ESTIMATE, confirm on contract note
MIN_GROSS_MOVE_PCT = 1.5    # India worthwhile bar

def eur_rate():
    try:
        h = yf.Ticker("EURINR=X").history(period="5d", interval="1d")
        h = h["Close"].dropna()
        return float(h.iloc[-1]) if len(h) else 90.0
    except Exception:
        return 90.0

def get_series(ticker):
    try:
        h = yf.Ticker(ticker).history(period="4mo", interval="1d", auto_adjust=False)
        if h is None or len(h) == 0:
            print("    [skip] " + ticker + ": no data"); return None
        h = h[["Open","High","Low","Close","Volume"]].dropna()
        h = h[h["Close"] > 0]
        if len(h) < 20:
            print("    [skip] " + ticker + ": only " + str(len(h)) + " clean rows"); return None
        closes=[float(x) for x in h["Close"].tolist()]
        highs =[float(x) for x in h["High"].tolist()]
        lows  =[float(x) for x in h["Low"].tolist()]
        vols  =[float(x) for x in h["Volume"].tolist()]
        if closes[-1] != closes[-1]:
            print("    [skip] " + ticker + ": last close NaN"); return None
        return {"closes":closes,"highs":highs,"lows":lows,"vols":vols}
    except Exception as e:
        print("    [error] " + ticker + ": " + str(e)); return None

def sma(x,n): return sum(x[-n:])/n if len(x)>=n else None
def rsi(c,n=14):
    if len(c)<n+1: return None
    g=l=0.0
    for i in range(-n,0):
        ch=c[i]-c[i-1]; g+=max(ch,0); l+=max(-ch,0)
    if l==0: return 100.0
    rs=(g/n)/(l/n); return 100-(100/(1+rs))
def atr_pct(h,lo,c,n=14):
    if len(c)<n+1: return None
    trs=[]
    for i in range(-n,0):
        trs.append(max(h[i]-lo[i], abs(h[i]-c[i-1]), abs(lo[i]-c[i-1])))
    return (sum(trs)/n/c[-1])*100 if c[-1] else None

def analyze(ticker,name,rate):
    s=get_series(ticker)
    if not s or len(s["closes"])<20: return None
    c=s["closes"]; price=c[-1]
    sma5,sma20=sma(c,5),sma(c,20); r=rsi(c); a=atr_pct(s["highs"],s["lows"],c)
    avgvol=sma(s["vols"],20) or 0
    if None in (sma5,sma20,r,a): return None

    score=50.0
    if sma5>sma20: score+=15
    else: score-=10
    if price>sma20: score+=8
    if 45<=r<=68: score+=12
    elif r>75: score-=12
    elif r<35: score-=6
    if 1.2<=a<=4.5: score+=8      # India names run a bit hotter; widen band slightly
    elif a>7: score-=10
    if avgvol>500000: score+=7    # NSE liquidity threshold
    affordable = price <= POOL_INR
    if not affordable: score-=25
    score=max(0,min(100,score))
    conf="High" if score>=72 else ("Med" if score>=60 else "Low")

    buy_low=round(price*(1-0.003),2); buy_high=round(price*(1+0.004),2)
    est_dayhigh=round(price*(1+(a/100)*0.9),2)
    est_dayend =round(price*(1+(a/100)*0.5),2)
    stop       =round(price*(1-(a/100)*1.1),2)
    tgt_move_pct=(est_dayhigh/price-1)*100

    max_alloc=POOL_INR*0.98
    shares=int(max_alloc//price) if price<=max_alloc else 0
    cost=round(shares*price,2)
    fee_cost=round(cost*ROUNDTRIP_FEE_PCT/100,2)
    fee_drag_pct=ROUNDTRIP_FEE_PCT if cost>0 else None
    worthwhile=(shares>=1) and (tgt_move_pct>=MIN_GROSS_MOVE_PCT)

    return {"spark": [round(x, 2) for x in c[-30:]],"ticker":ticker,"name":name,"price":round(price,2),"conf":conf,"score":round(score,1),
            "rsi":round(r,1),"atr_pct":round(a,2),"sma5":round(sma5,2),"sma20":round(sma20,2),
            "avgvol":int(avgvol),"buy_low":buy_low,"buy_high":buy_high,"est_dayhigh":est_dayhigh,
            "est_dayend":est_dayend,"stop":stop,"tgt_move_pct":round(tgt_move_pct,2),
            "shares":shares,"cost":cost,"cost_eur":round(cost/rate,2),"fee_cost":fee_cost,
            "fee_drag_pct":fee_drag_pct,"worthwhile":worthwhile,"affordable":affordable,
            "currency":"INR"}

def main():
    rate=eur_rate()
    picks=[]
    with open("watchlist_in.csv") as f:
        for row in csv.DictReader(f):
            res=analyze(row["ticker"],row["name"],rate)
            if res: picks.append(res)
    picks.sort(key=lambda x:(x["worthwhile"],x["score"]),reverse=True)
    top=picks[:3]
    actionable=[p for p in top if p["worthwhile"] and p["conf"] in ("Med","High")]
    now=datetime.datetime.now(datetime.timezone.utc).astimezone(
        datetime.timezone(datetime.timedelta(hours=1)))  # display in CET
    stamp=now.strftime("%Y-%m-%d %H:%M CET")
    with open("picks_today_in.json","w") as f:
        json.dump({"date":now.strftime("%Y-%m-%d"),"generated":stamp,"eurinr":round(rate,2),
                   "picks":top,"actionable_count":len(actionable)},f,indent=2)
    print("["+stamp+"] INDIA scanned "+str(len(picks))+"; top "+str(len(top))+
          "; actionable "+str(len(actionable))+"; EURINR "+str(round(rate,2)))
    for p in top:
        print("  "+p["ticker"]+" "+p["conf"]+" score "+str(p["score"])+"  INR"+str(p["price"])+
              "  "+str(p["shares"])+"sh INR"+str(p["cost"])+" (~EUR"+str(p["cost_eur"])+
              ")  tgt "+str(p["tgt_move_pct"])+"%  worthwhile="+str(p["worthwhile"]))

if __name__=="__main__":
    main()
