# refresh_watchlist.py — daily intelligent watchlist for Germany (XETRA .DE).
# Scores a broad universe by movement + liquidity + momentum + affordability,
# keeps the top ~12 "most tradable movers" -> writes watchlist.csv.
# Data: yfinance (~15-min delayed). Research/education. NOT financial advice.

import csv
import yfinance as yf

POOL_EUR = 200.0
KEEP = 12
MIN_ATR_PCT = 1.5     # must be able to move enough to matter vs 3% fee bar over a swing

# Broad liquid German universe (DAX + liquid MDAX). Edit freely.
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
        if len(h) < 20: return None
        c=[float(x) for x in h["Close"]]; hi=[float(x) for x in h["High"]]
        lo=[float(x) for x in h["Low"]]; v=[float(x) for x in h["Volume"
