#!/usr/bin/env python3
"""Quick test to check if Bybit API is accessible from this environment"""
import requests
import sys

endpoint = "https://api.bybit.com"
symbol = "HYPEUSDT"

print(f"Testing Bybit API endpoint: {endpoint}/v5/market/tickers")
print(f"Symbol: {symbol}")
print("-" * 50)

try:
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; TestBot/1.0)",
        "Accept": "application/json"
    }
    url = f"{endpoint}/v5/market/tickers?category=linear&symbol={symbol}"
    print(f"URL: {url}")
    print(f"Headers: {headers}")
    print("-" * 50)
    
    res = requests.get(url, headers=headers, timeout=10)
    
    print(f"Status Code: {res.status_code}")
    print(f"Response Headers: {dict(res.headers)}")
    print("-" * 50)
    
    if res.status_code == 200:
        data = res.json()
        print("✅ SUCCESS! API is accessible")
        if "result" in data and "list" in data["result"] and len(data["result"]["list"]) > 0:
            price = data["result"]["list"][0].get("lastPrice")
            print(f"Price for {symbol}: ${price}")
        else:
            print(f"Unexpected response format: {data}")
    else:
        print(f"❌ FAILED with status {res.status_code}")
        print(f"Response: {res.text[:500]}")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ ERROR: {e}")
    sys.exit(1)
