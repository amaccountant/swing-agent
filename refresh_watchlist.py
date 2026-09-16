# refresh_watchlist.py — daily intelligent watchlist for Germany (XETRA .DE).
# Scores a broad universe by movement + liquidity + momentum + affordability,
# keeps the top ~12 "most tradable movers" -> writes watchlist.csv.
# Data: yfinance (~15-min delayed). Research/education. NOT financial advice.

import os, csv
import yfinance as yf

POOL_EUR = 200.0
KEEP = 12
MIN_ATR_PCT = 1.5

UNIVERSE = {
 "SAP.DE":"SAP SE","DTE.DE":"Deutsche Telekom","DBK.DE":"Deutsche Bank","CBK.DE":"Commerzbank",
 "LHA.DE":"Lufthansa","IFX.DE":"Infineon","RWE.DE":"RWE","EOAN.DE":"E.ON","VOW3.DE":"Volkswagen pref",
 "BAYN.DE":"Bayer","BMW.DE":"BMW","MBG.DE":"Mercedes-Benz","ALV.DE":"Allianz","BAS.DE":"BASF",
 "SIE.DE":"Siemens","MUV2.DE":"Munich Re","DPW.DE":"DHL Group","ADS.DE":"Adidas","HEN3.DE":"Henkel",
 "FRE.DE":"Fresenius","CON.DE":"Continental","ZAL.DE":"Zalando","HFG.DE":"HelloFresh","SHL.DE":"Siemens Healthineers",
 "P911.DE":"Porsche AG","1COV.DE":"Covestro","RHM.DE":"Rheinmetall","HEI.DE":"Heidelberg Materials",
 "SY1.DE":"Symrise","QIA.DE":"Qiagen","EVK.DE":"Evonik","LXS.DE":"Lanxess","NDA.DE":"Aurubis",
 "PUM.DE":"Puma","TKA.DE":"ThyssenKrupp","SDF.DE":"K+S","FNTN.DE":"Freenet","NEM.DE":"Nemetschek",
 "AIR.DE":"Airbus","DHER.DE":"Delivery Hero"
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
        if price > POOL_EUR:
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
        sc = atrp*10 + (turnover**0.5)/50 + trend*15 + mom_ok*10
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

    # SAFETY: if too few names qualified, keep existing list rather than wiping it
    if len(top) < 3:
        if os.path.exists("watchlist.csv"):
            print("WARNING: only " + str(len(top)) + " qualified - keeping existing watchlist.csv.")
            return
        print("WARNING: no qualifying names and no existing list - writing fallback.")
        top = [{"ticker":"RWE.DE","name":"RWE","atrp":0,"score":0,"price":0},
               {"ticker":"IFX.DE","name":"Infineon","atrp":0,"score":0,"price":0},
               {"ticker":"BAYN.DE","name":"Bayer","atrp":0,"score":0,"price":0}]

    with open("watchlist.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["ticker","name","note"])
        for r in top:
            w.writerow([r["ticker"], r["name"],
                        "auto: ATR " + str(r.get("atrp",0)) + "% score " + str(r.get("score",0))])
    print("Germany watchlist refreshed: " + str(len(top)) + " names (of " + str(len(ranked)) + " qualifying)")
    for r in top:
        print("  " + r["ticker"] + "  EUR" + str(r.get("price",0)) +
              "  ATR " + str(r.get("atrp",0)) + "%  score " + str(r.get("score",0)))

if __name__ == "__main__":
    main()
