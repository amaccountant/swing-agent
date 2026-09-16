# refresh_watchlist_in.py — daily intelligent watchlist for India (NSE .NS).
# Same tradability scoring, INR pool. Research/education. NOT financial advice.

import os, csv
import yfinance as yf

POOL_INR = 20000.0
KEEP = 12
MIN_ATR_PCT = 1.2

UNIVERSE = {
 "RELIANCE.NS":"Reliance","TCS.NS":"TCS","INFY.NS":"Infosys","HDFCBANK.NS":"HDFC Bank",
 "ICICIBANK.NS":"ICICI Bank","SBIN.NS":"SBI","TATAMOTORS.NS":"Tata Motors","AXISBANK.NS":"Axis Bank",
 "LT.NS":"L&T","ITC.NS":"ITC","TATASTEEL.NS":"Tata Steel","HINDALCO.NS":"Hindalco",
 "BAJFINANCE.NS":"Bajaj Finance","ADANIENT.NS":"Adani Ent","WIPRO.NS":"Wipro","MARUTI.NS":"Maruti",
 "SUNPHARMA.NS":"Sun Pharma","TITAN.NS":"Titan","ONGC.NS":"ONGC","COALINDIA.NS":"Coal India",
 "JSWSTEEL.NS":"JSW Steel","POWERGRID.NS":"Power Grid","NTPC.NS":"NTPC","BPCL.NS":"BPCL",
 "TECHM.NS":"Tech Mahindra","HCLTECH.NS":"HCL Tech","GRASIM.NS":"Grasim","VEDL.NS":"Vedanta",
 "ADANIPORTS.NS":"Adani Ports","TATAPOWER.NS":"Tata Power","IOC.NS":"IOC","GAIL.NS":"GAIL",
 "SAIL.NS":"SAIL","PNB.NS":"PNB","BANKBARODA.NS":"Bank of Baroda","IDEA.NS":"Vodafone Idea",
 "ZOMATO.NS":"Zomato","YESBANK.NS":"Yes Bank","ASHOKLEY.NS":"Ashok Leyland","M&M.NS":"M&M"
}

def score(ticker):
    try:
        h = yf.Ticker(ticker).history(period="3mo", interval="1d", auto_adjust=False)
        h = h[["High","Low","Close","Volume"]].dropna()
        h = h[h["Close"] > 0]
        if len(h) < 20:
            return None
        c  = [float(x) for x in h["Close"]]
        hi = [float(x) for x in h["High"]]
        lo = [float(x) for x in h["Low"]]
        v  = [float(x) for x in h["Volume"]]
        price = c[-1]
        if price > POOL_INR:
            return None
        trs = []
        for i in range(-14, 0):
            trs.append(max(hi[i]-lo[i], abs(hi[i]-c[i-1]), abs(lo[i]-c[i-1])))
        atrp = (sum(trs)/14/price) * 100
        if atrp < MIN_ATR_PCT:
            return None
        avgvol = sum(v[-20:]) / 20
        turnover = avgvol * price
        sma5 = sum(c[-5:]) / 5
        sma20 = sum(c[-20:]) / 20
        trend = 1 if sma5 > sma20 else 0
        g = l = 0.0
        for i in range(-14, 0):
            ch = c[i] - c[i-1]; g += max(ch, 0); l += max(-ch, 0)
        rsi = 100 if l == 0 else 100 - (100/(1+(g/14)/(l/14)))
        mom_ok = 1 if 45 <= rsi <= 70 else 0
        sc = atrp*10 + (turnover**0.5)/500 + trend*15 + mom_ok*10
        return {"ticker":ticker, "price":round(price,2), "atrp":round(atrp,2),
                "turnover":int(turnover), "score":round(sc,1)}
    except Exception as e:
        print("  [skip] " + ticker + ": " + str(e))
        return None

def main():
    ranked = []
    for t, name in UNIVERSE.items():
        try:
            r = score(t)
        except Exception as e:
            print("  [skip] " + t + ": " + str(e)); r = None
        if r:
            r["name"] = name; ranked.append(r)
    ranked.sort(key=lambda x: x["score"], reverse=True)
    top = ranked[:KEEP]

    if len(top) < 3:
        if os.path.exists("watchlist_in.csv"):
            print("WARNING: only " + str(len(top)) + " qualified - keeping existing watchlist_in.csv.")
            return
        print("WARNING: no qualifying names - writing fallback.")
        top = [{"ticker":"RELIANCE.NS","name":"Reliance","atrp":0,"score":0,"price":0},
               {"ticker":"TCS.NS","name":"TCS","atrp":0,"score":0,"price":0},
               {"ticker":"INFY.NS","name":"Infosys","atrp":0,"score":0,"price":0}]

    with open("watchlist_in.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["ticker","name","note"])
        for r in top:
            w.writerow([r["ticker"], r["name"],
                        "auto: ATR " + str(r.get("atrp",0)) + "% score " + str(r.get("score",0))])
    print("India watchlist refreshed: " + str(len(top)) + " names (of " + str(len(ranked)) + " qualifying)")
    for r in top:
        print("  " + r["ticker"] + "  INR" + str(r.get("price",0)) +
              "  ATR " + str(r.get("atrp",0)) + "%  score " + str(r.get("score",0)))

if __name__ == "__main__":
    main()
