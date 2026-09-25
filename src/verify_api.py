import urllib.request
import json
import time

def verify():
    url = "http://127.0.0.1:8000/api/trades"
    # Wait up to 5 seconds for server ready
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=3) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    print("SUCCESS: /api/trades responded 200 OK")
                    print(f"- Status: {data.get('status')}")
                    print(f"- Live Trades Count: {len(data.get('live_trades', []))}")
                    t0 = data.get('live_trades', [])[0]
                    print(f"- Sample Trade: {t0.get('side')} {t0.get('leverage')}x | Time: {t0.get('timestamp_kst')} | Hold: {t0.get('holding_time')} | Exit: {t0.get('exit_reason')}")
                    s = data.get('summary', {})
                    print(f"- Summary: {s.get('wins')}승 {s.get('losses')}패 | WinRate: {s.get('win_rate_pct')}% | NetPnL: {s.get('net_pnl_btc')} BTC")
                    assert t0.get('side') is not None, "side is None"
                    assert t0.get('leverage') is not None, "leverage is None"
                    assert t0.get('timestamp_kst') is not None, "timestamp_kst is None"
                    assert s.get('wins') is not None, "wins is None"
                    
                    # Verify Root HTML
                    root_req = urllib.request.Request("http://127.0.0.1:8000/", headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(root_req, timeout=3) as r_resp:
                        html = r_resp.read().decode('utf-8')
                        has_tab = "tab-btn-live-trades" in html and "tab-btn-legend-trades" in html
                        has_wonyo = "triggerWonyoQuote" in html
                        print(f"SUCCESS: Root HTML fetched (Tabs: {has_tab}, WonyoQuote: {has_wonyo})")
                    return True
        except Exception as e:
            print("Retry error:", e)
            time.sleep(1)
    print("FAILED to connect to /api/trades")
    return False

if __name__ == "__main__":
    verify()
