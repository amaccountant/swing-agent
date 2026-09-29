# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Malviyaarjun
# Swing Research Agent - watchlist builder (Germany, XETRA)
# Picks the 14 most liquid, active and affordable names from a fixed universe
# and writes them to watchlist.csv for probability_engine.py.
# Research/education only. NOT financial advice.

import os, csv
import yfinance as yf

MAX_PRICE = 1000.0     # max price per share (half of EUR2000 paper capital)
KEEP = 14
MIN_ATR_PCT = 1.2
MIN_TURNOVER = 2000000.0

UNIVERSE = {
 "SAP.DE": "SAP SE", "DTE.DE": "Deutsche Telekom", "DBK.DE": "Deutsche Bank",
 "CBK.DE": "Commerzbank", "LHA.DE": "Lufthansa", "IFX.DE": "Infineon", "RWE.DE": "RWE",
 "EOAN.DE": "E.ON", "VOW3.DE": "Volkswagen pref", "BAYN.DE": "Bayer", "BMW.DE": "BMW",
 "MBG.DE": "Mercedes-Benz", "ALV.DE": "Allianz", "BAS.DE": "BASF", "SIE.DE": "Siemens",
 "MUV2.DE": "Munich Re", "ADS.DE": "Adidas", "HEN3.DE": "Henkel", "FRE.DE": "Fresenius",
 "CON.DE": "Continental", "ZAL.DE": "Zalando", "HFG.DE": "HelloFresh",
 "SHL.DE": "Siemens Healthineers", "P911.DE": "Porsche AG", "RHM.DE": "Rheinmetall",
 "HEI.DE": "Heidelberg Materials", "SY1.DE": "Symrise", "EVK.DE": "Evonik",
 "LXS.DE": "Lanxess", "PUM.DE": "Puma", "TKA.DE": "ThyssenKrupp", "SDF.DE": "K+S",
 "FNTN.DE": "Freenet", "NEM.DE": "Nemetschek", "AIR.DE": "Airbus",
 "DHER.DE": "Delivery Hero", "BEI.DE": "Beiersdorf", "DB1.DE": "Deutsche Boerse",
 "MTX.DE": "MTU Aero", "QIA.DE": "Qiagen", "SRT3.DE": "Sartorius", "BNR.DE": "Brenntag",
 "G1A.DE": "GEA Group", "KGX.DE": "Kion Group", "NDA.DE": "Aurubis"
}

FALLBACK = [("RWE.DE", "RWE"), ("IFX.DE", "Infineon"), ("BAYN.DE", "Bayer"),
            ("SAP.DE", "SAP SE"), ("ALV.DE", "Allianz")]


def score(ticker):
    try:
        h = yf.Ticker(ticker).history(period="6mo", interval="1d", auto_adjust=False)
        h = h[["High", "Low", "Close", "Volume"]].dropna()
        h = h[h["Close"] > 0]
        if len(h) < 30:
            return None
        c = [float(x) for x in h["Close"]]
        hi = [float(x) for x in h["High"]]
        lo = [float(x) for x in h["Low"]]
        v = [float(x) for x in h["Volume"]]
        price = c[-1]
        if price > MAX_PRICE:
            return None
        trs = []
        for i in range(-14, 0):
            trs.append(max(hi[i] - lo[i], abs(hi[i] - c[i - 1]), abs(lo[i] - c[i - 1])))
        atrp = (sum(trs) / 14 / price) * 100
        if atrp < MIN_ATR_PCT:
            return None
        turnover = (sum(v[-20:]) / 20) * price
        if turnover < MIN_TURNOVER:
            return None
        sma20 = sum(c[-20:]) / 20
        ret20 = (price / c[-21] - 1) * 100 if len(c) >= 21 else 0
        trend = 1 if price > sma20 else 0
        sc = atrp * 6 + (turnover ** 0.5) / 60 + trend * 12 + max(min(ret20, 15), -15)
        return {"ticker": ticker, "price": round(price, 2), "atrp": round(atrp, 2),
                "ret20": round(ret20, 2), "score": round(sc, 1)}
    except Exception as e:
        print("  [skip] " + ticker + ": " + str(e))
        return None


def write(rows):
    with open("watchlist.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ticker", "name", "note"])
        for r in rows:
            w.writerow([r["ticker"], r["name"],
                        "ATR " + str(r.get("atrp", 0)) + "% | 20d " + str(r.get("ret20", 0))
                        + "% | score " + str(r.get("score", 0))])


def main():
    ranked = []
    for t, name in UNIVERSE.items():
        r = score(t)
        if r:
            r["name"] = name
            ranked.append(r)
    ranked.sort(key=lambda x: x["score"], reverse=True)
    top = ranked[:KEEP]

    if len(top) < 3:
        if os.path.exists("watchlist.csv"):
            print("WARNING: only " + str(len(top)) + " qualified - keeping existing watchlist.csv")
            return
        print("WARNING: no qualifying names and no existing list - writing fallback list")
        top = [{"ticker": t, "name": n} for t, n in FALLBACK]

    write(top)
    print("watchlist.csv: " + str(len(top)) + " names (of " + str(len(ranked)) + " qualifying)")
    for r in top:
        print("  " + r["ticker"] + "  EUR" + str(r.get("price", "-"))
              + "  ATR " + str(r.get("atrp", "-")) + "%  20d " + str(r.get("ret20", "-")) + "%")


if __name__ == "__main__":
    main()
