from typing import Dict, List, Optional

class VWAPStrategy:
    def __init__(self, ema_len=34, ema_slope_len=3, pullback_dist=0.5, 
                 atr_len=14, sl_mult=2.0, tp_mult=2.0, long_only=True):
        self.ema_len = ema_len
        self.ema_slope_len = ema_slope_len
        self.pullback_dist = pullback_dist
        self.atr_len = atr_len
        self.sl_mult = sl_mult
        self.tp_mult = tp_mult
        self.long_only = long_only

    def _ema(self, data, period):
        if len(data) < period:
            return data
        k = 2.0 / (period + 1)
        ema = [sum(data[:period]) / period]
        for price in data[period:]:
            ema.append(price * k + ema[-1] * (1 - k))
        result = [None] * (period - 1) + ema
        return result

    def _atr(self, highs, lows, closes, period):
        if len(closes) < period + 1:
            return [0] * len(closes)
        trs = []
        for i in range(1, len(closes)):
            tr1 = highs[i] - lows[i]
            tr2 = abs(highs[i] - closes[i-1])
            tr3 = abs(lows[i] - closes[i-1])
            trs.append(max(tr1, tr2, tr3))

        atr = [sum(trs[:period]) / period]
        for tr in trs[period:]:
            atr.append((atr[-1] * (period - 1) + tr) / period)

        result = [0] * (period) + atr
        return result

    def _vwap(self, candles):
        vwap = []
        cum_tp_vol = 0.0
        cum_vol = 0.0

        for c in candles:
            tp = (c["high"] + c["low"] + c["close"]) / 3.0
            vol = max(c["volume"], 1.0)
            cum_tp_vol += tp * vol
            cum_vol += vol
            vwap.append(cum_tp_vol / cum_vol if cum_vol > 0 else c["close"])

        return vwap

    def analyze(self, candles):
        if len(candles) < max(self.ema_len, self.atr_len) + 10:
            return {"signal": None, "reason": "Insufficient data", "strength": 0}

        closes = [c["close"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]

        vwap = self._vwap(candles)
        ema9 = self._ema(closes, 9)
        ema20 = self._ema(closes, self.ema_len)
        ema50 = self._ema(closes, 50)
        atr = self._atr(highs, lows, closes, self.atr_len)

        i = len(candles) - 1
        curr_close = closes[i]
        curr_vwap = vwap[i]
        curr_ema9 = ema9[i]
        curr_ema20 = ema20[i]
        curr_ema50 = ema50[i]
        curr_atr = atr[i]

        if curr_ema20 is None or curr_atr == 0:
            return {"signal": None, "reason": "Indicators not ready", "strength": 0}

        prev_ema20 = ema20[i - self.ema_slope_len] if i >= self.ema_slope_len else curr_ema20
        ema_slope = curr_ema20 - prev_ema20

        bull_trend = curr_close > curr_vwap and ema_slope > 0
        bear_trend = curr_close < curr_vwap and ema_slope < 0 and not self.long_only

        vwap_dist = abs(curr_close - curr_vwap) / curr_close * 100 if curr_vwap else 99.0
        near_vwap = vwap_dist <= self.pullback_dist

        was_near_vwap = near_vwap
        for j in range(1, 4):
            if i - j >= 0 and curr_vwap:
                dist = abs(closes[i-j] - curr_vwap) / closes[i-j] * 100
                if dist <= self.pullback_dist:
                    was_near_vwap = True
                    break

        bounce_long = was_near_vwap and curr_close > curr_vwap
        bounce_short = was_near_vwap and curr_close < curr_vwap

        signal = None
        entry_price = curr_close
        stop_loss = None
        take_profit = None
        strength = 0

        if bull_trend and bounce_long:
            signal = "LONG"
            stop_loss = curr_close - curr_atr * self.sl_mult
            take_profit = curr_close + curr_atr * self.tp_mult
            strength = min(100, (ema_slope / curr_ema20 * 100) * 10 + 50)
        elif bear_trend and bounce_short:
            signal = "SHORT"
            stop_loss = curr_close + curr_atr * self.sl_mult
            take_profit = curr_close - curr_atr * self.tp_mult
            strength = min(100, (abs(ema_slope) / curr_ema20 * 100) * 10 + 50)

        return {
            "signal": signal,
            "price": curr_close,
            "vwap": curr_vwap,
            "ema9": curr_ema9,
            "ema20": curr_ema20,
            "ema50": curr_ema50,
            "ema_slope": ema_slope,
            "atr": curr_atr,
            "vwap_dist": vwap_dist,
            "bull_trend": bull_trend,
            "bear_trend": bear_trend,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "strength": strength,
            "reason": "Trend: " + ("BULL" if bull_trend else "BEAR" if bear_trend else "NEUTRAL") + ", VWAP dist: " + str(round(vwap_dist, 2)) + "%, Strength: " + str(round(strength, 1))
        }
