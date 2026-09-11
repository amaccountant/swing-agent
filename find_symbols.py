# find_symbols.py — decisive test: does the key work for US? for Germany? print full error bodies.
import os, json, urllib.request, urllib.parse

API_KEY = os.environ.get("TWELVE_DATA_KEY","").strip()
BASE = "https://api.twelvedata.com"

def get_raw(path, params):
    params = dict(params); params["apikey"] = API_KEY
    url = f"{BASE}/{path}?" + urllib.parse.urlencode(params)
    safe_url = url.replace(API_KEY, "***KEY***")
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            body = r.read().decode()
        return safe_url, r.status, body
    except urllib.error.HTTPError as e:
        return safe_url, e.code, e.read().decode()
    except Exception as e:
        return safe_url, "EXC", str(e)

tests = [
    ("US AAPL",            "time_series", {"symbol":"AAPL","interval":"1day","outputsize":3}),
    ("US MSFT quote",      "quote",       {"symbol":"MSFT"}),
    ("DE SAP plain",       "time_series", {"symbol":"SAP","interval":"1day","outputsize":3}),
    ("DE SAP mic XETR",    "time_series", {"symbol":"SAP","mic_code":"XETR","interval":"1day","outputsize":3}),
    ("DE SAP exch XETRA",  "time_series", {"symbol":"SAP","exchange":"XETRA","interval":"1day","outputsize":3}),
    ("API usage",          "api_usage",   {}),
]
for label, path, params in tests:
    url, status, body = get_raw(path, params)
    print(f"\n=== {label} ===")
    print("URL   :", url)
    print("STATUS:", status)
    print("BODY  :", body[:400])
