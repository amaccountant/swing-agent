# find_symbols.py — find the exact symbol/mic_code your plan exposes for each target company,
# then verify a time_series call actually returns data for the best match.
import os, json, urllib.request, urllib.parse

API_KEY = os.environ.get("TWELVE_DATA_KEY","").strip()
BASE = "https://api.twelvedata.com"

def get(path, params):
    params = dict(params); params["apikey"] = API_KEY
    url = f"{BASE}/{path}?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode())

# Companies we want, matched by ISIN (unique + reliable).
targets = {
    "SAP SE":            "DE0007164600",
    "Deutsche Telekom":  "DE0005557508",
    "Deutsche Bank":     "DE0005140008",
    "Commerzbank":       "DE000CBK1001",
    "Lufthansa":         "DE0008232125",
    "Infineon":          "DE0006231004",
    "RWE":               "DE0007037129",
    "E.ON":              "DE000ENAG999",
    "Volkswagen pref":   "DE0007664039",
    "Bayer":             "DE000BAY0017",
}

pref_mic = ["XFRA","XETR","XSTU","XMUN","XDUS"]  # preference order

for name, isin in targets.items():
    try:
        res = get("stocks", {"isin": isin})
        rows = res.get("data", []) if isinstance(res, dict) else []
        if not rows:
            print(f"{name} ({isin}) -> NOT in catalog"); continue
        # choose preferred exchange listing
        rows.sort(key=lambda r: pref_mic.index(r.get("mic_code")) if r.get("mic_code") in pref_mic else 99)
        best = rows[0]
        sym, mic = best.get("symbol"), best.get("mic_code")
        # verify time_series returns data for this symbol+mic
        p = {"symbol": sym, "mic_code": mic, "interval":"1day", "outputsize":3}
        try:
            d = get("time_series", p)
            ok = "values" in d
            close = d["values"][0]["close"] if ok else None
            print(f"{name:20} sym={sym:8} mic={mic:6} -> {'OK close='+close if ok else d.get('message', d)}")
        except Exception as e:
            print(f"{name:20} sym={sym:8} mic={mic:6} -> time_series EXCEPTION {e}")
    except Exception as e:
        print(f"{name:20} ({isin}) -> stocks lookup EXCEPTION {e}")
