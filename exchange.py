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
        hashed_payload = hashlib.sha512(body.encode('utf-8')).hexdigest()
        signature_string = f"{method}
{url_path}
{query_string}
{hashed_payload}
{t}"
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            signature_string.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()
        return {
            "KEY": self.api_key,
            "Timestamp": t,
            "SIGN": signature,
            "Content-Type": "application/json"
        }

    def get_balance(self):
        """Get USDT balance"""
        path = "/spot/accounts"
        headers = self._sign("GET", "/api/v4/spot/accounts")
        resp = requests.get(f"{self.BASE_URL}/spot/accounts", headers=headers, timeout=10)
        data = resp.json()
        for acc in data:
            if acc.get('currency') == 'USDT':
                return float(acc.get('available', 0))
        return 0.0

    def get_klines(self, symbol, interval="15m", limit=200):
        """Get candlestick data"""
        path = "/spot/candlesticks"
        params = {"currency_pair": symbol, "interval": interval, "limit": limit}
        resp = requests.get(f"{self.BASE_URL}/spot/candlesticks", params=params, timeout=10)
        data = resp.json()
        # Gate.io format: [time, volume, close, high, low, open]
        candles = []
        for c in data:
            candles.append({
                'time': int(c[0]),
                'volume': float(c[1]),
                'close': float(c[2]),
                'high': float(c[3]),
                'low': float(c[4]),
                'open': float(c[5])
            })
        return candles

    def get_ticker(self, symbol):
        """Get current price"""
        resp = requests.get(f"{self.BASE_URL}/spot/tickers", params={"currency_pair": symbol}, timeout=10)
        data = resp.json()
        if data:
            return float(data[0].get('last', 0))
        return 0.0

    def place_order(self, symbol, side, amount, price=None, order_type="market"):
        """Place spot order"""
        body = json.dumps({
            "currency_pair": symbol,
            "side": side.lower(),  # buy or sell
            "type": order_type,
            "amount": str(amount)
        })
        if price and order_type == "limit":
            body_dict = json.loads(body)
            body_dict["price"] = str(price)
            body = json.dumps(body_dict)

        path = "/spot/orders"
        headers = self._sign("POST", "/api/v4/spot/orders", "", body)
        resp = requests.post(f"{self.BASE_URL}/spot/orders", headers=headers, data=body, timeout=10)
        return resp.json()

    def get_open_orders(self, symbol):
        """Get open orders"""
        path = "/spot/open_orders"
        params = f"currency_pair={symbol}"
        headers = self._sign("GET", "/api/v4/spot/open_orders", params)
        resp = requests.get(f"{self.BASE_URL}/spot/open_orders?{params}", headers=headers, timeout=10)
        return resp.json()

    def cancel_order(self, order_id, symbol):
        """Cancel an order"""
        path = f"/spot/orders/{order_id}"
        body = json.dumps({"currency_pair": symbol})
        headers = self._sign("DELETE", f"/api/v4/spot/orders/{order_id}", f"currency_pair={symbol}", body)
        resp = requests.delete(f"{self.BASE_URL}/spot/orders/{order_id}", headers=headers, data=body, timeout=10)
        return resp.json()
