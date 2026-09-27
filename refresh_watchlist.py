# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Malviyaarjun
# refresh_watchlist.py — v3 universe builder (Germany). Research/education only.

import os, csv
import yfinance as yf

POOL_EUR = 1000.0     # v3: max price per share (half of EUR2000 paper capital)
KEEP = 14
MIN_ATR_PCT = 1.2

UNIVERSE = {
 "SAP.DE":"SAP SE","DTE.DE":"Deutsche Telekom","DBK.DE":"Deutsche Bank","CBK.DE":"Commerzbank",
 "LHA.DE":"Lufthansa","IFX.DE":"Infineon","RWE.DE":"RWE","EOAN.DE":"E.ON","VOW3.DE":"Volkswagen pref",
 "BAYN.DE":"Bayer","BMW.DE":"BMW","MBG.DE":"Mercedes-Benz","ALV.DE":"Allianz","BAS.DE":"BASF",
 "SIE.DE":"Siemens","MUV2.DE":"Munich Re","ADS.DE":"Adidas","HEN3.DE":"Henkel",
 "FRE.DE":"Fresenius","CON.DE":"Continental","ZAL.DE":"Zalando","HFG.DE":"HelloFresh",
 "SHL.DE":"Siemens Healthineers","P911.DE":"Porsche AG","RHM.DE":"Rheinmetall",
 "HEI.DE":"Heidelberg Materials","SY1.DE":"Symrise","EVK.DE":"Evonik","LXS.DE":"Lanxess",
 "PUM.DE":"Puma","TKA.DE":"ThyssenKrupp","SDF.DE":"K+S","FNTN.DE":"Freenet",
 "NEM.DE":"Nemetschek","AIR.DE":"Airbus","DHER.DE":"Delivery Hero","BEI.DE":"Beiersdorf",
 "DB1.DE":"Deutsche Boerse","MTX.DE":"MTU Aero","QIA.DE":"Qiagen","SRT3.DE":"Sartorius",
 "BNR.DE":"Brenntag","G1A.DE":"GEA Group","KGX.DE":"Kion Group","NDA.DE":"Aurubis"
}

def score(ticker):
    try:
        h = yf.Ticker(ticker).history(period="6mo", interval="1d", auto_adjust=False)
        h = h[["High","Low","Close","Volume"]].dropna()
        h = h[h["Close"] > 0]
        if len(h) < 30: return None
        c  = [float(x) for x in h["Close"]]
        hi = [float(x) for x in h["High"]]
        lo = [float(x) for x in h["Low"]]
        v  = [float(x) for x in h["Volume"]]
        price = c[-1]
        if price > POOL_EUR: return None
        trs = []
        for i in range(-14, 0):
            trs.append(max(hi[i]-lo[i], abs(hi[i]-c[i-1]), abs(lo[i]-c[i-1])))
        atrp = (sum(trs)/14/price) * 100
        if atrp < MIN_ATR_PCT: return None
        avgvol = sum(v[-20:]) / 20
        turnover = avgvol * price
        if turnover < 2000000: return None
        sma20 = sum(c[-20:]) / 20
        ret20 = (price/c[-21] - 1) * 100 if len(c) >= 21 else 0
        trend = 1 if price > sma20 else 0
        sc = atrp*6 + (turnover**0.5)/60 + trend*12 + max(min(ret20, 15), -15)
        return {"ticker":ticker, "price":round(price,2), "atrp":round(atrp,2),
                "turnover":int(turnover), "ret20":round(ret20,2), "score":round(sc,1)}
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
        if os.path.exists("watchlist.csv"):
            print("WARNING: only " + str(len(top)) + " qualified - keeping existing watchlist.csv.")
            return
        print("WARNING: no qualifying names - writing fallback.")
        top = [{"ticker":"RWE.DE","name":"RWE","atrp":0,"score":0,"price":0,"ret20":0},
               {"ticker":"IFX.DE","name":"Infineon","atrp":0,"score":0,"price":0,"ret20":0},
               {"ticker":"BAYN.DE","name":"Bayer","atrp":0,"score":0,"price":0,"ret20":0}]

    with open("watchlist.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["ticker","name","note"])
        for r in top:
            w.writerow([r["ticker"], r["name"],
                        "auto: ATR " + str(r.get("atrp",0)) + "% ret20 "
                        + str(r.get("ret20",0)) + "% score " + str(r.get("score",0))])
    print("v3 watchlist: " + str(len(top)) + " names (of " + str(len(ranked)) + " qualifying)")
    for r in top:
        print("  " + r["ticker"] + "  EUR" + str(r.get("price",0))
              + "  ATR " + str(r.get("atrp",0)) + "%  ret20 " + str(r.get("ret20",0))
              + "%  score " + str(r.get("score",0)))

if __name__ == "__main__":
    main()
