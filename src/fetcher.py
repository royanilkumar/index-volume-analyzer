import requests
import pandas as pd
from datetime import datetime

class NSEFetcher:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self._init_session()

    def _init_session(self):
        try:
            self.session.get("https://www.nseindia.com", timeout=10)
        except Exception as e:
            print(f"[ERROR] Session initialization failed: {e}")

    def fetch_index_snapshot(self, index_symbol="NIFTY 50"):
        """Fetches current constituent traded volumes for a given index."""
        url = f"https://www.nseindia.com/api/equity-stockIndices?index={index_symbol.replace(' ', '%20')}"
        try:
            res = self.session.get(url, timeout=10)
            if res.status_code == 200:
                raw_data = res.json().get('data', [])
                records = []
                today = datetime.now().strftime('%Y-%m-%d')
                
                for item in raw_data:
                    # Skip the index summary row itself
                    if item.get('priority') == 1:
                        continue
                    records.append({
                        "date": today,
                        "symbol": item.get('symbol'),
                        "last_price": item.get('lastPrice', 0.0),
                        "p_change": item.get('pChange', 0.0),
                        "total_volume": item.get('totalTradedVolume', 0),
                        "total_value": item.get('totalTradedValue', 0.0)
                    })
                return pd.DataFrame(records)
        except Exception as e:
            print(f"[ERROR] Fetching stock index failed: {e}")
        return pd.DataFrame()

    def fetch_derivative_depth(self, symbol="NIFTY"):
        """Fetches pending buy (bid) vs sell (ask) quantity for near-month futures."""
        url = f"https://www.nseindia.com/api/quote-derivative?symbol={symbol}"
        try:
            res = self.session.get(url, timeout=10)
            if res.status_code == 200:
                data = res.json()
                fut = data['stocks'][0]['marketDeptOrderBook']
                buy_qty = fut.get('totalBuyQuantity', 0)
                sell_qty = fut.get('totalSellQuantity', 0)
                
                return {
                    "date": datetime.now().strftime('%Y-%m-%d'),
                    "symbol": symbol,
                    "buy_qty": buy_qty,
                    "sell_qty": sell_qty,
                    "net_delta": buy_qty - sell_qty
                }
        except Exception as e:
            print(f"[ERROR] Derivative depth fetch failed: {e}")
        return None