import hmac
import hashlib
import json
import time
import requests
from config import GATEIO_API_KEY, GATEIO_API_SECRET

class GateIO:
    BASE_URL = "https://api.gateio.ws/api/v4"

    def __init__(self):
        self.api_key = GATEIO_API_KEY
        self.api_secret = GATEIO_API_SECRET

    def _sign(self, method, url_path, query_string="", body=""):
        t = str(int(time.time()))
        hashed_payload = hashlib.sha512(body.encode("utf-8")).hexdigest()
        nl = chr(10)
        signature_string = method + nl + url_path + nl + query_string + nl + hashed_payload + nl + t
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            signature_string.encode("utf-8"),
            hashlib.sha512
        ).hexdigest()
        return {
            "KEY": self.api_key,
            "Timestamp": t,
            "SIGN": signature,
            "Content-Type": "application/json"
        }

    def get_balance(self):
        headers = self._sign("GET", "/api/v4/spot/accounts")
        resp = requests.get(self.BASE_URL + "/spot/accounts", headers=headers, timeout=10)
        data = resp.json()
        for acc in data:
            if acc.get("currency") == "USDT":
                return float(acc.get("available", 0))
        return 0.0

    def get_top_coins(self, limit=500):
        """Get top 500 coins by volume"""
        resp = requests.get(self.BASE_URL + "/spot/tickers", timeout=10)
        data = resp.json()
        coins = []
        for item in data:
            symbol = item.get("currency_pair", "")
            if symbol.endswith("_USDT") and not any(symbol.startswith(x) for x in ["3", "5", "1", "2"]):
                volume = float(item.get("quote_volume", 0))
                price = float(item.get("last", 0))
                if volume > 500000 and price > 0.001:
                    coins.append({
                        "symbol": symbol,
                        "volume": volume,
                        "price": price
                    })
        coins.sort(key=lambda x: x["volume"], reverse=True)
        return coins[:limit]

    def get_klines(self, symbol, interval="1h", limit=200):
        params = {"currency_pair": symbol, "interval": interval, "limit": limit}
        resp = requests.get(self.BASE_URL + "/spot/candlesticks", params=params, timeout=10)
        data = resp.json()
        candles = []
        for c in data:
            candles.append({
                "time": int(c[0]),
                "volume": float(c[1]),
                "close": float(c[2]),
                "high": float(c[3]),
                "low": float(c[4]),
                "open": float(c[5])
            })
        return candles

    def get_ticker(self, symbol):
        resp = requests.get(self.BASE_URL + "/spot/tickers", params={"currency_pair": symbol}, timeout=10)
        data = resp.json()
        if data:
            return float(data[0].get("last", 0))
        return 0.0

    def place_order(self, symbol, side, amount, price=None, order_type="market"):
        body_dict = {
            "currency_pair": symbol,
            "side": side.lower(),
            "type": order_type,
            "amount": str(amount)
        }
        if price and order_type == "limit":
            body_dict["price"] = str(price)
        body = json.dumps(body_dict)
        headers = self._sign("POST", "/api/v4/spot/orders", "", body)
        resp = requests.post(self.BASE_URL + "/spot/orders", headers=headers, data=body, timeout=10)
        return resp.json()
