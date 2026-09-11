# find_symbols.py — one-time helper: list German (XETRA) stocks your Twelve Data key can access.
import os, json, urllib.request, urllib.parse

API_KEY = os.environ.get("TWELVE_DATA_KEY","").strip()
BASE = "https://api.twelvedata.com"

def get(path, params):
    params = dict(params); params["apikey"] = API_KEY
    url = f"{BASE}/{path}?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode())

# 1) Confirm which endpoints your plan allows, and check a few names by ISIN + by symbol.
tests = [
    ("SAP by symbol+country", {"symbol":"SAP","country":"Germany"}),
    ("SAP by mic XETR",       {"symbol":"SAP","mic_code":"XETR"}),
    ("SAP by exchange XETRA", {"symbol":"SAP","exchange":"XETRA"}),
    ("Telekom by ISIN",       {"symbol":"","isin":"DE0005557508"}),
]
for label, extra in tests:
    p = {"interval":"1day","outputsize":3}; p.update(extra)
    p = {k:v for k,v in p.items() if v != ""}
    try:
        d = get("time_series", p)
        ok = "values" in d
        print(f"[{label}] -> {'OK, last close='+d['values'][0]['close'] if ok else d.get('message', d)}")
    except Exception as e:
        print(f"[{label}] -> EXCEPTION {e}")

# 2) Ask the catalog which German stocks exist on your plan (first 25).
try:
    lst = get("stocks", {"country":"Germany"})
    data = lst.get("data", []) if isinstance(lst, dict) else []
    print(f"\nGerman stocks in catalog: {len(data)} (showing first 25)")
    for row in data[:25]:
        print(f"  {row.get('symbol'):10} {row.get('mic_code'):6} {row.get('exchange'):8} {row.get('name')}")
except Exception as e:
    print("stocks list error:", e)
